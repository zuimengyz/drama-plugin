"""Read-only package sealing and evidence gates, independent of Host and Provider."""
from __future__ import annotations
from typing import Any
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.sequence import SequencePackage, FilmReview
from drama_plugin.contracts.production_freeze import ProductionDesignFreeze, FreezeEntry


def sequence_handoff(package: SequencePackage, current_fingerprints: dict[str, str]) -> dict[str, Any]:
    package = SequencePackage.model_validate(dump_contract(package))
    for pin in package.source_pins:
        if current_fingerprints.get(pin.key) != pin.fingerprint:
            raise ValueError('Sequence source missing or changed: ' + pin.key)
    unresolved = list(package.unresolved)
    unresolved.extend(note for b in package.bibles for note in b.unresolved)
    unresolved.extend(note for s in package.shots for note in s.unresolved)
    return {'package': dump_contract(package), 'fingerprint': sha256_canonical(package),
            'designReady': package.status == 'DESIGN_REVIEWED' and not unresolved,
            'unresolved': unresolved, 'productionAuthorized': False,
            'meaning': 'Use the existing MCP route, current approvals and budget separately; no adoption or generation permission.'}


def _coverage(review: FilmReview, modes: set[str]) -> list[list[float]]:
    intervals = sorted((o.start, o.end) for o in review.observations if o.mode in modes)
    missing = []
    end = 0.0
    for start, stop in intervals:
        if start > end:
            missing.append([end, start])
        end = max(end, stop)
    if end < review.duration:
        missing.append([end, review.duration])
    return missing


def film_review_verdict(review: FilmReview, current_media_hash: str, *, require_director: bool = False) -> dict[str, Any]:
    review = FilmReview.model_validate(dump_contract(review))
    if review.media_hash != current_media_hash:
        raise ValueError('Review belongs to different rendered bytes; rewatch repaired output')
    gaps = _coverage(review, {'NORMAL_AV'})
    blocked = [f.key for f in review.findings if f.severity == 'MAJOR' and not f.resolved]
    checks = (review.technical, review.story_rhythm, review.visual_continuity, review.sound)
    status = 'REPAIR_REQUIRED' if blocked or 'FAIL' in checks else 'REVIEW_INCOMPLETE'
    if not blocked and not gaps and all(c == 'PASS' for c in checks) and review.persistence_verified:
        status = 'CONTENT_REVIEW_COMPLETE_PENDING_USER_ADOPTION'
    if review.performance_alignment:
        from drama_plugin.performance_direction import ALIGNMENT_DIMENSIONS
        if 'FAIL' in review.performance_alignment.values():
            status = 'REPAIR_REQUIRED'
        elif (set(review.performance_alignment) != ALIGNMENT_DIMENSIONS
              or 'UNKNOWN' in review.performance_alignment.values()
              or review.performance_review_basis != 'OBSERVED_MEDIA'
              or not review.performance_required_beats
              or set(review.performance_beats) != set(review.performance_required_beats)
              or any(set(row) != ALIGNMENT_DIMENSIONS or any(v != 'PASS' for v in row.values()) for row in review.performance_beats.values())):
            status = 'REVIEW_INCOMPLETE'
    if review.performance_coverage_fingerprint:
        from drama_plugin.performance_coverage import full_av_coverage
        if full_av_coverage(review)['status'] != 'COVERED':
            status = 'AV_PERFORMANCE_COVERAGE_INCOMPLETE'
    if require_director and review.director is None:
        status = 'INSUFFICIENT_EVIDENCE'
    elif review.director and review.director.disposition != 'APPROVE':
        status = 'INSUFFICIENT_EVIDENCE' if review.director.disposition == 'INSUFFICIENT_EVIDENCE' else 'REPAIR_REQUIRED'
    if review.editorial_usability:
        if any(e.outside_approved_intent for e in review.editorial_usability):
            status = 'REQUIRES_ADAPTIVE_DIRECTOR_REVIEW'
        elif any(e.basis != 'OBSERVED_MEDIA' for e in review.editorial_usability):
            status = 'REVIEW_INCOMPLETE'
        elif any(e.editorial_usability != 'USABLE_FULL' for e in review.editorial_usability):
            status = 'EDITORIAL_REPAIR_REQUIRED'
    return {'status': status, 'normalAvCoverageGaps': gaps, 'unresolvedMajorFindings': blocked,
            'persistenceVerified': review.persistence_verified, 'userAdoption': 'UNCHANGED',
            'warning': 'Observation records are observer attestations, not proof that a tool or model can hear or watch.'}


def executable_sequence_handoff(package: SequencePackage, current_fingerprints: dict[str, str],
                                freeze: 'ProductionDesignFreeze',
                                current_entries: tuple['FreezeEntry', ...]) -> dict[str, Any]:
    """Design completeness and approval completeness are independent; never grants spend."""
    from drama_plugin.production_freeze import freeze_gate
    from drama_plugin.contracts.production_freeze import ProductionDesignFreeze
    package = SequencePackage.model_validate(dump_contract(package))
    freeze = ProductionDesignFreeze.model_validate(dump_contract(freeze))
    base = sequence_handoff(package, current_fingerprints)
    ref = package.production_design_freeze
    if (not ref or ref.snapshot_id != freeze.snapshot_id or ref.fingerprint != sha256_canonical(freeze)
            or package.scope_id != freeze.scope):
        raise ValueError('PRODUCTION_DESIGN_FREEZE_STALE_OR_MISSING')
    entries = {e.semantic_key: e for e in freeze.entries}
    design_missing = list(package.unresolved)
    for shot in package.shots:
        clip = shot.production
        if not clip:
            design_missing.append(shot.key + ': EXECUTABLE_CLIP_MISSING')
            continue
        design_missing.extend(shot.unresolved)
        for duty in clip.reference_duties:
            if duty.requirement == 'REQUIRED':
                entry = entries.get(duty.freeze_entry_key or '')
                if entry is None or entry.requirement != 'REQUIRED' or entry.role != duty.role:
                    raise ValueError('REQUIRED_REFERENCE_NOT_IN_FREEZE: ' + duty.key)
        if any(a.mount_orientation for a in clip.choreography):
            if not any(b.living_asset for b in package.bibles if b.key in clip.asset_refs):
                raise ValueError('MOUNT_INTERACTION_BIBLE_MISSING')
    if any(not b.acceptance_criteria for b in package.bridges):
        design_missing.append('BRIDGE_ACCEPTANCE_MISSING')
    gate = freeze_gate(freeze, current_entries)
    ready = package.status == 'DESIGN_REVIEWED' and not design_missing
    return {**base, 'designReady': ready, 'productionDesignComplete': gate['status'] == 'COMPLETE',
            'generationAuthorized': False, 'produced': False, 'reviewed': False, 'userAdopted': False,
            'designMissing': design_missing, 'productionDesignGate': gate,
            'reviewInterface': {'required': 'FilmReview.mediaHash == actual output SHA-256',
                                'observation': 'NORMAL_AV coverage remains mandatory for film completion'},
            'status': 'EXECUTABLE_DESIGN_READY' if ready else 'PARTIAL'}
