"""E1 offline control-plane, retained-media, review and AV closure acceptance."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.execution.audio import ApprovedAudioConsumer
from drama_plugin.execution.capability import TargetExecution
from drama_plugin.execution.contracts import (
    AVDerivative, AudioExecution, AudioPlacement, Authorization, CreativeMediaReview,
    ExecutionOperation, FinishingRecipe, MediaBinding, OperationState, ProviderAttempt,
    ProviderReceipt, ProviderResult, ReviewedAVCandidate, TechnicalMediaReview,
)
from drama_plugin.execution.media import LocalMediaStore, inspect, probe
from drama_plugin.execution.review import MockReviewer
from drama_plugin.execution.transport import CapabilityAbsent, IntakeTransient, ReplayTransport, serialize_request
from drama_plugin.generation.contracts import AudioExecutionPlan, FinalPromptArtifact, GenerationPreparation, PromptIR
from drama_plugin.governance.contracts import GateEffect, HardStopFamily
from drama_plugin.runtime import ArtifactReference, RunMode, RuntimeState
from drama_plugin.runtime.contracts import CapabilityInput, ResultStatus, RecoveryClass
from test_production_package import fixture
from test_prompt_audio_convergence import generation_fixture, load, parallel_fixture

ROOT = Path(__file__).resolve().parents[1]
APPROVAL = ArtifactReference(owner="user-decision", artifact_ref="offline-fixture-approval", version=1)


@pytest.fixture(autouse=True)
def offline_boundary(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("E1 forbids all external generation/network/legacy orchestration")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr("drama_plugin.plugin.load_config", lambda _: DramaPluginConfig())
    monkeypatch.setattr("drama_plugin.professional.compile_prompt_projection", forbidden)
    monkeypatch.setattr("drama_plugin.hosts.cinematic_projection.project", forbidden)
    monkeypatch.setattr("drama_plugin.visual.video_prompt.compile_request_ir", forbidden)
    monkeypatch.setattr("drama_plugin.hosts.http_video.VideoProviderHost.generate", forbidden, raising=False)


def create_video(path, duration_ms=6000, *, audio=True):
    command = ["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=64x64:r=10"]
    if audio:
        command += ["-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000"]
    command += ["-t", str(duration_ms / 1000), "-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if audio:
        command += ["-c:a", "aac"]
    subprocess.run([*command, str(path)], check=True, capture_output=True)
    return ProviderResult(result_id="recorded-video-result", locator=str(path),
                          expected_hash=hashlib.sha256(path.read_bytes()).hexdigest())


@pytest.fixture(scope="module")
def recorded_video(tmp_path_factory):
    return create_video(tmp_path_factory.mktemp("e1-media") / "fixture.mp4")


def create_clip(store, tmp_path, event, duration_ms, frequency=330):
    path = tmp_path / (event + ".wav")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
        f"sine=frequency={frequency}:sample_rate=48000", "-t", str(duration_ms / 1000), str(path)],
        check=True, capture_output=True)
    return store.retain(path.read_bytes(), kind="AUDIO", mime="audio/wav")


async def setup(generation_fixture, tmp_path, recorded_video, *, behavior="success", reviewer=True,
                transport=True, native_policy="PRESERVE", parallel=False, mode=RunMode.EXPERIMENT,
                authorized=True, cost=0, budget=0, audio_consumer=True):
    if parallel:
        generation_fixture = parallel_fixture(generation_fixture)
    replay = ReplayTransport(tmp_path / "remote", recorded_video, behavior=behavior)
    plugin = load(generation_fixture, ledger_path=tmp_path / "ledger.sqlite3",
        target_transports={"offline-replay": replay} if transport else {},
        target_reviewer=MockReviewer() if reviewer is True else reviewer or None,
        target_audio=ApprovedAudioConsumer() if audio_consumer else None)
    prepared_run = plugin.create_generation_run(work_id="work", scene_id="scene", shot_id="shot",
        mode=mode, run_id="prepare")
    done = await plugin.runtime.run(prepared_run.run_id)
    assert done.state == RuntimeState.SUCCEEDED
    preparation_ref = plugin.generation_artifacts.prepared(done.run_id)
    prepared = plugin.generation_artifacts.get(preparation_ref, GenerationPreparation)
    plan = plugin.generation_artifacts.get(prepared.audio_plan_ref, AudioExecutionPlan)
    placements, bed_placements = [], []
    if native_policy != "PRESERVE":
        for index, event in enumerate(plan.speech_events):
            start, end = event.window_ms or (0, 1000)
            media = create_clip(plugin.execution.media, tmp_path, event.event_id, end - start, 330 + index * 110)
            fade_relation = next((r for r in plan.relations if r.event_id == event.event_id and r.relation.value == "FADE_BEHIND"), None)
            fade = next(e.window_ms for e in plan.speech_events if e.event_id == fade_relation.target_event_id) if fade_relation else None
            placements.append(AudioPlacement(event_id=event.event_id, source_ref=event.source_ref,
                media=media, start_ms=start, gain_db=-12, fade_out_window_ms=fade))
        for index, ref in enumerate((*plan.ambience_refs, *plan.foley_refs, *plan.music_refs)):
            media = create_clip(plugin.execution.media, tmp_path, "bed" + str(index), plan.duration_ms, 110)
            bed_placements.append(AudioPlacement(event_id="bed" + str(index), source_ref=ref,
                media=media, start_ms=0, gain_db=-24))
    recipe = FinishingRecipe.seal(scope=plan.scope, run_id="execute", source_package_ref=prepared.source_package_ref,
        preparation_ref=preparation_ref, audio_plan_ref=prepared.audio_plan_ref, approval_ref=APPROVAL,
        native_policy=native_policy, placements=tuple(placements),
        bed_refs=(*plan.ambience_refs, *plan.foley_refs, *plan.music_refs) if native_policy != "PRESERVE" else (),
        bed_placements=tuple(bed_placements))
    authorization = Authorization(approval_ref=APPROVAL, authorized=authorized,
        estimated_cost_microunits=cost, budget_microunits=budget)
    run = plugin.create_execution_run(run_id="execute", mode=mode, preparation_ref=preparation_ref,
        authorization=authorization, recipe=recipe, route="offline-replay")
    inputs = CapabilityInput(run_id=run.run_id, operation_id="execute:0", scope=run.scope)
    return plugin, replay, inputs


def submissions(replay):
    log = replay.directory / "submissions.jsonl"
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def checkpoint(plugin, inputs):
    operation, _, _ = plugin.execution._approved(inputs)
    return plugin.execution.store.checkpoint(operation.artifact_reference())


@pytest.mark.parametrize("mode", list(RunMode))
async def test_complete_offline_candidate_exact_transfer_and_identity(generation_fixture, tmp_path, recorded_video, mode, monkeypatch):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video, mode=mode)
    before = generation_fixture[0].work.model_dump_json()
    preparation = plugin.execution.derived(plugin.execution.store.inputs(inputs.run_id).preparation_ref, GenerationPreparation)
    final = plugin.execution.derived(preparation.final_prompt_ref, FinalPromptArtifact)
    prompt_ir_ref = ArtifactReference(owner="prompt-ir", artifact_ref="prompt-ir:" + final.prompt_ir_fingerprint, version=1)
    prompt_ir = plugin.execution.derived(prompt_ir_ref, PromptIR)
    fingerprints = (preparation.source_package_ref, final.fingerprint, prompt_ir.fingerprint,
                    plugin.execution.derived(preparation.audio_plan_ref, AudioExecutionPlan).fingerprint)
    def forbidden(*args, **kwargs):
        raise AssertionError("Execution must not rediscover creative/legacy state")
    monkeypatch.setattr(plugin.shot_assembler, "assemble", forbidden)
    monkeypatch.setattr(plugin.prompt_compiler.generator, "generate", forbidden)
    monkeypatch.setattr(plugin.providers.production, "generate_video", forbidden)
    done = await plugin.runtime.run(inputs.run_id)
    assert done.state == RuntimeState.SUCCEEDED, done
    candidate = plugin.execution.store.get(done.last_result.artifact_refs[0], ReviewedAVCandidate)
    assert candidate.readiness == "REVIEWED_AV_CANDIDATE" and not candidate.canon_adopted and not candidate.final_delivery
    assert len(submissions(replay)) == 1
    assert submissions(replay)[0]["promptText"] == final.prompt_text
    assert fingerprints == (preparation.source_package_ref, plugin.execution.derived(preparation.final_prompt_ref, FinalPromptArtifact).fingerprint,
        plugin.execution.derived(prompt_ir_ref, PromptIR).fingerprint,
        plugin.execution.derived(preparation.audio_plan_ref, AudioExecutionPlan).fingerprint)
    assert generation_fixture[0].work.model_dump_json() == before
    assert {key for key in plugin.runtime.executor.native_keys if key.startswith("execution.")} == {
        "execution.provider:v1", "execution.media_intake:v1", "execution.media_review:v1",
        "execution.audio:v1", "execution.av_candidate:v1"}
    assert plugin.execution.store.get(candidate.av_creative_ref, CreativeMediaReview).media == candidate.media
    assert plugin.execution.store.get(candidate.av_technical_ref, TechnicalMediaReview).media == candidate.media
    assert plugin.execution.store.get(candidate.video_creative_ref, CreativeMediaReview).media != candidate.media
    assert probe(plugin.execution.media.path(candidate.media)).audio_codec
    with plugin.ledger.transaction() as db:
        assert {r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")} == {
            "production_run", "immutable_artifact", "ledger_index", "production_operation"}
        ledger_text = "\n".join(row[0] for row in db.execute("SELECT body_json FROM immutable_artifact"))
        assert "base64" not in ledger_text
        assert candidate.media.content_hash in ledger_text
    assert await plugin.runtime.run(inputs.run_id) == done
    assert len(submissions(replay)) == 1


async def test_crash_before_send_reserved_can_send_once(generation_fixture, tmp_path, recorded_video):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video)
    claimed = plugin.execution.reserve(inputs)
    assert claimed.state == OperationState.RESERVED and submissions(replay) == []
    restored = load(generation_fixture, ledger_path=plugin.ledger.path,
        target_transports={"offline-replay": replay}, target_reviewer=MockReviewer(), target_audio=ApprovedAudioConsumer())
    assert restored.execution.reserve(inputs) == claimed
    assert (await restored.runtime.run(inputs.run_id)).state == RuntimeState.SUCCEEDED
    assert len(submissions(replay)) == 1


async def test_ack_loss_restore_queries_same_attempt_without_resubmit(generation_fixture, tmp_path, recorded_video):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video, behavior="ack-loss")
    waiting = await plugin.runtime.run(inputs.run_id)
    assert waiting.state == RuntimeState.WAITING_EXTERNAL
    initial = checkpoint(plugin, inputs)
    assert initial.state == OperationState.UNKNOWN
    assert plugin.gate_findings.decision(plugin.gate_findings.latest(inputs.run_id)).risk_families == (HardStopFamily.HS3,)
    restored = load(generation_fixture, ledger_path=plugin.ledger.path,
        target_transports={"offline-replay": ReplayTransport(replay.directory, recorded_video)},
        target_reviewer=MockReviewer(), target_audio=ApprovedAudioConsumer())
    done = await restored.resume_execution_run(inputs.run_id)
    assert done.state == RuntimeState.SUCCEEDED
    assert checkpoint(restored, inputs).attempt_ref == initial.attempt_ref
    assert len(submissions(replay)) == 1


async def test_unknown_unqueryable_hard_blocks_without_resubmission(generation_fixture, tmp_path, recorded_video):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video, behavior="ack-loss")
    replay.query_available = False
    waiting = await plugin.runtime.run(inputs.run_id)
    assert waiting.state == RuntimeState.FAILED
    assert waiting.last_result.code == "PROVIDER_UNKNOWN_WITHOUT_LOOKUP"
    assert waiting.last_result.recovery_class == RecoveryClass.HARD_BLOCK
    for _ in range(3):
        assert await plugin.resume_execution_run(inputs.run_id) == waiting
    assert checkpoint(plugin, inputs).state == OperationState.UNKNOWN
    assert len(submissions(replay)) == 1


async def test_submitting_without_receipt_is_uncertain_never_resubmitted(generation_fixture, tmp_path, recorded_video):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video)
    reserved = plugin.execution.reserve(inputs)
    assert plugin.execution.store.claim_dispatch(reserved.operation_ref)
    assert not plugin.execution.store.claim_dispatch(reserved.operation_ref)
    result = await plugin.execution.execute(inputs)
    assert result.status == ResultStatus.FAILED
    assert result.code == "PROVIDER_UNKNOWN_WITHOUT_LOOKUP"
    assert checkpoint(plugin, inputs).state == OperationState.UNKNOWN
    assert submissions(replay) == []


async def test_running_restore_polls_same_provider_task(generation_fixture, tmp_path, recorded_video):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video, behavior="running")
    waiting = await plugin.runtime.run(inputs.run_id)
    assert waiting.state == RuntimeState.WAITING_EXTERNAL
    current = checkpoint(plugin, inputs)
    receipt = plugin.execution.store.get(current.receipt_ref, ProviderReceipt)
    terminal = ProviderReceipt.seal(**{**receipt.model_dump(exclude={"fingerprint"}), "state": "SUCCEEDED", "result": recorded_video})
    replay._path(plugin.execution.store.get(current.attempt_ref, ProviderAttempt)).write_text(terminal.model_dump_json())
    assert (await plugin.resume_execution_run(inputs.run_id)).state == RuntimeState.SUCCEEDED
    assert len(submissions(replay)) == 1
    assert plugin.execution.store.get(checkpoint(plugin, inputs).receipt_ref, ProviderReceipt).remote_identity == receipt.remote_identity


@pytest.mark.parametrize("behavior,code", (("failed", "PROVIDER_DEFINITE_FAILURE"), ("not-submitted", "DEFINITELY_NOT_SUBMITTED")))
async def test_provider_definite_failure_not_all_errors_unknown(generation_fixture, tmp_path, recorded_video, behavior, code):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video, behavior=behavior)
    done = await plugin.runtime.run(inputs.run_id)
    assert done.state == RuntimeState.FAILED and done.last_result.code == code
    assert checkpoint(plugin, inputs).state == OperationState.FAILED
    assert len(submissions(replay)) == (behavior != "not-submitted")


@pytest.mark.parametrize("authorized,cost,budget,family", ((False, 0, 0, HardStopFamily.HS2), (True, 2, 1, HardStopFamily.HS2), (True, 1, 2, HardStopFamily.HS4)))
async def test_pre_side_effect_checks_use_existing_governor(generation_fixture, tmp_path, recorded_video, authorized, cost, budget, family):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video, authorized=authorized, cost=cost, budget=budget)
    done = await plugin.runtime.run(inputs.run_id)
    assert done.state == (RuntimeState.FAILED if cost else RuntimeState.WAITING_USER)
    decision = plugin.gate_findings.decision(plugin.gate_findings.latest(inputs.run_id))
    assert decision.effect == GateEffect.BLOCK and family in decision.risk_families
    with pytest.raises(KeyError):
        checkpoint(plugin, inputs)
    with plugin.ledger.transaction() as db:
        assert db.execute("SELECT count(*) FROM immutable_artifact WHERE artifact_type='execution-operation'").fetchone()[0] == 0
    assert submissions(replay) == []


async def test_provider_absent_and_live_transport_never_called(generation_fixture, tmp_path, recorded_video):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video, transport=False)
    done = await plugin.runtime.run(inputs.run_id)
    assert done.state == RuntimeState.FAILED and done.last_result.recovery_class == RecoveryClass.HARD_BLOCK
    assert plugin.gate_findings.decision(plugin.gate_findings.latest(inputs.run_id)).effect == GateEffect.CAPABILITY_ABSENT
    replay.offline = False
    plugin.execution.transports["offline-replay"] = replay
    assert await plugin.resume_execution_run(inputs.run_id) == done
    assert submissions(replay) == []


async def test_media_intake_retry_does_not_submit_again(generation_fixture, tmp_path, recorded_video, monkeypatch):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video)
    assert (await plugin.execution.execute(inputs)).status == ResultStatus.SUCCEEDED
    original = replay.obtain
    attempts = 0
    async def transient(result):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise IntakeTransient()
        return await original(result)
    monkeypatch.setattr(replay, "obtain", transient)
    first = await plugin.execution.intake(inputs)
    assert first.status == ResultStatus.RETRYABLE_FAILURE
    second = await plugin.execution.intake(inputs)
    assert second.status == ResultStatus.SUCCEEDED
    assert await plugin.execution.intake(inputs) == second
    assert len(submissions(replay)) == 1 and attempts == 2
    assert checkpoint(plugin, inputs).progress.intake_attempts == 2


async def test_intake_retry_is_bounded(generation_fixture, tmp_path, recorded_video, monkeypatch):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video)
    await plugin.execution.execute(inputs)
    async def failed(result):
        raise IntakeTransient()
    monkeypatch.setattr(replay, "obtain", failed)
    for _ in range(2):
        assert (await plugin.execution.intake(inputs)).status == ResultStatus.RETRYABLE_FAILURE
    exhausted = await plugin.execution.intake(inputs)
    assert exhausted.status == ResultStatus.FAILED and exhausted.code == "MEDIA_INTAKE_RETRY_EXHAUSTED"
    assert exhausted.recovery_class == RecoveryClass.HARD_BLOCK
    assert (await plugin.execution.intake(inputs)).code == "MEDIA_INTAKE_RETRY_EXHAUSTED"
    assert len(submissions(replay)) == 1


@pytest.mark.parametrize("boundary", ("provider", "intake", "review", "audio"))
async def test_restored_stages_resume_without_repeating_prior_work(generation_fixture, tmp_path, recorded_video, monkeypatch, boundary):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video)
    stages = [plugin.execution.execute, plugin.execution.intake, plugin.execution.review, plugin.execution.execute_audio]
    for handler in stages[:("provider", "intake", "review", "audio").index(boundary)+1]:
        assert (await handler(inputs)).status == ResultStatus.SUCCEEDED
    current = checkpoint(plugin, inputs)
    restored = load(generation_fixture, ledger_path=plugin.ledger.path,
        target_transports={"offline-replay": replay}, target_reviewer=MockReviewer(), target_audio=ApprovedAudioConsumer())
    async def forbidden(*args):
        raise AssertionError("Completed retained stage must not be repeated")
    monkeypatch.setattr(replay, "submit", forbidden)
    if current.progress.video_ref:
        monkeypatch.setattr(replay, "obtain", forbidden)
    if current.progress.video_creative_ref:
        original = restored.execution.reviewer.review
        async def only_derivative(operation, media, **kwargs):
            assert media != restored.execution.store.get(current.progress.video_ref, MediaBinding).media
            return await original(operation, media, **kwargs)
        monkeypatch.setattr(restored.execution.reviewer, "review", only_derivative)
    if current.progress.audio_ref:
        monkeypatch.setattr(restored.execution.audio, "render", forbidden)
    assert (await restored.runtime.run(inputs.run_id)).state == RuntimeState.SUCCEEDED
    assert len(submissions(replay)) == 1


@pytest.mark.parametrize("case", ("valid", "corrupt", "duration", "no-audio", "mime"))
def test_technical_review_fixtures(tmp_path, recorded_video, case):
    store = LocalMediaStore(tmp_path / "media")
    if case == "corrupt":
        media = store.retain(b"corrupt mp4 fixture", kind="VIDEO", mime="video/mp4")
    elif case == "no-audio":
        result = create_video(tmp_path / "silent.mp4", audio=False)
        media = store.retain(Path(result.locator).read_bytes(), kind="VIDEO", mime="video/mp4")
    elif case == "mime":
        clip = create_clip(store, tmp_path, "not-video", 6000)
        # Different store accepts advertised MIME, QA must inspect actual bytes.
        other = LocalMediaStore(tmp_path / "wrong-mime")
        media = other.retain(store.path(clip).read_bytes(), kind="VIDEO", mime="video/mp4")
        store = other
    else:
        media = store.retain(Path(recorded_video.locator).read_bytes(), kind="VIDEO", mime="video/mp4")
    observation, failures = inspect(store, media, duration_ms=2000 if case == "duration" else 6000,
                                    tolerance_ms=100, audio_expected=True)
    if case == "valid":
        assert observation.video_codec and observation.audio_codec and failures == ()
    else:
        assert failures


@pytest.mark.parametrize("reviewer,outcome", ((MockReviewer(), "PASS"), (MockReviewer("REVISE"), "REVISE"), (None, "CAPABILITY_ABSENT")))
async def test_creative_review_boundary(generation_fixture, tmp_path, recorded_video, reviewer, outcome):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video, reviewer=reviewer)
    await plugin.execution.execute(inputs)
    await plugin.execution.intake(inputs)
    before = generation_fixture[0].work.model_dump_json()
    result = await plugin.execution.review(inputs)
    assert result.status == {"PASS":ResultStatus.SUCCEEDED,"REVISE":ResultStatus.WAITING_EXTERNAL,
        "CAPABILITY_ABSENT":ResultStatus.FAILED}[outcome]
    progress = checkpoint(plugin, inputs).progress
    assert plugin.execution.store.get(progress.video_technical_ref, TechnicalMediaReview).outcome == "PASS"
    with plugin.ledger.transaction() as db:
        bodies = [CreativeMediaReview.model_validate_json(r[0]) for r in db.execute(
            "SELECT body_json FROM immutable_artifact WHERE artifact_type='creative-media-review'")]
    assert len(bodies) == 1 and bodies[0].outcome == outcome
    assert bodies[0].media == plugin.execution.store.get(progress.video_ref, MediaBinding).media
    if outcome == "REVISE":
        assert bodies[0].observations[0].owner and bodies[0].observations[0].required_revision
    assert generation_fixture[0].work.model_dump_json() == before


async def test_absent_reviewer_registration_does_not_reset_hard_blocked_runtime(generation_fixture, tmp_path, recorded_video):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video, reviewer=False)
    blocked = await plugin.runtime.run(inputs.run_id)
    assert blocked.state == RuntimeState.FAILED and blocked.last_result.recovery_class == RecoveryClass.HARD_BLOCK
    plugin.execution.reviewer = MockReviewer()
    assert await plugin.resume_execution_run(inputs.run_id) == blocked
    # The existing owner can read/review its fixed media; there is no paid retry.
    assert (await plugin.execution.review(inputs)).status == ResultStatus.SUCCEEDED
    assert len(submissions(replay)) == 1


async def test_parallel_audio_real_measured_placements_preserve_all_relations(generation_fixture, tmp_path, recorded_video):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video, parallel=True, native_policy="REPLACE")
    for handler in (plugin.execution.execute, plugin.execution.intake, plugin.execution.review, plugin.execution.execute_audio):
        assert (await handler(inputs)).status == ResultStatus.SUCCEEDED
    done = await plugin.runtime.run(inputs.run_id)
    assert done.state == RuntimeState.SUCCEEDED, done
    candidate = plugin.execution.store.get(done.last_result.artifact_refs[0], ReviewedAVCandidate)
    audio = plugin.execution.store.get(candidate.audio_execution_ref, AudioExecution)
    timings = {t.event_id: t for t in audio.timings}
    assert {t.layer for t in timings.values()} == {"PRIMARY", "SECONDARY", "BACKGROUND"}
    assert timings["S1"].start_ms < timings["P1"].end_ms
    assert timings["S1"].start_ms < timings["P2"].start_ms < timings["S1"].end_ms
    assert timings["BG"].start_ms < timings["P2"].end_ms and timings["BG"].end_ms > timings["P2"].start_ms
    assert timings["P1"].end_ms <= timings["P2"].start_ms
    assert audio.audio_plan_ref == plugin.execution.store.get(checkpoint(plugin, inputs).operation_ref, ExecutionOperation).audio_plan_ref
    assert audio.subtitle_status == "UNTIMED" and not audio.render_authorized  # BG is nonverbatim.
    # Physical proof: BG's 660 Hz component is present before the approved fade
    # and absent after it. Other layers use distinct frequencies.
    from array import array
    import math
    decoded = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(plugin.execution.media.path(audio.media)),
        "-ac", "1", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    samples = array("f"); samples.frombytes(decoded)
    def component(start):
        window = samples[int(start * 48000):int((start + 0.2) * 48000)]
        return abs(sum(value * math.sin(2 * math.pi * 660 * index / 48000) for index, value in enumerate(window))) / len(window)
    assert component(1.5) > 0.005
    assert component(4.5) < component(1.5) * 0.001


async def test_timed_speech_preparation_and_no_subtitle_render(generation_fixture, tmp_path, recorded_video):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video, native_policy="REPLACE")
    done = await plugin.runtime.run(inputs.run_id)
    assert done.state == RuntimeState.SUCCEEDED, done
    candidate = plugin.execution.store.get(done.last_result.artifact_refs[0], ReviewedAVCandidate)
    audio = plugin.execution.store.get(candidate.audio_execution_ref, AudioExecution)
    assert audio.subtitle_status == "TIMED_PREPARATION" and not audio.render_authorized
    assert audio.timings[0].end_ms == 1000


async def test_audio_capability_absent_no_fish_fallback(generation_fixture, tmp_path, recorded_video):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video, audio_consumer=False)
    waiting = await plugin.runtime.run(inputs.run_id)
    assert waiting.state == RuntimeState.WAITING_EXTERNAL and waiting.cursor == 3
    assert checkpoint(plugin, inputs).progress.audio_ref is None
    assert len(submissions(replay)) == 1


async def test_two_workers_unique_submit_and_registration(generation_fixture, tmp_path, recorded_video):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video)
    other = load(generation_fixture, ledger_path=plugin.ledger.path,
        target_transports={"offline-replay": replay}, target_reviewer=MockReviewer(), target_audio=ApprovedAudioConsumer())
    results = await asyncio.gather(plugin.execution.execute(inputs), other.execution.execute(inputs))
    assert all(r.status == ResultStatus.SUCCEEDED for r in results)
    imports = await asyncio.gather(plugin.execution.intake(inputs), other.execution.intake(inputs))
    assert imports[0] == imports[1]
    assert len(submissions(replay)) == 1
    with plugin.ledger.transaction() as db:
        assert db.execute("SELECT count(*) FROM production_operation WHERE operation_ref_json IS NOT NULL").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM immutable_artifact WHERE artifact_type='provider-attempt'").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM immutable_artifact WHERE artifact_type='media-binding'").fetchone()[0] == 1


def test_content_identity_retention_is_idempotent(tmp_path, recorded_video):
    first = LocalMediaStore(tmp_path / "media")
    content = Path(recorded_video.locator).read_bytes()
    identity = first.retain(content, kind="VIDEO", mime="video/mp4")
    assert LocalMediaStore(first.directory).retain(content, kind="VIDEO", mime="video/mp4") == identity
    assert len(list(first.directory.iterdir())) == 2
    with pytest.raises(ValueError, match="hash"):
        first.retain(content, kind="VIDEO", mime="video/mp4", expected_hash="a" * 64)


async def test_receipt_cannot_bind_wrong_attempt_or_prompt(generation_fixture, tmp_path, recorded_video):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video)
    from drama_plugin.runtime.contracts import RuntimeScope
    wrong_scope = inputs.model_copy(update={"scope": RuntimeScope(work_id="work", scene_id="scene", shot_id="other")})
    denied = await plugin.execution.execute(wrong_scope)
    assert denied.status == ResultStatus.FAILED and submissions(replay) == []
    assert plugin.gate_findings.decision(plugin.gate_findings.latest(inputs.run_id)).risk_families == (HardStopFamily.HS1,)
    operation, request, _ = plugin.execution._approved(inputs)
    reserved = plugin.execution.reserve(inputs)
    attempt = plugin.execution.store.get(reserved.attempt_ref, ProviderAttempt)
    receipt = await replay.submit(operation, attempt, request)
    plugin.execution.store.claim_dispatch(reserved.operation_ref)
    wrong = ProviderReceipt.seal(**{**receipt.model_dump(exclude={"fingerprint"}), "request_fingerprint": "b" * 64})
    with pytest.raises(ValueError, match="identity"):
        plugin.execution.store.receipt(reserved.operation_ref, wrong)


async def test_wrong_media_cannot_reuse_review_artifact(generation_fixture, tmp_path, recorded_video):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video)
    await plugin.execution.execute(inputs)
    await plugin.execution.intake(inputs)
    await plugin.execution.review(inputs)
    progress = checkpoint(plugin, inputs).progress
    review = plugin.execution.store.get(progress.video_creative_ref, CreativeMediaReview)
    changed = CreativeMediaReview.seal(**{**review.model_dump(exclude={"fingerprint"}),
        "media": plugin.execution.media.retain(b"other media", kind="VIDEO", mime="video/mp4")})
    assert changed.artifact_reference() != review.artifact_reference()
    plugin.execution.store.put(changed)
    with pytest.raises(ValueError, match="immutable"):
        plugin.execution.store.progress(checkpoint(plugin, inputs).operation_ref, video_creative_ref=changed.artifact_reference())


def test_execution_has_no_legacy_host_or_prompt_calls():
    directory = ROOT / "src/drama_plugin/execution"
    code = "\n".join(p.read_text() for p in directory.glob("*.py"))
    for forbidden in ("route_production(", "VideoProviderHost", "sequence_execution", "productionHistory",
                      "promptHistory", "FishRoleDubbingProvider", "compile_request_ir", "cinematic_projection"):
        assert forbidden not in code


def test_real_s02_k02_multi_process_reviewed_candidate(tmp_path):
    script = ROOT / "integration/target_execution_shadow.py"
    evidence = tmp_path / "shadow"
    result = subprocess.run([sys.executable, str(script), "all", "--directory", str(evidence)],
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, cwd=ROOT,
        capture_output=True, text=True, timeout=150)
    assert result.returncode == 0, result.stdout + result.stderr
    result = json.loads((evidence / "summary.json").read_text())
    assert result["end"] == "REVIEWED_AV_CANDIDATE"
    assert len(set(result["processIds"])) == 5
    assert result["syntheticSubmissions"] == 1 and result["realProviderSubmission"] == 0
    assert result["fingerprintsUnchanged"]


def shadow_command(phase, directory, *arguments):
    return [sys.executable, str(ROOT / "integration/target_execution_shadow.py"), phase,
            "--directory", str(directory), *arguments]


@pytest.mark.parametrize("boundary", ("reserved", "after-send"))
def test_real_process_crash_restore_no_blind_second_submit(tmp_path, boundary):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    directory = tmp_path / "crash"
    subprocess.run(shadow_command("prepare", directory), env=env, check=True, capture_output=True, timeout=60)
    if boundary == "after-send":
        crashed = subprocess.run(shadow_command("provider", directory, "--behavior", "crash-after-send"),
                                 env=env, capture_output=True, timeout=60)
        assert crashed.returncode == 73
        from drama_plugin.persistence import ProductionLedger
        ledger = ProductionLedger(directory / "ledger.sqlite3")
        with ledger.transaction() as db:
            assert db.execute("SELECT dispatch_state FROM production_operation WHERE operation_ref_json IS NOT NULL").fetchone()[0] == "SUBMITTING"
    for phase in ("provider", "media", "finish", "terminal"):
        completed = subprocess.run(shadow_command(phase, directory), env=env, capture_output=True, text=True, timeout=60)
        assert completed.returncode == 0, completed.stdout + completed.stderr
    terminal = json.loads((directory / "terminal.json").read_text())
    assert terminal["candidate"]["readiness"] == "REVIEWED_AV_CANDIDATE"
    assert terminal["syntheticSubmissions"] == 1 and terminal["realProviderSubmission"] == 0


def test_two_real_processes_dispatch_and_intake_same_operation(tmp_path):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    directory = tmp_path / "concurrent"
    subprocess.run(shadow_command("prepare", directory), env=env, check=True, capture_output=True, timeout=60)
    workers = [subprocess.Popen(shadow_command("worker", directory, "--label", name), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for name in ("worker-a", "worker-b")]
    for worker in workers:
        stdout, stderr = worker.communicate(timeout=60)
        assert worker.returncode == 0, stdout + stderr
    a, b = [json.loads((directory / (name + ".json")).read_text()) for name in ("worker-a", "worker-b")]
    assert a["pid"] != b["pid"]
    assert a["operationRef"] == b["operationRef"] and a["attemptRef"] == b["attemptRef"]
    assert a["progress"]["video_ref"] == b["progress"]["video_ref"]
    assert a["syntheticSubmissions"] == b["syntheticSubmissions"] == 1
    from drama_plugin.persistence import ProductionLedger
    ledger = ProductionLedger(directory / "ledger.sqlite3")
    with ledger.transaction() as db:
        assert db.execute("SELECT count(*) FROM immutable_artifact WHERE artifact_type='media-binding'").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM immutable_artifact WHERE artifact_type='provider-attempt'").fetchone()[0] == 1


async def test_candidate_cannot_borrow_other_media_pass_reviews(generation_fixture, tmp_path, recorded_video):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video)
    done = await plugin.runtime.run(inputs.run_id)
    candidate = plugin.execution.store.get(done.last_result.artifact_refs[0], ReviewedAVCandidate)
    fake = ReviewedAVCandidate.seal(**{**candidate.model_dump(exclude={"fingerprint"}),
        "av_creative_ref": candidate.video_creative_ref})
    with pytest.raises(ValueError, match="exact media"):
        plugin.execution.store.put(fake)
    with pytest.raises(ValueError, match="exact media"):
        plugin.ledger.put_artifact(fake.owner, fake.artifact_reference(), fake.scope, fake.fingerprint, fake)


async def test_missing_speech_consumer_is_capability_absence(generation_fixture, tmp_path, recorded_video):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video)
    selected = plugin.execution.store.inputs(inputs.run_id)
    prepared = plugin.execution.derived(selected.preparation_ref, GenerationPreparation)
    recipe = FinishingRecipe.seal(scope=inputs.scope, run_id="missing-speech", source_package_ref=prepared.source_package_ref,
        preparation_ref=selected.preparation_ref, audio_plan_ref=prepared.audio_plan_ref, approval_ref=APPROVAL, native_policy="REPLACE")
    plugin.create_execution_run(run_id="missing-speech", mode=RunMode.EXPERIMENT, preparation_ref=selected.preparation_ref,
        authorization=selected.authorization, recipe=recipe, route="offline-replay")
    waiting = await plugin.runtime.run("missing-speech")
    assert waiting.state == RuntimeState.WAITING_EXTERNAL and waiting.cursor == 3


async def test_provider_absence_does_not_manufacture_external_task_or_free_recovery(generation_fixture, tmp_path, recorded_video):
    plugin, replay, inputs = await setup(generation_fixture, tmp_path, recorded_video, transport=False)
    failed = await plugin.runtime.run(inputs.run_id)
    assert failed.state == RuntimeState.FAILED and failed.last_result.recovery_class == RecoveryClass.HARD_BLOCK
    with pytest.raises(KeyError):
        checkpoint(plugin, inputs)
    plugin.execution.transports["offline-replay"] = replay
    assert (await plugin.resume_execution_run(inputs.run_id)).state == RuntimeState.FAILED
    assert submissions(replay) == []
