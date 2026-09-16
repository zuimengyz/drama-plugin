import copy
import pytest
from pydantic import ValidationError
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.authorial_voice import (AuthorialInterventionGate,AuthorialVoiceBudget,
 LiteraryCandidate,LiteraryProvenance,GATE_DIMENSIONS)
from drama_plugin.authorial_voice import evaluate_intervention

PIN={'ref':'scene:closure','fingerprint':'a'*64}
def gate():
 return AuthorialInterventionGate(workId='work:1',nodeId='closure',eventKind='VICTORY',sourcePins=[PIN])
def qualified():
 d=dump_contract(gate());d.update(visualSufficient=False,worldVoiceExhausted=True,literaryCodaEligibility='QUALIFIED',eligibilityReason='actual dramatic investment',
 findings={k:{'status':'QUALIFIED' if k!='VISUAL_SUFFICIENCY' else 'NOT_QUALIFIED','reason':'pinned scene observation','sourceRefs':['scene:closure']} for k in GATE_DIMENSIONS},
 intent={k:'specific literary reason' for k in ['whyNow','charactersCannotSay','imageAlreadySays','whatRemainsUnsaid','desiredAftertaste','whyThisForm','whyNotSilence']})
 return AuthorialInterventionGate.model_validate(d)
def candidate(form='SHORT_AUTHORIAL_SENTENCE'):
 return LiteraryCandidate(key='text',form=form,formRationale='earned local form',text='The door remained open.',
 provenance={'relation':'ORIGINAL_PROJECT_TEXT','epistemicStatus':'AUTHORIAL_INTERPRETATION'},semanticPosition='after the action',semanticMotifs=['open door'],emotionalFunction='uncertainty')
def budget():return AuthorialVoiceBudget(workId='work:1')

def test_default_no_intervention_and_no_forced_epitaph():
 r=evaluate_intervention(gate());assert r['decision']=='NO_AUTHORIAL_INTERVENTION' and not r['adopted']
 g=gate();g.event_kind='DEATH';assert evaluate_intervention(g)['decision']=='NO_AUTHORIAL_INTERVENTION'

def test_minor_role_and_major_role_can_both_receive_silence():
 g=qualified();g.findings['AUDIENCE_EMOTIONAL_INVESTMENT'].status='NOT_QUALIFIED'
 assert evaluate_intervention(g,candidate(),budget())['decision']=='NO_AUTHORIAL_INTERVENTION'
 g=qualified();g.visual_sufficient=True
 assert evaluate_intervention(g,candidate(),budget())['decision']=='NO_AUTHORIAL_INTERVENTION'

def test_visual_sufficiency_and_world_voice_suppress_even_qualified_text():
 for field in ['visual_sufficient','world_voice_exhausted']:
  g=qualified();setattr(g,field,field=='visual_sufficient')
  assert evaluate_intervention(g,candidate(),budget())['decision']=='NO_AUTHORIAL_INTERVENTION'

def test_non_death_can_qualify_but_never_adopts_or_judges_automatically():
 r=evaluate_intervention(qualified(),candidate(),budget())
 assert r['decision']=='AUTHORIAL_CANDIDATE_FOR_REVIEW'
 assert not any(r[k] for k in ['adopted','canonMutation','characterDialogueMutation','automaticMoralVerdict'])

def test_missing_intent_or_scarcity_memory_suppresses():
 assert evaluate_intervention(qualified(),candidate())['decision']=='NO_AUTHORIAL_INTERVENTION'
 g=qualified();g.intent=None
 assert evaluate_intervention(g,candidate(),budget())['decision']=='NO_AUTHORIAL_INTERVENTION'

@pytest.mark.parametrize('dimension',['REDUNDANCY_SCARCITY','OVER_EXPLANATION_RISK'])
def test_explicit_scarcity_and_over_explanation_findings_can_veto(dimension):
 g=qualified();g.findings[dimension].status='PARTIAL'
 assert evaluate_intervention(g,candidate(),budget())['decision']=='NO_AUTHORIAL_INTERVENTION'

def test_open_literary_form_and_no_text_coda_are_supported():
 c=candidate('CUSTOM:INVENTED_FRAGMENT');assert evaluate_intervention(qualified(),c,budget())['decision']=='AUTHORIAL_CANDIDATE_FOR_REVIEW'
 c=LiteraryCandidate(key='silent',form='NO_TEXT_VISUAL_CODA',formRationale='leave an object',semanticPosition='closure',emotionalFunction='pause')
 assert evaluate_intervention(qualified(),c,budget())['decision']=='NO_AUTHORIAL_INTERVENTION'

def test_provenance_quote_adapted_original_and_no_historical_canon_promotion():
 for relation,status in [('HISTORICAL_QUOTE','SOURCE_QUOTATION'),('ADAPTED_HISTORICAL_TEXT','PROJECT_ADAPTATION'),('ORIGINAL_PROJECT_TEXT','AUTHORIAL_INTERPRETATION')]:
  p=LiteraryProvenance(relation=relation,epistemicStatus=status,sourcePins=[PIN],sourceExcerpt='verified words',adaptationNote='changed wording')
  assert p.canonical_fact is False
  d=dump_contract(p);d['canonicalFact']=True
  with pytest.raises(ValidationError):LiteraryProvenance.model_validate(d)
 d=dump_contract(candidate());d['provenance']['epistemicStatus']='SOURCE_QUOTATION'
 with pytest.raises(ValidationError):LiteraryCandidate.model_validate(d)
 d=dump_contract(candidate());d['provenance']={'relation':'HISTORICAL_QUOTE','epistemicStatus':'SOURCE_QUOTATION','sourcePins':[PIN],'sourceExcerpt':'other text'}
 with pytest.raises(ValidationError,match='equal'):LiteraryCandidate.model_validate(d)

def test_historical_text_needs_sources_and_adaptation_note():
 with pytest.raises(ValidationError,match='pinned'):LiteraryProvenance(relation='HISTORICAL_QUOTE',epistemicStatus='SOURCE_QUOTATION')
 with pytest.raises(ValidationError,match='explain'):LiteraryProvenance(relation='ADAPTED_HISTORICAL_TEXT',epistemicStatus='PROJECT_ADAPTATION',sourcePins=[PIN],sourceExcerpt='source')

def test_each_intervention_raises_scarcity_duty_without_count_quota():
 c=candidate();d=dump_contract(budget());d['recentInterventions']=[{'key':'old','form':c.form,'semanticMotifs':['open door'],'emotionalFunction':c.emotional_function,'sourcePin':PIN}]
 b=AuthorialVoiceBudget.model_validate(d);r=evaluate_intervention(qualified(),c,b)
 assert r['decision']=='NO_AUTHORIAL_INTERVENTION'
 assert set(r['repetitionConcerns'][0]['concerns'])=={'FORM_REPETITION','SEMANTIC_REPETITION','EMOTIONAL_REDUNDANCY'}
 b.distinct_contribution_against['old']='new irreversible public meaning';b.repetition_explanations['old']='deliberate transformed recurrence'
 assert evaluate_intervention(qualified(),c,b)['decision']=='AUTHORIAL_CANDIDATE_FOR_REVIEW'
 d=dump_contract(b);d['recentInterventions'].append({**d['recentInterventions'][0],'key':'new-use','form':'OTHER','semanticMotifs':[],'emotionalFunction':'other'})
 assert evaluate_intervention(qualified(),c,AuthorialVoiceBudget.model_validate(d))['decision']=='NO_AUTHORIAL_INTERVENTION'

@pytest.mark.parametrize('field,value',[('voice','CHARACTER'),('characterDialogueMutation',True),('canonMutation',True),('status','ADOPTED'),('verdictMode','MORAL_VERDICT'),('dialogueText','replacement dialogue')])
def test_candidate_cannot_rewrite_dialogue_adopt_or_issue_automatic_verdict(field,value):
 d=dump_contract(candidate());d[field]=value
 with pytest.raises(ValidationError):LiteraryCandidate.model_validate(d)

def test_silence_cannot_hide_text_and_budget_cannot_leak_between_works():
 d=dump_contract(candidate());d['form']='NO_AUTHORIAL_INTERVENTION'
 with pytest.raises(ValidationError,match='Silence'):LiteraryCandidate.model_validate(d)
 b=budget();b.work_id='other'
 with pytest.raises(ValueError,match='another work'):evaluate_intervention(qualified(),candidate(),b)


@pytest.mark.parametrize('concern',['CHARACTER_REPETITION','NEARBY_INTERVENTION'])
def test_character_and_proximity_raise_duty_even_when_form_and_emotion_differ(concern):
 c=candidate();c.character_ids=('person:1',)
 d=dump_contract(budget());d['recentInterventions']=[{'key':'prior','form':'OTHER','semanticMotifs':[],
  'emotionalFunction':'different','sourcePin':PIN,'characterIds':['person:1'] if concern=='CHARACTER_REPETITION' else []}]
 d['nearbyInterventionKeys']=['prior'] if concern=='NEARBY_INTERVENTION' else []
 d['distinctContributionAgainst']={'prior':'new dramatic function'}
 b=AuthorialVoiceBudget.model_validate(d);r=evaluate_intervention(qualified(),c,b)
 assert r['decision']=='NO_AUTHORIAL_INTERVENTION'
 assert concern in r['repetitionConcerns'][0]['concerns']
 b.repetition_explanations['prior']='specific reason the recurrence transforms the earlier use'
 assert evaluate_intervention(qualified(),c,b)['decision']=='AUTHORIAL_CANDIDATE_FOR_REVIEW'


def test_nearby_keys_cannot_invent_interventions():
 with pytest.raises(ValidationError,match='actual-use ledger'):
  AuthorialVoiceBudget(workId='work:1',nearbyInterventionKeys=['nonexistent'])
