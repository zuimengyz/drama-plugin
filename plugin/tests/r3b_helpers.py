"""Authored offline R3B fixtures. Helpers never infer or approve production data."""
from copy import deepcopy
from hashlib import sha256

from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.dpd import BeatDPD, DPDLayerState, LineDPD
from drama_plugin.contracts.screenplay_playability import BeatPlayability, LinePlayability
from drama_plugin.contracts.scene_dramaturgy import ResponseInterpretation
from drama_plugin.dpd import compose_dpd
from drama_plugin.scene_dramaturgy import AXES, scene_body_hash, dramaturgy_subject, carrier_text
from performance_direction_helpers import make_case


def carrier(scene, text, actor, target, role, *, line=None, cause=None, important=False, silence=None):
    if line:
        ref = 'spoken:' + line
    else:
        start = scene['content']['screenplayAction'].index(text)
        ref = f'action:{start}:{start + len(text)}'
    return dict(ref=ref, textHash=sha256(text.encode()).hexdigest(), actor=actor, target=target,
                role=role, causeRef=cause, important=important, silenceFunction=silence)


def authored_review(scene, dpds, *, concerns=()):
    refs = [x['ref'] for x in scene['content']['dramaturgy']['carriers']]
    findings = [dict(axis=axis, scope='SCENE', status='PASS', finding='SOURCE_PROCESS_REVIEWED',
        reason='Synthetic source locators and actor tasks were authored together; no claim of artistic outcome.',
        evidenceRefs=refs, repairOwner='scene-development') for axis in sorted(AXES)]
    for info in scene['content']['dramaturgy'].get('information', []):
        findings.append(dict(axis='INFORMATION_RELEASE', scope=info['informationRef'], status='PASS',
            finding='RELEASE_FUNCTION_REVIEWED', reason='The authored release serves the declared current choice.',
            evidenceRefs=refs, repairOwner='scene-development'))
    findings.extend(deepcopy(concerns))
    return dict(subjectHash=dramaturgy_subject(scene, dpds), author='fixture-author', reviewer='fixture-author',
                basis='SELF_AUDIT', isolationEvidence='Same-context offline fixture design, not independent review.',
                inputsReceived=['exact source scene', 'source carrier annotations', 'DPD'], findings=findings)


def synthetic_case(sid='scene'):
    base = make_case('intimate')
    scene = dict(id=sid, episodeId='episode', order=1, title='Synthetic causal exchange', location=None,
        content=dict(revisionId='r3b-test', characters=['speaker:repairer', 'partner'],
            screenplayAction='A waits by the door. B keeps facing the desk. A stays by the door. B turns toward A. A remains at the door.',
            spokenContent=[dict(id='L1', speakerKey='speaker:repairer', text='Follow me.', target='partner',
                                intent='Ask the partner to follow', performanceIntent='A direct request to the partner.'),
                           dict(id='L2', speakerKey='speaker:repairer', text='Then answer here.', target='partner',
                                intent='Request an answer without leaving', performanceIntent='Change the request after the refusal.')]))
    cs = []
    cs.append(carrier(scene, 'A waits by the door.', 'speaker:repairer', 'partner', 'STIMULUS'))
    cs.append(carrier(scene, 'Follow me.', 'speaker:repairer', 'partner', 'ACTION', line='L1', important=True))
    cs.append(carrier(scene, 'B keeps facing the desk.', 'partner', 'speaker:repairer', 'RESPONSE', cause=cs[1]['ref']))
    cs.append(carrier(scene, 'A stays by the door.', 'speaker:repairer', 'partner', 'REACTION', cause=cs[2]['ref']))
    cs.append(carrier(scene, 'Then answer here.', 'speaker:repairer', 'partner', 'ACTION', line='L2', cause=cs[2]['ref'], important=True))
    cs.append(carrier(scene, 'B turns toward A.', 'partner', 'speaker:repairer', 'RESPONSE', cause=cs[4]['ref']))
    cs.append(carrier(scene, 'A remains at the door.', 'speaker:repairer', 'partner', 'AFTERMATH', cause=cs[5]['ref']))
    scene['content']['dramaturgy'] = dict(sourceBodyHash=scene_body_hash(scene), carriers=cs,
        interactions=[dict(actionRef=cs[1]['ref'], responseRef=cs[2]['ref'], nextActionRef=cs[4]['ref'], strategyChange=True),
                      dict(actionRef=cs[4]['ref'], responseRef=cs[5]['ref'])], information=[],
        entryState={'relationship':'Trying to leave together'}, exitState={'relationship':'Remaining for an answer'},
        stateEvidence=[cs[0]['ref'], cs[-1]['ref']])
    sd = base['dpd'].scene.model_copy(update={'scene_id': sid, 'source_fingerprint': fp(scene)})
    dpds = {}
    for idx, action, reaction, objective, tactic in [
        (1, cs[1], cs[3], 'Get the partner to follow', 'Ask the partner to leave together'),
        (2, cs[4], cs[6], 'Get an answer here', 'Drop the demand to move and ask for an answer')]:
        ref = sid + ':spoken:L' + str(idx)
        direction = base['dpd'].beat.direction.model_copy(update={'objective': objective, 'tactic': tactic, 'interaction_target': 'partner'})
        bd = BeatDPD(scene_id=sid, beat_id=ref, actor='speaker:repairer', obstacle='The partner stays at the desk',
            transition_trigger='The partner stays facing the desk' if idx == 1 else 'The partner turns toward A', direction=direction,
            playability=playability(scene, action, reaction), response_interpretations=(ResponseInterpretation(
                action_ref=action['ref'], response_ref=cs[2 if idx == 1 else 5]['ref'],
                expected_response='The partner leaves the desk and follows' if idx == 1 else 'The partner turns and answers here',
                interpretation='The partner is not following' if idx == 1 else 'The partner offers attention, not yet an answer',
                transition_reason='Keeping the original direction frustrates the request to move; ask here instead' if idx == 1 else None,
                next_beat_id=sid + ':spoken:L2' if idx == 1 else None),))
        source_line = scene['content']['spokenContent'][idx - 1]
        ld = base['dpd'].line.model_copy(update={'scene_id': sid, 'beat_id': ref, 'spoken_content_id': source_line['id'],
            'speaker':'speaker:repairer', 'dramatic_action':source_line['intent'], 'direction': None,
            'playability':LinePlayability(source_text_hash=sha256(source_line['text'].encode()).hexdigest(),
                literal_meaning=source_line['intent'], speakability_review='Exact short request addressed to the source partner.', fragmentation='CONTINUOUS')})
        dpds[ref] = compose_dpd(sd, bd, ld)
    for idx in (2, 5):
        c = cs[idx]
        ref = sid + ':carrier:' + c['ref']
        dpds[ref] = BeatDPD(scene_id=sid, beat_id=ref, actor='partner', obstacle='A keeps requesting movement',
            transition_trigger=carrier_text(scene, c['causeRef']),
            direction=DPDLayerState(objective='Keep this exchange at the desk', interaction_target='speaker:repairer', tactic='Withhold movement' if idx == 2 else 'Offer attention without following'),
            playability=playability(scene, c, c))
    return dict(source=scene, scene_dpd=sd, dpds=dpds, review=authored_review(scene, dpds), carriers=cs, base=base)


def playability(scene, action, reaction):
    return BeatPlayability(source_scene_hash=fp(scene), source_excerpt=carrier_text(scene, action['ref']),
        playable_actions=({'actor': action['actor'], 'target': action['target'], 'behavior': carrier_text(scene, action['ref'])},),
        reaction={'actor':reaction['actor'], 'target':reaction['target'], 'behavior':carrier_text(scene, reaction['ref'])},
        performance_state='The authored carrier is maintained in this current exchange.',
        review_evidence='Source-authored behavior; no generated movement.',
        action_carrier_refs=(action['ref'],), reaction_carrier_ref=reaction['ref'])


def repin_case(case):
    scene = case['source']
    scene['content']['dramaturgy']['sourceBodyHash'] = scene_body_hash(scene)
    sd = case['scene_dpd'].model_copy(update={'source_fingerprint': fp(scene)})
    case['scene_dpd'] = sd
    for key, d in list(case['dpds'].items()):
        beat = d.beat if hasattr(d, 'effective') else d
        beat = beat.model_copy(update={'playability':beat.playability.model_copy(update={'source_scene_hash':fp(scene)})})
        case['dpds'][key] = compose_dpd(sd, beat, d.line) if hasattr(d, 'effective') else beat
    case['review'] = authored_review(scene, case['dpds'])
