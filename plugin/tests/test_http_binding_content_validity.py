from copy import deepcopy
from datetime import datetime,timezone
import pytest
from drama_plugin.visual.execution import validate_http_binding,validate_binding
from drama_plugin.visual.video_selection import Evidence


def fixture():
 execution={'transport':'HTTP','backend':{'provider':'seedance','backend_key':'official'},'capability':{'kind':'video_generation','model_key':'seedance-2-fast'}}
 d={'execution':execution,'execution_contract':{'schema_fingerprint':'schema'}}
 b={'execution':deepcopy(execution),'provider_schema_fingerprint':'schema','endpoint_fingerprint':'endpoint','operation':'video.create_task','authentication_status':'CONFIGURED_NOT_VERIFIED','evidence':{'source':'configured official adapter; offline schema contract','checked_at':'1999-01-01T00:00:00Z','expires_at':'1999-01-02T00:00:00Z','verified':True}}
 return d,b


def test_expired_static_attestation_valid_without_timestamp_mutation():
 d,b=fixture();old=deepcopy(b);validate_http_binding(d,b);assert b==old
 assert not Evidence.model_validate(b['evidence']).current(datetime(2199,1,1,tzinfo=timezone.utc))


@pytest.mark.parametrize('mutation',['schema','model','provider','mode','unverified'])
def test_changed_binding_identity_still_rejected(mutation):
 d,b=fixture()
 if mutation=='schema':b['provider_schema_fingerprint']='changed'
 if mutation=='model':b['execution']['capability']['model_key']='other'
 if mutation=='provider':b['execution']['backend']['provider']='other'
 if mutation=='mode':b['execution']['transport']='MCP'
 if mutation=='unverified':b['evidence']['verified']=False
 with pytest.raises(ValueError):validate_http_binding(d,b)


def test_ephemeral_mcp_discovery_retains_expiry():
 d,b=fixture();d['execution']['transport']='MCP';b['execution']=deepcopy(d['execution'])
 d['request']={'tool':'submit'};b.update(operation='submit',server_id='s',tool_name='submit',authenticated=True)
 with pytest.raises(ValueError,match='discovery expired'):validate_binding(d,b)


@pytest.mark.asyncio
@pytest.mark.parametrize('status,code',[(401,'AuthenticationError'),(403,'AccessDenied'),(400,'ModelNotOpen')])
async def test_explicit_provider_rejection_still_fail_closed(status,code):
 import httpx
 from test_official_video_providers import request,config,resolve,MODELS
 from drama_plugin.providers.video.adapters import ADAPTERS
 calls=[]
 def reply(req):
  calls.append(req)
  return httpx.Response(status,json={'error':{'code':code,'message':'offline authorization rejection'}})
 async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
  provider=ADAPTERS['seedance'](MODELS['seedance'],config('seedance'),resolve=resolve,client=client)
  task=await provider.create_task(request('seedance'),client_request_id='offline')
 assert task.status=='NOT_CREATED' and task.provider_task_id is None and task.error_code
 assert len(calls)==1
