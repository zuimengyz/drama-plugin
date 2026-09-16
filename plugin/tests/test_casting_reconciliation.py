import copy
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.performance_casting import RoleArchetypeProfile, CastingFinding
from drama_plugin.contracts.casting_discriminants import (ArchetypeReference, RoleSaliencePolicy,
 VisualCastingPlan, VisualDiscriminant, AudienceAppealFinding)
from drama_plugin.casting_discriminants import compile_visual_discriminants, visual_selection_gate, validate_visual_plan
from drama_plugin.performance_casting import profile_fingerprint
from test_performance_casting import profile, review
from test_casting_discriminants import plan

def reconciled():
 p=profile();v=dump_contract(plan(p))
 v['saliencePolicy']={'definingDiscriminantIds':['outline']}
 v['discriminants'][0]['responsibility']='FACE_DIRECT'
 v['discriminants'][0]['geometricRegions']={k:{'measure':'width/length','lower':a,'upper':b} for k,a,b in [('n',.6,.7),('w',.9,1.0)]}
 return p,VisualCastingPlan.model_validate(v)

def reference(role):
 return ArchetypeReference(roleIdentity=role,referenceId='test-reference',sourceRef='source:game',sourceFingerprint='a'*64,
  properNames=['Lu Bu','吕布','Dynasty Warriors'],interpretation='mechanism only',
  transferablePrinciples=[{'key':'power-before-prettiness','mechanism':'preserve structural mass','discriminantIds':['outline']}],
  doNotTransfer=['exact-face','costume','personality'])

def test_optional_references_preserve_legacy_fingerprint_and_do_not_share_defaults():
 a=profile();b=profile();old=dump_contract(a)
 assert 'archetypeReferences' not in old and a.archetype_references==()
 a.archetype_references=(reference(a.identity),)
 assert b.archetype_references==() and b.archetypal_exaggeration is None
 assert profile_fingerprint(b)==sha256_canonical(old)

@pytest.mark.parametrize('other',['liu_bang','wujiang_tingzhang'])
def test_reference_cannot_move_into_other_role(other):
 p=profile();p.archetype_references=(reference(p.identity),)
 d=dump_contract(p);d['identity']=other
 with pytest.raises(ValidationError,match='ROLE_LEAK'):RoleArchetypeProfile.model_validate(d)

def test_reference_is_optional_role_scoped_and_never_inherited():
 d=dump_contract(reference('x'))
 for key,value in [('scope','GLOBAL'),('inheritByDefault',True),('usage','COPY_TARGET')]:
  bad=copy.deepcopy(d);bad[key]=value
  with pytest.raises(ValidationError):ArchetypeReference.model_validate(bad)

def test_mechanisms_extract_to_discriminants_without_reference_names():
 p,v=reconciled();p.archetype_references=(reference(p.identity),);v.profile_fingerprint=profile_fingerprint(p)
 c=compile_visual_discriminants(p,v,'n','FACE')
 assert c['referenceMechanisms'][0]['principles'][0]['discriminantIds']==['outline']
 assert 'narrow midface' in c['prompt'] and 'Lu Bu' not in c['prompt']
 v.appeal.channels[0].audience_effect='Copy Lu Bu face'
 with pytest.raises(ValueError,match='PROPER_NAME'):compile_visual_discriminants(p,v,'n','FACE')

def test_new_reference_cannot_waive_salience_with_legacy_plan():
 p=profile();p.archetype_references=(reference(p.identity),);v=plan(p)
 with pytest.raises(ValueError,match='SALIENCE_POLICY'):validate_visual_plan(p,v)

@pytest.mark.parametrize('field',['beautyIsSearchGate','optimizationMayReduceSalience'])
def test_role_salience_before_beauty_is_not_optional_booleans(field):
 with pytest.raises(ValidationError):RoleSaliencePolicy.model_validate({'definingDiscriminantIds':['x'],field:True})

def test_contrastive_search_rejects_overlapping_regions_even_with_different_labels():
 p,v=reconciled();d=dump_contract(v)
 d['discriminants'][0]['geometricRegions']['w']['lower']=.65
 with pytest.raises(ValidationError,match='mutually exclusive'):VisualCastingPlan.model_validate(d)

@pytest.mark.parametrize('responsibility,stage',[('BODY_SPATIAL','SCALE'),('SOCIAL_RELATIONAL','SOCIAL'),('PERFORMANCE','PERFORMANCE'),('STORY_ONLY',None)])
def test_responsibility_split_rejects_story_body_social_performance_as_face(responsibility,stage):
 d=dump_contract(plan(profile()).discriminants[0]);d.update(responsibility=responsibility,stage=stage)
 assert VisualDiscriminant.model_validate(d).stage==stage
 d['stage']='FACE'
 with pytest.raises(ValidationError,match='responsibility'):VisualDiscriminant.model_validate(d)

def test_selection_cannot_compensate_salience_with_beauty_or_auto_approve():
 p,v=reconciled();f=review(p,'FACE');s=review(p,'SCALE',prior=f.media);r=review(p,'PERFORMANCE',prior=s.media)
 for x in [f,s,r]:x.audience_appeal=AudienceAppealFinding(planFingerprint=sha256_canonical(v),primaryResponse='RESPECT',status='PASS',observation='screen appeal passes',proofLimit='test')
 assert visual_selection_gate(p,v,[f,s,r])['finalists']==[]
 f.findings['salience:outline']=CastingFinding(status='PARTIAL',observation='prettier but defining width diluted')
 assert visual_selection_gate(p,v,[f,s,r])['finalists']==[]
 f.findings['salience:outline'].status='PASS'
 result=visual_selection_gate(p,v,[f,s,r]);assert result['status']=='USER_SELECTION_REQUIRED'
 assert result['userApprovedWinner'] is None and result['formalPromotionAllowed'] is False
 assert visual_selection_gate(p,v,[f,s,r],purpose='CALIBRATION')['finalists']==[]

def test_role_scoped_appeal_does_not_change_other_roles():
 a,av=reconciled();b,bv=reconciled();before=dump_contract(bv.appeal)
 av.appeal.channels[0].mode='HEROIC';av.appeal.primary_response='AWE'
 assert dump_contract(bv.appeal)==before
 assert compile_visual_discriminants(a,av,'n','FACE')['appeal']!=compile_visual_discriminants(b,bv,'n','FACE')['appeal']

def test_controlled_exaggeration_requires_preserved_anatomy_and_salience():
 p,v=reconciled()
 from drama_plugin.contracts.casting_discriminants import ControlledArchetypalExaggeration
 p.archetypal_exaggeration=ControlledArchetypalExaggeration(mode='HEROIC_STYLIZATION',definingDiscriminantIds=['outline'],
  anatomicalLimit='live-action anatomy and coherent bone/skin',realismObservations=['articulated neck'],forbiddenDrifts=['cartoon'])
 v.profile_fingerprint=profile_fingerprint(p)
 c=compile_visual_discriminants(p,v,'n','FACE')
 assert 'live-action anatomy' in c['prompt'] and 'cartoon' in c['ForbiddenDrifts']
 p.archetypal_exaggeration.defining_discriminant_ids=('unknown',);v.profile_fingerprint=profile_fingerprint(p)
 with pytest.raises(ValueError,match='Exaggeration'):compile_visual_discriminants(p,v,'n','FACE')


def test_calibration_consumes_exaggeration_and_reference_choices_without_candidate_eligibility():
 p,v=reconciled()
 from drama_plugin.contracts.casting_discriminants import ControlledArchetypalExaggeration
 p.archetype_references=(reference(p.identity),)
 p.archetypal_exaggeration=ControlledArchetypalExaggeration(mode='HEROIC_STYLIZATION',definingDiscriminantIds=['outline'],
  anatomicalLimit='Exceptional structural scale with articulating live-action bone and skin.',
  realismObservations=['plausible articulated anatomy'],forbiddenDrifts=['cartoon'])
 v.profile_fingerprint=profile_fingerprint(p)
 c=compile_visual_discriminants(p,v,'n','FACE',purpose='CALIBRATION',calibration_conditions={'frame':'fixed neutral framing'})
 assert p.archetypal_exaggeration.anatomical_limit in c['prompt']
 assert 'aesthetic refinement must never reduce' in c['prompt']
 assert c['exaggerationProjection']['projectedChoices'][0]['line'] in c['prompt']
 assert c['referenceMechanisms'][0]['principles'][0]['projectedChoices'][0]['line'] in c['prompt']
 assert not c['approvalEligible']
 # Changing authored exaggeration must change actual calibration text, not just metadata.
 p.archetypal_exaggeration.anatomical_limit='Changed bounded anatomy requirement.'
 v.profile_fingerprint=profile_fingerprint(p)
 changed=compile_visual_discriminants(p,v,'n','FACE',purpose='CALIBRATION',calibration_conditions={'frame':'fixed neutral framing'})
 assert changed['prompt']!=c['prompt']
 assert 'Lu Bu' not in changed['prompt']
