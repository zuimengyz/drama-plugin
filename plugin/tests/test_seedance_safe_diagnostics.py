import json
import httpx
import pytest
from drama_plugin.providers.video.diagnostics import seedance_error
from drama_plugin.providers.video.base import SafeProviderError
from drama_plugin.contracts.video import ProviderTask
from test_official_video_providers import config
from drama_plugin.providers.video.adapters import SeedanceProvider


def test_error_allowlist_redacts_secrets_and_image_bytes():
    secret='actual-secret-key';blob='A'*1000
    response=httpx.Response(400,json={'error':{'code':'InvalidParameter','message':f'Invalid input data:image/png;base64,{blob} Bearer {secret} https://private/token abc '+blob},'request_id':'req-1','Authorization':secret},headers={'x-request-id':'req-2','set-cookie':secret})
    out=seedance_error(response,secret);text=json.dumps(out)
    assert out['http_status']==400 and out['official_error_code']=='InvalidParameter' and out['request_id']=='req-2'
    assert secret not in text and blob not in text and 'https://' not in text and 'data:image' not in text
    assert len(out['official_error_message'])<=500
    assert seedance_error(httpx.Response(400,text='raw secret '+secret),secret)=={'http_status':400}


@pytest.mark.asyncio
async def test_real_seedance_http_error_is_safe_and_durable():
    async def resolve(ref):return 'https://example.test/image.png'
    def handler(request):return httpx.Response(400,json={'error':{'code':'InputImageRejected','message':'Image source is not trusted.'}},headers={'x-tt-logid':'trace-123'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        p=SeedanceProvider('seedance-2-fast',config('seedance'),resolve=resolve,client=client)
        with pytest.raises(SafeProviderError) as exc:await p._http('POST','/contents/generations/tasks',body={'model':'offline'})
        assert exc.value.code=='HTTP_400' and not exc.value.retryable
        d=exc.value.diagnostics
        assert d=={'http_status':400,'official_error_code':'InputImageRejected','official_error_message':'Image source is not trusted.','request_id':'trace-123'}
        task=ProviderTask(provider='seedance',model='seedance-2-fast',client_request_id='offline',request_fingerprint='a'*64,status='NOT_CREATED',error_details=d)
        assert ProviderTask.model_validate(task.durable()).error_details==d

@pytest.mark.asyncio
async def test_create_task_retains_diagnostics_without_job():
    from test_seedance_prompt_generator import sample
    r=sample()
    async def resolve(ref):return 'https://example.test/image.png'
    def handler(request):return httpx.Response(400,json={'error':{'code':'InvalidParameter','message':'unsupported input'}},headers={'x-request-id':'req-safe'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        p=SeedanceProvider(r.continuity.primary_model,config('seedance'),resolve=resolve,client=client)
        task=await p.create_task(r,client_request_id='offline')
        assert task.status=='NOT_CREATED' and task.provider_task_id is None
        assert task.error_details['official_error_code']=='InvalidParameter'
        assert task.error_message=='unsupported input'
        assert task.durable()['errorDetails']['request_id']=='req-safe'
