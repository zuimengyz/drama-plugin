"""Two-process T6 recovery probes using controlled, explicitly synthetic sources."""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace
import json
from pathlib import Path

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.creation import Work, Script, Episode, Scene, Shot
from drama_plugin.generation.contracts import FinalPromptArtifact, GenerationPreparation
from drama_plugin.governance.contracts import GateEffect
from drama_plugin.persistence import DurableReviewStore, DurableRunStore, ProductionLedger, UserDecisionRecord
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.runtime import (
    ActionKind, ArtifactReference, CapabilityResult, DecisionCategory, LegacyCapabilityBridge,
    ResultStatus, RunMode, RuntimeAction, RuntimeEngine, RuntimeState, RuntimeWorkflow,
    UserDecisionRequest,
)
from unittest.mock import patch

PLUGIN = Path(__file__).resolve().parents[1]
MODELS = {"work": Work, "script": Script, "episode": Episode, "scene": Scene, "shot": Shot}


def load_data(file: Path) -> MockDramaData:
    rows = json.loads(file.read_text())
    data = MockDramaData.empty()
    for key, model in MODELS.items():
        setattr(data, key, model.model_validate(rows[key]))
    return data


def save_data(file: Path, data: MockDramaData) -> None:
    file.write_text(json.dumps({key: dump_contract(getattr(data, key)) for key in MODELS},
        ensure_ascii=False, indent=2) + "\n")


def policy_v2(plugin: DramaPlugin) -> None:
    old = plugin.prompt_compiler.catalog.policy("seedance-2-standard")
    plugin.prompt_compiler.catalog.policy = lambda _: replace(old, version="test-t6-v2", fingerprint="d" * 64)


async def target_case(scenario: str, phase: str, ledger_path: Path,
                      fixture: Path, designs: Path, output: Path, prior: Path | None):
    data = load_data(fixture)
    with patch("drama_plugin.plugin.load_config", return_value=DramaPluginConfig()):
        async with DramaPlugin.load(PLUGIN, mock_data=data,
                legacy_reads=True, production_artifact_roots=(designs,), ledger_path=ledger_path) as plugin:
            if phase == "start":
                seed = plugin.create_generation_run(work_id="work", scene_id="scene", shot_id="shot",
                    mode=RunMode.EXPERIMENT, run_id=scenario + "-seed")
                first = await plugin.runtime.run(seed.run_id)
                assert first.state == RuntimeState.SUCCEEDED
                old_prepared_ref = plugin.generation_artifacts.prepared(seed.run_id)
                old_prepared = plugin.generation_artifacts.get(old_prepared_ref, GenerationPreparation)
                if scenario == "package":
                    data.shot.content["subjectAction"] = "合法作者修订后的当前动作"
                    save_data(fixture, data)
                    pending = plugin.create_generation_run(work_id="work", scene_id="scene", shot_id="shot",
                        mode=RunMode.EXPERIMENT, run_id="package-pending",
                        package_ref=old_prepared.source_package_ref)
                    checkpoint = await plugin.runtime.run(pending.run_id, max_ticks=2)
                    assert checkpoint.cursor == 1 and checkpoint.state == RuntimeState.READY
                else:
                    policy_v2(plugin)
                    pending = plugin.create_generation_run(work_id="work", scene_id="scene", shot_id="shot",
                        mode=RunMode.EXPERIMENT, run_id="prompt-pending",
                        cached_preparation_ref=old_prepared_ref)
                    checkpoint = await plugin.runtime.run(pending.run_id, max_ticks=5)
                    assert checkpoint.cursor == 4 and checkpoint.state == RuntimeState.READY
                decision = plugin.gate_findings.decision(plugin.gate_findings.latest(pending.run_id))
                assert decision.effect == GateEffect.AUTO_MAINTAIN
                result = {"scenario": scenario, "phase": phase, "runId": pending.run_id,
                    "state": checkpoint.state.value, "cursor": checkpoint.cursor,
                    "revision": checkpoint.revision,
                    "oldPackageRef": old_prepared.source_package_ref.model_dump(mode="json"),
                    "oldFinalRef": old_prepared.final_prompt_ref.model_dump(mode="json"),
                    "gateEffect": decision.effect.value}
            else:
                expected = json.loads(prior.read_text())
                if scenario == "prompt":
                    policy_v2(plugin)
                restored = await plugin.runtime.recover_run(expected["runId"])
                assert restored.revision == expected["revision"] and restored.state == RuntimeState.READY
                decision = plugin.gate_findings.decision(plugin.gate_findings.latest(restored.run_id))
                assert decision.effect == GateEffect.AUTO_MAINTAIN and decision.user_decision is None
                counts = {"assembler": 0, "generator": 0}
                assemble = plugin.shot_assembler.assemble
                generate = plugin.prompt_compiler.generator.generate
                async def counted_assembly(*a, **k):
                    counts["assembler"] += 1
                    return await assemble(*a, **k)
                def counted_generator(*a, **k):
                    counts["generator"] += 1
                    return generate(*a, **k)
                with patch.object(plugin.shot_assembler, "assemble", counted_assembly), \
                     patch.object(plugin.prompt_compiler.generator, "generate", counted_generator):
                    finished = await plugin.runtime.run(restored.run_id)
                assert finished.state == RuntimeState.SUCCEEDED
                prepared = plugin.generation_artifacts.get(
                    plugin.generation_artifacts.prepared(restored.run_id), GenerationPreparation)
                final = plugin.generation_artifacts.get(prepared.final_prompt_ref, FinalPromptArtifact)
                assert (prepared.source_package_ref != ArtifactReference.model_validate(expected["oldPackageRef"])) == (scenario == "package")
                assert prepared.final_prompt_ref != ArtifactReference.model_validate(expected["oldFinalRef"])
                assert counts == ({"assembler": 1, "generator": 1} if scenario == "package" else
                    {"assembler": 0, "generator": 1})
                result = {"scenario": scenario, "phase": phase, "runId": restored.run_id,
                    "state": finished.state.value, "revision": finished.revision,
                    "gateEffectBeforeResume": decision.effect.value,
                    "assemblerCalls": counts["assembler"], "generatorCalls": counts["generator"],
                    "governanceMaintenanceCount": plugin.gate_findings.maintenance_count(restored.run_id),
                    "userDecisionRequested": False, "newPackageRef": prepared.source_package_ref.model_dump(mode="json"),
                    "newFinalRef": prepared.final_prompt_ref.model_dump(mode="json"),
                    "promptContainsLegalRevision": "合法作者修订后的当前动作" in final.prompt_text,
                    "providerSubmission": 0}
                if scenario == "package":
                    assert result["governanceMaintenanceCount"] == 1 and result["promptContainsLegalRevision"]
                else:
                    assert plugin.ledger.get_index("generation-rebuild", restored.run_id) == 1
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"scenario": scenario, "phase": phase, "state": result["state"]}))


async def wait_case(scenario: str, phase: str, ledger_path: Path,
                    output: Path, prior: Path | None):
    if scenario == "user":
        action = RuntimeAction(kind=ActionKind.REQUEST_USER_DECISION,
            decision=UserDecisionRequest(category=DecisionCategory.ART_APPROVAL, question="批准测试镜头？"))
    else:
        action = RuntimeAction(kind=ActionKind.WAIT_EXTERNAL,
            external_ref=ArtifactReference(owner="quality-review", artifact_ref="review-fixture", version=1))
    workflow = RuntimeWorkflow(workflow_id="t6-wait-fixture:v1", steps=(action,))
    ledger = ProductionLedger(ledger_path)
    runtime = RuntimeEngine(LegacyCapabilityBridge({}), store=DurableRunStore(ledger),
        workflows={workflow.workflow_id: workflow})
    if phase == "start":
        run = runtime.create_run(work_id="work", mode=RunMode.EXPERIMENT,
            workflow_id=workflow.workflow_id, run_id=scenario + "-wait")
        state = await runtime.run(run.run_id)
        expected_state = RuntimeState.WAITING_USER if scenario == "user" else RuntimeState.WAITING_EXTERNAL
        assert state.state == expected_state
        result = {"scenario": scenario, "phase": phase, "runId": run.run_id,
            "state": state.state.value, "revision": state.revision,
            "decisionId": runtime.decision_id(run.run_id) if scenario == "user" else None,
            "externalRef": action.external_ref.model_dump(mode="json") if scenario == "external" else None}
    else:
        old = json.loads(prior.read_text())
        restored = await runtime.recover_run(old["runId"])
        assert restored.state.value == old["state"] and restored.revision == old["revision"]
        assert (await runtime.run(restored.run_id)).state == restored.state
        review_ref = None
        if scenario == "user":
            assert runtime.decision_id(restored.run_id) == old["decisionId"]
            record = UserDecisionRecord.seal(run_id=restored.run_id, scope=restored.scope,
                decision_id=old["decisionId"], category=DecisionCategory.ART_APPROVAL, accepted=True)
            review = DurableReviewStore(ledger)
            review_ref = review.put_user_decision(record)
            await runtime.decide(restored.run_id, decision_id=old["decisionId"],
                accepted=True, decision_ref=review_ref)
            assert review.user_decision(review_ref) == record
        else:
            await runtime.record_external_result(restored.run_id,
                external_ref=ArtifactReference.model_validate(old["externalRef"]),
                result=CapabilityResult(status=ResultStatus.SUCCEEDED))
        terminal = await runtime.run(restored.run_id)
        assert terminal.state == RuntimeState.SUCCEEDED
        result = {"scenario": scenario, "phase": phase, "runId": restored.run_id,
            "state": terminal.state.value, "reviewRef": review_ref.model_dump(mode="json") if review_ref else None,
            "sameWaitIdentity": True, "providerSubmission": 0}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"scenario": scenario, "phase": phase, "state": result["state"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=("package", "prompt", "user", "external"))
    parser.add_argument("phase", choices=("start", "resume"))
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prior", type=Path)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--designs", type=Path)
    args = parser.parse_args()
    if args.scenario in {"package", "prompt"}:
        assert args.fixture and args.designs
        asyncio.run(target_case(args.scenario, args.phase, args.ledger,
            args.fixture, args.designs, args.output, args.prior))
    else:
        asyncio.run(wait_case(args.scenario, args.phase, args.ledger, args.output, args.prior))
