"""Provider-neutral Character Art control plane; casting importance never selects medium."""
from typing import Literal
from pydantic import model_validator
from .base import ContractModel

VisualMedium = Literal['LIVE_ACTION_PHOTOREAL', 'CINEMATIC_CG']
CharacterTreatment = Literal['NATURAL', 'HEROIC', 'MYTHIC']
RealismLevel = Literal['NATURALISTIC', 'GROUNDED_STYLIZED', 'HEIGHTENED']
CastingMode = Literal['DESIGN_NEUTRAL', 'HERO_CASTING', 'SUPPORTING_CASTING']
RenderStylization = Literal['PHOTOREAL_DIGITAL_HUMAN', 'VISIBLE_FILMIC_CG', 'HEIGHTENED_FILMIC_CG']
PresentationMode = Literal['LOOKDEV_NEUTRAL', 'HERO_PRESENTATION', 'PERFORMANCE_PRESENTATION']


class VisualMediumIntent(ContractModel):
    visual_medium: VisualMedium
    character_treatment: CharacterTreatment = 'NATURAL'
    realism_level: RealismLevel = 'GROUNDED_STYLIZED'
    casting_mode: CastingMode = 'DESIGN_NEUTRAL'
    render_stylization: RenderStylization | None = None
    render_stylization_source: str | None = None
    presentation_mode: PresentationMode | None = None

    @model_validator(mode='after')
    def independent_style_authority(self) -> 'VisualMediumIntent':
        if self.visual_medium != 'CINEMATIC_CG' and self.render_stylization is not None:
            raise ValueError('CG_RENDER_STYLIZATION_REQUIRES_CG_MEDIUM')
        if self.render_stylization is not None:
            if not self.render_stylization_source or not self.render_stylization_source.strip():
                raise ValueError('RENDER_STYLIZATION_SOURCE_REQUIRED')
            if self.presentation_mode is None:
                raise ValueError('EXPLICIT_PRESENTATION_MODE_REQUIRED')
        elif self.render_stylization_source is not None:
            raise ValueError('RENDER_STYLIZATION_SOURCE_WITHOUT_TARGET')
        return self


def revise_render_intent(intent: VisualMediumIntent, *, render_stylization: RenderStylization,
                         source: str, presentation_mode: PresentationMode,
                         casting_mode: CastingMode | None = None) -> VisualMediumIntent:
    """Explicit owner revision; never select style from role, provider or realism."""
    from .base import dump_contract
    values = dump_contract(intent)
    values.update(renderStylization=render_stylization, renderStylizationSource=source,
                  presentationMode=presentation_mode)
    if casting_mode is not None:
        values['castingMode'] = casting_mode
    return VisualMediumIntent.model_validate(values)


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
