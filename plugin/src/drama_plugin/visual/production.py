"""Durable, one-at-a-time Host submission gate for new image campaigns.

No network calls. Reserve before invoking the returned provider item; record the
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
from typing import Any, Literal

from pydantic import Field

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.visual.frame_request import Hash, Record, Text, verify_compiled

CATEGORIES = Literal["IDENTITY", "COSTUME", "BLOCKING", "PROP_STRUCTURE", "PROP_STATE",
                     "SCENE", "ANATOMY", "MODERN_ARTIFACT", "CROP", "COSMETIC"]
HARD = {"IDENTITY", "COSTUME", "BLOCKING", "PROP_STRUCTURE", "PROP_STATE", "ANATOMY"}


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
            verify_compiled(frame)


def reserve(state: dict[str, Any], shot_id: str) -> dict[str, Any]:
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
    if prior:
        t = frame['template']
        correction = '; '.join(f['evidence'] for f in prior[-1]['review']['findings'] if f['severity'] == 'MAJOR')
        item['input_overrides'][t['prompt_node']][t['prompt_key']] += '\nTARGETED CORRECTION: ' + correction
        item['description'] = shot_id + '-revision'
    attempt_id = sha256_canonical({'plan': state['plan_fingerprint'], 'shot': shot_id,
                                   'attempt': len(prior) + 1, 'request': item,
                                   'remediations': state['remediations']})
    attempt = {'attempt_id': attempt_id, 'shot_id': shot_id, 'ordinal': len(prior) + 1,
               'frame_fingerprint': frame['fingerprint'], 'request': item,
               'request_fingerprint': sha256_canonical(item), 'status': 'RESERVED',
               'job_id': None, 'credits': None, 'billing_event_id': None}
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
    attempt.update(credits=credits, billing_event_id=billing_event_id)


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
    if not required_checks <= set(review.checks):
        raise ValueError("REQUIRED_REVIEW_CHECKS_MISSING")
    result = _review_status(review)
    attempt.update(review=review.model_dump(mode='json'), review_status=result)
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
            'technical_failures': sum(a['status'] in {'FAILED', 'NOT_CREATED', 'UNKNOWN'} for a in state['attempts']),
            'known_credits': sum(a['credits'] or 0 for a in state['attempts']),
            'billing_unknown_count': sum(a['credits'] is None for a in state['attempts']),
            'pause': state['pause']}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'reserve', 'result', 'review', 'resume', 'billing', 'status'])
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--shot')
    args = parser.parse_args()
    payload: Any = json.loads(args.input.read_text()) if args.input else None
    if args.command in {'init', 'result', 'review', 'resume', 'billing'} and args.input is None:
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
        if args.command == 'init':
            if args.state.exists():
                raise ValueError('CAMPAIGN_ALREADY_EXISTS')
            state = new_campaign(payload)
            result: Any = {'pilots': state['pilots'], 'plan_fingerprint': state['plan_fingerprint']}
        else:
            state = json.loads(args.state.read_text())
            check_campaign(state)
            if args.command == 'reserve':
                result = reserve(state, args.shot)
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
