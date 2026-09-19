"""NON_NORMATIVE_EXAMPLE: independent cross-work data, no current-film defaults."""
from copy import deepcopy
import pytest
from drama_plugin.contracts.base import dump_contract,sha256_canonical
from drama_plugin.contracts.coverage_realization import CoverageRealizationPolicy,CoverageRealizationPlan,CoverageDependency
from drama_plugin.contracts.editorial_authority import EditorialAuthority
from drama_plugin.contracts.creation import Shot
from drama_plugin.contracts.media import Media
from drama_plugin.coverage_realization import realization_handoff,generation_handoff,media_handoff
from test_editorial_authority import fixture,CASES

def setup(case=CASES[0],split='PROTECTED_SEQUENCE',mode='MULTI_MATERIAL_ALLOWED'):
 a=EditorialAuthority(**fixture(case));u=a.coverage_units[0];q=a.requirements[0]
 policy=CoverageRealizationPolicy(realization_mode=mode,split_policy=split,merge_policy='SHARED_WITH_EXPLICIT_REFS',continuity_keys={'axis_state':q.spatial_requirement,'prop_state':q.protected_action},required_temporal_order=q.cut.hold.event_sequence,required_shared_state={'boundary':'approved outgoing equals incoming'},production_risk='MEDIUM',rationale='Permit complementary production segments without attention drift',split_boundary_rule='Existing protected cut rules still govern')
 p=CoverageRealizationPlan(coverage_unit_id=u.key,scene_id=u.scene_id,director_intent_refs=[q.intent.director_intent_id],source_fingerprint=sha256_canonical(u),source_authority=u.source_authority,coverage_type='REQUIRED',policy=policy,planned_shot_refs=['formal-a','formal-b'],formalization_state='FORMALIZED',formalization_reason='Isolated in-memory fixture, not service persistence')
 current={case[0]:'a'*64};receipt=realization_handoff(a,[p],[],current);shots=[]
 for i,ref in enumerate(p.planned_shot_refs):
  f={'satisfiesCoverageIds':[u.key],'directorIntentRefs':list(p.director_intent_refs),'coverageSourceFingerprints':{u.key:p.source_fingerprint},'planFingerprint':receipt['planFingerprint'],'mustPreserve':[q.protected_action],'acceptableVariation':['Only approved secondary decoration'],'forbiddenDrift':['No omitted receiver'],'continuityKeys':policy.continuity_keys,'referencePriority':['Existing approved prop/identity sources'],'providerModeRequirement':['shared continuity'],'coverageSegments':{u.key:{'eventRefs':[q.cut.hold.event_sequence[i]],'continuityKeys':policy.continuity_keys,'sharedState':policy.required_shared_state,'attentionBreak':False,'evidenceLocator':'segment-'+str(i)}}}
  shots.append(Shot(id=ref,scene_id=u.scene_id,shot_no=str(i+1),content={'coverageRealization':f}))
 return a,[p],current,shots,receipt

def generate(a,p,c,s,h,deps=()):return generation_handoff(a,p,deps,s,scene_id=p[0].scene_id,current_sources=c,approval_fingerprint=h['planFingerprint'])

@pytest.mark.parametrize('case',CASES)
def test_cross_work_split_generation_media_identity_without_observation(case):
 a,p,c,s,h=setup(case);g=generate(a,p,c,s,h)
 assert len(g['shots'])==2 and g['providerCalls']==0
 lineage={k:g['shots'][0][k] for k in ('shotRef','shotFingerprint','coverageRefs','directorIntentRefs','sourceFingerprint','sceneId')}
 m=Media(id='synthetic-record',work_id=a.work_id,shot_id=s[0].id,media_type='VIDEO',source_ref='fixture://none',content_hash='b'*64,content={'coverageRealization':lineage})
 r=media_handoff(m,s[0],g,work_id=a.work_id,current_plan_fingerprint=h['planFingerprint'],current_source_verified=True,phase_approved=True)
 assert not r['observationPerformed'] and not r['adopted']
 for field in lineage:
  bad=m.model_copy(deep=True);bad.content['coverageRealization'][field]='wrong'
  with pytest.raises(ValueError,match='R5C_OBSERVATION_NOT_AUTHORIZED'):media_handoff(bad,s[0],g,work_id=a.work_id,current_plan_fingerprint=h['planFingerprint'],current_source_verified=True,phase_approved=True)

@pytest.mark.parametrize('defect',['missing-coverage','source','intent','event','scene','missing-shot','extra-shot','empty-satisfies','stale-shot','missing-reference','missing-segment','drop-event','reorder','attention','continuity','shared-state','no-approval','not-formal','group','changed-unit','duplicate-plan'])
def test_fail_closed(defect):
 a,p,c,s,h=setup();u=p[0].coverage_unit_id;f=s[0].content['coverageRealization']
 if defect=='missing-coverage':p=[]
 if defect=='source':c['court']='x'*64
 if defect=='intent':p[0].director_intent_refs=('invented',)
 if defect=='event':p[0].policy.required_temporal_order=('new action',)
 if defect=='scene':s[0].scene_id='other'
 if defect=='missing-shot':s.pop()
 if defect=='extra-shot':s.append(Shot(id='extra',scene_id='court',shot_no='3'))
 if defect=='empty-satisfies':f['satisfiesCoverageIds']=[]
 if defect=='stale-shot':f['planFingerprint']='b'*64
 if defect=='missing-reference':del f['referencePriority']
 if defect=='missing-segment':f['coverageSegments']={}
 if defect=='drop-event':f['coverageSegments'][u]['eventRefs']=[]
 if defect=='reorder':s[0].content['coverageRealization']['coverageSegments'][u]['eventRefs'],s[1].content['coverageRealization']['coverageSegments'][u]['eventRefs']=s[1].content['coverageRealization']['coverageSegments'][u]['eventRefs'],s[0].content['coverageRealization']['coverageSegments'][u]['eventRefs']
 if defect=='attention':f['coverageSegments'][u]['attentionBreak']=True
 if defect=='continuity':f['coverageSegments'][u]['continuityKeys']={}
 if defect=='shared-state':f['coverageSegments'][u]['sharedState']={}
 if defect=='no-approval':h['planFingerprint']='none'
 if defect=='not-formal':p[0].formalization_state='READY_FOR_SHOT_DESIGN'
 if defect=='group':p[0].planned_shot_group_refs=('unresolved-group',)
 if defect=='changed-unit':a.coverage_units[0].evidence_function='changed'
 if defect=='duplicate-plan':p.append(p[0])
 with pytest.raises(ValueError):generation_handoff(a,p,[],s,scene_id='court',current_sources=c,approval_fingerprint=h['planFingerprint'])

def test_no_internal_split_and_required_multiple_are_real_guards():
 a,p,c,s,h=setup(split='NO_INTERNAL_SPLIT')
 with pytest.raises(ValueError,match='Indivisible'):generate(a,p,c,s,h)
 a,p,c,s,h=setup(mode='MULTI_MATERIAL_REQUIRED')
 assert len(generate(a,p,c,s,h)['shots'])==2
 with pytest.raises(ValueError):CoverageRealizationPolicy(**{**dump_contract(p[0].policy),'splitPolicy':'NO_INTERNAL_SPLIT'})

@pytest.mark.parametrize('state',['READY_FOR_SHOT_DESIGN','FORMALIZED'])
def test_optional_and_unknown_not_automatically_formal(state):
 a,p,c,s,h=setup();raw=dump_contract(p[0]);raw.update(coverageType='OPTIONAL',formalizationState=state)
 with pytest.raises(ValueError):CoverageRealizationPlan(**raw)
 raw=dump_contract(p[0]);raw['policy']['realizationMode']='UNRESOLVED';raw['formalizationState']=state
 with pytest.raises(ValueError):CoverageRealizationPlan(**raw)

def test_shared_intents_use_one_coverage_identity_not_duplicate_schedule():
 a,p,c,s,h=setup();second=a.requirements[0].model_copy(deep=True);second.key='second';second.intent.director_intent_id='second-intent';a.requirements=(*a.requirements,second);p[0].director_intent_refs=(*p[0].director_intent_refs,'second-intent')
 h=realization_handoff(a,p,[],c)
 for shot in s:shot.content['coverageRealization'].update(planFingerprint=h['planFingerprint'],directorIntentRefs=list(p[0].director_intent_refs))
 assert len(generate(a,p,c,s,h)['shots'])==2

def test_many_coverages_share_one_shot_and_forbidden_or_cycle_rejected():
 a,p,c,s,h=setup();u=a.coverage_units[0].model_copy(deep=True);u.key='second-unit';a.coverage_units=(*a.coverage_units,u)
 q=a.requirements[0];q.required_coverage=(*q.required_coverage,u.key);q.minimum_coverage_count=2
 pp=p[0].model_copy(deep=True);pp.coverage_unit_id=u.key;pp.source_fingerprint=sha256_canonical(u);p.append(pp)
 for plan in p:plan.planned_shot_refs=('formal-a',)
 h=realization_handoff(a,p,[],c);s=s[:1];f=s[0].content['coverageRealization'];f.update(planFingerprint=h['planFingerprint'],satisfiesCoverageIds=[x.coverage_unit_id for x in p],coverageSourceFingerprints={x.coverage_unit_id:x.source_fingerprint for x in p})
 for plan in p:f['coverageSegments'][plan.coverage_unit_id]={'eventRefs':list(plan.policy.required_temporal_order),'continuityKeys':plan.policy.continuity_keys,'sharedState':plan.policy.required_shared_state,'attentionBreak':False,'evidenceLocator':plan.coverage_unit_id+'-range'}
 assert len(generate(a,p,c,s,h)['shots'])==1
 d=CoverageDependency(key='deny',coverage_unit_id=p[0].coverage_unit_id,target_coverage_unit_id=p[1].coverage_unit_id,relation='must_not_share_material_with',scope='same event interval',reason='Different source state',source_authority=p[0].source_authority);p[0].dependency_refs=('deny',);h=realization_handoff(a,p,[d],c);f['planFingerprint']=h['planFingerprint']
 with pytest.raises(ValueError,match='Forbidden'):generate(a,p,c,s,h,[d])
 d.relation='depends_on';d2=d.model_copy(update={'key':'reverse','coverage_unit_id':p[1].coverage_unit_id,'target_coverage_unit_id':p[0].coverage_unit_id});p[1].dependency_refs=('reverse',)
 with pytest.raises(ValueError,match='cycle'):realization_handoff(a,p,[d,d2],c)

def test_optional_stays_out_until_authenticated_condition_and_keeps_identity():
 a,p,c,s,h=setup();u=a.coverage_units[0].model_copy(deep=True);u.key='optional';u.necessity='OPTIONAL';u.activation_condition='Only if the approved detail is not readable after primary evidence is complete';a.coverage_units=(*a.coverage_units,u);a.requirements[0].optional_coverage=('optional',)
 op=p[0].model_copy(deep=True);op.coverage_unit_id=u.key;op.coverage_type='OPTIONAL';op.source_fingerprint=sha256_canonical(u);op.formalization_state='NOT_FORMALIZED';op.planned_shot_refs=();p.append(op)
 h=realization_handoff(a,p,[],c)
 for shot in s:shot.content['coverageRealization']['planFingerprint']=h['planFingerprint']
 assert len(generate(a,p,c,s,h)['shots'])==2
 assert all('optional' not in x['coverageRefs'] for x in generate(a,p,c,s,h)['shots'])
 op.optional_activation_evidence=(op.source_authority[0],)
 h=realization_handoff(a,p,[],c)
 with pytest.raises(ValueError,match='NOT_FORMALIZED'):generate(a,p,c,s,h)

def test_media_changed_shot_or_phase_blocks_without_observation():
 a,p,c,s,h=setup();g=generate(a,p,c,s,h);x=g['shots'][0];lineage={k:x[k] for k in ('shotRef','shotFingerprint','coverageRefs','directorIntentRefs','sourceFingerprint','sceneId')};m=Media(id='synthetic',work_id=a.work_id,shot_id=s[0].id,media_type='VIDEO',source_ref='fixture://none',content_hash='b'*64,content={'coverageRealization':lineage})
 with pytest.raises(ValueError):media_handoff(m,s[0],g,work_id=a.work_id,current_plan_fingerprint=h['planFingerprint'],current_source_verified=True,phase_approved=False)
 s[0].content['unapprovedChange']='changed'
 with pytest.raises(ValueError):media_handoff(m,s[0],g,work_id=a.work_id,current_plan_fingerprint=h['planFingerprint'],current_source_verified=True,phase_approved=True)
