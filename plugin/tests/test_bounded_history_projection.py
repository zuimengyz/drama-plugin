import json
from copy import deepcopy
import httpx
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.hosts import work_save_preflight as pre
from drama_plugin.visual.history_encoding import hydrate,decode,ENCODING

def serialize(v):return httpx.Request('POST','http://localhost',json=v).content

def fixture():
 frames=[{'request':{'prompt':str(i)*2000},'fingerprint':str(i)} for i in range(4)]
 s={'frames':{'current':{'exact':'current'}},'attempts':[{'attempt_id':'live','status':'RESERVED','credits':None,'reserved_credits':13}], 'plan_fingerprint':'pin', 'history_frames':{fp(f):f for f in frames},'route_revisions':[{'previous_frame_ref':fp(f),'reason':'superseded','ordinal':i} for i,f in enumerate(frames)],'pause':None,'budget':350}
 return {'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'work.patch_work','arguments':{'work_id':'w','expected_version':178,'changes':{'productionStage':s}}}}

def test_newest_prefix_bounded_and_losslessly_recoverable(monkeypatch):
 e=fixture();before=deepcopy(e);monkeypatch.setattr(pre,'MAX_WORK_SAVE_REQUEST_BYTES',6500)
 raw,r=pre.prepare(e,serialize);out=json.loads(raw)['params']['arguments']['changes']
 assert len(raw)<=6500 and 0<r['fullHistoryDepthRetained']<4
 assert hydrate(out)==before['params']['arguments']['changes'] and e==before
 archive=out['productionStage']['history_frames'];keys=list(archive)
 count=r['fullHistoryDepthRetained']
 assert all(archive[k].get('encoding')!=ENCODING for k in keys[-count:])
 for k in keys[:-count]:assert archive[k]['encoding']==ENCODING
 # The next oldest full item cannot fit; no fixed history-count cap.
 blocked=keys[-count-1];archive[blocked]=decode(archive[blocked])
 candidate=deepcopy(e);candidate['params']['arguments']['changes']=out
 assert len(serialize(candidate))>6500

def test_current_unresolved_snapshot_never_encoded(monkeypatch):
 e=fixture();s=e['params']['arguments']['changes']['productionStage'];ref=list(s['history_frames'])[-1]
 s['attempts'][0]['frame_ref']=ref
 monkeypatch.setattr(pre,'MAX_WORK_SAVE_REQUEST_BYTES',6500)
 raw,_=pre.prepare(e,serialize);out=json.loads(raw)['params']['arguments']['changes']['productionStage']
 assert out['history_frames'][ref]==s['history_frames'][ref]
 assert out['attempts']==s['attempts'] and out['frames']==s['frames'] and out['budget']==350

def test_normal_patch_is_byte_identical():
 e=fixture();raw,r=pre.prepare(e,serialize)
 assert raw==serialize(e) and r['archivesEncoded']==0


import pytest
@pytest.mark.asyncio
async def test_actual_mcp_patch_applies_projection_before_network(monkeypatch):
    from drama_plugin.hosts.mcp_media import McpMediaSession
    e=fixture();monkeypatch.setattr(pre,'MAX_WORK_SAVE_REQUEST_BYTES',6500)
    seen=[]
    def receive(request):
        seen.append(request.content)
        return httpx.Response(200,json={'result':{}})
    session=object.__new__(McpMediaSession);session.sequence=0;session.url='http://localhost/mcp';session.headers={}
    async with httpx.AsyncClient(transport=httpx.MockTransport(receive)) as client:
        session.client=client
        await session.rpc(e['method'],e['params'])
    assert len(seen)==1 and len(seen[0])<=6500
    projected=json.loads(seen[0])['params']['arguments']['changes']
    assert hydrate(projected)==e['params']['arguments']['changes']
    assert session.last_work_patch_bytes==len(seen[0])
