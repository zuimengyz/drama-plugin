from copy import deepcopy
import pytest
from drama_plugin.contracts.creation import Work
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.work_patch import validate_patch

def fixture():
 s={'stage':{'id':'S'},'attempts':[],'frames':{},'plan_fingerprint':sha256_canonical({}),'production_route':{}}
 return Work(id='w',title='w',content={'keep':{'history':[1,2]},'productionStage':s,'productionRoute':{}})

def test_scoped_validation():
 w=fixture();s=deepcopy(w.content['productionStage']);s['pause']='CONTENT_REPLAN_REQUIRED'
 validate_patch(w,1,{'productionStage':s})
 assert w.content['keep']=={'history':[1,2]}
 for version,changes in [(0,{'productionStage':s}),(1,{'other':s}),(1,{'productionStage':{}})]:
  with pytest.raises(Exception):validate_patch(w,version,changes)
 s['plan_fingerprint']='a'*64
 with pytest.raises(ValueError,match='CAMPAIGN_PLAN_CHANGED'):validate_patch(w,1,{'productionStage':s})

@pytest.mark.asyncio
async def test_patch_http_envelope_limit_before_network():
 import httpx
 from drama_plugin.hosts.mcp_media import McpMediaSession
 from drama_plugin.hosts.work_save_preflight import MAX_WORK_SAVE_REQUEST_BYTES
 s=object.__new__(McpMediaSession);s.sequence=0;s.url='http://localhost/mcp';s.headers={}
 calls=[]
 def handler(r):calls.append(r);return httpx.Response(200,json={'result':{}})
 async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
  s.client=client
  with pytest.raises(ValueError,match='WORK_PATCH_REQUEST_TOO_LARGE'):
   await s.rpc('tools/call',{'name':'work.patch_work','arguments':{'work_id':'w','expected_version':1,'changes':{'productionStage':{'data':'x'*MAX_WORK_SAVE_REQUEST_BYTES}}}})
 assert not calls
 assert MAX_WORK_SAVE_REQUEST_BYTES==8388608
