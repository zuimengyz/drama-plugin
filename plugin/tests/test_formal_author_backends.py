"""Production adapters/config with an in-process text wire; never real composition."""
import json
from pathlib import Path

import httpx
import pytest
from pydantic import TypeAdapter, ValidationError

from drama_plugin import DramaPlugin
from drama_plugin.config.loader import load_config
from drama_plugin.config.text_composition import TextCompositionConfig
from drama_plugin.creative_engine.backends import (
    TextCompositionBackend, FormalCanonAuthor, FormalDirectionAuthor, FormalProfessionalAuthor, compose_authors,
)
from drama_plugin.creative_engine.contracts import (
    AuthorRequest, Authority, CanonDraft, CreativeCheckpoint, DesignBody, Dialogue, Kind,
    SceneBody, ScriptBody, ShotBody, SourceBody, WorkBody,
)
from drama_plugin.execution.transport import CapabilityAbsent
from drama_plugin.runtime.contracts import ArtifactReference, CapabilityInput, ResultStatus, RunMode, RuntimeScope, RuntimeState

SKILLS = Path(__file__).resolve().parents[1] / 'skills'
REF = ArtifactReference(owner='source-owner', artifact_ref='offline-r3-language-authority', version=1)
ENV = {
    'DRAMA_PLUGIN_TEXT_COMPOSITION_PROVIDER': 'offline-compatible-text-service',
    'DRAMA_PLUGIN_TEXT_COMPOSITION_BASE_URL': 'https://text.invalid/v1',
    'DRAMA_PLUGIN_TEXT_COMPOSITION_API_KEY': 'offline-contract-key',
    'DRAMA_PLUGIN_CANON_AUTHOR_MODEL': 'offline-canon-model',
    'DRAMA_PLUGIN_DIRECTION_AUTHOR_MODEL': 'offline-direction-model',
    'DRAMA_PLUGIN_PROFESSIONAL_AUTHOR_MODEL': 'offline-professional-model',
}

def source():
    return SourceBody(goal='Contract smoke only', text='A traveler asks for shelter at a shut door.',
        source_document_language='en', original_work_language='ru', spoken_language_policy='source_original',
        spoken_language='ru', language_metadata_ref=REF)

def canon():
    return CanonDraft(work=WorkBody(interpretation='An appeal remains unanswered.', dramatic_intent='Observe the unanswered appeal.', character_meaning='The traveler needs shelter.'),
        script=ScriptBody(screenplay='A traveler asks at a closed door.'),
        scene=SceneBody(scene_text='The traveler calls once and waits.', dialogue=(Dialogue(id='appeal', speaker='traveler', text='Помогите.'),)))

def shot():
    return ShotBody(purpose='Observe the approved action', required_transition='A request becomes a wait', duration_ms=4000,
        subject_action='The traveler calls and waits', entry_state='Before the call', exit_state='Waiting', coverage='Approved action',
        blocking_intent='Remain at the doorway', camera_intent='Preserve the relation', editing_relation='After the wait',
        performance_direction='Complete the approved action', spoken_ids=('appeal',), professional_domains=('LIGHTING',))

def request(role='canon'):
    return AuthorRequest(scope=RuntimeScope(work_id='offline-r3', scene_id='scene', shot_id='shot'), source=source(), source_refs=(),
        canon=None if role=='canon' else canon(), shot=shot() if role=='professional' else None)

def model_output(role):
    if role=='canon': return canon().model_dump(mode='json', by_alias=True)
    if role=='direction': return shot().model_dump(mode='json', by_alias=True)
    return [DesignBody(domain='LIGHTING', facts={'source':'Approved practical', 'direction':'Side'}).model_dump(mode='json', by_alias=True)]

def response(body, finish='stop'):
    return httpx.Response(200, json={'choices':[{'finish_reason':finish,'message':{'role':'assistant','content':json.dumps(body)}}]})

def configured(monkeypatch, tmp_path):
    for k,v in ENV.items(): monkeypatch.setenv(k,v)
    return DramaPlugin.load(ledger_path=tmp_path/'smoke.sqlite3', creative_root=tmp_path/'creative')

def test_env_precedence_and_independent_roles(tmp_path):
    config_file=tmp_path/'config.yaml'
    config_file.write_text('text_composition:\n  provider: file-service\n  base_url: https://file.invalid/v1\n  api_key: offline-file-key\n  canon_model: file-canon\n  direction_model: file-direction\n  professional_model: file-professional\n')
    cfg=load_config(config_file, environment={'DRAMA_PLUGIN_CANON_AUTHOR_MODEL':'env-canon', 'DRAMA_PLUGIN_TEXT_COMPOSITION_BASE_URL':'https://env.invalid/v1'})
    assert cfg.text_composition.canon_model=='env-canon'
    assert cfg.text_composition.direction_model=='file-direction' and cfg.text_composition.professional_model=='file-professional'
    assert cfg.text_composition.base_url=='https://env.invalid/v1'
    assert 'offline-file-key' not in repr(cfg.text_composition)

@pytest.mark.parametrize('missing', list(ENV))
def test_missing_config_no_audio_or_test_fallback(missing):
    env={k:v for k,v in ENV.items() if k!=missing}
    env.update({'DRAMA_PLUGIN_PROVIDER_QWEN_OMNI_API_KEY':'offline-audio-key', 'DRAMA_PLUGIN_PROVIDER_QWEN_OMNI_MODEL':'offline-audio-model'})
    cfg=load_config(environment=env)
    authors=compose_authors(cfg.text_composition, SKILLS)
    if 'AUTHOR_MODEL' in missing:
        idx={'DRAMA_PLUGIN_CANON_AUTHOR_MODEL':0,'DRAMA_PLUGIN_DIRECTION_AUTHOR_MODEL':1,'DRAMA_PLUGIN_PROFESSIONAL_AUTHOR_MODEL':2}[missing]
        assert authors[idx] is None and sum(a is not None for a in authors)==2
    else: assert authors==(None,None,None)

@pytest.mark.parametrize('url',['http://text.invalid','https://user:key@text.invalid','https://text.invalid?token=key','https://text.invalid/#token'])
def test_unsafe_endpoint_rejected(url):
    with pytest.raises(ValidationError): TextCompositionConfig(base_url=url)

@pytest.mark.asyncio
async def test_load_autocomposes_and_each_role_contract_smoke(monkeypatch,tmp_path):
    p=configured(monkeypatch,tmp_path)
    authors=(p.creative.canon_author,p.creative.direction_author,p.professional_design.author)
    assert tuple(type(a) for a in authors)==(FormalCanonAuthor,FormalDirectionAuthor,FormalProfessionalAuthor)
    assert all(a.classification=='FORMAL' and a.__class__.__module__=='drama_plugin.creative_engine.backends' for a in authors)
    assert authors[0].client is authors[1].client is authors[2].client
    calls=[]
    def handler(req):
        payload=json.loads(req.content); calls.append(payload)
        role={'offline-canon-model':'canon','offline-direction-model':'direction','offline-professional-model':'professional'}[payload['model']]
        assert 'tools' not in payload and 'tool_choice' not in payload
        assert payload['messages'][0]['role']=='system' and payload['messages'][1]['role']=='user'
        assert json.loads(payload['messages'][1]['content'])['source']['originalWorkLanguage']=='ru'
        return response(model_output(role))
    authors[0].client.transport=httpx.MockTransport(handler)
    c=await authors[0].author(request()); d=await authors[1].author(request('direction')); pro=await authors[2].design(request('professional'))
    assert c==canon() and d==shot() and pro[0].domain.value=='LIGHTING'
    assert [x['model'] for x in calls]==['offline-canon-model','offline-direction-model','offline-professional-model']
    await p.aclose()

@pytest.mark.asyncio
@pytest.mark.parametrize('role',['canon','direction','professional'])
@pytest.mark.parametrize('remote_absent',[False,True])
async def test_registered_capability_invokes_formal_backend(monkeypatch,tmp_path,role,remote_absent):
    p=configured(monkeypatch,tmp_path); calls=[]
    def handler(req):
        calls.append(req)
        return httpx.Response(401,json={'error':'offline-contract-key'}) if remote_absent else response(model_output(role))
    p.creative.canon_author.client.transport=httpx.MockTransport(handler)
    run=p.create_film_run(work_id='offline-r3-capability',mode=RunMode.PRODUCTION,source=source())
    s=p.creative.state.input(run.run_id).source_ref; refs=[s]
    if role!='canon':
        c=canon()
        for kind,body in ((Kind.WORK,c.work),(Kind.SCRIPT,c.script),(Kind.SCENE,c.scene)):
            refs.append(p.creative_versions.write(writer=Authority.CANON,kind=kind,scope=run.scope,body=body,sources=tuple(refs),operation=run.run_id+':offline-fixture:'+kind.value))
    if role=='professional':
        refs.append(p.creative_versions.write(writer=Authority.DIRECTION,kind=Kind.SHOT,scope=run.scope,body=shot(),sources=tuple(refs),operation=run.run_id+':offline-fixture:shot'))
    p.creative.state.save(run.run_id,run.scope,CreativeCheckpoint(refs=tuple(refs)))
    inputs=CapabilityInput(run_id=run.run_id,scope=run.scope,operation_id=run.run_id+':single-contract-smoke')
    result=await p.runtime.executor.execute('creative.'+role+':v1',inputs)
    assert result.status==(ResultStatus.WAITING_EXTERNAL if remote_absent else ResultStatus.SUCCEEDED)
    assert len(calls)==1
    assert p.creative.state.checkpoint(run.run_id).package_ref is None
    await p.aclose()

@pytest.mark.asyncio
async def test_empty_formal_composition_waits_without_http(monkeypatch,tmp_path):
    for k in ENV: monkeypatch.delenv(k,raising=False)
    p=DramaPlugin.load(ledger_path=tmp_path/'empty.sqlite3')
    assert p.creative.canon_author is None and p.creative.direction_author is None and p.professional_design.author is None
    r=p.create_film_run(work_id='offline-unconfigured',mode=RunMode.PRODUCTION,source=source())
    r=await p.runtime.run(r.run_id)
    assert r.state==RuntimeState.WAITING_EXTERNAL and r.cursor==1
    assert p.creative.state.checkpoint(r.run_id).author_rounds==0
    await p.aclose()

@pytest.mark.asyncio
@pytest.mark.parametrize('role,bad',[
    ('canon', {'work':{},'script':{},'scene':{}}),
    ('direction', {**model_output('direction'),'dialogue':'unauthorized rewrite'}),
    ('direction', {**model_output('direction'),'spokenIds':['wrong-line']}),
    ('professional',[{'domain':'LIGHTING','facts':{'scene_text':'unauthorized rewrite'}}]),
    ('professional',[{'domain':'SOUND','facts':{'ambience':'cross-domain'}}]),
    ('professional',[]),
])
async def test_result_authority_validation_no_repair_or_fallback(role,bad):
    calls=[]
    def handler(req): calls.append(req); return response(bad)
    cfg=load_config(environment=ENV).text_composition
    c,d,p=compose_authors(cfg,SKILLS,transport=httpx.MockTransport(handler))
    with pytest.raises(ValueError):
        if role=='canon': await c.author(request())
        elif role=='direction': await d.author(request(role))
        else: await p.design(request(role))
    assert len(calls)==1

@pytest.mark.asyncio
@pytest.mark.parametrize('finish',['length','tool_calls'])
async def test_incomplete_model_output_rejected(finish):
    c,_,_=compose_authors(load_config(environment=ENV).text_composition,SKILLS,transport=httpx.MockTransport(lambda r:response(model_output('canon'),finish)))
    with pytest.raises(ValueError,match='INCOMPLETE'): await c.author(request())

@pytest.mark.asyncio
async def test_missing_language_or_model_does_not_call_transport():
    calls=[]; cfg=load_config(environment=ENV).text_composition
    backend=TextCompositionBackend(cfg,transport=httpx.MockTransport(lambda r:calls.append(r) or response({})))
    no_language=request().model_copy(update={'source':SourceBody(goal='No metadata',text='Text',spoken_language='en')})
    with pytest.raises(CapabilityAbsent,match='LANGUAGE'): await backend.complete('canon','system',no_language,TypeAdapter(CanonDraft))
    backend.config=TextCompositionConfig()
    with pytest.raises(CapabilityAbsent,match='CONFIGURATION'): await backend.complete('canon','system',request(),TypeAdapter(CanonDraft))
    assert calls==[]
