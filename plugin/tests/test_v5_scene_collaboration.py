"""Offline professional collaboration: real owners/author wire/compiler, no services.

The case decisions are Host-prepared fixtures, not model-authored or media proof.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import socket

import httpx
import pytest
from drama_plugin.creative_engine.author_projection import author_payload, direction_projection
from drama_plugin.creative_engine.contracts import Authority, CreativeCheckpoint, Dialogue, SceneBody
from drama_plugin.creative_engine.diagnostics import AuthorUnavailable
from drama_plugin.creative_engine.screenplay import ContextOriginal
from drama_plugin.film.contracts import FilmCanon, FilmDirection, CanonScene, LanguageMetadata, DeliveryProfile
from drama_plugin.runtime.contracts import CapabilityInput
from test_formal_author_backends import configured, REF
from test_event_scope_delivery import material, pipeline

CASES = sorted((Path(__file__).parent/'fixtures/v5_scene_collaboration').glob('*.json'))

@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('V5 offline validation forbids network/model/media calls')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)

def output(name, value):
    if dest := os.environ.get('V5_EVIDENCE_DIR'):
        path = Path(dest); path.mkdir(parents=True, exist_ok=True)
        (path/(name+'.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')

def scenario(case, slot):
    req, raw = material(single=True)
    row = case['shots'][slot]
    scene = SceneBody.model_validate({'sceneText':case['sourceExcerpt'],
        'subjects':[{'id':id,'name':name,'meaning':'Current selected scene participant'}
                    for id,name in zip(('courier','keeper'),case['people'])],
        'dialogue':case['dialogue']})
    ids = tuple(scene.dialogue[i].id for i in row['spoken'])
    req = req.model_copy(update={'source':req.source.model_copy(update={'text':case['sourceExcerpt'],'goal':case['intent']}), 'canon':req.canon.model_copy(update={'scene':scene,
        'script':req.canon.script.model_copy(update={'screenplay':(CASES[0].parent/'V4-screenplay-frozen.md').read_text()}),
        'work':req.canon.work.model_copy(update={'interpretation':case['intent'],
            'dramatic_intent':case['intent'],'character_meaning':'People share one inhabited space.'})}),
        'shot':req.shot.model_copy(update={'spoken_ids':ids,'duration_ms':row['duration'],
            'purpose':case['intent'],'required_transition':row['cut'],'entry_state':row['entry'],
            'exit_state':row['exit'],'subject_action':row['action'],'blocking_intent':case['world'],
            'camera_intent':row['camera'],'editing_relation':row['cut'],
            'performance_direction':'行动服务眼前的对象，等待者持续注意这件事。','coverage':row['label']})})
    f = {d['domain']:d['facts'] for d in raw}
    f['ACTION'].update(actionPhases=[{'beatSelection':0,'spokenSelections':list(range(len(ids))),
        'entryState':row['entry'],'action':row['action'],'observable':row['exit']}],
        physicalStateConstraints='物件的支撑随当前动作改变，不重复已经完成的操作。')
    perf=f['PERFORMANCE'];perf['sceneDPD']['dramaticPurpose']=case['intent']
    perf['sceneDPD']['conflictCondition']='The other person has a different immediate concern.'
    perf['lines']=[{'spokenSelection':i,'beatSelection':2 if scene.dialogue[index].speaker=='keeper' else 0,
        'dramaticAction':'Address the partner','observableIntent':'Speak during the current action',
        'continuity':'Speak once in the selected order','changeFromPrevious':'Current response'}
        for i,index in enumerate(row['spoken'])]
    for beat in perf['beats']:
        beat.update(objective='Attend to the current scene task',obstacle='The partner is occupied',
            tactic='Continue the selected work or wait',note='No extra action',
            transitionTrigger='The current action changes',physicalExpression='Attention follows the current task.')
    f['CAMERA']['movement']={'policy':row['camera']}
    f['WORLD'].update(setting=('旧木作坊台面，当前画框只见钱、布角与手。' if case['sourceScene']=='S01' and slot==0 else case['world']),physicalWorldRules='人物与道具在同一场所，改变机位不移动地标。')
    for i,s in enumerate(f['SUBJECTS']['presentSubjects']):
        s.update(role=case['people'][i],inSceneBehaviour='按当前行动与对象保持关系。')
    f['SOUND'].update(ambience=[{'design':'室内底声低。'}],contactTiedSound=[{'phaseIndex':0,'design':row['sound']}],
        audio_events=[{'spokenSelection':i,'delivery_mode':'OFF_SCREEN' if slot==0 else 'ON_SCREEN',
            'performance':'自然说话；提问在先，回答随后。','continuity':'仅在本次轮到说话时发声一次。'} for i in range(len(ids))])
    if len(ids)>1:
        f['SOUND']['speechRelations']=[{'spokenSelection':i,'targetSpokenSelection':i+1,'relation':'BEFORE'} for i in range(len(ids)-1)]
    f['EDITORIAL'].update(temporalStructure='保留当前动作的自然过程。',
        protectedEvents=[],spatialOrientation='换视点不改变人物与物件的实际位置。')
    return req,raw

@pytest.mark.parametrize('case_path', CASES, ids=lambda p:p.stem)
async def test_selected_scene_reaches_native_children_author_wire_and_provider_preview(case_path,tmp_path,monkeypatch):
    case=json.loads(case_path.read_text()); req,_=scenario(case,0)
    p=configured(monkeypatch,tmp_path/'owners')
    try:
        # Exercise the existing support and decision owner on the same complete
        # source. These are explicitly offline contributions by one Host.
        w=p.screenplays
        source=w.retain_context(ContextOriginal(work_id='V5-'+case['name'],label='Frozen V4 source',
            status='DESIGNATED_SOURCE',text=case['sourceExcerpt']))
        film=w.retain_context(ContextOriginal(work_id='V5-'+case['name'],label='Offline inherited framework',
            status='AUTHOR_CONCEPT',text=(case_path.parent/'V4-screenplay-frozen.md').read_text()))
        session='V5-'+case['name']
        w.begin(session_id=session,work_id=session,scope='SCENE',scene_id='scene',goal=case['intent'],
            source_refs=(source,film),full_film_ref=film,author_context={'classification':case['classification']})
        w.retain_v1(session,case['sourceExcerpt']); contributions=[]
        for role in ('director','blocking','camera','editorial'):
            packet=w.support_packet(session,specialty=role,question='Evaluate the same encounter before locking coverage')
            assert packet['original']['text']==case['sourceExcerpt']
            w.retain_support(session,specialty=role,text=case['contributions'][role],expected_revision=w.load(session).revision)
            contributions.append(packet)
        w.decide(session,choice='KEEP_ALL',reason='Keep inherited dramatic events; choose the separate offline coverage proposal. '+case['contributions']['hostDecision'],expected_revision=w.load(session).revision)
        selected=w.shot_handoff(session)
        run=p.create_source_film_run(work_id=session,run_id=session,source=req.source,
            languages=LanguageMetadata(source_document_language='zh',original_work_language='ru',spoken_language='ru',authority_ref=REF),
            profile=DeliveryProfile(width=1280,height=720),rights_refs=(REF,),route='offline',model='offline-model')
        p.film.store.put_author(run.run_id,FilmCanon(work=req.canon.work,script=req.canon.script,
            scenes=(CanonScene(scene_id='scene',scene=req.canon.scene),)))
        inp=CapabilityInput(run_id=run.run_id,scope=run.scope,operation_id='V5-offline')
        # Preserve the real selected scene in the parent, as the formal path does.
        p.film.save(inp,screenplay_ref=w.objects.put('V5-selected-scenes',{'selectedSceneScreenplays':[selected]}))
        rows=[]
        for i,row in enumerate(case['shots']):
            r,_=scenario(case,i); body=r.shot.model_dump(mode='json',by_alias=True);body.pop('spokenIds');body['spokenSelections']=row['spoken']
            rows.append({'sceneSelection':0,'shot':body,'requiresSelections':[] if i==0 else [i-1],'transition':row['transition']})
        directed=FilmDirection.model_validate(direction_projection({'shots':rows},p.film.request(inp),film=True))
        p.film.store.put_author(run.run_id,directed)
        traces=[]; child_pins=[]
        for i,ds in enumerate(directed.shots):
            unit=p.film.create_unit(inp,i);child=p.runtime.store.load(unit.creative_run_id)
            p.creative.state.save(child.run_id,child.scope,CreativeCheckpoint(refs=unit.refs))
            request=p.creative._request(CapabilityInput(run_id=child.run_id,scope=child.scope,operation_id='inspect'),Authority.PROFESSIONAL)
            payload=author_payload(request);context=payload['hostScreenplay']['sceneDirection']
            assert context['currentShotSelection']==i and len(context['shots'])==len(rows)
            assert 'sourceRefs' not in context
            assert [r['shot']['entryState'] for r in context['shots']]==[r['entry'] for r in case['shots']]
            assert request.screenplay_context['sceneDirection']['sourceRefs']
            assert context['shots'][i]['shot']['subjectAction']==request.shot.subject_action
            child_pins.append(p.creative.state.input(child.run_id).screenplay_ref)
            # Inspect the actual text backend envelope without making a text call.
            captured=[]
            def receive(r):
                captured.append(json.loads(r.content));return httpx.Response(503)
            p.professional_design.author.client.transport=httpx.MockTransport(receive)
            with pytest.raises(AuthorUnavailable):await p.professional_design.author.design(request)
            assert json.loads(captured[-1]['messages'][1]['content'])['hostScreenplay']['sceneDirection']==context
            for skill in ('blocking','cinematography','editorial-design'):
                assert (p.professional_design.author.skills_root/skill/'SKILL.md').read_text() in captured[-1]['messages'][0]['content']
            _,raw=scenario(case,i)
            from drama_plugin.film.media_units import boundary_for
            from types import SimpleNamespace
            with monkeypatch.context() as local:
                local.setattr('drama_plugin.film.media_units.phases_for', lambda *args: (None, raw[0]['facts']['actionPhases']))
                if i:
                    local.setattr('drama_plugin.film.media_units.unit_for_task', lambda *args: SimpleNamespace(shot_id=directed.shots[i-1].shot_id))
                film_boundary=boundary_for(p,run.run_id,unit,0,previous_task=object() if i else None)
            assert film_boundary==('START' if i==0 else {'cut':'CUT','match':'MATCH','continuous':'CONTINUE'}[case['shots'][i]['transition']])
            downstream,_,_,out=await pipeline(tmp_path/f'wire-{i}',monkeypatch,request,raw,duration=None)
            try:
                wire=out[0]['wire'];prompt=wire['content'][0]['text']
                assert case['shots'][i]['action'] in prompt
                assert case['shots'][i]['exit'] in prompt
                assert all(row['action'] not in prompt for j,row in enumerate(case['shots']) if j!=i)
                assert 'sceneDirection' not in prompt and 'V5-' not in prompt
                assert not out[0]['ready'].provider_submission_allowed
                traces.append({'label':case['shots'][i]['label'],'authorPayload':payload,
                    'pinnedContext':request.screenplay_context,'rawProfessionalOriginal':raw,
                    'providerPreview':wire,'submissionAllowed':False,'filmBoundarySelection':film_boundary,
                    'boundaryEvidence':'Real boundary selector with offline phase/predecessor inputs; no observed predecessor media or admitted boundary execution.'})
            finally:await downstream.aclose()
        # Parent revision must not silently replace any child's immutable context.
        old=[w.objects.read_ref(pin) for pin in child_pins]
        altered=directed.model_copy(update={'shots':(directed.shots[0].model_copy(update={
            'shot':directed.shots[0].shot.model_copy(update={'exit_state':'Changed parent proposal'})}),*directed.shots[1:])})
        p.film.store.put_author(run.run_id,altered)
        for i,pin in enumerate(child_pins):
            if i == 0:
                with pytest.raises(ValueError, match='Creative operation identity conflict'):
                    p.film.create_unit(inp,i)
            else:
                same=p.film.create_unit(inp,i)
                assert p.creative.state.input(same.creative_run_id).screenplay_ref==pin
            assert w.objects.read_ref(pin)==old[i]
        output(case['name'],{'classification':case['classification'],'modelCalls':0,'mediaCalls':0,
            'networkBlocked':True,'selectedScreenplay':selected,'contributions':case['contributions'],
            'traces':traces,'recovery':'Existing children retained their pinned context after parent revision; a revised proposal needs new children.'})
    finally:await p.aclose()
