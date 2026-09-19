"""NON_NORMATIVE_EXAMPLE: independent structured data, never current-film footage."""
from copy import deepcopy
import pytest
from drama_plugin.contracts.base import dump_contract,sha256_canonical
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.contracts.adaptive_direction import *
from drama_plugin.contracts.editorial_authority import EditorialUsability
from drama_plugin.contracts.sequence import FilmReview
from drama_plugin.contracts.film_grammar import AestheticPairwiseReviewContract
from drama_plugin.adaptive_direction import adaptive_review,fixture_receipt,downstream_overlay_handoff,pairwise_handoff,authorize_observation

CHECKS=['historical_provenance','character_arc','priority','performance','film_grammar','editorial','continuity_prop','continuity_costume','continuity_injury','continuity_position','continuity_knowledge','continuity_relationship','runtime','music_sound']
DIMS=['scenes','coverage','shots','cut_conditions','performance','continuity','runtime','music','sound','film_grammar','historical_claims']
CASES=[('court','The listener opens the letter before the speaker finishes','Wait for the closing words, then open the seal','PERFORMANCE'),('civilian','The basket receiver shifts weight once after taking the load','Keep the unplanned weight adjustment; it preserves the exchange','PERFORMANCE'),('different-battle','The withdrawing group reverses direction across the gate join','Keep the clear retreat fragment and replace only the reversed segment','SPATIAL')]

def fixture(case=CASES[0],kind='EDITORIAL_FIX',classification='MATERIAL_DEVIATION',priority='P3'):
 name,fact,instruction,domain=case;pin=SourcePin(key=name+'-authority',kind='DIRECTION',fingerprint='a'*64);current={pin.key:pin.fingerprint,name+'-evidence':'b'*64}
 e=ObservedMaterialEvidence(key='e',basis='STRUCTURED_FIXTURE',media_ref=name+'-media',media_hash='c'*64,shot_ref=name+'-shot',scene_id=name+'-scene',coverage_refs=[name+'-coverage'],director_intent_refs=[name+'-intent'],start=0,end=5,facts={'actions':[fact]},observation_confidence='HIGH',observer_type='STRUCTURED_FIXTURE',method='STRUCTURED_FIXTURE',evidence_refs=[SourcePin(key=name+'-evidence',kind='DIRECTION',fingerprint='b'*64)])
 u=EditorialUsability(asset_ref=e.media_ref,media_hash=e.media_hash,scene_id=e.scene_id,director_intent_ids=e.director_intent_refs,usable_ranges=[{'start':0,'end':5,'functions':['approved exchange']}],covered_requirements=['requirement'],continuity_status='PASS',axis_status='PASS',performance_status='PASS',audio_status='PASS',editorial_usability='USABLE_FULL',evidence_refs=['fixture-only'],basis='SYNTHETIC_FIXTURE')
 dev=DeviationAssessment(key='dev',domain=domain,classification=classification,intended_refs=[pin],observed_evidence_refs=['e'],difference=fact,judged_consequence='Source reception sequence is affected' if classification=='MATERIAL_DEVIATION' else 'Unplanned motion keeps approved action and relationship',affected_priority_ids=['approved-priority'],priority_impact=priority)
 d=AdaptiveDecision(key=name+'-decision',media_ref=e.media_ref,evidence_refs=['e'],deviations=[dev],decision=kind,what_worked=['Stable face and voice in stipulated usable segment'],what_failed=['Only scoped order mismatch'] if classification=='MATERIAL_DEVIATION' else [],what_is_preserved=['Approved material outside the identified mismatch'],what_changes=['Scoped implementation only'] if kind!='KEEP' else [],lower_cost_options={'KEEP':'Would retain the identified defect'},artistic_judgment={'causal_clarity':'Requires intact receipt; decorative appearance cannot substitute'},editorial_usability_ref=sha256_canonical(u),authority_refs=[pin],next_action=instruction)
 return e,u,d,current,fixture_receipt(e,work_id=name,approved_priorities={'approved-priority':priority if priority!='NONE' else 'P3'})

def surprise(d):
 d.surprise=SurpriseAssessment(expected='Approved exchange completes',unexpected_evidence_refs=['e'],why_potentially_better='Weight transfer remains visible without a decorative insert',added_character_or_action_value='The receiver adjusts under the actual load rather than posing',checks={k:'PASS' for k in CHECKS},check_reasons={k:'Fixture stipulates this boundary unchanged; independently checked' for k in CHECKS})
 d.downstream_impact=AdaptiveDownstreamImpact(overlay_id='future-overlay',base_authority=d.authority_refs,parent_revision_ref=d.authority_refs[0],affected={k:() for k in DIMS},dispositions={k:'No change in this fixture' for k in DIMS},preserved_media_refs=[d.media_ref])
 return d

@pytest.mark.parametrize('case',CASES)
def test_independent_work_decision_preserves_and_does_not_execute(case):
 e,u,d,c,r=fixture(case);v=adaptive_review(d,[e],u,r,c)
 assert v['status']=='DRY_RUN_DECISION_PROPOSAL_READY' and not v['executionAuthorized'] and not v['formalMediaAuthorized']
 review=FilmReview(media_hash=e.media_hash,duration=5,observed_material_evidence=[e],adaptive_decisions=[d],editorial_usability=[u]);assert review.adaptive_decisions

@pytest.mark.parametrize('defect',['judgment-as-fact','technical-acting','frames-order','silent-audio','live-fixture','live-without-review','bad-range'])
def test_observation_honesty(defect):
 e,*_=fixture();raw=dump_contract(e)
 if defect=='judgment-as-fact':raw['facts']={'actions':['表演很差']}
 if defect=='technical-acting':raw.update(basis='OBSERVED_MEDIA',observerType='TECHNICAL_RUNTIME',method='TECHNICAL',factReviewRef=dict(key='f',kind='DIRECTION',fingerprint='a'*64))
 if defect=='frames-order':raw.update(basis='OBSERVED_MEDIA',observerType='HUMAN',method='FRAMES',facts={'action_order':['one before two']},factReviewRef=dict(key='f',kind='DIRECTION',fingerprint='a'*64))
 if defect=='silent-audio':raw.update(basis='OBSERVED_MEDIA',observerType='HUMAN',method='NORMAL_VIDEO',facts={'audio_events':['spoken words']},factReviewRef=dict(key='f',kind='DIRECTION',fingerprint='a'*64))
 if defect=='live-fixture':raw['basis']='OBSERVED_MEDIA'
 if defect=='live-without-review':raw.update(basis='OBSERVED_MEDIA',observerType='HUMAN',method='NORMAL_AV')
 if defect=='bad-range':raw['end']=0
 with pytest.raises(ValueError):ObservedMaterialEvidence(**raw)

@pytest.mark.parametrize('defect',['missing-evidence','stale-source','wrong-media','wrong-shot','wrong-coverage','stale-dailies','fact-hash','fixture-promoted'])
def test_binding_fail_closed(defect):
 e,u,d,c,r=fixture()
 if defect=='missing-evidence':d.evidence_refs=('absent',)
 if defect=='stale-source':c['court-authority']='x'*64
 if defect=='wrong-media':r['mediaRef']='other'
 if defect=='wrong-shot':r['shotRef']='other'
 if defect=='wrong-coverage':r['coverageRefs']=['other']
 if defect=='stale-dailies':d.editorial_usability_ref='x'*64
 if defect=='fact-hash':e.media_hash='f'*64
 if defect=='fixture-promoted':r['basis']='OBSERVED_MEDIA'
 with pytest.raises(ValueError):adaptive_review(d,[e],u,r,c)

def test_unknown_not_completed_or_rejected():
 e,u,d,c,r=fixture();e.uncertain_observations=('Hand occluded during receipt',);d.deviations[0].classification='OBSERVATION_UNCERTAIN';v=adaptive_review(d,[e],u,r,c)
 assert 'OBSERVATION_REQUIRED' in v['issues']

@pytest.mark.parametrize('kind',['TARGETED_PICKUP','TARGETED_RETAKE','ROUTE_CHANGE','UPSTREAM_REWRITE','REJECT'])
def test_no_automatic_expensive_decision(kind):
 e,u,d,c,r=fixture();d.decision=kind
 with pytest.raises(ValueError):adaptive_review(d,[e],u,r,c)

@pytest.mark.parametrize('priority,issue',[('P0','BLOCK_HUMAN_REVIEW_REQUIRED'),('P1','P1_EXPLICIT_REVIEW_REQUIRED'),('P2','FILM_GRAMMAR_EQUIVALENCE_REQUIRED')])
def test_authority_escalation(priority,issue):
 e,u,d,c,r=fixture(priority=priority);assert issue in adaptive_review(d,[e],u,r,c)['issues']

def test_surprise_has_all_gates_and_future_overlay():
 e,u,d,c,r=fixture(CASES[1],classification='POSITIVE_SURPRISE_CANDIDATE',priority='NONE');d=surprise(d);d.decision='KEEP_SURPRISE'
 v=adaptive_review(d,[e],u,r,c);assert not v['issues']
 with pytest.raises(ValueError):downstream_overlay_handoff(d,v,current_sources=c,reviewed_decision_fingerprint=None)
 out=downstream_overlay_handoff(d,v,current_sources=c,reviewed_decision_fingerprint=sha256_canonical(d));assert out['writes']==0 and out['fixtureOnly']
 for key in CHECKS:
  bad=d.model_copy(deep=True);bad.surprise.checks[key]='UNKNOWN';assert 'SURPRISE_GATE_NOT_PASSED' in adaptive_review(bad,[e],u,r,c)['issues']
 bad=d.model_copy(deep=True);bad.downstream_impact.affected['historical_claims']=('invented claim',);assert 'HISTORICAL_AUTHORITY_REQUIRED' in adaptive_review(bad,[e],u,r,c)['issues']

def test_positive_different_does_not_become_retry():
 e,u,d,c,r=fixture(CASES[1],kind='KEEP',classification='ACCEPTABLE_VARIATION',priority='NONE');v=adaptive_review(d,[e],u,r,c);assert not v['issues'] and v['decision']=='KEEP'

def test_redirection_is_delta_not_new_psychology():
 e,u,d,c,r=fixture();red=PerformanceRedirection(subject='recipient',intended_behavior='Open after completed line',observed_evidence_refs=['e'],performance_deviation_ref='dev',preserve=['voice','face','initial posture'],change=['hand release timing'],minimal_correction='Delay the hand action until the sentence ends',next_take_instruction='Keep your hand on the letter until the closing words; then open the seal.',scope='hand timing only',confidence='HIGH',authority_refs=d.authority_refs);d.performance_redirection=red;assert not adaptive_review(d,[e],u,r,c)['issues']
 for instruction in ['更克制一点','更悲伤','更高级']:
  with pytest.raises(ValueError):PerformanceRedirection(**{**dump_contract(red),'nextTakeInstruction':instruction})

def pair():
 e,u,d,c,r=fixture();b=e.model_copy(deep=True);b.key='b';b.media_ref='candidate-b';b.media_hash='d'*64
 review=AestheticPairwiseReviewContract(source_pins=d.authority_refs,constitution_ref=d.authority_refs[0],candidate_a=dict(key=e.media_ref,kind='MEDIA',fingerprint=e.media_hash),candidate_b=dict(key=b.media_ref,kind='MEDIA',fingerprint=b.media_hash),evidence_refs=e.evidence_refs,technical_difference='A has sharper decorative highlights',performance_difference='B keeps receiver visible',camera_difference='A rotates away before receipt; B holds shared relation',aesthetic_difference='B preserves causality',constitution_alignment_a={'receipt':'CONFLICT'},constitution_alignment_b={'receipt':'ALIGNED'},artificiality_risk='A overly uniform motion',overstatement_risk='A decorative emphasis',generic_beauty_risk='A loses specificity',preferred_candidate='B',reason='B shows the recipient completing receipt before the sender leaves',confidence=.8,human_review_required=True,work_id='court',coverage_refs=e.coverage_refs,director_intent_refs=e.director_intent_refs,sound_difference='Same stipulated words',candidate_risks={'A':{'overstatement':'HIGH'},'B':{'overstatement':'LOW'}})
 return review,e,b,c

def test_pairwise_pretty_can_lose_but_feedback_not_invented():
 r,a,b,c=pair();v=pairwise_handoff(r,a,b,c);assert v['preferredCandidate']=='B' and v['userPreference']=='UNSPECIFIED' and not v['modelLearningClaimed']
 r.user_preference='A'
 with pytest.raises(ValueError):pairwise_handoff(r,a,b,c)
 r.user_preference='UNSPECIFIED';b.coverage_refs=('different',)
 with pytest.raises(ValueError):pairwise_handoff(r,a,b,c)

def test_filmreview_retains_evidence_separation_and_cannot_fake_live():
 e,u,d,c,r=fixture();review=FilmReview(media_hash=e.media_hash,duration=5,observed_material_evidence=[e],adaptive_decisions=[d]);from drama_plugin.sequence import film_review_verdict
 assert film_review_verdict(review,e.media_hash)['status']=='ADAPTIVE_DRY_RUN_ONLY'
 raw=dump_contract(e);raw.update(basis='OBSERVED_MEDIA',observerType='HUMAN',method='NORMAL_AV',factReviewRef=dump_contract(d.authority_refs[0]));live=ObservedMaterialEvidence(**raw)
 with pytest.raises(ValueError):FilmReview(media_hash=e.media_hash,duration=5,observed_material_evidence=[live])
 assert 'adaptiveDecisions' not in dump_contract(FilmReview(media_hash='a'*64,duration=5))


def test_candidate_cannot_bypass_surprise_with_keep_or_downgrade_priority():
 e,u,d,c,r=fixture(CASES[1],kind='KEEP',classification='POSITIVE_SURPRISE_CANDIDATE',priority='NONE')
 assert 'SURPRISE_REVIEW_REQUIRED_BEFORE_KEEP' in adaptive_review(d,[e],u,r,c)['issues']
 e,u,d,c,r=fixture();r['priorityLevels']['approved-priority']='P1'
 with pytest.raises(ValueError,match='downgrade'):adaptive_review(d,[e],u,r,c)

def test_adaptation_requires_retained_surprise_identity():
 e,u,d,c,r=fixture(CASES[1],classification='POSITIVE_SURPRISE_CANDIDATE',priority='NONE');d=surprise(d);d.decision='KEEP_SURPRISE'
 assert not adaptive_review(d,[e],u,r,c)['issues']
 previous=d.model_copy(deep=True);d.key='next';d.decision='ADAPT_DOWNSTREAM'
 assert 'RETAINED_SURPRISE_RECEIPT_REQUIRED' in adaptive_review(d,[e],u,r,c)['issues']
 d.retained_surprise_ref=SourcePin(key=previous.key,kind='DIRECTION',fingerprint=sha256_canonical(previous));c[previous.key]=sha256_canonical(previous)
 assert not adaptive_review(d,[e],u,r,c,prior_surprise=previous)['issues']

@pytest.mark.parametrize('defect',['none','authority','runtime','phase','lineage'])
def test_real_observation_entry_requires_all_receipts(defect):
 from test_coverage_realization import setup,generate
 from drama_plugin.contracts.media import Media
 from drama_plugin.adaptive_direction import AUTHORITY_ROLES
 a,p,c,s,h=setup();g=generate(a,p,c,s,h);x=g['shots'][0]
 lineage={k:x[k] for k in ('shotRef','shotFingerprint','coverageRefs','directorIntentRefs','sourceFingerprint','sceneId')}
 m=Media(id='isolated-record',work_id=a.work_id,shot_id=s[0].id,media_type='VIDEO',source_ref='fixture://no-file',content_hash='b'*64,content={'coverageRealization':lineage})
 pin=SourcePin(key='attestation',kind='DIRECTION',fingerprint='a'*64);c[pin.key]=pin.fingerprint
 roles={k:[pin] for k in AUTHORITY_ROLES};caps=['SEMANTIC_VIDEO','SEMANTIC_AUDIO']
 if defect=='authority':roles.pop('priority')
 if defect=='runtime':caps=['FFPROBE']
 if defect=='lineage':m.content['coverageRealization']['shotRef']='wrong'
 kwargs=dict(work_id=a.work_id,plan_fingerprint=h['planFingerprint'],authorities=roles,current_sources=c,phase_approved=defect!='phase',runtime_capabilities=caps,runtime_evidence=pin,approved_priorities={'p':'P1'})
 if defect=='none':
  out=authorize_observation(m,s[0],g,**kwargs);assert not out['observationPerformed']
 else:
  with pytest.raises(ValueError):authorize_observation(m,s[0],g,**kwargs)

def test_live_pairwise_cannot_skip_formal_authority_gate():
 r,a,b,c=pair()
 for e in (a,b):
  e.basis='OBSERVED_MEDIA';e.observer_type='HUMAN';e.method='NORMAL_AV';e.fact_review_ref=r.source_pins[0]
 with pytest.raises(ValueError,match='R5C_OBSERVATION_NOT_AUTHORIZED'):pairwise_handoff(r,a,b,c)

@pytest.mark.parametrize('kind,issue',[('LOCAL_REPAIR',None),('TARGETED_PICKUP',None),('TARGETED_RETAKE',None),('ROUTE_CHANGE','MODEL_SELECTION_AUTHORITY_REQUIRED'),('UPSTREAM_REWRITE','HUMAN_UPSTREAM_REVIEW_REQUIRED'),('REJECT',None)])
def test_explicit_minimal_escalation_contract(kind,issue):
 e,u,d,c,r=fixture();d.decision=kind
 ladder=['KEEP','EDITORIAL_FIX','LOCAL_REPAIR','TARGETED_PICKUP','TARGETED_RETAKE','ROUTE_CHANGE','UPSTREAM_REWRITE','REJECT']
 d.lower_cost_options={k:'Isolated failure interval remains unavailable using this method; preserve all unrelated source' for k in ladder[:ladder.index(kind)]}
 d.why_editing_is_not_enough='Required event absent from all stipulated source ranges';d.why_retake_is_necessary='Only the required receipt action is missing';d.why_no_usable_fragment='Isolated fixture stipulates every interval has missing identity and no reusable audio'
 
 if kind=='REJECT':
  u.editorial_usability='UNUSABLE';u.usable_ranges=();u.covered_requirements=();d.editorial_usability_ref=sha256_canonical(u)
 v=adaptive_review(d,[e],u,r,c)
 if issue:assert issue in v['issues']
 else:assert not v['issues']
 assert not v['executionAuthorized']


def test_reject_cannot_discard_declared_good_fragments():
 e,u,d,c,r=fixture();d.decision='REJECT';d.lower_cost_options={k:'Fixture insufficient to repair full action' for k in ['KEEP','EDITORIAL_FIX','LOCAL_REPAIR','TARGETED_PICKUP','TARGETED_RETAKE','ROUTE_CHANGE','UPSTREAM_REWRITE']};d.why_editing_is_not_enough='Missing essential order';d.why_no_usable_fragment='Contradictory claim intentionally tested'
 assert 'REJECT_CONFLICTS_WITH_USABLE_FRAGMENT' in adaptive_review(d,[e],u,r,c)['issues']
