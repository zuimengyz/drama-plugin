"""Provider-neutral, evidence-bound video qualification; no generation or ranking claims."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import Field

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.visual.frame_request import Hash, Record, Text


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


class Requirements(Record):
    work_id: Text
    scene_id: Text
    shot_id: Text
    target_id: Text
    shot_type: Text
    source_fingerprint: Hash
    mode: Literal['SINGLE_IMAGE', 'START_END']
    controls: tuple[Text, ...] = Field(min_length=1)
    duration_seconds: int = Field(gt=0)
    aspect_ratio: Text
    sound: Text
    language: Text | None = None
    frozen_creative: dict[str, Any] = Field(min_length=1)
    inputs: tuple[VideoInput, ...] = Field(min_length=1, max_length=2)
    required: tuple[Text, ...] = Field(min_length=1)
    forbidden: tuple[Text, ...] = Field(min_length=1)


def validate_requirements(r: Requirements) -> None:
    roles = [i.role for i in r.inputs]
    if r.mode == 'SINGLE_IMAGE' and roles not in [['FIRST_FRAME'], ['REFERENCE']]:
        raise ValueError('SINGLE_IMAGE_REQUIRES_EXACTLY_ONE_INPUT')
    if r.mode == 'START_END' and roles != ['FIRST_FRAME', 'LAST_FRAME']:
        raise ValueError('START_END_REQUIRES_ORDERED_PAIR')
    if any(i.target_id != r.target_id for i in r.inputs):
        raise ValueError('CROSS_TARGET_INPUT')
    if len({i.media_id for i in r.inputs}) != len(r.inputs):
        raise ValueError('DUPLICATE_ENDPOINT_MEDIA')
    needed = {'FIRST_FRAME'} if roles == ['FIRST_FRAME'] else {'REFERENCE'} if roles == ['REFERENCE'] else {'FIRST_FRAME', 'LAST_FRAME'}
    if not needed <= set(r.controls):
        raise ValueError('INPUT_ROLE_CONTROL_MISMATCH')


class Cost(Record):
    # Each component is incremental; reused assets are explicitly zero.
    components: dict[Text, float] = Field(min_length=1)
    unit: Literal['credits'] = 'credits'
    evidence: Evidence
    uncertainty: tuple[Text, ...] = ()

    def total(self) -> float:
        import math
        if any(not math.isfinite(v) or v < 0 for v in self.components.values()):
            raise ValueError('INVALID_COST')
        return sum(self.components.values())


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
    mode: Literal['SINGLE_IMAGE', 'START_END']
    template: Text
    graph_hash: Hash
    adapter_fingerprint: Hash
    parameters: dict[str, Any]
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
    if q.status == 'FAIL' and r.shot_type in q.task_types:
        reasons.append('PROJECT_QUALITY_FAILED')
    if not trial and not scoped_pass:
        reasons.append('LIMITED_TRIAL_ONLY')
    if not c.cost.evidence.current(now) or c.cost.uncertainty:
        reasons.append('COST_UNRESOLVED_OR_EXPIRED')
    total = c.cost.total()
    return {'candidate_id': c.candidate_id, 'eligible': not reasons, 'exclusions': reasons,
            'qualification': 'QUALIFIED' if scoped_pass else 'LIMITED_TRIAL',
            'quality': q.model_dump(mode='json'), 'incremental_credits': total,
            'fit_concerns': list(c.fit_concerns)}


def choose(r: Requirements, candidates: list[Candidate], *, now: datetime | None = None,
           trial: bool = True) -> dict[str, Any]:
    if len({c.candidate_id for c in candidates}) != len(candidates):
        raise ValueError('DUPLICATE_CANDIDATE')
    results = [qualify(r, c, now=now, trial=trial) for c in candidates]
    eligible = [v for v in results if v['eligible']]
    eligible.sort(key=lambda v: (len(v['fit_concerns']), v['qualification'] != 'QUALIFIED',
                                 v['incremental_credits'], v['candidate_id']))
    return {'selected': eligible[0]['candidate_id'] if eligible else None, 'candidates': results}


def seal_decision(r: Requirements, c: Candidate, request: dict[str, Any], *, stage_id: str,
                  rationale: str, comparisons: list[dict[str, Any]], fallback: str,
                  host_adapter: dict[str, Any] | None = None,
                  now: datetime | None = None) -> dict[str, Any]:
    result = qualify(r, c, now=now)
    if not result['eligible'] or not rationale.strip() or not fallback.strip():
        raise ValueError('INELIGIBLE_OR_UNEXPLAINED_DECISION')
    material = {'schema': 'video-decision-v1', 'stage_id': stage_id,
                'spec': {**r.model_dump(mode='json'), 'shot_id': r.target_id},
                'requirements': r.model_dump(mode='json'), 'candidate': c.model_dump(mode='json'),
                'request': request, 'request_fingerprint': sha256_canonical(request),
                'rationale': rationale, 'comparisons': comparisons, 'fallback': fallback,
                'qualification': result['qualification']}
    if host_adapter is not None:
        material['host_adapter'] = host_adapter
    return {**material, 'fingerprint': sha256_canonical(material)}


def verify_decision(d: dict[str, Any], *, now: datetime | None = None) -> None:
    if d['fingerprint'] != sha256_canonical({k: v for k, v in d.items() if k != 'fingerprint'}):
        raise ValueError('DECISION_CHANGED')
    r = Requirements.model_validate(d['requirements'])
    if d['spec'] != {**r.model_dump(mode='json'), 'shot_id': r.target_id}:
        raise ValueError('DECISION_SPEC_REQUIREMENTS_MISMATCH')
    c = Candidate.model_validate(d['candidate'])
    if not qualify(r, c, now=now)['eligible']:
        raise ValueError('DECISION_EXPIRED_OR_INELIGIBLE')
    if d['request_fingerprint'] != sha256_canonical(d['request']):
        raise ValueError('REQUEST_CHANGED')
