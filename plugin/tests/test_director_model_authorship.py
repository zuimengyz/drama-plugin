"""Offline protocol/selection tests, never independent model artistry."""
import json
from pathlib import Path
import httpx
import pytest
from drama_plugin.config.loader import load_config
from drama_plugin.creative_engine.backends import compose_authors
from drama_plugin.creative_engine.host_text import HostOriginalRequired
from drama_plugin.creative_engine.direction_narrative import native_director_narrative
from drama_plugin.creative_engine.diagnostics import response_context, AuthorResultFailure
from drama_plugin.creative_engine.text_wire import decode_completion, validate_reasoning
from drama_plugin.execution.transport import CapabilityAbsent
from test_director_narrative_handoff import workshop,selected_writer,isolated
from test_formal_author_backends import request, ENV, SKILLS


def config(**extra):
    return load_config(environment={**ENV,'DRAMA_PLUGIN_TEXT_AUTHORSHIP':'HOST',
        'DRAMA_PLUGIN_DIRECTION_AUTHORSHIP':'MODEL','DRAMA_PLUGIN_TEXT_COMPOSITION_PROVIDER':'grok',
        'DRAMA_PLUGIN_DIRECTION_AUTHOR_MODEL':'grok-4.7',
        'DRAMA_PLUGIN_TEXT_COMPOSITION_REASONING_EFFORT':'high',**extra}).text_composition


async def test_direction_model_does_not_switch_other_authors():
    seen=[]
    def wire(req):
        body=json.loads(req.content);seen.append(body)
        assert body['model']=='grok-4.7' and body['reasoning_effort']=='high'
        return httpx.Response(200,json={'model':'grok-4.7','usage':{'prompt_tokens':2,'completion_tokens':3,
            'cost_in_usd_ticks':20,'prompt_tokens_details':{'cached_tokens':1},'completion_tokens_details':{'reasoning_tokens':5}},
            'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':json.dumps({'text':'Film','world':'Era candidate','look':'Authored look'})}}]})
    ca,da,pa=compose_authors(config(),SKILLS,transport=httpx.MockTransport(wire))
    with pytest.raises(HostOriginalRequired):await ca.author(request())
    with pytest.raises(HostOriginalRequired):await pa.design(request('professional'))
    original=await da.film_treatment(request('direction'),{'screenplay':'Writer','designatedSource':'Source'})
    assert original.world=='Era candidate' and len(seen)==1
    d=response_context.get();assert d.model=='grok-4.7' and d.usage['reasoning_tokens']==5 and d.usage['cost_in_usd_ticks']==20
    assert d.usage['cached_tokens']==1


@pytest.mark.parametrize('model,effort,ok',[('grok-4.7','high',True),('grok-4.7','xhigh',True),
    ('grok-4.5','xhigh',False),('grok-4.7','none',False),('unknown-model','high',False)])
def test_exact_reasoning_support(model,effort,ok):
    c=config().model_copy(update={'direction_model':model,'reasoning_effort':effort})
    if ok:validate_reasoning(c,'direction')
    else:
        with pytest.raises(CapabilityAbsent,match='REASONING_POLICY_UNSUPPORTED'):validate_reasoning(c,'direction')


async def test_cold_model_candidate_is_retained_then_explicitly_selected(tmp_path):
    w=workshop(tmp_path);pin=selected_writer(w);before=w.objects.read_ref(pin);calls=[]
    def wire(req):
        data=json.loads(req.content);payload=json.loads(data['messages'][1]['content']);calls.append(payload)
        if 'designatedSource' in payload:body={'text':'Unpolished model film','world':'Model proposes unnamed town; uncertain era.','look':'Model chooses violet shadow.'}
        else:
            assert payload['filmIdentity']['world']['text']=='Model proposes unnamed town; uncertain era.'
            assert payload['selectedFilmDirection']=='Unpolished model film'
            body={'text':'Scene response based on selected world.'}
        return httpx.Response(200,json={'model':'grok-4.7','choices':[{'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(body)}}]})
    _,da,_=compose_authors(config(),SKILLS,transport=httpx.MockTransport(wire))
    req=request('direction').model_copy(update={'scope':request().scope.model_copy(update={'work_id':'fixture','scene_id':None}), 'screenplay_context':before})
    with pytest.raises(HostOriginalRequired) as pending:
        await native_director_narrative(w,da,req,operation='cold')
    packet=pending.value.request_packet
    assert packet['task']=='film.director-candidate-selection:v1'
    assert len(calls)==1 and 'filmIdentity' not in before
    # Re-enter before selection: retained candidate, no duplicate external request.
    with pytest.raises(HostOriginalRequired):await native_director_narrative(w,da,req,operation='cold')
    assert len(calls)==1
    candidate=packet['input']['candidate'];assert candidate['actualAuthor']=='MODEL' and not candidate['formalAdoption']
    w.bind_host_author_original(None,work_id='fixture',scene_id=None,task=packet['task'],input_fingerprint=packet['inputFingerprint'],
        content={'candidateFingerprint':packet['input']['candidateRef']['fingerprint'],'reason':'Select experiment only'},reason='Select exact author candidate')
    c=await native_director_narrative(w,da,req,operation='cold')
    assert len(calls)==2
    assert c['directorNarrative']['film']['actualAuthor']=='MODEL'
    assert c['directorNarrative']['film']['selectedBy']=='HOST'
    assert c['directorNarrative']['film']['text']==candidate['original']['text']
    assert c['filmIdentity']['originals']['world']['original']['text']==candidate['original']['world']
    assert c['screenplay']==before['screenplay'] and w.objects.read_ref(pin)==before
    # Already selected originals resume without MODEL reauthorship.
    await native_director_narrative(w,da,req.model_copy(update={'screenplay_context':c}),operation='other')
    assert len(calls)==2


def test_streamed_usage_and_missing_termination():
    chunks=[{'model':'grok-4.7','choices':[{'index':0,'delta':{'content':'{"text":'},'finish_reason':None}]},
            {'model':'grok-4.7','choices':[{'index':0,'delta':{'content':'"ok"}'},'finish_reason':'stop'}]},
            {'model':'grok-4.7','choices':[],'usage':{'completion_tokens_details':{'reasoning_tokens':9}}}]
    raw=':heartbeat\n\n'+''.join('data: '+json.dumps(x)+'\n\n' for x in chunks)
    out=decode_completion((raw+'data: [DONE]\n').encode(),streamed=True)
    assert out['choices'][0]['message']['content']=='{"text":"ok"}'
    assert out['usage']['completion_tokens_details']['reasoning_tokens']==9
    with pytest.raises(AuthorResultFailure,match='AUTHOR_STREAM_INCOMPLETE'):decode_completion(raw.encode(),streamed=True)


async def test_explicit_missing_model_never_falls_back():
    ca,da,pa=compose_authors(config(DRAMA_PLUGIN_DIRECTION_AUTHOR_MODEL=''),SKILLS)
    assert ca is not None and pa is not None and da is None
