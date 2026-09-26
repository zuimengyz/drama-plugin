"""Real Host/professional/Book/prompt boundaries; all approvals below are synthetic."""
from __future__ import annotations
import json
from copy import deepcopy
from pathlib import Path
from typing import Any
import pytest
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.director import DirectorWorkspace, CapabilityRequest
from drama_plugin.contracts.interpretation import InterpretationApproval
from drama_plugin.contracts.professional import CreativeBible, DirectorPackage, ShotAssembly
from drama_plugin.director import pin, request_pin
from drama_plugin.interpretation import (intent_pin, validate_interpretation, validate_approval,
    project_board, department_handoff, check_consumer_dependencies, evidence_fingerprint)
from drama_plugin.hosts.creative_source import CreativeSourceHost
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
from drama_plugin.hosts.professional import ProfessionalDepartmentHost
from drama_plugin.professional import (validate_bible, bible_pin, approval_subject, compile_prompt_projection)
from drama_plugin.preproduction import complete_production_book
from r3d_helpers import case, approval, use, reviewed
from test_professional_departments import baseline, record, with_records, rebind, package_fixture, retain
from preproduction_helpers import make_case
from test_visual_prompt_ir import visual_ir
from test_seedance_prompt_generator import sample
from drama_plugin.visual.prompt_ir import compile_ir
from drama_plugin.visual.video_prompt import compile_request_ir


def consumer_graph() -> tuple[Any, Any, Any, dict[str,Any]]:
    bibles,artifacts,current=baseline()  # type: ignore[no-untyped-call]
    c=case();approval(c);artifacts.update(c['artifacts']);current.update(c['current'])
    values={'camera_height':'approved shoulder height'}
    r=record(values).model_copy(update={'source_refs':(c['ref'],c['approval_ref']),'interpretation_uses':(use(c,values),)})  # type: ignore[no-untyped-call]
    bibles['cinematography']=with_records(bibles['cinematography'],r)  # type: ignore[no-untyped-call]
    rebind(bibles,artifacts,current)  # type: ignore[no-untyped-call]
    return bibles,artifacts,current,c


def approve_bible(bible: CreativeBible, artifacts: dict[str,Any], current: dict[str,str]) -> CreativeBible:
    receipt=dict(kind='PROFESSIONAL_CREATIVE_APPROVAL',subjectId=bible.id,workRef='work',decision='APPROVE',
        subjectFingerprint=approval_subject(bible),approvedBy=['user:fixture'])
    ref=pin('approval:'+bible.id,receipt);artifacts[ref.key]=receipt;current[ref.key]=ref.fingerprint
    return CreativeBible.model_validate({**dump_contract(bible),'status':'APPROVED','approvedBy':['user:fixture'],'approvalRefs':[dump_contract(ref)]})


def test_real_bible_and_host_require_approval_and_retain_trace(tmp_path: Path) -> None:
    b,a,current,c=consumer_graph();camera=b['cinematography']
    with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):validate_bible(camera,a,current)
    host=ProfessionalDepartmentHost(tmp_path)
    for key,value in a.items():host.store.put(key,value)
    out=host.submit('cinematography',camera,current=current,approved_interpretation_refs=(c['approval_ref'],))
    assert out['validationStatus']=='PASS'
    saved=host.store.read_ref(bible_pin(camera))
    assert saved['content'][0]['interpretationUses'][0]['interpretationRef']==dump_contract(c['ref'])
    current[c['ref'].key]='f'*64
    with pytest.raises(ValueError,match='STALE'):host.submit('cinematography',camera,current=current,approved_interpretation_refs=(c['approval_ref'],))


@pytest.mark.parametrize('consumer',['cinematography','lighting-design','shot-design','prompt-compiler'])
def test_actual_dependency_graph_cascades_only_along_consumed_edges(consumer: str) -> None:
    b,a,current,c=consumer_graph()
    refs=(bible_pin(b[consumer]),)
    check_consumer_dependencies(refs,a,current,(c['approval_ref'],))
    # New version changes current head, preserving immutable originals.
    v2=deepcopy(c['item']);v2['interpretation']['version']=2;v2['meaning']+=' Changed adaptation choice.';reviewed(v2)
    current[c['ref'].key]=intent_pin(v2).fingerprint
    with pytest.raises(ValueError,match='STALE'):check_consumer_dependencies(refs,a,current,(c['approval_ref'],))
    check_consumer_dependencies((bible_pin(b['costume-design']),),a,current,(c['approval_ref'],))


def test_source_package_change_invalidates_unchanged_claim_and_approval() -> None:
    b,a,current,c=consumer_graph();before=fp(c['item'])
    current[c['source_ref'].key]='f'*64
    with pytest.raises(ValueError,match='STALE'):validate_bible(b['cinematography'],a,current,approved_interpretation_refs=(c['approval_ref'],))
    assert fp(c['item'])==before


@pytest.mark.parametrize('field,value',[('decision','REVOKE'),('decision','REJECT'),('scope',{'kind':'SCENE','refs':['other']})])
def test_changed_approval_content_revalidated_even_with_new_trusted_ref(field: str,value: Any) -> None:
    c=case();a=approval(c);raw=deepcopy(c['artifacts'][a.key]);raw[field]=value
    r=InterpretationApproval.model_validate(raw)
    with pytest.raises(ValueError):validate_approval(c['item'],r,c['artifacts'],c['current'])


def test_host_receipt_cannot_turn_self_audit_into_user_approval(tmp_path: Path) -> None:
    c=case();a=approval(c);host=CreativeSourceHost(tmp_path)
    for key,value in c['artifacts'].items():host.store.put(key,value)
    with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):
        host.retain_interpretation_approval(c['ref'],c['artifacts'][a.key],current=c['current'],approved_refs=())
    assert host.retain_interpretation_approval(c['ref'],c['artifacts'][a.key],current=c['current'],approved_refs=(a,))==a
    stale={**c['current'],c['ref'].key:'0'*64}
    with pytest.raises(ValueError,match='STALE'):host.interpretation_board((c['ref'],),current=stale)


@pytest.mark.parametrize('approved',[False,True])
@pytest.mark.parametrize('aliased',[False,True])
def test_director_dispatch_uses_existing_approval_boundary(tmp_path: Path,approved: bool,aliased: bool) -> None:
    c=case();a=approval(c);store=DirectorArtifactStore(tmp_path)
    if aliased:
        c['ref']=pin('ordinary-intent-alias',c['item']);c['artifacts'][c['ref'].key]=c['item'];c['current'][c['ref'].key]=c['ref'].fingerprint
    for key,value in c['artifacts'].items():store.put(key,value)
    w=store.create(DirectorWorkspace(workspace_id='film',scope_id='work',branch_id='main',source_pins=(c['source_ref'],),intent_refs=(c['ref'],)))
    q=CapabilityRequest(request_id='q',workspace_id='film',scope_id='work',branch_id='main',source_pins=w.source_pins,intent_refs=w.intent_refs,
        capability='shot-design',task='Review owned coverage obligations',result_kind='DESIGN_ONLY',must_preserve=('source facts',),
        prohibitions=('NO CANON CHANGE',),priority='HIGH',required_evidence=('source-bound coverage',),approval_refs=(a,) if approved else ())
    qr=store.put(request_pin(q).key,dump_contract(q));w=store.transition(w,'REQUEST',qr,c['current'])
    if not approved:
        with pytest.raises(ValueError,match='USER_APPROVAL_REQUIRED'):store.transition(w,'DISPATCH',None,c['current'])
    elif aliased:
        with pytest.raises(ValueError,match='INTERPRETATION_IDENTITY_MISMATCH'):store.transition(w,'DISPATCH',None,c['current'],approved_refs=(a,))
    else:
        assert store.transition(w,'DISPATCH',None,c['current'],approved_refs=(a,)).checkpoint=='DISPATCHED'


def test_unapproved_current_work_intent_cannot_make_book_ready() -> None:
    p,r,current,a=make_case()  # type: ignore[no-untyped-call]
    c=case();current.update(c['current']);a.update(c['artifacts']);p=p.model_copy(update={'intent_ref':c['ref']})
    result=complete_production_book(p,r,current,a)
    assert result['status']=='DIRECTOR_PRODUCTION_BOOK_NOT_READY' and not result['productionAuthorized']
    assert 'USER_INTERPRETATION_APPROVAL_REQUIRED' in result['missing']


def test_real_professional_projection_and_seedance_gpt_image_exclude_interpretation() -> None:
    b,a,current,c=consumer_graph();b['cinematography']=approve_bible(b['cinematography'],a,current)
    rebind(b,a,current)  # type: ignore[no-untyped-call]
    package=package_fixture(b,a,current)  # type: ignore[no-untyped-call]
    shot=ShotAssembly.model_validate(a[package.shot_assembly_refs[0].key]);shot=shot.model_copy(update={'department_refs':{'cinematography':bible_pin(b['cinematography'])}})
    hr=pin('assembly:shot',dump_contract(shot));a[hr.key]=dump_contract(shot);current[hr.key]=hr.fingerprint
    package=package.model_copy(update={'shot_assembly_refs':(hr,)})
    receipt=dict(kind='PROFESSIONAL_CREATIVE_APPROVAL',subjectId=package.id,workRef='work',decision='APPROVE',subjectFingerprint=approval_subject(package),approvedBy=['user:fixture'])
    pr=pin('approval:package',receipt);a[pr.key]=receipt;current[pr.key]=pr.fingerprint
    package=DirectorPackage.model_validate({**dump_contract(package),'status':'APPROVED','approvedBy':['user:fixture'],'approvalRefs':[dump_contract(pr)]})
    projection=compile_prompt_projection(package,shot,a,current,adapter='seedance',approved_interpretation_refs=(c['approval_ref'],))
    projected=projection['projection']['cinematography'][0]
    assert 'interpretationUses' not in projected and projected['sourceRefs']==[]
    # Owner-authored observable fact travels through existing real IR/serializers.
    observable=projected['values']['camera_height']
    ir=visual_ir(provider='GPT Image')  # type: ignore[no-untyped-call]
    ir['camera']['perspective']['text']=observable
    image=compile_ir(ir,provider_family='GPT Image')['prompt']
    video=sample()  # type: ignore[no-untyped-call]
    video.prompt_ir['camera']['perspective']['text']=observable
    compiled=compile_request_ir(video);assert compiled['generator']['family']=='seedance_2'
    for output in (json.dumps(projection),image,compiled['prompt']):
        for forbidden in (c['item']['meaning'],c['ref'].key,'evidenceReview','counterEvidence','interpretationUses','confidence','fixture-reader'):
            assert forbidden not in output
    assert observable in image and observable in compiled['prompt']
    # Invalidated dependency stops upstream projection before another IR is built.
    current[c['ref'].key]='f'*64
    with pytest.raises(ValueError,match='STALE'):compile_prompt_projection(package,shot,a,current,adapter='seedance',approved_interpretation_refs=(c['approval_ref'],))


def test_legacy_record_serialization_and_gate_stay_identical() -> None:
    old=record({'camera_height':'shoulder height'})  # type: ignore[no-untyped-call]
    assert 'interpretationUses' not in dump_contract(old)
    b,a,current=baseline()  # type: ignore[no-untyped-call]
    assert validate_bible(b['cinematography'],a,current)['validationStatus']=='PASS'


def test_real_current_work_candidate_star_identities_and_no_adoption() -> None:
    path=Path(__file__).parent/'fixtures/r3d/interpretation-candidate.json';data=json.loads(path.read_text())
    before=deepcopy(data);items=data['items'];by_id={i['id']:i for i in items}
    assert project_board(items,data['originals'],data['current'])==data['board']
    assert len(data['primaryRowIds'])==8 and not data['approvalRefs'] and not data['productionAuthorized']
    assert by_id['H-S1']['interpretation']['confidence']=='HIGH'
    assert by_id['H-S2']['interpretation']['confidence']=='HIGH'
    assert by_id['H-S3']['interpretation']['status']=='OPEN'
    assert by_id['H-S6']['interpretation']['status']=='UNSUPPORTED'
    assert by_id['H-S7']['interpretation']['status']=='REJECTED'
    occ=[o for i in items for o in i['interpretation']['occurrences']]
    assert {o['id'] for o in occ}=={'STAR-REALITY-01','STAR-DREAM-01'}
    assert all(not set(o['anchorIds']) & {'A021','A023','A030','A031'} for o in occ)
    for item in items:
        f=validate_interpretation(item,data['originals'],data['current'])
        assert f.counter_evidence and f.evidence_review and not f.fact_refs
        with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):
            department_handoff(intent_pin(item),pin('unapproved',{}),'any',data['originals'],data['current'])
    core=by_id['I-CORE']['interpretation']
    character=next(i for i in core['implications'] if i['department']=='character-dramaturgy')
    world=next(i for i in core['implications'] if i['department']=='production-design')
    assert character['characterStateRef']=='C_MAN:sealed' and world['worldFactRefs']==['E_VISIT','E_GIRL']
    assert data==before


@pytest.mark.parametrize('attack',['arc','world'])
def test_current_character_and_world_ownership_reject_forged_sources(attack: str) -> None:
    data=json.loads((Path(__file__).parent/'fixtures/r3d/interpretation-candidate.json').read_text())
    item=data['items'][0];i=item['interpretation']['implications'][0]
    if attack=='arc':i['characterStateRef']='C_MAN:invented'
    else:i['worldFactRefs']=['I_EXIT']
    reviewed(item)
    with pytest.raises(ValueError,match='CHARACTER_STATE_MUST_REFERENCE|WORLD_FACT_CANNOT'):
        validate_interpretation(item,data['originals'],data['current'])


def test_professional_cannot_combine_conflicting_approvals_across_records() -> None:
    from drama_plugin.interpretation import validate_record_selection
    c1,c2=case(),case('I2');c1['item']['interpretation']['conflictsWith']=['I2'];reviewed(c1['item'])
    c1['ref']=intent_pin(c1['item']);c1['current'][c1['ref'].key]=c1['ref'].fingerprint
    approval(c1);approval(c2)
    records=[]
    for c in (c1,c2):
        values={'camera_height':'shoulder height'}
        records.append(record(values).model_copy(update={'source_refs':(c['ref'],c['approval_ref']),'interpretation_uses':(use(c,values),)}))  # type: ignore[no-untyped-call]
    with pytest.raises(ValueError,match='CONFLICTING_INTERPRETATIONS'):
        validate_record_selection(tuple(records),{**c1['artifacts'],**c2['artifacts']},{**c1['current'],**c2['current']})


def test_bible_cannot_hide_unapproved_interpretation_as_generic_source() -> None:
    b,a,current=baseline()  # type: ignore[no-untyped-call]
    c=case();a.update(c['artifacts']);current.update(c['current'])
    hidden=pin('ordinary-alias',c['item']);a[hidden.key]=c['item'];current[hidden.key]=hidden.fingerprint
    bible=b['cinematography'].model_copy(update={'source_refs':(*b['cinematography'].source_refs,hidden)})
    with pytest.raises(ValueError,match='EXPLICIT_INTERPRETATION_CONSUMPTION_REQUIRED'):validate_bible(bible,a,current)
