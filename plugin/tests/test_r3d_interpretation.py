from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any
import pytest
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.interpretation import InterpretationFacet, InterpretationApproval, InterpretiveImplication
from drama_plugin.contracts.professional import CreativeRecord
from drama_plugin.director import pin
from drama_plugin.interpretation import (validate_interpretation, validate_approval, department_handoff, project_board,
    intent_pin, validate_consumption, require_record_consumption, check_consumer_dependencies, validate_approved_selection)
from drama_plugin.hosts.creative_source import CreativeSourceHost
from r3d_helpers import case, reviewed, approval, use


def test_board_is_a_pure_view_and_never_approval() -> None:
    c=case();before=deepcopy(c)
    board=project_board([c['item']],c['artifacts'],c['current'])
    assert board['status']=='AWAITING_USER_APPROVAL' and not board['productionAuthorized']
    assert c==before
    with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):
        department_handoff(c['ref'],pin('fake',{}),'Q1',c['artifacts'],c['current'])


def test_user_receipt_requires_host_attestation_and_exact_version() -> None:
    c=case();a=approval(c)
    with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):
        department_handoff(c['ref'],a,'Q1',c['artifacts'],c['current'])
    out=department_handoff(c['ref'],a,'Q1',c['artifacts'],c['current'],approved_refs=(a,))
    assert out['department']=='cinematography' and 'meaning' not in out
    c['item']['meaning']+=' A different choice.'
    with pytest.raises(ValueError): department_handoff(c['ref'],a,'Q1',c['artifacts'],c['current'],approved_refs=(a,))


@pytest.mark.parametrize('attack',['none','high','counter-unreviewed','counter-ignored','source-fact','anchor','canon','review','how','prompt'])
def test_evidence_and_authority_adversaries(attack: str) -> None:
    c=case();f=c['item']['interpretation']
    if attack=='none':
        c['item']['meaning']='STAR = generic hope';f['supporting']=[];f['confidence']='LOW'
    elif attack=='high': f['supporting'][0]['basis']='INDIRECT'
    elif attack in ('counter-unreviewed','counter-ignored'):
        f['counterEvidence']=[dict(id='C1',anchorIds=['a'],basis='DIRECT_TEXT',strength='STRONG',reason='The source opposes the claim.')]
        f['counterSearch']='COUNTER_EVIDENCE_FOUND'
        if attack=='counter-ignored':f['counterAssessments']=[dict(evidenceId='C1',effect='CONTRADICTS',reason='Strong counter-text contradicts the broad claim.')]
    elif attack=='source-fact': f['factRefs']=['interpretation']
    elif attack=='anchor': f['supporting'][0]['anchorIds']=['missing']
    elif attack=='canon': f['canonConsistency']='CONCERN'
    elif attack=='review': f['evidenceReview']=None
    elif attack=='how': f['implications'][0]['boundaryReview']='HOW_LEAK'
    elif attack=='prompt': f['implications'][0]['department']='prompt-compiler'
    with pytest.raises(ValueError):
        if attack!='review': reviewed(c['item'])
        validate_interpretation(c['item'],c['artifacts'],c['current'],for_approval=True)


@pytest.mark.parametrize('state',['REJECTED','UNSUPPORTED'])
def test_rejected_cannot_enter_handoff(state: str) -> None:
    c=case();c['item']['interpretation']['status']=state;reviewed(c['item'])
    with pytest.raises(ValueError,match='CANNOT_HANDOFF'):
        validate_interpretation(c['item'],c['artifacts'],c['current'])


def test_contested_preserved_without_forcing_a_winner() -> None:
    c=case();f=c['item']['interpretation'];f['status']='CONTESTED';f['confidence']='CONTESTED';reviewed(c['item'])
    c['ref']=intent_pin(c['item']);c['artifacts'][c['ref'].key]=c['item'];c['current'][c['ref'].key]=c['ref'].fingerprint
    a=approval(c)
    with pytest.raises(ValueError,match='CANNOT_BECOME_DETERMINISTIC'):
        department_handoff(c['ref'],a,'Q1',c['artifacts'],c['current'],approved_refs=(a,))
    a=approval(c,mode='PRESERVE_AMBIGUITY')
    assert department_handoff(c['ref'],a,'Q1',c['artifacts'],c['current'],approved_refs=(a,))['ambiguityPolicy']=='PRESERVE_AMBIGUITY'


def test_multi_valent_can_share_user_approval_without_merging() -> None:
    c1,c2=case(),case('I2');a1,a2=approval(c1),approval(c2)
    arts={**c1['artifacts'],**c2['artifacts']};current={**c1['current'],**c2['current']}
    board=project_board([c1['item'],c2['item']],arts,current,approval_refs={'I1':a1,'I2':a2},approved_refs=(a1,a2))
    assert [r['id'] for r in board['rows']]==['I1','I2']
    assert all(r['approvalState']=='APPROVED_FOR_THIS_ADAPTATION' for r in board['rows'])


def test_conflicting_selections_cannot_both_be_deterministic() -> None:
    c1,c2=case(),case('I2');c1['item']['interpretation']['conflictsWith']=['I2'];reviewed(c1['item'])
    a1,a2=approval(c1),approval(c2)
    receipts={c['item']['id']:InterpretationApproval.model_validate(c['artifacts'][a.key]) for c,a in [(c1,a1),(c2,a2)]}
    with pytest.raises(ValueError,match='CONFLICTING_INTERPRETATIONS'):
        validate_approved_selection([c1['item'],c2['item']],receipts)


@pytest.mark.parametrize('department',['character-dramaturgy','scene-development','dramatic-performance-direction','costume-design',
    'specialized-asset-design','production-design','cinematography','lighting-design','color-design','sound-design','music-direction','editorial-design','shot-design'])
def test_each_owner_receives_questions_not_a_design(department: str) -> None:
    c=case(department=department);a=approval(c)
    handoff=department_handoff(c['ref'],a,'Q1',c['artifacts'],c['current'],approved_refs=(a,))
    assert handoff['implementationOwner']==department
    assert not {'lens','costume','cameraMovement','lowKey','cutSeconds','meaning','sourceText'} & set(handoff)
    values={'professional_choice':'The owner provides an observable or audible decision.'}
    assert validate_consumption(use(c,values),department=department,work_ref='work',scope_refs=('work',),values=values,
        artifacts=c['artifacts'],current=c['current'],approved_refs=(a,))['status']=='PASS'


@pytest.mark.parametrize('field',['lens','shotSize','cameraMovement','color','cutSeconds','costume'])
def test_implication_contract_cannot_carry_how(field: str) -> None:
    c=case();raw=c['item']['interpretation']['implications'][0];raw[field]='35mm / cold blue / torn black coat'
    with pytest.raises(ValueError,match='Extra inputs'): InterpretiveImplication.model_validate(raw)


def test_music_question_allows_no_score_and_yield() -> None:
    for policy in ('DO_NOT_SCORE','YIELD'):
        c=case(department='music-direction');c['item']['interpretation']['implications'][0]['musicPolicy']=policy;reviewed(c['item'])
        c['ref']=intent_pin(c['item']);c['current'][c['ref'].key]=c['ref'].fingerprint
        a=approval(c)
        assert department_handoff(c['ref'],a,'Q1',c['artifacts'],c['current'],approved_refs=(a,))['musicPolicy']==policy


def test_drift_returns_owner_without_rewriting_and_source_exception_routes_review() -> None:
    c=case(department='sound-design');a=approval(c);values={'ambience':'All human activity must disappear.'}
    u=use(c,values,'DRIFT');before=deepcopy(values)
    args=dict(department='sound-design',work_ref='work',scope_refs=('work',),values=values,artifacts=c['artifacts'],current=c['current'],approved_refs=(a,))
    assert validate_consumption(u,**args)['status']=='INTERPRETATION_DRIFT_CONCERN'
    assert values==before
    u=u.model_copy(update={'disposition':'INDEPENDENT_SOURCE','independent_source_refs':(c['source_ref'],)})
    assert validate_consumption(u,**args)['status']=='SOURCE_PRIORITY_REVIEW_REQUIRED'


@pytest.mark.parametrize('attack',['interpretation','approval','evidence','decision'])
def test_selective_stale_and_exact_dependency(attack: str) -> None:
    c1,c2=case(),case('I2','costume-design');a1,a2=approval(c1),approval(c2)
    arts={**c1['artifacts'],**c2['artifacts']};current={**c1['current'],**c2['current']}
    values={'camera_point_of_view':'Observe the two independently moving figures.'}
    u1,u2=use(c1,values),use(c2,values)
    if attack=='interpretation':current[c1['ref'].key]='f'*64
    elif attack=='approval':current[a1.key]='f'*64
    elif attack=='evidence':
        # Per-item evidence revision invalidates that item. A real package update
        # correctly stales all consumers sharing that package's coarse source pin.
        c1['item']['interpretation']['confidenceReason']='New scoped evidence assessment.'
    else:values={'camera_point_of_view':'A changed implementation.'}
    with pytest.raises(ValueError):
        validate_consumption(u1,department='cinematography',work_ref='work',scope_refs=('work',),values=values,artifacts=arts,current=current,approved_refs=(a1,a2))
    if attack!='decision':
        assert validate_consumption(u2,department='costume-design',work_ref='work',scope_refs=('work',),values=values,artifacts=arts,current=current,approved_refs=(a1,a2))['status']=='PASS'


def test_consumption_cannot_be_hidden_as_a_plain_source_pin() -> None:
    c=case();a=approval(c)
    r=CreativeRecord(id='camera',scope_refs=('work',),values={'camera_point_of_view':'Observe the figures.'},provenance='NEW_PROFESSIONAL_ELABORATION',source_refs=(c['ref'],a))
    with pytest.raises(ValueError,match='EXPLICIT_INTERPRETATION_CONSUMPTION'):
        require_record_consumption(r,'cinematography','work',c['artifacts'],c['current'],(a,))


def test_old_versions_are_immutable_and_board_revision_is_not_source_revision(tmp_path: Path) -> None:
    c=case();host=CreativeSourceHost(tmp_path)
    host.store.put(c['source_ref'].key,c['artifacts'][c['source_ref'].key])
    v1=host.retain_interpretation(c['item'],current={k:v for k,v in c['current'].items() if k!=c['ref'].key});old=deepcopy(c['item'])
    revised=deepcopy(old);revised['meaning']='Another adaptation-specific choice.';revised['interpretation']['version']=2;reviewed(revised)
    v2=host.retain_interpretation(revised,current=c['current'],previous_ref=v1)
    assert v1.key==v2.key and v1.fingerprint!=v2.fingerprint
    assert host.store.read_ref(v1)==old
    assert revised['interpretation']['observations']==old['interpretation']['observations']
    assert host.store.read_ref(c['source_ref'])==c['artifacts'][c['source_ref'].key]
    with pytest.raises(ValueError,match='PREDECESSOR'):
        host.retain_interpretation(revised,current=c['current'])


def test_direct_interpretation_prose_is_not_a_professional_decision() -> None:
    c=case();a=approval(c);values={'camera_point_of_view':c['item']['meaning']}
    with pytest.raises(ValueError,match='PROSE_IS_NOT_PROFESSIONAL_DECISION'):
        validate_consumption(use(c,values),department='cinematography',work_ref='work',scope_refs=('work',),values=values,
            artifacts=c['artifacts'],current=c['current'],approved_refs=(a,))
