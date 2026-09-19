"""Pure editorial handoff and authority guards; no rendering or adaptive decisions."""
from __future__ import annotations
from typing import Any
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.editorial_authority import EditorialAuthority, CoverageRequirement, EditorialUsability

def editorial_handoff(authority: EditorialAuthority, current_sources: dict[str,str], approved_priorities: dict[str,dict[str,str]]) -> dict[str,Any]:
    pins=list(authority.source_authority)
    for r in authority.requirements:pins.extend(r.intent.source_authority)
    for u in authority.coverage_units:pins.extend(u.source_authority)
    for t in authority.transitions:pins.extend(t.source_authority)
    if any(current_sources.get(p.key)!=p.fingerprint for p in pins):raise ValueError('Stale editorial source authority')
    for r in authority.requirements:
        levels=approved_priorities.get(r.intent.director_intent_id)
        if not levels or set(r.intent.protected_priority_ids)!={k for k,v in levels.items() if v in {'P0','P1'}}:
            raise ValueError('Editorial protection differs from approved priority authority')
    required={u.key for u in authority.coverage_units if u.necessity=='REQUIRED'}
    # A certificate of function loss, not a mathematical proof of artistic optimality.
    loss={key:[r.key for r in authority.requirements if key in r.required_coverage] for key in required}
    return {'planFingerprint':sha256_canonical(authority),'requiredCoverageUnits':len(required),
            'optionalCoverageUnits':len(authority.coverage_units)-len(required),'removalWitnesses':loss,
            'minimumClaim':'Human-declared minimal function set; each removed unit loses named evidence. Reassess equivalence before adding optional material.',
            'designBound':True,'mediaExecutable':False,'generationAuthorized':False,
            'nextOwner':'shot-design formalization; cinematic-finishing measured PictureEditPlan after actual observation'}

def cut_verdict(requirement: CoverageRequirement, completed_events: tuple[str,...], *,
                reaction_complete: bool | None, spatial_ready: bool | None,
                audio_ready: bool | None, priority_impact: str='NONE',
                p2_grammar_equivalent: bool | None=None) -> str:
    if priority_impact not in {'NONE','P0','P1','P2','P3'}:raise ValueError('Unknown priority impact')
    if priority_impact in {'P0','P1'}:return 'UPSTREAM_AUTHORITY_REQUIRED'
    if priority_impact=='P2' and p2_grammar_equivalent is not True:return 'UPSTREAM_AUTHORITY_REQUIRED'
    seq=requirement.cut.hold.event_sequence
    if completed_events!=seq or any(x is not True for x in [reaction_complete,spatial_ready,audio_ready]):return 'CUT_PROHIBITED'
    return 'CUT_ALLOWED_BY_DECLARED_EVIDENCE'

def usability_handoff(value: EditorialUsability, current_media_hash: str) -> dict[str,Any]:
    if value.media_hash!=current_media_hash:raise ValueError('Changed media invalidates usability')
    if value.outside_approved_intent:
        return {'status':'OUTSIDE_APPROVED_INTENT','next':'REQUIRES_ADAPTIVE_DIRECTOR_REVIEW','adopt':False}
    return {'status':value.editorial_usability,'basis':value.basis,'adopt':False,
            'observationClaimed':value.basis=='OBSERVED_MEDIA',
            'repairOptions':[dump_contract(x) for x in value.repair_options],
            'pickupRequirements':list(value.pickup_requirements)}

def compression_verdict(*, what_is_removed: str, why_redundant: str,
                        surviving_intent_ids: tuple[str,...], priority_impact: str) -> str:
    if not what_is_removed.strip() or not why_redundant.strip() or not surviving_intent_ids:raise ValueError('Compression needs removal, redundancy and surviving intent evidence')
    if priority_impact not in {'NONE','P0','P1','P2','P3'}:raise ValueError('Unknown priority impact')
    return 'COMPRESSION_CANDIDATE' if priority_impact=='NONE' else 'UPSTREAM_AUTHORITY_REQUIRED'

def editorial_picture_handoff(authority: EditorialAuthority, plan: Any,
                              decisions: tuple[Any,...], *, current_sources: dict[str,str],
                              approved_priorities: dict[str,dict[str,str]],
                              current_media_hashes: dict[str,str], canon_fingerprint: str) -> dict[str,Any]:
    """Compose authority with existing measured PictureEditPlan; does not render."""
    from drama_plugin.contracts.dramatic_editorial import PictureEditPlan
    from drama_plugin.contracts.editorial_authority import EditorialDecision
    from drama_plugin.production_design import picture_edit_handoff
    plan=PictureEditPlan.model_validate(plan)
    decisions=tuple(EditorialDecision.model_validate(d) for d in decisions)
    editorial_handoff(authority,current_sources,approved_priorities)
    if {d.edit_index for d in decisions}!=set(range(len(plan.picture_edit))):
        raise ValueError('Every measured edit needs a source-bound decision')
    requirements={r.key:r for r in authority.requirements}
    for d in decisions:
        r=requirements.get(d.coverage_requirement_id)
        if r is None or (r.intent.scene_id,r.intent.director_intent_id,r.cut.key)!=(d.scene_id,d.director_intent_id,d.cut_condition_id):
            raise ValueError('Decision provenance does not resolve')
        if any(current_sources.get(p.key)!=p.fingerprint for p in d.source_authority):raise ValueError('Stale decision authority')
        if cut_verdict(r,d.completed_events,reaction_complete=d.reaction_complete,spatial_ready=d.spatial_ready,audio_ready=d.audio_ready,priority_impact=d.priority_impact,p2_grammar_equivalent=d.p2_grammar_equivalent)!='CUT_ALLOWED_BY_DECLARED_EVIDENCE':
            raise ValueError('Cut prohibited or upstream authority required')
    result=picture_edit_handoff(plan,current_sources=current_media_hashes,canon_fingerprint=canon_fingerprint)
    result['missingEditorialRequirements']=sorted(set(requirements)-{d.coverage_requirement_id for d in decisions})
    if result['missingEditorialRequirements']:
        result['assemblyReady']=False
    result['editorialDecisionFingerprint']=sha256_canonical([dump_contract(d) for d in decisions])
    result['evidenceLimit']='Observer attestations must be verified against actual bytes; no automatic event recognition'
    return result
