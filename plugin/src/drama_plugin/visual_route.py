"""Pure route resolution and opt-in handoffs; no writes, approval or provider access."""
from copy import deepcopy
from typing import Any, Literal, Sequence
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.asset import Asset, AssetType
from drama_plugin.contracts.visual_route import (
    ProjectVisualRoutes, SequenceVisualRoute, ResolvedVisualRoute,
    RouteContext, RouteCastingContext, VisualRoute,
)
from drama_plugin.tools.registry import ToolRegistry


def resolve_visual_route(project: ProjectVisualRoutes, sequence: SequenceVisualRoute) -> ResolvedVisualRoute:
    project = ProjectVisualRoutes.model_validate(dump_contract(project))
    sequence = SequenceVisualRoute.model_validate(dump_contract(sequence))
    if project.work_id != sequence.work_id:
        raise ValueError('VISUAL_ROUTE_WORK_MISMATCH')
    route = sequence.visual_route or project.visual_route
    if route not in project.enabled_routes:
        raise ValueError('VISUAL_ROUTE_NOT_ENABLED')
    return ResolvedVisualRoute(work_id=project.work_id, sequence_key=sequence.sequence_key,
        visual_route=route, project_fingerprint=sha256_canonical(project),
        sequence_fingerprint=sha256_canonical(sequence), inherited=sequence.visual_route is None)


def resolved_context(context: RouteContext) -> ResolvedVisualRoute:
    context = RouteContext.model_validate(dump_contract(context))
    route = resolve_visual_route(context.project, context.sequence)
    if route.visual_route != context.style.visual_route:
        raise ValueError('VISUAL_ROUTE_STYLE_MISMATCH')
    return route


def bind_route_artifact(payload: dict[str, Any], context: RouteContext, *,
                        responsibility: Literal['CASTING', 'ART_DIRECTION', 'CAMERA', 'PERFORMANCE', 'AUTHORIAL_PRESENTATION']) -> dict[str, Any]:
    """Separate wrapper, never inject metadata into an old approved payload."""
    route = resolved_context(context)
    body = {'visualRoute': route.visual_route, 'route': dump_contract(route),
        'style': dump_contract(context.style), 'responsibility': responsibility,
        'sourcePayload': deepcopy(payload), 'sourceFingerprint': sha256_canonical(payload),
        'status': 'DESIGN_DRY_RUN', 'productionAllowed': False, 'approvalTransferAllowed': False}
    return {**body, 'fingerprint': sha256_canonical(body)}


def verify_route_artifact(packet: dict[str, Any], context: RouteContext) -> None:
    expected = bind_route_artifact(packet['sourcePayload'], context, responsibility=packet['responsibility'])
    if packet != expected:
        raise ValueError('ROUTE_ARTIFACT_STALE_OR_CHANGED')


def check_sequence_routes(packets: Sequence[dict[str, Any]], context: RouteContext) -> None:
    """One concrete clip has one route; comparisons use separate sequence keys."""
    for packet in packets:
        verify_route_artifact(packet, context)


def project_casting_route(compiled: dict[str, Any], context: RouteCastingContext, *, character_identity: str) -> dict[str, Any]:
    context = RouteCastingContext.model_validate(dump_contract(context))
    base_context = RouteContext(project=context.project, sequence=context.sequence, style=context.style)
    route = resolved_context(base_context)
    if (context.character_identity != character_identity or
        context.profile_fingerprint != compiled['profileFingerprint'] or
        context.plan_fingerprint != compiled['planFingerprint']):
        raise ValueError('ROUTE_CASTING_SOURCE_MISMATCH')
    style = context.style
    if style.visual_language is not None:
        raise ValueError('EXPLICIT_EXPRESSION_LANGUAGE_REQUIRES_ROUTE_OWNED_CASTING_TEMPLATE')
    # Legacy dry-run only; explicit expression profiles use separate templates.
    lines = [style.rendering, style.shape_language, style.material_palette,
             style.historical_boundary, *style.forbidden_drifts]
    if compiled['stage'] == 'PERFORMANCE':
        lines.extend([style.camera_grammar, style.performance_grammar])
    out = deepcopy(compiled)
    out['basePromptFingerprint'] = compiled['promptFingerprint']
    from drama_plugin.visual_medium import compile_character_art
    from drama_plugin.contracts.visual_medium import legacy_medium_intent
    language = 'REALISTIC_CG' if route.visual_route == 'stylized_cinematic_cg' else 'LIVE_ACTION_REALIST'
    out.update(compile_character_art(legacy_medium_intent(language),
        [dict(id='legacy.route.'+str(i), text=line, sources=['route.style']) for i, line in enumerate(lines)] +
        [dict(id='legacy.discriminants', text=compiled['prompt'], sources=['visualCastingPlan'])],
        legacy=True, source_intent='legacy:route.style'))
    out['visualRoute'] = route.visual_route
    out['route'] = dump_contract(route)
    out['routeStyleFingerprint'] = sha256_canonical(style)
    out['routeCastingCriteria'] = list(style.casting_criteria)
    out['routeContextFingerprint'] = sha256_canonical(context)
    out['routeReviewRequired'] = True
    out['routeStageConditionsFingerprint'] = sha256_canonical({
        'conditions': compiled['conditionsFingerprint'], 'routeContext': out['routeContextFingerprint']})
    out['productionAllowed'] = False
    return out


def discover_route_assets(assets: Sequence[Asset], *, work_id: str, visual_route: VisualRoute) -> dict[str, Any]:
    """Filter existing Asset content; untagged records are legacy/unknown, never CG."""
    # Validate requested route even for callers outside typed Python.
    ProjectVisualRoutes(work_id=work_id, revision='query', visual_route=visual_route, enabled_routes=(visual_route,))
    matches, legacy, excluded = [], [], []
    for asset in assets:
        if asset.work_id != work_id:
            continue
        stored = asset.content.get('visualRoute')
        row = {'assetId': asset.id, 'contentFingerprint': sha256_canonical(asset.content),
               'referenceMediaIds': list(asset.reference_media_ids), 'approvalInherited': False}
        if stored == visual_route:
            matches.append(row)
        elif stored is None:
            legacy.append({**row, 'reason': 'UNTAGGED_REQUIRES_SOURCE_REVIEW; no implicit CG eligibility'})
        else:
            excluded.append({**row, 'reason': 'DIFFERENT_OR_INVALID_VISUAL_ROUTE'})
    return {'visualRoute': visual_route, 'matches': matches, 'legacyForReview': legacy,
            'excluded': excluded, 'mutations': 0, 'selectionOrApproval': False}


async def search_route_assets(tools: ToolRegistry, *, work_id: str, visual_route: VisualRoute,
                              query: str, asset_type: AssetType | None = None) -> dict[str, Any]:
    assets = await tools.invoke('asset.search_assets', query=query, asset_type=asset_type)
    return discover_route_assets(assets, work_id=work_id, visual_route=visual_route)
