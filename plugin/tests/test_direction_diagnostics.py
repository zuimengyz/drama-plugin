"""Offline diagnostic fidelity and secrecy; no contract repair or provider traffic."""
import asyncio
import hashlib
import json

import httpx
import pytest
from drama_plugin.creative_engine.backends import FormalDirectionAuthor, TextCompositionBackend
from drama_plugin.creative_engine.diagnostics import AuthorResultFailure, AuthorUnavailable
from drama_plugin.config.loader import load_config
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.creative_engine.contracts import Authority, CreativeCheckpoint, Kind
from drama_plugin.runtime.contracts import CapabilityInput, RuntimeState, RunMode
from test_formal_author_backends import ENV, SKILLS, canon, configured, model_output, request, shot, source

SECRET='offline-contract-key'
REASONING='HIDDEN_REASONING_DO_NOT_STORE'


def wire(body,finish='stop'):
    return httpx.Response(200,json={'model':'offline-direction-model','usage':{'prompt_tokens':12,'completion_tokens':8,
        'completion_tokens_details':{'reasoning_tokens':3},'untrusted':SECRET},'choices':[{'finish_reason':finish,
        'message':{'role':'assistant','content':body,'reasoning_content':REASONING}}]})


def author(handler):
    return FormalDirectionAuthor(TextCompositionBackend(load_config(environment=ENV).text_composition,
        transport=httpx.MockTransport(handler)),SKILLS)


@pytest.mark.asyncio
@pytest.mark.parametrize('change,stage,path,validator',[
    ('invalid_json','JSON_PARSE',('$',),None),
    ('field','DTO_SCHEMA',('durationMs',),None),
    ('authority','DIALOGUE_AUTHORITY',('spokenIds',),'FormalDirectionAuthor.canon_dialogue_authority'),
    ('order','SHOT_POST_VALIDATION',('professionalDomains',),'ShotBody.domains'),
    ('length','INCOMPLETE_OUTPUT',(),None),
    ('extra','DTO_SCHEMA',('<extra>',),None),
])
async def test_precise_failure_without_raw_input_context_or_reasoning(change,stage,path,validator):
    output=model_output('direction');finish='stop'
    if change=='field':output['durationMs']=SECRET
    if change=='authority':output['spokenIds']=['not-canon-line']
    if change=='order':output['professionalDomains']=['SOUND','CAMERA']
    if change=='extra':output[SECRET]=REASONING
    if change=='length':finish='length'
    resp=wire(SECRET if change=='invalid_json' else json.dumps(output),finish)
    with pytest.raises(AuthorResultFailure) as caught:
        await author(lambda r:resp).author(request('direction'))
    d=caught.value.diagnostic
    assert d.failure_stage==stage and d.validator==validator
    assert (d.issues[0].field_path if d.issues else ())==path
    assert d.response_hash==hashlib.sha256(resp.content).hexdigest()
    assert d.finish_reason==finish and d.model=='offline-direction-model'
    assert d.usage['reasoning_tokens']==3
    assert SECRET not in d.model_dump_json() and REASONING not in d.model_dump_json()
    assert SECRET not in str(caught.value) and REASONING not in str(caught.value)


@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['http','wire_json','missing_choices','transport'])
async def test_provider_protocol_failure_is_not_domain_failure(kind):
    def handle(r):
        if kind=='transport':raise httpx.ReadTimeout(SECRET,request=r)
        if kind=='http':return httpx.Response(401,json={'error':SECRET,'reasoning_content':REASONING})
        if kind=='wire_json':return httpx.Response(200,text=SECRET)
        return httpx.Response(200,json={'choices':[]})
    with pytest.raises((AuthorResultFailure,AuthorUnavailable)) as caught:
        await author(handle).author(request('direction'))
    d=caught.value.diagnostic
    assert d.failure_stage=='PROVIDER_PROTOCOL'
    assert SECRET not in d.model_dump_json() and REASONING not in d.model_dump_json()
    assert d.exception_type


@pytest.mark.asyncio
async def test_valid_direction_unchanged_and_task_local_failure_metadata():
    async def handle(r):
        if json.loads(r.content)['messages'][1]['content'].find('parallel-bad')>=0:
            await asyncio.sleep(0.01)
            return wire('not JSON')
        return wire(json.dumps(model_output('direction')))
    a=author(handle)
    bad=request('direction').model_copy(update={'scope':request('direction').scope.model_copy(update={'work_id':'parallel-bad'})})
    result=await asyncio.gather(a.author(request('direction')),a.author(bad),return_exceptions=True)
    assert result[0]==shot() and isinstance(result[1],AuthorResultFailure)
    assert result[1].diagnostic.response_hash==hashlib.sha256(wire('not JSON').content).hexdigest()


async def seed_direction_checkpoint(p,run):
    # Offline fixture only; product resume never authors or replaces these Canon versions.
    refs=[p.creative.state.input(run.run_id).source_ref]
    c=canon()
    for k,body in ((Kind.WORK,c.work),(Kind.SCRIPT,c.script),(Kind.SCENE,c.scene)):
        refs.append(p.creative_versions.write(writer=Authority.CANON,kind=k,scope=run.scope,body=body,
            sources=tuple(refs),operation=run.run_id+':offline:'+k.value))
    cp=CreativeCheckpoint(refs=tuple(refs));p.creative.state.save(run.run_id,run.scope,cp)
    native=p.runtime.store.load(run.run_id)
    p.runtime.store.save(native.model_copy(update={'state':RuntimeState.READY,'cursor':2,'revision':native.revision+1}),expected_revision=native.revision)
    return cp


@pytest.mark.asyncio
@pytest.mark.parametrize('unexpected',[False,True])
async def test_runtime_stable_failure_with_exact_persisted_safe_diagnostic(monkeypatch,tmp_path,unexpected):
    p=configured(monkeypatch,tmp_path)
    run=p.create_film_run(work_id='offline-diag-runtime',mode=RunMode.PRODUCTION,source=source())
    cp=await seed_direction_checkpoint(p,run)
    if unexpected:
        class Broken:
            async def author(self,r):raise RuntimeError(SECRET+' '+REASONING)
        p.creative.direction_author=Broken()
    else:p.creative.direction_author.client.transport=httpx.MockTransport(lambda r:wire('{invalid'))
    done=await p.runtime.run(run.run_id)
    assert done.state==RuntimeState.BLOCKED and done.cursor==2
    assert done.last_result.code=='CAPABILITY_EXECUTION_ERROR'
    ref=done.last_result.artifact_refs[0]
    body=p.creative_versions.objects.read_ref(SourcePin(key='diagnostic',kind='CANON',fingerprint=ref.artifact_ref.split(':')[1]))
    d=body['diagnostic']
    assert d['failure_stage']==('INTERNAL' if unexpected else 'JSON_PARSE')
    assert body['versionRefs']==cp.model_dump(mode='json',by_alias=True)['refs']
    assert SECRET not in json.dumps(body) and REASONING not in json.dumps(body)
    assert p.creative.state.checkpoint(run.run_id).refs==cp.refs
    await p.aclose()
