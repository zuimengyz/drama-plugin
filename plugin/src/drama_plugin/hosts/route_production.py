"""Work-owned route and existing visual stage. No parallel event state machine.

The official Work holds the canonical stage; local JSON is an audit snapshot.
The Host submits only the request returned by a persisted reservation, once.
An uncertain return is inspected through the Work before any external submission.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.creation import Work
from drama_plugin.exceptions import ContractValidationError
from drama_plugin.providers.base import MemoryProvider, MediaProvider
from drama_plugin.visual.video_selection import ProductionRoute, qualify_route, route_input_gate, choose_routes
from drama_plugin.config.video_route import VideoRoutePolicy
from drama_plugin.visual import production


async def guard_direct_generation(memory: MemoryProvider, parameters: dict[str, Any] | None) -> None:
    # A naked prompt has no replayable professional contract, gate or reservation.
    # Keep the old API as an explicit migration error; absence of Work is not consent.
    raise ContractValidationError('USE_FORMAL_ROUTE_RESERVATION_BEFORE_PAID_GENERATION: legacy raw prompt execution retired')


async def validate_route_direction_sources(memory: MemoryProvider, work: Work, route: ProductionRoute) -> None:
    from drama_plugin.creative_source import production_gate
    production_gate(work.content, work.content.get('productionJurisdiction'))
    # Source-pinned director artifacts use the same route, not another selector.
    # Re-read canon before a new/revised route can become a production plan.
    if route.requirements.get('cinematic_directions'):
        from drama_plugin.visual.cinematic import validate_canon, verify_frozen
        for frozen in route.requirements['cinematic_directions'].values():
            spec = verify_frozen(frozen)
            shot = await memory.get_shot(spec.shot_id)
            scene = await memory.get_scene(shot.scene_id)
            episode = await memory.get_episode(scene.episode_id)
            script = await memory.get_script(episode.script_id)
            from drama_plugin.creative_source import validate_script_content
            validate_script_content(work.content, script.content)
            context: dict[str, Any] = {key: value.model_dump(mode='json') for key, value in
                [('work', work), ('script', script), ('episode', episode), ('scene', scene), ('shot', shot)]}
            if frozen.get('dialogueCoverage'):
                context['dialogueCoverage'] = frozen['dialogueCoverage']
                context['sceneShots'] = [s.model_dump(mode='json') for s in await memory.list_shots(scene.id)]
            validate_canon(spec, context)


async def save_route(memory: MemoryProvider, work_id: str, raw: dict[str, Any], *,
                     policy: VideoRoutePolicy | None = None, task_policy: VideoRoutePolicy | None = None) -> dict[str, Any]:
    route = ProductionRoute.model_validate(raw)
    if route.work_id != work_id:
        raise ValueError('ROUTE_WORK_MISMATCH')
    work = await memory.get_work(work_id)
    await validate_route_direction_sources(memory, work, route)
    existing = work.content.get('productionRoute')
    if existing == raw and policy is None and task_policy is None:
        return qualify_route(route)
    stage = work.content.get('productionStage')
    if stage and any(a['status'] in {'RESERVED', 'UNKNOWN'} for a in stage['attempts']):
        raise ValueError('RECOVER_OR_REVIEW_BEFORE_ROUTE_CHANGE')
    choice = choose_routes([route], policy=policy, task_policy=task_policy)
    if not choice['selected']:
        raise ValueError('NO_EXECUTABLE_CANDIDATE:' + str(choice['route_policy_resolution']))
    result = qualify_route(route)
    result['route_policy_resolution'] = choice['route_policy_resolution']
    if not result['eligible']:
        raise ValueError('INCOMPLETE_OR_INELIGIBLE_PRODUCTION_ROUTE')
    if stage:
        old = ProductionRoute.model_validate(stage['production_route'])
        if route.candidate.cost.unit != stage['stage'].get('budget_unit', 'credits'):
            raise ValueError('BUDGET_UNIT_MISMATCH')
        if route.continuation:
            previous = [old] + [ProductionRoute.model_validate(r['previous_route'])
                for r in stage.get('route_revisions', []) if r.get('previous_route')]
            same = [p.continuation for p in previous if p.continuation and
                    p.continuation.authorization_ref == route.continuation.authorization_ref]
            if same and any(a != route.continuation for a in same):
                raise ValueError('CONTINUATION_AUTHORIZATION_CANNOT_RESET_BASELINE')
            production.continuation_baseline(stage, route, opening=not same)
            target = route.continuation.target_id
            if (route.work_id != old.work_id or route.stage_id != old.stage_id
                    or target not in old.video_targets
                    or route.requirements.get('shots', {}).get(target) != old.requirements.get('shots', {}).get(target)):
                raise ValueError('CONTINUATION_CANNOT_CHANGE_FORMAL_TARGET_OR_STAGE')
        elif (route.work_id, route.stage_id, route.video_targets, route.creative_fingerprint) != (
                old.work_id, old.stage_id, old.video_targets, old.creative_fingerprint):
            raise ValueError('ROUTE_CHANGE_CANNOT_RESET_TARGET_OR_STAGE')
        if stage['stage']['budget_credits'] is not None and result['incremental_credits'] > stage['stage']['budget_credits']:
            raise ValueError('ROUTE_CHANGE_EXCEEDS_AUTHORIZATION')
        stage = deepcopy(stage)
        stage.setdefault('route_revisions', []).append({'previous_route': existing,
            'after_attempt': len(stage['attempts']), 'next_route_id': route.route_id})
        stage['production_route'] = raw
    content = {**work.content, 'productionPolicy': {**work.content.get('productionPolicy', {}), 'routeRequired': True,
               'videoRoutePolicyResolution': choice['route_policy_resolution']}, 'productionRoute': raw}
    if stage:
        content['productionStage'] = stage
    await memory.save_work(work.id, work.title, content, work.description)
    fresh = await memory.get_work(work.id)
    if (fresh.content.get('productionRoute') != raw or
            fresh.content.get('productionPolicy', {}).get('videoRoutePolicyResolution') != choice['route_policy_resolution']):
        raise ValueError('ROUTE_WRITE_NOT_VERIFIED')
    return result


async def operate(memory: MemoryProvider, work_id: str, command: str,
                  payload: dict[str, Any], *, media: MediaProvider | None = None) -> dict[str, Any]:
    work = await memory.get_work(work_id)
    raw_route = work.content.get('productionRoute')
    if not raw_route:
        raise ValueError('FORMAL_ROUTE_REQUIRED_BEFORE_IMAGES')
    route = ProductionRoute.model_validate(raw_route)
    if route.work_id != work.id:
        raise ValueError('ROUTE_WORK_MISMATCH')
    if command in {'check-input', 'init-stage', 'add-frame', 'reserve', 'begin-submission', 'replan', 'retry-not-created'}:
        await validate_route_direction_sources(memory, work, route)
    if command == 'begin-submission':
        from drama_plugin.hosts.specialized_asset import validate_visual_submission
        attempt = next(a for a in work.content.get('productionStage', {}).get('attempts', [])
                       if a['attempt_id'] == payload['attempt_id'])
        requirements = attempt['frame_snapshot'].get('requirements', {})
        intent = requirements.get('frozen_creative', {}).get('cinematic_direction')
        validate_visual_submission(work, attempt['request'], authority_context=requirements.get('authority_context'), creative_intent=intent)
    if command == 'check-input':
        duty = route_input_gate(route, payload['target_id'], payload['purpose'])
        if not work.content.get('productionStage'):
            raise ValueError('EXPLICIT_V2_STAGE_BUDGET_REQUIRED')
        return {'duty': duty.model_dump(mode='json'), 'submissionAllowed': False,
                'next': 'compile actual inputs and reserve the exact request'}
    original_stage = work.content.get('productionStage')
    if command in {'reserve', 'begin-submission', 'retry-not-created', 'add-frame', 'replan'}:
        from drama_plugin.visual.video_selection import Requirements
        from drama_plugin.visual.reference_duties import validate_media_snapshot
        frame = payload.get('frame')
        if frame is None and original_stage:
            target = payload.get('shot_id')
            if command in {'retry-not-created', 'begin-submission'}:
                target = next(a['shot_id'] for a in original_stage['attempts'] if a['attempt_id'] == payload['attempt_id'])
            frame = original_stage['frames'].get(target)
        if frame and frame.get('requirements', {}).get('frozen_creative', {}).get('creative_schema') == 'cinematic-shot-v1':
            req = Requirements.model_validate(frame['requirements'])
            if req.inputs and media is None:
                raise ValueError('FORMAL_REFERENCE_REFRESH_REQUIRED')
            for inp in req.inputs:
                assert media is not None
                fresh_media = await media.get_media(inp.media_id)
                validate_media_snapshot(inp, fresh_media.model_dump(mode='json'), work_id=work_id)
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
        if command == 'reseal-plan':
            production.reseal_plan(state, **payload)
        production.check_campaign(state)
        if command == 'reseal-plan':
            result = {'resealed': True}
        elif command == 'add-frame':
            production.add_route_frame(state, payload['frame']); result = {'added': True}
        elif command == 'reserve':
            result = production.reserve(state, **payload)
        elif command == 'begin-submission':
            result = production.begin_submission(state, **payload)
        elif command == 'result':
            production.record_result(state, **payload); result = production.metrics(state)
        elif command in {'video-task', 'video-delivery'}:
            from drama_plugin.contracts.video import ProviderTask, VideoRequest, request_fingerprint
            from drama_plugin.visual.execution import validate_result_identity
            task = ProviderTask.model_validate(payload['task'])
            attempt = next(a for a in state['attempts'] if a['attempt_id'] == payload['attempt_id'])
            item = attempt['request']
            if (attempt.get('execution_binding', {}).get('execution', {}).get('transport') != 'HTTP'
                    or (task.provider, task.model) != (item['provider'], item['model'])
                    or task.client_request_id != attempt['attempt_id']
                    or task.request_fingerprint != request_fingerprint(VideoRequest.model_validate(item['videoRequest']))
                    or task.output_url or attempt.get('job_id') not in (None, task.provider_task_id)):
                raise ValueError('OFFICIAL_TASK_IDENTITY_MISMATCH')
            if task.provider_task_id:
                if command == 'video-task':
                    validate_result_identity(attempt, payload['receipt'], task.provider_task_id)
                attempt['job_id'] = task.provider_task_id
            attempt['video_task'] = task.durable()
            attempt['video_cost'] = dict(provider=task.provider, model=task.model, duration=task.duration,
                resolution=task.resolution, estimatedCost=task.estimated_cost, actualCost=task.actual_cost,
                currency=task.currency, attempt=attempt['ordinal'],
                accepted=attempt.get('review_status','').startswith('PASS') if attempt.get('review_status') else None,
                rejectedReason=attempt.get('current_review',attempt.get('review')) if attempt.get('review_status') == 'FAIL' else None)
            if command == 'video-delivery':
                if attempt['status'] != 'COMPLETED' or not task.output_media_id or media is None:
                    raise ValueError('COMPLETED_PERSISTENCE_REQUIRED')
                record = await media.get_media(task.output_media_id)
                if record.work_id != work_id or record.content_hash != attempt['output_hash'] or payload['delivery'].get('mediaId') != record.id:
                    raise ValueError('OFFICIAL_MEDIA_IDENTITY_MISMATCH')
                attempt.update(delivery=payload['delivery'], persistence_status='VERIFIED',
                    delivery_status=payload['delivery']['deliveryStatus'], technical_status='PASS' if all(v == 'PASS' for v in payload['checks'].values()) else 'FAIL',
                    technical={'checks':payload['checks'], 'probe':payload['probe']})
            elif task.status in {'FAILED', 'NOT_CREATED'} and attempt['status'] == 'UNKNOWN':
                production.record_result(state, attempt_id=attempt['attempt_id'], status=task.status,
                    job_id=task.provider_task_id, evidence=task.error_code or 'Provider confirmed failure')
            result = {'task':task.durable()}
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
        elif command == 'revise-review':
            result = {'review': production.revise_review(state, **payload)}
        elif command == 'select-input':
            result = production.select_input(state, **payload)
        elif command == 'resume':
            production.resume(state, **payload); result = production.metrics(state)
        elif command == 'sync-review':
            from drama_plugin.hosts.visual_delivery import sync_review
            result = await sync_review(state, **payload)
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
