"""Work-owned route and existing visual stage. No parallel event state machine.

The official Work holds the canonical stage; local JSON is an audit snapshot.
The Host submits only the request returned by a persisted reservation, once.
An uncertain return is inspected through the Work before any external submission.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.exceptions import ContractValidationError
from drama_plugin.providers.base import MemoryProvider
from drama_plugin.visual.video_selection import ProductionRoute, qualify_route, route_input_gate
from drama_plugin.visual import production


async def guard_direct_generation(memory: MemoryProvider, parameters: dict[str, Any] | None) -> None:
    options = parameters or {}
    wid = options.get('workId')
    if not wid:
        # Preserve legacy unscoped callers. New story orchestration always supplies
        # its formal workId and cannot enter through this legacy path.
        if options.get('routeId'):
            raise ContractValidationError('FORMAL_WORK_CONTEXT_REQUIRED')
        return
    work = await memory.get_work(str(wid))
    if work.content.get('productionPolicy', {}).get('routeRequired'):
        raise ContractValidationError('USE_FORMAL_ROUTE_RESERVATION_BEFORE_PAID_GENERATION')


async def save_route(memory: MemoryProvider, work_id: str, raw: dict[str, Any]) -> dict[str, Any]:
    route = ProductionRoute.model_validate(raw)
    if route.work_id != work_id:
        raise ValueError('ROUTE_WORK_MISMATCH')
    work = await memory.get_work(work_id)
    existing = work.content.get('productionRoute')
    if existing == raw:
        return qualify_route(route)
    stage = work.content.get('productionStage')
    if stage and any(a['status'] in {'RESERVED', 'UNKNOWN'} or
                     (a['status'] == 'COMPLETED' and 'review' not in a) for a in stage['attempts']):
        raise ValueError('RECOVER_OR_REVIEW_BEFORE_ROUTE_CHANGE')
    result = qualify_route(route)
    if not result['eligible']:
        raise ValueError('INCOMPLETE_OR_INELIGIBLE_PRODUCTION_ROUTE')
    if stage:
        old = ProductionRoute.model_validate(stage['production_route'])
        if (route.work_id, route.stage_id, route.video_targets, route.creative_fingerprint) != (
                old.work_id, old.stage_id, old.video_targets, old.creative_fingerprint):
            raise ValueError('ROUTE_CHANGE_CANNOT_RESET_TARGET_OR_STAGE')
        if stage['stage']['budget_credits'] is not None and result['incremental_credits'] > stage['stage']['budget_credits']:
            raise ValueError('ROUTE_CHANGE_EXCEEDS_AUTHORIZATION')
        stage = deepcopy(stage)
        stage['production_route'] = raw
    content = {**work.content, 'productionPolicy': {**work.content.get('productionPolicy', {}), 'routeRequired': True}, 'productionRoute': raw}
    if stage:
        content['productionStage'] = stage
    await memory.save_work(work.id, work.title, content, work.description)
    fresh = await memory.get_work(work.id)
    if fresh.content.get('productionRoute') != raw:
        raise ValueError('ROUTE_WRITE_NOT_VERIFIED')
    return result


async def operate(memory: MemoryProvider, work_id: str, command: str,
                  payload: dict[str, Any]) -> dict[str, Any]:
    work = await memory.get_work(work_id)
    raw_route = work.content.get('productionRoute')
    if not raw_route:
        raise ValueError('FORMAL_ROUTE_REQUIRED_BEFORE_IMAGES')
    route = ProductionRoute.model_validate(raw_route)
    if route.work_id != work.id:
        raise ValueError('ROUTE_WORK_MISMATCH')
    if command == 'check-input':
        duty = route_input_gate(route, payload['target_id'], payload['purpose'])
        if not work.content.get('productionStage'):
            raise ValueError('EXPLICIT_V2_STAGE_BUDGET_REQUIRED')
        return {'duty': duty.model_dump(mode='json'), 'submissionAllowed': False,
                'next': 'compile actual inputs and reserve the exact request'}
    original_stage = work.content.get('productionStage')
    if command == 'init-stage':
        if original_stage is not None:
            raise ValueError('RESTORE_EXISTING_FORMAL_STAGE')
        state = production.new_stage(stage_id=route.stage_id, frames=[], production_route=raw_route,
                                     protected_targets=[], **payload)
        result: Any = {'initialized': True}
    else:
        if original_stage is None:
            raise ValueError('EXPLICIT_V2_STAGE_BUDGET_REQUIRED')
        state = deepcopy(original_stage)
        production.check_campaign(state)
        if command == 'add-frame':
            production.add_route_frame(state, payload['frame']); result = {'added': True}
        elif command == 'reserve':
            result = production.reserve(state, **payload)
        elif command == 'result':
            production.record_result(state, **payload); result = production.metrics(state)
        elif command == 'billing':
            production.reconcile_billing(state, **payload); result = production.metrics(state)
        elif command == 'usage':
            import math
            attempt = next(a for a in state['attempts'] if a['attempt_id'] == payload['attempt_id'])
            if attempt['job_id'] != payload['job_id'] or not payload.get('event_id') or not payload.get('evidence'):
                raise ValueError('USAGE_JOB_AND_EVIDENCE_REQUIRED')
            if not math.isfinite(payload['credits']) or payload['credits'] < 0:
                raise ValueError('INVALID_USAGE')
            if any(a is not attempt and a.get('provider_usage', {}).get('event_id') == payload['event_id']
                   for a in state['attempts']):
                raise ValueError('USAGE_EVENT_ALREADY_LINKED')
            if attempt.get('provider_usage') and attempt['provider_usage'] != payload:
                raise ValueError('CONFLICTING_USAGE_OBSERVATION')
            attempt['provider_usage'] = payload
            if payload.get('submission_ack_at'):
                attempt['submitted_at'] = payload['submission_ack_at']
            result = {'usageRecorded': True, 'invoiceSettlement': 'UNKNOWN'}
        elif command == 'review':
            result = {'review': production.record_review(state, production.Review.model_validate(payload))}
        elif command == 'inspect':
            production.inspect_output(state, **payload); result = production.metrics(state)
        elif command == 'persist':
            from drama_plugin.hosts.visual_delivery import complete_attempt
            if payload.get('work_id') != work_id:
                raise ValueError('PERSISTENCE_WORK_MISMATCH')
            attempt = next(a for a in state['attempts'] if a['attempt_id'] == payload['attempt_id'])
            target = attempt['shot_id']
            consumers = next((i.for_targets for i in route.inputs if i.target_id == target), (target,))
            if route.requirements.get('shots') and payload.get('shot_id') not in {
                    route.requirements['shots'].get(t) for t in consumers}:
                raise ValueError('PERSISTENCE_OUTSIDE_PLANNED_SHOTS')
            result = await complete_attempt(state, **payload)
        elif command == 'replan':
            production.replan(state, **payload); result = production.metrics(state)
        elif command == 'retry-not-created':
            result = production.retry_not_created(state, **payload)
        else:
            raise ValueError('UNKNOWN_ROUTE_OPERATION')
    # Detect a changed full-replacement owner before saving. The CLI serializes
    # this Host's operations; no claim of a distributed transaction is made.
    current = await memory.get_work(work_id)
    if (command != 'persist' and current.content != work.content) or (command == 'persist' and
            (current.content.get('productionStage') != original_stage or
             current.content.get('productionRoute') != raw_route)):
        raise ValueError('WORK_CHANGED_RELOAD_BEFORE_RESERVING')
    content = {**current.content, 'productionStage': state}
    try:
        await memory.save_work(work.id, work.title, content, work.description)
    except Exception:
        fresh = await memory.get_work(work_id)
        if fresh.content.get('productionStage') != state:
            raise
    fresh = await memory.get_work(work_id)
    if fresh.content.get('productionStage') != state:
        raise ValueError('FORMAL_RESERVATION_NOT_VERIFIED_DO_NOT_SUBMIT')
    return {'result': result, 'state': state, 'formalOwner': work_id,
            'stateFingerprint': sha256_canonical(state), 'localRole': 'REBUILDABLE_AUDIT_VIEW'}
