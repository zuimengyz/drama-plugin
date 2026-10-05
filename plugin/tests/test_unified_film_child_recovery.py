"""A committed native child keeps one paid identity through parent process loss."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

import httpx
import pytest
from pydantic import SecretStr

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.video import CostEstimate
from drama_plugin.execution.live_transport import FinancialTerms, TargetHttpTransport
from drama_plugin.execution.review import HumanReviewer
from drama_plugin.generation.contracts import FinalPromptArtifact, GenerationPreparation
from drama_plugin.providers.video.adapters import SeedanceProvider
from drama_plugin.providers.video.registry import ProviderSettings
from drama_plugin.runtime.contracts import CapabilityInput, RuntimeState
from test_unified_mainline import MediaService, FAKE_SECRET, video
from test_unified_planning_recovery import create, load


@pytest.mark.asyncio
async def test_native_film_two_parent_process_interruptions_recover_same_child_task(tmp_path, monkeypatch, video):
    service = MediaService(video)
    vendor_calls = []

    def vendor(request):
        vendor_calls.append(request)
        if request.method == "POST":
            return httpx.Response(200, json={"id": "same-offline-task", "status": "running"})
        if request.url.host == "ark.cn-beijing.volces.com":
            return httpx.Response(200, json={"id": "same-offline-task", "status": "succeeded",
                "content": {"video_url": "https://result.invalid/proof.mp4"}})
        return httpx.Response(200, content=video.read_bytes())

    async def no_reference(_):
        raise AssertionError("No reference generation")

    def compose():
        plugin, authors = load(tmp_path, monkeypatch)
        plugin.providers.media = service.provider()
        plugin.execution.reviewer = HumanReviewer()
        adapter = SeedanceProvider("seedance-2-fast", ProviderSettings(
            base_url="https://ark.cn-beijing.volces.com/api/v3", api_key=SecretStr(FAKE_SECRET)),
            resolve=no_reference, client=httpx.AsyncClient(transport=httpx.MockTransport(vendor)))
        plugin.execution.transports["seedance"] = TargetHttpTransport(adapter, tmp_path / "ack",
            ledger=plugin.ledger, qualification_only=False)
        return plugin, authors

    monkeypatch.setenv("DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS", str(tmp_path))
    p, authors = compose()
    original = p.generation_capability.on_ready

    def mock_cost_owner(run_id, preparation_ref):
        prepared = p.generation_artifacts.get(preparation_ref, GenerationPreparation)
        final = p.generation_artifacts.get(prepared.final_prompt_ref, FinalPromptArtifact)
        digest = sha256_canonical(TargetHttpTransport.preview(prepared, final))
        now = datetime.now(timezone.utc)
        quote = CostEstimate(currency="CNY", amount=1, source="OFFLINE_COST_FIXTURE_NO_PAID_ACTION",
            checked_at=now, expires_at=now + timedelta(hours=1), request_fingerprint=digest)
        terms = FinancialTerms(preparation_ref=preparation_ref, profile=prepared.task.profile,
            wire_payload_hash=digest, cost_quote=quote, budget_microunits=1000000, max_paid_operations=1)
        p.ledger.put_index("media-proof-cost-terms", run_id, terms,
            scope=p.runtime.store.load(run_id).scope, once=True)
        if original:
            original(run_id, preparation_ref)

    p.generation_capability.on_ready = mock_cost_owner
    run = await p.runtime.run(create(p).run_id)
    cp = p.film.store.checkpoint(run.run_id)
    await p.decide_target_run(run.run_id, decision_id=p.runtime.decision_id(run.run_id),
        accepted=True, source_ref=cp.plan_ref)
    run = await p.runtime.run(run.run_id)
    await p.decide_target_run(run.run_id, decision_id=p.runtime.decision_id(run.run_id),
        accepted=True, source_ref=p.film.pending_decision(run.run_id)[1])
    run = await p.runtime.run(run.run_id)
    child_id = next(r.artifact_ref for r in run.last_result.artifact_refs if r.owner == "runtime")
    await p.decide_target_run(run.run_id, decision_id=p.runtime.decision_id(run.run_id),
        accepted=True, source_ref=p.generation_artifacts.prepared(child_id))
    run = await p.runtime.run(run.run_id)
    child = p.runtime.store.load(child_id)
    assert run.state == child.state == RuntimeState.WAITING_EXTERNAL
    fixed_external = child.last_result.external_ref
    fixed_child_attempts = child.step_attempts
    fixed_parent_attempts = run.step_attempts
    fixed_revision = run.execution_revision
    assert len([request for request in vendor_calls if request.method == "POST"]) == 1
    assert authors.calls == ["canon", "direction", "professional"]

    class ProcessExit(BaseException):
        pass

    for interruption in range(2):
        current, restored_authors = (p, authors) if interruption == 0 else compose()
        execute = current.runtime.executor.execute

        async def exit_before_parent_handler(key, inputs):
            if key == "film.execute:v1":
                raise ProcessExit()
            return await execute(key, inputs)

        monkeypatch.setattr(current.runtime.executor, "execute", exit_before_parent_handler)
        with pytest.raises(ProcessExit):
            await current.resume_source_film_run(run.run_id)
        crashed = current.runtime.store.load(run.run_id)
        # The first interruption happens during reconciliation (already durable
        # WAIT); the second happens after a fresh Runtime starts the same action.
        assert crashed.state in {RuntimeState.WAITING_EXTERNAL, RuntimeState.RUNNING}
        assert crashed.step_attempts == fixed_parent_attempts
        assert crashed.execution_revision == fixed_revision
        same_child = current.runtime.store.load(child_id)
        assert same_child.state == RuntimeState.WAITING_EXTERNAL
        assert same_child.last_result.external_ref == fixed_external
        assert same_child.step_attempts == fixed_child_attempts
        assert current.film.inspect_media_execution(CapabilityInput(run_id=run.run_id,
            operation_id=f"{run.run_id}:5", scope=run.scope)).completed
        if interruption:
            assert restored_authors.calls == []
        monkeypatch.setattr(current.runtime.executor, "execute", execute)
        # Force a genuine dispatch crash on the second attempt, through the
        # public result API; no ledger/checkpoint mutation or budget reset.
        if interruption == 0:
            from drama_plugin.runtime.contracts import CapabilityResult, RecoveryClass, ResultStatus
            await current.runtime.record_external_result(run.run_id, external_ref=run.last_result.external_ref,
                result=CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="PARENT_LOCAL_COMMIT_PENDING",
                    recovery_class=RecoveryClass.AUTO_RECOVER))

    # A new interpreter reconstructs the exact committed child witness solely
    # from durable owner state, before any provider query is resumed.
    script = """
import json, pathlib, pytest, sys
from test_unified_planning_recovery import load
from drama_plugin.runtime.contracts import CapabilityInput, RuntimeState
plugin, authors=load(pathlib.Path(sys.argv[1]),pytest.MonkeyPatch())
run=plugin.runtime.store.load('native-film')
inspection=plugin.film.inspect_media_execution(CapabilityInput(run_id=run.run_id,operation_id=f'{run.run_id}:5',scope=run.scope))
assert inspection.completed and inspection.revision==run.execution_revision
child=plugin.runtime.store.load(plugin.film.store.checkpoint(run.run_id).units[0].generation_run_id)
assert child.state==RuntimeState.WAITING_EXTERNAL and not authors.calls
print(json.dumps({'child':child.run_id,'attempts':child.step_attempts,'external':child.last_result.external_ref.model_dump()}))
"""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join((str(Path(__file__).parent), str(Path(__file__).parents[1] / "src")))
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path)], env=environment,
        capture_output=True, text=True, check=True)
    restored = json.loads(result.stdout)
    assert restored["child"] == child_id and restored["attempts"] == fixed_child_attempts
    assert restored["external"] == fixed_external.model_dump()

    resumed, restored_authors = compose()
    finished = await resumed.resume_source_film_run(run.run_id)
    child = resumed.runtime.store.load(child_id)
    assert finished.state == child.state == RuntimeState.WAITING_USER, child.model_dump_json()
    assert child.last_result.user_decision.category.value == "ART_APPROVAL"
    assert resumed.film.store.checkpoint(run.run_id).units[0].generation_run_id == child_id
    assert not restored_authors.calls
    assert len([request for request in vendor_calls if request.method == "POST"]) == 1
    assert len([request for request in vendor_calls if request.method == "GET" and "same-offline-task" in str(request.url)]) == 1
    assert service.imports == 1
