"""T5 offline authority, real consumers, governance, overlap, size and recovery."""
from __future__ import annotations

import ast
from dataclasses import replace
import inspect
import json
from pathlib import Path
import socket

import pytest
from pydantic import ValidationError

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.generation.audio import AudioPerformanceAssembler
from drama_plugin.generation.checks import execution_findings
from drama_plugin.generation.contracts import (
    AudioExecutionPlan, CoverageEntry, CoverageStatus, ExecutionDiagnostic, FinalPromptArtifact, GenerationPreparation,
    GenerationTask, Intelligibility, PromptCoverage, PromptIR, SpeechLayer, TemporalRelation,
)
from drama_plugin.generation.seedance import ExactPromptTransfer
from drama_plugin.governance.contracts import GateCategory, GateEffect, HardStopFamily
from drama_plugin.production.contracts import PackageContent, ProductionPackage, SourceDomain
from drama_plugin.runtime import ArtifactReference, RunMode, RuntimeState

from test_production_package import fixture

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("T5 forbids network, media/paid calls and legacy Prompt projection")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr("drama_plugin.plugin.load_config", lambda _: DramaPluginConfig())
    monkeypatch.setattr("drama_plugin.professional.compile_prompt_projection", forbidden)
    monkeypatch.setattr("drama_plugin.hosts.cinematic_projection.project", forbidden)
    monkeypatch.setattr("drama_plugin.visual.video_prompt.compile_request_ir", forbidden)


def change_bible(fixture, department, records=None, update=None):
    data, directory = fixture
    file = directory / (department + ".json")
    body = json.loads(file.read_text()) if file.exists() else json.loads((directory / "cinematography.json").read_text())
    if not file.exists():
        body.update(id="t5-" + department, type=department, createdByCapability=department)
        body["content"] = []
    if records is not None:
        body["content"] = [{"id": identity, "scopeRefs": ["scene"], "values": values,
            "provenance": "NEW_PROFESSIONAL_ELABORATION", "sourceRefs": body["sourceRefs"]}
            for identity, values in records]
    if update is not None:
        update(body)
    file.write_text(json.dumps(body))
    data.shot.content["departmentRefs"][department] = {"key": "bible:" + body["id"], "kind": "DESIGN",
        "fingerprint": sha256_canonical(body)}
    return body


@pytest.fixture
def generation_fixture(fixture):
    data, _ = fixture
    data.shot.content["plannedDurationMs"] = 6000
    data.shot.content["spokenContentBindings"] = [{"spokenContentId": "L1", "coverageIntent": "ON_SCREEN_SPEAKER"}]
    data.scene.content["spokenContent"] = [{"id": "L1", "kind": "DIALOGUE", "speakerKey": "A",
        "text": "机制测试的精确正文。", "language": "中文", "mustKeep": True}]
    change_bible(fixture, "shot-design", [("K01", {"shot_ref": "K01", "purpose": "Observe", "subjects": ["A", "B"]})])
    change_bible(fixture, "cinematography", [("CAM-01", {"perspective": "双人同侧可见", "camera_movement": "固定"})])
    change_bible(fixture, "environment-design", [("room", {"location_identity": "测试房间，桌子和门保持原位", "topology": "桌侧通向门"})])
    change_bible(fixture, "character-art", [("A", {"character_ref": "A", "face_structure": "已批准的测试主体A面部"}),
                                            ("B", {"character_ref": "B", "face_structure": "已批准的测试主体B面部"})])
    change_bible(fixture, "dialogue-design", [("L1", {"line_id": "L1", "dialogue_text": "机制测试的精确正文。", "speaker": "A"})])
    return fixture


def load(fixture, **kwargs):
    return DramaPlugin.load(ROOT, mock_data=fixture[0], legacy_reads=True, production_artifact_roots=(fixture[1],), **kwargs)


async def prepare(plugin, *, mode=RunMode.EXPERIMENT, run_id="t5", **kwargs):
    run = plugin.create_generation_run(work_id="work", scene_id="scene", shot_id="shot", mode=mode, run_id=run_id, **kwargs)
    return await plugin.runtime.run(run.run_id)


def artifacts(plugin, run):
    final, audio, ready = run.last_result.artifact_refs
    return (plugin.generation_artifacts.get(final, FinalPromptArtifact),
            plugin.generation_artifacts.get(audio, AudioExecutionPlan),
            plugin.generation_artifacts.get(ready, GenerationPreparation))


@pytest.mark.parametrize("mode", list(RunMode))
async def test_plugin_owns_package_only_e2e_and_no_creative_mutation(generation_fixture, monkeypatch, mode):
    plugin = load(generation_fixture)
    before = [dump_contract(getattr(generation_fixture[0], name)) for name in ("work", "scene", "shot")]
    def forbidden(*args, **kwargs):
        pytest.fail("Provider must not be invoked")
    monkeypatch.setattr(plugin.providers.production, "generate_video", forbidden)
    monkeypatch.setattr(plugin.providers.production, "generate_image", forbidden)
    calls = []
    original = plugin.runtime.executor.execute
    async def execute(key, inputs):
        calls.append(key)
        return await original(key, inputs)
    monkeypatch.setattr(plugin.runtime.executor, "execute", execute)
    run = await prepare(plugin, mode=mode)
    assert run.state == RuntimeState.SUCCEEDED
    final, audio, ready = artifacts(plugin, run)
    assert ready.readiness == "READY_FOR_PROVIDER" and ready.provider_submission_allowed is False
    assert final.source_package_ref == audio.source_package_ref == ready.source_package_ref
    assert calls.count("generation.compile:v1") == 1
    assert "generation.ready:v1" in calls and all(not k.startswith("legacy.") for k in calls)
    assert before == [dump_contract(getattr(generation_fixture[0], name)) for name in ("work", "scene", "shot")]
    assert "机制测试的精确正文。" in final.prompt_text
    assert "机制测试的精确正文。" not in audio.model_dump_json()
    assert "approvedSceneText" not in plugin.runtime.serialize(run.run_id)


async def test_single_generator_deterministic_final_and_exact_transfer(generation_fixture, monkeypatch):
    plugin = load(generation_fixture)
    count = 0
    original = plugin.prompt_compiler.generator.generate
    def generate(*args, **kwargs):
        nonlocal count
        count += 1
        return original(*args, **kwargs)
    monkeypatch.setattr(plugin.prompt_compiler.generator, "generate", generate)
    first = await prepare(plugin)
    second = await prepare(plugin, run_id="second")
    assert first.last_result.artifact_refs == second.last_result.artifact_refs
    assert count == 1
    final, _, _ = artifacts(plugin, first)
    assert ExactPromptTransfer.prompt(final) == final.prompt_text
    assert FinalPromptArtifact.model_validate_json(final.model_dump_json()) == final


async def test_immutable_extra_rejection_and_no_full_source_body(generation_fixture):
    plugin = load(generation_fixture)
    run = await prepare(plugin)
    final, plan, _ = artifacts(plugin, run)
    for item in (final, plan):
        with pytest.raises(ValidationError):
            item.fingerprint = "a" * 64
        with pytest.raises(ValidationError):
            type(item).model_validate({**item.model_dump(), "extras": {"full_bible": "no"}})
    with pytest.raises(ValidationError):
        FinalPromptArtifact.model_validate({**final.model_dump(), "prompt_text": "overwritten"})
    assert "CANON TEXT MUST NEVER" not in final.prompt_text
    for field in ("research_notes", "productionHistory", "approvedSceneText", "full_package"):
        assert field not in final.model_dump_json() + plan.model_dump_json()


async def test_consumer_does_not_rediscover_departments_or_read_history(generation_fixture, monkeypatch):
    plugin = load(generation_fixture)
    run = await prepare(plugin)
    ref = artifacts(plugin, run)[0].source_package_ref
    def forbidden(*a, **k):
        pytest.fail("Consumers may only resolve Package refs")
    monkeypatch.setattr(plugin.professional_design, "resolve", forbidden)
    monkeypatch.setattr(plugin.shot_assembler, "assemble", forbidden)
    monkeypatch.setattr(plugin.prompt_compiler.reader.resolver, "scope_sources", forbidden)
    seen = []
    original = plugin.prompt_compiler.reader.resolver.resolve
    async def resolve(source):
        seen.append(source)
        assert source.path and source.path[-1] != "approvedSceneText"
        return await original(source)
    monkeypatch.setattr(plugin.prompt_compiler.reader.resolver, "resolve", resolve)
    result = await plugin.prompt_compiler.compile(ref)
    assert result.preparation_ref is not None and seen
    allowed = {s.reference for s in plugin.production_packages.get(ref).sources}
    allowed.update(plugin.production_packages.get(ref).obligations)
    assert set(seen) <= allowed


@pytest.mark.parametrize("case", ["irrelevant_1000", "research_notes", "legacy_history", "unselected_generator"])
async def test_complexity_and_information_budget(generation_fixture, monkeypatch, case):
    plugin = load(generation_fixture)
    first = await prepare(plugin)
    final, plan, _ = artifacts(plugin, first)
    if case == "irrelevant_1000":
        body = json.loads((generation_fixture[1] / "cinematography.json").read_text())
        body["sceneRefs"] = ["unrelated-scene"]
        body["content"][0]["scopeRefs"] = ["unrelated-scene"]
        for i in range(1000):
            body["id"] = f"unrelated-{i}"
            (generation_fixture[1] / f"unrelated-{i}.json").write_text(json.dumps(body))
    elif case == "research_notes":
        change_bible(generation_fixture, "cinematography", update=lambda body: body["content"][0]["values"].update(
            research_notes="LARGE UNUSED RESEARCH" * 20000))
    elif case == "legacy_history":
        generation_fixture[0].work.content["promptHistory"] = ["HISTORY NEVER SENT" * 10000] * 20
    else:
        from importlib import import_module
        module = import_module("drama_plugin.prompt_generators.registry")
        monkeypatch.setattr(module, "RESERVED", (*module.RESERVED, "unselected_new_generator"))
        from drama_plugin.generation import seedance
        original = seedance.get_generator
        class UnselectedGenerator:
            family, version, supported_modes = "unselected_new_generator", "1", ("text_to_video",)
            def generate(self, *args, **kwargs):
                pytest.fail("The unselected generator must never execute")
        monkeypatch.setattr(seedance, "get_generator", lambda family: UnselectedGenerator()
            if family == "unselected_new_generator" else original(family))
    second = await prepare(plugin, run_id="complexity-second")
    new_final, new_plan, _ = artifacts(plugin, second)
    assert new_final.prompt_text == final.prompt_text
    assert len(new_plan.model_dump_json()) == len(plan.model_dump_json())
    assert len(new_final.model_dump_json()) == len(final.model_dump_json())
    if case in {"irrelevant_1000", "unselected_generator"}:
        assert first.last_result.artifact_refs == second.last_result.artifact_refs


async def test_warning_continues_and_required_overflow_hs4(generation_fixture, monkeypatch):
    plugin = load(generation_fixture)
    run = await prepare(plugin)
    decision = plugin.gate_findings.decision(plugin.gate_findings.latest(run.run_id))
    assert decision.effect == GateEffect.CONTINUE
    assert any(plugin.gate_findings.finding(ref).category == GateCategory.WARNING for ref in decision.finding_refs)
    policy = plugin.prompt_compiler.catalog.policy("seedance-2-standard")
    monkeypatch.setattr(plugin.prompt_compiler.catalog, "policy", lambda _: replace(policy, hard_limit=20, fingerprint="b" * 64))
    failed = await prepare(plugin, run_id="overflow")
    assert failed.state == RuntimeState.FAILED
    decision = plugin.gate_findings.decision(plugin.gate_findings.latest(failed.run_id))
    assert decision.risk_families == (HardStopFamily.HS4,)


async def test_optional_budget_omitted_warning_not_hard_stop(generation_fixture, monkeypatch):
    change_bible(generation_fixture, "color-design", [("palette", {"scene_palettes": "可选颜色细节" * 200})])
    plugin = load(generation_fixture)
    policy = plugin.prompt_compiler.catalog.policy("seedance-2-standard")
    monkeypatch.setattr(plugin.prompt_compiler.catalog, "policy", lambda _: replace(policy, hard_limit=900, fingerprint="c" * 64))
    run = await prepare(plugin)
    assert run.state == RuntimeState.SUCCEEDED
    final, _, _ = artifacts(plugin, run)
    coverage = plugin.generation_artifacts.get(final.coverage_ref, PromptCoverage)
    assert any(e.status == CoverageStatus.OPTIONAL_OMITTED for e in coverage.entries)
    assert all(e.status != CoverageStatus.UNRESOLVED for e in coverage.entries if e.obligation == "EXECUTION_REQUIRED")


async def test_generator_absent_and_required_tts_are_capability_absent(generation_fixture):
    plugin = load(generation_fixture)
    for identity, task in (("unknown-generator", GenerationTask(target_model="vidu-reference-to-video")),
                           ("tts-required", GenerationTask(tts_required=True))):
        run = await prepare(plugin, run_id=identity, task=task)
        assert run.state == RuntimeState.FAILED
        decision = plugin.gate_findings.decision(plugin.gate_findings.latest(run.run_id))
        assert decision.effect == GateEffect.CAPABILITY_ABSENT and not decision.risk_families


async def test_missing_required_and_dialogue_mismatch(generation_fixture):
    data = generation_fixture[0]
    change_bible(generation_fixture, "dialogue-design", [("L1", {"line_id": "L1", "dialogue_text": "禁止改写", "speaker": "A"})])
    plugin = load(generation_fixture)
    run = await prepare(plugin)
    assert run.state == RuntimeState.FAILED
    decision = plugin.gate_findings.decision(plugin.gate_findings.latest(run.run_id))
    assert decision.risk_families == (HardStopFamily.HS1,)
    assert data.scene.content["spokenContent"][0]["text"] == "机制测试的精确正文。"


async def test_wrong_package_scope_hs1(generation_fixture):
    plugin = load(generation_fixture)
    good = await prepare(plugin)
    package_ref = artifacts(plugin, good)[0].source_package_ref
    run = plugin.create_generation_run(work_id="work", scene_id="scene", shot_id="other-shot",
        mode=RunMode.EXPERIMENT, run_id="wrong-shot", package_ref=package_ref)
    run = await plugin.runtime.run(run.run_id)
    assert run.state == RuntimeState.FAILED
    decision = plugin.gate_findings.decision(plugin.gate_findings.latest(run.run_id))
    assert decision.risk_families == (HardStopFamily.HS1,)


async def test_stale_prompt_auto_rebuild_not_user_approval(generation_fixture, monkeypatch):
    plugin = load(generation_fixture)
    first = await prepare(plugin)
    old = first.last_result.artifact_refs[-1]
    policy = plugin.prompt_compiler.catalog.policy("seedance-2-standard")
    monkeypatch.setattr(plugin.prompt_compiler.catalog, "policy", lambda _: replace(policy, version="test-v2", fingerprint="d" * 64))
    second = await prepare(plugin, run_id="rebuild", cached_preparation_ref=old)
    assert second.state == RuntimeState.SUCCEEDED
    assert second.last_result.artifact_refs[0] != first.last_result.artifact_refs[0]
    assert "rebuild" in plugin.generation_artifacts._maintenance
    assert second.wait_reason is None


async def test_stale_package_auto_reassembly_then_compile(generation_fixture):
    plugin = load(generation_fixture)
    first = await prepare(plugin)
    old = artifacts(plugin, first)[0].source_package_ref
    generation_fixture[0].shot.content["subjectAction"] = "合法作者修订后的当前动作"
    second = await prepare(plugin, run_id="package-stale", package_ref=old)
    assert second.state == RuntimeState.SUCCEEDED
    final, _, _ = artifacts(plugin, second)
    assert final.source_package_ref != old
    assert "合法作者修订后的当前动作" in final.prompt_text
    assert plugin.gate_findings.maintenance_count(second.run_id) == 1


async def test_recovery_after_compilation_does_not_repeat_assembler_or_generator(generation_fixture, monkeypatch):
    plugin = load(generation_fixture)
    run = plugin.create_generation_run(work_id="work", scene_id="scene", shot_id="shot", mode=RunMode.EXPERIMENT)
    current = await plugin.runtime.run(run.run_id, max_ticks=5)
    assert current.cursor == 4
    snapshot = plugin.runtime.serialize(run.run_id)
    restored = load(generation_fixture, production_package_store=plugin.production_packages,
        gate_finding_store=plugin.gate_findings, generation_artifact_store=plugin.generation_artifacts)
    restored.runtime.restore(snapshot)
    def forbidden(*a, **k):
        pytest.fail("Completed assembly/compilation cannot replay")
    monkeypatch.setattr(restored.shot_assembler, "assemble", forbidden)
    monkeypatch.setattr(restored.prompt_compiler.generator, "generate", forbidden)
    final = await restored.runtime.run(run.run_id)
    assert final.state == RuntimeState.SUCCEEDED
    expected = plugin.generation_artifacts.get(plugin.generation_artifacts.prepared(run.run_id), GenerationPreparation)
    assert final.last_result.artifact_refs[:2] == (expected.final_prompt_ref, expected.audio_plan_ref)


def parallel_fixture(fixture):
    """MECHANISM_FIXTURE_ONLY: these lines/layers are not the flagship S01 artwork."""
    data, _ = fixture
    data.scene.content["spokenContent"] = [{"id": key, "kind": "DIALOGUE", "speakerKey": speaker,
        "text": text, "language": "中文", "mustKeep": True} for key, speaker, text in (
            ("P1", "A", "机制主对白A"), ("S1", "B", "机制次对白B"), ("P2", "A", "机制插话A"))]
    data.shot.content["spokenContentBindings"] = [{"spokenContentId": line["id"], "coverageIntent": "ON_SCREEN_SPEAKER"}
                                               for line in data.scene.content["spokenContent"]]
    change_bible(fixture, "dialogue-design", [(line["id"], {"line_id": line["id"], "dialogue_text": line["text"], "speaker": line["speakerKey"]})
                                            for line in data.scene.content["spokenContent"]])
    events = [dict(event_id=identity, spoken_content_id=identity, speaker_key=speaker, layer=layer,
        intelligibility=priority, mix_priority=mix, window_ms=window) for identity, speaker, layer, priority, mix, window in (
            ("P1", "A", "PRIMARY", "MUST_UNDERSTAND", 3, [0, 2500]),
            ("S1", "B", "SECONDARY", "BRIEFLY_CLEAR", 2, [1000, 3500]),
            ("P2", "A", "PRIMARY", "MUST_UNDERSTAND", 3, [2500, 4000]))]
    events.append(dict(event_id="BG", texture_obligation="机制背景交谈声，不新增明确台词", layer="BACKGROUND",
                       intelligibility="BRIEFLY_CLEAR", mix_priority=1, window_ms=[0, 5000]))
    relations = [dict(event_id=a, target_event_id=b, relation=kind) for a, b, kind in (
        ("S1", "P1", "OVERLAP"), ("BG", "P1", "CONTINUE_UNDER"), ("P2", "S1", "INTERRUPT"),
        ("BG", "P2", "FADE_BEHIND"), ("P1", "P2", "BEFORE"), ("P2", "P1", "AFTER"))]
    change_bible(fixture, "sound-design", [("audio", {"audio_events": events, "audio_relations": relations,
        "ambience": "机制房间底声", "foreground_background_relationship": "机制主声优先，次声可短暂清楚"})])
    return fixture


async def test_parallel_audio_layers_relations_and_no_dialogue_copy(generation_fixture):
    fixture = parallel_fixture(generation_fixture)
    plugin = load(fixture)
    run = await prepare(plugin)
    assert run.state == RuntimeState.SUCCEEDED
    _, audio, _ = artifacts(plugin, run)
    assert {e.layer for e in audio.speech_events} == set(SpeechLayer)
    assert {r.relation for r in audio.relations} == set(TemporalRelation)
    assert audio.speech_events[-1].layer == SpeechLayer.BACKGROUND
    assert audio.speech_events[-1].intelligibility == Intelligibility.BRIEFLY_CLEAR
    assert audio.native_audio_is_final_mix is False
    for line in fixture[0].scene.content["spokenContent"]:
        assert line["text"] not in audio.model_dump_json()


async def test_many_lines_without_authored_relations_return_owner(generation_fixture):
    data = generation_fixture[0]
    data.scene.content["spokenContent"].append({"id": "L2", "kind": "DIALOGUE", "speakerKey": "B",
        "text": "另一个测试句", "language": "中文", "mustKeep": True})
    data.shot.content["spokenContentBindings"].append({"spokenContentId": "L2", "coverageIntent": "ON_SCREEN_SPEAKER"})
    plugin = load(generation_fixture)
    run = await prepare(plugin)
    assert run.state == RuntimeState.FAILED
    decision = plugin.gate_findings.decision(plugin.gate_findings.latest(run.run_id))
    diagnostics = plugin.generation_artifacts.diagnostics(plugin.gate_findings.finding(decision.finding_refs[0]).evidence_ref)
    assert any(d.code == "CREATIVE_SOURCE_INSUFFICIENT" and d.owner == "screenplay-dialogue" for d in diagnostics)


@pytest.mark.parametrize("invalid", ["dangling", "duplicate", "window", "unauthorized_interrupt", "cycle",
    "order_overlap", "interrupt_before_target", "wrong_canonical_interruption"])
async def test_audio_relation_contract_rejects_invalid_execution(generation_fixture, invalid):
    plugin = load(parallel_fixture(generation_fixture))
    run = await prepare(plugin)
    _, plan, _ = artifacts(plugin, run)
    values = plan.model_dump(exclude={"fingerprint"})
    if invalid == "dangling":
        values["relations"][0]["target_event_id"] = "unknown"
    elif invalid == "duplicate":
        values["relations"] = (*values["relations"], values["relations"][0])
    elif invalid == "window":
        values["speech_events"][0]["window_ms"] = (5100, 5500)
    elif invalid == "unauthorized_interrupt":
        values["relations"][2]["ends_target_speech"] = True
    elif invalid == "cycle":
        values["relations"] = (*values["relations"], {**values["relations"][4], "event_id": "P2", "target_event_id": "P1"})
    elif invalid == "order_overlap":
        values["speech_events"] = [{**e, "window_ms": None} for e in values["speech_events"]]
        values["relations"] = (*values["relations"], {**values["relations"][4], "relation": "OVERLAP"})
    elif invalid == "interrupt_before_target":
        values["speech_events"][2]["window_ms"] = (0, 1500)
        values["relations"] = (values["relations"][2],)
    else:
        values["relations"][2].update(ends_target_speech=True, interruption_ref=plan.speech_events[0].source_ref)
    with pytest.raises(ValidationError):
        AudioExecutionPlan.seal(**values)


async def test_interruption_reference_preserves_selected_canonical_identity(generation_fixture):
    plugin = load(parallel_fixture(generation_fixture))
    _, plan, _ = artifacts(plugin, await prepare(plugin))
    values = plan.model_dump(exclude={"fingerprint"})
    values["relations"][2].update(ends_target_speech=True, interruption_ref=plan.speech_events[1].source_ref)
    variant = AudioExecutionPlan.seal(**values)
    assert variant.speech_events == plan.speech_events
    assert variant.relations[2].interruption_ref == plan.speech_events[1].source_ref
    assert "机制次对白B" not in variant.model_dump_json()


async def test_native_audio_optional_and_disabled_video_only(generation_fixture):
    plugin = load(generation_fixture)
    run = await prepare(plugin, task=GenerationTask(native_audio="DISABLED"))
    assert run.state == RuntimeState.SUCCEEDED
    final, audio, _ = artifacts(plugin, run)
    assert "机制测试的精确正文。" not in final.prompt_text
    assert audio.speech_events and audio.native_audio_policy == "DISABLED"


async def test_optional_native_audio_unsupported_is_warning(generation_fixture, monkeypatch):
    plugin = load(generation_fixture)
    policy = plugin.prompt_compiler.catalog.policy("seedance-2-standard")
    monkeypatch.setattr(plugin.prompt_compiler.catalog, "policy", lambda _: replace(policy, native_audio=False, fingerprint="e" * 64))
    run = await prepare(plugin)
    assert run.state == RuntimeState.SUCCEEDED
    final, _, _ = artifacts(plugin, run)
    assert "机制测试的精确正文。" not in final.prompt_text
    required = await prepare(plugin, run_id="native-required", task=GenerationTask(native_audio="REQUIRED"))
    assert required.state == RuntimeState.FAILED


async def test_final_boundary_stale_package_repairs_internally(generation_fixture):
    plugin = load(generation_fixture)
    run = plugin.create_generation_run(work_id="work", scene_id="scene", shot_id="shot", mode=RunMode.EXPERIMENT)
    checkpoint = await plugin.runtime.run(run.run_id, max_ticks=7)
    assert checkpoint.cursor == 6
    generation_fixture[0].shot.content["subjectAction"] = "合法作者在发送前修订动作"
    completed = await plugin.runtime.run(run.run_id)
    assert completed.state == RuntimeState.SUCCEEDED
    assert "合法作者在发送前修订动作" in artifacts(plugin, completed)[0].prompt_text


async def test_seal_rejects_extra_fields(generation_fixture):
    plugin = load(generation_fixture)
    _, plan, _ = artifacts(plugin, await prepare(plugin))
    with pytest.raises(ValidationError):
        AudioExecutionPlan.seal(**plan.model_dump(exclude={"fingerprint"}), extras={"unbounded": True})


@pytest.mark.parametrize("invalid", ["wrong_package_owner", "wrong_final_owner", "empty_span", "text_without_span", "reference_without_input",
    "wrong_speech_scene", "scene_wide_ir"])
async def test_artifact_links_and_coverage_cannot_claim_false_authority(generation_fixture, invalid):
    plugin = load(generation_fixture)
    final, plan, ready = artifacts(plugin, await prepare(plugin))
    with pytest.raises(ValidationError):
        if invalid == "wrong_package_owner":
            AudioExecutionPlan.seal(**{**plan.model_dump(exclude={"fingerprint"}),
                "source_package_ref": ArtifactReference(owner="scene", artifact_ref="scene")})
        elif invalid == "wrong_final_owner":
            GenerationPreparation.seal(**{**ready.model_dump(exclude={"fingerprint"}),
                "final_prompt_ref": ArtifactReference(owner="legacy-prompt", artifact_ref="old")})
        elif invalid == "wrong_speech_scene":
            values = plan.model_dump(exclude={"fingerprint"})
            values["speech_events"][0]["source_ref"]["artifact_ref"] = "other-scene"
            AudioExecutionPlan.seal(**values)
        elif invalid == "scene_wide_ir":
            ir = plugin.generation_artifacts.get(ArtifactReference(owner="prompt-ir", artifact_ref="prompt-ir:" + final.prompt_ir_fingerprint, version=1), PromptIR)
            values = ir.model_dump(exclude={"fingerprint"})
            values["scope"]["shot_id"] = None
            PromptIR.seal(**values)
        else:
            coverage = plugin.generation_artifacts.get(final.coverage_ref, PromptCoverage)
            values = next(e for e in coverage.entries if e.status == CoverageStatus.TEXT_COVERED).model_dump()
            if invalid == "empty_span":
                values["span"] = (2, 2)
            elif invalid == "text_without_span":
                values["span"] = None
            else:
                values.update(status=CoverageStatus.REFERENCE_COVERED, span=None, input_ref=None)
            CoverageEntry.model_validate(values)


async def test_missing_required_camera_returns_owner_and_hs4(generation_fixture):
    change_bible(generation_fixture, "cinematography", [("CAM-01", {"perspective": "双人同侧可见"})])
    plugin = load(generation_fixture)
    run = await prepare(plugin)
    assert run.state == RuntimeState.FAILED
    decision = plugin.gate_findings.decision(plugin.gate_findings.latest(run.run_id))
    assert decision.risk_families == (HardStopFamily.HS4,)
    diagnostics = [d for ref in decision.finding_refs for d in plugin.generation_artifacts.diagnostics(
        plugin.gate_findings.finding(ref).evidence_ref)]
    assert any(d.owner == "camera" and d.code == "EXECUTION_REQUIRED_MISSING" for d in diagnostics)


async def test_design_pin_is_not_a_media_reference(generation_fixture):
    plugin = load(generation_fixture)
    run = await prepare(plugin, task=GenerationTask(input_mode="reference"))
    assert run.state == RuntimeState.FAILED
    decision = plugin.gate_findings.decision(plugin.gate_findings.latest(run.run_id))
    assert decision.risk_families == (HardStopFamily.HS4,)
    with pytest.raises(KeyError):
        plugin.generation_artifacts.prepared(run.run_id)


@pytest.mark.parametrize("code,category,family", [
    ("PROMPT_STALE", "AUTO_MAINTENANCE", None), ("OPTIONAL_COVERAGE", "WARNING", None),
    ("EXECUTION_REQUIRED_MISSING", "HARD_STOP", "HS4"), ("GENERATOR_ABSENT", "CAPABILITY_ABSENT", None),
    ("SCOPE_MISMATCH", "HARD_STOP", "HS1"), ("OPTIONAL_AMBIENCE_MISSING", "WARNING", None),
    ("DIALOGUE_IDENTITY_MISMATCH", "HARD_STOP", "HS1"), ("TTS_CAPABILITY_ABSENT", "CAPABILITY_ABSENT", None),
])
def test_t5_findings_belong_to_t3(code, category, family):
    from drama_plugin.runtime.contracts import RuntimeScope
    result = execution_findings((ExecutionDiagnostic(code=code, owner="test-owner", domain=SourceDomain.SOUND),),
        scope=RuntimeScope(work_id="work", scene_id="scene", shot_id="shot"),
        evidence_ref=ArtifactReference(owner="execution-diagnostic", artifact_ref="test"))[0]
    assert result.category == category and result.risk_family == family


def test_main_owners_have_no_prompt_creative_or_business_gate_logic():
    for file in ("runtime/engine.py", "production/assembler.py", "governance/governor.py"):
        text = (ROOT / "src/drama_plugin" / file).read_text()
        assert "PromptCompiler" not in text and "AudioPerformanceAssembler" not in text and "Seedance" not in text
    signature = inspect.signature(__import__("drama_plugin.generation.compiler", fromlist=["PromptCompiler"]).PromptCompiler.compile)
    assert tuple(signature.parameters) == ("self", "package_ref", "task")
    for file in (ROOT / "src/drama_plugin/generation").glob("*.py"):
        ast.parse(file.read_text())
