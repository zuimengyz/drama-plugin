"""Evidence coordination and approved handoff, not a literary truth engine.

Pure functions; storage remains DirectorArtifactStore, freshness remains SourcePin
and the caller's current map, and approval authority remains Host approved_refs.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.creative_source import LiteraryPackage
from drama_plugin.contracts.interpretation import InterpretationFacet, InterpretationApproval, InterpretationUse
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.director import pin, freshness

DEPARTMENTS = frozenset({'story-architecture', 'scene-development', 'character-dramaturgy', 'director',
    'dramatic-performance-direction', 'costume-design', 'specialized-asset-design', 'production-design',
    'cinematography', 'lighting-design', 'color-design', 'sound-design', 'music-direction', 'editorial-design', 'shot-design'})


def resolve(ref: SourcePin, artifacts: Mapping[str, Any], current: Mapping[str, str]) -> dict[str, Any]:
    value = artifacts.get(ref.key)
    if freshness((ref,), current) or not isinstance(value, dict) or fp(value) != ref.fingerprint:
        raise ValueError('STALE_OR_MISSING_INTERPRETATION_SOURCE:' + ref.key)
    return value


def facet(item: Mapping[str, Any]) -> InterpretationFacet:
    if not all(item.get(k) for k in ('id', 'meaning', 'why', 'scopeLevel', 'scopeRef')):
        raise ValueError('EXISTING_CINEMATIC_INTENT_REQUIRED')
    return InterpretationFacet.model_validate(item.get('interpretation'))


def intent_pin(item: Mapping[str, Any]) -> SourcePin:
    f = facet(item)
    return pin('interpretation:' + f.work_ref + ':' + f.branch_id + ':' + str(item['id']), item)


def evidence_subject(item: Mapping[str, Any]) -> str:
    body = deepcopy(dict(item))
    body['interpretation'] = dump_contract(facet(item))
    body['interpretation'].pop('evidenceReview', None)
    return fp(body)


def evidence_fingerprint(item: Mapping[str, Any]) -> str:
    data = dump_contract(facet(item))
    return fp({k:data[k] for k in ('sourceRef','observations','supporting','counterEvidence',
        'reviewedAnchorIds','counterAssessments','confidence','confidenceReason','evidenceReview')})


def validate_interpretation(item: Mapping[str, Any], artifacts: Mapping[str, Any],
                            current: Mapping[str, str], *, for_approval: bool = False) -> InterpretationFacet:
    f = facet(item)
    from drama_plugin.creative_source import validate_literary
    p = LiteraryPackage.model_validate(resolve(f.source_ref, artifacts, current))
    validate_literary(p)
    for ref in f.thesis_refs:
        resolve(ref, artifacts, current)
    anchors = {a.id for a in p.anchors}
    facts = {u.id for u in p.analysis.units if u.origin == 'SOURCE_FACT'}
    if not set(f.fact_refs) <= facts:
        raise ValueError('INTERPRETATION_CANNOT_AUTHOR_SOURCE_FACT')
    used = set(f.reviewed_anchor_ids)
    if not used <= anchors:
        raise ValueError('INTERPRETATION_ANCHOR_UNBOUND')
    anchor_groups = [r.anchor_ids for r in f.observations] + [e.anchor_ids for e in (*f.supporting, *f.counter_evidence)] + [o.anchor_ids for o in f.occurrences]
    for anchor_ids in anchor_groups:
        if not set(anchor_ids) <= used:
            raise ValueError('EVIDENCE_OUTSIDE_REVIEWED_SOURCE_SCOPE')
    if f.confidence == 'HIGH':
        if not any(e.strength == 'STRONG' and e.basis in ('DIRECT_TEXT', 'RECURRENCE', 'STRUCTURAL_ECHO') for e in f.supporting):
            raise ValueError('HIGH_CONFIDENCE_REQUIRES_REVIEWED_SOURCE_RELATION')
        if any(a.effect == 'CONTRADICTS' and next(e for e in f.counter_evidence if e.id == a.evidence_id).strength == 'STRONG' for a in f.counter_assessments):
            raise ValueError('HIGH_CONFIDENCE_IGNORES_STRONG_COUNTER_EVIDENCE')
    if not f.evidence_review:
        raise ValueError('CONFIDENCE_EVIDENCE_REVIEW_REQUIRED')
    if f.evidence_review:
        r = f.evidence_review
        if r.authority != 'literary-source-analysis' or r.subject_hash != evidence_subject(item):
            raise ValueError('STALE_INTERPRETATION_EVIDENCE_REVIEW')
    arc_refs = {s.character_id + ':' + s.arc_stage for s in p.character_arc.states}
    for implication in f.implications:
        if implication.department not in DEPARTMENTS:
            raise ValueError('INTERPRETATION_CONSUMER_NOT_A_PROFESSIONAL_OWNER')
        if f.status in ('REJECTED', 'UNSUPPORTED'):
            raise ValueError('REJECTED_INTERPRETATION_CANNOT_HANDOFF')
        if implication.scope != f.scope:
            raise ValueError('IMPLICATION_SCOPE_REQUIRES_MATCHING_INTERPRETATION_VERSION')
        if implication.character_state_ref and implication.character_state_ref not in arc_refs:
            raise ValueError('CHARACTER_STATE_MUST_REFERENCE_EXISTING_ARC')
        if not set(implication.world_fact_refs) <= facts:
            raise ValueError('WORLD_FACT_CANNOT_BE_CHARACTER_INTERPRETATION')
        if implication.boundary_review == 'HOW_LEAK':
            raise ValueError('IMPLICATION_CANNOT_DESIGN_DEPARTMENT')
    if for_approval:
        if (not f.supporting or f.status in ('REJECTED', 'UNSUPPORTED')
                or f.layer != 'WORKING_INTERPRETATION'):
            raise ValueError('UNSUPPORTED_OR_UNSELECTED_INTERPRETATION')
        if not f.evidence_review or f.evidence_review.status != 'APPROVED' or f.canon_consistency != 'PRESERVED':
            raise ValueError('SOURCE_PRESERVATION_EVIDENCE_REVIEW_REQUIRED')
        if any(i.boundary_review != 'QUESTIONS_ONLY' for i in f.implications):
            raise ValueError('IMPLICATION_BOUNDARY_REVIEW_REQUIRED')
    return f


def validate_approval(item: Mapping[str, Any], receipt: InterpretationApproval,
                      artifacts: Mapping[str, Any], current: Mapping[str, str]) -> None:
    f = validate_interpretation(item, artifacts, current, for_approval=True)
    r = InterpretationApproval.model_validate(dump_contract(receipt))
    if (r.subject_id != item['id'] or r.subject_fingerprint != fp(item) or r.work_ref != f.work_ref
            or r.branch_id != f.branch_id or r.scope != f.scope or r.evidence_fingerprint != evidence_fingerprint(item)):
        raise ValueError('INTERPRETATION_APPROVAL_SCOPE_OR_VERSION_MISMATCH')
    if r.decision != 'APPROVE':
        raise ValueError('INTERPRETATION_APPROVAL_REVOKED_OR_REJECTED')
    if (f.status in ('OPEN', 'CONTESTED') or f.confidence == 'CONTESTED') and r.mode != 'PRESERVE_AMBIGUITY':
        raise ValueError('OPEN_INTERPRETATION_CANNOT_BECOME_DETERMINISTIC_CONSTRAINT')


def approved_interpretation(ref: SourcePin, approval_ref: SourcePin, artifacts: Mapping[str, Any],
                            current: Mapping[str, str], approved_refs: tuple[SourcePin, ...]) -> tuple[dict[str, Any], InterpretationApproval]:
    item = resolve(ref, artifacts, current)
    if intent_pin(item) != ref:
        raise ValueError('INTERPRETATION_IDENTITY_MISMATCH')
    if approval_ref not in approved_refs:
        raise ValueError('USER_INTERPRETATION_APPROVAL_REQUIRED')
    receipt = InterpretationApproval.model_validate(resolve(approval_ref, artifacts, current))
    validate_approval(item, receipt, artifacts, current)
    return item, receipt


def department_handoff(ref: SourcePin, approval_ref: SourcePin, implication_id: str,
                       artifacts: Mapping[str, Any], current: Mapping[str, str], *,
                       approved_refs: tuple[SourcePin, ...] = ()) -> dict[str, Any]:
    item, receipt = approved_interpretation(ref, approval_ref, artifacts, current, approved_refs)
    f = facet(item)
    matches = [i for i in f.implications if i.id == implication_id]
    if len(matches) != 1:
        raise ValueError('EXPLICIT_INTERPRETATION_IMPLICATION_REQUIRED')
    i = matches[0]
    return {'interpretationRef':dump_contract(ref), 'approvalRef':dump_contract(approval_ref),
            'implicationId':i.id, 'department':i.department, 'scope':dump_contract(i.scope),
            'form':i.form, 'question':i.question, 'limitations':list(i.limitations),
            'negativeBoundaries':list(f.negative_boundaries),
            'ambiguityPolicy':receipt.mode, 'characterStateRef':i.character_state_ref,
            'worldFactRefs':list(i.world_fact_refs), 'musicPolicy':i.music_policy,
            'implementationOwner':i.department, 'projectionUse':'REASONING_ONLY_EXCLUDE_FROM_PROMPT'}


def validate_consumption(use: InterpretationUse, *, department: str, work_ref: str,
                         scope_refs: tuple[str, ...], values: Mapping[str, Any], artifacts: Mapping[str, Any],
                         current: Mapping[str, str], approved_refs: tuple[SourcePin, ...] = ()) -> dict[str, Any]:
    use = InterpretationUse.model_validate(dump_contract(use))
    handoff = department_handoff(use.interpretation_ref, use.approval_ref, use.implication_id,
                                artifacts, current, approved_refs=approved_refs)
    f = facet(resolve(use.interpretation_ref, artifacts, current))
    if (department != handoff['department'] or work_ref != f.work_ref or dump_contract(use.scope) != handoff['scope']
            or (f.scope.kind != 'WHOLE_WORK' and not set(scope_refs) <= set(f.scope.refs))
            or (f.scope.kind == 'WHOLE_WORK' and f.scope.refs != (work_ref,))):
        raise ValueError('INTERPRETATION_CONSUMER_SCOPE_MISMATCH')
    if use.decision_fingerprint != fp(values):
        raise ValueError('STALE_INTERPRETATION_CONSUMPTION_REVIEW')
    item = resolve(use.interpretation_ref, artifacts, current)
    def strings(value: Any) -> list[str]:
        if isinstance(value, str): return [value]
        if isinstance(value, dict): return [s for v in value.values() for s in strings(v)]
        if isinstance(value, (tuple, list)): return [s for v in value for s in strings(v)]
        return []
    if any(str(item['meaning']) in text for text in strings(dict(values))):
        raise ValueError('INTERPRETATION_PROSE_IS_NOT_PROFESSIONAL_DECISION')
    # Semantic judgments are owner-authored and pinned to the actual decision;
    # no claim that a lexical classifier can understand or rewrite a design.
    if use.disposition == 'INDEPENDENT_SOURCE':
        if not use.independent_source_refs:
            raise ValueError('INDEPENDENT_SOURCE_EVIDENCE_REQUIRED')
        for source in use.independent_source_refs:
            resolve(source, artifacts, current)
        status = 'SOURCE_PRIORITY_REVIEW_REQUIRED'
    elif use.disposition != 'CONSISTENT':
        status = 'INTERPRETATION_DRIFT_CONCERN' if use.disposition == 'DRIFT' else 'INTERPRETATION_REVIEW_REQUIRED'
    else:
        status = 'PASS'
    return {'status':status, 'owner':department, 'interpretationRef':dump_contract(use.interpretation_ref),
            'implicationId':use.implication_id, 'reason':use.reason,
            'independentSourceRefs':[dump_contract(p) for p in use.independent_source_refs], 'rewritten':False}


def validate_interpretation_set(items: list[dict[str, Any]], artifacts: Mapping[str, Any],
                                current: Mapping[str, str]) -> None:
    ids = {str(i['id']) for i in items}
    if len(ids) != len(items): raise ValueError('DUPLICATE_INTERPRETATION_ID')
    for item in items:
        f = validate_interpretation(item, artifacts, current)
        if not set(f.conflicts_with) <= ids - {str(item['id'])}:
            raise ValueError('UNKNOWN_COMPETING_INTERPRETATION')
        for occurrence in f.occurrences:
            if not set(occurrence.related_interpretation_ids) <= ids:
                raise ValueError('MOTIF_INTERPRETATION_UNBOUND')


def project_board(items: list[dict[str, Any]], artifacts: Mapping[str, Any], current: Mapping[str, str], *,
                  approval_refs: Mapping[str, SourcePin] | None = None,
                  approved_refs: tuple[SourcePin, ...] = ()) -> dict[str, Any]:
    validate_interpretation_set(items, artifacts, current)
    rows=[]
    selected=[]
    receipts={}
    for item in items:
        f=facet(item); state='AWAITING_USER_APPROVAL'; approval=(approval_refs or {}).get(str(item['id']))
        if approval:
            _, receipt=approved_interpretation(intent_pin(item),approval,artifacts,current,approved_refs)
            state=receipt.mode
            selected.append(item); receipts[str(item['id'])]=receipt
        rows.append({'id':item['id'],'section':f.section,'meaning':item['meaning'],'confidence':f.confidence,
                     'status':f.status,'approvalState':state,'evidenceRef':dump_contract(intent_pin(item)),
                     'limitations':list(f.limitations)})
    validate_approved_selection(selected, receipts)
    return {'kind':'FILM_INTERPRETATION_BOARD_VIEW','status':'AWAITING_USER_APPROVAL' if any(r['approvalState']=='AWAITING_USER_APPROVAL' for r in rows) else 'REVIEWED_VIEW',
            'adoption':'NOT_ADOPTED','rows':rows,'sourceFingerprint':fp(items),'productionAuthorized':False}


def render_board(board: Mapping[str, Any]) -> str:
    if board.get('kind')!='FILM_INTERPRETATION_BOARD_VIEW': raise ValueError('BOARD_PROJECTION_REQUIRED')
    def clean(value: Any) -> str: return str(value).replace('|','／').replace('\n',' ')
    lines=['# Film Interpretation Board — R3D Candidate', '',
           'CANDIDATE · NOT_ADOPTED · '+str(board['status']), '',
           '批准对象是此电影版本采用的理解，不是文学真理、剧本采纳或生产许可。', '',
           '| 项目 | 候选理解 | 证据状态 / 审批 |', '|---|---|---|']
    for row in board['rows']:
        lines.append('| '+clean(row['section'])+' · '+clean(row['id'])+' | '+clean(row['meaning'])+' | '+clean(row['confidence'])+' / '+clean(row['status'])+' / '+clean(row['approvalState'])+' |')
    lines.extend(['', '支持、反证、限定、源锚点与部门问题见 [证据 JSON](interpretation-candidate.json)。',
                  '可按条目选择：采用、修改、保留歧义或不采用。当前没有任何用户批准；不进入 R3C-R。', ''])
    return '\n'.join(lines)


def require_record_consumption(record: Any, department: str, work_ref: str,
                               artifacts: Mapping[str, Any], current: Mapping[str, str],
                               approved_refs: tuple[SourcePin, ...] = ()) -> None:
    from drama_plugin.contracts.professional import CreativeRecord
    r = CreativeRecord.model_validate(dump_contract(record) if hasattr(record,'model_dump') else record)
    declared = {(u.interpretation_ref.key,u.interpretation_ref.fingerprint) for u in r.interpretation_uses}
    if {(p.key,p.fingerprint) for p in r.source_refs if p.key.startswith('interpretation:') or isinstance(artifacts.get(p.key), dict) and artifacts[p.key].get('interpretation')} != declared:
        raise ValueError('EXPLICIT_INTERPRETATION_CONSUMPTION_REQUIRED')
    for use in r.interpretation_uses:
        if use.approval_ref not in r.source_refs:
            raise ValueError('INTERPRETATION_APPROVAL_DEPENDENCY_REQUIRED')
        receipt=validate_consumption(use,department=department,work_ref=work_ref,
            scope_refs=r.scope_refs,values=r.values,artifacts=artifacts,current=current,approved_refs=approved_refs)
        if receipt['status']!='PASS': raise ValueError(receipt['status']+':'+department)


def validate_record_selection(records: tuple[Any, ...], artifacts: Mapping[str, Any], current: Mapping[str, str]) -> None:
    """A consumer cannot independently combine incompatible adopted readings."""
    from drama_plugin.contracts.professional import CreativeRecord
    items: dict[str, dict[str, Any]] = {}
    receipts: dict[str, InterpretationApproval] = {}
    for raw in records:
        record = CreativeRecord.model_validate(dump_contract(raw) if hasattr(raw, 'model_dump') else raw)
        for use in record.interpretation_uses:
            item = resolve(use.interpretation_ref, artifacts, current)
            identity = str(item['id'])
            items[identity] = item
            receipts[identity] = InterpretationApproval.model_validate(resolve(use.approval_ref, artifacts, current))
    validate_approved_selection(list(items.values()), receipts)


def dependency_pins(value: Mapping[str, Any]) -> tuple[SourcePin, ...]:
    """Walk only declared SourcePins, never invent an all-to-all dependency graph."""
    found: dict[tuple[str,str],SourcePin]={}
    def walk(node: Any) -> None:
        if isinstance(node,dict):
            if set(node)=={'key','kind','fingerprint'}:
                p=SourcePin.model_validate(node);found[(p.key,p.fingerprint)]=p
            else:
                for child in node.values(): walk(child)
        elif isinstance(node,(list,tuple)):
            for child in node: walk(child)
    walk(dict(value))
    return tuple(found.values())


def check_consumer_dependencies(refs: tuple[SourcePin, ...], artifacts: Mapping[str, Any],
                                current: Mapping[str, str], approved_refs: tuple[SourcePin, ...] = ()) -> None:
    """Revalidate actual consumed originals, retaining existing pin/hash semantics.

    Unknown canonical leaves remain the upstream owner's responsibility. Missing
    interpretation originals are never accepted. This computes no global stale map.
    """
    visited: set[tuple[str,str]]=set()
    queue=list(refs)
    checked: list[SourcePin]=[]
    opted_in=False
    while queue:
        ref=queue.pop(); key=(ref.key,ref.fingerprint)
        if key in visited: continue
        visited.add(key)
        checked.append(ref)
        if ref.key not in artifacts:
            if ref.key.startswith(('interpretation:', 'interpretation-approval:')):
                raise ValueError('MISSING_INTERPRETATION_ORIGINAL')
            continue
        value=artifacts[ref.key]
        if not isinstance(value,dict): continue
        opted_in = opted_in or bool(value.get('interpretation'))
        if value.get('schemaVersion')=='creative-bible-v1':
            validate_record_selection(tuple(value.get('content', [])), artifacts, current)
            for record in value.get('content',[]):
                opted_in = opted_in or bool(record.get('interpretationUses'))
                require_record_consumption(record,value['createdByCapability'],value['workRef'],artifacts,current,approved_refs)
        queue.extend(dependency_pins(value))
    if opted_in:
        for consumed in checked:
            if freshness((consumed,),current): raise ValueError('STALE_CONSUMED_SOURCE:'+consumed.key)
            if consumed.key in artifacts: resolve(consumed,artifacts,current)


def validate_approved_selection(items: list[dict[str, Any]], receipts: Mapping[str, InterpretationApproval]) -> None:
    by_id={str(i['id']):i for i in items}
    for item in items:
        r=receipts[str(item['id'])]
        for other in facet(item).conflicts_with:
            if other in by_id and (r.mode!='PRESERVE_AMBIGUITY' or receipts[other].mode!='PRESERVE_AMBIGUITY'):
                raise ValueError('CONFLICTING_INTERPRETATIONS_REQUIRE_AMBIGUITY_OR_USER_SELECTION')
