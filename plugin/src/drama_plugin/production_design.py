"""Source-pinned design handoff and human-evidence review; no generation access."""
from __future__ import annotations
from typing import Any, Literal, Mapping
from drama_plugin.contracts.location_design import LocationDesign, LocationDesignRef, SceneLocationBinding
from drama_plugin.contracts.character_evidence import CharacterCoverageReview
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.production_design import ProductionDesignContent, CharacterState, CharacterVisualSpec
from drama_plugin.contracts.production_design import CastingBrief, CastingReconciliation, CastingTestConditions
from drama_plugin.contracts.dramatic_editorial import DramaticPeakMap, PictureEditPlan


def design_handoff(content: ProductionDesignContent, *, consumer: Literal['asset-resolution','cinematic-direction','shot-design'],
                   state: CharacterState | None = None, for_production: bool = False) -> dict[str, Any]:
    content=ProductionDesignContent.model_validate(dump_contract(content))
    if consumer not in {'asset-resolution','cinematic-direction','shot-design'}:raise ValueError('Wrong design consumer')
    if for_production and content.usage_mode!='APPROVED_DESIGN':raise ValueError('Candidate design cannot replace approved reference')
    if state and (not isinstance(content.spec,CharacterVisualSpec) or state.character_identity!=content.spec.character_identity):
        raise ValueError('Transient state belongs to a different identity')
    raw=dump_contract(content)
    return {'content':raw,'contentFingerprint':sha256_canonical(raw),
            'historicalPolicyFingerprint':sha256_canonical({k: raw['spec'][k] for k in ('historicalBasis', 'evidenceStatus', 'uncertainties', 'forbiddenAssumptions')} if isinstance(content.spec, LocationDesign) else content.spec.historical_constraints),
            'consumer':consumer,'characterState':dump_contract(state) if state else None,
            'productionEligible':content.usage_mode=='APPROVED_DESIGN'}


def verify_design_handoff(raw: dict[str, Any], *, production: bool = False) -> ProductionDesignContent:
    content=ProductionDesignContent.model_validate(raw['content'])
    state=CharacterState.model_validate(raw['characterState']) if raw.get('characterState') else None
    expected=design_handoff(content,consumer=raw['consumer'],state=state,for_production=production)
    if raw!=expected:raise ValueError('Stable design or historical policy changed downstream')
    return content


def casting_briefs(handoff: dict[str, Any], *, reconciliation: CastingReconciliation,
                   conditions: CastingTestConditions, variations: dict[str, str]) -> list[CastingBrief]:
    """Compile an explicitly authorized candidate search without rewriting its source."""
    content = verify_design_handoff(handoff)
    if not isinstance(content.spec, CharacterVisualSpec) or handoff['consumer'] != 'asset-resolution':
        raise ValueError('Casting requires the character handoff to asset-resolution')
    if handoff.get('characterState'):
        raise ValueError('Transient scene state contaminates a neutral casting test')
    reconciliation = CastingReconciliation.model_validate(dump_contract(reconciliation))
    conditions = CastingTestConditions.model_validate(dump_contract(conditions))
    if not 2 <= len(variations) <= 6 or len(set(variations.values())) != len(variations):
        raise ValueError('Casting needs distinct bounded directions')
    return [CastingBrief(candidate_id=key, source_content=content.model_copy(deep=True),
                         source_fingerprint=sha256_canonical(content), reconciliation=reconciliation,
                         conditions=conditions, variation=value) for key, value in variations.items()]


def validate_reference_design(raw: dict[str, Any], asset_content: dict[str, Any]) -> None:
    verify_design_handoff(raw,production=True)
    if asset_content.get('productionDesignFingerprint')!=raw['contentFingerprint']:
        raise ValueError('Asset resolution must use the approved design revision, not redesign identity')


def review_design(observations: dict[str, str]) -> dict[str, Any]:
    required={'identity','visual_authority','faction_hierarchy','faction_contrast','location_specificity',
              'motif_function','storytelling','modern_styling','fantasy_contamination','historical_fidelity',
              'first_glance_importance','silhouette','costume_authority','blocking_authority','camera_privilege',
              'reaction_authority','physical_presence','face_suitability'}
    if set(observations)-required or any(v not in {'PASS','PARTIAL','FAIL','UNKNOWN'} for v in observations.values()):
        raise ValueError('Review uses evidence statuses, not beauty scores')
    missing=sorted(required-set(observations))
    status='FAIL' if 'FAIL' in observations.values() else 'PARTIAL' if missing or any(v!='PASS' for v in observations.values()) else 'PASS'
    return {'status':status,'observations':observations,'missing':missing,'meaning':'Design review is not generated-image validation or user casting approval'}


def review_peaks(plan: DramaticPeakMap) -> dict[str, Any]:
    return {'status':'WARN' if not plan.peaks or not plan.strongest_excerpt else 'PASS',
            'reason':'No earned memory excerpt identified' if not plan.peaks or not plan.strongest_excerpt else plan.memory_review,
            'dynamicRange':plan.dynamic_range,'deleteStrongestTest':plan.delete_strongest_test,
            'automaticCanonWrite':False}


def picture_edit_handoff(plan: PictureEditPlan, *, current_sources: dict[str, str], canon_fingerprint: str) -> dict[str, Any]:
    plan=PictureEditPlan.model_validate(dump_contract(plan))
    if canon_fingerprint!=plan.source_canon_fingerprint:raise ValueError('Finishing cannot rewrite Script Peak or Canon')
    if any(current_sources.get(s.media_id)!=s.content_hash for s in plan.sources):raise ValueError('Edit source Media changed')
    return {'plan':dump_contract(plan),'fingerprint':sha256_canonical(plan),
            'assemblyReady':plan.status=='REVIEWED','sourceMutationAllowed':False}


def resolve_location_design(binding: SceneLocationBinding, *, scene_id: str,
                            current: Mapping[str, str], artifacts: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve one immutable place and return its bounded delta separately."""
    binding = SceneLocationBinding.model_validate(dump_contract(binding))
    ref = binding.location_ref.artifact_ref
    raw = artifacts.get(ref.key)
    if raw is None or current.get(ref.key) != ref.fingerprint or sha256_canonical(raw) != ref.fingerprint:
        raise ValueError('Missing or stale location original: ' + ref.key)
    location = LocationDesign.model_validate(raw)
    if location.id != binding.location_ref.location_id:
        raise ValueError('Location identity mismatch')
    if scene_id not in location.scene_refs:
        raise ValueError('Location is not designed for this scene')
    return {'locationRef': dump_contract(binding.location_ref),
            'base': dump_contract(location),
            'localOverride': dump_contract(binding.local_override) if binding.local_override else None,
            'productionAuthorized': False}


def review_character_coverage(review: CharacterCoverageReview,
                              characters: tuple[CharacterVisualSpec, ...]) -> dict[str, Any]:
    """Review explicit identities and placements, never names or a headcount KPI."""
    review = CharacterCoverageReview.model_validate(dump_contract(review))
    characters = tuple(CharacterVisualSpec.model_validate(dump_contract(c)) for c in characters)
    by_id = {c.character_identity: c for c in characters}
    if len(by_id) != len(characters):
        raise ValueError('Duplicate character identity')
    missing: list[str] = []
    notes: list[dict[str, Any]] = []
    for c in characters:
        if c.evidence is None:
            missing.append('CHARACTER_EVIDENCE_REQUIRED:' + c.character_identity)
        elif not set(c.evidence.scene_refs) <= set(review.scene_refs):
            missing.append('CHARACTER_SCENE_OUTSIDE_REVIEW:' + c.character_identity)
        elif c.evidence.historical_status == 'DRAMATIC_RECONSTRUCTION' and len(set(c.evidence.dramatic_function)) >= 5:
            notes.append({'code': 'FICTIONAL_PROXY_OVERLOAD', 'severity': 'NOTE',
                          'characterIdentity': c.character_identity,
                          'functions': list(c.evidence.dramatic_function),
                          'repairOwner': 'director'})
    for d in review.decisions:
        candidate = by_id.get(d.character_identity)
        placement = next((p for p in candidate.evidence.scene_placements if p.scene_id == d.scene_id), None) if candidate and candidate.evidence else None
        if d.decision == 'UNRESOLVED':
            missing.append('CHARACTER_COVERAGE_UNRESOLVED:' + d.character_identity + ':' + d.scene_id)
        elif d.decision == 'INCLUDE' and (candidate is None or candidate.evidence is None or candidate.evidence.historical_status != 'DOCUMENTED' or placement is None or placement.evidence_status != 'DOCUMENTED'):
            missing.append('DOCUMENTED_ACTOR_PLACEMENT_REQUIRED:' + d.character_identity + ':' + d.scene_id)
        elif d.decision == 'EXCLUDE_WITH_REASON' and placement is not None:
            missing.append('CHARACTER_COVERAGE_DECISION_CONFLICT:' + d.character_identity + ':' + d.scene_id)
    return {'status': 'CHARACTER_COVERAGE_NOT_READY' if missing else 'CHARACTER_COVERAGE_READY',
            'missing': missing, 'notes': notes, 'productionAuthorized': False}
