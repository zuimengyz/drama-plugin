"""Offline request/real-file QA regressions. No live provider calls."""
import socket
from pathlib import Path

import pytest
from pydantic import ValidationError

from drama_plugin.config.video_route import VideoRoutePolicy
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.execution.contracts import ProviderRequest
from drama_plugin.execution.live_transport import wire_payload
from drama_plugin.execution.media import LocalMediaStore, inspect
from drama_plugin.generation.contracts import ExecutionProfile
from drama_plugin.generation.operation import resolve_profile
from drama_plugin.providers.video.registry import automatic_duration_bounds_ms
from test_target_execution import recorded_video
from test_unified_mainline import video, no_external_calls


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('No network or paid generation in duration regression')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)
    monkeypatch.setenv('DRAMA_PLUGIN_ROUTE_VIDEO_MODEL', 'seedance-2-standard')


def profile(**kwargs):
    return resolve_profile(model='seedance-2-standard', resolution='720p', ratio='16:9',
                           native_audio=True, policy=VideoRoutePolicy(), **kwargs)


def wire(value):
    request = ProviderRequest(model=value.model, input_mode=value.mode,
        prompt_text='手把最后一枚钱放在木台上。', duration_ms=value.requested_duration_ms,
        native_audio='REQUIRED', profile=value, return_last_frame=True)
    return wire_payload(request, provider=value.provider, resolution=value.resolution,
                        aspect_ratio=value.aspect_ratio)


def test_omitted_duration_explicitly_uses_vendor_auto_and_maximum_budget_bound():
    value = profile()
    assert value.duration_mode == 'AUTO'
    assert value.requested_duration_ms == 15000
    body = wire(value)
    assert body['duration'] == -1 and body['generate_audio'] is True
    assert body['model'] == 'doubao-seedance-2-0-260128'
    assert 'frames' not in body
    restored = ExecutionProfile.model_validate_json(value.model_dump_json(by_alias=True))
    assert restored == value and wire(restored) == body
    assert profile(duration_ms=None) == value


def test_fixed_duration_and_historical_serialization_are_unchanged():
    value = profile(duration_ms=8000)
    assert wire(value)['duration'] == 8
    original = value.model_dump(mode='json', by_alias=True, exclude={'duration_mode'})
    assert 'durationMode' not in original and 'duration_mode' not in original
    restored = ExecutionProfile.model_validate(original)
    assert restored.model_dump(mode='json', by_alias=True) == original
    assert sha256_canonical(restored) == sha256_canonical(original)
    assert sha256_canonical(wire(profile(duration_ms=15000))) != sha256_canonical(wire(profile()))


@pytest.mark.parametrize('duration', [0, -1, 35000, 4500])
def test_unsupported_fixed_duration_is_not_silently_replaced(duration):
    with pytest.raises(ValueError, match='REQUEST_UNSUPPORTED'):
        profile(duration_ms=duration)


def test_auto_cannot_understate_budget_or_claim_another_provider():
    base = profile().model_dump()
    for changes in ({'requested_duration_ms': 4000}, {'provider': 'minimax'},
                    {'model': 'minimax-h3'}):
        with pytest.raises((ValueError, ValidationError), match='AUTO_DURATION'):
            ExecutionProfile.model_validate({**base, **changes})
    with pytest.raises(ValueError, match='AUTO_DURATION_UNSUPPORTED'):
        automatic_duration_bounds_ms('minimax-h3')


@pytest.mark.parametrize('model', ['seedance-2-standard', 'seedance-2-fast', 'seedance-2-mini'])
def test_seedance_2_family_uses_same_documented_range(model, monkeypatch):
    monkeypatch.setenv('DRAMA_PLUGIN_ROUTE_VIDEO_MODEL', model)
    value = resolve_profile(model=model, resolution='720p', ratio='16:9',
                            native_audio=True, policy=VideoRoutePolicy())
    assert automatic_duration_bounds_ms(model) == (4000, 15000)
    assert wire(value)['duration'] == -1


def test_actual_six_second_media_passes_auto_but_not_fixed_fifteen_seconds(tmp_path, recorded_video):
    store = LocalMediaStore(tmp_path / 'media')
    media = store.retain(Path(recorded_video.locator).read_bytes(), kind='VIDEO', mime='video/mp4')
    observed, failures = inspect(store, media, duration_ms=15000,
        duration_bounds_ms=(4000, 15000), tolerance_ms=100, audio_expected=True)
    assert observed.video_duration_ms == 6000 and failures == ()
    _, fixed_failures = inspect(store, media, duration_ms=15000,
        tolerance_ms=100, audio_expected=True)
    assert 'RESULT_DURATION_MISMATCH' in fixed_failures
    _, outside = inspect(store, media, duration_ms=15000,
        duration_bounds_ms=(8000, 15000), tolerance_ms=100, audio_expected=True)
    assert 'RESULT_DURATION_OUT_OF_RANGE' in outside


@pytest.mark.asyncio
async def test_native_compiler_transport_and_review_preserve_automatic_profile(tmp_path, monkeypatch, video):
    """Exercise real native owners; the single HTTP POST ends in MockTransport."""
    import json
    from test_unified_mainline import load, task_for, prepare_goal
    from drama_plugin.persistence.review import UserDecisionRecord
    from drama_plugin.runtime.contracts import ArtifactReference, DecisionCategory, RuntimeState
    from drama_plugin.execution.contracts import ExecutionOperation, TechnicalMediaReview
    from drama_plugin.generation.contracts import GenerationPreparation, FinalPromptArtifact
    from drama_plugin.execution.live_transport import TargetHttpTransport

    monkeypatch.setenv('DRAMA_PLUGIN_ROUTE_VIDEO_MODEL', 'seedance-2-fast')
    p, package, service, calls = load(tmp_path, monkeypatch, video)
    try:
        original_package = package.model_dump_json()
        original = task_for(p, package)
        auto = resolve_profile(model=original.profile.model, resolution='720p', ratio='16:9',
                               native_audio=True, policy=p.operation_resolver.policy)
        material = dict(p.creative_versions.objects.read_ref(original.owners.rights_pin))
        material['profile'] = auto.model_dump(mode='json', by_alias=True)
        material['processingScope'] = {**material['processingScope'], 'durationSeconds': 15}
        request = ArtifactReference(owner='source-rights', artifact_ref='offline-auto-duration-rights', version=1)
        old, scope, _ = p.ledger.get_artifact('user-decision', original.owners.rights_decision_ref)
        decision = p.reviews.put_user_decision(UserDecisionRecord.seal(run_id=old['runId'], scope=scope,
            decision_id=old['runId']+':automatic-duration', category=DecisionCategory.ADOPTION,
            accepted=True, source_ref=request))
        material.update(requestRef=request.model_dump(mode='json', by_alias=True),
                        decisionRef=decision.model_dump(mode='json', by_alias=True))
        rights = p.creative_versions.objects.put('offline-auto-duration-rights', material)
        owners = original.owners.model_copy(update={'rights_pin': rights,
            'rights_request_ref': request, 'rights_decision_ref': decision})
        task = original.model_copy(update={'profile': auto, 'owners': owners})
        waiting = await prepare_goal(p, package, task)
        assert waiting.state == RuntimeState.WAITING_USER and waiting.cursor == 9, waiting.model_dump()
        prepared = p.generation_artifacts.get(p.generation_artifacts.prepared(waiting.run_id), GenerationPreparation)
        final = p.generation_artifacts.get(prepared.final_prompt_ref, FinalPromptArtifact)
        assert final.matches_task(prepared.task)
        assert prepared.task.profile.duration_mode == 'AUTO'
        assert TargetHttpTransport.preview(prepared, final, ledger=p.ledger)['duration'] == -1
        posts = [r for r in calls if r.method == 'POST']
        assert len(posts) == 1 and json.loads(posts[0].content)['duration'] == -1
        with p.ledger.transaction() as db:
            row = db.execute('SELECT operation_ref_json FROM production_operation WHERE operation_ref_json IS NOT NULL').fetchone()
        op = p.execution.store.get(ArtifactReference.model_validate_json(row[0]), ExecutionOperation)
        cp = p.execution.store.checkpoint(op.artifact_reference())
        review = p.execution.store.get(cp.progress.current_video_technical_ref, TechnicalMediaReview)
        assert review.outcome == 'PASS' and review.observation.video_duration_ms == 4000
        assert package.model_dump_json() == original_package
    finally:
        await p.aclose()
