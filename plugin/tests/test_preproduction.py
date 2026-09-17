from copy import deepcopy
from pathlib import Path
import pytest
from pydantic import ValidationError
from preproduction_helpers import make_case
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.preproduction import ScreenplayReadinessReview, CostumeState, StylizationReview, DirectorDepartmentPacket, DepartmentConflict
from drama_plugin.contracts.dramatic_editorial import EditorialRhythmPlan, ShotTransition
from drama_plugin.contracts.director import DirectorWorkspace, CapabilityRequest
from drama_plugin.director import pin, enter, request_pin, DirectorError
from drama_plugin.preproduction import readiness, stylization, costume_continuity, transition_completeness, department_integration, gate_progress
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
from drama_plugin.hosts.director_capabilities import LocalCapabilityBridge
from drama_plugin.hosts.director_runtime import dispatch_local
from drama_plugin import DramaPlugin


def changed_review(r, dimension, verdict):
    data=dump_contract(r)
    for f in data['findings']:
        if f['dimension']==dimension:f.update(verdict=verdict,revisionScope='回到对应Scene验证可见选择与后果')
    return ScreenplayReadinessReview.model_validate(data)


@pytest.mark.parametrize('name',['war','relationship','political'])
@pytest.mark.parametrize('route',['stylized_cinematic_cg','live_action_realist'])
def test_three_genres_same_pipeline_and_route_isolation(name,route):
    p,r,c,a=make_case(name,route)
    out=department_integration(p,r,c,a)
    assert out['status']=='DIRECTOR_PRODUCTION_BOOK_READY_FOR_USER_REVIEW'
    assert out['productionAuthorized'] is False and out['userApproved'] is False
    assert readiness(r,c)['status']=='READY_FOR_DIRECTION'
    assert a[name+':film-design']['stylization']['cgPolicyApplied']==(route=='stylized_cinematic_cg')


def test_event_only_cannot_silently_pass_or_use_average():
    p,r,c,a=make_case()
    r=r.model_copy(update=dict(human_stakes_carrier=None,emotional_counterline=None,repeated_scene_pattern='event-report-decision-march-battle'))
    result=readiness(r,c)
    assert result['status']=='DIRECTOR_REQUESTS_SCRIPT_REVIEW'
    assert {'human_stakes_carrier','emotional_counterline','repeated_scene_pattern'}<=set(result['blockers'])


def test_relationship_without_causality_fails():
    p,r,c,a=make_case('relationship')
    assert readiness(changed_review(r,'narrative_spine','MAJOR'),c)['directionAllowed'] is False
    assert readiness(r,c)['directionAllowed']  # non-romantic mother/daughter can pass


def test_unknown_and_core_na_cannot_pass():
    p,r,c,a=make_case()
    for verdict in ['UNKNOWN','NA']:
        assert not readiness(changed_review(r,'human_stakes',verdict),c)['directionAllowed']
    assert readiness(changed_review(r,'dialogue','NOTE'),c)['status']=='READY_WITH_NOTES'


def test_affordance_exclusion_reason_allowed_unresolved_blocks():
    p,r,c,a=make_case()
    raw=dump_contract(r);raw['affordances'][0]['decision']='EXCLUDE_WITH_REASON'
    raw['affordances'][0]['reason']='窄视点已由同伴负重承载，不插入另一段仪式'
    assert readiness(ScreenplayReadinessReview.model_validate(raw),c)['directionAllowed']
    raw['affordances'][0]['decision']='UNRESOLVED'
    assert not readiness(ScreenplayReadinessReview.model_validate(raw),c)['directionAllowed']


def test_stale_readiness_stops():
    p,r,c,a=make_case();c[r.source_pins[0].key]='f'*64
    assert readiness(r,c)['status']=='STALE_SOURCE'


@pytest.mark.parametrize('description',['朴素功能性皮甲','电影化分层精工甲，轮廓与材料有节制地提升'])
def test_plain_and_elevated_design_both_allowed(description):
    p,r,c,a=make_case();raw=deepcopy(a['war:film-design']['stylization']);raw['softRealization']=[description]
    assert stylization(StylizationReview.model_validate(raw))['status']=='DESIGN_POLICY_CONSISTENT'


@pytest.mark.parametrize('violation',['霓虹发光符文','不可能承重盔甲','现代时装剪裁破坏时代','所有角色传奇装备','无因果超尺度装饰'])
def test_explicit_fantasy_findings_never_pass(violation):
    p,r,c,a=make_case();raw=deepcopy(a['war:film-design']['stylization']);raw['violations']=[violation]
    assert stylization(StylizationReview.model_validate(raw))['status']=='REVISE'


def test_cg_policy_cannot_leak_into_live_action():
    p,r,c,a=make_case();raw=deepcopy(a['war:film-design']['stylization']);raw['route']='live_action_realist'
    with pytest.raises(ValidationError):StylizationReview.model_validate(raw)


def test_costume_battle_rain_next_scene_no_reset():
    p,r,c,a=make_case();prev=CostumeState.model_validate(a['war:war2-state']);now=CostumeState.model_validate(a['war:war3-state'])
    ref=pin('war:war2-state',prev)
    assert costume_continuity(prev,now,ref)==()
    assert 'UNEXPLAINED_COSTUME_CHANGE:damage' in costume_continuity(prev,now.model_copy(update={'damage':'崭新'}),ref)
    assert 'UNEXPLAINED_COSTUME_CHANGE:water' in costume_continuity(prev,now.model_copy(update={'water':'全干'}),ref)


@pytest.mark.parametrize('field',['screenDirection','axis','eyeline','motionContinuity','soundCarry','timeRelation','spaceRelation'])
def test_transition_seven_dimensions_required(field):
    p,r,c,a=make_case();raw=deepcopy(a['war:war1-coverage']['transitions'][0]);del raw[field]
    with pytest.raises(ValidationError):ShotTransition.model_validate(raw)


def test_transition_time_sound_and_legacy_serialization():
    p,r,c,a=make_case();raw=deepcopy(a['war:war1-coverage']);raw.pop('transitions')
    old=EditorialRhythmPlan.model_validate(raw)
    assert 'transitions' not in dump_contract(old)
    assert transition_completeness(old)
    for time in ['continuous','compressed continuous','explicit ellipsis','new time','parallel']:
        t=deepcopy(a['war:war1-coverage']['transitions'][0]);t['timeRelation']=time
        for sound in ['carry','cut','fade','prelap','offscreen continuation']:
            t['soundCarry']=sound;ShotTransition.model_validate(t)


def test_missing_scene_or_boundary_stops_book():
    p,r,c,a=make_case()
    out=department_integration(p.model_copy(update={'entries':tuple(e for e in p.entries if e.department!='lighting')}),r,c,a)
    assert out['status']=='DIRECTOR_PRODUCTION_BOOK_NOT_READY'
    out=department_integration(p.model_copy(update={'sequence_transition_refs':()}),r,c,a)
    assert any(x.startswith('MISSING_SCENE_TRANSITION') for x in out['missing'])


def rebind_entry(p,c,a,dept,scope,data):
    old=next(e for e in p.entries if e.department==dept and e.scope_id==scope)
    ref=pin(old.artifact_ref.key,data);a[ref.key]=data;c[ref.key]=ref.fingerprint
    return p.model_copy(update={'entries':tuple(e.model_copy(update={'artifact_ref':ref}) if e==old else e for e in p.entries)})


def test_lighting_night_interior_exterior_dawn_and_unmotivated_source():
    p,r,c,a=make_case()
    assert [a['war:war'+str(i)+'-light']['daytimeLogic'] for i in (1,2,3)]==['night interior','night exterior','dawn']
    raw=deepcopy(a['war:war2-light']);raw['motivatedSources']=['无来源的英雄金光']
    p=rebind_entry(p,c,a,'lighting','war2',raw)
    out=department_integration(p,r,c,a)
    assert out['status']=='DEPARTMENT_CONFLICT'
    assert out['conflicts'][0]['repairOwner']=='cinematic-direction'


@pytest.mark.parametrize('code,owner,evidence',[
 ('COSTUME_LIGHT','cinematic-direction','暗衣在黑背景中失去轮廓，原灯光未提供可见手部'),
 ('LAYOUT_BLOCKING','production-design','门口被道具占满，人物通过路线与平面不兼容'),
 ('DIRECTION_AXIS','shot-design','前镜左出，接镜无重新定位却从右向左'),
 ('COLOR_HIERARCHY','production-design','克制青灰阶段突然变成英雄金色')])
def test_semantic_conflicts_retain_owner_and_never_mutate_departments(code,owner,evidence):
    p,r,c,a=make_case(); before=deepcopy(a)
    conflict=DepartmentConflict(code=code,subject_refs=(p.entries[1].artifact_ref,p.entries[3].artifact_ref),evidence=evidence,repair_owner=owner)
    out=department_integration(p.model_copy(update={'conflicts':(conflict,)}),r,c,a)
    assert out['status']=='DEPARTMENT_CONFLICT'
    assert out['conflicts'][0]['repairOwner']==owner
    assert a==before


def test_summary_cannot_replace_original_and_self_review_not_approval():
    p,r,c,a=make_case();del a[p.entries[0].artifact_ref.key]
    with pytest.raises(ValueError,match='Missing or stale'):department_integration(p,r,c,a)
    p,r,c,a=make_case();p=p.model_copy(update={'self_review_ref':None})
    assert department_integration(p,r,c,a)['status']=='DIRECTOR_PRODUCTION_BOOK_NOT_READY'


def test_downstream_cannot_promote_upstream_gates():
    assert not gate_progress({'G8':'PASS','G9':'PASS'},'G10')['allowed']
    assert gate_progress({f'G{i}':'PASS' for i in range(10)},'G10')['productionAuthorized'] is False


def test_director_entry_and_real_store_dispatch_gate(tmp_path):
    p,r,c,a=make_case(); store=DirectorArtifactStore(tmp_path)
    for k,v in a.items():assert store.put(k,v).fingerprint==c[k]
    w=DirectorWorkspace(workspace_id='preproduction',branch_id='fixture',scope_id='war',source_pins=p.source_pins,intent_refs=(p.intent_ref,),route_ref=p.route_ref,preproduction_required=True,readiness_ref=p.readiness_ref)
    assert enter(w,c)['action']=='SCREENPLAY_READINESS_REQUIRED'
    assert enter(w,c,readiness_review=dump_contract(r))['action']=='INTERPRET_AND_INTEND'
    store.create(w)
    assert store.resume(w.workspace_id,w.branch_id,c)['action']=='INTERPRET_AND_INTEND'
    data=store.put('input',{'filmDesign':a['war:film-design']});c[data.key]=data.fingerprint
    q=CapabilityRequest(request_id='film',workspace_id=w.workspace_id,branch_id=w.branch_id,scope_id=w.scope_id,source_pins=w.source_pins,intent_refs=w.intent_refs,route_ref=w.route_ref,capability='production-design',task='Validate film design handoff',result_kind='DESIGN_ONLY',must_preserve=('Canon',),prohibitions=('NO PROVIDER',),priority='HIGH',required_evidence=('CONTRACT_VALID',),requirement_refs=(data,))
    qr=store.put(request_pin(q).key,dump_contract(q));c[qr.key]=qr.fingerprint
    w=store.transition(w,'REQUEST',qr,c)
    plugin=DramaPlugin.load(Path(__file__).resolve().parents[1]); bridge=LocalCapabilityBridge(store,plugin.skills.get)
    done=dispatch_local(store,bridge,w,data,c,retain_execution=lambda q,f:None)
    assert done.checkpoint=='REVIEW_PENDING'
    assert not done.adopted_head


def test_director_bad_readiness_blocks_dispatch(tmp_path):
    p,r,c,a=make_case();bad=changed_review(r,'human_stakes','MAJOR');ref=pin('bad',bad);c[ref.key]=ref.fingerprint
    w=DirectorWorkspace(workspace_id='test',branch_id='test',scope_id='war',source_pins=p.source_pins,preproduction_required=True,readiness_ref=ref)
    assert enter(w,c,readiness_review=dump_contract(bad))['action']=='DIRECTOR_REQUESTS_SCRIPT_REVIEW'
    old=DirectorWorkspace(workspace_id='legacy',branch_id='legacy',scope_id='war',source_pins=p.source_pins)
    assert 'preproductionRequired' not in dump_contract(old)
    assert enter(old,c)['action']=='INTERPRET_AND_INTEND'
