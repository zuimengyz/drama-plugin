"""Provider-neutral Character Art control plane; casting importance never selects medium."""
from typing import Literal
from .base import ContractModel

VisualMedium = Literal['LIVE_ACTION_PHOTOREAL', 'CINEMATIC_CG']
CharacterTreatment = Literal['NATURAL', 'HEROIC', 'MYTHIC']
RealismLevel = Literal['NATURALISTIC', 'GROUNDED_STYLIZED', 'HEIGHTENED']
CastingMode = Literal['DESIGN_NEUTRAL', 'HERO_CASTING', 'SUPPORTING_CASTING']


class VisualMediumIntent(ContractModel):
    visual_medium: VisualMedium
    character_treatment: CharacterTreatment = 'NATURAL'
    realism_level: RealismLevel = 'GROUNDED_STYLIZED'
    casting_mode: CastingMode = 'DESIGN_NEUTRAL'


def legacy_medium_intent(language: str, mode: CastingMode = 'DESIGN_NEUTRAL') -> VisualMediumIntent:
    """Explicit legacy adapter, never infer medium from prose, role or casting mode."""
    mapping = {
        'LIVE_ACTION_REALIST': ('LIVE_ACTION_PHOTOREAL', 'NATURAL', 'NATURALISTIC'),
        'REALISTIC_CG': ('CINEMATIC_CG', 'NATURAL', 'NATURALISTIC'),
        'HEROIC_CINEMATIC_CG': ('CINEMATIC_CG', 'HEROIC', 'GROUNDED_STYLIZED'),
    }
    if language.upper() not in mapping:
        raise ValueError('EXPLICIT_VISUAL_MEDIUM_REQUIRED')
    medium, treatment, realism = mapping[language.upper()]
    return VisualMediumIntent.model_validate(dict(visualMedium=medium, characterTreatment=treatment,
                                                 realismLevel=realism, castingMode=mode))


def medium_route(intent: VisualMediumIntent) -> str:
    return 'stylized_cinematic_cg' if intent.visual_medium == 'CINEMATIC_CG' else 'live_action_realist'
