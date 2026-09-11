"""Provider-neutral, evidence-bound video qualification; no generation or ranking claims."""
from __future__ import annotations

from datetime import datetime, timezone
from collections.abc import Callable
from typing import Any, Literal

from pydantic import Field
from drama_plugin.config.video_route import VideoRoutePolicy, RouteMode, resolve_policy, canonical_model_key

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.visual.frame_request import Hash, Record, Text
from drama_plugin.visual.reference_duties import ReferenceDuty, validate_duties, validate_endpoint
from drama_plugin.visual.execution import ExecutionRoute, require_execution


class Evidence(Record):
    source: Text
    checked_at: datetime
    expires_at: datetime
    verified: bool

    def current(self, now: datetime) -> bool:
        return (self.verified and self.checked_at.tzinfo is not None
                and self.expires_at.tzinfo is not None
                and self.checked_at <= now < self.expires_at)


class VideoInput(Record):
    media_id: Text
    version: Text
    content_hash: Hash
    target_id: Text
    role: Literal['FIRST_FRAME', 'LAST_FRAME', 'REFERENCE']
    state: Text
    review_evidence: Text
    source_ref: Text | None = None
    mime_type: Text | None = None
    endpoint_state: Text | None = None
    endpoint_evidence: Text | None = None
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)


class Requirements(Record):
    work_id: Text
    scene_id: Text
    shot_id: Text
    target_id: Text
    shot_type: Text
    source_fingerprint: Hash
    mode: Literal['SINGLE_IMAGE', 'START_END', 'TEXT_TO_VIDEO']
    controls: tuple[Text, ...] = Field(min_length=1)
    duration_seconds: int = Field(gt=0)
    aspect_ratio: Text
    sound: Text
    language: Text | None = None
    frozen_creative: dict[str, Any] = Field(min_length=1)
    inputs: tuple[VideoInput, ...] = Field(max_length=2)
    reference_duties: tuple[ReferenceDuty, ...] = ()
    required: tuple[Text, ...] = Field(min_length=1)
    forbidden: tuple[Text, ...] = Field(min_length=1)


def validate_requirements(r: Requirements) -> None:
    from drama_plugin.visual.cinematic import validate_selection_handoff
    spec = validate_selection_handoff(r.frozen_creative, work_id=r.work_id, scene_id=r.scene_id,
                               shot_id=r.shot_id, duration=r.duration_seconds)
    if spec:
        intent = spec.source_sound_intent
        if intent is None:
            raise ValueError('SOURCE_SOUND_INTENT_REQUIRED_FOR_NEW_REQUEST')
        if (intent.native_audio_policy == 'REQUIRED' and r.sound == 'SILENT' or
                intent.native_audio_policy == 'DISABLED' and r.sound != 'SILENT' or
                intent.canonical_dialogue_bindings and r.sound == 'SILENT'):
            raise ValueError('SOURCE_SOUND_ROUTE_CONFLICT')
        validate_duties(spec, r.inputs, r.reference_duties)
        for inp in r.inputs:
            validate_endpoint(inp, spec)
    roles = [i.role for i in r.inputs]
    if r.mode == 'TEXT_TO_VIDEO' and (roles or 'TEXT' not in r.controls):
        raise ValueError('TEXT_TO_VIDEO_REQUIRES_ZERO_INPUTS')
    if r.mode == 'SINGLE_IMAGE' and roles not in [['FIRST_FRAME'], ['REFERENCE']]:
        raise ValueError('SINGLE_IMAGE_REQUIRES_EXACTLY_ONE_INPUT')
    if r.mode == 'START_END' and roles != ['FIRST_FRAME', 'LAST_FRAME']:
        raise ValueError('START_END_REQUIRES_ORDERED_PAIR')
    if any(i.target_id != r.target_id for i in r.inputs):
        raise ValueError('CROSS_TARGET_INPUT')
    if len({i.media_id for i in r.inputs}) != len(r.inputs):
        raise ValueError('DUPLICATE_ENDPOINT_MEDIA')
    needed = {'TEXT'} if not roles else {'FIRST_FRAME'} if roles == ['FIRST_FRAME'] else {'REFERENCE'} if roles == ['REFERENCE'] else {'FIRST_FRAME', 'LAST_FRAME'}
    if not needed <= set(r.controls):
        raise ValueError('INPUT_ROLE_CONTROL_MISMATCH')


def direction_quality(material: dict[str, Any], c: Candidate, shot_type: str) -> dict[str, Any]:
    """Expose director demands against scoped observations, never model scores."""
    from drama_plugin.visual.cinematic import verify_frozen
    if not material:
        return {}
    spec = verify_frozen(material)
    requirements = spec.execution_requirements
    demands = {f'{group}.{key}': value for group, values in (
        ('performance', requirements.performance), ('motion', requirements.motion),
        ('continuity', requirements.continuity)) for key, value in values.items()}
    observed = {key: c.quality.dimensions.get(key, 'UNKNOWN') if shot_type in c.quality.task_types else 'UNKNOWN' for key in demands}
    return {'fingerprint': material['fingerprint'], 'execution_requirements': requirements.model_dump(mode='json', by_alias=True),
            'reference_requirements': [x.model_dump(mode='json', by_alias=True) for x in spec.reference_requirements],
            'observed': observed,
            'failed': [key for key, level in demands.items() if level == 'HIGH' and observed[key] == 'FAIL'],
            'proven': all(observed[key] == 'PASS' for key, level in demands.items() if level == 'HIGH')}


class Cost(Record):
    # Each component is incremental; reused assets are explicitly zero.
    components: dict[Text, float | None] = Field(min_length=1)
    unit: Literal['credits'] = 'credits'
    evidence: Evidence
    uncertainty: tuple[Text, ...] = ()

    def total(self) -> float | None:
        import math
        if any(v is None for v in self.components.values()):
            return None
        values = [v for v in self.components.values() if v is not None]
        if any(not math.isfinite(v) or v < 0 for v in values):
            raise ValueError('INVALID_COST')
        return sum(values)


class Quality(Record):
    status: Literal['UNKNOWN', 'PASS', 'FAIL'] = 'UNKNOWN'
    samples: int = Field(ge=0, default=0)
    task_types: tuple[Text, ...] = ()
    evidence: tuple[Text, ...] = ()
    dimensions: dict[str, Literal['PASS', 'FAIL', 'UNKNOWN']] = Field(default_factory=dict)


class Candidate(Record):
    candidate_id: Text
    model: Text
    variant: Text
    mode: Literal['SINGLE_IMAGE', 'START_END', 'TEXT_TO_VIDEO']
    template: Text
    graph_hash: Hash
    adapter_fingerprint: Hash
    parameters: dict[str, Any]
    capability: dict[str, Any] = Field(default_factory=dict)
    # Each layer must verify the exact combination, not union separate claims.
    layers: dict[Literal['official', 'interface', 'template', 'project'], Evidence]
    controls: tuple[Text, ...]
    combinations: tuple[tuple[Text, ...], ...]
    durations: tuple[int, ...]
    aspect_ratios: tuple[Text, ...]
    sounds: tuple[Text, ...]
    languages: tuple[Text, ...] = ()
    fit_concerns: tuple[Text, ...] = ()
    quality: Quality
    cost: Cost
    risks: tuple[Text, ...] = ()


# One Host boundary, like production.video_verifier; no provider import in Core.
execution_sealer: Callable[[Requirements, Candidate, dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None

def qualify(r: Requirements, c: Candidate, *, now: datetime | None = None,
            trial: bool = True) -> dict[str, Any]:
    r = Requirements.model_validate(r.model_dump())
    c = Candidate.model_validate(c.model_dump())
    validate_requirements(r)
    now = now or datetime.now(timezone.utc)
    reasons = []
    layers: tuple[Literal['official', 'interface', 'template', 'project'], ...] = ('official', 'interface', 'template', 'project')
    for layer in layers:
        e = c.layers.get(layer)
        if e is None or not e.current(now):
            reasons.append('UNVERIFIED_OR_EXPIRED:' + layer)
    if c.mode != r.mode:
        reasons.append('MODE_MISMATCH')
    if not set(r.controls) <= set(c.controls):
        reasons.append('MISSING_REQUIRED_CONTROL')
    if not any(set(r.controls) <= set(combo) for combo in c.combinations):
        reasons.append('UNSUPPORTED_CONTROL_COMBINATION')
    if r.duration_seconds not in c.durations:
        reasons.append('NARRATIVE_DURATION_UNSUPPORTED')
    if r.aspect_ratio not in c.aspect_ratios:
        reasons.append('ASPECT_RATIO_UNSUPPORTED')
    if r.sound not in c.sounds or (r.language and r.language not in c.languages):
        reasons.append('REQUIRED_SOUND_OR_LANGUAGE_UNSUPPORTED')
    q = c.quality
    if q.status == 'UNKNOWN' and (q.samples or q.evidence or q.dimensions):
        reasons.append('UNKNOWN_QUALITY_CANNOT_CLAIM_SAMPLES')
    if q.status != 'UNKNOWN' and (not q.samples or not q.evidence or not q.task_types):
        reasons.append('QUALITY_CLAIM_WITHOUT_EVIDENCE')
    scoped_pass = (q.status == 'PASS' and r.shot_type in q.task_types
                   and all(q.dimensions.get(k) == 'PASS' for k in
                           ['identity_props', 'action_narrative', 'sound_performance', 'continuity']))
    direction = direction_quality(r.frozen_creative.get('cinematic_direction', {}), c, r.shot_type)
    if direction:
        reasons.extend('DIRECTOR_REQUIREMENT_FAILED:' + k for k in direction['failed'])
        scoped_pass = scoped_pass and direction['proven']
    if q.status == 'FAIL' and r.shot_type in q.task_types:
        reasons.append('PROJECT_QUALITY_FAILED')
    if not trial and not scoped_pass:
        reasons.append('LIMITED_TRIAL_ONLY')
    if not c.cost.evidence.current(now) or c.cost.uncertainty or c.cost.total() is None:
        reasons.append('COST_UNRESOLVED_OR_EXPIRED')
    total = c.cost.total()
    return {'candidate_id': c.candidate_id, 'eligible': not reasons, 'exclusions': reasons,
            'qualification': 'QUALIFIED' if scoped_pass else 'LIMITED_TRIAL',
            'quality': q.model_dump(mode='json'), 'incremental_credits': total,
            'fit_concerns': list(c.fit_concerns), **({'cinematic_direction': direction} if direction else {})}


def model_key(c: Candidate) -> str:
    key = canonical_model_key(c.model)
    if c.capability.get('model_key', key) != key:
        raise ValueError('MODEL_IDENTITY_MISMATCH')
    return key


def _select_qualified(candidates: list[Candidate], results: list[dict[str, Any]], *,
                      policy: VideoRoutePolicy | None = None,
                      task_policy: VideoRoutePolicy | None = None,
                      dry_run: bool = False) -> dict[str, Any]:
    """Order/scope only. Never alter qualification, costs, or provider controls."""
    configured = resolve_policy(policy or VideoRoutePolicy())
    effective = resolve_policy(configured, task_policy)
    keys = {c.candidate_id: model_key(c) for c in candidates}
    by_id = {c.candidate_id: c for c in candidates}
    if len(by_id) != len(candidates):
        raise ValueError('DUPLICATE_CANDIDATE')
    def selectable(v: dict[str, Any]) -> bool:
        return bool(v['eligible'] or dry_run and set(v['exclusions']) <= {'COST_UNRESOLVED_OR_EXPIRED'})
    def rank(v: dict[str, Any]) -> tuple[Any, ...]:
        return (not v['eligible'], v['qualification'] != 'QUALIFIED',
                v['incremental_credits'] if v['incremental_credits'] is not None else float('inf'), v['candidate_id'])
    selected = None
    attempts: list[dict[str, Any]] = []
    groups = [None] if effective.mode == RouteMode.AUTO else list(effective.sequence())
    for key in groups:
        group = [v for v in results if key is None or keys[v['candidate_id']] == key]
        eligible = sorted((v for v in group if selectable(v)), key=rank)
        winner = eligible[0]['candidate_id'] if eligible else None
        if not group:
            attempts.append({'model': key, 'qualification': 'NOT_EVALUATED', 'accepted': False,
                             'reason': ['NO_CANDIDATE_EVIDENCE']})
        for v in group:
            attempts.append({'model': keys[v['candidate_id']], **v,
                             'accepted': v['candidate_id'] == winner,
                             'reason': v['exclusions'] or [v['qualification']],
                             'qualification_fingerprint': sha256_canonical(v)})
        if winner is not None:
            selected = winner
            break
    effective_json = effective.model_dump(mode='json')
    resolution = {'configured_policy': configured.model_dump(mode='json'),
                  'effective_policy': effective_json, 'source': effective.source.value,
                  'preferred_model': effective.preferred_model, 'fallbacks': list(effective.fallbacks),
                  'active_sequence': list(effective.sequence()),
                  'fallbacks_state': 'ACTIVE' if effective.mode == RouteMode.PREFER else 'INACTIVE',
                  'attempts': attempts, 'selected_model': keys[selected] if selected else None,
                  'selected_candidate': selected,
                  'selected_candidate_fingerprint': sha256_canonical(by_id[selected].model_dump(mode='json')) if selected else None,
                  'policy_fingerprint': sha256_canonical(effective_json),
                  'selection_reason': ('LEGACY_QUALIFICATION_QUALITY_COST' if effective.mode == RouteMode.AUTO else 'FIRST_EXECUTABLE_POLICY_MODEL') if selected else 'NO_EXECUTABLE_CANDIDATE',
                  'dry_run_only': dry_run}
    return {'selected': selected, 'candidates': results, 'route_policy_resolution': resolution}


def _policy_candidates(candidates: list[Candidate], policy: VideoRoutePolicy | None,
                       task_policy: VideoRoutePolicy | None) -> list[Candidate]:
    effective = resolve_policy(policy or VideoRoutePolicy(), task_policy)
    # Check identities even for inactive entries; typos never silently disappear.
    for c in candidates:
        model_key(c)
    if effective.mode == RouteMode.AUTO:
        return candidates
    return [c for key in effective.sequence() for c in candidates if model_key(c) == key]


def choose(r: Requirements, candidates: list[Candidate], *, now: datetime | None = None,
           trial: bool = True, policy: VideoRoutePolicy | None = None,
           task_policy: VideoRoutePolicy | None = None, dry_run: bool = False) -> dict[str, Any]:
    if len({c.candidate_id for c in candidates}) != len(candidates):
        raise ValueError('DUPLICATE_CANDIDATE')
    # Invalid shared references/script fail before ordering; no preference can repair them.
    candidates = [Candidate.model_validate(c.model_dump()) for c in candidates]
    candidates = _policy_candidates(candidates, policy, task_policy)
    results = [qualify(r, c, now=now, trial=trial) for c in candidates]
    return _select_qualified(candidates, results, policy=policy, task_policy=task_policy, dry_run=dry_run)


def verify_policy_resolution(resolution: dict[str, Any], c: Candidate,
                             result: dict[str, Any], *, dry_run: bool) -> None:
    configured = VideoRoutePolicy.model_validate(resolution['configured_policy'])
    effective = VideoRoutePolicy.model_validate(resolution['effective_policy'])
    if effective.source != 'TASK_OVERRIDE' and resolve_policy(configured) != effective:
        raise ValueError('POLICY_SOURCE_MISMATCH')
    if (resolution['policy_fingerprint'] != sha256_canonical(effective.model_dump(mode='json'))
            or resolution['source'] != effective.source
            or resolution['selected_model'] != model_key(c)
            or resolution['selected_candidate'] != c.candidate_id
            or resolution['selected_candidate_fingerprint'] != sha256_canonical(c.model_dump(mode='json'))
            or effective.mode != RouteMode.AUTO and model_key(c) not in effective.sequence()):
        raise ValueError('POLICY_SELECTION_MISMATCH')
    accepted = [a for a in resolution['attempts'] if a['accepted']]
    if (len(accepted) != 1 or accepted[0].get('candidate_id') != c.candidate_id
            or accepted[0].get('qualification_fingerprint') != sha256_canonical(result)):
        raise ValueError('POLICY_QUALIFICATION_CHANGED')
    if resolution['dry_run_only'] and not dry_run:
        raise ValueError('DRY_RUN_POLICY_CANNOT_AUTHORIZE_PRODUCTION')


def seal_decision(r: Requirements, c: Candidate, request: dict[str, Any], *, stage_id: str,
                  rationale: str, comparisons: list[dict[str, Any]], fallback: str,
                  host_adapter: dict[str, Any] | None = None,
                  now: datetime | None = None, dry_run: bool = False,
                  production_route: ProductionRoute | None = None,
                  policy_resolution: dict[str, Any] | None = None) -> dict[str, Any]:
    r = Requirements.model_validate(r.model_dump())
    c = Candidate.model_validate(c.model_dump())
    result = qualify(r, c, now=now)
    permitted_offline = dry_run and set(result['exclusions']) <= {'COST_UNRESOLVED_OR_EXPIRED'}
    if (not result['eligible'] and not permitted_offline) or not rationale.strip() or not fallback.strip():
        raise ValueError('INELIGIBLE_OR_UNEXPLAINED_DECISION')
    resolution = policy_resolution or choose(r, [c], now=now, dry_run=dry_run)['route_policy_resolution']
    verify_policy_resolution(resolution, c, result, dry_run=dry_run)
    from copy import deepcopy
    material = {'route_policy_resolution': deepcopy(resolution), 'schema': 'video-decision-v1', 'stage_id': stage_id,
                'spec': {**r.model_dump(mode='json'), 'shot_id': r.target_id},
                'requirements': r.model_dump(mode='json'), 'candidate': c.model_dump(mode='json'),
                'request': request, 'request_fingerprint': sha256_canonical(request),
                'rationale': rationale, 'comparisons': comparisons, 'fallback': fallback,
                'qualification': result['qualification']}
    if dry_run:
        material['dry_run_only'] = True
        material['submission_allowed'] = False
    if host_adapter is not None:
        material['host_adapter'] = host_adapter
    if production_route is not None:
        route = ProductionRoute.model_validate(production_route.model_dump())
        execution = require_execution(route.execution, model_key(c))
        if (route.stage_id != stage_id or route.work_id != r.work_id or r.target_id not in route.video_targets
                or not same_execution_candidate(route.candidate, c)):
            raise ValueError('EXECUTION_ROUTE_MISMATCH: decision scope or candidate')
        material.update(production_route=route.model_dump(mode='json'),
                        route_fingerprint=sha256_canonical(route.model_dump(mode='json')),
                        execution=execution.model_dump(mode='json'),
                        execution_fingerprint=sha256_canonical(execution.model_dump(mode='json')))
    elif r.frozen_creative.get('creative_schema') == 'cinematic-shot-v1' and not dry_run:
        raise ValueError('MCP_CAPABILITY_UNAVAILABLE: production route required for sealing')
    if r.frozen_creative.get('creative_schema') == 'cinematic-shot-v1':
        if host_adapter is None:
            raise ValueError('INSPECTED_HOST_ADAPTER_REQUIRED')
        if execution_sealer is None:
            raise ValueError('HOST_EXECUTION_SEALER_REQUIRED')
        material['execution_contract'] = execution_sealer(r,c,request,host_adapter)
    return {**material, 'fingerprint': sha256_canonical(material)}


def verify_decision(d: dict[str, Any], *, now: datetime | None = None, allow_dry_run: bool = False) -> None:
    if d['fingerprint'] != sha256_canonical({k: v for k, v in d.items() if k != 'fingerprint'}):
        raise ValueError('DECISION_CHANGED')
    r = Requirements.model_validate(d['requirements'])
    # Preserve serialized legacy defaults: parsing new optional fields must not
    # rewrite a historical seal before its normal freshness checks.
    if d['spec'] != {**d['requirements'], 'shot_id': r.target_id}:
        raise ValueError('DECISION_SPEC_REQUIREMENTS_MISMATCH')
    c = Candidate.model_validate(d['candidate'])
    result = qualify(r,c,now=now)
    if d.get('dry_run_only') and not allow_dry_run:
        raise ValueError('DRY_RUN_REQUEST_CANNOT_BE_RESERVED_OR_SUBMITTED')
    if not result['eligible'] and not (allow_dry_run and d.get('dry_run_only') and set(result['exclusions']) <= {'COST_UNRESOLVED_OR_EXPIRED'}):
        raise ValueError('DECISION_EXPIRED_OR_INELIGIBLE')
    if d.get('route_policy_resolution'):
        verify_policy_resolution(d['route_policy_resolution'], c, result, dry_run=bool(d.get('dry_run_only')))
    if d['request_fingerprint'] != sha256_canonical(d['request']):
        raise ValueError('REQUEST_CHANGED')
    if d.get('production_route') is not None:
        route = ProductionRoute.model_validate(d['production_route'])
        execution = require_execution(route.execution, model_key(c)).model_dump(mode='json')
        if (d.get('route_fingerprint') != sha256_canonical(d['production_route'])
                or d.get('execution') != execution
                or d.get('execution_fingerprint') != sha256_canonical(execution)
                or not same_execution_candidate(route.candidate, c) or route.work_id != r.work_id
                or route.stage_id != d['stage_id'] or r.target_id not in route.video_targets):
            raise ValueError('EXECUTION_ROUTE_MISMATCH: sealed route')
    elif r.frozen_creative.get('creative_schema') == 'cinematic-shot-v1' and not (allow_dry_run and d.get('dry_run_only')):
        raise ValueError('MCP_CAPABILITY_UNAVAILABLE: legacy cinematic seal must be resealed')


class PlannedInput(Record):
    """An input duty before bytes exist; never a placeholder Media identity."""
    target_id: Text
    purpose: Text
    role: Literal['FIRST_FRAME', 'LAST_FRAME', 'REFERENCE']
    for_targets: tuple[Text, ...] = Field(min_length=1)
    preparation: Literal['REUSE', 'NEW', 'CONVERT']
    specification: Text
    rationale: Text
    cost_key: Text
    source_media_id: Text | None = None
    roles_by_target: dict[Text, Literal['FIRST_FRAME', 'LAST_FRAME', 'REFERENCE']] = Field(default_factory=dict)
    requires_pass_targets: tuple[Text, ...] = ()
    active: bool = True


def same_execution_candidate(planned: Candidate, actual: Candidate) -> bool:
    # Planning prices the whole stage; a materialized decision prices this call.
    return all(getattr(planned, key) == getattr(actual, key) for key in (
        'candidate_id', 'model', 'variant', 'mode', 'template', 'graph_hash',
        'adapter_fingerprint', 'parameters', 'capability'))


class ContinuationAuthorization(Record):
    """Explicit one-candidate continuation of the same Work-owned stage."""
    authorization_ref: Text
    reason: Text
    target_id: Text
    baseline_stage_fingerprint: Hash
    baseline_attempts_fingerprint: Hash
    baseline_attempt_count: int = Field(ge=1)
    max_new_video_attempts: Literal[1] = 1
    max_quoted_credits: float = Field(gt=0, allow_inf_nan=False)


class ProductionRoute(Record):
    route_id: Text
    work_id: Text
    stage_id: Text
    creative_fingerprint: Hash
    video_targets: tuple[Text, ...] = Field(min_length=1)
    # Legacy stages retain their original limits; a newly authorized stage may
    # use a monetary envelope without inheriting another story's call counts.
    max_image_attempts: int | None = Field(default=6, gt=0)
    max_video_attempts: int | None = Field(default=2, gt=0)
    requirements: dict[Text, Any] = Field(min_length=1)
    candidate: Candidate
    # Optional only for historical records; new cinematic production requires it.
    execution: ExecutionRoute | None = None
    continuation: ContinuationAuthorization | None = None
    inputs: tuple[PlannedInput, ...] = ()
    quality_thresholds: dict[Text, Text] = Field(min_length=1)
    stops: tuple[Text, ...] = Field(min_length=1)
    fallback: Text
    # The small-trial Host accepts a single verified generation per request only.
    generations_per_video_request: int = Field(ge=1)
    generation_count_evidence: Evidence
    video_request_credits: float = Field(gt=0, allow_inf_nan=False)


def qualify_route(route: ProductionRoute, *, now: datetime | None = None) -> dict[str, Any]:
    """Jointly qualify capability, planned inputs and all preparation costs.

    Existing image compatibility is a priced planning choice, not a model veto.
    The later sealed video decision still requires actual verified input Media.
    """
    route = ProductionRoute.model_validate(route.model_dump())
    c = route.candidate
    r = route.requirements
    now = now or datetime.now(timezone.utc)
    reasons: list[str] = []
    directions: dict[str, Any] = {}
    if route.continuation and (route.video_targets != (route.continuation.target_id,)
                              or r.get('creative_schema') != 'cinematic-shot-v1'):
        raise ValueError('CONTINUATION_REQUIRES_ONE_FROZEN_TARGET')
    if r.get('creative_schema') == 'cinematic-shot-v1' or r.get('cinematic_directions'):
        require_execution(route.execution, model_key(c))
        from drama_plugin.visual.cinematic import verify_frozen
        raw_directions = r.get('cinematic_directions', {})
        if set(raw_directions) != set(route.video_targets):
            raise ValueError('COMPLETE_FROZEN_CINEMATIC_DIRECTIONS_REQUIRED')
        for target, raw in raw_directions.items():
            spec = verify_frozen(raw)
            if (spec.work_id != route.work_id or spec.shot_id != r.get('shots', {}).get(target)
                    or spec.duration_seconds != r['duration_seconds']):
                raise ValueError('ROUTE_CINEMATIC_SCOPE_OR_DURATION_CHANGED')
            directions[target] = direction_quality(raw, c, r['shot_type'])
            reasons.extend('DIRECTOR_REQUIREMENT_FAILED:' + key for key in directions[target]['failed'])
    if route.generations_per_video_request != 1 or not route.generation_count_evidence.current(now):
        reasons.append('UNVERIFIED_OR_MULTI_GENERATION_REQUEST')
    if len(set(route.video_targets)) != len(route.video_targets):
        reasons.append('DUPLICATE_VIDEO_TARGET')
    for layer in ('official', 'interface', 'template', 'project'):
        evidence = c.layers.get(layer)
        if evidence is None or not evidence.current(now):
            reasons.append('UNVERIFIED_OR_EXPIRED:' + layer)
    controls = set(r['controls'])
    if not controls <= set(c.controls) or not any(controls <= set(x) for x in c.combinations):
        reasons.append('CREATIVE_CONTROL_COMBINATION_UNSUPPORTED')
    if (r['duration_seconds'] not in c.durations or r['aspect_ratio'] not in c.aspect_ratios
            or r['sound'] not in c.sounds or (r.get('language') and r['language'] not in c.languages)):
        reasons.append('CREATIVE_DURATION_ASPECT_OR_SOUND_UNSUPPORTED')
    if len({i.target_id for i in route.inputs}) != len(route.inputs):
        reasons.append('DUPLICATE_INPUT_DUTY')
    for target in route.video_targets:
        roles = [i.roles_by_target.get(target, i.role) for i in route.inputs if i.active and target in i.for_targets]
        if c.mode == 'TEXT_TO_VIDEO' and roles:
            reasons.append('TEXT_TO_VIDEO_REQUIRES_ZERO_INPUTS:' + target)
        if c.mode == 'START_END' and sorted(roles) != ['FIRST_FRAME', 'LAST_FRAME']:
            reasons.append('PLANNED_ENDPOINT_PAIR_REQUIRED:' + target)
        if c.mode == 'SINGLE_IMAGE' and roles not in [['FIRST_FRAME'], ['REFERENCE']]:
            reasons.append('PLANNED_SINGLE_INPUT_REQUIRED:' + target)
        if any(role not in c.controls for role in roles):
            reasons.append('INPUT_SEMANTICS_UNSUPPORTED:' + target)
    for i in route.inputs:
        if not set(i.requires_pass_targets) <= ({x.target_id for x in route.inputs} | set(route.video_targets)) or i.target_id in i.requires_pass_targets:
            reasons.append('INVALID_INPUT_REVIEW_DEPENDENCY')
        if not set(i.roles_by_target) <= set(i.for_targets):
            reasons.append('ROLE_MAP_OUTSIDE_CONSUMERS')
        if not set(i.for_targets) <= set(route.video_targets):
            reasons.append('UNPLANNED_VIDEO_TARGET')
        if i.preparation == 'REUSE' and not i.source_media_id:
            reasons.append('REUSE_SOURCE_REQUIRED')
    required_costs = {i.cost_key for i in route.inputs} | {'video', 'audio', 'references', 'addons', 'correction'}
    calls = 1 if route.continuation else max(2, len(route.video_targets))
    if (c.cost.components.get('video') or 0) < calls * route.video_request_credits:
        reasons.append('SHARED_TWO_REQUEST_VIDEO_ENVELOPE_MISSING')
    if not required_costs <= set(c.cost.components) or c.cost.uncertainty or not c.cost.evidence.current(now) or c.cost.total() is None:
        reasons.append('COMPLETE_ROUTE_COST_UNRESOLVED')
    if any(i.preparation == 'REUSE' and c.cost.components.get(i.cost_key) != 0 for i in route.inputs):
        reasons.append('REUSE_INCREMENTAL_COST_MUST_BE_ZERO')
    q = c.quality
    if q.status == 'UNKNOWN' and (q.samples or q.evidence or q.dimensions):
        reasons.append('UNKNOWN_QUALITY_CANNOT_CLAIM_SAMPLES')
    if q.status != 'UNKNOWN' and (not q.samples or not q.evidence or not q.task_types):
        reasons.append('QUALITY_CLAIM_WITHOUT_EVIDENCE')
    if q.status == 'FAIL' and r['shot_type'] in q.task_types:
        reasons.append('APPLICABLE_QUALITY_FAILURE')
    passed = (q.status == 'PASS' and r['shot_type'] in q.task_types
              and all(q.dimensions.get(k) == 'PASS' for k in route.quality_thresholds))
    if directions:
        passed = passed and all(d['proven'] for d in directions.values())
    return {'route_id': route.route_id, 'eligible': not reasons, 'exclusions': reasons,
            'qualification': 'QUALIFIED' if passed else 'LIMITED_TRIAL',
            'incremental_credits': c.cost.total(), 'quality_thresholds': route.quality_thresholds,
            'input_compatibility': 'accounted in preparation, costs and risks',
            **({'cinematic_directions': directions} if directions else {})}


def route_input_gate(route: ProductionRoute, target_id: str, purpose: str) -> PlannedInput:
    result = qualify_route(route)
    if not result['eligible']:
        raise ValueError('ROUTE_NOT_EXECUTABLE:' + ','.join(result['exclusions']))
    matches = [i for i in route.inputs if i.target_id == target_id and i.purpose == purpose]
    if len(matches) != 1 or not matches[0].active or matches[0].preparation == 'REUSE':
        raise ValueError('PAID_IMAGE_NOT_A_NECESSARY_ROUTE_INPUT')
    return matches[0]


def choose_routes(routes: list[ProductionRoute], *, policy: VideoRoutePolicy | None = None,
                  task_policy: VideoRoutePolicy | None = None, now: datetime | None = None) -> dict[str, Any]:
    """Planning uses the existing planned-input qualifier, never fake Media."""
    allowed = _policy_candidates([r.candidate for r in routes], policy, task_policy)
    routes = [r for c in allowed for r in routes if r.candidate == c]
    results = [{**qualify_route(route, now=now), 'candidate_id': route.candidate.candidate_id}
               for route in routes]
    return _select_qualified([r.candidate for r in routes], results, policy=policy, task_policy=task_policy)
