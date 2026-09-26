from __future__ import annotations
from typing import Any
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.creative_source import LiteraryPackage, StageReview
from drama_plugin.contracts.interpretation import InterpretationFacet, InterpretationApproval, InterpretationUse
from drama_plugin.director import pin
from drama_plugin.interpretation import intent_pin, evidence_subject, evidence_fingerprint
from literary_fixture import fixture


def reviewed(item: dict[str, Any]) -> dict[str, Any]:
    f=InterpretationFacet.model_validate(item['interpretation'])
    item['interpretation']=dump_contract(f)
    f.evidence_review=StageReview(authority='literary-source-analysis',subject_hash=evidence_subject(item),
        status='APPROVED',reviewer='fixture-reader',evidence='Checked scoped support, counter-evidence and limitations; design fixture only.')
    item['interpretation']=dump_contract(f)
    return item


def case(identity: str='I1', department: str='cinematography') -> dict[str, Any]:
    source=dump_contract(LiteraryPackage.model_validate(fixture()))  # type: ignore[no-untyped-call]
    source_ref=pin('source:synthetic',source)
    scope={'kind':'WHOLE_WORK','refs':['work']}
    item={'id':identity,'meaning':'World remains socially active; the protagonist withdraws from it.',
          'why':'Coordinate relation without declaring the world dead.','scopeLevel':'FILM','scopeRef':'work',
          'priority':'SHOULD','kind':'RELATIONSHIP','interpretation':{
              'version':1,'workRef':'work','branchId':'main','scope':scope,'layer':'WORKING_INTERPRETATION',
              'status':'MULTI_VALENT','section':'World Relation','sourceRef':dump_contract(source_ref),
              'factRefs':['e1'], 'observations':[{'id':'O1','version':1,'observation':'Two people remain present.', 'scope':scope,'anchorIds':['a']}],
              'supporting':[{'id':'E1','anchorIds':['a'],'basis':'DIRECT_TEXT','strength':'STRONG','reason':'The authored scene names both participants.'}],
              'counterEvidence':[], 'counterSearch':'NO_COUNTER_EVIDENCE_FOUND_IN_REVIEWED_SCOPE','reviewedAnchorIds':['a'],
              'limitations':['Presence does not prove benevolence.'],'confidence':'HIGH','confidenceReason':'Direct local relation, bounded to this encounter.',
              'canonConsistency':'PRESERVED','reviewBasis':'SELF_AUDIT','implications':[{'id':'Q1','department':department,'scope':scope,
              'form':'QUESTION','question':'Which relation must remain perceptible here?','limitations':['Owner decides implementation.'],'boundaryReview':'QUESTIONS_ONLY'}]}}
    reviewed(item);ref=intent_pin(item)
    artifacts={source_ref.key:source,ref.key:item}
    current={k:fp(v) for k,v in artifacts.items()}
    return {'item':item,'ref':ref,'artifacts':artifacts,'current':current,'source_ref':source_ref}


def approval(c: dict[str, Any], *, mode: str='APPROVED_FOR_THIS_ADAPTATION') -> Any:
    f=InterpretationFacet.model_validate(c['item']['interpretation'])
    r=InterpretationApproval.model_validate(dict(subjectId=c['item']['id'],subjectFingerprint=fp(c['item']),workRef='work',
        branchId='main',approvedBy=['fixture-user'],actorType='USER',decision='APPROVE',mode=mode,scope=dump_contract(f.scope),
        evidenceFingerprint=evidence_fingerprint(c['item']),version=1))
    ref=pin('interpretation-approval:'+c['ref'].key,dump_contract(r))
    c['artifacts'][ref.key]=dump_contract(r);c['current'][ref.key]=ref.fingerprint;c['approval_ref']=ref
    return ref


def use(c: dict[str, Any], values: dict[str, Any], disposition: str='CONSISTENT') -> InterpretationUse:
    return InterpretationUse.model_validate(dict(interpretationRef=dump_contract(c['ref']),approvalRef=dump_contract(c['approval_ref']),
        implicationId='Q1',scope=c['item']['interpretation']['scope'],decisionFingerprint=fp(values),disposition=disposition,
        reviewer='fixture-department-reviewer',reason='Decision checked against the exact obligation; no automatic literary judgment.'))
