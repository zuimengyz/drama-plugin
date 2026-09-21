"""Provider-neutral, route-exclusive expression projection. Never authors events."""
from copy import deepcopy
from typing import Any, Literal
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.expression import (
    CharacterExpressionProfiles, RouteExpressionProfile, ActionExpressionBinding,
)

PHYSICAL_BOUNDARY = (
    'Grounded articulating anatomy, weight, gravity, functional jointed equipment and causal contact. '
    'Preserve source events, participants, hits, casualties and outcomes. Presentation intensity is not violence level. '
    'Forbidden: magic, supernatural shockwaves, glowing weapons, explosive ground, weightless spins, '
    'people flying tens of metres, invented mass casualties or copied franchise designs.'
)


def select_expression(bundle: CharacterExpressionProfiles, route: str) -> RouteExpressionProfile:
    bundle = CharacterExpressionProfiles.model_validate(dump_contract(bundle))
    profile: RouteExpressionProfile | None
    if route == 'live_action_realist':
        profile = bundle.live_action_expression_profile
    elif route == 'stylized_cinematic_cg':
        profile = bundle.cg_expression_profile
    else:
        raise ValueError('EXPRESSION_ROUTE_UNSUPPORTED')
    if profile is None:
        raise ValueError('EXPLICIT_ROUTE_EXPRESSION_PROFILE_REQUIRED_NO_FALLBACK')
    return profile


def compile_casting_expression(bundle: CharacterExpressionProfiles, route: str,
                               mode: Literal['DESIGN_NEUTRAL', 'HERO_CASTING']) -> dict[str, Any]:
    from .contracts.visual_medium import legacy_medium_intent
    from .visual_medium import compile_character_art
    profile = select_expression(bundle, route)
    core = bundle.character_core_profile
    lines = [
        'FULL BODY: single person, entire head and both feet with margin; hands, clothing construction and any authored props visible. Vertical character selection image; no face close-up, cropped legs, collage, text or watermark.',
        f'Character identity: {core.identity}. Archetype: {core.archetype}.',
        'Shared personality: ' + '; '.join(core.personality_core),
        'Historical position: ' + core.historical_position,
        'Fixed narrative facts (not extra objects to illustrate): ' + '; '.join(core.story_facts),
        *[key + ': ' + value for key, value in dump_contract(profile.design).items() if key != 'actionSignature'],
        PHYSICAL_BOUNDARY, 'Unapproved candidate; retain for user review, never auto-adopt as canonical identity.',
    ]
    return compile_character_art(legacy_medium_intent(profile.visual_language, mode),
        [dict(id='expression.'+str(i), text=text, sources=['expressionProfiles']) for i, text in enumerate(lines)],
        legacy=True, source_intent='legacy:expressionProfiles.visualLanguage')


def casting_expression(bundle: CharacterExpressionProfiles, route: str,
                       mode: Literal['DESIGN_NEUTRAL', 'HERO_CASTING']) -> str:
    return str(compile_casting_expression(bundle, route, mode)['prompt'])


def project_action_expression(actions: list[dict[str, Any]], binding: ActionExpressionBinding) -> dict[str, Any]:
    binding = ActionExpressionBinding.model_validate(dump_contract(binding))
    if sha256_canonical(actions) != binding.source_action_fingerprint:
        raise ValueError('ACTION_EXPRESSION_SOURCE_EVENTS_CHANGED')
    level = binding.director.action_intensity
    language = {
        'grounded': 'Economical travel and readable effort; observe causal movement with restrained camera.',
        'cinematic': 'Accentuate authored weight transfer and momentum with motivated tracking and clear spatial continuity.',
        'heroic': 'CG-only broad whole-body force, decisive acceleration, weighty follow-through; motivated low tracking or impact reframing.',
        'extreme_heroic': 'CG-only selective climax escalation of silhouette, amplitude and camera scale; preserve grounded contact and recovery.',
    }[level]
    return {'character': binding.core.identity, 'scope': 'ONLY_NAMED_CHARACTER_NOT_OTHER_ACTORS', 'canonicalActions': deepcopy(actions), 'visualRoute': binding.profile.route,
        'actionIntensity': level, 'presentation': language,
        'characterSignature': binding.profile.design.action_signature,
        'directorDecision': dump_contract(binding.director), 'physicalBoundary': PHYSICAL_BOUNDARY,
        'sourceActionFingerprint': binding.source_action_fingerprint}
