"""NON_NORMATIVE fixtures. Explicit data is never a runtime default."""
from copy import deepcopy
import pytest
from pydantic import ValidationError
from drama_plugin.contracts.directing_continuity import DirectorIntentPriority, SpatialContinuity, PhaseReadiness
PIN={'key':'fixture-source','kind':'DESIGN','fingerprint':'a'*64}
CASES=[
 ('court-conversation','The letter states the agreed terms','The receiver conceals recognition','Candle reflections','Table between sender and receiver','Sender left, receiver right; clerk enters rear centre'),
 ('civilian-street','The siblings retain distinct identities','One sibling takes the other’s load','Balanced shopfront framing','Walking line past the shop door','Walk left to right; neighbour enters from the doorway behind'),
 ('different-battle','The detachment receives the approved withdrawal order','The messenger completes the relay','Decorative banner motion','Courtyard gate to signal post','Withdraw into depth; courier crosses from right to left'),
]
def priority(case):
 name,fact,core,enrich,axis,direction=case
 # The message carrier is central here; its importance is not inferred from its object type.
 return dict(work_scope=name,intent_group_id=name+':opening',source_pins=[PIN],intent_priority=[
 dict(intent_id='fact',intent=fact,priority='P0',reason='Source fidelity'),
 dict(intent_id='core',intent=core,priority='P1',reason='Required dramatic change'),
 dict(intent_id='form',intent='Keep both participants readable',priority='P2',reason='Replaceable realization'),
 dict(intent_id='enrich',intent=enrich,priority='P3',reason='Optional appearance')],protected_intent=['fact','core'],degradable_intent=['form','enrich'],protect_first=['fact','core'],sacrifice_first=['enrich','form'],sacrifice_before=[['enrich','form'],['form','core']],never_sacrifice_for=[['core','enrich']],allowed_substitution='Choose another work-consistent position while preserving the receiving action',unresolved_conflict_policy='STOP_AND_REPORT_CONFLICT')
def spatial(case):
 return dict(work_scope=case[0],scope_id='opening',source_pins=[PIN],primary_axis=case[4],screen_direction=case[5],entry_direction='As explicitly stated in this work’s master',exit_direction='Retain the established destination',subject_relation='Receiver remains on the established side of sender',axis_mode='STABLE',allow_axis_cross=True,axis_cross_reason='A participant walks around the other',axis_cross_condition='Show the crossing or establish a new master before another directional action',reorientation_required=True,reorientation_anchor=case[4])
@pytest.mark.parametrize('case',CASES)
def test_cross_work_explicit_independent_priority_and_axis(case):
 p=DirectorIntentPriority.model_validate(priority(case)); a=SpatialContinuity.model_validate(spatial(case))
 assert DirectorIntentPriority.model_validate(p.model_dump(by_alias=True))==p
 assert SpatialContinuity.model_validate(a.model_dump(by_alias=True))==a
 assert a.primary_axis==case[4]
 assert p.intent_priority[1].intent==case[2]
 for token in ['Gaixia','N/M/F','Wujiang','Xiang Yu','horse','hero','southward']:
  assert token.lower() not in (p.model_dump_json()+a.model_dump_json()).lower()

def test_same_object_can_have_different_tiers_and_order():
 d=priority(CASES[0]);d['intent_priority'][1]['intent']='Letter transfer'; d['intent_priority'][3]['intent']='Background cup';a=DirectorIntentPriority.model_validate(d)
 d=priority(CASES[1]);d['intent_priority'][1]['intent']='Cup transfer';d['intent_priority'][3]['intent']='Background letter';b=DirectorIntentPriority.model_validate(d)
 assert a.intent_priority[1].priority==b.intent_priority[1].priority=='P1'
 # Different battle protects message visibility as P1, and places secondary performance at P2.
 d=priority(CASES[2]);d['intent_priority'][1]['intent']='Camera reveals the complete signal';d['intent_priority'][2]['intent']='Secondary listeners share one gesture';DirectorIntentPriority.model_validate(d)
@pytest.mark.parametrize('bad',['missing','p0_degradable','wrong_order','cycle','unknown','contradiction','duplicate'])
def test_invalid_priority_relations_rejected(bad):
 d=priority(CASES[0])
 if bad=='missing':d['degradable_intent']=['form']
 elif bad=='p0_degradable':d['intent_priority'][2]['priority']='P0'
 elif bad=='wrong_order':d['sacrifice_first']=['form','enrich']
 elif bad=='cycle':d['sacrifice_before']+=[['form','enrich']]
 elif bad=='unknown':d['never_sacrifice_for']=[['missing','enrich']]
 elif bad=='contradiction':d['never_sacrifice_for']=[['enrich','form']]
 else:d['intent_priority'].append(deepcopy(d['intent_priority'][0]))
 with pytest.raises(ValidationError):DirectorIntentPriority.model_validate(d)
@pytest.mark.parametrize('bad',['reset','cross','reason','anchor','mode'])
def test_axis_cannot_hide_reorientation(bad):
 d=spatial(CASES[0])
 if bad=='reset':d.update(axis_mode='RESET',allow_axis_cross=False,reorientation_required=False)
 elif bad=='cross':d['reorientation_required']=False
 elif bad=='reason':d['axis_cross_reason']=' '
 elif bad=='anchor':d['reorientation_anchor']=' '
 else:d.update(axis_mode='MOTIVATED_AXIS_CROSS',allow_axis_cross=False)
 with pytest.raises(ValidationError):SpatialContinuity.model_validate(d)
def test_static_conversation_needs_no_movement_default():
 d=spatial(CASES[0]);d.update(screen_direction='No travel; sender left and receiver right',entry_direction='Already seated',exit_direction='Remain seated',allow_axis_cross=False,reorientation_required=False,axis_cross_reason='No crossing needed',axis_cross_condition='Any changed setup requires a new declaration')
 assert SpatialContinuity.model_validate(d).axis_mode=='STABLE'
@pytest.mark.parametrize('assessment,blocking,result',[('MET',True,'READY'),('UNMET',False,'READY_WITH_NON_BLOCKING_GAPS'),('UNKNOWN',True,'BLOCKED'),('UNMET',True,'BLOCKED')])
def test_gate_separates_unknown_and_blocking(assessment,blocking,result):
 r=dict(requirement_id='binding',category='BINDING',required_state='BOUND',current_state='BOUND' if assessment=='MET' else 'UNKNOWN',assessment=assessment,blocking=blocking,evidence_refs=[PIN] if assessment=='MET' else [],reason='Fixture evidence')
 assert PhaseReadiness(work_scope='fixture',target_phase='next',requirements=[r],result=result).result==result
 if assessment=='MET':
  r['evidence_refs']=[]
  with pytest.raises(ValidationError):PhaseReadiness(work_scope='fixture',target_phase='next',requirements=[r],result=result)
def test_no_implicit_work_authority():
 for cls in [DirectorIntentPriority,SpatialContinuity,PhaseReadiness]:
  with pytest.raises(ValidationError):cls.model_validate({})
  assert not {'provider','retake','cuts','media'} & cls.model_fields.keys()
