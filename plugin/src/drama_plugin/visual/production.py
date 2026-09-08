"""Durable, one-at-a-time Host submission gate for image and video production.

Core reservations are offline; the explicit persist command calls the configured Media adapter.
Reserve before invoking the returned provider item; record the
job outcome, then record evidence-based review. An uncertain submission remains
reserved across process restarts and cannot silently spend again.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Callable, Literal

from pydantic import Field

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.visual.frame_request import Hash, Record, Text, verify_compiled

CATEGORIES = Literal["IDENTITY", "COSTUME", "BLOCKING", "PROP_STRUCTURE", "PROP_STATE",
                     "SCENE", "ANATOMY", "MODERN_ARTIFACT", "CROP", "COSMETIC",
                     "ACTION", "CAMERA", "DIALOGUE", "SPEAKER", "SOUND", "CONTINUITY", "ENDPOINTS"]
HARD = {"IDENTITY", "COSTUME", "BLOCKING", "PROP_STRUCTURE", "PROP_STATE", "ANATOMY",
        "ACTION", "DIALOGUE", "SPEAKER", "SOUND", "CONTINUITY", "ENDPOINTS"}


video_verifier: Callable[[dict[str, Any]], None] | None = None


def verify_visual(frame: dict[str, Any]) -> None:
    if frame.get('schema') == 'video-decision-v1':
        from drama_plugin.visual.video_selection import verify_decision
        verify_decision(frame)
        if video_verifier is None:
            raise ValueError('HOST_VIDEO_VERIFIER_REQUIRED')
        video_verifier(frame)
    else:
        verify_compiled(frame)


def new_stage(*, stage_id: str, authorization_ref: str, budget_credits: float,
              frames: list[dict[str, Any]], protected_targets: list[str]) -> dict[str, Any]:
    if not stage_id.strip() or not authorization_ref.strip() or not math.isfinite(budget_credits) or budget_credits <= 0:
        raise ValueError('EXPLICIT_STAGE_BUDGET_REQUIRED')
    if not frames or len({f['spec']['shot_id'] for f in frames}) != len(frames):
        raise ValueError('EMPTY_OR_DUPLICATE_STAGE_TARGET')
    for f in frames:
        verify_visual(f)
        if f.get('schema') == 'video-decision-v1' and f['stage_id'] != stage_id:
            raise ValueError('DECISION_BUDGET_SCOPE_MISMATCH')
        if f['spec']['shot_id'] in protected_targets:
            raise ValueError('PROTECTED_TARGET')
    images = [f for f in frames if f.get('schema') != 'video-decision-v1']
    videos = [f for f in frames if f.get('schema') == 'video-decision-v1']
    if len(videos) > 1:
        raise ValueError('STAGE_ONE_FORMAL_VIDEO_TARGET')
    if len(images) > 3:
        raise ValueError('STAGE_IMAGE_LIMIT')
    if images:
        new_campaign(images)  # Preserve V2-05 identity/version/risk qualification.
    return {'schema': 'visual-campaign-v1', 'frames': {f['spec']['shot_id']: f for f in frames},
            'plan_fingerprint': sha256_canonical(frames), 'pilots': [f['spec']['shot_id'] for f in frames],
            'attempts': [], 'pause': None, 'remediations': [],
            'stage': {'id': stage_id, 'authorization_ref': authorization_ref,
                      'budget_credits': budget_credits, 'protected_targets': protected_targets,
                      'video_target': videos[0]['spec']['shot_id'] if videos else None}}


def _fresh(observation: dict[str, Any]) -> None:
    from datetime import datetime, timezone
    from drama_plugin.visual.video_selection import Evidence
    if not Evidence.model_validate(observation['evidence']).current(datetime.now(timezone.utc)):
        raise ValueError('LIVE_PRICE_OR_BALANCE_EXPIRED')


def exposure(state: dict[str, Any]) -> float:
    return float(sum(a['credits'] if a['credits'] is not None else a['reserved_credits'] for a in state['attempts']))


def _stage_gate(state: dict[str, Any], frame: dict[str, Any], request: dict[str, Any],
                quote: dict[str, Any] | None, balance: dict[str, Any] | None) -> float:
    if quote is None or balance is None:
        raise ValueError('FRESH_QUOTE_AND_BALANCE_REQUIRED')
    _fresh(quote); _fresh(balance)
    from datetime import datetime
    observed = datetime.fromisoformat(balance['evidence']['checked_at'])
    if any(a.get('billing_reconciled_at') and observed <= datetime.fromisoformat(a['billing_reconciled_at']) for a in state['attempts']):
        raise ValueError('BALANCE_MUST_BE_REFRESHED_AFTER_SETTLEMENT')
    if quote['request_fingerprint'] != sha256_canonical(request) or quote.get('uncertainty'):
        raise ValueError('REQUEST_QUOTE_MISMATCH_OR_UNKNOWN_CHARGES')
    if quote.get('unit') != 'credits' or balance.get('unit') != 'credits':
        raise ValueError('BUDGET_UNIT_MISMATCH')
    amount = quote['conservative_credits']; available = balance['available_credits']; margin = balance['margin_credits']
    if any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in [amount, available, margin]) or min(amount, available) < 0 or amount == 0 or margin <= 0:
        raise ValueError('INVALID_QUOTE_OR_BALANCE')
    unsettled = sum(a['reserved_credits'] for a in state['attempts'] if a['credits'] is None)
    if exposure(state) + amount > state['stage']['budget_credits'] or unsettled + amount + margin > available:
        raise ValueError('STAGE_BUDGET_OR_BALANCE_EXCEEDED')
    video = frame.get('schema') == 'video-decision-v1'
    if video:
        # Quote may include margin, but cannot undercut the recorded paid path.
        costs = frame['candidate']['cost']['components']
        minimum = sum(v for k, v in costs.items() if k not in {'correction', 'new_inputs', 'existing_input'})
        if amount < minimum:
            raise ValueError('QUOTE_BELOW_SELECTED_PATH_COST')
    if video and frame['stage_id'] != state['stage']['id']:
        raise ValueError('DECISION_BUDGET_SCOPE_MISMATCH')
    if video and sum(a.get('media_kind') == 'VIDEO' for a in state['attempts']) >= 2:
        raise ValueError('STAGE_VIDEO_ATTEMPTS_EXHAUSTED')
    if not video:
        initials = {a['shot_id'] for a in state['attempts'] if a.get('media_kind') == 'IMAGE'}
        if frame['spec']['shot_id'] not in initials and len(initials) >= 3:
            raise ValueError('STAGE_IMAGE_ATTEMPTS_EXHAUSTED')
    if frame['spec']['shot_id'] in state['stage']['protected_targets']:
        raise ValueError('PROTECTED_TARGET')
    return float(amount)


class Finding(Record):
    category: CATEGORIES
    severity: Literal["MAJOR", "MINOR"]
    evidence: Text
    remedy: Literal["REGENERATE", "POSTPROCESS", "ACCEPT"]


class Review(Record):
    attempt_id: Hash
    output_hash: Hash
    reviewer: Text
    evidence: Text
    # Applicable requirements must be inspected, including crop-safe composition.
    checks: dict[str, Literal["PASS", "FAIL", "UNKNOWN"]] = Field(min_length=1)
    findings: tuple[Finding, ...] = ()


def _review_status(review: Review) -> str:
    for f in review.findings:
        if f.category in HARD and (f.severity != "MAJOR" or f.remedy != "REGENERATE"):
            raise ValueError("SEMANTIC_FAILURE_CANNOT_BE_DOWNGRADED")
        if f.severity == "MAJOR" and f.remedy != "REGENERATE":
            raise ValueError("MAJOR_FAILURE_REQUIRES_REVISION")
        if f.severity == "MINOR" and f.remedy == "REGENERATE":
            raise ValueError("MINOR_FAILURE_USE_ACCEPT_OR_POSTPROCESS")
    if "UNKNOWN" in review.checks.values():
        raise ValueError("REVIEW_INCOMPLETE")
    failed = "FAIL" in review.checks.values()
    major = any(f.severity == "MAJOR" for f in review.findings)
    if failed != major:
        raise ValueError("CHECKS_AND_FINDINGS_DISAGREE")
    return "FAIL" if major else "PASS_WITH_NOTES" if review.findings else "PASS"


def new_campaign(frames: list[dict[str, Any]]) -> dict[str, Any]:
    if not frames:
        raise ValueError("EMPTY_CAMPAIGN")
    for f in frames:
        verify_compiled(f)
    ids = [f['spec']['shot_id'] for f in frames]
    if len(ids) != len(set(ids)):
        raise ValueError("DUPLICATE_SHOT")
    # An entity/state has one authoritative version for this campaign. State
    # transitions may use another explicitly locked version, never 'latest'.
    versions: dict[tuple[str, str], tuple[str, ...]] = {}
    identities: dict[str, tuple[str, str]] = {}
    for frame in frames:
        for r in frame['spec']['references']:
            key = (r['entity_key'], r['state'])
            value = (r['asset_id'], r['media_id'], r['version'], r['content_hash'])
            if key in versions and versions[key] != value:
                raise ValueError("CROSS_SHOT_REFERENCE_VERSION_DRIFT")
            versions[key] = value
        for a in frame['spec']['actors']:
            identity = (a['identity'], a['costume'])
            if a['entity_key'] in identities and identities[a['entity_key']] != identity:
                raise ValueError("CROSS_SHOT_IDENTITY_OR_COSTUME_DRIFT")
            identities[a['entity_key']] = identity
    # Greedy coverage of risk, model and reference-state cohorts. Actual planned
    # shots are pilots; later novel cohorts cannot ride on an easy dialogue PASS.
    def cohort(f: dict[str, Any]) -> set[str]:
        policy = sha256_canonical({"template": f['template'], "refs": [
            {k: r[k] for k in ('entity_key', 'media_id', 'content_hash', 'state')}
            for r in f['spec']['references']]})
        return {policy + ':' + risk for risk in f['risks']}
    remaining = set().union(*(cohort(f) for f in frames))
    pilots: list[str] = []
    while remaining:
        chosen = max(frames, key=lambda f: len(cohort(f) & remaining))
        pilots.append(chosen['spec']['shot_id'])
        remaining -= cohort(chosen)
    for sid in ids:
        if len(pilots) >= min(3, len(ids)):
            break
        if sid not in pilots:
            pilots.append(sid)
    if len(pilots) > 3:
        raise ValueError("SPLIT_CAMPAIGN_BY_RISK_OR_REFERENCE_STATE: more than 3 representative shots needed")
    return {"schema": "visual-campaign-v1", "frames": {f['spec']['shot_id']: f for f in frames},
            "plan_fingerprint": sha256_canonical(frames), "pilots": pilots,
            "attempts": [], "pause": None, "remediations": []}


def check_campaign(state: dict[str, Any], *, verify_inputs: bool = False) -> None:
    frames = list(state['frames'].values())
    if state['plan_fingerprint'] != sha256_canonical(frames):
        raise ValueError("CAMPAIGN_PLAN_CHANGED")
    for frame in frames:
        if frame['fingerprint'] != sha256_canonical({k: v for k, v in frame.items() if k != 'fingerprint'}):
            raise ValueError("COMPILED_FRAME_CHANGED")
        if verify_inputs:
            verify_visual(frame)


def reserve(state: dict[str, Any], shot_id: str, *, quote: dict[str, Any] | None = None,
            balance: dict[str, Any] | None = None) -> dict[str, Any]:
    check_campaign(state, verify_inputs=True)
    if state['pause']:
        raise ValueError("CAMPAIGN_PAUSED:" + state['pause'])
    if any(a['status'] in {'RESERVED', 'UNKNOWN', 'COMPLETED'} and 'review' not in a for a in state['attempts']):
        raise ValueError("PREVIOUS_ATTEMPT_NEEDS_OUTCOME_OR_REVIEW")
    frame = state['frames'][shot_id]
    prior = [a for a in state['attempts'] if a['shot_id'] == shot_id]
    if any(a.get('review_status', '').startswith('PASS') for a in prior):
        raise ValueError("DO_NOT_REGENERATE_PASSED_SHOT")
    if len(prior) >= 2:
        raise ValueError("TARGETED_REVISION_BUDGET_EXHAUSTED")
    if prior and prior[-1].get('review_status') != 'FAIL':
        raise ValueError("TECHNICAL_FAILURE_REQUIRES_OUTCOME_RECOVERY_NOT_VISUAL_REVISION")
    passed = {a['shot_id'] for a in state['attempts'] if a.get('review_status', '').startswith('PASS')}
    if shot_id not in state['pilots'] and not set(state['pilots']) <= passed:
        raise ValueError("REPRESENTATIVE_REVIEW_REQUIRED")
    item = deepcopy(frame['request'])
    is_video = frame.get('schema') == 'video-decision-v1'
    if is_video and 'stage' not in state:
        raise ValueError('VIDEO_REQUIRES_SHARED_STAGE_BUDGET')
    if prior and is_video and prior[-1]['frame_fingerprint'] == frame['fingerprint']:
        raise ValueError('VIDEO_REVISION_REQUIRES_REQUALIFIED_DECISION')
    if prior and not is_video:
        t = frame['template']
        correction = '; '.join(f['evidence'] for f in prior[-1]['review']['findings'] if f['severity'] == 'MAJOR')
        item['input_overrides'][t['prompt_node']][t['prompt_key']] += '\nTARGETED CORRECTION: ' + correction
        item['description'] = shot_id + '-revision'
    reserved_credits = _stage_gate(state, frame, item, quote, balance) if 'stage' in state else None
    attempt_id = sha256_canonical({'plan': state['plan_fingerprint'], 'shot': shot_id,
                                   'attempt': len(prior) + 1, 'request': item,
                                   'remediations': state['remediations']})
    attempt = {'attempt_id': attempt_id, 'shot_id': shot_id, 'ordinal': len(prior) + 1,
               'frame_fingerprint': frame['fingerprint'], 'request': item,
               'request_fingerprint': sha256_canonical(item), 'status': 'RESERVED',
               'job_id': None, 'credits': None, 'billing_event_id': None}
    if 'stage' in state:
        attempt.update(reserved_credits=reserved_credits, quote=deepcopy(quote), balance=deepcopy(balance),
                       media_kind='VIDEO' if is_video else 'IMAGE', stage_id=state['stage']['id'],
                       technical_status='PENDING', content_status='PENDING_REVIEW', user_adoption='PENDING', copies=[], persistence_status='PERSISTENCE_PENDING', delivery_status='PENDING')
    state['attempts'].append(attempt)
    return attempt


def record_result(state: dict[str, Any], *, attempt_id: str, status: str, job_id: str | None,
                  output_hash: str | None = None, evidence: str, credits: float | None = None,
                  billing_event_id: str | None = None) -> None:
    attempt = next(a for a in state['attempts'] if a['attempt_id'] == attempt_id)
    if attempt['status'] not in {'RESERVED', 'UNKNOWN'}:
        raise ValueError("OUTCOME_ALREADY_RECORDED")
    if status not in {'COMPLETED', 'UNKNOWN', 'FAILED', 'NOT_CREATED'} or not evidence.strip():
        raise ValueError("INVALID_PROVIDER_OUTCOME")
    if status in {'COMPLETED', 'FAILED'} and not job_id:
        raise ValueError("JOB_ID_REQUIRED")
    if attempt['job_id'] and attempt['job_id'] != job_id:
        raise ValueError("RECOVERY_JOB_ID_CHANGED")
    if job_id and any(a is not attempt and a['job_id'] == job_id for a in state['attempts']):
        raise ValueError("JOB_ALREADY_BOUND")
    if status == 'COMPLETED':
        from pydantic import TypeAdapter
        TypeAdapter(Hash).validate_python(output_hash)
    if credits is not None and (not math.isfinite(credits) or credits < 0 or not billing_event_id or not job_id):
        raise ValueError("BILLING_EVENT_REQUIRED_FOR_CREDITS")
    if billing_event_id and any(a is not attempt and a['billing_event_id'] == billing_event_id for a in state['attempts']):
        raise ValueError("BILLING_EVENT_ALREADY_BOUND")
    attempt.update(status=status, job_id=job_id, output_hash=output_hash, provider_evidence=evidence,
                   credits=credits, billing_event_id=billing_event_id)
    if status in {'FAILED', 'NOT_CREATED'}:
        state['pause'] = 'PROVIDER_FAILURE_REQUIRES_RECOVERY'


def reconcile_billing(state: dict[str, Any], *, attempt_id: str, job_id: str,
                      credits: float, billing_event_id: str) -> None:
    attempt = next(a for a in state['attempts'] if a['attempt_id'] == attempt_id)
    if not job_id or attempt['job_id'] != job_id:
        raise ValueError('BILLING_JOB_MISMATCH')
    if not math.isfinite(credits) or credits < 0 or not billing_event_id.strip():
        raise ValueError('INVALID_BILLING_EVENT')
    if attempt['billing_event_id'] is not None:
        if attempt['billing_event_id'] == billing_event_id and attempt['credits'] == credits:
            return
        raise ValueError('BILLING_ALREADY_RECONCILED')
    if any(a['billing_event_id'] == billing_event_id for a in state['attempts']):
        raise ValueError('BILLING_EVENT_ALREADY_BOUND')
    from datetime import datetime, timezone
    attempt.update(credits=credits, billing_event_id=billing_event_id, billing_reconciled_at=datetime.now(timezone.utc).isoformat())


def record_review(state: dict[str, Any], review: Review) -> str:
    review = Review.model_validate(review.model_dump())
    attempt = next(a for a in state['attempts'] if a['attempt_id'] == review.attempt_id)
    if attempt['status'] != 'COMPLETED' or attempt['output_hash'] != review.output_hash:
        raise ValueError("REVIEW_OUTPUT_MISMATCH")
    if 'review' in attempt:
        raise ValueError("REVIEW_ALREADY_RECORDED")
    spec = state['frames'][attempt['shot_id']]['spec']
    required_checks = {'IDENTITY', 'COSTUME', 'BLOCKING', 'PROP_STRUCTURE', 'PROP_STATE',
                       'SCENE', 'ANATOMY', 'MODERN_ARTIFACT', 'CROP'}
    # An irrelevant dimension is explicitly PASS with rationale in evidence.
    required_checks |= {'required:' + x for x in spec['required']}
    required_checks |= {'forbidden:' + x for x in spec['forbidden']}
    if attempt.get('media_kind') == 'VIDEO':
        required_checks |= {'ACTION', 'CAMERA', 'DIALOGUE', 'SPEAKER', 'SOUND', 'CONTINUITY', 'ENDPOINTS'}
        if attempt['technical_status'] != 'PASS':
            raise ValueError('VIDEO_TECHNICAL_REVIEW_REQUIRED')
    if not required_checks <= set(review.checks):
        raise ValueError("REQUIRED_REVIEW_CHECKS_MISSING")
    result = _review_status(review)
    attempt.update(review=review.model_dump(mode='json'), review_status=result)
    if 'stage' in state:
        attempt['content_status'] = result
    since = state['remediations'][-1]['after_attempt'] if state['remediations'] else 0
    reviewed = [a for a in state['attempts'][since:] if 'review' in a]
    recent = reviewed[-3:]
    counts = Counter(f['category'] for a in recent for f in {
        f['category']: f for f in a['review']['findings'] if f['severity'] == 'MAJOR'}.values())
    if any(n >= 2 for n in counts.values()):
        state['pause'] = 'COMMON_FAILURE_REPLAN'
    if len(reviewed) >= 2 and all(a['review_status'] == 'FAIL' for a in reviewed[-2:]):
        state['pause'] = 'CONSECUTIVE_FAILURE_REPLAN'
    if result == 'FAIL' and attempt['ordinal'] == 2:
        state['pause'] = 'TARGETED_REVISION_FAILED'
    return result


def resume(state: dict[str, Any], *, reason: str) -> None:
    """A review-backed replan can release the breaker, never erase attempts.

The frozen plan remains authoritative; reference/model/Shot changes require a
separate, explicitly scoped campaign. Failed second attempts remain exhausted.
"""
    if not reason.strip() or state['pause'] not in {'COMMON_FAILURE_REPLAN', 'CONSECUTIVE_FAILURE_REPLAN'}:
        raise ValueError("REPLAN_EVIDENCE_REQUIRED_OR_NOT_RESUMABLE")
    failed = {a['shot_id'] for a in state['attempts'] if a.get('review_status') == 'FAIL'}
    if any(sum(a['shot_id'] == sid for a in state['attempts']) >= 2 for sid in failed):
        raise ValueError("TARGETED_REVISION_BUDGET_EXHAUSTED")
    if len(set(state['pilots']) | failed) > 3:
        raise ValueError("SPLIT_AND_REPLAN_REQUIRED")
    state['pilots'] = sorted(set(state['pilots']) | failed)
    state['remediations'].append({'reason': reason, 'after_attempt': len(state['attempts'])})
    state['pause'] = None


def metrics(state: dict[str, Any]) -> dict[str, Any]:
    first = [a for a in state['attempts'] if a['ordinal'] == 1 and 'review' in a]
    passed = sum(a['review_status'].startswith('PASS') for a in first)
    return {'first_reviewed': len(first), 'first_usable': passed,
            'first_pass_yield': passed / len(first) if first else None,
            'unreviewed': sum(a['status'] == 'COMPLETED' and 'review' not in a for a in state['attempts']),
            'generation_attempts': len(state['attempts']),
            'technical_failures': sum(a['status'] in {'FAILED', 'NOT_CREATED'} for a in state['attempts']),
            'known_credits': sum(a['credits'] or 0 for a in state['attempts']),
            'in_flight_or_unknown_count': sum(a['status'] in {'RESERVED', 'UNKNOWN'} for a in state['attempts']),
            'billing_unknown_count': sum(a['credits'] is None for a in state['attempts']),
            'pause': state['pause']}


def replan(state: dict[str, Any], *, frame: dict[str, Any], reason: str) -> None:
    """Replace one path in the same stage, retaining all failure and spending history."""
    if 'stage' not in state or not reason.strip():
        raise ValueError('SHARED_STAGE_AND_REPLAN_EVIDENCE_REQUIRED')
    verify_visual(frame)
    sid = frame['spec']['shot_id']
    if sid in state['stage']['protected_targets']:
        raise ValueError('PROTECTED_TARGET')
    if frame.get('schema') == 'video-decision-v1' and frame['stage_id'] != state['stage']['id']:
        raise ValueError('DECISION_BUDGET_SCOPE_MISMATCH')
    video = frame.get('schema') == 'video-decision-v1'
    if video and state['stage'].get('video_target') not in {None, sid}:
        raise ValueError('STAGE_ONE_FORMAL_VIDEO_TARGET')
    prior = [a for a in state['attempts'] if a['shot_id'] == sid]
    if any(a['status'] in {'RESERVED', 'UNKNOWN'} or (a['status'] == 'COMPLETED' and 'review' not in a) for a in state['attempts']):
        raise ValueError('RECOVER_OR_REVIEW_ORIGINAL_ATTEMPT')
    if any(a.get('review_status', '').startswith('PASS') for a in prior) or len(prior) >= 2:
        raise ValueError('PASSED_OR_EXHAUSTED_TARGET')
    if prior and prior[-1].get('review_status') != 'FAIL':
        raise ValueError('TECHNICAL_FAILURE_NOT_AN_ARTISTIC_RETRY')
    old = state['frames'].get(sid)
    if old:
        if old.get('schema') != frame.get('schema'):
            raise ValueError('TARGET_MEDIA_KIND_CHANGED')
        if frame.get('schema') == 'video-decision-v1':
            for key in ['work_id', 'scene_id', 'shot_id', 'target_id', 'shot_type', 'source_fingerprint',
                        'duration_seconds', 'aspect_ratio', 'sound', 'language', 'required', 'forbidden']:
                if old['requirements'][key] != frame['requirements'][key]:
                    raise ValueError('CREATIVE_REQUIREMENTS_CHANGED')
            def creative(f: dict[str, Any]) -> dict[str, Any]:
                return {k: v for k, v in f['requirements']['frozen_creative'].items() if k != 'motion_prompt'}
            if creative(old) != creative(frame):
                raise ValueError('CREATIVE_REQUIREMENTS_CHANGED')
        elif old['spec'] != frame['spec']:
            raise ValueError('IMAGE_REPLAN_MUST_PRESERVE_FROZEN_SPEC')
    proposed = {**state['frames'], sid: frame}
    images = [f for f in proposed.values() if f.get('schema') != 'video-decision-v1']
    if len(images) > 3:
        raise ValueError('STAGE_IMAGE_LIMIT')
    if images:
        new_campaign(images)
    state['frames'] = proposed
    if video:
        state['stage']['video_target'] = sid
    state['plan_fingerprint'] = sha256_canonical(list(proposed.values()))
    if sid not in state['pilots']:
        state['pilots'].append(sid)
    state['remediations'].append({'reason': reason, 'after_attempt': len(state['attempts']), 'target': sid,
                                  'previous_fingerprint': old['fingerprint'] if old else None})
    state['pause'] = None


def inspect_output(state: dict[str, Any], *, attempt_id: str, technical: dict[str, Any],
                   copies: list[dict[str, Any]], content_observation: str) -> None:
    import hashlib
    a: dict[str, Any] = next(a for a in state['attempts'] if a['attempt_id'] == attempt_id)
    if a['status'] != 'COMPLETED' or not content_observation.strip():
        raise ValueError('COMPLETED_OUTPUT_AND_OBSERVATION_REQUIRED')
    required = {'duration', 'dimensions', 'fps', 'audio', 'integrity', 'linkage'}
    if set(technical.get('checks', {})) != required or not technical.get('evidence') or not technical.get('probe'):
        raise ValueError('TECHNICAL_EVIDENCE_REQUIRED')
    if any(v not in {'PASS', 'FAIL', 'UNKNOWN'} for v in technical['checks'].values()):
        raise ValueError('INVALID_TECHNICAL_CHECK')
    for copy in copies:
        if copy['job_id'] != a['job_id'] or copy['content_hash'] != a['output_hash']:
            raise ValueError('COPY_JOB_OR_HASH_MISMATCH')
        if hashlib.sha256(Path(copy['local_path']).read_bytes()).hexdigest() != copy['content_hash']:
            raise ValueError('COPY_BYTES_MISMATCH')
        if not {'upload_name', 'media_id', 'storage_object'} <= set(copy):
            raise ValueError('DISTINCT_MEDIA_IDENTIFIERS_REQUIRED')
    if not copies:
        raise ValueError('LOCAL_OUTPUT_REQUIRED')
    a.update(technical=deepcopy(technical), technical_status='PASS' if all(v == 'PASS' for v in technical['checks'].values()) else ('FAIL' if 'FAIL' in technical['checks'].values() else 'PENDING_REVIEW'),
             copies=deepcopy(copies), content_observation=content_observation)


def retry_not_created(state: dict[str, Any], *, attempt_id: str, evidence: str,
                      quote: dict[str, Any], balance: dict[str, Any]) -> dict[str, Any]:
    """Retry the same request only after proof it never created a provider job."""
    a: dict[str, Any] = next(a for a in state['attempts'] if a['attempt_id'] == attempt_id)
    if (a['status'] != 'NOT_CREATED' or a['job_id'] is not None or a['credits'] is not None
            or not evidence.strip() or a.get('technical_retry_count', 0) >= 2):
        raise ValueError('NOT_CREATED_PROOF_REQUIRED_OR_RETRIES_EXHAUSTED')
    frame = state['frames'][a['shot_id']]
    verify_visual(frame)
    if frame['fingerprint'] != a['frame_fingerprint']:
        raise ValueError('RETRY_REQUEST_CHANGED')
    # Temporarily exclude this same reservation for validation; no second spend.
    remaining = {**state, 'attempts': [other for other in state['attempts'] if other is not a]}
    amount = _stage_gate(remaining, frame, a['request'], quote, balance)
    a.update(status='RESERVED', reserved_credits=amount, quote=deepcopy(quote), balance=deepcopy(balance),
             technical_retry_count=a.get('technical_retry_count', 0)+1, retry_evidence=evidence)
    state['pause'] = None
    return a


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'init-stage', 'reserve', 'result', 'review', 'resume', 'billing', 'status', 'replan', 'inspect', 'retry-not-created', 'persist'])
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--shot')
    args = parser.parse_args()
    payload: Any = json.loads(args.input.read_text()) if args.input else None
    if args.command in {'init', 'init-stage', 'result', 'review', 'resume', 'billing', 'replan', 'inspect', 'retry-not-created', 'persist'} and args.input is None:
        parser.error('--input is required for this command')
    if args.command == 'reserve' and not args.shot:
        parser.error('--shot is required for reserve')
    args.state.parent.mkdir(parents=True, exist_ok=True)
    # O_EXCL plus atomic replace avoids concurrent Host reservations. A stale
    # lock after a crash must be inspected; never delete it automatically.
    lock = args.state.with_suffix(args.state.suffix + '.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(fd, str(os.getpid()).encode())
        if args.command in {'init', 'init-stage'}:
            if list(args.state.parent.glob('.visual-stage-*.json')):
                raise ValueError('STAGE_REQUIRES_SAME_STATE_NOT_NEW_CAMPAIGN')
            if args.state.exists():
                raise ValueError('CAMPAIGN_ALREADY_EXISTS')
            state = new_stage(**payload) if args.command == 'init-stage' else new_campaign(payload)
            if 'stage' in state:
                # A directory has one durable stage anchor; renaming the state or
                # changing campaign/model does not grant a second budget.
                anchor = args.state.parent / ('.visual-stage-' + sha256_canonical(state['stage']['id']) + '.json')
                with anchor.open('x') as handle:
                    json.dump({'state_path': str(args.state.resolve()), 'stage_id': state['stage']['id']}, handle)
            result: Any = {'pilots': state['pilots'], 'plan_fingerprint': state['plan_fingerprint']}
        else:
            state = json.loads(args.state.read_text())
            check_campaign(state)
            if 'stage' in state:
                anchor = args.state.parent / ('.visual-stage-' + sha256_canonical(state['stage']['id']) + '.json')
                if json.loads(anchor.read_text())['state_path'] != str(args.state.resolve()):
                    raise ValueError('STAGE_STATE_PATH_CHANGED')
            if args.command == 'reserve':
                result = reserve(state, args.shot, **(payload or {}))
            elif args.command == 'retry-not-created':
                result = retry_not_created(state, **payload)
            elif args.command == 'replan':
                replan(state, **payload)
                result = metrics(state)
            elif args.command == 'persist':
                import asyncio
                from drama_plugin.hosts.visual_delivery import complete_attempt
                result = asyncio.run(complete_attempt(state, **payload))
            elif args.command == 'inspect':
                inspect_output(state, **payload)
                result = metrics(state)
            elif args.command == 'result':
                record_result(state, **payload)
                result = metrics(state)
            elif args.command == 'review':
                result = record_review(state, Review.model_validate(payload))
            elif args.command == 'resume':
                resume(state, **payload)
                result = metrics(state)
            elif args.command == 'billing':
                reconcile_billing(state, **payload)
                result = metrics(state)
            else:
                result = metrics(state)
        if 'stage' in state and isinstance(result, dict):
            result['stage_exposure_credits'] = exposure(state)
            result['stage_remaining_credits'] = state['stage']['budget_credits'] - exposure(state)
        if args.command != 'status':
            with tempfile.NamedTemporaryFile(mode='w', dir=args.state.parent, delete=False) as f:
                json.dump(state, f, ensure_ascii=False, indent=2, allow_nan=False)
                f.flush()
                os.fsync(f.fileno())
                temp = f.name
            os.replace(temp, args.state)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        os.close(fd)
        lock.unlink()


if __name__ == '__main__':
    main()
