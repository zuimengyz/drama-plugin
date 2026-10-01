"""T7: Target never falls through; evidenced old attempts remain readable."""
from __future__ import annotations

import json
import asyncio
import socket
from pathlib import Path

import pytest

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.creation import Work
from drama_plugin.generation.contracts import FinalPromptArtifact, GenerationTask
from drama_plugin.governance.contracts import GateCode, GateFinding
from drama_plugin.providers.mock import MockDramaData, MockMemoryProvider
from drama_plugin.runtime import (
    ArtifactReference, CapabilityInput, CapabilityResult, LegacyCapability, LegacyCapabilityBridge,
    ResultStatus, RunMode, RuntimeScope, RuntimeState,
)
from drama_plugin.runtime.capabilities import TargetCapabilityRouter
from drama_plugin.runtime.legacy_boundary import (
    LegacyAccessDecision, LegacyAccessRequest, LegacyBoundary, LegacyOrigin, LegacyPurpose,
    require_legacy_recovery,
)
from drama_plugin.runtime.legacy_recovery import LegacyRecovery
from test_prompt_audio_convergence import generation_fixture
from test_prompt_obligation_reconciliation import bound_fixture
from test_production_package import fixture

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT.parents[1] / "artifacts/gaixia-production/formal-final.json"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("T7 forbids Provider, network, and media submission")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr("drama_plugin.plugin.load_config", lambda _: DramaPluginConfig())


def test_boundary_only_opens_named_read_and_evidenced_recovery():
    wall = LegacyBoundary()
    request = LegacyAccessRequest(LegacyOrigin.TARGET, "work", "run", "work.get_work",
                                  LegacyPurpose.READ_ONLY)
    assert wall.decide(request) == LegacyAccessDecision.ALLOW_READ_ONLY
    assert wall.decide(LegacyAccessRequest(LegacyOrigin.TARGET, "work", "run",
        "work.production_stage.recover", LegacyPurpose.RECOVERY, "run")) == LegacyAccessDecision.REJECT_TARGET_FALLBACK
    assert wall.decide(LegacyAccessRequest(LegacyOrigin.HISTORICAL, "work", "attempt",
        "work.production_stage.recover", LegacyPurpose.RECOVERY, "attempt")) == LegacyAccessDecision.ALLOW_RECOVERY
    assert wall.decide(LegacyAccessRequest(LegacyOrigin.HISTORICAL, "work", "attempt",
        "work.production_stage.recover", LegacyPurpose.RECOVERY, "other")) == LegacyAccessDecision.REJECT_TARGET_FALLBACK


@pytest.mark.asyncio
async def test_target_router_rejects_arbitrary_registered_legacy_tool_without_call():
    called: list[str] = []
    async def old(inputs):
        called.append(inputs.operation_id)
        return CapabilityResult(status=ResultStatus.SUCCEEDED)
    bridge = LegacyCapabilityBridge({key: LegacyCapability(old, replay_safe=True) for key in (
        "work.get_work", "production.route", "old.compile_video_prompt", "provider.submit")})
    router = TargetCapabilityRouter({}, bridge)
    inputs = CapabilityInput(run_id="target", operation_id="target:0", scope=RuntimeScope(work_id="work"))
    assert router.native_keys == frozenset()
    assert router.migration_keys == frozenset({"work.get_work"})
    for key in ("production.route", "old.compile_video_prompt", "provider.submit", "unknown"):
        result = await router.execute(key, inputs)
        assert result.status == ResultStatus.FAILED and result.code == "LEGACY_GUARD"
        assert not router.replay_safe(key)
    assert called == []
    assert (await router.execute("work.get_work", inputs)).status == ResultStatus.SUCCEEDED
    assert called == ["target:0"]


@pytest.mark.asyncio
async def test_real_historical_attempt_requires_explicit_recovery_and_only_reads():
    work = Work.model_validate(json.loads(HISTORICAL.read_text()))
    data = MockDramaData(work=work)
    attempt_id = work.content["productionStage"]["attempts"][0]["attempt_id"]
    recovery = LegacyRecovery(MockMemoryProvider(data), LegacyBoundary())
    before = data.work.model_dump_json()
    snapshot = await recovery.resume_legacy_run(work_id=work.id, attempt_id=attempt_id)
    assert snapshot["workId"] == work.id and snapshot["attemptId"] == attempt_id
    assert snapshot["attemptStatus"] == "COMPLETED" and not snapshot["submissionAllowed"]
    assert len(snapshot["auditSourceFingerprint"]) == 64
    assert data.work.model_dump_json() == before
    with pytest.raises(ValueError, match="EXISTING_ATTEMPT"):
        await recovery.resume_legacy_run(work_id=work.id, attempt_id="new-target-run")


@pytest.mark.asyncio
async def test_plugin_recovery_rejects_target_run_identity(tmp_path):
    work = Work.model_validate(json.loads(HISTORICAL.read_text()))
    attempt_id = work.content["productionStage"]["attempts"][0]["attempt_id"]
    plugin = DramaPlugin.load(ROOT, mock_data=MockDramaData(work=work), ledger_path=tmp_path / "ledger.sqlite3")
    assert (await plugin.resume_legacy_run(work_id=work.id, attempt_id=attempt_id))["attemptId"] == attempt_id
    plugin.create_generation_run(work_id=work.id, scene_id="scene", shot_id="shot",
        mode=RunMode.EXPERIMENT, run_id=attempt_id)
    with pytest.raises(ValueError, match="LEGACY_GUARD"):
        await plugin.resume_legacy_run(work_id=work.id, attempt_id=attempt_id)


@pytest.mark.asyncio
async def test_direct_legacy_route_rejects_new_work_and_session_is_scoped(tmp_path, monkeypatch):
    from drama_plugin.hosts.route_production import save_route
    from test_production_route import Memory, route
    monkeypatch.setattr("drama_plugin.config.production_routes.require_video", lambda *args: None)
    with pytest.raises(ValueError, match="LEGACY_GUARD"):
        await save_route(Memory(), "W", route(tmp_path).model_dump(mode="json"))
    work = Work.model_validate(json.loads(HISTORICAL.read_text()))
    attempt_id = work.content["productionStage"]["attempts"][0]["attempt_id"]
    plugin = DramaPlugin.load(ROOT, mock_data=MockDramaData(work=work), ledger_path=tmp_path / "ledger.sqlite3")
    with pytest.raises(ValueError, match="LEGACY_GUARD"):
        require_legacy_recovery(work.id, work.content["productionStage"])
    async with plugin.legacy_recovery_session(work_id=work.id, attempt_id=attempt_id) as snapshot:
        assert snapshot["attemptId"] == attempt_id
        require_legacy_recovery(work.id, work.content["productionStage"])
        with pytest.raises(ValueError, match="LEGACY_GUARD"):
            require_legacy_recovery("other-work", work.content["productionStage"])
        trigger = asyncio.Event()
        async def delayed_use():
            await trigger.wait()
            require_legacy_recovery(work.id, work.content["productionStage"])
        child = asyncio.create_task(delayed_use())
    with pytest.raises(ValueError, match="LEGACY_GUARD"):
        require_legacy_recovery(work.id, work.content["productionStage"])
    trigger.set()
    with pytest.raises(ValueError, match="LEGACY_GUARD"):
        await child


@pytest.mark.asyncio
async def test_s02_target_shadow_uses_no_legacy_orchestration_and_restores(bound_fixture, tmp_path, monkeypatch):
    fixture, _, binding = bound_fixture
    data, directory = fixture
    before = data.work.model_dump_json()
    path = tmp_path / "ledger.sqlite3"
    first = DramaPlugin.load(ROOT, mock_data=data, production_artifact_roots=(directory,), ledger_path=path)
    first.execution_references.register(binding)
    def forbidden(*args, **kwargs):
        pytest.fail("Target crossed into Legacy orchestration or transport")
    monkeypatch.setattr("drama_plugin.runtime.bridge.LegacyCapabilityBridge.execute", forbidden)
    monkeypatch.setattr("drama_plugin.hosts.route_production.save_route", forbidden)
    monkeypatch.setattr("drama_plugin.hosts.route_production.operate", forbidden)
    monkeypatch.setattr("drama_plugin.hosts.cinematic_projection.project", forbidden)
    monkeypatch.setattr("drama_plugin.visual.video_prompt.compile_video_prompt", forbidden)
    monkeypatch.setattr("drama_plugin.hosts.http_video.VideoProviderHost.submit", forbidden)
    monkeypatch.setattr("drama_plugin.hosts.ark_image.ArkImageHost.submit", forbidden)
    run = first.create_generation_run(work_id="work", scene_id="scene", shot_id="shot",
        mode=RunMode.EXPERIMENT, run_id="t7-shadow",
        task=GenerationTask(input_mode="image_to_video", native_audio="REQUIRED"))
    partial = await first.runtime.run(run.run_id, max_ticks=5)
    assert partial.state == RuntimeState.READY
    second = DramaPlugin.load(ROOT, mock_data=data, production_artifact_roots=(directory,), ledger_path=path)
    assert (await second.runtime.recover_run(run.run_id)) == partial
    done = await second.runtime.run(run.run_id)
    assert done.state == RuntimeState.SUCCEEDED and len(done.last_result.artifact_refs) == 3
    assert data.work.model_dump_json() == before
    assert second.ledger.load_run(run.run_id) == done
    assert second.runtime.executor.native_keys
    assert second.runtime.executor.legacy.registered_keys == frozenset({"work.get_work"})


@pytest.mark.asyncio
@pytest.mark.parametrize("task,expected", [
    (GenerationTask(target_model="vidu-reference-to-video"), RuntimeState.WAITING_EXTERNAL),
    (GenerationTask(input_mode="reference"), RuntimeState.BLOCKED),
])
async def test_target_failure_has_no_old_prompt_or_route_fallback(generation_fixture, tmp_path, monkeypatch,
                                                                   task, expected):
    data, directory = generation_fixture
    plugin = DramaPlugin.load(ROOT, mock_data=data, production_artifact_roots=(directory,),
        ledger_path=tmp_path / "ledger.sqlite3")
    def forbidden(*args, **kwargs):
        pytest.fail("Target failure fell back to a Legacy execution entry")
    monkeypatch.setattr("drama_plugin.runtime.bridge.LegacyCapabilityBridge.execute", forbidden)
    monkeypatch.setattr("drama_plugin.hosts.route_production.operate", forbidden)
    monkeypatch.setattr("drama_plugin.hosts.cinematic_projection.project", forbidden)
    monkeypatch.setattr("drama_plugin.visual.video_prompt.compile_video_prompt", forbidden)
    run = plugin.create_generation_run(work_id="work", scene_id="scene", shot_id="shot",
        mode=RunMode.EXPERIMENT, run_id="t7-failure", task=task)
    result = await plugin.runtime.run(run.run_id)
    assert result.state == expected
    decision = plugin.gate_findings.decision(plugin.gate_findings.latest(run.run_id))
    assert decision.effect == ("CAPABILITY_ABSENT" if expected == RuntimeState.WAITING_EXTERNAL else "BLOCK")


@pytest.mark.asyncio
async def test_stale_reference_auto_reassembles_without_old_route(bound_fixture, monkeypatch):
    fixture, store, binding = bound_fixture
    data, directory = fixture
    plugin = DramaPlugin.load(ROOT, mock_data=data, production_artifact_roots=(directory,),
        reference_execution_store=store)
    task = GenerationTask(input_mode="image_to_video", native_audio="REQUIRED")
    original = plugin.create_generation_run(work_id="work", scene_id="scene", shot_id="shot",
        mode=RunMode.EXPERIMENT, run_id="original", task=task)
    completed = await plugin.runtime.run(original.run_id)
    assert completed.state == RuntimeState.SUCCEEDED
    prior = plugin.generation_artifacts.get(completed.last_result.artifact_refs[0], FinalPromptArtifact)
    store.register(binding.model_copy(update={"version": 2}))
    def forbidden(*args, **kwargs):
        pytest.fail("Stale binding fell back to Legacy route")
    monkeypatch.setattr("drama_plugin.runtime.bridge.LegacyCapabilityBridge.execute", forbidden)
    monkeypatch.setattr("drama_plugin.hosts.route_production.operate", forbidden)
    resumed = plugin.create_generation_run(work_id="work", scene_id="scene", shot_id="shot",
        mode=RunMode.EXPERIMENT, run_id="stale", task=task, package_ref=prior.source_package_ref)
    result = await plugin.runtime.run(resumed.run_id)
    assert result.state == RuntimeState.SUCCEEDED
    current = plugin.generation_artifacts.get(result.last_result.artifact_refs[0], FinalPromptArtifact)
    assert current.source_package_ref != prior.source_package_ref
    assert current.execution_reference_refs[0].version == 2


@pytest.mark.asyncio
async def test_provider_absence_finding_waits_without_old_provider(bound_fixture, tmp_path, monkeypatch):
    fixture, _, binding = bound_fixture
    data, directory = fixture
    plugin = DramaPlugin.load(ROOT, mock_data=data, production_artifact_roots=(directory,),
        ledger_path=tmp_path / "ledger.sqlite3")
    plugin.execution_references.register(binding)
    def forbidden(*args, **kwargs):
        pytest.fail("Capability absence invoked old Provider")
    monkeypatch.setattr("drama_plugin.hosts.http_video.VideoProviderHost.submit", forbidden)
    monkeypatch.setattr("drama_plugin.hosts.ark_image.ArkImageHost.submit", forbidden)
    scope = RuntimeScope(work_id="work", scene_id="scene", shot_id="shot")
    finding = GateFinding.classified(GateCode.CAPABILITY_NOT_IMPLEMENTED,
        owner="provider-adapter", scope=scope,
        evidence_ref=ArtifactReference(owner="capability-catalog", artifact_ref="offline:provider-absent", version=1),
        required=True)
    ref = plugin.gate_findings.put_finding(finding)
    run = plugin.create_governed_run(work_id="work", scene_id="scene", shot_id="shot",
        mode=RunMode.EXPERIMENT, run_id="provider-unavailable", finding_refs=(ref,))
    result = await plugin.runtime.run(run.run_id)
    assert result.state == RuntimeState.WAITING_EXTERNAL
    decision = plugin.gate_findings.decision(plugin.gate_findings.latest(run.run_id))
    assert decision.effect == "CAPABILITY_ABSENT"


def test_critical_lifecycle_metadata_is_machine_visible():
    from drama_plugin.hosts import cinematic_projection, route_production, sequence_execution
    from drama_plugin.hosts.http_video import VideoProviderHost
    from drama_plugin.hosts.ark_image import ArkImageHost
    from drama_plugin.visual import video_prompt
    assert LegacyCapabilityBridge.lifecycle == "MIGRATION_ONLY"
    assert route_production.lifecycle == "LEGACY_RECOVERY_ONLY"
    assert sequence_execution.lifecycle == VideoProviderHost.lifecycle == ArkImageHost.lifecycle == "LEGACY_RECOVERY_ONLY"
    assert cinematic_projection.lifecycle == video_prompt.lifecycle == "LEGACY_COMPATIBILITY"
