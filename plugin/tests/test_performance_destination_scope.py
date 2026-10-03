"""No network. Only a current approved Performance scope can exempt presence."""
from copy import deepcopy

import pytest
from pydantic import ValidationError

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.dpd import BeatDPD, DPDLayerState, LineDPD, PerformanceTargetRole, SceneDPD
from drama_plugin.creative_engine.contracts import Authority, DesignBody, Dialogue, Kind, SceneBody, ShotBody, SourceBody
from drama_plugin.creative_engine.store import CreativeVersionStore
from drama_plugin.dpd import compose_dpd
from drama_plugin.performance_coverage import validate_performance_target, validate_shot_dpd_coverage
from drama_plugin.professional_design.performance_scope import (
    PerformanceProjectionScope, PerformanceScopeWitness, ProjectionEvidence, SubjectProjection,
    read_performance_scope, retain_performance_scope)
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeScope
from test_formal_author_backends import model_output


@pytest.fixture
def setup(tmp_path):
    versions = CreativeVersionStore(tmp_path / 'owner')
    scope = RuntimeScope(work_id='scope-work', scene_id='scope-scene', shot_id='scope-shot')
    source = versions.write(writer=Authority.SOURCE, kind=Kind.SOURCE, scope=scope,
        body=SourceBody(goal='bounded proof', text='One exchange followed by a crossing to a distant presence.', spoken_language='en'),
        sources=(), operation='source')
    scene = versions.write(writer=Authority.CANON, kind=Kind.SCENE, scope=scope,
        body=SceneBody(scene_text='One exchange; a distant presence has no response.',
            dialogue=(Dialogue(id='line-1',speaker='adult',text='Go.'), Dialogue(id='line-2',speaker='child',text='Help.'))),
        sources=(source,), operation='scene')
    shot = versions.write(writer=Authority.DIRECTION, kind=Kind.SHOT, scope=scope,
        body=ShotBody.model_validate({**model_output('direction'), 'spokenIds':['line-1','line-2']}),
        sources=(source,scene), operation='shot')
    facts = {'beats': [
        {'id':'b1','actor':'adult','target':'child','objective':'Leave','obstacle':'Appeal','tactic':'Delegate'},
        {'id':'b2','actor':'child','target':'adult','objective':'Get help','obstacle':'Refusal','tactic':'Persist'},
        {'id':'b3','actor':'child','target':'distant presence', 'objective':'Not authored.',
         'obstacle':'Not authored.','tactic':'Not authored.',
         'note':'Spatial destination only; no authored response, dialogue or task; behavior expansion forbidden.'}]}
    professional = versions.write(writer=Authority.PROFESSIONAL,kind=Kind.PROFESSIONAL,scope=scope,
        body=DesignBody(domain='PERFORMANCE',facts=facts),sources=(source,scene,shot),operation='performance')
    decision = ArtifactReference(owner='user-decision',artifact_ref='user-decision:'+'a'*64,version=1)
    adopted_scene = versions.write(writer=Authority.CANON,kind=Kind.SCENE,scope=scope,
        body=versions.resolve(scene).body,sources=(source,),operation='adopt-scene',
        adoption_decision=decision,candidate_origin=scene)
    adopted_shot = versions.write(writer=Authority.DIRECTION,kind=Kind.SHOT,scope=scope,
        body=versions.resolve(shot).body,sources=(source,adopted_scene),operation='adopt-shot',
        adoption_decision=decision,candidate_origin=shot)
    adopted_performance = versions.write(writer=Authority.PROFESSIONAL,kind=Kind.PROFESSIONAL,scope=scope,
        body=versions.resolve(professional).body,sources=(source,adopted_scene,adopted_shot),operation='adopt-performance',
        adoption_decision=decision,candidate_origin=professional)
    evidence = tuple(ProjectionEvidence(field_path=('beats','2',key),value_hash=sha256_canonical(facts['beats'][2][key]))
                     for key in ('note','objective','obstacle','tactic','target'))
    subjects = (
        SubjectProjection(subject_ref='adult',source_target_label='adult',role='INTERACTIVE_PARTNER',beat_ids=('b1',),spoken_ids=('line-1',)),
        SubjectProjection(subject_ref='child',source_target_label='child',role='INTERACTIVE_PARTNER',beat_ids=('b2','b3'),spoken_ids=('line-2',)),
        SubjectProjection(subject_ref='destination',source_target_label='distant presence',role='NON_INTERACTIVE_DESTINATION',
            beat_ids=('b3',),spatial_presence_only=True,behavior_expansion_forbidden=True))
    declaration = PerformanceProjectionScope(scope=scope,performance_ref=adopted_performance,scene_ref=adopted_scene,
        shot_ref=adopted_shot,adoption_decision_ref=decision,evidence=evidence,subjects=subjects)
    pin = retain_performance_scope(versions,declaration,writer=Authority.PROFESSIONAL)
    witness = read_performance_scope(versions,pin)
    return versions,declaration,pin,witness


@pytest.mark.parametrize('requirement',['spoken_ids','reciprocal_actions','authored_responses','listener_tasks','objectives','obstacles','tactics','dramatic_exchanges'])
def test_actual_partner_obligations_cannot_be_exempted(setup,requirement):
    versions,d,pin,witness = setup
    subject = d.subjects[-1].model_dump()
    subject[requirement] = ('required-obligation',)
    with pytest.raises(ValidationError,match='PARTNER_DPD_REQUIRED'):
        SubjectProjection.model_validate(subject)
    active = d.subjects[0].model_dump()
    active[requirement] = ('line-1',) if requirement == 'spoken_ids' else ('required-obligation',)
    interactive = SubjectProjection.model_validate(active)
    revised = PerformanceProjectionScope.model_validate({**d.model_dump(),'subjects':(interactive,*d.subjects[1:])})
    new_pin = retain_performance_scope(versions,revised,writer=Authority.PROFESSIONAL)
    with pytest.raises(ValueError,match='PARTNER_DPD_REQUIRED'):
        validate_performance_target('adult',{},projection_scope=read_performance_scope(versions,new_pin))


def test_approved_noninteractive_destination_requires_no_fake_psychology(setup):
    _,_,_,witness = setup
    result = validate_performance_target('destination',{},projection_scope=witness)
    assert result == {'role':'NON_INTERACTIVE_DESTINATION','partnerDPDRequired':False,'status':'PARTNER_DPD_NOT_REQUIRED'}


def test_consumers_cannot_issue_or_deserialize_exemptions(setup):
    versions,d,pin,witness = setup
    with pytest.raises(ValueError,match='WRONG_WRITER'):
        retain_performance_scope(versions,d,writer=Authority.DIRECTION)
    with pytest.raises(ValueError,match='TRUSTED_PERFORMANCE_SCOPE_REQUIRED'):
        validate_performance_target('destination',{},projection_scope=d)
    spoof = PerformanceScopeWitness(object(),versions,pin)
    with pytest.raises(ValueError,match='TRUSTED_PERFORMANCE_SCOPE_REQUIRED'):
        validate_performance_target('destination',{},projection_scope=spoof)
    # The original interaction gate never interprets caller role strings as grants.
    from drama_plugin.performance_coverage import validate_interaction
    fields = ('speaker_ref','listener_ref','speaker_action','listener_action','speaker_target','listener_attention',
              'gaze_handoff','voice_handoff','physical_handoff','partner_cue','response_timing','next_beat_owner')
    direction = {k:'destination' for k in fields}
    direction['role'] = 'NON_INTERACTIVE_DESTINATION'
    with pytest.raises(ValueError,match='PARTNER_DPD_REQUIRED'):
        validate_interaction(direction,{})


@pytest.mark.parametrize('field',['action','response','reciprocalAction','listenerTask','objective','tactic'])
def test_new_background_response_invalidates_old_scope_and_cannot_be_reexempted(setup,field):
    versions,d,pin,witness = setup
    old = versions.resolve(d.performance_ref)
    candidate = versions.resolve(old.candidate_origin_ref)
    facts = deepcopy(candidate.body.facts)
    facts['additionalParticipant'] = {'actor':'destination',field:'Authored interaction now required.'}
    updated_candidate = versions.write(writer=Authority.PROFESSIONAL,kind=Kind.PROFESSIONAL,scope=d.scope,
        body=DesignBody(domain='PERFORMANCE',facts=facts),sources=candidate.source_refs,operation='revised-candidate')
    changed = versions.write(writer=Authority.PROFESSIONAL,kind=Kind.PROFESSIONAL,scope=d.scope,
        body=versions.resolve(updated_candidate).body,sources=old.source_refs,operation='revised-production',
        adoption_decision=d.adoption_decision_ref,candidate_origin=updated_candidate)
    fresh = CreativeVersionStore(versions.root)
    with pytest.raises(ValueError,match='PARTNER_DPD_REQUIRED.*STALE'):
        validate_performance_target('destination',{},projection_scope=read_performance_scope(fresh,pin))
    misleading = PerformanceProjectionScope.model_validate({**d.model_dump(),'performance_ref':changed})
    with pytest.raises(ValueError,match='PARTNER_DPD_REQUIRED'):
        retain_performance_scope(versions,misleading,writer=Authority.PROFESSIONAL)


def test_canonical_dialogue_cannot_be_declared_destination(setup):
    versions,d,_,_=setup
    counterfeit = d.subjects[-1].model_copy(update={'subject_ref':'adult'})
    misleading = PerformanceProjectionScope.model_validate({**d.model_dump(),'subjects':(counterfeit,d.subjects[1])})
    with pytest.raises(ValueError,match='PARTNER_DPD_REQUIRED.*spoken'):
        retain_performance_scope(versions,misleading,writer=Authority.PROFESSIONAL)


def test_source_evidence_mismatch_and_unbound_target_rejected(setup):
    versions,d,_,witness = setup
    corrupted = d.evidence[0].model_copy(update={'value_hash':'b'*64})
    misleading = PerformanceProjectionScope.model_validate({**d.model_dump(),'evidence':(corrupted,*d.evidence[1:])})
    with pytest.raises(ValueError,match='EVIDENCE_MISMATCH'):
        retain_performance_scope(versions,misleading,writer=Authority.PROFESSIONAL)
    with pytest.raises(ValueError,match='PARTNER_DPD_REQUIRED.*unbound'):
        validate_performance_target('arbitrary-person',{},projection_scope=witness)


def test_full_shot_gate_checks_all_lines_beats_and_presence_without_expansion(setup):
    versions,d,pin,witness=setup
    scene_dpd=SceneDPD(scene_id=d.scope.scene_id,source_fingerprint=sha256_canonical(versions.resolve(d.scene_ref).body),
        dramatic_purpose='A refused appeal changes its destination.',conflict_condition='Refusal',power_structure='Adult and child',
        direction=DPDLayerState(public_private_context='Public street'))
    beats={}
    snapshots={}
    for key,actor,target in [('b1','adult','child'),('b2','child','adult')]:
        beat=BeatDPD(scene_id=d.scope.scene_id,beat_id=key,actor=actor,obstacle='Approved obstacle',transition_trigger='Next source action',
            direction=DPDLayerState(objective='Approved task',interaction_target=target,tactic='Approved tactic',
                authority_position='Approved position',relationship_stance='Approved relation',internal_activation='HIGH',external_control='HIGH'))
        beats[key]=beat
        line_id='line-1' if actor=='adult' else 'line-2'
        snapshots[line_id]=compose_dpd(scene_dpd,beat,LineDPD(scene_id=d.scope.scene_id,beat_id=key,spoken_content_id=line_id,
            speaker=actor,dramatic_action='Approved tactic',observable_intent='Approved task',continuity='Source turn',change_from_previous='Source turn'))
    beats['b3']=BeatDPD(scene_id=d.scope.scene_id,beat_id='b3',actor='child',obstacle='Not authored.',
        transition_trigger='Approved crossing completes',direction=DPDLayerState(interaction_target='destination',
            performance_boundaries=('No reciprocal performance or response added.',)))
    result=validate_shot_dpd_coverage(projection_scope=witness,snapshots=snapshots,beats=beats)
    assert result['status']=='PASS' and result['spokenCount']==2 and result['beatCount']==3
    assert result['targetRequirements']['destination']['partnerDPDRequired'] is False
    assert beats['b3'].direction.objective is None and beats['b3'].direction.tactic is None
    with pytest.raises(ValueError,match='BEAT_DPD_COVERAGE_MISMATCH'):
        validate_shot_dpd_coverage(projection_scope=witness,snapshots=snapshots,beats={k:v for k,v in beats.items() if k!='b3'})
    with pytest.raises(ValueError,match='SPOKEN_DPD_COVERAGE_MISMATCH'):
        validate_shot_dpd_coverage(projection_scope=witness,snapshots={},beats=beats)
    fresh = read_performance_scope(CreativeVersionStore(versions.root),pin)
    assert validate_shot_dpd_coverage(projection_scope=fresh,snapshots=snapshots,beats=beats)==result
