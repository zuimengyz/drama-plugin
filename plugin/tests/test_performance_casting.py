import pytest
from pydantic import ValidationError
from drama_plugin.contracts.base import dump_contract,sha256_canonical
from drama_plugin.contracts.performance_casting import RoleArchetypeProfile,CastingReview,CastingBudget
from drama_plugin.performance_casting import stage_brief,eligible,user_selection_gate,excavation_gate

def profile(order=('FACE','SCALE','PERFORMANCE'),identity='test-role',presence='moral gravity',state='persuasion'):
 p=RoleArchetypeProfile.model_validate({'identity':identity,'revision':'r1','sources':[{'ref':'local scene','fingerprint':'a'*64,'basis':'CANDIDATE','evidence':'The other person has a viable alternative.'}],'storyFunction':'Persuade a person who can refuse','screenFunction':'Notice patient attention','ageBand':'chosen for role, including child or elderly','culturalWorldFit':'authored world','attractivenessPolicy':'individual, not compulsory beauty','presence':[{'name':presence,'audienceImpression':'attention without coercion','visibleCarriers':['gaze and mouth']}],'faceArchetypes':[{'key':'one','geometry':'wide planes','presenceChoice':'composed','distinction':'wide vs narrow'},{'key':'two','geometry':'narrow planes','presenceChoice':'alert','distinction':'narrow vs wide'}],'body':{'observables':{'frame':'ordinary','posture':'contained'}},'relativeScale':{'anchors':['ordinary chair'],'sharedPlane':'feet and chair legs same floor depth','cameraControl':'eye-level','observableRelationship':'ordinary scale, posture distinctive','invalidatingCheats':['platform'],'limit':'fictional anchor not measured historical height'},'performanceStates':[{'key':state,'trigger':'valid refusal','playableTask':'keep the listener engaged','preservedTraits':['age'],'visibleChange':'pause before reply'}],'sceneObligations':['do not replace persuasion with force'],'approvalScope':'candidate person only','stagePlan':[{'stage':s,'reason':'role-specific claim','conditions':{'light':'same daylight','frame':'same view'},'criteria':['role_fit'],'minimumCandidates':1,'maximumCandidates':2} for s in order],'omittedStages':{s:'not a distinguishing claim' for s in {'FACE','SCALE','PERFORMANCE'}-set(order)}})

 p.omitted_stages['SOCIAL']='not the distinguishing claim in this unit fixture'
 from drama_plugin.contracts.performance_casting import CharacterExcavation,EXCAVATION_DIMENSIONS
 core={'context':{'identity':'local professional','rank':'no military rank','occupation':'ferry operator','socialPosition':'works for passengers','institutionalPower':'controls own vessel only','culturalHistoricalContext':'authored premodern crossing','habitualDecisionRights':['where to step'],'expectedSocialReaction':['passenger waits for safe boarding'],'situatedValues':['local practical duty, not power over passenger fate']},'watchability':'competent care despite low rank','insights':[{'dimension':d,'interpretation':'Synthetic context-bound test account','basis':'PROJECT_CHARACTER_INTERPRETATION','sourceRefs':['local scene'],'castingImplications':[{'stage':'FACE','choice':'attentive person','observableTest':'attends to passenger'}]} for d in sorted(EXCAVATION_DIMENSIONS)]}
 p.excavation=CharacterExcavation.model_validate({**core,'checks':{k:{'status':'PASS','reasoning':'unit fixture only','reviewedFingerprint':sha256_canonical(core)} for k in ['IDENTITY_LOST','ERA_CONTEXT_LOST']},'reviewerBoundary':'synthetic unit fixture, not historical review'})
 return p

def review(p,stage,cid='one',status='PASS',prior=()):
 plan=next(x for x in p.stage_plan if x.stage==stage)
 m={'mediaId':stage+cid,'contentHash':sha256_canonical(stage+cid),'taskId':stage+cid+'task','sourceRef':stage+cid+'source'}
 findings={k:{'status':status,'observation':'synthetic test observation'} for k in [*plan.criteria,*(['identity_preserved',*['state:'+s.key for s in p.performance_states]] if stage=='PERFORMANCE' else [])]}
 findings['conditions_preserved']={'status':'PASS','observation':'synthetic matched conditions'}
 if stage=='SOCIAL':findings['identity_preserved']={'status':'PASS','observation':'same retained candidate'}
 return CastingReview.model_validate({'candidateId':cid,'stage':stage,'profileFingerprint':sha256_canonical(p),'conditionsFingerprint':sha256_canonical(plan.conditions),'media':[m],'stateMedia':{s.key:m for s in p.performance_states} if stage=='PERFORMANCE' else {},'identityReferences':prior,'findings':findings,'reviewerBoundary':'unit fixture, not an artistic review'})

@pytest.mark.parametrize('order',[('FACE','SCALE','PERFORMANCE'),('SCALE','FACE','PERFORMANCE'),('PERFORMANCE','FACE'),('FACE',)])
def test_routes(order):
 b=stage_brief(profile(order),order[0],['one']);assert b['stage']==order[0];assert b['execution']=='DRY_RUN';assert not b['formalPromotionAllowed']
@pytest.mark.parametrize('identity,presence,state',[('child','playful resistance','comic disappointment'),('elder','intellectual force','quiet calculation'),('mother','maternal calm','grief under restraint')])
def test_generic_role_state_transport(identity,presence,state):
 b=stage_brief(profile(identity=identity,presence=presence,state=state),'FACE',['one']);assert b['profile']['identity']==identity;assert b['profile']['presence'][0]['name']==presence;assert b['profile']['performanceStates'][0]['key']==state

def test_omission_and_scale():
 d=dump_contract(profile(('FACE',)));d['omittedStages']={}
 with pytest.raises(ValidationError):RoleArchetypeProfile.model_validate(d)
 d=dump_contract(profile());d['relativeScale']=None
 with pytest.raises(ValidationError):RoleArchetypeProfile.model_validate(d)

def test_predecessor_gates():
 p=profile();bad=review(p,'FACE',status='PARTIAL')
 with pytest.raises(ValueError,match='PRIOR_STAGE'):stage_brief(p,'SCALE',['one'],[bad])
 f=review(p,'FACE',status='SHORTLIST');assert stage_brief(p,'SCALE',['one'],[f])['identityReferences']['one']
 s=review(p,'SCALE',status='SHORTLIST',prior=f.media)
 with pytest.raises(ValueError,match='PRIOR_STAGE'):stage_brief(p,'PERFORMANCE',['one'],[f,s])

def test_stale_and_duplicate():
 p=profile();r=review(p,'FACE');p.revision='changed'
 with pytest.raises(ValueError,match='Stale'):eligible(p,'FACE',[r])
 p=profile();r.conditions_fingerprint='b'*64
 with pytest.raises(ValueError,match='Stale'):eligible(p,'FACE',[r])
 r=review(p,'FACE')
 with pytest.raises(ValueError,match='duplicate'):eligible(p,'FACE',[r,r])

def test_budget_mcp():
 p=profile();b=CastingBudget(cap=10,recordedCost=5,outstandingReservations=2,requestedReservation=3,costLimitations='quote only');assert stage_brief(p,'FACE',['one'],budget=b,execution='MCP')
 b.requested_reservation=3.01
 with pytest.raises(ValueError,match='BUDGET_STOP'):stage_brief(p,'FACE',['one'],budget=b,execution='MCP')
 with pytest.raises(ValueError,match='CASTING_EXECUTION_INTENT_REQUIRED'):stage_brief(p,'FACE',['one'],execution='GUI')
 with pytest.raises(ValueError,match='CURRENT_BUDGET_REQUIRED'):stage_brief(p,'FACE',['one'],execution='MCP')

def test_selection_lineage_and_nonapproval():
 p=profile();f=review(p,'FACE');s=review(p,'SCALE',prior=f.media);r=review(p,'PERFORMANCE',prior=s.media)
 g=user_selection_gate(p,[f,s,r]);assert g['status']=='USER_SELECTION_REQUIRED';assert g['userApprovedWinner'] is None;assert g['formalPromotionAllowed'] is False
 r.identity_references=();assert user_selection_gate(p,[f,s,r])['finalists']==[]
 d=dump_contract(f);d['status']='USER_APPROVED'
 with pytest.raises(ValidationError):CastingReview.model_validate(d)

def test_distinct_state_media_required():
 p=profile(('PERFORMANCE',));r=review(p,'PERFORMANCE');r.state_media={};assert eligible(p,'PERFORMANCE',[r])==[]
 d=dump_contract(p);d['performanceStates'].append({**d['performanceStates'][0],'key':'second'});p=RoleArchetypeProfile.model_validate(d);r=review(p,'PERFORMANCE');assert eligible(p,'PERFORMANCE',[r])==[]

def test_schema_generic():
 schema=RoleArchetypeProfile.model_json_schema();assert 'xiang_yu' not in str(schema).lower();assert 'martial' not in str(schema).lower();assert 'genderExpression' in schema['properties']

def test_actual_conditions_and_mutated_budget():
 p=profile();r=review(p,'FACE');r.findings['conditions_preserved'].status='PARTIAL'
 assert eligible(p,'FACE',[r])==[]
 b=CastingBudget(cap=10,recordedCost=1,outstandingReservations=0,requestedReservation=1,costLimitations='test')
 b.recorded_cost=-100
 with pytest.raises(ValidationError):stage_brief(p,'FACE',['one'],budget=b,execution='MCP')

@pytest.mark.parametrize('check',['IDENTITY_LOST','ERA_CONTEXT_LOST'])
def test_context_failure_blocks_new_generation(check):
 p=profile();p.excavation.checks[check].status='FAIL'
 b=CastingBudget(cap=20,recordedCost=0,outstandingReservations=0,requestedReservation=1,costLimitations='fixture')
 with pytest.raises(ValueError,match=check):stage_brief(p,'FACE',['one'],budget=b,execution='MCP')
 assert user_selection_gate(p,[])['finalists']==[]

def test_context_change_requires_rereview():
 p=profile();p.excavation.context.institutional_power='a different authority'
 assert excavation_gate(p)['reasons']==['EXCAVATION_REVIEW_STALE']

def test_legacy_read_is_not_spend_permission():
 d=dump_contract(profile());d.pop('excavation');d.pop('socialPresence');d['omittedStages'].pop('SOCIAL')
 p=RoleArchetypeProfile.model_validate(d);assert stage_brief(p,'FACE',['one'])['excavationGate']['status']=='BLOCKED'
 b=CastingBudget(cap=20,recordedCost=0,outstandingReservations=0,requestedReservation=1,costLimitations='fixture')
 with pytest.raises(ValueError,match='CHARACTER_EXCAVATION_MISSING'):stage_brief(p,'FACE',['one'],budget=b,execution='MCP')

def test_excavation_source_links_and_coverage():
 d=dump_contract(profile());d['excavation']['insights'].pop()
 with pytest.raises(ValidationError):RoleArchetypeProfile.model_validate(d)
 d=dump_contract(profile());d['excavation']['insights'][0]['sourceRefs']=['invented unknown source']
 with pytest.raises(ValidationError,match='trace'):RoleArchetypeProfile.model_validate(d)

def test_social_stage_requires_relation_proof_and_pass():
 d=dump_contract(profile());d['stagePlan'][1]['stage']='SOCIAL';d['omittedStages']={'SCALE':'No special relative size claim'}
 with pytest.raises(ValidationError,match='Social presence'):RoleArchetypeProfile.model_validate(d)
 d['socialPresence']={'participants':['professional','high rank visitor'],'sharedSpace':'same pier','cameraControl':'eye level','socialRelations':['visitor follows professional feet instruction'],'decisionRights':'boarding only, not visitor fate','observableTest':'local competence despite lower rank','invalidatingCheats':['kneeling'],'limit':'still only'}
 p=RoleArchetypeProfile.model_validate(d);f=review(p,'FACE');s=review(p,'SOCIAL',status='PARTIAL',prior=f.media)
 with pytest.raises(ValueError,match='PRIOR_STAGE'):stage_brief(p,'PERFORMANCE',['one'],[f,s])
 s=review(p,'SOCIAL',prior=f.media);assert stage_brief(p,'PERFORMANCE',['one'],[f,s])['identityReferences']
 s.findings.pop('identity_preserved');assert eligible(p,'SOCIAL',[s])==[]
