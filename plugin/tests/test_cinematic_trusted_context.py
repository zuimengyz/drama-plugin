"""Explicit trust crosses compilation/sealing boundaries without changing wire data."""
from types import SimpleNamespace
import pytest
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.hosts import http_video, specialized_asset
from drama_plugin.visual.video_selection import Cost,Evidence,Quality
from test_video_selection import evidence
from test_seedance_prompt_generator import cinematic_sample


def test_compile_and_seal_forward_external_authority(tmp_path,monkeypatch):
    req=cinematic_sample(tmp_path)
    authority={'workId':req.work_id,'assets':[]}
    req=req.model_copy(update={'authority_context':authority})
    work=SimpleNamespace(id=req.work_id)
    trusted=(SourcePin(key='test-external-approval',kind='DIRECTION',fingerprint='a'*64),)
    calls=[]
    def check(context,intent,current=None,*,approved_interpretation_refs=()):
        calls.append((current,approved_interpretation_refs))
        if current is not work or approved_interpretation_refs!=trusted:
            raise ValueError('USER_INTERPRETATION_APPROVAL_REQUIRED')
    monkeypatch.setattr(specialized_asset,'validate_authority_context',check)
    c=http_video.candidate(req,'seedance-2-mini',cost=Cost(components={'video':20,'audio':0,'references':0,'addons':0,'correction':0},evidence=evidence()),evidence=Evidence.model_validate(evidence()),quality=Quality())
    wire=http_video.compile_request(req,c,work=work,approved_interpretation_refs=trusted)
    seal=http_video.seal_execution(req,c,wire,{},work=work,approved_interpretation_refs=trusted)
    assert len(calls)==2 and all(x==(work,trusted) for x in calls)
    assert 'test-external-approval' not in str(wire)+str(seal)
    for refs in [(),(trusted[0].model_copy(update={'fingerprint':'b'*64}),)]:
        with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):
            http_video.compile_request(req,c,work=work,approved_interpretation_refs=refs)
    with pytest.raises(ValueError,match='MOVIE_VISUAL_AUTHORITY_MISMATCH'):
        http_video.compile_request(req,c,work=SimpleNamespace(id='other'),approved_interpretation_refs=trusted)
    with pytest.raises(ValueError,match='CURRENT_WORK_CONTEXT_REQUIRED'):
        http_video.compile_request(req,c,approved_interpretation_refs=trusted)
