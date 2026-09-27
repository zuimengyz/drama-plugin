import json
from copy import deepcopy
import httpx
import pytest
from drama_plugin.contracts.base import sha256_canonical as digest
from drama_plugin.hosts import work_save_preflight as p
from drama_plugin.visual.history_encoding import hydrate, encode, decode


def envelope(content):
    return {'jsonrpc':'2.0','id':123,'method':'tools/call','params':{'name':'work.save_work','arguments':{'work_id':'W','title':'中文 × title','description':None,'content':content}}}


def serialize(value):return httpx.Request('POST','http://localhost/mcp',json=value).content


def fixture():
    old={'request':{'prompt':'OLD 文学 '*4000},'fingerprint':'old'};active={'request':{'prompt':'CURRENT'},'fingerprint':'new'}
    ref=digest(old)
    return {'productionRoute':{'current':'frozen'},'continuityPacks':{'exact':'pack'},'productionStage':{
        'frames':{'current':active},'plan_fingerprint':digest({'current':active}),'history_frames':{ref:old},
        'attempts':[{'attempt_id':'old','frame_ref':ref,'status':'COMPLETED','ordinal':1,'reserved_credits':10,'credits':None,'provider_usage':{'credits':5}},
                    {'attempt_id':'active','frame_ref':digest(active),'status':'UNKNOWN','ordinal':2,'reserved_credits':12,'credits':None}],
        'stage':{'budget_credits':100},'pause':'WAIT','input_selections':{}}}


def test_under_limit_no_history_change():
    env=envelope(fixture());raw,report=p.prepare(env,serialize)
    assert raw==serialize(env) and report['archivesEncoded']==0


def test_adaptive_lossless_keeps_all_ledger_and_seals(monkeypatch):
    monkeypatch.setattr(p,'MAX_WORK_SAVE_REQUEST_BYTES',12000)
    content=fixture();original=deepcopy(content);raw,report=p.prepare(envelope(content),serialize)
    encoded=json.loads(raw)['params']['arguments']['content']
    assert len(raw)<12000-report['headroom'] and report['archivesEncoded']==1
    assert hydrate(encoded)==original and content==original
    from drama_plugin.visual.history import attempt_frame, compact
    stage=encoded['productionStage']
    assert attempt_frame(stage,stage['attempts'][0])==original['productionStage']['history_frames'][stage['attempts'][0]['frame_ref']]
    compact(stage)
    assert hydrate(encoded)==original
    assert encoded['productionStage']['attempts']==original['productionStage']['attempts']
    assert encoded['productionStage']['frames']==original['productionStage']['frames']
    assert report['attemptsSummarized']==0


@pytest.mark.parametrize('reason',['selected','unresolved','failed','current','no_history'])
def test_no_safe_history_fails_before_send(monkeypatch,reason):
    monkeypatch.setattr(p,'MAX_WORK_SAVE_REQUEST_BYTES',12000)
    c=fixture();s=c['productionStage']
    if reason=='selected':s['input_selections']={'x':{'attempt_id':'old'}}
    if reason=='unresolved':s['attempts'][0]['status']='RESERVED'
    if reason=='failed':s['attempts'][0]['status']='FAILED'
    if reason=='current':s['attempts'].reverse()
    if reason=='no_history':c['unrelatedSource']='x'*15000;s['history_frames']={}
    with pytest.raises(ValueError,match='NO_SAFE_HISTORY'):p.prepare(envelope(c),serialize)


def test_envelope_overhead_counts(monkeypatch):
    env=envelope({'small':'x'});size=len(serialize(env))
    monkeypatch.setattr(p,'MAX_WORK_SAVE_REQUEST_BYTES',size)
    assert len(p.prepare(env,serialize)[0])==size
    env['id']=1234
    with pytest.raises(ValueError):p.prepare(env,serialize)


def test_corrupt_archive_and_size_bomb_fail():
    v=encode({'x':'x'*100});assert decode(v)=={'x':'x'*100}
    for key,value in [('sha256','0'*64),('decoded_bytes',5),('decoded_bytes',0),('data','INVALID!')]:
        with pytest.raises(ValueError):decode({**v,key:value})


@pytest.mark.asyncio
async def test_actual_mcp_request_bounded_and_work_decode(tmp_path,monkeypatch):
    from drama_plugin.hosts.mcp_media import McpMediaSession
    from drama_plugin.providers.http.providers import _one
    from drama_plugin.contracts.creation import Work
    monkeypatch.setattr(p,'MAX_WORK_SAVE_REQUEST_BYTES',12000)
    config=tmp_path/'mcp.json';config.write_text(json.dumps({'mcpServers':{'drama-tools':{'url':'http://localhost/mcp'}}}))
    content=fixture();calls=[]
    def handler(request):
        calls.append(request);assert int(request.headers['content-length'])==len(request.content)<12000
        raw=json.loads(request.content);stored=raw['params']['arguments']['content']
        decoded=_one(Work,{'id':'W','title':'test','content':stored})
        assert decoded.content==content
        return httpx.Response(200,json={'jsonrpc':'2.0','id':raw['id'],'result':{'structuredContent':decoded.model_dump(mode='json')}})
    s=McpMediaSession(config);await s.client.aclose();s.client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        await s.rpc('tools/call',envelope(content)['params'])
        assert len(calls)==1
        bad=fixture();bad['unrelatedSource']='x'*20000
        with pytest.raises(ValueError):await s.rpc('tools/call',envelope(bad)['params'])
        assert len(calls)==1
    finally:await s.client.aclose()
