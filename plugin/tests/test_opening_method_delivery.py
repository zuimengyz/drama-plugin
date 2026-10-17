"""Hand-authored offline inputs test real contracts/wires, never author/media quality."""
from copy import deepcopy
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest
from drama_plugin.creative_engine.author_projection import direction_projection, author_payload
from drama_plugin.creative_engine.backends import FormalDirectionAuthor, FormalCanonAuthor, DIRECTION_CRAFT
from drama_plugin.creative_engine.contracts import CreativeCheckpoint, Dialogue, Authority
from drama_plugin.creative_engine.diagnostics import AuthorResultFailure
from drama_plugin.film.contracts import FilmCanon, FilmDirection, CanonScene, LanguageMetadata, DeliveryProfile
from drama_plugin.runtime.contracts import CapabilityInput
from test_formal_author_backends import configured, REF
from test_event_scope_delivery import material, pipeline

SKILLS = Path(__file__).resolve().parents[1] / 'skills'
CASES = {
    'direct-silent-action': dict(
        purpose='Enter inside mutual work before attributing fault for a damaged delivery.',
        entry='A wet packet is already sliding at the counter edge.',
        actions=['The keeper catches the packet with one palm while the courier holds the loose cord.',
                 'The courier loosens the cord while the keeper continues bearing the weight.'],
        middle='The packet rests on the keeper palm and the cord remains taut.',
        exit='The keeper supports the packet freely; both can inspect its torn seal.',
        sounds=['A single paper scrape accompanies the catch.', 'The cord slides softly through the fingers.'],
        next='The keeper turns the torn seal toward the courier; both inspect it without another handoff.',
        next_exit='Both have seen the torn seal but neither has assigned blame.',
        next_sound='The seal paper crackles once as it turns.',
        relation='Cut on the supported packet to inspection; retain the unanswered question of responsibility.',
        words=None),
    'sound-before-source': dict(
        purpose='Share interrupted attention before revealing the caller need.',
        entry='The keeper folds a cloth behind a closed grille; the courier remains outside the view.',
        actions=['The unseen courier taps the grille twice; the keeper stops folding.',
                 'The keeper lays the cloth aside and listens without another tap.'],
        middle='The tapping has ended and the keeper hands are still on the cloth.',
        exit='The cloth is aside; the keeper is attending to the closed grille.',
        sounds=['Two offscreen taps interrupt the room tone before the caller becomes visible.',
                'No further tap; distant rain remains audible during listening.'],
        next='The keeper opens the grille and sees the courier holding a damaged packet.',
        next_exit='The open grille connects the two people and the damaged packet is visible.',
        next_sound='The grille hinge sounds only as it opens.',
        relation='Cut from listening to the grille opening; reveal the source without replaying the taps.',
        words=None),
    'retrospective-voice-and-ellipsis': dict(
        purpose='Let retrospective testimony coexist with an encounter whose answer remains unseen.',
        entry='The courier holds an opened letter while the keeper waits at the counter.',
        actions=['The courier studies the seal while retrospective speech addresses the audience.',
                 'The keeper begins reading the letter while the courier attends in silence.'],
        middle='The retrospective phrase has ended; the opened letter remains between them.',
        exit='The keeper is reading; the reply is not yet known.',
        sounds=['Paper rustles below the retrospective voice.', 'Only the room and the turning page remain.'],
        next_entry='After an approved interval, a sealed reply rests beside the opened letter.',
        next='The courier takes the sealed reply; the keeper leaves its contents unexplained.',
        next_exit='The courier has the sealed reply; its contents remain unknown.',
        next_sound='The reply lifts from the counter with a brief paper contact.',
        relation='Ellipsis omits the unobserved reading and writing interval; do not invent the reply contents.',
        words='Я помню.'),
}


@pytest.fixture(autouse=True)
def text_only(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('Opening checks forbid network and media/subprocess execution')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)
    monkeypatch.setattr(subprocess, 'Popen', deny)


def evidence(name, value):
    if folder := os.environ.get('OPENING_EVIDENCE_DIR'):
        root = Path(folder); root.mkdir(parents=True, exist_ok=True)
        (root / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2))


async def test_exact_method_loading_changes_direction_not_autonomous_v1(tmp_path, monkeypatch):
    p = configured(monkeypatch, tmp_path/'plugin')
    try:
        author = p.creative.direction_author
        assert author is p.film.direction_author
        current = author.system_contract()
        planning = (SKILLS/'shot-design/references/planning.md').read_text()
        assert current.count(planning) == 1
        assert author.film_system_contract().startswith(current)
        # Compare complete contracts after removing the new section in a temp
        # tree. This is a loading proof, not a keyword/creative quality test.
        start = planning.index('### When this group opens the work\n')
        end = planning.index('## 3. Give every Shot', start)
        before = planning[:start] + planning[end:]
        clone = tmp_path/'prior-skills'
        for rel in DIRECTION_CRAFT:
            path = clone/rel; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(before if rel=='shot-design/references/planning.md' else (SKILLS/rel).read_text())
        prior = FormalDirectionAuthor(author.client, clone)
        assert prior.system_contract() == current.replace(planning, before)
        assert prior.execution_fingerprint(film=True) != author.execution_fingerprint(film=True)
        assert FormalCanonAuthor(author.client, clone).film_original_system() == p.film.canon_author.film_original_system()
        assert planning not in p.film.canon_author.film_original_system()
        evidence('loading', dict(classification='REAL_LOCAL_LOADING_NO_AUTHOR_CALL',
            skillsRoot=str(author.skills_root), paths=DIRECTION_CRAFT,
            beforeSystem=prior.system_contract(), afterSystem=current,
            filmFingerprintBefore=prior.execution_fingerprint(film=True),
            filmFingerprintAfter=author.execution_fingerprint(film=True), autonomousV1Unchanged=True))
    finally:
        await p.aclose()


def scenario(name, *, following=False):
    c = CASES[name]; req, raw = material(single=following)
    spoken = bool(c['words']) and not following
    dialogue = (Dialogue(id='call', speaker='courier', text=c['words']),) if c['words'] else ()
    text = ' '.join([c['entry'], *c['actions'], c.get('next_entry',''), c['next'],
                    'Retrospective exact words: '+c['words'] if c['words'] else 'No speech.'])
    scene = req.canon.scene.model_copy(update={'scene_text':text,'dialogue':dialogue})
    req = req.model_copy(update={'source':req.source.model_copy(update={'text':text}),
        'canon':req.canon.model_copy(update={'scene':scene,
            'work':req.canon.work.model_copy(update={'interpretation':c['purpose'],'dramatic_intent':c['purpose'],
                'character_meaning':'The courier and keeper attend to an unresolved encounter.'}),
            'script':req.canon.script.model_copy(update={'screenplay':text})}),
        'shot':req.shot.model_copy(update={'spoken_ids':('call',) if spoken else (),
            'purpose':c['purpose'] if not following else 'Develop the encounter from the established relation.',
            'required_transition':c['relation'], 'entry_state':c.get('next_entry',c['exit']) if following else c['entry'],
            'exit_state':c['next_exit'] if following else c['exit'],
            'subject_action':c['next'] if following else ' '.join(c['actions']),
            'editing_relation':c['relation'], 'coverage':'Keep the current action and receiving person readable.',
            'camera_intent':'Follow the current interaction without an ornamental reset.'})})
    f = {d['domain']:d['facts'] for d in raw}
    actions = [c['next']] if following else c['actions']
    entries = [c.get('next_entry',c['exit'])] if following else [c['entry'],c['middle']]
    exits = [c['next_exit']] if following else [c['middle'],c['exit']]
    f['ACTION']['actionPhases'] = [dict(beatSelection=i,spokenSelections=[0] if spoken and i==0 else [],
        entryState=entries[i],action=action,observable=exits[i]) for i,action in enumerate(actions)]
    if not following: f['ACTION']['actionPhases'][1]['transition']='continuous'
    perf = f['PERFORMANCE']
    perf['sceneDPD'].update(dramaticPurpose=c['purpose'],conflictCondition='The response is unsettled.')
    perf['sceneDPD']['direction'].update(objective='Attend to the encounter',tactic='Allow a response')
    for beat in perf['beats']:
        beat.update(objective='Attend to the encounter',obstacle='The outcome is unsettled',
                    tactic='Read the partner action',physicalExpression='Attention stays with the partner; no added gesture.')
    perf['lines'] = [dict(spokenSelection=0,beatSelection=0,dramaticAction='Recall',
        observableIntent='Address the audience retrospectively',continuity='The encounter continues',
        changeFromPrevious='First and only phrase')] if spoken else []
    camera = f['CAMERA']['movement']; camera['policy']='Whole opening relation: '+c['purpose']
    camera['phaseDirections'] = [dict(phaseIndex=i,inheritedState=entries[i],
        decision='HOLD' if i==0 else 'CONTINUE',trigger='The current attention event.',
        motivation='Read the receiver as well as the object.',
        trajectory='Same counter-side view; preserve the listener in depth.',amplitude='None',
        endState=exits[i],sceneContext=c['purpose'],precedingBeatContext=c['entry'],
        followingBeatContext=c['next']) for i in range(len(actions))]
    f['SUBJECTS']['presentSubjects'][0]['inSceneBehaviour']='Keep the courier posture stable during the current exchange.'
    f['SUBJECTS']['presentSubjects'][1]['inSceneBehaviour']='Attend without an invented response.'
    f['SOUND'].update(ambience=[{'design':'Distant rain and room air remain continuous.'}],
        contactTiedSound=[{'phaseIndex':i,'design':s} for i,s in enumerate([c['next_sound']] if following else c['sounds'])],
        silence='Withhold score; do not remove the room.',
        audio_events=[dict(spokenSelection=0,delivery_mode='VOICE_OVER',performance='Retrospective address, outside the pictured encounter.',
            continuity='Speak once; the visible people do not lip-sync it.')] if spoken else [])
    f['EDITORIAL'].update(temporalStructure=c['relation'],
        protectedEvents=[{'phaseIndex':i,'design':'Retain the receiving opportunity until: '+state} for i,state in enumerate(exits)])
    return req,raw


@pytest.mark.parametrize('name', CASES)
async def test_group_contract_native_children_and_final_wires(name,tmp_path,monkeypatch):
    req,_ = scenario(name); second,_ = scenario(name,following=True)
    p = configured(monkeypatch,tmp_path/'group')
    try:
        run = p.create_source_film_run(work_id='opening-'+name,run_id='opening-'+name,source=req.source,
            languages=LanguageMetadata(source_document_language='en',original_work_language='ru',spoken_language='ru',authority_ref=REF),
            profile=DeliveryProfile(width=1280,height=720),rights_refs=(REF,),route='offline',model='offline-model')
        canon = FilmCanon(work=req.canon.work,script=req.canon.script,scenes=(CanonScene(scene_id='scene',scene=req.canon.scene),))
        p.film.store.put_author(run.run_id,canon)
        inp = CapabilityInput(run_id=run.run_id,scope=run.scope,operation_id='opening-contract')
        request = p.film.request(inp); rows=[]
        for i,original in enumerate((req.shot,second.shot)):
            body=original.model_dump(mode='json',by_alias=True); body.pop('spokenIds')
            body['spokenSelections']=[0] if original.spoken_ids else []
            rows.append(dict(sceneSelection=0,shot=body,requiresSelections=[] if i==0 else [0],transition='cut'))
        before=deepcopy(rows)
        result=FilmDirection.model_validate(direction_projection({'shots':rows},request,film=True))
        assert rows==before and result.shots[1].requires==(result.shots[0].shot_id,)
        p.film.store.put_author(run.run_id,result); traces=[]
        for i,directed in enumerate(result.shots):
            unit=p.film.create_unit(inp,i); child=p.runtime.store.load(unit.creative_run_id)
            p.creative.state.save(child.run_id,child.scope,CreativeCheckpoint(refs=unit.refs))
            child_req=p.creative._request(CapabilityInput(run_id=child.run_id,scope=child.scope,operation_id='inspect'),Authority.PROFESSIONAL)
            assert child_req.shot==directed.shot
            payload=author_payload(child_req)
            for key in ('purpose','requiredTransition','entryState','exitState','editingRelation'):
                assert payload['shot'][key]==rows[i]['shot'][key]
            _,raw=scenario(name,following=bool(i))
            downstream,_,_,out=await pipeline(tmp_path/f'wire-{i}',monkeypatch,child_req,raw,duration=None)
            try:
                texts=[o['wire']['content'][0]['text'] for o in out]
                for n,(row,text) in enumerate(zip(out,texts)):
                    action=raw[0]['facts']['actionPhases'][n]['action']
                    sound=next(d['facts'] for d in raw if d['domain']=='SOUND')['contactTiedSound'][n]['design']
                    assert action in text
                    # Existing finite-leaf formatting can join clauses with ';'.
                    assert all(part in text for part in sound.rstrip('.').split(' and '))
                    assert 'Distant rain' in text and 'room air remain continuous' in text
                    assert 'preserve the listener in depth' in text
                    assert 'Withhold score' in text and 'Retain the receiving opportunity' in text
                    assert row['wire']['duration']==-1 and not row['ready'].provider_submission_allowed
                    assert 'When this group opens the work' not in text
                    assert 'openingShotAnchor' not in text and 'FilmScorePlan' not in text
                    assert CASES[name]['purpose'] not in text
                if i==0:
                    assert out[1]['task'].unit.execution_context.boundary=='CONTINUE'
                    assert CASES[name]['actions'][0] not in texts[1]
                    assert CASES[name]['sounds'][0].rstrip('.') not in texts[1]
                    assert 'NEW SHOT START' not in texts[1] and CASES[name]['next'] not in texts[0]
                    if CASES[name]['words']:
                        assert texts[0].count('{'+CASES[name]['words']+'}')==1
                        assert CASES[name]['words'] not in texts[1]
                    else: assert not out[0]['task'].unit.spoken_ids
                traces.append(dict(direction=directed.model_dump(mode='json',by_alias=True),childPayload=payload,
                    finalRequests=[o['wire'] for o in out],submissionAllowed=[o['ready'].provider_submission_allowed for o in out]))
            finally: await downstream.aclose()
        for fault in ('source','extra-field'):
            bad=deepcopy(rows)
            if fault=='source':bad[0]['sceneSelection']=99
            else:bad[0]['shot']['openingPlan']={'firstSound':'invented parallel authority'}
            with pytest.raises(AuthorResultFailure):direction_projection({'shots':bad},request,film=True)
        evidence(name,dict(classification='HAND_AUTHORED_OFFLINE_CONTRACT_AND_WIRE_FIXTURE',
            modelCalls=0,mediaCalls=0,group=traces,negativeContractsRejected=['invalid-scene','openingPlan']))
    finally: await p.aclose()


async def test_semantically_bad_reintroduction_is_not_rewritten_by_compiler(tmp_path,monkeypatch):
    req,raw=scenario('direct-silent-action')
    repeated=raw[0]['facts']['actionPhases'][0]['action']
    raw[0]['facts']['actionPhases'][1]['action']=repeated
    p,_,_,out=await pipeline(tmp_path,monkeypatch,req,raw)
    try:
        # Contract acceptance is not creative acceptance: preserve a known bad
        # original to expose the owner defect, rather than inventing a repair.
        assert repeated in out[1]['wire']['content'][0]['text']
        evidence('negative-repeated-introduction',dict(classification='KNOWN_BAD_AUTHOR_INPUT_NOT_CREATIVE_PASS',
            wrongAction=repeated,finalRequest=out[1]['wire'],disposition='Return to creative owner, not a compiler gate.'))
    finally: await p.aclose()
