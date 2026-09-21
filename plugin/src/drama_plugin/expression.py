"""Provider-neutral, route-exclusive expression projection. Never authors events."""
from copy import deepcopy
import json
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


def casting_expression(bundle: CharacterExpressionProfiles, route: str,
                       mode: Literal['DESIGN_NEUTRAL', 'HERO_CASTING']) -> str:
    profile = select_expression(bundle, route)
    core = bundle.character_core_profile
    if mode == 'HERO_CASTING' and (profile.route != 'stylized_cinematic_cg'
            or profile.visual_language != 'HEROIC_CINEMATIC_CG'
            or profile.heroic_exaggeration not in ('heroic', 'legendary')):
        raise ValueError('HERO_CASTING_REQUIRES_EXPLICIT_CG_HEROIC_PROFILE')
    # Independent positive templates, never a shared actor prompt with a medium suffix.
    if profile.route == 'live_action_realist':
        opening = ('LIVE_ACTION_REALIST costume casting. Real human proportions, achievable actor performance, '
                   'wearable clothing and executable gestures. Restrained motivated camera; '
                   'no hero-proportion or exaggerated silhouette defaults. Neutral readable presentation.')
    elif mode == 'HERO_CASTING':
        opening = ('HEROIC_CINEMATIC_CG / HERO_CASTING. Original sculpted feature-film CG character design. '
                   'Heroic proportion, strong silhouette, dominant physical presence and readable heroic composition. '
                   'Amplify designed volumes and martial aura within this character envelope. '
                   'Not an actor costume photo, studio audition, beauty portrait or generic game face.')
    else:
        opening = (profile.visual_language + ' / DESIGN_NEUTRAL. Designed three-dimensional character, '
                   'neutral presentation for proportion and costume inspection; retain authored shape design. '
                   'No automatic hero pose, low camera or flying cloth.')
    lines = [opening,
        'FULL BODY: single person, entire head and both feet with margin; hands, armor joints and complete weapon visible. '
        'Vertical character selection image; no face close-up, cropped legs, collage, text or watermark.',
        f'Character identity: {core.identity}. Archetype: {core.archetype}.',
        'Shared personality: ' + '; '.join(core.personality_core),
        'Historical position: ' + core.historical_position,
        'Fixed narrative facts (not extra objects to illustrate): ' + '; '.join(core.story_facts)]
    if profile.route == 'stylized_cinematic_cg':
        lines.append('CG-only expression envelope: ' + json.dumps({
            k: v for k, v in dump_contract(profile).items()
            if k not in ('design', 'realismBase', 'character', 'coreFingerprint', 'revision')}, ensure_ascii=False))
    lines += [key + ': ' + value for key, value in dump_contract(profile.design).items() if key != 'actionSignature']
    lines += [PHYSICAL_BOUNDARY, 'Unapproved candidate; retain for user review, never auto-adopt as canonical identity.']
    return '\n'.join(lines)


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
