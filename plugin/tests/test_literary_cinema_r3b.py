"""R3B causal/identity adversaries. No provider calls or creative source writes."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.dpd import DPDSnapshot
from drama_plugin.contracts.cinematic import ObservableAction
from drama_plugin.contracts.screenplay_playability import BeatPlayability
from drama_plugin.contracts.performance_direction import DirectorPerformanceIntent, PerformanceProjection
from drama_plugin.contracts.scene_dramaturgy import DramaturgyReview
from drama_plugin.dpd import compose_dpd
from drama_plugin.scene_dramaturgy import source_dramaturgy, review_scene_dramaturgy, dramaturgy_subject, validate_carrier_order
from drama_plugin.screenplay_playability import validate_exact_turn, dialogue_turn_fingerprint
from drama_plugin.performance_direction import validate_turn_direction, validate_projection
from drama_plugin.performance_coverage import full_performance_coverage_gate, resolve_shared_direction, STANDARD
from r3b_helpers import synthetic_case, authored_review, repin_case
from formal_performance_helpers import formal_case

sys.path.insert(0, str(Path(__file__).parents[1] / 'integration/fixtures'))


def gate(case):
    return review_scene_dramaturgy(case['source'], case['dpds'], case['review'])


def formal_gate(case):
    return full_performance_coverage_gate(case['inventory'], case['directions'],
        current_source_hash=case['source_hash'], contexts=case['contexts'], dpds=case['dpds'],
        formal_source=case['formal_source'], scene_dpds=case['scene_dpds'], dramaturgy_reviews=case['dramaturgy_reviews'])


def refreshed_review(case):
    case['review'] = authored_review(case['source'], case['dpds'])


def test_action_expected_actual_response_and_next_tactic_are_source_bound_and_pure():
    case = synthetic_case()
    before = deepcopy(case)
    assert gate(case)['status'] == 'PASS'
    assert case == before
    trace = case['dpds']['scene:spoken:L1'].beat.response_interpretations[0]
    assert trace.expected_response != trace.interpretation
    assert trace.response_ref == case['carriers'][2]['ref']
    assert trace.next_beat_id == 'scene:spoken:L2'
    receipt = gate(case)['causalCoverage'][0]
    assert receipt['expectedResponse'] == trace.expected_response
    assert receipt['actualResponseRef'] == trace.response_ref


def test_existing_scene_owner_can_author_facet_without_giving_it_to_director():
    from drama_plugin.professional import registry
    for source_type in ('LITERARY', 'HISTORICAL'):
        owners = registry(source_type)
        assert 'dramaturgy' in owners['scene-development'].can_create
        assert 'dramaturgy' not in owners['director'].can_create


def test_presence_without_response_edge_fails():
    case = synthetic_case()
    case['source']['content']['dramaturgy']['interactions'] = []
    repin_case(case)
    with pytest.raises(ValueError, match='NOT_SOURCE_INTERACTION'):
        gate(case)


@pytest.mark.parametrize('attack', ['expected', 'transition', 'next', 'listener'])
def test_missing_causal_explanation_or_listener_task_is_not_a_pass(attack):
    case = synthetic_case()
    key = 'scene:spoken:L1';d = case['dpds'][key]
    if attack == 'listener':
        case['dpds'] = {k:v for k,v in case['dpds'].items() if isinstance(v, DPDSnapshot)}
    else:
        trace = d.beat.response_interpretations[0]
        trace = trace.model_copy(update={'expected_response':'respond'} if attack == 'expected' else
                                 {'transition_reason':None} if attack == 'transition' else {'next_beat_id':None})
        case['dpds'][key] = compose_dpd(d.scene, d.beat.model_copy(update={'response_interpretations':(trace,)}), d.line)
    refreshed_review(case)
    result = gate(case)
    assert result['status'] == 'CONCERN'
    assert any(f['status'] == 'CONCERN' and f['repairOwner'] == 'dramatic-performance-direction' for f in result['findings'])


def test_different_tactic_strings_are_not_proof_of_strategy_change():
    case = synthetic_case();d=case['dpds']['scene:spoken:L1']
    trace=d.beat.response_interpretations[0].model_copy(update={'next_beat_id':'scene:spoken:L1'})
    case['dpds']['scene:spoken:L1']=compose_dpd(d.scene,d.beat.model_copy(update={'response_interpretations':(trace,)}),d.line)
    refreshed_review(case)
    assert any(f['finding']=='RESPONSE_TO_NEXT_TACTIC_REQUIRED' for f in gate(case)['findings'])


def test_source_action_order_cannot_be_changed_by_reordering_annotations():
    case=synthetic_case()
    cs=case['source']['content']['dramaturgy']['carriers']
    cs[0],cs[3]=cs[3],cs[0]
    with pytest.raises(ValueError,match='TEMPORAL_ORDER|ORDER_MISMATCH'):
        source_dramaturgy(case['source'])


def test_raise_then_withdraw_witness_cannot_reverse_source_even_when_both_substrings_exist():
    case=synthetic_case();d=case['dpds']['scene:spoken:L1']
    from r3b_helpers import carrier
    from drama_plugin.scene_dramaturgy import scene_body_hash
    scene={'id':'scene','content':{'characters':['speaker:repairer','partner'],
        'screenplayAction':'raise hand. withdraw hand.','spokenContent':[]}}
    cs=[carrier(scene,'raise hand.','speaker:repairer','partner','STIMULUS'),
        carrier(scene,'withdraw hand.','speaker:repairer','partner','AFTERMATH')]
    scene['content']['dramaturgy']=dict(sourceBodyHash=scene_body_hash(scene),carriers=cs,
        entryState={'hand':'down'},exitState={'hand':'withdrawn'},stateEvidence=[c['ref'] for c in cs])
    refs=(cs[1]['ref'],cs[0]['ref'])
    actions=tuple(ObservableAction(actor=d.beat.actor,target='partner',behavior=t) for t in ('withdraw hand.','raise hand.'))
    witness=BeatPlayability(source_scene_hash=fp(scene),source_excerpt='raise hand.',playable_actions=actions,
        reaction=actions[0],performance_state='Stops reaching',review_evidence='Two exact authored source actions.',
        action_carrier_refs=refs,reaction_carrier_ref=cs[1]['ref'])
    with pytest.raises(ValueError,match='PLAYABILITY_TEMPORAL_ORDER_MISMATCH'):
        validate_carrier_order(scene,d.beat.model_copy(update={'playability':witness}))


def test_trigger_cannot_be_labelled_as_reaction_to_later_action():
    case=synthetic_case()
    cs=case['source']['content']['dramaturgy']['carriers']
    cs[0]['role']='REACTION';cs[0]['causeRef']=cs[3]['ref']
    with pytest.raises(ValueError,match='TRIGGER_REACTION_ORDER_MISMATCH'):
        source_dramaturgy(case['source'])
    case=synthetic_case();d=case['dpds']['scene:spoken:L1']
    c=case['carriers'][0]
    witness=d.beat.playability.model_copy(update={'reaction_carrier_ref':c['ref'],
        'reaction':ObservableAction(actor=c['actor'],target=c['target'],behavior='A waits by the door.')})
    with pytest.raises(ValueError,match='TRIGGER_IS_NOT_REACTION'):
        validate_carrier_order(case['source'],d.beat.model_copy(update={'playability':witness}))


def add_information(case, **kwargs):
    cs=case['carriers']
    info=dict(informationRef='request',parts={'need':'Help is needed','destination':'Leave together'},
        releases=[dict(carrierRef=cs[1]['ref'],parts=['need','destination'],audience=True,characters=['partner'])], **kwargs)
    case['source']['content']['dramaturgy']['information']=[info]
    repin_case(case)


def test_premature_information_is_a_scene_concern_even_when_exact_dialogue_passes():
    case=synthetic_case();add_information(case,notBefore=case['carriers'][2]['ref'])
    d=case['dpds']['scene:spoken:L1']
    assert validate_exact_turn(case['source'],'L1',d)['text']=='Follow me.'
    result=gate(case)
    assert result['status']=='CONCERN'
    assert any(f['finding']=='DRAMATICALLY_PREMATURE' and f['repairOwner']=='scene-development' for f in result['findings'])
    assert result['informationCoverage'][0]['firstReleaseParts']==['need','destination']


def test_late_information_is_symmetric_and_checks_each_knowledge_subject():
    case=synthetic_case();add_information(case,neededBy=case['carriers'][1]['ref'],neededBySubjects=['AUDIENCE','partner'])
    assert any(f['finding']=='DRAMATICALLY_LATE' for f in gate(case)['findings'])
    info=case['source']['content']['dramaturgy']['information'][0]
    info['priorKnowledge']={'AUDIENCE':['need','destination'],'partner':['need','destination']}
    repin_case(case)
    assert gate(case)['status']=='PASS'


def test_justified_direct_exposition_passes_without_compulsory_resistance():
    case=synthetic_case()
    line=case['source']['content']['spokenContent'][0];line['text']='火车十分钟后开。'
    case['carriers'][1]['textHash']=sha256(line['text'].encode()).hexdigest()
    # The fixture changes its own synthetic exact source, not the literary film.
    d=case['dpds']['scene:spoken:L1']
    witness=d.beat.playability.model_copy(update={'source_excerpt':line['text'],
        'playable_actions':(ObservableAction(actor='speaker:repairer',target='partner',behavior=line['text']),)})
    ld=d.line.model_copy(update={'playability':d.line.playability.model_copy(update={'source_text_hash':sha256(line['text'].encode()).hexdigest()})})
    case['dpds']['scene:spoken:L1']=compose_dpd(d.scene,d.beat.model_copy(update={'playability':witness}),ld)
    add_information(case,directStatementReason='Already established travel context; the purpose is immediate deadline communication.')
    assert gate(case)['status']=='PASS'


def test_silence_refusal_can_cause_next_action_but_environment_has_no_psychology():
    case=synthetic_case()
    c=case['source']['content']['dramaturgy']['carriers'][2]
    c.update(role='SILENCE',silenceFunction='REFUSAL',important=True)
    repin_case(case)
    assert gate(case)['status']=='PASS'
    key='scene:carrier:'+c['ref'];case['dpds'].pop(key);refreshed_review(case)
    assert any(f['finding']=='SILENCE_DPD_REQUIRED' for f in gate(case)['findings'])
    case=synthetic_case();case['source']['content']['dramaturgy']['carriers'][0]['role']='ENVIRONMENT'
    with pytest.raises(ValueError,match='ENVIRONMENT_CANNOT_HAVE_ACTOR_PSYCHOLOGY'):
        source_dramaturgy(case['source'])


def test_review_is_versioned_and_cannot_claim_false_independence():
    case=synthetic_case();review=deepcopy(case['review']);review['basis']='INDEPENDENT_REVIEW'
    with pytest.raises(ValueError,match='DISTINCT_READER'):DramaturgyReview.model_validate(review)
    case['review']['subjectHash']='0'*64
    with pytest.raises(ValueError,match='STALE_DRAMATURGY_REVIEW'):gate(case)
    case=synthetic_case();case['review']['findings'][0]['evidenceRefs']=['invented']
    with pytest.raises(ValueError,match='EVIDENCE_UNBOUND'):gate(case)


async def test_formal_book_source_enumerates_two_interactions_not_one_generic_row(tmp_path):
    case=await formal_case(tmp_path/'formal.json')
    assert len(case['inventory']['interactions'])==6
    assert formal_gate(case)['status']=='FULL_PERFORMANCE_COVERAGE_READY'
    case['inventory']['interactions'].pop()
    with pytest.raises(ValueError,match='FORMAL_INVENTORY_MISMATCH:interactions'):formal_gate(case)


async def test_p0_two_legal_same_scene_directions_swapped_fail(tmp_path):
    case=await formal_case(tmp_path/'formal.json')
    assert formal_gate(case)['status']=='FULL_PERFORMANCE_COVERAGE_READY'
    a,b='war1:spoken:L1','war1:spoken:L2'
    case['directions'][a]['objective_ref'],case['directions'][b]['objective_ref']=b,a
    case['projections'][a],case['projections'][b]=case['projections'][b],case['projections'][a]
    with pytest.raises(ValueError,match='EXACT_DIALOGUE_TURN_MISMATCH'):formal_gate(case)


@pytest.mark.parametrize('attack',['speaker','target','same-text-speaker','text'])
def test_p0_speaker_target_and_text_are_part_of_turn_identity(attack):
    case=synthetic_case();d=case['dpds']['scene:spoken:L1']
    if attack in ('speaker','same-text-speaker'):
        # Same exact text/hash cannot excuse a different speaker, even with a
        # recomposed, internally consistent DPD snapshot.
        line=d.line.model_copy(update={'speaker':'partner'})
        bad=compose_dpd(d.scene,d.beat,line)
        with pytest.raises(ValueError,match='DIALOGUE_SPEAKER_MISMATCH'):
            validate_exact_turn(case['source'],'L1',bad)
    elif attack=='target':
        line=d.line.model_copy(update={'direction':d.beat.direction.model_copy(update={'interaction_target':'friend'})})
        bad=compose_dpd(d.scene,d.beat,line)
        with pytest.raises(ValueError,match='DIALOGUE_TARGET_MISMATCH'):
            validate_exact_turn(case['source'],'L1',bad)
    else:
        bad=d.model_copy(update={'line':d.line.model_copy(update={'playability':d.line.playability.model_copy(update={'source_text_hash':'0'*64})})})
        bad=compose_dpd(bad.scene,bad.beat,bad.line)
        with pytest.raises(ValueError,match='EXACT_DIALOGUE_TEXT_MISMATCH'):
            validate_exact_turn(case['source'],'L1',bad)


@pytest.mark.parametrize('change',['dialogue','target','dpd','scene-version','intent-turn','projection-turn','review'])
async def test_stale_director_intent_or_projection_fails(tmp_path,change):
    case=await formal_case(tmp_path/'formal.json')
    scene=case['formal_source'].tree['scenes'][0];key='war1:spoken:L1';d=case['dpds'][key]
    intent=case['intents']['war1'];pair=case['projections'][key];current=case['current']
    validate_turn_direction(scene,'L1',d,intent,pair,current)
    if change=='dialogue':scene['content']['spokenContent'][0]['text']+=' New words.'
    elif change=='target':scene['content']['spokenContent'][0]['target']='friend'
    elif change=='scene-version':scene['content']['revisionId']='later'
    elif change=='dpd':d=compose_dpd(d.scene,d.beat.model_copy(update={'obstacle':'different approved constraint'}),d.line)
    elif change=='intent-turn':intent=intent.model_copy(update={'turn_fingerprints':{'L1':'0'*64}})
    elif change=='projection-turn':pair['VOICE']=pair['VOICE'].model_copy(update={'turn_fingerprint':'0'*64})
    elif change=='review':current={**current,'dramaturgy:war1':'0'*64}
    with pytest.raises(ValueError):validate_turn_direction(scene,'L1',d,intent,pair,current)


async def test_target_coverage_row_cannot_point_at_another_listener(tmp_path):
    case=await formal_case(tmp_path/'formal.json');case['directions']['war1:spoken:L1']['target_ref']='friend'
    with pytest.raises(ValueError,match='EXACT_DIALOGUE_TARGET_MISMATCH'):formal_gate(case)


async def test_interaction_cannot_cover_wrong_response_by_same_listener(tmp_path):
    case=await formal_case(tmp_path/'formal.json')
    rows=[x for x in case['inventory']['interactions'] if x['scene']=='war1']
    case['directions'][rows[0]['ref']]['interaction']['listener_dpd']=case['directions'][rows[1]['ref']]['interaction']['listener_dpd']
    with pytest.raises(ValueError,match='LISTENER_CAUSAL_COVERAGE_MISMATCH'):formal_gate(case)


async def test_direction_density_requires_reasons_and_shared_language_is_not_another_intent(tmp_path):
    case=await formal_case(tmp_path/'formal.json')
    d=case['directions']['war1:spoken:L1'];d['detail']='STANDARD'
    with pytest.raises(ValueError,match='DIRECTION_DENSITY_REQUIRES_EXPANDED'):formal_gate(case)
    d['detail']='EXPANDED';d['density']['reason']=''
    with pytest.raises(ValidationError):formal_gate(case)
    rows={'scene':{'scene':'s','source_ref':'scenes:s',**{k:'Shared approved constraint' for k in STANDARD}},
          'turn':{'scene':'s','source_ref':'scenes:s','shared_ref':'scene','objective_ref':'exact-dpd','target_ref':'B','detail':'STANDARD'}}
    before=deepcopy(rows);out=resolve_shared_direction(rows)
    assert out['turn']['core']=='Shared approved constraint' and out['turn']['objective_ref']=='exact-dpd'
    assert rows==before


@pytest.mark.parametrize('where,field',[('director','objective'),('director','subtext'),('performance','subtext'),('performance','dialogueIntent')])
def test_no_new_psychological_or_dialogue_authority(where,field):
    case=synthetic_case()['base']
    model=DirectorPerformanceIntent if where=='director' else PerformanceProjection
    value=dump_contract(case['intent'] if where=='director' else case['visual'].director_performance)
    value[field]='Unapproved replacement'
    with pytest.raises(ValidationError,match='Extra inputs'):model.model_validate(value)


def test_adaptation_freedom_reuses_decisions_and_fails_on_unresolved_protected_fact():
    from literary_fixture import fixture
    from drama_plugin.contracts.creative_source import LiteraryPackage
    from drama_plugin.creative_source import adaptation_freedom_receipt, compile_source
    data=fixture();p=LiteraryPackage.model_validate(data)
    receipt=adaptation_freedom_receipt(p)
    assert receipt['authorizingOwner']=='literary-adaptation'
    assert receipt['decisions'][0]['whatChanged']==p.adaptation.decisions[0].expression
    review=next(x for x in data['reviews'] if x['authority']=='literary-adaptation')
    review['preservationChecks']['e1']['status']='CONCERN'
    with pytest.raises(ValueError,match='SOURCE_CRITICAL_PRESERVATION_UNRESOLVED'):
        compile_source(dict(source=data,jurisdiction='TEST',intendedUse='ADAPTATION'))
    review['preservationChecks']={}
    with pytest.raises(ValueError,match='PRESERVATION_REVIEW_REQUIRED'):
        compile_source(dict(source=data,jurisdiction='TEST',intendedUse='ADAPTATION'))
    assert compile_source(dict(source=data,jurisdiction='TEST',intendedUse='STUDY'))


def test_legacy_adaptation_verification_cannot_be_used_as_new_compilation_approval():
    from literary_fixture import fixture
    from drama_plugin.creative_source import _compile_source, compile_source, verify_screenplay_input
    data=fixture()
    next(r for r in data['reviews'] if r['authority']=='literary-adaptation')['preservationChecks']={}
    request=dict(source=data,jurisdiction='TEST',intendedUse='ADAPTATION')
    old=_compile_source(request,verify_legacy=True)  # recreate pre-R3B wire shape
    assert 'adaptationFreedomReceipt' not in old.resolved_input
    assert verify_screenplay_input(data,dump_contract(old))==old
    with pytest.raises(ValueError,match='PRESERVATION_REVIEW_REQUIRED'):compile_source(request)
    tampered=dump_contract(old);tampered['resolvedInput']['cinema']['expressions'][0]['shootableExpression']='A new event'
    with pytest.raises(ValueError,match='STALE_OR_TAMPERED'):verify_screenplay_input(data,tampered)


def test_identical_yes_from_two_speakers_cannot_exchange_direction():
    from drama_plugin.contracts.screenplay_playability import LinePlayability
    from performance_direction_helpers import make_case
    base=make_case('intimate')['dpd']
    scene={'id':'same-word','content':{'screenplayAction':'A remains seated. B remains standing.',
        'spokenContent':[{'id':'A-yes','speakerKey':'A','target':'B','text':'是。','intent':'Answer B','performanceIntent':'A brief answer.'},
                         {'id':'B-yes','speakerKey':'B','target':'A','text':'是。','intent':'Answer A','performanceIntent':'A brief answer.'}]}}
    sd=base.scene.model_copy(update={'scene_id':'same-word','source_fingerprint':fp(scene)})
    ds=[]
    for line,behavior in zip(scene['content']['spokenContent'],['A remains seated.','B remains standing.']):
        bd=base.beat.model_copy(update={'scene_id':'same-word','beat_id':line['id'],'actor':line['speakerKey'],
            'direction':base.beat.direction.model_copy(update={'interaction_target':line['target'],'tactic':'Answer the current question'}),
            'playability':BeatPlayability(source_scene_hash=fp(scene),source_excerpt=behavior,
                playable_actions=(ObservableAction(actor=line['speakerKey'],target=line['target'],behavior=behavior),),
                reaction=ObservableAction(actor=line['speakerKey'],target=line['target'],behavior=behavior),
                performance_state='Remain in the current conversation',review_evidence='Different speakers and targets on identical text.')})
        ld=base.line.model_copy(update={'scene_id':'same-word','beat_id':line['id'],'spoken_content_id':line['id'],
            'speaker':line['speakerKey'],'dramatic_action':line['intent'],'direction':None,
            'playability':LinePlayability(source_text_hash=sha256('是。'.encode()).hexdigest(),literal_meaning=line['intent'],
                speakability_review='Brief affirmative to the named partner.',fragmentation='CONTINUOUS')})
        ds.append(compose_dpd(sd,bd,ld))
        assert validate_exact_turn(scene,line['id'],ds[-1])['text']=='是。'
    with pytest.raises(ValueError,match='EXACT_DIALOGUE_TURN_MISMATCH'):
        validate_exact_turn(scene,'A-yes',ds[1])
    forged=compose_dpd(sd,ds[1].beat,ds[1].line.model_copy(update={'spoken_content_id':'A-yes'}))
    with pytest.raises(ValueError,match='DIALOGUE_SPEAKER_MISMATCH'):
        validate_exact_turn(scene,'A-yes',forged)


def test_prompt_remains_a_translator_after_upstream_gate_and_never_completes_missing_performance():
    from test_seedance_prompt_generator import sample
    from test_visual_prompt_ir import fact
    from drama_plugin.visual.video_prompt import compile_request_ir
    case=synthetic_case();assert gate(case)['status']=='PASS'
    r=sample();ir=deepcopy(r.prompt_ir)
    # An explicit approved source projection, not generator-authored intention.
    ir['video_temporal']['performance']=[fact('A remains at the door.',scope='CLIP')]
    r=r.model_copy(update={'prompt_ir':ir});before=deepcopy(r.model_dump())
    prompt=compile_request_ir(r)['prompt']
    assert 'A remains at the door.' in prompt
    assert 'Get an answer here' not in prompt and r.model_dump()==before
    ir=deepcopy(ir);ir['video_temporal']['performance']=[fact('sad',scope='CLIP')]
    with pytest.raises(ValueError,match='UNRESOLVED:performance:OBSERVABLE_CARRIER_REQUIRED'):
        compile_request_ir(r.model_copy(update={'prompt_ir':ir}))


def test_current_screenplay_fixture_has_not_been_rewritten():
    root=Path(__file__).parent/'fixtures/screenplay_r2'
    data=(root/'04-screenplay-r2.md').read_bytes()
    assert sha256(data).hexdigest()=='dae155c1d27e6091d8277e773fa22e1ca20b549e6a3e936322256a246b425c08'
    pack=json.loads((root/'performance-sidecar.json').read_text())
    assert sha256(data).hexdigest()==pack['screenplaySha256']


@pytest.mark.parametrize(('sid','expected'),[('S01','PASS'),('S02','CONCERN'),('S03','PASS'),('S04','PASS')])
def test_current_screenplay_diagnostics_preserve_silence_pressure_and_dream_unknown(sid,expected):
    from r3b_screenplay_diagnostics import diagnostic
    case=diagnostic(sid);before=deepcopy(case)
    result=gate(case)
    assert case==before
    assert result['status']==expected,result
    if sid=='S02':
        assert any(f['finding']=='DRAMATICALLY_PREMATURE' and f['repairOwner']=='scene-development' for f in result['findings'])
        assert case['source']['content']['spokenContent'][0]['text']=='先生……我妈妈出事了。跟我来，快！'
    if sid=='S04':
        assert not case['dpds'] and case['source']['content']['dramaturgy']['suspensionReason']


async def test_missing_new_handoff_cannot_fallback_in_formal_book(tmp_path):
    case=await formal_case(tmp_path/'formal.json')
    case['dramaturgy_reviews']={}
    with pytest.raises(ValueError,match='FORMAL_DRAMATURGY_REVIEW_REQUIRED'):formal_gate(case)


async def completed_book_case(tmp_path):
    from preproduction_helpers import make_case
    from music_fixture_builder import silent_plan
    case=await formal_case(tmp_path/'canonical.json')
    packet,review,current,artifacts=make_case(formal=case)
    current.update(case['current'])
    score=silent_plan(packet.scope_id,packet.source_pins,packet.intent_ref,case['intents'],'FORMAL')
    current.update({d.performance_intent_ref.key:d.performance_intent_ref.fingerprint for d in score.scene_music_decisions})
    reviewed={k:case[k] for k in ('inventory','directions','dramaturgy_reviews')}
    reviewed.update({k:{ref:dump_contract(v) for ref,v in case[k].items()} for k in ('scene_dpds','dpds','intents')})
    reviewed['score_plan']=dump_contract(score)
    reviewed['projections']={k:{ch:dump_contract(v) for ch,v in pair.items()} for k,pair in case['projections'].items()}
    case['self_review']={'verdict':'PASS','reviewedFingerprint':fp(reviewed),'sourcePins':case['formal_source'].pins,'routeRef':dump_contract(packet.route_ref)}
    return case,packet,review,current,artifacts,score


@pytest.mark.parametrize('attack',[None,'swap','intent','information-concern','review','listener-scope'])
async def test_actual_book_completion_consumes_new_gates(tmp_path,attack):
    from drama_plugin.preproduction import complete_production_book
    c,p,r,current,a,score=await completed_book_case(tmp_path)
    if attack=='swap':
        c['directions']['war1:spoken:L1']['objective_ref']='war1:spoken:L2'
        c['directions']['war1:spoken:L2']['objective_ref']='war1:spoken:L1'
    elif attack=='intent':c['intents']['war1']=c['intents']['war1'].model_copy(update={'dramaturgy_fingerprint':'0'*64})
    elif attack=='review':c['dramaturgy_reviews']={}
    elif attack=='listener-scope':
        intent=c['intents']['war1'];c['intents']['war1']=intent.model_copy(update={'dpd_fingerprints':intent.dpd_fingerprints[:2]})
    elif attack=='information-concern':
        finding=c['dramaturgy_reviews']['war1']['findings'][0]
        finding.update(status='CONCERN',finding='DRAMATICALLY_LATE',reason='A necessary premise was withheld at the current choice.')
    out=complete_production_book(p,r,current,a,performance=c,score_plan=score)
    assert out['status']==('DIRECTOR_PRODUCTION_BOOK_NOT_READY' if attack else 'DIRECTOR_PRODUCTION_BOOK_READY_FOR_USER_REVIEW'),out
    if attack=='swap':assert any('EXACT_DIALOGUE_TURN_MISMATCH' in x for x in out['missing'])
    assert out['productionAuthorized'] is False
