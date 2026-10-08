"""NON_NORMATIVE fixtures; fabricated audio/events, never live attestation."""
import json
from pathlib import Path
from hashlib import sha256
import uuid
import wave
import httpx
import pytest
from drama_plugin.config import load_config
from drama_plugin.config.audio_semantic import QwenOmniConfig
from drama_plugin.exceptions import ConfigurationError
from drama_plugin.providers.http.qwen_omni import BailianQwenOmniAudioSemanticProvider, BLIND_AUDIO_PROMPT
from drama_plugin.providers.base.audio_semantic import AudioSemanticInput
from drama_plugin.hosts.audio_semantic import observe_audio, align_for_user_review, attested_audio_facet

P='DRAMA_PLUGIN_PROVIDER_'

def event():return dict(start=.5,end=1.5,description='A brief sound',speakerHint='UNKNOWN',confidence='MEDIUM',uncertainty='Source uncertain')
def body():return dict(speechEvents=[],performanceSoundEvents=[],environmentEvents=[],otherSoundEvents=[event()],subjectiveAudioChanges=[],uncertainObservations=['UNKNOWN source'])

@pytest.fixture
def source(tmp_path):
    path=tmp_path/'fixture.wav'
    with wave.open(str(path),'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(bytes(64000))
    return AudioSemanticInput(path,'a'*64,sha256(path.read_bytes()).hexdigest(),3.,5.,8.)

def provider(handler,**kwargs):
    # Generated mock-only opaque value, not a real service credential.
    config=QwenOmniConfig(api_key=uuid.uuid4().hex,base_url='https://example.test/v1',**kwargs)
    return BailianQwenOmniAudioSemanticProvider(config,transport=httpx.MockTransport(handler))

def success(data=None):
    return httpx.Response(200,json={'id':'mock-request','choices':[{'message':{'content':json.dumps(data or body())}}],'usage':{'total_tokens':12}})

def test_off_does_not_need_key():
    assert load_config(environment={}).providers.audio_semantic.mode=='off'
    assert load_config(environment={P+'AUDIO_SEMANTIC_MODE':'off'}).services.qwen_omni.model=='qwen3.8-omni-flash'

@pytest.mark.parametrize('missing',['API_KEY','BASE_URL'])
def test_enabled_config_requires_pair(missing):
    env={P+'AUDIO_SEMANTIC_MODE':'bailian_qwen_omni',P+'QWEN_OMNI_API_KEY':uuid.uuid4().hex,P+'QWEN_OMNI_BASE_URL':'https://example.test/v1'}
    del env[P+'QWEN_OMNI_'+missing]
    with pytest.raises(ConfigurationError):load_config(environment=env)

def test_env_override_and_secret_repr():
    secret=uuid.uuid4().hex
    env={P+'AUDIO_SEMANTIC_MODE':'bailian_qwen_omni',P+'QWEN_OMNI_API_KEY':secret,P+'QWEN_OMNI_BASE_URL':'https://example.test/v1',P+'QWEN_OMNI_MODEL':'model-override',P+'QWEN_OMNI_REASONING_EFFORT':'low',P+'QWEN_OMNI_USE_MULTICHANNEL':'true'}
    c=load_config(environment=env).services.qwen_omni
    assert (c.model,c.reasoning_effort,c.use_multichannel)==('model-override','low',True)
    assert secret not in repr(c) and secret not in c.model_dump_json()
    env[P+'QWEN_OMNI_BASE_URL']='http://invalid'
    with pytest.raises(ConfigurationError) as error:load_config(environment=env)
    assert secret not in str(error.value) and error.value.__suppress_context__

def test_no_global_dashscope_fallback():
    with pytest.raises(ConfigurationError):load_config(environment={P+'AUDIO_SEMANTIC_MODE':'bailian_qwen_omni',P+'QWEN_OMNI_BASE_URL':'https://example.test/v1','DASHSCOPE_API_KEY':uuid.uuid4().hex})


@pytest.mark.asyncio
async def test_subtitle_transcription_uses_same_config_audio_and_complete_sse(source):
    import base64
    def handler(request):
        payload=json.loads(request.content)
        assert payload['model']=='configured-omni' and payload['reasoning_effort']=='low'
        assert payload['use_multichannel'] is True and payload['modalities']==['text']
        assert payload['max_tokens']==2048 and payload['stream_options']['include_usage']
        content=payload['messages'][0]['content']
        assert base64.b64decode(content[0]['input_audio']['data'].split(',',1)[1])==source.audio_path.read_bytes()
        assert 'verbatim' in content[1]['text'] and '(ru)' in content[1]['text']
        assert 'speechEvents' not in content[1]['text'] and 'response_format' not in payload
        chunks=[{'choices':[{'index':0,'delta':{'reasoning_content':'not transcript','content':'Я всегда '}}]},
            {'choices':[{'index':0,'delta':{'content':'был смешон.'}},{'index':1,'delta':{'content':'not selected'}}]},
            {'choices':[],'usage':{'prompt_tokens':3,'completion_tokens':4}}]
        return httpx.Response(200,headers={'content-type':'text/event-stream'},text='\n'.join('data: '+json.dumps(c) for c in chunks)+'\ndata: [DONE]\n')
    p=provider(handler,model='configured-omni',reasoning_effort='low',use_multichannel=True)
    r=await p.transcribe_audio(source,language='ru');await p.aclose()
    assert r.status=='AUDIO_TRANSCRIPTION_CANDIDATE' and r.observation is None
    assert r.transcript['text']=='Я всегда был смешон.' and r.transcript['verification']=='UNVERIFIED'
    assert r.receipt['usage']['completion_tokens']==4 and r.receipt['semanticProviderCalls']==1


@pytest.mark.asyncio
async def test_invalid_auxiliary_observation_preserves_independent_speech(source):
    data=body();data['speechEvents']=[{**event(),'description':'Я всегда был смешон.'}]
    data['environmentEvents']=[{'start':0,'end':9,'description':'Out of window, missing fields'}]
    p=provider(lambda r:success(data));r=await p.observe_audio(source);await p.aclose()
    assert r.status=='AUDIO_SEMANTIC_RESPONSE_INVALID' and r.observation is None
    assert r.receipt['failureCategory']=='AUXILIARY_OBSERVATION_VALIDATION_FAILED'
    assert r.transcript['segments'][0]['start']==3.5 and r.transcript['text']=='Я всегда был смешон.'
    assert r.transcript['verification']=='UNVERIFIED' and r.receipt['semanticProviderCalls']==1


@pytest.mark.asyncio
async def test_subtitle_plain_non_json_and_text_parse_failure_are_distinct(source):
    p=provider(lambda r:httpx.Response(200,json={'choices':[{'message':{'content':'Я был смешон.'}}]}))
    r=await p.transcribe_audio(source,language='ru');await p.aclose()
    assert r.transcript['text']=='Я был смешон.'
    p=provider(lambda r:httpx.Response(200,json={'choices':[]}))
    r=await p.transcribe_audio(source,language='ru');await p.aclose()
    assert r.transcript is None and r.receipt['failureCategory']=='TEXT_RESPONSE_PARSE_FAILED'

@pytest.mark.asyncio
async def test_request_absolute_timeline_and_pending_fusion(source):
    def handler(request):
        payload=json.loads(request.content)
        assert payload['model']=='qwen3.8-omni-flash' and payload['reasoning_effort']=='none'
        assert payload['use_multichannel'] is False and payload['modalities']==['text']
        assert 'response_format' not in payload and 'tools' not in payload
        content=payload['messages'][0]['content']
        assert content[0]['input_audio']['data'].startswith('data:audio/wav;base64,')
        assert content[0]['input_audio']['format']=='wav'
        assert len(payload['messages'])==1
        return success()
    p=provider(handler)
    result=await observe_audio(p,source);await p.aclose()
    assert result.status=='READY_FOR_USER_ATTESTATION'
    assert result.observation.other_sound_events[0].start==3.5
    assert result.receipt['semanticProviderCalls']==1
    visual={'sourceHash':'a'*64,'duration':8,'events':[{'id':'v','start':3,'end':5,'visual':{'text':'fixture action'}}]}
    fusion=align_for_user_review(visual,result)
    assert fusion['audioSemanticUserAttestation']=='PENDING' and fusion['adoptedAudioFacts']==[]
    assert not fusion['formalMediaAuthorized']
    with pytest.raises(ValueError):attested_audio_facet(result,{},None,None)

@pytest.mark.asyncio
@pytest.mark.parametrize('bad',['malformed','missing','negative','end-before-start','out-of-range','invalid-enum','named-speaker','extra'])
async def test_invalid_not_retried(source,bad):
    data=body()
    if bad=='missing':del data['environmentEvents']
    if bad=='negative':data['otherSoundEvents'][0]['start']=-1
    if bad=='end-before-start':data['otherSoundEvents'][0]['end']=0
    if bad=='out-of-range':data['otherSoundEvents'][0]['end']=9
    if bad=='invalid-enum':data['otherSoundEvents'][0]['confidence']='CERTAIN'
    if bad=='named-speaker':data['otherSoundEvents'][0]['speakerHint']='Named_person'
    if bad=='extra':data['expectedMeaning']='unauthorized'
    p=provider(lambda r: httpx.Response(200,json={'choices':[{'message':{'content':'not JSON'}}]}) if bad=='malformed' else success(data))
    r=await p.observe_audio(source);await p.aclose()
    assert r.status=='AUDIO_SEMANTIC_RESPONSE_INVALID' and r.receipt['semanticProviderCalls']==1
    assert r.raw_text

@pytest.mark.asyncio
@pytest.mark.parametrize('status,text,code',[(401,'invalid key','QWEN_OMNI_AUTH_FAILED'),(403,'workspace mismatch','QWEN_OMNI_ENDPOINT_OR_REGION_MISMATCH'),(404,'model unavailable','QWEN_OMNI_MODEL_UNAVAILABLE'),(413,'large','AUDIO_INPUT_TOO_LARGE')])
async def test_provider_errors_no_fallback(source,status,text,code):
    p=provider(lambda r:httpx.Response(status,text=text,headers={'x-request-id':'failed-request'}))
    r=await p.observe_audio(source);await p.aclose()
    assert r.status==code and r.receipt['semanticProviderCalls']==1 and r.receipt['requestId']=='failed-request'

@pytest.mark.asyncio
@pytest.mark.parametrize('failure',['timeout','429','500','reset'])
async def test_bounded_transient_retries(source,failure,monkeypatch):
    async def no_sleep(n):pass
    monkeypatch.setattr('drama_plugin.providers.http.qwen_omni.asyncio.sleep',no_sleep)
    def handler(r):
        if failure=='timeout':raise httpx.ReadTimeout('transient',request=r)
        if failure=='reset':raise httpx.ReadError('reset',request=r)
        return httpx.Response(int(failure),text='transient')
    p=provider(handler)
    r=await p.observe_audio(source);await p.aclose()
    assert r.receipt['semanticProviderCalls']==3 and r.receipt['retryCount']==2
    assert r.status=='QWEN_OMNI_TRANSIENT_FAILURE'

@pytest.mark.asyncio
async def test_sse_usage_and_unknown(source):
    data=body();data['otherSoundEvents'][0]['confidence']='UNKNOWN'
    parts=[{'id':'stream-id','choices':[{'delta':{'content':json.dumps(data)}}]}, {'choices':[],'usage':{'total_tokens':5}}]
    text='\n\n'.join('data: '+json.dumps(p) for p in parts)+'\n\ndata: [DONE]\n'
    p=provider(lambda r:httpx.Response(200,text=text,headers={'content-type':'text/event-stream'}))
    r=await p.observe_audio(source);await p.aclose()
    assert r.observation.other_sound_events[0].confidence=='UNKNOWN'
    assert r.receipt['usage']=={'total_tokens':5}
    assert r.status=='AUDIO_SEMANTIC_NO_RELIABLE_EVENTS'

@pytest.mark.asyncio
@pytest.mark.parametrize('response',[[], {'choices':[{'message':{'content':None}}]}, {'choices':[{'message':{'content':[]}}]}])
async def test_nontext_response_has_receipt(source,response):
    p=provider(lambda r:httpx.Response(200,json=response))
    r=await p.observe_audio(source);await p.aclose()
    assert r.status=='AUDIO_SEMANTIC_RESPONSE_INVALID' and r.receipt['semanticProviderCalls']==1

@pytest.mark.asyncio
async def test_size_guard_does_not_submit(source,monkeypatch):
    monkeypatch.setattr('drama_plugin.providers.http.qwen_omni.BASE64_LIMIT',100)
    p=provider(lambda r:pytest.fail('oversized input submitted'))
    r=await p.observe_audio(source);await p.aclose()
    assert r.status=='AUDIO_INPUT_TOO_LARGE' and r.receipt['semanticProviderCalls']==0
    assert 'SPLIT_BY_TIME_WINDOW' in r.receipt['requiredAction']

@pytest.mark.asyncio
async def test_source_hash_guard(source):
    p=provider(lambda r:pytest.fail('hash mismatch submitted'))
    bad=AudioSemanticInput(source.audio_path,'a'*64,'b'*64,3,5,8)
    r=await p.observe_audio(bad);await p.aclose()
    assert r.status=='AUDIO_SOURCE_HASH_MISMATCH'

@pytest.mark.asyncio
async def test_error_secret_redacted(source):
    p=provider(lambda r:success())
    key=p.config.api_key.get_secret_value()
    await p._client.aclose()
    p._client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(401,text='key='+key)))
    r=await p.observe_audio(source);await p.aclose()
    assert key not in json.dumps(r.receipt) and key not in r.raw_text

@pytest.mark.parametrize('scenario',['court-dialogue','civilian-action','different-battle'])
@pytest.mark.asyncio
async def test_same_boundary_no_work_prompt(source,scenario):
    def handler(request):
        text=json.loads(request.content)['messages'][0]['content'][1]['text']
        assert scenario not in text
        for forbidden in ['screenplay','expected dialogue','Director Intent','项羽','虞姬','S22','乌江','N/M/F']:
            assert forbidden not in text
        return success()
    p=provider(handler);result=await p.observe_audio(source);await p.aclose()
    assert result.status=='READY_FOR_USER_ATTESTATION'

def test_blind_api_has_no_context_argument():
    import inspect
    assert list(inspect.signature(BailianQwenOmniAudioSemanticProvider.observe_audio).parameters)==['self','source']
    assert 'expected' not in BLIND_AUDIO_PROMPT.lower()

@pytest.mark.asyncio
async def test_composition_root_host_path(source,tmp_path):
    from drama_plugin import DramaPlugin
    config=tmp_path/'config.yaml'
    config.write_text('providers:\n  audio_semantic:\n    mode: bailian_qwen_omni\nservices:\n  qwen_omni:\n    api_key: '+uuid.uuid4().hex+'\n    base_url: https://example.test/v1\n')
    plugin=DramaPlugin.load(Path(__file__).resolve().parents[1],config_path=config)
    p=plugin.providers.audio_semantic
    assert isinstance(p,BailianQwenOmniAudioSemanticProvider)
    await p._client.aclose();p._client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r:success()))
    r=await observe_audio(plugin.providers.audio_semantic,source)
    assert r.status=='READY_FOR_USER_ATTESTATION' and len(plugin.tools.list())==52
    await plugin.aclose()
