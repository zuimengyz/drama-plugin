import pytest
from pydantic import ValidationError
from drama_plugin.contracts.base import dump_contract,sha256_canonical
from drama_plugin.contracts.casting_discriminants import VisualCastingPlan,VisualDiscriminant,CompleteCandidateProofSet,AudienceAppealFinding
from drama_plugin.casting_discriminants import compile_visual_discriminants,validate_visual_plan,verify_submitted_projection,visual_selection_gate
from drama_plugin.performance_casting import profile_fingerprint
from test_performance_casting import profile,review

def plan(p):
 counter=next(i for i,x in enumerate(p.excavation.insights) if x.dimension=='COUNTER_STEREOTYPE')
 ds=[{'key':'outline','responsibility':'DIRECTLY_VISUALIZABLE','stage':'FACE','basisPointers':['/presence'],'axis':'width','choices':{'n':'narrow midface','w':'wide midface'},'observation':'compare width'},
 {'key':'scale','responsibility':'BODY_SPATIAL_ONLY','stage':'SCALE','basisPointers':['/body'],'axis':'relative size','choices':{'base':'shared floor body relation'},'observation':'shared plane'},
 {'key':'state','responsibility':'PERFORMANCE_DEPENDENT','stage':'PERFORMANCE','basisPointers':['/performanceStates'],'axis':'response','choices':{'base':'listen to a refusal'},'observation':'attention changes'},
 {'key':'political_judgment','responsibility':'STORY_DEPENDENT','stage':None,'basisPointers':['/sceneObligations'],'axis':'story','choices':{'base':'political judgment belongs to story'},'observation':'choices and cost'}]
 return VisualCastingPlan.model_validate({'profileFingerprint':profile_fingerprint(p),'intent':{'basis':{'excavation':['/excavation'],'identity_era_social':['/excavation/context'],'counter_stereotype':[f'/excavation/insights/{counter}'],'role_obligations':['/sceneObligations']},'searchQuestion':'discover unlike possibilities','selectionQuestion':'test role appeal'},'appeal':{'channels':[{'mode':'intellectual_attractive','audienceEffect':'attention to an argument','discriminantIds':['outline']}],'primaryResponse':'RESPECT','selectionPrinciple':'beauty does not compensate for role failure'},'discriminants':ds,'variants':[{'key':k,'assignments':{'outline':k,'scale':'base','state':'base'}} for k in ['n','w']],'contrastAxes':['outline'],'proofSet':{'requiredStages':['FACE','SCALE','PERFORMANCE'],'socialIdentityEssential':False,'scope':'REDUCED','omittedReasons':{'SOCIAL':'not the distinguishing relation in this synthetic fixture'},'rationale':'scoped test'}})

def test_compilation_and_real_submission_equality():
 p=profile();v=plan(p);c=compile_visual_discriminants(p,v,'n','FACE')
 assert 'narrow midface' in c['prompt'] and 'wide midface' not in c['prompt']
 assert all(x not in c['prompt'] for x in ['political judgment belongs to story','shared floor body relation','listen to a refusal'])
 assert c['responsibilityBuckets']['STORY_NOT_FOR_STATIC_REVIEW'][0]['key']=='political_judgment'
 assert verify_submitted_projection(c,c['prompt'])['status']=='PASS'
 with pytest.raises(ValueError,match='SUBMITTED_PROMPT'):verify_submitted_projection(c,c['prompt'].replace('narrow','wide'))

def test_appeal_is_active_and_sources_are_typed():
 p=profile();v=plan(p);a=compile_visual_discriminants(p,v,'n','FACE');v.appeal.channels[0].audience_effect='practical competence'
 b=compile_visual_discriminants(p,v,'n','FACE');assert a['prompt']!=b['prompt'] and a['planFingerprint']!=b['planFingerprint']
 v.intent.basis['identity_era_social']=('/body',)
 with pytest.raises(ValueError,match='wrong responsibility'):validate_visual_plan(p,v)

def test_stale_and_unresolved_basis():
 p=profile();v=plan(p);p.revision='new'
 with pytest.raises(ValueError,match='STALE'):validate_visual_plan(p,v)
 p=profile();v=plan(p);v.discriminants[0].basis_pointers=('/absent',)
 with pytest.raises(ValueError,match='Unresolved'):validate_visual_plan(p,v)

@pytest.mark.parametrize('responsibility',['STORY_DEPENDENT','PERFORMANCE_DEPENDENT','BODY_SPATIAL_ONLY'])
def test_nonface_information_cannot_be_face(responsibility):
 d=dump_contract(plan(profile()).discriminants[0]);d['responsibility']=responsibility
 with pytest.raises(ValidationError,match='responsibility'):VisualDiscriminant.model_validate(d)

def test_contrast_is_not_just_different_labels():
 d=dump_contract(plan(profile()));d['variants'][1]['assignments']['outline']='n'
 with pytest.raises(ValidationError,match='share all'):VisualCastingPlan.model_validate(d)
 d=dump_contract(plan(profile()));d['discriminants'][0]['choices']['w']='narrow midface'
 with pytest.raises(ValidationError,match='distinct face'):VisualCastingPlan.model_validate(d)

def test_calibration_omits_appeal_and_never_selects():
 p=profile();v=plan(p);control={'subject':'neutral population','view':'same frontal light'}
 c=compile_visual_discriminants(p,v,'n','FACE',purpose='CALIBRATION',calibration_conditions=control)
 assert [r['text'] for r in c['visualMediumCompilation']['inputSections']]==list(control.values())+['narrow midface']
 assert c['prompt'].startswith('Live-action human performer.')
 assert visual_selection_gate(p,v,[],purpose='CALIBRATION')['finalists']==[]
 with pytest.raises(ValueError,match='cannot silently replace'):compile_visual_discriminants(p,v,'n','FACE',calibration_conditions=control)

def test_complete_proof_and_key_social_identity():
 d={'requiredStages':['FACE','SCALE'],'socialIdentityEssential':True,'scope':'REDUCED','omittedReasons':{'SOCIAL':'skip','PERFORMANCE':'skip'},'rationale':'test'}
 with pytest.raises(ValidationError,match='SOCIAL'):CompleteCandidateProofSet.model_validate(d)
 d['scope']='COMPLETE';d['socialIdentityEssential']=False
 with pytest.raises(ValidationError,match='Complete'):CompleteCandidateProofSet.model_validate(d)

def test_appeal_gate_noncompensation_and_fingerprint():
 p=profile();v=plan(p);f=review(p,'FACE');s=review(p,'SCALE',prior=f.media);r=review(p,'PERFORMANCE',prior=s.media);rs=[f,s,r]
 assert visual_selection_gate(p,v,rs)['finalists']==[]
 for x in rs:x.audience_appeal=AudienceAppealFinding(planFingerprint=sha256_canonical(v),primaryResponse='RESPECT',status='PASS',observation='synthetic evidence',proofLimit='unit only')
 assert visual_selection_gate(p,v,rs)['status']=='USER_SELECTION_REQUIRED'
 r.audience_appeal.primary_response='LIKING';assert visual_selection_gate(p,v,rs)['finalists']==[]
 r.audience_appeal.primary_response='RESPECT';r.audience_appeal.plan_fingerprint='0'*64;assert visual_selection_gate(p,v,rs)['finalists']==[]

def test_story_cannot_be_static_review_criterion():
 p=profile();p.stage_plan[0].criteria=('political_judgment',);v=plan(p)
 with pytest.raises(ValueError,match='Story-dependent'):validate_visual_plan(p,v)
