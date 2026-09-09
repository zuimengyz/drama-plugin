"""Durable, one-at-a-time Host submission gate for image and video production.

Core reservations are offline; the explicit persist command calls the configured Media adapter.
Reserve before invoking the returned provider item; record the
job outcome, then record evidence-based review. An uncertain submission remains
reserved across process restarts and cannot silently spend again.
"""
from __future__ import annotations

import argparse
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


def new_stage(*, stage_id: str, authorization_ref: str, budget_credits: float | None,
              frames: list[dict[str, Any]], protected_targets: list[str],
              production_route: dict[str, Any] | None = None,
              no_monetary_cap: bool = False) -> dict[str, Any]:
    unlimited = no_monetary_cap and budget_credits is None and production_route is not None
    if (not stage_id.strip() or not authorization_ref.strip() or
            (not unlimited and (budget_credits is None or not math.isfinite(budget_credits) or budget_credits <= 0)) or
            (no_monetary_cap and not unlimited)):
        raise ValueError('EXPLICIT_STAGE_BUDGET_REQUIRED')
    if (not frames and production_route is None) or len({f['spec']['shot_id'] for f in frames}) != len(frames):
        raise ValueError('EMPTY_OR_DUPLICATE_STAGE_TARGET')
    if production_route is not None:
        from drama_plugin.visual.video_selection import ProductionRoute, qualify_route
        route = ProductionRoute.model_validate(production_route)
        if route.stage_id != stage_id or not qualify_route(route)['eligible']:
            raise ValueError('APPROVED_EXECUTABLE_ROUTE_REQUIRED')
        if budget_credits is not None and qualify_route(route)['incremental_credits'] > budget_credits:
            raise ValueError('COMPLETE_ROUTE_EXCEEDS_AUTHORIZATION')
    for f in frames:
        verify_visual(f)
        if f.get('schema') == 'video-decision-v1' and f['stage_id'] != stage_id:
            raise ValueError('DECISION_BUDGET_SCOPE_MISMATCH')
        if f['spec']['shot_id'] in protected_targets:
            raise ValueError('PROTECTED_TARGET')
    images = [f for f in frames if f.get('schema') != 'video-decision-v1']
    videos = [f for f in frames if f.get('schema') == 'video-decision-v1']
    video_limit = production_route.get('max_video_attempts', 2) if production_route else 1
    image_limit = production_route.get('max_image_attempts', 6) if production_route else 3
    if video_limit is not None and len(videos) > video_limit:
        raise ValueError('STAGE_ONE_FORMAL_VIDEO_TARGET')
    if image_limit is not None and len(images) > image_limit:
        raise ValueError('STAGE_IMAGE_LIMIT')
    if images:
        new_campaign(images)  # Preserve V2-05 identity/version/risk qualification.
    result: dict[str, Any] = {'schema': 'visual-campaign-v1', 'frames': {f['spec']['shot_id']: f for f in frames},
            'plan_fingerprint': sha256_canonical({f['spec']['shot_id']: f for f in frames}), 'pilots': [f['spec']['shot_id'] for f in frames],
            'attempts': [], 'pause': None, 'remediations': [],
            'stage': {'id': stage_id, 'authorization_ref': authorization_ref,
                      'budget_credits': budget_credits, 'protected_targets': protected_targets,
                      'video_target': videos[0]['spec']['shot_id'] if videos else None}}
    if production_route is not None:
        result['production_route'] = deepcopy(production_route)
        if unlimited:
            result['stage']['no_monetary_cap'] = True
        for f in frames:
            _route_frame_gate(result, f)
    return result


def _route_frame_gate(state: dict[str, Any], frame: dict[str, Any]) -> None:
    from drama_plugin.visual.video_selection import ProductionRoute, qualify_route, route_input_gate
    route = ProductionRoute.model_validate(state['production_route'])
    if not qualify_route(route)['eligible']:
        raise ValueError('ROUTE_EXPIRED_OR_INCOMPLETE')
    target = frame['spec']['shot_id']
    if frame.get('schema') == 'video-decision-v1':
        if target not in route.video_targets or frame['requirements']['work_id'] != route.work_id:
            raise ValueError('VIDEO_OUTSIDE_ROUTE_SCOPE')
        if (frame['requirements']['source_fingerprint'] != route.creative_fingerprint or
                (route.requirements.get('shots') and frame['requirements']['shot_id'] != route.requirements['shots'].get(target))):
            raise ValueError('VIDEO_CREATIVE_OR_FORMAL_SHOT_CHANGED')
        if frame['candidate']['candidate_id'] != route.candidate.candidate_id:
            raise ValueError('MODEL_SWITCH_REQUIRES_ROUTE_REPLAN')
        for key in ('model', 'variant', 'mode', 'template', 'graph_hash', 'adapter_fingerprint', 'parameters'):
            if frame['candidate'][key] != route.candidate.model_dump(mode='json')[key]:
                raise ValueError('VIDEO_REQUEST_DIFFERS_FROM_ROUTE:' + key)
        if target != route.video_targets[0] and not any(
                a.get('media_kind') == 'VIDEO' and a['shot_id'] == route.video_targets[0]
                and a.get('review_status', '').startswith('PASS') for a in state['attempts']):
            raise ValueError('FIRST_VIDEO_PASS_REQUIRED_FOR_ADJACENT_TARGET')
    else:
        duty = next((i for i in route.inputs if i.target_id == target), None)
        if duty is None:
            raise ValueError('PAID_IMAGE_NOT_A_NECESSARY_ROUTE_INPUT')
        route_input_gate(route, target, duty.purpose)
        passed = {a['shot_id'] for a in state['attempts'] if a.get('review_status', '').startswith('PASS')}
        if not set(duty.requires_pass_targets) <= passed:
            raise ValueError('REQUIRED_INPUT_OR_VIDEO_REVIEW_NOT_PASSED')
        if frame['spec'].get('identity_bootstrap') and duty.target_id != route.inputs[0].target_id:
            raise ValueError('BOOTSTRAP_CANNOT_BYPASS_EXISTING_IDENTITIES')
        if frame['spec']['shot_fingerprint'] != route.creative_fingerprint:
            raise ValueError('IMAGE_CREATIVE_SOURCE_CHANGED')
        source = frame['spec'].get('edit_source')
        if source:
            matches = [a for a in state['attempts'] if a.get('output_hash') == source['content_hash']
                       and a.get('delivery', {}).get('mediaId') == source['media_id']
                       and a.get('persistence_status') == 'VERIFIED']
            if len(matches) != 1:
                raise ValueError('EDIT_SOURCE_REQUIRES_VERIFIED_FORMAL_ATTEMPT')
            baseline = matches[0]
            if source['review'] == 'EDIT_BASELINE':
                if target != baseline['shot_id'] or not baseline.get('current_review'):
                    raise ValueError('EDIT_BASELINE_REQUIRES_SAME_TARGET_REASSESSMENT')
            elif baseline.get('review_status') != source['review']:
                raise ValueError('EDIT_SOURCE_CURRENT_REVIEW_MISMATCH')


def add_route_frame(state: dict[str, Any], frame: dict[str, Any]) -> None:
    """Materialize a planned duty after inputs exist without a second campaign."""
    check_campaign(state)
    verify_visual(frame)
    _route_frame_gate(state, frame)
    target = frame['spec']['shot_id']
    if target in state['frames']:
        raise ValueError('EXISTING_TARGET_REQUIRES_REPLAN')
    state['frames'][target] = deepcopy(frame)
    state['pilots'].append(target)
    state['plan_fingerprint'] = sha256_canonical(state['frames'])


def _fresh(observation: dict[str, Any]) -> None:
    from datetime import datetime, timezone
    from drama_plugin.visual.video_selection import Evidence
    if not Evidence.model_validate(observation['evidence']).current(datetime.now(timezone.utc)):
        raise ValueError('LIVE_PRICE_OR_BALANCE_EXPIRED')


def exposure(state: dict[str, Any]) -> float:
    return float(sum(a['credits'] if a['credits'] is not None else a['reserved_credits'] for a in state['attempts']))


def _stage_gate(state: dict[str, Any], frame: dict[str, Any], request: dict[str, Any],
                quote: dict[str, Any] | None, balance: dict[str, Any] | None) -> float:
    if 'production_route' in state:
        _route_frame_gate(state, frame)
    if quote is None:
        raise ValueError('FRESH_QUOTE_AND_BALANCE_REQUIRED')
    _fresh(quote)
    if balance is None:
        raise ValueError('ACCOUNT_OBSERVATION_REQUIRED')
    _fresh(balance)
    from datetime import datetime
    observed = datetime.fromisoformat(balance['evidence']['checked_at'])
    if any(a.get('billing_reconciled_at') and observed <= datetime.fromisoformat(a['billing_reconciled_at']) for a in state['attempts']):
        raise ValueError('BALANCE_MUST_BE_REFRESHED_AFTER_SETTLEMENT')
    if quote['request_fingerprint'] != sha256_canonical(request) or quote.get('uncertainty'):
        raise ValueError('REQUEST_QUOTE_MISMATCH_OR_UNKNOWN_CHARGES')
    if quote.get('unit') != 'credits' or balance.get('unit') != 'credits':
        raise ValueError('BUDGET_UNIT_MISMATCH')
    amount = quote['conservative_credits']; available = balance['available_credits']; margin = balance['margin_credits']
    if any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in [amount, margin]) or amount <= 0 or margin <= 0 or (available is not None and (not isinstance(available,(int,float)) or not math.isfinite(available) or available < 0)):
        raise ValueError('INVALID_QUOTE_OR_BALANCE')
    unsettled = sum(a['reserved_credits'] for a in state['attempts'] if a['credits'] is None)
    cap = state['stage']['budget_credits']
    if cap is None and not state['stage'].get('no_monetary_cap'):
        raise ValueError('EXPLICIT_STAGE_BUDGET_REQUIRED')
    # An unavailable provider balance is recorded as unknown. The explicit
    # stage ceiling still bounds all paid and unsettled requests below.
    if (cap is not None and exposure(state) + amount > cap) or (available is not None and unsettled + amount + margin > available):
        raise ValueError('STAGE_BUDGET_OR_BALANCE_EXCEEDED')
    video = frame.get('schema') == 'video-decision-v1'
    if video:
        # Quote may include margin, but cannot undercut the recorded paid path.
        costs = frame['candidate']['cost']['components']
        minimum = (state['production_route']['video_request_credits']
                   if 'production_route' in state else
                   sum(v for k, v in costs.items() if k not in {'correction', 'new_inputs', 'existing_input'}))
        if amount < minimum:
            raise ValueError('QUOTE_BELOW_SELECTED_PATH_COST')
    if video and frame['stage_id'] != state['stage']['id']:
        raise ValueError('DECISION_BUDGET_SCOPE_MISMATCH')
    video_limit = state.get('production_route', {}).get('max_video_attempts', 2)
    image_limit = state.get('production_route', {}).get('max_image_attempts', 6)
    if video and video_limit is not None and sum(a.get('media_kind') == 'VIDEO' and a['status'] != 'NOT_CREATED' for a in state['attempts']) >= video_limit:
        raise ValueError('STAGE_VIDEO_ATTEMPTS_EXHAUSTED')
    if not video:
        if 'production_route' in state and image_limit is not None and sum(a.get('media_kind') == 'IMAGE' and a['status'] != 'NOT_CREATED' for a in state['attempts']) >= image_limit:
            raise ValueError('STAGE_IMAGE_ATTEMPTS_EXHAUSTED')
        initials = {a['shot_id'] for a in state['attempts'] if a.get('media_kind') == 'IMAGE'}
        if 'production_route' not in state and frame['spec']['shot_id'] not in initials and len(initials) >= 3:
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
    # The Host assesses narrative impact; category names do not assign severity.
    major = any(f.severity == 'MAJOR' for f in review.findings)
    if any(f.severity == 'MINOR' and f.remedy == 'REGENERATE' for f in review.findings):
        raise ValueError('MINOR_FAILURE_USE_ACCEPT_OR_POSTPROCESS')
    if ('FAIL' in review.checks.values()) != major:
        raise ValueError('CHECKS_AND_FINDINGS_DISAGREE')
    if major:
        return 'FAIL'
    if 'UNKNOWN' in review.checks.values():
        return 'PENDING_REVIEW'
    return 'PASS_WITH_NOTES' if review.findings else 'PASS'


def current_review(attempt: dict[str, Any]) -> dict[str, Any]:
    return dict(attempt.get('current_review', attempt.get('review', {})))


def usable(attempt: dict[str, Any]) -> bool:
    return str(attempt.get('review_status', '')).startswith('PASS')


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
            "plan_fingerprint": sha256_canonical({f['spec']['shot_id']: f for f in frames}), "pilots": pilots,
            "attempts": [], "pause": None, "remediations": []}


def reseal_plan(state: dict[str, Any], *, sealed_frames: list[dict[str, Any]]) -> None:
    """Recover an order-sensitive legacy seal using its exact saved request receipt."""
    before = state['plan_fingerprint']
    if sha256_canonical(sealed_frames) != before:
        raise ValueError('ORIGINAL_PLAN_SEAL_REQUIRED')
    if {f['spec']['shot_id']: f for f in sealed_frames} != state['frames']:
        raise ValueError('SEALED_PLAN_CONTENT_CHANGED')
    state.setdefault('plan_revisions', []).append({'previous_fingerprint': before,
        'reason': 'Verified original receipt; canonical mapping ignores storage object-key order'})
    state['plan_fingerprint'] = sha256_canonical(state['frames'])
    check_campaign(state)


def check_campaign(state: dict[str, Any], *, verify_inputs: bool = False) -> None:
    frames = list(state['frames'].values())
    if state['plan_fingerprint'] not in (sha256_canonical(state['frames']), sha256_canonical(frames)):
        raise ValueError("CAMPAIGN_PLAN_CHANGED")
    for frame in frames:
        if frame['fingerprint'] != sha256_canonical({k: v for k, v in frame.items() if k != 'fingerprint'}):
            raise ValueError("COMPILED_FRAME_CHANGED")
        if verify_inputs:
            verify_visual(frame)


def reserve(state: dict[str, Any], shot_id: str, *, quote: dict[str, Any] | None = None,
            balance: dict[str, Any] | None = None) -> dict[str, Any]:
    check_campaign(state)
    verify_visual(state['frames'][shot_id])
    if state['pause']:
        raise ValueError("CAMPAIGN_PAUSED:" + state['pause'])
    if any(a['status'] in {'RESERVED', 'UNKNOWN'} for a in state['attempts']):
        raise ValueError("PREVIOUS_ATTEMPT_NEEDS_OUTCOME_OR_REVIEW")
    frame = state['frames'][shot_id]
    prior = [a for a in state['attempts'] if a['shot_id'] == shot_id]
    if any(usable(a) for a in prior):
        raise ValueError('DO_NOT_REGENERATE_PASSED_SHOT')
    if prior and prior[-1].get('review_status') != 'FAIL':
        raise ValueError('TECHNICAL_FAILURE_REQUIRES_OUTCOME_RECOVERY_NOT_VISUAL_REVISION')
    passed = {a['shot_id'] for a in state['attempts'] if a.get('review_status', '').startswith('PASS')}
    if shot_id not in state['pilots'] and not set(state['pilots']) <= passed:
        raise ValueError("REPRESENTATIVE_REVIEW_REQUIRED")
    item = deepcopy(frame['request'])
    is_video = frame.get('schema') == 'video-decision-v1'
    if is_video and 'stage' not in state:
        raise ValueError('VIDEO_REQUIRES_SHARED_STAGE_BUDGET')
    if prior and is_video and prior[-1]['frame_fingerprint'] == frame['fingerprint']:
        raise ValueError('VIDEO_REVISION_REQUIRES_REQUALIFIED_DECISION')
    if prior and not is_video and not frame['spec'].get('edit_source'):
        t = frame['template']
        correction = '; '.join(f['evidence'] for f in prior[-1].get('current_review', prior[-1]['review'])['findings'] if f['severity'] == 'MAJOR')
        if item['tool'] == 'submit_workflow':
            item['workflow'][t['prompt_node']]['inputs'][t['prompt_key']] += '\nTARGETED CORRECTION: ' + correction
        else:
            item['input_overrides'][t['prompt_node']][t['prompt_key']] += '\nTARGETED CORRECTION: ' + correction
            item['description'] = shot_id + '-revision'
    reserved_credits = _stage_gate(state, frame, item, quote, balance) if 'stage' in state else None
    attempt_id = sha256_canonical({'plan': state['plan_fingerprint'], 'shot': shot_id,
                                   'attempt': len(prior) + 1, 'request': item,
                                   'remediations': state['remediations']})
    attempt = {'attempt_id': attempt_id, 'shot_id': shot_id, 'ordinal': len(prior) + 1,
               'frame_fingerprint': frame['fingerprint'], 'frame_snapshot': deepcopy(frame), 'request': item,
               'request_fingerprint': sha256_canonical(item), 'status': 'RESERVED',
               'job_id': None, 'credits': None, 'billing_event_id': None}
    if 'production_route' in state:
        attempt.update(call_id=attempt_id, target_id=shot_id,
                       call_reason='CONTENT_REWORK' if prior else 'INITIAL',
                       production_layer='LIMITED_TRIAL')
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
    if attempt.get('media_kind') == 'VIDEO' and attempt.get('technical_status') != 'PASS':
        raise ValueError('VIDEO_TECHNICAL_REVIEW_REQUIRED')
    result = _review_status(review)
    attempt.update(review=review.model_dump(mode='json'), review_status=result)
    if 'stage' in state:
        attempt['content_status'] = result
    previous_pause = state.get('pause')
    if result == 'FAIL':
        state['pause'] = 'CONTENT_REPLAN_REQUIRED'
    state.setdefault('review_events', []).append({'attempt_id':attempt['attempt_id'],
        'result':result,'previous_pause':previous_pause,'pause':state.get('pause')})
    return result


def revise_review(state: dict[str, Any], *, review: dict[str, Any], reason: str,
                  expected_review_hash: str) -> str:
    """Append a reassessment while preserving the original event and paid history."""
    revised = Review.model_validate(review)
    attempt = next(a for a in state['attempts'] if a['attempt_id'] == revised.attempt_id)
    if not reason.strip() or 'review' not in attempt:
        raise ValueError('ORIGINAL_REVIEW_AND_REVISION_REASON_REQUIRED')
    current = attempt.get('current_review', attempt['review'])
    if sha256_canonical(current) != expected_review_hash:
        raise ValueError('REVIEW_CHANGED_RELOAD')
    # Reuse every existing output/hash/check validation without replacing history.
    check = deepcopy(state)
    candidate = next(a for a in check['attempts'] if a['attempt_id'] == revised.attempt_id)
    candidate.pop('review')
    result = record_review(check, revised)
    from datetime import datetime, timezone
    event = {'review': revised.model_dump(mode='json'), 'reason': reason,
             'previous_review_hash': expected_review_hash, 'result': result,
             'recorded_at': datetime.now(timezone.utc).isoformat()}
    attempt.setdefault('original_review_status', attempt['review_status'])
    attempt.setdefault('review_revisions', []).append(event)
    attempt.update(current_review=event['review'], review_status=result, content_status=result)
    return result


def resume(state: dict[str, Any], *, reason: str, incremental_credits: float = 0) -> None:
    """Host records its next strategy; no creative approval token or counter reset."""
    if not reason.strip() or not math.isfinite(incremental_credits) or incremental_credits < 0:
        raise ValueError('REPLAN_REASON_AND_COST_REQUIRED')
    if any(a['status'] in {'RESERVED','UNKNOWN'} for a in state['attempts']):
        raise ValueError('RECOVER_ORIGINAL_SUBMISSION_FIRST')
    state['remediations'].append({'reason':reason,'incremental_credits':incremental_credits,
        'after_attempt':len(state['attempts']),'previous_pause':state.get('pause')})
    state['pause'] = None


def select_input(state: dict[str, Any], *, attempt_id: str, purpose: str, reason: str,
                 incremental_credits: float = 0) -> dict[str, Any]:
    a = next(a for a in state['attempts'] if a['attempt_id'] == attempt_id)
    if not usable(a) or a.get('persistence_status') != 'VERIFIED' or not a.get('delivery', {}).get('mediaId'):
        raise ValueError('USABLE_PERSISTED_INPUT_REQUIRED')
    if not purpose.strip():
        raise ValueError('INPUT_PURPOSE_REQUIRED')
    selection = dict(attempt_id=attempt_id,media_id=a['delivery']['mediaId'],
        content_hash=a['output_hash'],review_hash=sha256_canonical(current_review(a)),
        authority='HOST_WORKING_INPUT',purpose=purpose,reason=reason)
    resume(state,reason=reason,incremental_credits=incremental_credits)
    old=state.setdefault('input_selections',{}).get(a['shot_id'])
    state['remediations'][-1].update(target=a['shot_id'],previous_selection=old,selection=selection)
    state['input_selections'][a['shot_id']]=selection
    return selection


def metrics(state: dict[str, Any]) -> dict[str, Any]:
    first = [a for a in state['attempts'] if a['ordinal'] == 1 and 'review' in a]
    passed = sum(a.get('original_review_status',a['review_status']).startswith('PASS') for a in first)
    return {'first_reviewed': len(first), 'first_usable': passed,
            'first_pass_yield': passed / len(first) if first else None,
            'unreviewed': sum(a['status'] == 'COMPLETED' and 'review' not in a for a in state['attempts']),
            'generation_attempts': sum(bool(a.get('job_id')) for a in state['attempts']),
            'technical_failures': sum(a['status'] in {'FAILED', 'NOT_CREATED'} for a in state['attempts']),
            'known_credits': sum(a['credits'] or 0 for a in state['attempts']),
            'in_flight_or_unknown_count': sum(a['status'] in {'RESERVED', 'UNKNOWN'} for a in state['attempts']),
            'billing_unknown_count': sum(a['credits'] is None for a in state['attempts']),
            'pause': state['pause']}


def replan(state: dict[str, Any], *, frame: dict[str, Any], reason: str,
           incremental_credits: float = 0) -> None:
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
    if 'production_route' in state:
        _route_frame_gate(state, frame)
    if video and 'production_route' not in state and state['stage'].get('video_target') not in {None, sid}:
        raise ValueError('STAGE_ONE_FORMAL_VIDEO_TARGET')
    prior = [a for a in state['attempts'] if a['shot_id'] == sid]
    if any(a['status'] in {'RESERVED', 'UNKNOWN'}  for a in state['attempts']):
        raise ValueError('RECOVER_OR_REVIEW_ORIGINAL_ATTEMPT')
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
        else:
            for key in ('shot_id','shot_fingerprint'):
                if old['spec'][key] != frame['spec'][key]:
                    raise ValueError('IMAGE_CREATIVE_SOURCE_CHANGED')
    if not math.isfinite(incremental_credits) or incremental_credits < 0:
        raise ValueError('INVALID_REPLAN_COST')
    proposed = {**state['frames'], sid: frame}
    images = [f for f in proposed.values() if f.get('schema') != 'video-decision-v1']
    if len(images) > (6 if 'production_route' in state else 3):
        raise ValueError('STAGE_IMAGE_LIMIT')
    state['frames'] = proposed
    if video and 'production_route' not in state:
        state['stage']['video_target'] = sid
    state['plan_fingerprint'] = sha256_canonical(proposed)
    if sid not in state['pilots']:
        state['pilots'].append(sid)
    state['remediations'].append({'reason': reason, 'after_attempt': len(state['attempts']), 'target': sid,
                                  'previous_fingerprint': old['fingerprint'] if old else None})
    state['remediations'][-1].update(previous_frame=old, previous_pause=state.get('pause'),
        incremental_credits=incremental_credits,frame_fingerprint=frame['fingerprint'])
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
    if 'production_route' in state:
        # Keep each actual submission event visible, including confirmed noncreation.
        # Conservatively count all submission attempts toward this small stage cap.
        amount = _stage_gate(state, frame, a['request'], quote, balance)
        new = deepcopy(a)
        new_id = sha256_canonical({'retry_of': attempt_id, 'event': len(state['attempts']) + 1})
        new.update(attempt_id=new_id, call_id=new_id, status='RESERVED',
                   ordinal=a['ordinal'] + 1, call_reason='TECHNICAL_RETRY',
                   reserved_credits=amount, quote=deepcopy(quote), balance=deepcopy(balance),
                   technical_retry_count=a.get('technical_retry_count', 0) + 1,
                   retry_of=attempt_id, retry_evidence=evidence)
        state['attempts'].append(new)
        state['pause'] = None
        return new
    # Legacy stages retain their existing recovery contract.
    remaining = {**state, 'attempts': [other for other in state['attempts'] if other is not a]}
    amount = _stage_gate(remaining, frame, a['request'], quote, balance)
    a.update(status='RESERVED', reserved_credits=amount, quote=deepcopy(quote), balance=deepcopy(balance),
             technical_retry_count=a.get('technical_retry_count', 0)+1, retry_evidence=evidence)
    state['pause'] = None
    return a


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'init-stage', 'reserve', 'result', 'review', 'resume', 'billing', 'status', 'replan', 'inspect', 'retry-not-created', 'persist', 'add-route-frame'])
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--shot')
    args = parser.parse_args()
    payload: Any = json.loads(args.input.read_text()) if args.input else None
    if args.command in {'init', 'init-stage', 'result', 'review', 'resume', 'billing', 'replan', 'inspect', 'retry-not-created', 'persist', 'add-route-frame'} and args.input is None:
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
            elif args.command == 'add-route-frame':
                add_route_frame(state, payload)
                result = metrics(state)
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
            result['stage_remaining_credits'] = (state['stage']['budget_credits'] - exposure(state)
                                                 if state['stage']['budget_credits'] is not None else None)
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
