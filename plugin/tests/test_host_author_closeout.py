"""Real Host selection through existing authors; no mock transport or model call.

Authored fixture content below tests handoff, not independent model creativity.
All registered identities are disposable generic fixtures, never The Medicine.
"""
from copy import deepcopy
import json
import socket

import httpx
import pytest

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.config.text_composition import TextCompositionConfig
from drama_plugin.creative_engine.backends import compose_authors, FormalProfessionalAuthor
from drama_plugin.creative_engine.host_text import HostOriginalRequired
from drama_plugin.creative_engine.contracts import Authority
from drama_plugin.film.contracts import FilmCanon, FilmDirection, CanonScene, DirectedShot, LanguageMetadata, DeliveryProfile
from drama_plugin.runtime.contracts import CapabilityInput, ResultStatus
from test_formal_author_backends import source, canon, shot, request, SKILLS, REF, ENV
from test_director_narrative_handoff import selected_writer
from author_model_helpers import model_dto


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail('Host text must not invoke an HTTP client or socket')
    for name in ('connect', 'connect_ex'):
        monkeypatch.setattr(socket.socket, name, deny)
    monkeypatch.setattr(httpx.AsyncClient, 'post', deny)
    monkeypatch.delenv('DRAMA_PLUGIN_CONFIG_FILE', raising=False)
    monkeypatch.setenv('DRAMA_PLUGIN_FILM_STORE_ENABLED', '0')


def host_plugin(monkeypatch, tmp_path):
    # Even complete model credentials cannot trigger implicit model fallback.
    for k, v in ENV.items(): monkeypatch.setenv(k, v)
    monkeypatch.delenv('DRAMA_PLUGIN_TEXT_AUTHORSHIP')
    return DramaPlugin.load(ledger_path=tmp_path/'fixture.sqlite3', creative_root=tmp_path/'creative')


async def select_missing(p, error, content):
    packet = await p.tools.invoke('screenplay.host_author_request', work_id=error.request_packet['scope']['workId'])
    assert packet == error.request_packet
    assert packet['instructions'] and packet['outputSchema']
    ref = await p.tools.invoke('screenplay.bind_host_author_original', handoff_ref=None,
        work_id=packet['scope']['workId'], scene_id=packet['scope']['sceneId'],
        task=packet['task'], input_fingerprint=packet['inputFingerprint'], content=content,
        reason='Host explicitly selects this fixture original; no formal production adoption.')
    original = p.screenplays.objects.read_ref(ref)
    assert original['actualAuthor'] == original['selectedBy'] == 'HOST'
    assert original['formalAdoption'] is False
    return packet, ref


@pytest.mark.parametrize('role', ['canon', 'direction', 'professional'])
async def test_default_host_missing_original_never_calls_configured_model(role):
    config = TextCompositionConfig(provider='deepseek',base_url='https://api.deepseek.com',api_key='unused',
        canon_model='unused',direction_model='unused',professional_model='unused')
    authors = compose_authors(config, SKILLS)
    a = authors[{'canon':0, 'direction':1, 'professional':2}[role]]
    with pytest.raises(HostOriginalRequired, match='HOST_AUTHOR_ORIGINAL_REQUIRED') as missing:
        await (a.design(request(role)) if role=='professional' else a.author(request(role)))
    assert missing.value.request_packet['actualAuthor']=='HOST'
    assert 'hostAuthoring' not in json.dumps(missing.value.request_packet['input'])


async def test_host_film_original_without_prior_screenplay_and_exact_input_selection(monkeypatch,tmp_path):
    p=host_plugin(monkeypatch,tmp_path)
    a=p.creative.canon_author
    r=request()
    packet={'source':'An existing source, not a completed screenplay.'}
    with pytest.raises(HostOriginalRequired) as missing:
        await a.film_original(r,packet)
    _,ref=await select_missing(p,missing.value,{'text':'Host writes the whole original.'})
    assert (await a.film_original(r,packet)).text=='Host writes the whole original.'
    assert p.screenplays.objects.read_ref(ref)['content']['text']=='Host writes the whole original.'
    with pytest.raises(HostOriginalRequired):
        await a.film_original(r,{'source':'Changed source needs a new Host selection.'})
    with pytest.raises(ValueError,match='exact pending'):
        p.screenplays.bind_host_author_original(None,work_id=r.scope.work_id,scene_id=r.scope.scene_id,
            task='invented-task',input_fingerprint='0'*64,content={'text':'Wrong'},reason='Invalid')
    await p.aclose()


async def test_default_film_host_chain_preserves_writer_and_frozen_coverage(monkeypatch,tmp_path):
    p=host_plugin(monkeypatch,tmp_path)
    assert p.config.text_composition.authorship=='HOST'
    pin=selected_writer(p.screenplays,work='host-fixture')
    writer_original=deepcopy(p.screenplays.objects.read_ref(pin))
    run=p.create_source_film_run(work_id='host-fixture',run_id='host-fixture',source=source(),
        languages=LanguageMetadata(source_document_language='en',original_work_language='ru',spoken_language='ru',authority_ref=REF),
        profile=DeliveryProfile(width=1280,height=720),rights_refs=(REF,),route='offline',model='offline-model',
        screenplay_ref=pin,workflow_id='source-to-final-film:v1')
    c=canon()
    film=FilmCanon(work=c.work,script=c.script,scenes=(CanonScene(scene_id='one',scene=c.scene),))
    film_text='Keep the listener and unseen room co-present; hearing need not grant visual access.'
    scene_text='Hold a fixed shared doorway view through the call and wait. Keep the lamp beside the doorway.'
    authored_shot=shot().model_copy(update={'camera_intent':'Fixed doorway view; do not follow sound into the room.',
        'performance_direction':'Listen before returning attention to the closed door.'})
    coverage=FilmDirection(shots=(DirectedShot(scene_id='one',shot_id='view',shot=authored_shot),))
    originals={
        'film.canon:v1:FormalCanonAuthor':model_dto(film.model_dump(mode='json',by_alias=True)),
        'host.scene-original:v1':{'text':c.scene.scene_text},
        'host.scene-decision:v1':{'choice':'KEEP_ALL','reason':'Host keeps the writer original.','text':None},
        'film.director-treatment:v2':{'text':film_text},
        'scene.director-treatment:v1':{'text':scene_text},
        'film.direction:v1:FormalDirectionAuthor':model_dto(coverage.model_dump(mode='json',by_alias=True)),
        FormalProfessionalAuthor.implementation_identity:[{'domain':'LIGHTING','facts':{
            'sources':['Door-side practical lamp'],
            'directionAndQuality':'Lamp fixed beside the doorway; the held camera and listening actor share its lateral light.'}}],
    }
    seen=[]
    async def continue_with_host(call):
        # Explicitly selected fixture originals, never synthesized transport replies.
        for _ in range(len(originals)+1):
            try: return await call()
            except HostOriginalRequired as error:
                packet=error.request_packet; task=packet['task']
                assert task not in seen, 'Selected result must resume the same task without input drift'
                assert task in originals
                if task in ('film.director-treatment:v2','scene.director-treatment:v1'):
                    assert 'FILM_CRAFT_READING' in packet['instructions']
                if task=='scene.director-treatment:v1':
                    assert packet['input']['selectedFilmDirection']==film_text
                if task in ('film.direction:v1:FormalDirectionAuthor',FormalProfessionalAuthor.implementation_identity):
                    narrative=packet['input']['hostScreenplay']['directorNarrative']
                    assert narrative['film']['text']==film_text
                    assert next(iter(narrative['scenes'].values()))['text']==scene_text
                    assert narrative['film']['selectedBy']=='HOST'
                await select_missing(p,error,originals[task]); seen.append(task)
        pytest.fail('Host continuation did not finish')
    base=CapabilityInput(run_id=run.run_id,operation_id='host-fixture:canon',scope=run.scope)
    await continue_with_host(lambda:p.film.canon(base))
    directed=base.model_copy(update={'operation_id':'host-fixture:direction'})
    assert (await continue_with_host(lambda:p.film.direction(directed))).status==ResultStatus.SUCCEEDED
    checkpoint=p.film.store.checkpoint(run.run_id)
    retained=p.screenplays.objects.read_ref(checkpoint.screenplay_ref)
    assert retained['screenplay']['text']==c.script.screenplay
    assert p.screenplays.objects.read_ref(pin)==writer_original
    assert p.film.store.author(checkpoint.canon_ref,FilmCanon).script.screenplay==c.script.screenplay
    unit=p.film.create_unit(directed,0)
    child=p.runtime.store.load(unit.creative_run_id)
    await p.creative.source(CapabilityInput(run_id=child.run_id,operation_id='host-child-source',scope=child.scope))
    pro_req=p.creative._request(CapabilityInput(run_id=child.run_id,operation_id='host-professional',scope=child.scope),Authority.PROFESSIONAL)
    result=await continue_with_host(lambda:p.professional_design.author.design(pro_req))
    assert result[0].facts['sources']==['Door-side practical lamp']
    assert pro_req.shot.camera_intent==authored_shot.camera_intent
    assert seen==list(originals)
    old=checkpoint.model_dump(mode='json')
    def no_more(*args,**kwargs):pytest.fail('Frozen coverage must not ask for new Host text')
    p.creative.canon_author.client.host_original_reader=no_more
    await p.film.direction(directed.model_copy(update={'operation_id':'host-recovery'}))
    await p.creative._direction(CapabilityInput(run_id=child.run_id,operation_id='host-child-recovery',scope=child.scope))
    assert p.film.store.checkpoint(run.run_id).direction_ref==checkpoint.direction_ref
    assert p.creative.state.checkpoint(child.run_id).package_ref is None
    assert p.screenplays.objects.read_ref(pin)==writer_original
    await p.aclose()


async def test_registered_host_selection_resumes_same_runtime_step(monkeypatch,tmp_path):
    from drama_plugin.runtime.contracts import RuntimeState
    p=host_plugin(monkeypatch,tmp_path)
    pin=selected_writer(p.screenplays,work='host-resume')
    run=p.create_source_film_run(work_id='host-resume',run_id='host-resume',source=source(),
        languages=LanguageMetadata(source_document_language='en',original_work_language='ru',spoken_language='ru',authority_ref=REF),
        profile=DeliveryProfile(width=1280,height=720),rights_refs=(REF,),route='offline',model='offline-model',
        screenplay_ref=pin,workflow_id='source-to-final-film:v1')
    run=await p.runtime.run(run.run_id)
    assert run.state==RuntimeState.WAITING_USER
    assert 'HOST_AUTHOR_ORIGINAL_REQUIRED' in run.last_result.user_decision.question
    pending=await p.tools.invoke('screenplay.host_author_request',work_id='host-resume')
    assert pending['task']=='film.canon:v1:FormalCanonAuthor'
    c=canon();film=FilmCanon(work=c.work,script=c.script,scenes=(CanonScene(scene_id='one',scene=c.scene),))
    args=dict(handoff_ref=pin,work_id='host-resume',scene_id=None,task=pending['task'],
        input_fingerprint=pending['inputFingerprint'],content=model_dto(film.model_dump(mode='json',by_alias=True)),
        reason='Host selects exact canonical projection of unchanged writer.',run_id=run.run_id)
    with pytest.raises(ValueError,match='exact Host original'):
        await p.tools.invoke('screenplay.bind_host_author_original',**{**args,'input_fingerprint':'0'*64})
    await p.tools.invoke('screenplay.bind_host_author_original',**args)
    ready=p.runtime.store.load(run.run_id)
    assert ready.state==RuntimeState.READY and ready.cursor==run.cursor
    assert p.film.store.checkpoint(run.run_id).canon_ref is None # selection did not skip execution
    after=await p.runtime.run(run.run_id)
    assert after.state==RuntimeState.WAITING_USER and after.cursor>run.cursor
    assert p.film.store.checkpoint(run.run_id).canon_ref is not None
    assert p.screenplays.host_author_request('host-resume')['task']=='host.scene-original:v1'
    await p.aclose()


def test_host_controls_leave_historical_empty_context_identity_unchanged():
    from drama_plugin.creative_engine.host_text import without_host_originals
    legacy = {'authorContext': {}, 'context': {'authorContext': {}}, 'screenplay': {'text': 'Frozen writer'}}
    assert without_host_originals(legacy)==legacy
    selected = deepcopy(legacy)
    selected['authorContext']['hostAuthoring']={'one': {'content': 'not a creative input'}}
    assert without_host_originals(selected)==legacy
