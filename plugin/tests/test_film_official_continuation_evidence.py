"""Official frame delivery must be exact and source-proved, without Provider calls."""
from copy import deepcopy
import pytest
import drama_plugin.film_storage.projection as projection


def evidence(monkeypatch):
    scope={'workId':'w','sceneId':'s','shotId':'k'}
    binding={'role':'FIRST_FRAME','scope':scope,'endpointFrameRef':{'owner':'continuation-frame','artifactRef':'frame','version':1},
        'media':{'mediaId':'frame-image','contentHash':'a'*64}}
    frame={'scope':scope,'runId':'prior-run','receiptRef':{'owner':'provider-receipt','artifactRef':'receipt','version':1},
        'media':{'mediaId':'frame-image','contentHash':'a'*64,'byteCount':42,'kind':'IMAGE'}}
    url='https://official.example/tail.png?exact=1'
    receipt={'scope':scope,'runId':'prior-run','state':'SUCCEEDED','provider':'seedance','lastFrameUrl':url}
    file={'media_type':'IMAGE','storage_state':'READY','content_hash':'a'*64,'file_size':42}
    records={'frame':frame,'receipt':receipt}
    monkeypatch.setattr(projection,'ledger_body',lambda store,ref,kind:(records[ref['artifactRef']],scope))
    return scope,binding,frame,receipt,file,url


def test_exact_official_tail_matches_retained_scope_receipt_and_bytes(monkeypatch):
    scope,binding,_,_,file,url=evidence(monkeypatch)
    assert projection.official_continuation_delivered(None,binding,file,url,scope)


@pytest.mark.parametrize('wrong', ['url','scope','role','hash','size','state','provider','run','pending','identity'])
def test_missing_or_different_official_evidence_remains_partial(monkeypatch,wrong):
    scope,binding,frame,receipt,file,url=evidence(monkeypatch)
    if wrong=='url':url+='2'
    elif wrong=='scope':scope=deepcopy(scope);scope['workId']='other-work'
    elif wrong=='role':binding['role']='REFERENCE'
    elif wrong=='hash':file['content_hash']='b'*64
    elif wrong=='size':file['file_size']=43
    elif wrong=='state':receipt['state']='UNKNOWN'
    elif wrong=='provider':receipt['provider']='other'
    elif wrong=='run':receipt['runId']='other-run'
    elif wrong=='pending':file['storage_state']='PENDING'
    elif wrong=='identity':frame['media']['mediaId']='other-image'
    assert not projection.official_continuation_delivered(None,binding,file,url,scope)


def test_absent_retained_frame_does_not_invent_delivery_proof(monkeypatch):
    scope,binding,_,_,file,url=evidence(monkeypatch)
    def absent(*args):raise projection.FilmStorageUnavailable('missing')
    monkeypatch.setattr(projection,'ledger_body',absent)
    assert not projection.official_continuation_delivered(None,binding,file,url,scope)
