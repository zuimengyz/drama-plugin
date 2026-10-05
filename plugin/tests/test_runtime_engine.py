"""T1 offline acceptance: orchestration, references, waits, recovery and authority."""
from __future__ import annotations

import asyncio
import json
import socket
from pathlib import Path

import pytest
from pydantic import ValidationError

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.runtime import (
    ActionKind, ArtifactReference, CapabilityInput, CapabilityResult, DecisionCategory,
    FoundationPolicy, InMemoryRunStore, LegacyCapability, LegacyCapabilityBridge,
    ResultStatus, RunMode, RuntimeAction, RuntimeEngine, RuntimeRun, RuntimeState,
    RuntimeWorkflow, UserDecisionRequest,
)
from drama_plugin.runtime.engine import validate_transition

ROOT = Path(__file__).resolve().parents[1]
CALL = RuntimeAction(kind=ActionKind.CALL_CAPABILITY, capability_key="local.read")


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("T1 must not open any network connection")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


def engine_for(handler, *, steps=(CALL,), replay_safe=True, policy=None, store=None):
    workflow = RuntimeWorkflow(workflow_id="offline:v1", steps=steps)
    return RuntimeEngine(LegacyCapabilityBridge({
        "local.read": LegacyCapability(handler, replay_safe=replay_safe),
    }), store=store, workflows={workflow.workflow_id: workflow},
        policies=None if policy is None else {policy.mode: policy})


async def success(inputs: CapabilityInput) -> CapabilityResult:
    return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(
        ArtifactReference(owner="CanonStore", artifact_ref=inputs.scope.work_id, version=1),
    ))


def create(engine, *, mode=RunMode.EXPERIMENT, run_id="run-1"):
    return engine.create_run(work_id="work-1", mode=mode, workflow_id="offline:v1", run_id=run_id)


@pytest.mark.parametrize("mode", list(RunMode))
def test_contract_mode_state_action_identity_and_reference_only_json(mode):
    engine = engine_for(success)
    run = create(engine, mode=mode)
    assert run.state == RuntimeState.PLANNED and run.scope.work_id == "work-1"
    assert run.mode == mode and mode.value.lower() in run.policy_id
    assert engine.next_action(run.run_id) == CALL
    assert RuntimeRun.model_validate_json(engine.serialize(run.run_id)) == run
    with pytest.raises(ValidationError):
        RuntimeRun.model_validate({**run.model_dump(), "work_content": {"script": "forbidden"}})
    with pytest.raises(ValidationError):
        CapabilityInput(run_id="r", operation_id="o", scope=run.scope, content={"scene": "forbidden"})
    with pytest.raises(ValidationError):
        ArtifactReference(owner="CanonStore", artifact_ref="", content={})
    with pytest.raises(ValidationError):
        run.mode = RunMode.PRODUCTION


@pytest.mark.parametrize("action", [
    {"kind": "CALL_CAPABILITY"},
    {"kind": "COMPLETE", "capability_key": "local.read"},
    {"kind": "REQUEST_USER_DECISION"},
    {"kind": "REQUEST_USER_DECISION", "decision": {"category": "HASH", "question": "hash?"}},
    {"kind": "WAIT_EXTERNAL"},
    {"kind": "STOP"},
])
def test_invalid_action_contract_rejected(action):
    with pytest.raises(ValidationError):
        RuntimeAction.model_validate(action)


@pytest.mark.parametrize("before,after", [
    (RuntimeState.PLANNED, RuntimeState.READY),
    (RuntimeState.READY, RuntimeState.RUNNING),
    (RuntimeState.RUNNING, RuntimeState.READY),
    (RuntimeState.READY, RuntimeState.SUCCEEDED),
])
def test_legal_transition(before, after):
    validate_transition(before, after)


@pytest.mark.parametrize("before,after", [
    (RuntimeState.PLANNED, RuntimeState.SUCCEEDED),
    (RuntimeState.SUCCEEDED, RuntimeState.RUNNING),
    (RuntimeState.WAITING_USER, RuntimeState.RUNNING),
    (RuntimeState.FAILED, RuntimeState.READY),
])
def test_invalid_transition_explicitly_rejected(before, after):
    with pytest.raises(ValueError, match="Invalid runtime transition"):
        validate_transition(before, after)


@pytest.mark.asyncio
async def test_plugin_owns_offline_loop_calls_existing_tool_once_without_canon_copy(monkeypatch):
    monkeypatch.setattr("drama_plugin.plugin.load_config", lambda _: DramaPluginConfig())
    data = MockDramaData()
    assert data.work is not None
    canonical_before = data.work.model_dump_json()
    plugin = DramaPlugin.load(ROOT, mock_data=data, legacy_reads=True)
    calls = []
    original = plugin.tools.invoke

    async def read(code, **arguments):
        assert code == "work.get_work"
        calls.append(arguments["work_id"])
        return await original(code, **arguments)

    monkeypatch.setattr(plugin.tools, "invoke", read)

    async def forbid_generation(*args, **kwargs):
        pytest.fail("T1 must never invoke generation")
    for name in ("generate_image", "generate_video"):
        monkeypatch.setattr(plugin.providers.production, name, forbid_generation)
    run = plugin.runtime.create_run(work_id=data.work.id, mode=RunMode.EXPERIMENT)
    assert plugin.runtime.next_action(run.run_id).capability_key == "work.get_work"
    completed = await plugin.runtime.run(run.run_id)
    assert completed.state == RuntimeState.SUCCEEDED
    assert calls == [data.work.id]
    assert (await plugin.runtime.run(run.run_id)) == completed
    assert calls == [data.work.id]
    snapshot = plugin.runtime.serialize(run.run_id)
    assert data.work.title not in snapshot and data.work.content["theme"] not in snapshot
    assert data.work.model_dump_json() == canonical_before
    assert completed.last_result.artifact_refs[0].version == data.work.version
    assert plugin.runtime.executor.legacy.lifecycle == "MIGRATION_ONLY"
    assert len(plugin.tools.list()) == 52 and len(plugin.skills.list()) == 57
    await plugin.aclose()


@pytest.mark.asyncio
async def test_internal_next_step_not_chosen_by_host_and_auto_maintenance_never_asks_user():
    calls = []

    async def read(inputs):
        calls.append(inputs.operation_id)
        return await success(inputs)
    engine = engine_for(read, steps=(CALL, RuntimeAction(
        kind=ActionKind.AUTO_MAINTENANCE, capability_key="local.read")))
    run = create(engine)
    completed = await engine.run(run.run_id)
    assert completed.state == RuntimeState.SUCCEEDED
    assert calls == ["run-1:0", "run-1:1"]
    assert completed.cursor == 2 and completed.last_result is not None
    assert "history" not in json.loads(engine.serialize(run.run_id))


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", list(RunMode))
async def test_round_trip_ready_resumes_same_action_without_replanning(mode):
    engine = engine_for(success)
    run = create(engine, mode=mode)
    ready = await engine.run(run.run_id, max_ticks=1)
    assert ready.state == RuntimeState.READY
    before = engine.next_action(run.run_id)
    restored_engine = engine_for(success)
    restored = restored_engine.restore(engine.serialize(run.run_id))
    assert restored == ready and restored_engine.next_action(run.run_id) == before
    assert (await restored_engine.run(run.run_id)).state == RuntimeState.SUCCEEDED
    terminal = restored_engine.serialize(run.run_id)
    final_engine = engine_for(success)
    final_engine.restore(terminal)
    assert (await final_engine.run(run.run_id)).state == RuntimeState.SUCCEEDED


def test_restore_rejects_policy_mix_changed_workflow_and_forged_completion():
    engine = engine_for(success)
    run = create(engine)
    snapshot = json.loads(engine.serialize(run.run_id))
    snapshot["mode"] = "PRODUCTION"
    with pytest.raises(ValueError, match="policy/workflow changed"):
        engine_for(success).restore(json.dumps(snapshot))
    changed = engine_for(success, steps=(CALL, CALL))
    with pytest.raises(ValueError, match="policy/workflow changed"):
        changed.restore(engine.serialize(run.run_id))
    snapshot = json.loads(engine.serialize(run.run_id))
    snapshot["state"] = "SUCCEEDED"
    with pytest.raises(ValueError, match="skip pending steps"):
        engine_for(success).restore(json.dumps(snapshot))
    with pytest.raises(ValueError, match="already exists"):
        engine.restore(engine.serialize(run.run_id))
    with pytest.raises(ValueError, match="Policy registry identity"):
        RuntimeEngine(engine.executor, policies={RunMode.EXPERIMENT: FoundationPolicy(RunMode.PRODUCTION)})


@pytest.mark.asyncio
async def test_completed_step_checkpoint_does_not_repeat_after_restore():
    calls = []

    async def read(inputs):
        calls.append(inputs.operation_id)
        return await success(inputs)
    engine = engine_for(read, steps=(CALL, CALL))
    run = create(engine)
    ready = await engine.run(run.run_id, max_ticks=2)
    assert ready.cursor == 1 and calls == ["run-1:0"]
    restored = engine_for(read, steps=(CALL, CALL))
    restored.restore(engine.serialize(run.run_id))
    assert (await restored.run(run.run_id)).state == RuntimeState.SUCCEEDED
    assert calls == ["run-1:0", "run-1:1"]


@pytest.mark.asyncio
async def test_shared_memory_store_serializes_concurrent_loop_owners():
    calls = []

    async def read(inputs):
        calls.append(inputs.operation_id)
        await asyncio.sleep(0)
        return await success(inputs)
    store = InMemoryRunStore()
    first, second = engine_for(read, store=store), engine_for(read, store=store)
    run = create(first)
    results = await asyncio.gather(first.run(run.run_id), second.run(run.run_id))
    assert all(r.state == RuntimeState.SUCCEEDED for r in results)
    assert calls == ["run-1:0"]


@pytest.mark.asyncio
@pytest.mark.parametrize("replay_safe", [True, False])
async def test_interrupted_call_restores_blocked_not_unknown_or_redispatched(replay_safe):
    started = asyncio.Event()

    async def pending(inputs):
        started.set()
        await asyncio.Event().wait()
        return await success(inputs)
    engine = engine_for(pending, replay_safe=replay_safe)
    run = create(engine)
    task = asyncio.create_task(engine.run(run.run_id))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert engine.store.load(run.run_id).state == RuntimeState.RUNNING
    calls = []

    async def recovered(inputs):
        calls.append(inputs.operation_id)
        return await success(inputs)
    resumed = engine_for(recovered, replay_safe=replay_safe)
    restored = resumed.restore(engine.serialize(run.run_id))
    assert restored.state == (RuntimeState.READY if replay_safe else RuntimeState.FAILED)
    result = await resumed.run(run.run_id)
    if replay_safe:
        assert result.state == RuntimeState.SUCCEEDED
        assert calls == ["run-1:0"]
    else:
        assert result.last_result.code == "INTERRUPTED_UNSAFE_CAPABILITY"
        assert not calls


@pytest.mark.asyncio
async def test_recoverable_failure_is_internal_bounded_and_not_a_user_decision():
    calls = []
    async def unavailable(inputs):
        calls.append(inputs.operation_id)
        return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="TEXT_TIMEOUT")
    engine = engine_for(unavailable)
    run = create(engine)
    failed = await engine.run(run.run_id)
    assert failed.state == RuntimeState.FAILED and failed.step_attempts == 2
    assert failed.last_result.code == "RETRY_LIMIT_REACHED"
    assert calls == ["run-1:0", "run-1:0"]
    with pytest.raises(ValueError, match="not waiting"):
        engine.decision_id(run.run_id)


@pytest.mark.asyncio
async def test_unexpected_internal_failure_is_hard_and_safe():
    calls = []
    async def broken(inputs):
        calls.append(inputs.operation_id)
        raise RuntimeError("secret/full Canon content must not persist")
    engine = engine_for(broken)
    run = create(engine)
    failed = await engine.run(run.run_id)
    assert failed.state == RuntimeState.FAILED and failed.step_attempts == 1
    assert failed.last_result.code == "CAPABILITY_EXECUTION_ERROR"
    assert "secret" not in engine.serialize(run.run_id)
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("accepted", [True, False])
async def test_user_decision_round_trip_resumes_only_matching_request(accepted):
    decision = RuntimeAction(kind=ActionKind.REQUEST_USER_DECISION,
        decision=UserDecisionRequest(category=DecisionCategory.ADOPTION, question="是否正式采纳这个版本？"))
    engine = engine_for(success, steps=(decision, CALL))
    run = create(engine)
    waiting = await engine.run(run.run_id)
    assert waiting.state == RuntimeState.WAITING_USER
    restored = engine_for(success, steps=(decision, CALL))
    restored.restore(engine.serialize(run.run_id))
    assert restored.next_action(run.run_id) == engine.next_action(run.run_id) == decision
    reference = ArtifactReference(owner="ReviewStore", artifact_ref="decision:1")
    with pytest.raises(ValueError, match="another step"):
        await restored.decide(run.run_id, decision_id="wrong", accepted=accepted, decision_ref=reference)
    await restored.decide(run.run_id, decision_id=restored.decision_id(run.run_id),
        accepted=accepted, decision_ref=reference)
    result = await restored.run(run.run_id)
    assert result.state == (RuntimeState.SUCCEEDED if accepted else RuntimeState.FAILED)


@pytest.mark.asyncio
async def test_external_wait_requires_matching_dependency_without_provider_state_copy():
    reference = ArtifactReference(owner="LocalDependency", artifact_ref="dependency:1")
    wait = RuntimeAction(kind=ActionKind.WAIT_EXTERNAL, external_ref=reference)
    engine = engine_for(success, steps=(wait, CALL))
    run = create(engine)
    assert (await engine.run(run.run_id)).state == RuntimeState.WAITING_EXTERNAL
    recovered = engine_for(success, steps=(wait, CALL))
    recovered.restore(engine.serialize(run.run_id))
    assert recovered.next_action(run.run_id) == wait
    with pytest.raises(ValueError, match="another dependency"):
        await recovered.record_external_result(run.run_id,
            external_ref=reference.model_copy(update={"artifact_ref": "other"}), result=await success(
                CapabilityInput(run_id="r", operation_id="o", scope=run.scope)))
    await recovered.record_external_result(run.run_id, external_ref=reference,
        result=CapabilityResult(status=ResultStatus.SUCCEEDED))
    assert (await recovered.run(run.run_id)).state == RuntimeState.SUCCEEDED


@pytest.mark.asyncio
async def test_unregistered_capability_cannot_fall_through_to_any_legacy_tool():
    bridge = LegacyCapabilityBridge({})
    engine = RuntimeEngine(bridge)
    run = engine.create_run(work_id="work-1", mode=RunMode.PRODUCTION)
    blocked = await engine.run(run.run_id)
    assert blocked.state == RuntimeState.FAILED
    assert blocked.last_result.code == "CAPABILITY_NOT_REGISTERED"
    with pytest.raises(ValueError, match="Only a blocked"):
        await engine.retry(run.run_id)


@pytest.mark.asyncio
async def test_maximum_run_identity_remains_valid_during_capability_execution():
    calls = []

    async def read(inputs):
        calls.append(inputs.operation_id)
        return await success(inputs)
    engine = engine_for(read)
    run = create(engine, run_id="r" * 256)
    assert (await engine.run(run.run_id)).state == RuntimeState.SUCCEEDED
    assert calls == [f"{run.run_id}:0"]
    with pytest.raises(ValidationError):
        create(engine, run_id="r" * 257)


@pytest.mark.parametrize("fault", ["planned_progress", "external_at_end", "external_reference", "inflight_no_attempt"])
def test_restore_rejects_inconsistent_checkpoint_context_before_inserting(fault):
    reference = ArtifactReference(owner="LocalDependency", artifact_ref="dependency:1")
    wait = RuntimeAction(kind=ActionKind.WAIT_EXTERNAL, external_ref=reference)
    engine = engine_for(success, steps=(CALL, wait))
    run = create(engine)
    snapshot = json.loads(engine.serialize(run.run_id))
    if fault == "planned_progress":
        snapshot["cursor"] = 1
    elif fault == "inflight_no_attempt":
        snapshot["state"] = "RUNNING"
    else:
        snapshot.update(state="WAITING_EXTERNAL", waitReason="EXTERNAL_RESULT_PENDING",
            cursor=2 if fault == "external_at_end" else 1,
            lastResult={"status": "WAITING_EXTERNAL", "externalRef": {
                "owner": "LocalDependency", "artifactRef": "different"}})
    recovered = engine_for(success, steps=(CALL, wait))
    with pytest.raises(ValueError):
        recovered.restore(json.dumps(snapshot))
    with pytest.raises(KeyError):
        recovered.store.load(run.run_id)


@pytest.mark.asyncio
async def test_user_decision_rejects_truthy_string_without_advancing():
    decision = RuntimeAction(kind=ActionKind.REQUEST_USER_DECISION,
        decision=UserDecisionRequest(category=DecisionCategory.ADOPTION, question="是否采纳？"))
    engine = engine_for(success, steps=(decision,))
    run = create(engine)
    waiting = await engine.run(run.run_id)
    with pytest.raises(ValueError, match="explicit boolean"):
        await engine.decide(run.run_id, decision_id=engine.decision_id(run.run_id),
            accepted="false", decision_ref=ArtifactReference(owner="ReviewStore", artifact_ref="decision:1"))
    assert engine.store.load(run.run_id) == waiting
