"""Pure event placement/review guards. No generation, editing, adoption or formal IO."""
from __future__ import annotations
from typing import Any, Mapping, Sequence
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.film_score import FilmScorePlan

SILENT = {'NO_SCORE', 'NO_SCORE_MUST_PRESERVE', 'DIEGETIC_ONLY'}


def review_placement(plan: FilmScorePlan, *, current: Mapping[str, str],
                     action_scenes: Mapping[str, str]) -> dict[str, Any]:
    plan = FilmScorePlan.model_validate(dump_contract(plan))
    pins = [*plan.source_pins, plan.film_intent_ref, *(d.performance_intent_ref for d in plan.scene_music_decisions)]
    for cue in plan.music_cues:
        policy = cue.yield_policy
        if policy is None:
            raise ValueError('EVERY_PLACED_CUE_REQUIRES_YIELD_POLICY')
        pins.extend(policy.protected_no_score_refs)
        pins.extend(e.source_ref for e in policy.events)
        for pin in (*policy.protected_no_score_refs, *(e.source_ref for e in policy.events)):
            if action_scenes.get(pin.key) not in plan.scene_ids:
                raise ValueError('PLACEMENT_REQUIRES_REAL_SOURCE_ACTION')
        for event in policy.events:
            scene = action_scenes[event.source_ref.key]
            decision = next(d for d in plan.scene_music_decisions if d.scene_id == scene)
            if event.action not in {'STOP', 'DROP', 'DO_NOT_RETURN'}:
                if scene not in cue.scene_ids or decision.decision in SILENT or cue.cue_id not in decision.cue_refs:
                    raise ValueError('SCORE_CANNOT_OVERRIDE_SILENCE_OR_DIEGETIC_SOUND')
                if event.source_ref.key in plan.excluded_performance_refs:
                    raise ValueError('HISTORICAL_VERSE_NOT_FILM_SCORE')
    if any(current.get(p.key) != p.fingerprint for p in pins):
        raise ValueError('STALE_MUSIC_PLACEMENT_SOURCE')
    return {'status':'PLACEMENT_DESIGN_READY', 'planFingerprint':sha256_canonical(plan),
            'scenes':len(plan.scene_ids), 'scoreScenes':[d.scene_id for d in plan.scene_music_decisions if d.cue_refs],
            'artisticAdoption':False, 'pictureConformed':False, 'providerCalls':0}


def require_score_permission(plan: FilmScorePlan, *, scene_id: str, action_refs: Sequence[str],
                             cue_id: str) -> None:
    """Finishing cannot cure a protection conflict by changing a BGM label/volume."""
    plan = FilmScorePlan.model_validate(dump_contract(plan))
    decision = next((d for d in plan.scene_music_decisions if d.scene_id == scene_id), None)
    if decision is None or decision.decision in SILENT:
        raise ValueError('NO_SCORE_ACTIVE_DECISION_REQUIRES_DIRECTOR_MUSIC_REREVIEW')
    cue = next((c for c in plan.music_cues if c.cue_id == cue_id), None)
    if cue is None or cue_id not in decision.cue_refs or cue.yield_policy is None:
        raise ValueError('CURRENT_CUE_PLACEMENT_REQUIRED')
    if not action_refs or set(action_refs) & set(plan.excluded_performance_refs):
        raise ValueError('SOURCE_ACTION_REQUIRED_HISTORICAL_VERSE_EXCLUDED')
    protected = {p.key for c in plan.music_cues if c.yield_policy for p in c.yield_policy.protected_no_score_refs}
    if protected.intersection(action_refs):
        raise ValueError('NO_SCORE_MUST_PRESERVE')
    permitted = {e.source_ref.key for e in cue.yield_policy.events if e.action in {'ENTER','BUILD','HOLD','THIN','DUCK','RETURN'}}
    exits={e.source_ref.key for e in cue.yield_policy.events if e.action in {'DROP','STOP'}}
    if set(action_refs) & permitted & exits:
        raise ValueError('MIXED_PHASE_SOURCE_ACTION_REQUIRES_PICTURE_CONFORM_REVIEW')
    if not set(action_refs) <= permitted:
        raise ValueError('ACTION_OUTSIDE_SCORE_PERMISSION')


def reconcile_material(*, material_hash: str, planned: str, realized: str,
                       user_receipt: Mapping[str, Any], disposition: str) -> dict[str, Any]:
    """Derived review facet; planned function does not dictate actual sound or adoption."""
    if user_receipt.get('materialHash') != material_hash or user_receipt.get('contentListening') != 'ACCEPTABLE_MATERIAL':
        raise ValueError('SOURCE_BOUND_USER_LISTENING_REQUIRED')
    if disposition not in {'REJECT','REGENERATE','REPLACE_FUNCTION'}:
        raise ValueError('EXPLICIT_RECONCILIATION_REQUIRED')
    return {'materialHash':material_hash, 'plannedFunction':planned, 'realizedFunction':realized,
            'realizedEvidence':'USER_LISTENING', 'functionMismatch':'PARTIAL' if planned != realized else 'NONE',
            'disposition':disposition, 'contentListeningAcceptable':True, 'placementReviewRequired':True,
            'generationFailed':False, 'approved':False, 'adopted':False, 'productionEligible':False}


def validate_finishing_score_binding(recipe: Mapping[str, Any]) -> None:
    """Opt-in FilmScorePlan binding for the existing renderer; legacy recipes unchanged.

    Proposal plans can be reviewed, never rendered. Real shot/media ranges belong to
    Picture Conform, not to these source-action events. No inline override bypass.
    """
    facet = recipe.get('scorePlacement')
    if facet is None:
        if any(layer.get('scoreBinding') for layer in recipe.get('layers', [])):
            raise ValueError('SCORE_PLAN_REQUIRED')
        return
    plan = FilmScorePlan.model_validate(facet['plan'])
    if facet.get('planFingerprint') != sha256_canonical(plan):
        raise ValueError('STALE_SCORE_PLAN_BINDING')
    review_placement(plan, current=facet['current'], action_scenes=facet['actionScenes'])
    if plan.source_kind != 'FORMAL' or plan.review_status != 'DESIGN_REVIEWED':
        raise ValueError('PROPOSAL_SCORE_CANNOT_ENTER_FORMAL_FINISHING')
    bgm = recipe.get('soundPlan', {}).get('bgm', {})
    layers = [x for x in recipe.get('layers', []) if x.get('role') == 'BGM']
    if bgm.get('decision') != 'NO_BGM' and not layers:
        raise ValueError('ACTIVE_SCORE_REQUIRES_BOUND_LAYERS')
    for layer in layers:
        binding = layer.get('scoreBinding', {})
        if binding.get('planFingerprint') != sha256_canonical(plan):
            raise ValueError('LAYER_CURRENT_SCORE_BINDING_REQUIRED')
        require_score_permission(plan, scene_id=binding.get('sceneId', ''),
                                 action_refs=binding.get('actionRefs', []), cue_id=binding.get('cueId', ''))
