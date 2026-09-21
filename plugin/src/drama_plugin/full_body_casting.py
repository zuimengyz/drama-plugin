"""One authorized whole-character candidate, separate from legacy proof stages.

Host must read the current Work and explicitly record the user's scoped directive.
This module cannot grant authority, select a candidate, or call a generator.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Literal
import json
from pydantic import model_serializer
from drama_plugin.contracts.expression import CharacterExpressionProfiles, CastingArchetypeProfile, ApprovedVisualTargetRange
from drama_plugin.expression import compile_casting_expression, select_expression
from drama_plugin.contracts.visual_medium import legacy_medium_intent
from drama_plugin.visual_medium import compile_character_art, VERSION

from drama_plugin.contracts.base import ContractModel, dump_contract, sha256_canonical
from drama_plugin.contracts.creative_asset import Text, Hash
from drama_plugin.contracts.creation import Work
from drama_plugin.contracts.performance_casting import RoleArchetypeProfile
from drama_plugin.contracts.casting_discriminants import VisualCastingPlan
from drama_plugin.contracts.visual_route import RouteCastingContext, RouteContext
from drama_plugin.casting_discriminants import compile_visual_discriminants, validate_visual_plan
from drama_plugin.visual_route import resolved_context
from drama_plugin.hosts.artifact_io import native_io


class FullBodyCastingSpec(ContractModel):
    purpose: Literal['CHARACTER_FULL_BODY_CASTING'] = 'CHARACTER_FULL_BODY_CASTING'
    character: Text
    variant: Text
    framing: Literal['FULL_BODY'] = 'FULL_BODY'
    costume: Text
    weapon: Text
    posture: Text
    lighting_background: Text
    sources: dict[str, Hash]
    casting_mode: Literal['DESIGN_NEUTRAL', 'HERO_CASTING'] = 'DESIGN_NEUTRAL'
    expression_profiles: CharacterExpressionProfiles | None = None
    mode_visual_intents: dict[str, dict[str, str]] | None = None
    archetype_profile: CastingArchetypeProfile | None = None
    approved_target_range: ApprovedVisualTargetRange | None = None

    @model_serializer(mode='wrap')
    def compatible_dump(self, handler: Any) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        for field, alias in (('archetype_profile','archetypeProfile'),('approved_target_range','approvedTargetRange')):
            if getattr(self,field) is None:
                data.pop(field,None); data.pop(alias,None)
        if self.mode_visual_intents is None:
            data.pop('modeVisualIntents', None)
            data.pop('mode_visual_intents', None)
        if self.expression_profiles is None:
            data.pop('expressionProfiles', None)
            data.pop('expression_profiles', None)
            if self.casting_mode == 'DESIGN_NEUTRAL':
                data.pop('castingMode', None)
                data.pop('casting_mode', None)
        return data


class CastingExecutionAuthorization(ContractModel):
    authorization_id: Text
    authority: Literal['USER_EXPLICIT_SINGLE_CANDIDATE']
    directive_ref: Text
    directive_hash: Hash
    work_id: Text
    work_revision: Text
    character: Text
    purpose: Literal['CHARACTER_FULL_BODY_CASTING']
    max_outputs: Literal[1]
    stop_after_first_result: Literal[True]
    inputs_fingerprint: Hash
    status: Literal['AUTHORIZED', 'RESERVED', 'COMPLETED']


def full_body_design(profile: RoleArchetypeProfile, plan: VisualCastingPlan,
                     context: RouteCastingContext, spec: FullBodyCastingSpec) -> dict[str, Any]:
    """Reuses authored face discriminants, not FACE/SCALE test conditions."""
    spec = FullBodyCastingSpec.model_validate(dump_contract(spec))
    if spec.character != profile.identity or spec.character != context.character_identity or not spec.sources:
        raise ValueError('CASTING_IDENTITY_OR_SOURCES_MISSING')
    if resolved_context(RouteContext(project=context.project, sequence=context.sequence, style=context.style)).visual_route != 'stylized_cinematic_cg':
        raise ValueError('EXPLICIT_CG_ROUTE_REQUIRED')
    if spec.expression_profiles is not None:
        meta = validate_visual_plan(profile, plan)
        if (context.profile_fingerprint != plan.profile_fingerprint or context.plan_fingerprint != meta['planFingerprint']
                or spec.variant not in {v.key for v in plan.variants}):
            raise ValueError('ROUTE_CASTING_SOURCE_MISMATCH')
        base = {'profileFingerprint': plan.profile_fingerprint, 'planFingerprint': meta['planFingerprint'], 'FaceDiscriminants': []}
    else:
        base = compile_visual_discriminants(profile, plan, spec.variant, 'FACE', route_context=context)
    if (spec.approved_target_range is not None or spec.archetype_profile is not None) and (spec.expression_profiles is None or context.style.visual_language != 'HEROIC_CINEMATIC_CG'):
        raise ValueError('APPROVED_RANGE_REQUIRES_EXPLICIT_HEROIC_COMPILATION')
    faces = [x['text'] for x in base['FaceDiscriminants']]
    style = context.style
    prompt = '\n'.join([
        'Single original character design candidate for a historical cinematic CG film. FULL BODY, one person only.',
        'Show the entire head and both feet with margin, both hands, clothing and any authored props. Vertical composition; no close-up, portrait crop, contact sheet, text or watermark.',
        style.rendering, style.shape_language, style.material_palette,
        'Apparent age: ' + profile.age_band,
        'Cultural design: ' + profile.cultural_world_fit,
        *faces,
        'Body structure: ' + '；'.join(profile.body.observables.values()),
        spec.costume, spec.weapon, spec.posture, spec.lighting_background,
        style.historical_boundary, *('Forbidden drift: ' + x for x in (*style.forbidden_drifts, *profile.drift_avoidance)),
        'Preserve role-defining structure before beauty. This is an unapproved whole-character candidate, not a scale proof or an adopted identity.',
    ])
    compilation = None
    if spec.expression_profiles is not None:
        if spec.expression_profiles.character_core_profile.identity != spec.character:
            raise ValueError('CASTING_EXPRESSION_CHARACTER_MISMATCH')
        selected = select_expression(spec.expression_profiles, 'stylized_cinematic_cg')
        if style.visual_language != selected.visual_language:
            raise ValueError('CASTING_STYLE_EXPRESSION_LANGUAGE_MISMATCH')
        # New route-owned design replaces legacy anatomical/costume/pose prose.
        # Spec fields remain for replay of P1-R, never merged into a new envelope.
        if style.visual_language != 'HEROIC_CINEMATIC_CG':
            base_compilation = compile_casting_expression(spec.expression_profiles, 'stylized_cinematic_cg', spec.casting_mode)
            compilation = compile_character_art(legacy_medium_intent(selected.visual_language, spec.casting_mode),
                base_compilation['visualMediumCompilation']['inputSections'] +
                [dict(id='legacy.style',text='\n'.join([style.rendering, style.material_palette, style.historical_boundary,
                    *('Forbidden drift: '+x for x in style.forbidden_drifts)]),sources=['route.style'])],
                legacy=True, source_intent='legacy:route.style.visualLanguage')
            prompt=compilation['prompt']
        if style.visual_language == 'HEROIC_CINEMATIC_CG':
            from drama_plugin.casting_visual_compiler import compile_heroic_visual_intent
            if spec.mode_visual_intents is None or set(spec.mode_visual_intents) != {'HERO_CASTING', 'DESIGN_NEUTRAL'}:
                raise ValueError('EXPLICIT_MODE_VISUAL_INTENTS_REQUIRED')
            compilation = compile_heroic_visual_intent(spec.expression_profiles, 'stylized_cinematic_cg',
                spec.casting_mode, spec.mode_visual_intents[spec.casting_mode], dump_contract(style),
                archetype=spec.archetype_profile, target_range=spec.approved_target_range)
            prompt = compilation['prompt']
    if compilation is None:
        compilation = compile_character_art(legacy_medium_intent(style.visual_language or 'REALISTIC_CG', spec.casting_mode),
            [dict(id='legacy.fullBody',text=prompt,sources=['profile','plan','spec','route.style'])],
            legacy=True, source_intent='legacy:route.style')
        prompt=compilation['prompt']
    inputs = {'compilerVersion':VERSION,'compiledPrompt':compilation['promptFingerprint'],'profile': base['profileFingerprint'], 'plan': base['planFingerprint'],
              'context': sha256_canonical(context), 'spec': dump_contract(spec)}
    return {**compilation, 'visualCompilation': compilation, 'purpose': spec.purpose, 'character': spec.character, 'visualRoute': 'stylized_cinematic_cg',
            'inputsFingerprint': sha256_canonical(inputs), 'prompt': prompt,
            'promptFingerprint': sha256_canonical(prompt), 'sources': spec.sources,
            'status': 'DESIGN_ONLY', 'userAdoption': 'PENDING', 'maxOutputs': 1}


def executable_full_body(work: Work, profile: RoleArchetypeProfile, plan: VisualCastingPlan,
                         context: RouteCastingContext, spec: FullBodyCastingSpec,
                         authorization_id: str) -> dict[str, Any]:
    from drama_plugin.characters.consumption import require_work_character
    package_route = context.style.visual_language or work.content.get('visualLanguage')
    if package_route not in {'HEROIC_CINEMATIC_CG','REALISTIC_CG'}:
        raise ValueError('EXPLICIT_CHARACTER_EXPRESSION_ROUTE_REQUIRED')
    package_context = require_work_character(work, spec.character, consumer='performance-casting', purpose='CASTING',
        route=package_route.lower())
    design = full_body_design(profile, plan, context, spec)
    binding = work.content.get('visualRouteBinding', {})
    route = resolved_context(RouteContext(project=context.project, sequence=context.sequence, style=context.style))
    if (work.content.get('approval', {}).get('status') != 'APPROVED'
            or work.id != route.work_id
            or work.content.get('visualRoute') != route.visual_route
            or binding.get('workRevision') != work.content.get('revisionId')
            or binding.get('project') != dump_contract(context.project)
            or binding.get('styleFingerprint') != sha256_canonical(context.style)
            or binding.get('sourcePins') != spec.sources):
        raise ValueError('CURRENT_APPROVED_WORK_ROUTE_BINDING_REQUIRED')
    if spec.expression_profiles is not None and work.content.get('characterExpressionProfiles', {}).get(spec.character) != dump_contract(spec.expression_profiles):
        raise ValueError('CURRENT_WORK_EXPRESSION_BINDING_REQUIRED')
    if spec.approved_target_range is not None:
        target = spec.approved_target_range
        if (spec.archetype_profile is None
                or work.content.get('approvedVisualTargetRanges', {}).get(target.range_id) != dump_contract(target)
                or work.content.get('castingArchetypeProfiles', {}).get(spec.archetype_profile.key) != dump_contract(spec.archetype_profile)):
            raise ValueError('CURRENT_WORK_APPROVED_RANGE_AND_ARCHETYPE_REQUIRED')
    raw = work.content.get('characterCastingAuthorizations', {}).get(authorization_id)
    if raw is None:
        raise ValueError('EXPLICIT_CASTING_AUTHORIZATION_REQUIRED')
    auth = CastingExecutionAuthorization.model_validate(raw)
    if (auth.authorization_id != authorization_id or auth.work_id != work.id
            or auth.work_revision != work.content.get('revisionId') or auth.character != spec.character
            or auth.inputs_fingerprint != design['inputsFingerprint'] or auth.status != 'AUTHORIZED'):
        raise ValueError('CASTING_AUTHORIZATION_STALE_OR_CONSUMED')
    return {**design, 'characterPackageContext': package_context, 'status': 'EXECUTABLE_SINGLE_CANDIDATE', 'workId': work.id,
            'workRevision': auth.work_revision, 'authorizationId': authorization_id,
            'authorizationFingerprint': sha256_canonical(auth), 'stopAfterFirstResult': True,
            'executionRoute': 'QUALIFIED_HOST_VISUAL_MCP', 'referenceMediaIds': []}


async def reserve_full_body(memory: Any, work_id: str, profile: RoleArchetypeProfile,
                            plan: VisualCastingPlan, context: RouteCastingContext,
                            spec: FullBodyCastingSpec, authorization_id: str,
                            request: dict[str, Any], ledger_root: Path) -> dict[str, Any]:
    """Consume once BEFORE Host submission. Unknown outcomes are never resubmitted.

    Uses the existing Host lock/write primitives plus formal Work readback. This
    is a single-Host handoff, not a distributed submission/approval service.
    """
    ledger_root.mkdir(parents=True, exist_ok=True)
    key = sha256_canonical([work_id, authorization_id])
    ledger = ledger_root / (key + '.json')
    io = native_io()
    with io.guard(ledger_root / (key + '.lock')):
        if ledger.exists():
            raise ValueError('CASTING_ATTEMPT_ALREADY_RESERVED_RECOVER_ONLY')
        work = await memory.get_work(work_id)
        brief = executable_full_body(work, profile, plan, context, spec, authorization_id)
        import hashlib
        auth = work.content['characterCastingAuthorizations'][authorization_id]
        target_pins = {spec.approved_target_range.approval_ref: spec.approved_target_range.approval_hash} if spec.approved_target_range else {}
        for path, digest in [*spec.sources.items(), *target_pins.items(), (auth['directiveRef'], auth['directiveHash'])]:
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
                raise ValueError('CASTING_SOURCE_BYTES_CHANGED')
        # The caller's qualified Host adapter supplies an exact request, not a
        # provider URL or arbitrary rewrite of the brief.
        if (request.get('transport') != 'MCP' or request.get('mock') is not False
                or request.get('modality') != 'IMAGE' or request.get('outputCount') != 1
                or request.get('prompt') != brief['prompt'] or not request.get('capabilityEvidence')
                or not request.get('durableCompletionAvailable')):
            raise ValueError('QUALIFIED_SINGLE_IMAGE_REQUEST_REQUIRED')
        from drama_plugin.hosts.casting_projection import full_body_seedream_projection
        expected = full_body_seedream_projection(brief, request['capabilityEvidence'], seed=request['seed'])
        if request.get('providerRequest') != expected:
            raise ValueError('CASTING_PROVIDER_PROJECTION_CHANGED')
        record = {'status': 'RESERVED_SUBMISSION_OUTCOME_UNKNOWN', 'brief': brief,
                  'request': request, 'requestFingerprint': sha256_canonical(request)}
        # Write first: a failed/uncertain formal save is fail-closed, never a retry.
        io.write(ledger, json.dumps(record, ensure_ascii=False, indent=2))
        content = deepcopy(work.content)
        content['characterCastingAuthorizations'][authorization_id]['status'] = 'RESERVED'
        content.setdefault('characterCastingAttempts', {})[authorization_id] = record
        await memory.save_work(work.id, work.title, content, work.description)
        fresh = await memory.get_work(work.id)
        if fresh.content.get('characterCastingAttempts', {}).get(authorization_id) != record:
            raise ValueError('CASTING_RESERVATION_READBACK_FAILED')
        return record
