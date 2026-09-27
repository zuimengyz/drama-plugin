"""Offline lifecycle checks: planned duties are never execution references."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from drama_plugin.contracts.video import VideoRequest
from drama_plugin.hosts.http_video import candidate, VideoProviderHost
from drama_plugin.visual import production
from drama_plugin.visual.video_selection import Evidence, ProductionRoute, qualify_route, route_input_gate
from test_production_route import route
from test_video_selection import fixture, evidence
from test_official_video_providers import request, ref, with_refs, config


def planned(tmp_path: Path) -> ProductionRoute:
    r = route(tmp_path)  # type: ignore[no-untyped-call]
    req, *_ = fixture(tmp_path)  # type: ignore[no-untyped-call]
    c = candidate(req, 'seedance-2-fast', cost=r.candidate.cost,
                  evidence=Evidence.model_validate(evidence()), quality=r.candidate.quality)  # type: ignore[no-untyped-call]
    raw = r.model_dump(mode='json')
    raw['candidate'] = c.model_dump(mode='json')
    raw['requirements'].pop('language')
    raw['execution'] = {'transport': 'HTTP', 'backend': {'provider': 'seedance', 'backend_key': 'official'},
                        'capability': {'kind': 'video_generation', 'model_key': c.model}}
    return ProductionRoute.model_validate(raw)


def materialized() -> VideoRequest:
    r = request()  # type: ignore[no-untyped-call]
    r.continuity.primary_model = 'seedance-2-fast'
    first = ref()  # type: ignore[no-untyped-call]
    return with_refs(r, [first], input_mode='image_to_video', first_frame=first)  # type: ignore[no-untyped-call,no-any-return]


def test_planning_admits_image_but_not_video(tmp_path: Path) -> None:
    r = planned(tmp_path)
    assert qualify_route(r)['eligible']
    assert route_input_gate(r, 'I', 'START').source_media_id is None
    assert not qualify_route(r, execution_target='S1')['eligible']
    frame = {'schema': 'video-decision-v1', 'spec': {'shot_id': 'S1'}}
    with pytest.raises(ValueError, match='ROUTE_EXPIRED_OR_INCOMPLETE'):
        production._route_frame_gate({'production_route': r.model_dump(mode='json')}, frame)


@pytest.mark.parametrize('mutation', ['reuse', 'inactive', 'reference', 'fake_source', 'no_duty', 'extra_request'])
def test_only_explicit_new_first_frame_can_defer(tmp_path: Path, mutation: str) -> None:
    raw = planned(tmp_path).model_dump(mode='json')
    if mutation == 'reuse': raw['inputs'][0].update(preparation='REUSE', source_media_id='existing')
    if mutation == 'inactive': raw['inputs'][0]['active'] = False
    if mutation == 'reference': raw['inputs'][0]['role'] = 'REFERENCE'
    if mutation == 'fake_source': raw['inputs'][0]['source_media_id'] = 'placeholder'
    if mutation == 'no_duty': raw['inputs'] = []
    if mutation == 'extra_request': raw['requirements']['video_requests'] = {'OTHER': materialized().model_dump(mode='json')}
    assert not qualify_route(ProductionRoute.model_validate(raw))['eligible']


def test_materialized_request_and_sequential_targets(tmp_path: Path) -> None:
    raw = planned(tmp_path).model_dump(mode='json')
    raw['requirements']['video_requests'] = {'S1': materialized().model_dump(mode='json')}
    r = ProductionRoute.model_validate(raw)
    assert qualify_route(r)['eligible']
    assert qualify_route(r, execution_target='S1')['eligible']
    # Later fresh targets need not exist before executing the reviewed first one.
    raw['video_targets'].append('S2')
    duty = deepcopy(raw['inputs'][0]); duty.update(target_id='I2', for_targets=['S2'])
    raw['inputs'].append(duty)
    r = ProductionRoute.model_validate(raw)
    assert qualify_route(r, execution_target='S1')['eligible']
    assert not qualify_route(r, execution_target='S2')['eligible']
    assert not qualify_route(r, execution_target='OTHER')['eligible']


@pytest.mark.parametrize('missing', ['first_frame', 'media_id', 'version', 'content_hash', 'review_ref'])
def test_execution_contract_never_accepts_incomplete_reference(missing: str) -> None:
    raw = materialized().model_dump()
    if missing == 'first_frame': raw['first_frame'] = None
    else: raw['first_frame'].pop(missing)
    with pytest.raises(ValueError): VideoRequest.model_validate(raw)


@pytest.mark.asyncio
@pytest.mark.parametrize('state', ['valid', 'missing', 'cross_work', 'wrong_hash'])
async def test_real_host_resolves_only_owned_materialized_media(tmp_path: Path, state: str) -> None:
    r = materialized()
    class Memory:
        async def get_work(self, _: str) -> Any:
            return SimpleNamespace(content={'continuityPacks': {r.continuity.segment_id: r.continuity.model_dump(mode='json', by_alias=True)}})
    class Media:
        async def get_media(self, _: str) -> Any:
            if state == 'missing': raise ValueError('MEDIA_NOT_FOUND')
            return SimpleNamespace(id=r.first_frame.media_id, content={'reviewStatus':'PASS'}, work_id='OTHER' if state == 'cross_work' else 'W',  # type: ignore[union-attr]
                content_hash='c'*64 if state == 'wrong_hash' else r.first_frame.content_hash,  # type: ignore[union-attr]
                media_type=SimpleNamespace(value='IMAGE'))
        async def resolve_media(self, _: str) -> Any:
            return SimpleNamespace(media_id=r.first_frame.media_id, url='https://media.example.test/reviewed-image.png')  # type: ignore[union-attr]
    host = VideoProviderHost(Memory(), Media(), None, tmp_path, configuration={'seedance': config('seedance')})  # type: ignore[no-untyped-call]
    provider = await host._provider('W', {'provider': 'seedance', 'model': 'seedance-2-fast', 'videoRequest': r.model_dump(mode='json')})
    try:
        if state == 'valid':
            _, urls = await provider.materialize(r)
            assert urls[r.first_frame.media_id].startswith('https://')  # type: ignore[union-attr]
        else:
            with pytest.raises(ValueError, match='MEDIA_NOT_FOUND|CANONICAL_REFERENCE_MEDIA_CHANGED'):
                await provider.materialize(r)
    finally:
        await provider.aclose()
