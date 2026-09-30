"""T6 durable Target ledger: separate instances, CAS, review waits and size bounds."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.base import dump_contract
from drama_plugin.generation.contracts import (
    AudioExecutionPlan, FinalPromptArtifact, GenerationPreparation, GenerationTask,
    PromptCoverage, PromptIR,
)
from drama_plugin.governance.contracts import GateCode, GateFinding
from drama_plugin.persistence import (
    DurableReferenceExecutionStore, DurableRunStore, DurableReviewStore, ProductionLedger, UserDecisionRecord,
)
from drama_plugin.production.contracts import AssemblyIssueCode, ProductionPackage
from drama_plugin.production.sources import SourceReadError
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.runtime import (
    ActionKind, ArtifactReference, CapabilityResult, DecisionCategory,
    LegacyCapability, LegacyCapabilityBridge, ResultStatus, RunMode, RuntimeAction, RuntimeEngine,
    RuntimeRun, RuntimeScope, RuntimeState, RuntimeWorkflow, UserDecisionRequest,
)

from test_prompt_audio_convergence import generation_fixture
from test_prompt_obligation_reconciliation import bound_fixture
from test_production_package import fixture

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("T6 forbids network, Provider submission and media generation")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr("drama_plugin.plugin.load_config", lambda _: DramaPluginConfig())


def load(fixture, ledger_path):
    data, directory = fixture
    return DramaPlugin.load(ROOT, mock_data=data, production_artifact_roots=(directory,),
        ledger_path=ledger_path)


def engine(ledger, steps):
    workflow = RuntimeWorkflow(workflow_id="t6-offline:v1", steps=steps)
    return RuntimeEngine(LegacyCapabilityBridge({}), store=DurableRunStore(ledger),
        workflows={workflow.workflow_id: workflow})


def create_run(ledger, identity="run"):
    return RuntimeRun(run_id=identity, scope=RuntimeScope(work_id="work"), mode=RunMode.EXPERIMENT,
        policy_id="offline", workflow_id="offline:v1", workflow_fingerprint="0" * 64)


def test_cas_stale_writer_rejected_and_checkpoint_bounded(tmp_path):
    ledger = ProductionLedger(tmp_path / "ledger.sqlite3")
    a, b = DurableRunStore(ledger), DurableRunStore(ProductionLedger(ledger.path))
    original = a.create(create_run(ledger))
    assert a.load("run") == b.load("run") == original
    updated = a.save(original.model_copy(update={"revision": 1, "state": RuntimeState.READY}), expected_revision=0)
    assert updated.revision == 1
    with pytest.raises(ValueError, match="revision conflict"):
        b.save(original.model_copy(update={"revision": 1, "state": RuntimeState.READY}), expected_revision=0)
    assert len(ledger.load_run("run").model_dump_json().encode()) < 4096
    with pytest.raises(ValueError, match="immutable"):
        b.save(updated.model_copy(update={"revision": 2, "scope": RuntimeScope(work_id="other")}), expected_revision=1)


@pytest.mark.asyncio
async def test_two_plugin_instances_same_package_prompt_audio_binding_and_no_reexecute(bound_fixture, tmp_path, monkeypatch):
    fixture, _, binding = bound_fixture
    path = tmp_path / "ledger.sqlite3"
    first = load(fixture, path)
    first.execution_references.register(binding)
    run = first.create_generation_run(work_id="work", scene_id="scene", shot_id="shot",
        mode=RunMode.EXPERIMENT, run_id="durable-image",
        task=GenerationTask(input_mode="image_to_video", native_audio="REQUIRED"))
    partial = await first.runtime.run(run.run_id, max_ticks=5)
    assert partial.state == RuntimeState.READY and partial.cursor == 4
    ref = first.generation_artifacts.prepared(run.run_id)
    before = first.generation_artifacts.get(ref, GenerationPreparation)
    package = first.production_packages.get(before.source_package_ref)
    assert first.execution_references.mode(run.scope) == "image_to_video"
    second = load(fixture, path)
    assert second.runtime.store is not first.runtime.store
    assert second.ledger is not first.ledger
    assert (await second.runtime.recover_run(run.run_id)) == partial
    assert second.execution_references.mode(run.scope) == "image_to_video"
    assert second.production_packages.get(before.source_package_ref) == package
    def forbidden(*args, **kwargs):
        pytest.fail("Completed Assembler/Generator step was executed after restore")
    monkeypatch.setattr(second.shot_assembler, "assemble", forbidden)
    monkeypatch.setattr(second.prompt_compiler.generator, "generate", forbidden)
    done = await second.runtime.run(run.run_id)
    assert done.state == RuntimeState.SUCCEEDED
    assert done.last_result.artifact_refs == (before.final_prompt_ref, before.audio_plan_ref, ref)
    final = second.generation_artifacts.get(before.final_prompt_ref, FinalPromptArtifact)
    audio = second.generation_artifacts.get(before.audio_plan_ref, AudioExecutionPlan)
    assert final.source_package_ref == audio.source_package_ref == before.source_package_ref
    assert second.generation_artifacts.get(final.coverage_ref, PromptCoverage)
    irref = ArtifactReference(owner="prompt-ir", artifact_ref="prompt-ir:" + final.prompt_ir_fingerprint, version=1)
    assert second.generation_artifacts.get(irref, PromptIR)
    binding_ref = package.sources[-1].reference if package.sources[-1].domain == "REFERENCE" else next(
        s.reference for s in package.sources if s.domain == "REFERENCE" and s.reference.artifact_ref.startswith("execution-reference:"))
    resolved = second.execution_references.resolve(binding_ref)
    assert resolved["media"]["mediaId"] == binding.media.media_id
    assert resolved["media"]["contentHash"] == binding.media.content_hash
    third = load(fixture, path)
    assert (await third.runtime.recover_run(run.run_id)).state == RuntimeState.SUCCEEDED
    assert (await third.runtime.run(run.run_id)) == done
    assert third.generation_artifacts.get(before.final_prompt_ref, FinalPromptArtifact).fingerprint == final.fingerprint


@pytest.mark.asyncio
async def test_waiting_user_receipt_and_waiting_external_survive_new_store(tmp_path):
    ledger = ProductionLedger(tmp_path / "ledger.sqlite3")
    request = RuntimeAction(kind=ActionKind.REQUEST_USER_DECISION,
        decision=UserDecisionRequest(category=DecisionCategory.ART_APPROVAL, question="批准镜头方案？"))
    first = engine(ledger, (request,))
    run = first.create_run(work_id="work", mode=RunMode.EXPERIMENT,
        workflow_id="t6-offline:v1", run_id="user")
    waiting = await first.run(run.run_id)
    assert waiting.state == RuntimeState.WAITING_USER
    second = engine(ProductionLedger(ledger.path), (request,))
    assert (await second.recover_run(run.run_id)) == waiting
    decision_id = second.decision_id(run.run_id)
    assert decision_id == first.decision_id(run.run_id)
    receipt = UserDecisionRecord.seal(run_id=run.run_id, scope=run.scope,
        decision_id=decision_id, category=DecisionCategory.ART_APPROVAL, accepted=True)
    reviews = DurableReviewStore(second.store.ledger)
    decision_ref = reviews.put_user_decision(receipt)
    assert DurableReviewStore(ProductionLedger(ledger.path)).user_decision(decision_ref) == receipt
    await second.decide(run.run_id, decision_id=decision_id, accepted=True, decision_ref=decision_ref)
    assert (await second.run(run.run_id)).state == RuntimeState.SUCCEEDED

    dependency = ArtifactReference(owner="quality-review", artifact_ref="review:1", version=1)
    wait_action = RuntimeAction(kind=ActionKind.WAIT_EXTERNAL, external_ref=dependency)
    a = engine(ledger, (wait_action,))
    ext = a.create_run(work_id="work", mode=RunMode.EXPERIMENT,
        workflow_id="t6-offline:v1", run_id="external")
    original_wait = await a.run(ext.run_id)
    b = engine(ProductionLedger(ledger.path), (wait_action,))
    assert (await b.recover_run(ext.run_id)) == original_wait
    assert (await b.run(ext.run_id)).state == RuntimeState.WAITING_EXTERNAL
    await b.record_external_result(ext.run_id, external_ref=dependency,
        result=CapabilityResult(status=ResultStatus.SUCCEEDED))
    assert (await b.run(ext.run_id)).state == RuntimeState.SUCCEEDED


@pytest.mark.asyncio
async def test_formal_plugin_user_decision_writes_review_not_work(generation_fixture, tmp_path):
    data, _ = generation_fixture
    before = data.work.model_dump_json()
    path = tmp_path / "ledger.sqlite3"
    first = load(generation_fixture, path)
    finding = GateFinding.classified(GateCode.ART_APPROVAL_REQUIRED, owner="director",
        scope=RuntimeScope(work_id="work", scene_id="scene", shot_id="shot"),
        evidence_ref=ArtifactReference(owner="review-source", artifact_ref="approved-design", version=1))
    ref = first.gate_findings.put_finding(finding)
    run = first.create_governed_run(work_id="work", scene_id="scene", shot_id="shot",
        mode=RunMode.EXPERIMENT, run_id="reviewed", finding_refs=(ref,))
    waiting = await first.runtime.run(run.run_id)
    assert waiting.state == RuntimeState.WAITING_USER
    second = load(generation_fixture, path)
    restored = await second.runtime.recover_run(run.run_id)
    assert restored == waiting
    decision_id = second.runtime.decision_id(run.run_id)
    decided = await second.decide_target_run(run.run_id, decision_id=decision_id, accepted=True)
    assert decided.last_result.artifact_refs[0].owner == "user-decision"
    receipt = second.reviews.user_decision(decided.last_result.artifact_refs[0])
    assert receipt.decision_id == decision_id and receipt.accepted
    assert (await second.runtime.run(run.run_id)).state == RuntimeState.SUCCEEDED
    assert data.work.model_dump_json() == before


def test_unknown_artifact_type_and_arbitrary_body_rejected(tmp_path):
    ledger = ProductionLedger(tmp_path / "ledger.sqlite3")
    scope = RuntimeScope(work_id="work", scene_id="scene", shot_id="shot")
    ref = ArtifactReference(owner="anything", artifact_ref="anything:1", version=1)
    with pytest.raises(ValueError, match="Unregistered"):
        ledger.put_artifact("anything", ref, scope, "a" * 64, {"creativeCanon": "copy"})
    with pytest.raises(Exception):
        ledger.put_artifact("production-package", ArtifactReference(owner="production-package",
            artifact_ref="production-package:" + "a" * 64, version=1), scope, "a" * 64,
            {"creativeCanon": "copy"})
    with pytest.raises(ValueError, match="bounded flag"):
        ledger.put_index("generation-rebuild", "run", {"metadata": {"unbounded": True}}, scope=scope)


@pytest.mark.asyncio
async def test_durable_lock_and_cas_allow_only_one_process_style_advancer(tmp_path):
    ledger = ProductionLedger(tmp_path / "ledger.sqlite3")
    calls = []
    async def read(inputs):
        calls.append(inputs.operation_id)
        await asyncio.sleep(0.05)
        return CapabilityResult(status=ResultStatus.SUCCEEDED)
    action = RuntimeAction(kind=ActionKind.CALL_CAPABILITY, capability_key="local.read")
    workflow = RuntimeWorkflow(workflow_id="parallel:v1", steps=(action,))
    def make_engine():
        return RuntimeEngine(LegacyCapabilityBridge({"local.read": LegacyCapability(read, replay_safe=True)}),
            store=DurableRunStore(ProductionLedger(ledger.path)),
            workflows={workflow.workflow_id: workflow})
    first, second = make_engine(), make_engine()
    run = first.create_run(work_id="work", mode=RunMode.EXPERIMENT,
        workflow_id="parallel:v1", run_id="parallel")
    done = await asyncio.gather(first.run(run.run_id), second.run(run.run_id))
    assert all(item.state == RuntimeState.SUCCEEDED for item in done)
    assert calls == ["parallel:0"]
    with ledger.transaction() as db:
        operation = db.execute("SELECT dispatch_state,result_identity FROM production_operation").fetchone()
    assert operation["dispatch_state"] == "LOCAL_ONLY" and len(operation["result_identity"]) == 64


def test_reference_binding_versions_durable_current_and_immutable(bound_fixture, tmp_path):
    _, _, binding = bound_fixture
    ledger = ProductionLedger(tmp_path / "ledger.sqlite3")
    first = DurableReferenceExecutionStore(ledger)
    old = first.register(binding)
    assert DurableReferenceExecutionStore(ProductionLedger(ledger.path)).resolve(old)["media"]["mediaId"] == "unit-image"
    with pytest.raises(ValueError, match="Immutable"):
        first.register(binding.model_copy(update={"endpoint_state": "Different approved opening"}))
    revised = binding.model_copy(update={"version": 2, "endpoint_state": "Different approved opening"})
    new = DurableReferenceExecutionStore(ProductionLedger(ledger.path)).register(revised)
    assert new.version == 2 and new.fingerprint != old.fingerprint
    with pytest.raises(SourceReadError) as error:
        first.resolve(old)
    assert error.value.code == AssemblyIssueCode.VERSION_MISMATCH
    assert first.select(binding.scope)[0].version == 2
    assert first.ledger.get_artifact("reference-execution-binding", ArtifactReference(
        owner="professional", artifact_ref=old.artifact_ref, version=1))[2] == old.fingerprint


def test_missing_durable_reference_is_a_source_finding(bound_fixture, tmp_path):
    _, _, binding = bound_fixture
    store = DurableReferenceExecutionStore(ProductionLedger(tmp_path / "ledger.sqlite3"))
    with pytest.raises(SourceReadError) as error:
        store.resolve(binding.source().reference())
    assert error.value.code == AssemblyIssueCode.MISSING_REQUIRED_SOURCE


@pytest.mark.asyncio
async def test_artifact_storage_rejects_direct_cross_shot_write(generation_fixture, tmp_path):
    plugin = load(generation_fixture, tmp_path / "ledger.sqlite3")
    run = plugin.create_generation_run(work_id="work", scene_id="scene", shot_id="shot",
        mode=RunMode.EXPERIMENT, run_id="cross-shot-source")
    done = await plugin.runtime.run(run.run_id)
    artifact = plugin.generation_artifacts.get(done.last_result.artifact_refs[0], FinalPromptArtifact)
    with pytest.raises(ValueError, match="same-Shot"):
        plugin.ledger.put_artifact("final-prompt", artifact.artifact_reference(),
            RuntimeScope(work_id="work", scene_id="scene", shot_id="other-shot"),
            artifact.fingerprint, artifact)


@pytest.mark.asyncio
async def test_persistence_does_not_change_package_prompt_audio_or_binding_fingerprints(bound_fixture, tmp_path):
    fixture, memory_references, binding = bound_fixture
    data, directory = fixture
    memory = DramaPlugin.load(ROOT, mock_data=data, production_artifact_roots=(directory,),
        reference_execution_store=memory_references)
    durable = load(fixture, tmp_path / "ledger.sqlite3")
    durable_ref = durable.execution_references.register(binding)
    assert durable_ref == binding.source().reference()
    assert memory.execution_references.select(binding.scope)[0].reference() == durable_ref
    results = []
    for plugin, name in ((memory, "memory"), (durable, "durable")):
        run = plugin.create_generation_run(work_id="work", scene_id="scene", shot_id="shot",
            mode=RunMode.EXPERIMENT, run_id=name,
            task=GenerationTask(input_mode="image_to_video", native_audio="REQUIRED"))
        result = await plugin.runtime.run(run.run_id)
        assert result.state == RuntimeState.SUCCEEDED
        final_ref, audio_ref, prep_ref = result.last_result.artifact_refs
        prep = plugin.generation_artifacts.get(prep_ref, GenerationPreparation)
        package = plugin.production_packages.get(prep.source_package_ref)
        final = plugin.generation_artifacts.get(final_ref, FinalPromptArtifact)
        audio = plugin.generation_artifacts.get(audio_ref, AudioExecutionPlan)
        results.append((package.fingerprint, final.fingerprint, audio.fingerprint,
            durable_ref.fingerprint, prep.source_package_ref, final_ref, audio_ref))
    assert results[0] == results[1]


@pytest.mark.asyncio
async def test_identical_final_artifact_deduplicates_and_work_does_not_grow(generation_fixture, tmp_path):
    data, _ = generation_fixture
    path = tmp_path / "ledger.sqlite3"
    before = data.work.model_dump_json()
    plugin = load(generation_fixture, path)
    run = plugin.create_generation_run(work_id="work", scene_id="scene", shot_id="shot",
        mode=RunMode.EXPERIMENT, run_id="stress-source")
    completed = await plugin.runtime.run(run.run_id)
    assert completed.state == RuntimeState.SUCCEEDED
    finalref = completed.last_result.artifact_refs[0]
    final = plugin.generation_artifacts.get(finalref, FinalPromptArtifact)
    initial = plugin.ledger.counts()["immutable_artifact"]
    for _ in range(500):
        assert plugin.generation_artifacts.put(final) == finalref
    assert plugin.ledger.counts()["immutable_artifact"] == initial
    other = plugin.create_generation_run(work_id="work", scene_id="scene", shot_id="shot",
        mode=RunMode.EXPERIMENT, run_id="stress-other-run")
    second = await plugin.runtime.run(other.run_id)
    assert second.state == RuntimeState.SUCCEEDED
    assert second.last_result.artifact_refs[0] == finalref
    with plugin.ledger.transaction() as db:
        assert db.execute("SELECT count(*) FROM immutable_artifact WHERE artifact_type='final-prompt'").fetchone()[0] == 1
    assert data.work.model_dump_json() == before
    if evidence_file := os.environ.get("T6_DEDUP_EVIDENCE_FILE"):
        Path(evidence_file).write_text(json.dumps({
            "identicalFinalPromptWriteAttempts": 502,
            "finalPromptArtifactRows": 1,
            "distinctRunsReferencingSameFinalPrompt": 2,
            "sameReference": second.last_result.artifact_refs[0] == finalref,
            "workBytesBefore": len(before.encode()),
            "workBytesAfter": len(data.work.model_dump_json().encode()),
            "storageReductionVsNaiveCopies": "501/502 logical writes reused",
        }, ensure_ascii=False, indent=2) + "\n")


def test_real_s02_k02_three_independent_python_processes(tmp_path):
    script = ROOT / "integration/durable_persistence_shadow.py"
    database = tmp_path / "real-s02.sqlite3"
    outputs = [tmp_path / (name + ".json") for name in ("start", "resume", "terminal")]
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    for index, name in enumerate(("start", "resume", "terminal")):
        command = [sys.executable, str(script), name, "--ledger", str(database),
            "--output", str(outputs[index]), "--run-id", "t6-real-s02"]
        if index:
            command.extend(("--prior", str(outputs[index-1])))
        subprocess.run(command, cwd=ROOT, env=environment, capture_output=True,
            text=True, check=True, timeout=60)
    results = [json.loads(path.read_text()) for path in outputs]
    assert [r["state"] for r in results] == ["READY", "SUCCEEDED", "SUCCEEDED"]
    assert results[0]["refs"] == results[1]["refs"] == results[2]["refs"]
    assert results[0]["fingerprints"] == results[1]["fingerprints"] == results[2]["fingerprints"]
    assert results[0]["calls"] == {"assembler": 1, "generator": 1}
    assert all(r["calls"] == {"assembler": 0, "generator": 0} for r in results[1:])
    assert all(r["workBytesBefore"] == r["workBytesAfter"] for r in results)
    assert all(r["inputMode"] == "image_to_video" and r["readiness"] == "READY_FOR_PROVIDER"
        and not r["providerSubmissionAllowed"] for r in results)
    assert all(r["providerSubmission"] == r["paidCalls"] == r["mediaGeneration"] == 0
        for r in results)


@pytest.mark.parametrize("scenario", ("package", "prompt"))
def test_auto_maintenance_pending_cross_process(generation_fixture, tmp_path, scenario):
    data, designs = generation_fixture
    fixture = tmp_path / "source.json"
    fixture.write_text(json.dumps({key: dump_contract(getattr(data, key)) for key in
        ("work", "script", "episode", "scene", "shot")}, ensure_ascii=False) + "\n")
    script = ROOT / "integration/durable_recovery_cases.py"
    database = tmp_path / "auto.sqlite3"
    outputs = [tmp_path / "before.json", tmp_path / "after.json"]
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    for index, phase in enumerate(("start", "resume")):
        command = [sys.executable, str(script), scenario, phase, "--ledger", str(database),
            "--output", str(outputs[index]), "--fixture", str(fixture), "--designs", str(designs)]
        if index:
            command.extend(("--prior", str(outputs[0])))
        subprocess.run(command, cwd=ROOT, env=environment, capture_output=True,
            text=True, check=True, timeout=60)
    first, second = (json.loads(path.read_text()) for path in outputs)
    assert first["gateEffect"] == second["gateEffectBeforeResume"] == "AUTO_MAINTAIN"
    assert second["state"] == "SUCCEEDED" and not second["userDecisionRequested"]
    assert second["generatorCalls"] == 1 and second["providerSubmission"] == 0
    assert second["assemblerCalls"] == (1 if scenario == "package" else 0)


@pytest.mark.parametrize("scenario", ("user", "external"))
def test_wait_identity_cross_process(tmp_path, scenario):
    script = ROOT / "integration/durable_recovery_cases.py"
    database = tmp_path / "wait.sqlite3"
    outputs = [tmp_path / "wait.json", tmp_path / "resolved.json"]
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    for index, phase in enumerate(("start", "resume")):
        command = [sys.executable, str(script), scenario, phase, "--ledger", str(database),
            "--output", str(outputs[index])]
        if index:
            command.extend(("--prior", str(outputs[0])))
        subprocess.run(command, cwd=ROOT, env=environment, capture_output=True,
            text=True, check=True, timeout=60)
    first, second = (json.loads(path.read_text()) for path in outputs)
    assert first["state"] == ("WAITING_USER" if scenario == "user" else "WAITING_EXTERNAL")
    assert second["state"] == "SUCCEEDED" and second["sameWaitIdentity"]
    assert bool(second["reviewRef"]) == (scenario == "user")


@pytest.mark.asyncio
async def test_1000_checkpoints_500_prompts_many_findings_leave_work_constant(generation_fixture, tmp_path):
    data, _ = generation_fixture
    work_before = len(data.work.model_dump_json().encode())
    plugin = load(generation_fixture, tmp_path / "pressure.sqlite3")
    seed = plugin.create_generation_run(work_id="work", scene_id="scene", shot_id="shot",
        mode=RunMode.EXPERIMENT, run_id="pressure-seed")
    done = await plugin.runtime.run(seed.run_id)
    final = plugin.generation_artifacts.get(done.last_result.artifact_refs[0], FinalPromptArtifact)
    with plugin.ledger.transaction() as db:
        finding_before = db.execute("SELECT count(*) FROM immutable_artifact WHERE artifact_type='gate-finding'").fetchone()[0]
    checkpoint = plugin.runtime.create_run(work_id="work", scene_id="scene", shot_id="shot",
        mode=RunMode.EXPERIMENT, workflow_id="prepare-generation:v1", run_id="pressure-checkpoint")
    for _ in range(1000):
        checkpoint = plugin.runtime.store.save(checkpoint.model_copy(update={
            "revision": checkpoint.revision + 1}), expected_revision=checkpoint.revision)
    for index in range(500):
        candidate = FinalPromptArtifact.seal(**{**final.model_dump(exclude={"fingerprint"}),
            "prompt_text": final.prompt_text + f"\n执行变体 {index}"})
        plugin.generation_artifacts.put(candidate)
        plugin.gate_findings.put_finding(GateFinding.classified(
            GateCode.QUALITY_COVERAGE_RISK, owner="quality-review",
            scope=seed.scope, evidence_ref=ArtifactReference(owner="review-evidence",
                artifact_ref=f"finding-{index}", version=1)))
    with plugin.ledger.transaction() as db:
        checkpoint_bytes = db.execute("SELECT length(CAST(checkpoint_json AS BLOB)) FROM production_run WHERE run_id=?",
            (checkpoint.run_id,)).fetchone()[0]
        count = db.execute("SELECT count(*) FROM immutable_artifact WHERE artifact_type='final-prompt'").fetchone()[0]
        findings = db.execute("SELECT count(*) FROM immutable_artifact WHERE artifact_type='gate-finding'").fetchone()[0]
    assert checkpoint.revision == 1000 and checkpoint_bytes < 4096
    assert count == 501 and findings == finding_before + 500
    work_after = len(data.work.model_dump_json().encode())
    assert work_after == work_before
    if evidence_file := os.environ.get("T6_PRESSURE_EVIDENCE_FILE"):
        Path(evidence_file).write_text(json.dumps({
            "checkpoints": 1000, "distinctAdditionalFinalPrompts": 500,
            "additionalGateFindings": 500, "checkpointBytes": checkpoint_bytes,
            "workBytesBefore": work_before, "workBytesAfter": work_after,
            "finalPromptArtifactRows": count, "gateFindingArtifactRows": findings,
            "ledgerCounts": plugin.ledger.counts(),
        }, ensure_ascii=False, indent=2) + "\n")
