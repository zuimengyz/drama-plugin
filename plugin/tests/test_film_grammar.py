"""NON_NORMATIVE explicit inputs. No fixture is a runtime default."""
from copy import deepcopy
import pytest
from pydantic import ValidationError
from drama_plugin.contracts.film_grammar import WorkDirectingAuthority, AestheticPairwiseReviewContract, EditorialIntentHandoff, AdaptiveIntentHandoff
from drama_plugin.contracts.director import DirectorWorkspace
PIN = {'key': 'source', 'kind': 'DESIGN', 'fingerprint': 'a' * 64}
CASES = (
 ('court', 'petition listener', 'A sealed petition changes who may answer', 'Wait across the table until the clerk grants access', 'ceremonial distance'),
 ('battle', 'signal keeper', 'An obscured signal delays withdrawal', 'Reveal the relay only after the flag clears the smoke', 'distributed survival'),
 ('civilian', 'ferry porter', 'A burden must change hands before the boat can leave', 'Remain at ordinary working height while another worker enters', 'ordinary cooperation'),
)
def authority(case):
 scope,owner,reason,execution,criterion=case
 return dict(work_scope=scope,source_pins=[PIN],grammar_rules=[dict(rule_id='g1',domain='attention',narrative_reason=reason,applies_when='The source event changes access',execution=execution,exception='A blocked sightline requires a new position',exit_condition='The receiver completes the task')],evolution=[dict(scope_id='opening',perceptual_owner=owner,narrative_change=reason,rule_ids=['g1'],realization=execution)],aesthetic_rules=[dict(rule_id='a1',stance='PREFER',criterion=criterion,reason=reason,succeeds_when=execution,fails_when='Unmotivated emphasis replaces the receiving action')])
@pytest.mark.parametrize('case',CASES)
def test_distinct_explicit_work_grammar_roundtrip(case):
 value=WorkDirectingAuthority.model_validate(authority(case))
 assert WorkDirectingAuthority.model_validate(value.model_dump(by_alias=True))==value
 assert value.work_scope==case[0] and value.evolution[0].perceptual_owner==case[1]
 assert value.grammar_rules[0].execution==case[3]
 assert 'hero' not in value.model_dump_json().lower()
def test_no_implicit_work_style_and_independent_inputs():
 with pytest.raises(ValidationError): WorkDirectingAuthority.model_validate({'work_scope':'new','source_pins':[PIN]})
 values=[WorkDirectingAuthority.model_validate(authority(c)) for c in CASES]
 assert len({x.grammar_rules[0].execution for x in values})==3
 assert len({x.aesthetic_rules[0].criterion for x in values})==3
@pytest.mark.parametrize('mutation',['empty_reason','unknown_rule','duplicate_rule','duplicate_scope','duplicate_pin'])
def test_reject_causality_and_reference_gaps(mutation):
 d=deepcopy(authority(CASES[0]))
 if mutation=='empty_reason': d['grammar_rules'][0]['narrative_reason']=' '
 elif mutation=='unknown_rule': d['evolution'][0]['rule_ids']=['missing']
 elif mutation=='duplicate_rule': d['grammar_rules']*=2
 elif mutation=='duplicate_scope': d['evolution']*=2
 else: d['source_pins']*=2
 with pytest.raises(ValidationError): WorkDirectingAuthority.model_validate(d)
def pair():
 return dict(source_pins=[PIN],constitution_ref=PIN,candidate_a=PIN,candidate_b={**PIN,'key':'candidate-b','fingerprint':'b'*64},evidence_refs=[],technical_difference='UNKNOWN',performance_difference='UNKNOWN',camera_difference='UNKNOWN',aesthetic_difference='UNKNOWN',constitution_alignment_a={'a1':'UNKNOWN'},constitution_alignment_b={'a1':'UNKNOWN'},artificiality_risk='UNKNOWN',overstatement_risk='UNKNOWN',generic_beauty_risk='UNKNOWN',preferred_candidate='UNDETERMINED',reason='No observation',confidence=0,human_review_required=True)
def test_interface_preserves_unknown_and_requires_evidence_for_preference():
 assert AestheticPairwiseReviewContract.model_validate(pair()).preferred_candidate=='UNDETERMINED'
 d=pair(); d['preferred_candidate']='A'
 with pytest.raises(ValidationError): AestheticPairwiseReviewContract.model_validate(d)
 d=pair(); d['candidate_b']=PIN
 with pytest.raises(ValidationError): AestheticPairwiseReviewContract.model_validate(d)
 d=pair(); d['constitution_alignment_b']={'other':'UNKNOWN'}
 with pytest.raises(ValidationError): AestheticPairwiseReviewContract.model_validate(d)
def test_interfaces_have_no_execution_or_disposition():
 assert 'disposition' not in AdaptiveIntentHandoff.model_fields
 assert 'edits' not in EditorialIntentHandoff.model_fields
 assert 'provider' not in WorkDirectingAuthority.model_fields
 assert 'media_hash' not in WorkDirectingAuthority.model_fields
def test_existing_workspace_serialization_not_extended_or_defaulted():
 value=DirectorWorkspace(workspace_id='w',scope_id='s',branch_id='b',source_pins=(PIN,))
 dumped=value.model_dump(by_alias=True)
 assert 'filmGrammar' not in dumped
 assert dumped['intentRefs']==()
