"""Controlled author responses prove handoff/selection, not independent film art.

All production identities below are disposable generic fixtures, never The Medicine.
The literary sample uses pure packets in the separate isolated demonstration.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import socket

import httpx
import pytest

from drama_plugin.contracts.base import dump_contract
from drama_plugin.creative_engine.backends import FormalDirectionAuthor, HostSceneOriginal
from drama_plugin.creative_engine.author_projection import screenplay_view
from drama_plugin.creative_engine.direction_narrative import native_director_narrative
from drama_plugin.creative_engine.screenplay import ContextOriginal, ScreenplayWorkshop
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
from drama_plugin.film.contracts import FilmCanon, FilmDirection, CanonScene, DirectedShot, LanguageMetadata, DeliveryProfile
from drama_plugin.creative_engine.contracts import Authority, CanonDraft
from drama_plugin.runtime.contracts import CapabilityInput, ResultStatus
from test_formal_author_backends import configured, canon, shot, source, response, REF

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('No network in narrative handoff contract tests')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)
    monkeypatch.delenv('DRAMA_PLUGIN_CONFIG_FILE', raising=False)
    monkeypatch.setenv('DRAMA_PLUGIN_FILM_STORE_ENABLED', '0')


def workshop(tmp_path):
    return ScreenplayWorkshop(DirectorArtifactStore(tmp_path))


def selected_writer(w, *, work='fixture', session='writer'):
    pin = w.retain_context(ContextOriginal(work_id=work, label='source', status='DESIGNATED_SOURCE', text=source().text))
    w.begin(session_id=session, work_id=work, scope='FILM', goal='Generic fixture', source_refs=(pin,),
            author_context={'craftKnowledge': {'caseIds':['tokyo-story'], 'techniqueIds':['lighting-placement']}})
    w.retain_v1(session, canon().script.screenplay)
    w.decide(session, choice='KEEP_ALL', reason='Fixture writer selection', expected_revision=1)
    return w.bind_selection(session, work_id=work, scene_id=None)


class TextOnlyAuthor:
    def __init__(self): self.calls=[]; self.fail_scene=False
    async def film_treatment(self, request, packet):
        self.calls.append(('film', deepcopy(packet)))
        return HostSceneOriginal(text='Let offscreen sound lead attention, without granting visual access.')
    async def scene_treatment(self, request, packet):
        self.calls.append(('scene', deepcopy(packet)))
        if self.fail_scene: raise RuntimeError('injected scene failure')
        return HostSceneOriginal(text='Hold the doorway and listen before turning; lamp remains beside the door.')


def generic_request(context):
    c=canon()
    return SimpleNamespace(scope=SimpleNamespace(work_id='fixture', scene_id='one'), source=source(),
        canon=FilmCanon(work=c.work, script=c.script, scenes=(CanonScene(scene_id='one',scene=c.scene),
            CanonScene(scene_id='two',scene=c.scene.model_copy(update={'scene_text':'Later, the traveler leaves.'})))),
        screenplay_context=context, source_refs=())


async def test_selected_only_exact_prose_retry_and_basis(tmp_path):
    w=workshop(tmp_path); pin=selected_writer(w); original=w.objects.read_ref(pin)
    # Retained advice is not a selected Director original.
    w.retain_support('writer', specialty='director', text='UNSELECTED: reveal the other room.', expected_revision=w.load('writer').revision)
    author=TextOnlyAuthor(); request=generic_request(original)
    author.fail_scene=True
    with pytest.raises(RuntimeError): await native_director_narrative(w,author,request,operation='fixture-direction')
    author.fail_scene=False
    context=await native_director_narrative(w,author,request,operation='fixture-direction')
    assert [x[0] for x in author.calls].count('film')==1
    assert context['screenplay']==original['screenplay']
    assert w.objects.read_ref(pin)==original
    assert 'UNSELECTED' not in json.dumps(context)
    assert author.calls[-1][1]['neighboringScreenplays'][0]['screenplay']==canon().scene.scene_text
    payload=screenplay_view(context)
    assert payload['directorNarrative']['film']['selectedBy']=='DIRECTOR_AUTHOR_CANDIDATE'
    assert 'ref' not in payload['directorNarrative']['film']
    assert payload['directorNarrative']['scenes']['one']['text']==context['directorNarrative']['scenes']['one']['text']
    count=len(author.calls)
    request.screenplay_context=context
    assert await native_director_narrative(w,author,request,operation='other-operation')==context
    assert len(author.calls)==count
    request.canon=request.canon.model_copy(update={'scenes':(request.canon.scenes[0].model_copy(update={
        'scene':request.canon.scenes[0].scene.model_copy(update={'scene_text':'Changed writer event'})}),)})
    with pytest.raises(ValueError,match='basis changed'):
        await native_director_narrative(w,author,request,operation='changed')


async def test_host_selection_no_history_sweep_and_tamper(tmp_path):
    w=workshop(tmp_path); pin=selected_writer(w)
    chosen=w.bind_director_narrative(pin,work_id='fixture',scene_id=None,
        film_text='Host: allow common space without following each gaze.',reason='Host chooses shared observation.')
    packet=w.objects.read_ref(chosen); req=generic_request(packet); author=TextOnlyAuthor()
    result=await native_director_narrative(w,author,req,operation='host-choice')
    assert not any(k=='film' for k,_ in author.calls)
    assert result['directorNarrative']['film']['selectedBy']=='HOST'
    assert all(p['selectedFilmDirection'].startswith('Host:') for _,p in author.calls)
    bad=deepcopy(packet); bad['directorNarrative']['film']['text']='Forged text'
    req.screenplay_context=bad
    with pytest.raises(ValueError,match='original or scope mismatch'):
        await native_director_narrative(w,author,req,operation='tampered')
    req.scope=SimpleNamespace(work_id='another',scene_id='one'); req.screenplay_context=packet
    with pytest.raises(ValueError,match='original or scope mismatch'):
        await native_director_narrative(w,author,req,operation='cross-work')


@pytest.mark.parametrize('moving', [False, True])
async def test_default_film_path_delivers_to_coverage_and_professional_and_recovers(tmp_path,monkeypatch,moving):
    p=configured(monkeypatch,tmp_path)
    pin=selected_writer(p.screenplays,work='fixture-film')
    run=p.create_source_film_run(work_id='fixture-film',run_id='fixture-film',source=source(),
        languages=LanguageMetadata(source_document_language='en',original_work_language='ru',spoken_language='ru',authority_ref=REF),
        profile=DeliveryProfile(width=1280,height=720),rights_refs=(REF,),route='offline',model='offline-model',screenplay_ref=pin,workflow_id='source-to-final-film:v1')
    calls=[]; c=canon()
    film=FilmCanon(work=c.work,script=c.script,scenes=(CanonScene(scene_id='one',scene=c.scene),))
    film_text='Keep listeners and unseen space co-present; sound need not reveal its source.'
    scene_text=('Follow attention to the door after the sound; let the face enter the doorway shadow.' if moving else
                'Hold a fixed shared doorway view; the practical lamp stays at the door, not at camera.')
    def handler(req):
        envelope=json.loads(req.content); payload=json.loads(envelope['messages'][1]['content']); system=envelope['messages'][0]['content']
        if 'preservedV1' in payload:
            calls.append(('writer-decision',payload)); return response({'choice':'KEEP_ALL','reason':'Keep writer text','text':None})
        if 'Write the whole independent scene' in system:
            calls.append(('scene-writer',payload)); return response({'text':c.scene.scene_text})
        if 'designatedSource' in payload:
            calls.append(('film-narrative',payload)); assert 'FILM_CRAFT_READING' in system
            return response({'text':film_text})
        if 'selectedFilmDirection' in payload:
            calls.append(('scene-narrative',payload)); assert payload['selectedFilmDirection']==film_text
            return response({'text':scene_text})
        if envelope['model']=='offline-canon-model':
            calls.append(('canon',payload)); return response(film.model_dump(mode='json',by_alias=True))
        narrative=payload['hostScreenplay']['directorNarrative']
        assert narrative['film']['text']==film_text
        selected_scene=next(iter(narrative['scenes'].values()))['text']
        assert selected_scene==scene_text
        if envelope['model']=='offline-direction-model':
            calls.append(('coverage',payload))
            # Deliberate deterministic dependency, not an independent creative claim.
            choice='Fixed doorway view' if 'fixed' in selected_scene else 'Follow the traveler'
            result=FilmDirection(shots=(DirectedShot(scene_id='one',shot_id='view',shot=shot().model_copy(update={'camera_intent':choice})),))
            return response(result.model_dump(mode='json',by_alias=True))
        calls.append(('professional',payload))
        assert 'sceneDirection' in payload['hostScreenplay'] # old coverage remains separate
        assert 'FILM_CRAFT_READING' in system
        return response([{'domain':'LIGHTING','facts':{'sources':['Door-side practical lamp'],
            'directionAndQuality':'Lamp fixed beside the doorway; camera changes do not move the light.' if 'lamp stays' in selected_scene else 'Doorway shadow falls across the face as the actor turns; lamp remains in world space.'}}])
    p.creative.canon_author.client.transport=httpx.MockTransport(handler)
    base=CapabilityInput(run_id=run.run_id,operation_id='fixture-film:canon',scope=run.scope)
    await p.film.canon(base)
    directed=base.model_copy(update={'operation_id':'fixture-film:direction'})
    assert (await p.film.direction(directed)).status==ResultStatus.SUCCEEDED
    checkpoint=p.film.store.checkpoint(run.run_id)
    retained=p.screenplays.objects.read_ref(checkpoint.screenplay_ref)
    assert retained['screenplay']['text']==c.script.screenplay
    assert retained['selectedSceneScreenplays'][0]['directorNarrative']['film']['text']==film_text
    assert p.film.store.author(checkpoint.canon_ref,FilmCanon).script.screenplay==c.script.screenplay
    assert [k for k,_ in calls]==['canon','scene-writer','writer-decision','film-narrative','scene-narrative','coverage']
    unit=p.film.create_unit(directed,0)
    child=p.runtime.store.load(unit.creative_run_id)
    await p.creative.source(CapabilityInput(run_id=child.run_id,operation_id='fixture-child-source',scope=child.scope))
    professional_request=p.creative._request(CapabilityInput(run_id=child.run_id,operation_id='fixture-professional',scope=child.scope),Authority.PROFESSIONAL)
    designs=await p.professional_design.author.design(professional_request)
    assert ('Doorway shadow' if moving else 'camera changes do not move') in designs[0].facts['directionAndQuality']
    assert professional_request.shot.camera_intent == ('Follow the traveler' if moving else 'Fixed doorway view')
    count=len(calls)
    # Both film and child already have fixed coverage. Neither calls the new authors.
    await p.film.direction(directed.model_copy(update={'operation_id':'fixture-recovery'}))
    await p.creative._direction(CapabilityInput(run_id=child.run_id,operation_id='fixture-child-recovery',scope=child.scope))
    assert len(calls)==count
    assert p.film.store.checkpoint(run.run_id).direction_ref==checkpoint.direction_ref
    assert p.screenplays.objects.read_ref(checkpoint.screenplay_ref)==retained
    assert p.creative.state.checkpoint(child.run_id).package_ref is None
    # Simulate a historical handoff without any new Director layer. The frozen
    # Shot is sufficient for recovery; absence does not trigger backfill.
    old_context={k:v for k,v in professional_request.screenplay_context.items() if k!='directorNarrative'}
    old_pin=p.screenplays.objects.put('historical-fixture-handoff',old_context)
    cp=p.creative.state.checkpoint(child.run_id)
    p.creative.state.save(child.run_id,child.scope,cp.model_copy(update={'screenplay_ref':old_pin}))
    await p.creative._direction(CapabilityInput(run_id=child.run_id,operation_id='legacy-fixture-recovery',scope=child.scope))
    assert len(calls)==count
    assert p.screenplays.objects.read_ref(old_pin)==old_context
    # Host can select both levels on the existing full-film handoff without
    # rewriting its writer/Canon text or mutating the already frozen child.
    sid=next(iter(retained['directorNarrative']['scenes']))
    host_pin=await p.tools.invoke('screenplay.bind_director_narrative',handoff_ref=checkpoint.screenplay_ref,
        work_id=run.scope.work_id,scene_id=None,film_text='Host film voice and knowledge choice.',
        scene_texts={sid:'Host scene: remain outside the doorway after hearing.'},reason='Explicit Host choice')
    host_request=p.film.request(directed).model_copy(update={'screenplay_context':p.screenplays.objects.read_ref(host_pin)})
    selected=await native_director_narrative(p.screenplays,p.film.direction_author,host_request,operation='host-selected-only')
    assert selected['directorNarrative']['scenes'][sid]['selectedBy']=='HOST'
    assert len(calls)==count
    assert p.screenplays.objects.read_ref(checkpoint.screenplay_ref)==retained
    await p.aclose()


async def test_registered_host_scene_binding_preserves_writer(plugin):
    w=plugin.screenplays
    source_ref=w.retain_context(ContextOriginal(work_id='fixture',label='source',status='DESIGNATED_SOURCE',text='Source'))
    film_ref=w.retain_context(ContextOriginal(work_id='fixture',label='film',status='AUTHOR_CONCEPT',text=canon().script.screenplay))
    w.begin(session_id='scene-host',work_id='fixture',scene_id='one',scope='SCENE',goal='Local fixture',
            source_refs=(source_ref,film_ref),full_film_ref=film_ref)
    writer=w.retain_v1('scene-host',canon().scene.scene_text)
    w.decide('scene-host',choice='KEEP_ALL',reason='Keep writer original',expected_revision=1)
    pin=w.bind_selection('scene-host',work_id='fixture',scene_id='one')
    bound=await plugin.tools.invoke('screenplay.bind_director_narrative',handoff_ref=pin,work_id='fixture',scene_id='one',
        film_text='Hold spectator knowledge near the traveler.',scene_text='Listen without revealing the room.',reason='Host selection')
    context=w.objects.read_ref(bound)
    assert context['screenplayRef']==dump_contract(writer)
    assert context['directorNarrative']['scenes']['one']['selectedBy']=='HOST'
    req=generic_request(context)
    req.canon=canon()
    author=TextOnlyAuthor()
    await native_director_narrative(w,author,req,operation='selected-local')
    assert author.calls==[]
    assert w.objects.read_ref(writer)['text']==canon().scene.scene_text

from test_host_first_screenplay import plugin
