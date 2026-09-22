"""Movie-level medium and source-owned visual assets; no provider controls."""
from typing import Annotated, Literal, Self
from pydantic import Field, model_validator
from .base import ContractModel
from .creative_asset import Text
from .source_pin import SourcePin

VisualMedium = Literal['LIVE_ACTION', 'CG']


class MovieVisualMedium(ContractModel):
    schema_version: Literal['movie-visual-medium-v1'] = 'movie-visual-medium-v1'
    work_id: Text
    medium: VisualMedium
    configuration_source: Text


class GlobalVisualStyle(ContractModel):
    """Closed choices intentionally cannot carry individual anatomy or set design."""
    schema_version: Literal['global-visual-style-v1'] = 'global-visual-style-v1'
    work_id: Text
    runtime_ref: SourcePin
    realism: Literal['NATURALISTIC', 'GROUNDED_STYLIZED', 'HEIGHTENED']
    render_stylization: Literal['PHOTOREAL_DIGITAL_HUMAN', 'VISIBLE_FILMIC_CG', 'HEIGHTENED_FILMIC_CG'] | None = None
    material_philosophy: Literal['PHYSICALLY_CREDIBLE'] = 'PHYSICALLY_CREDIBLE'
    lighting_philosophy: Literal['MOTIVATED', 'EXPRESSIVE'] = 'MOTIVATED'
    readability: Literal['IDENTITY_WITHOUT_BEAUTIFICATION'] = 'IDENTITY_WITHOUT_BEAUTIFICATION'
    consistency: Literal['PRESERVE_AUTHORED_IDENTITY'] = 'PRESERVE_AUTHORED_IDENTITY'


class DramaturgyInput(ContractModel):
    bible_ref: SourcePin
    record_id: Text
    # Exact fields read from the original; the asset cannot replace their values.
    constraint_fields: tuple[Text, ...] = Field(min_length=1)


class AssetDecision(ContractModel):
    text: Text
    reason: Text
    source_refs: tuple[SourcePin, ...] = Field(min_length=1)


CharacterField = Literal['face', 'body', 'age_presentation', 'hair', 'facial_hair',
    'physical_identity', 'body_proportion', 'surface_state', 'visible_life_history',
    'occupational_physical_traits', 'visual_continuity']
CostumeField = Literal['garment_structure', 'layering', 'material', 'wear',
    'maintenance_state', 'social_class_expression', 'occupation_expression',
    'movement_practicality', 'continuity']
SceneField = Literal['architecture', 'spatial_hierarchy', 'interior_structure',
    'furniture', 'surface_material', 'wear', 'lived_in_state', 'social_function',
    'economic_level', 'period_visible_details', 'environment_continuity']


class AssetBase(ContractModel):
    id: Text
    director: DramaturgyInput
    dramaturgy: DramaturgyInput
    world: DramaturgyInput


class CharacterAsset(AssetBase):
    kind: Literal['CHARACTER'] = 'CHARACTER'
    character_id: Text
    arc_stage: Text
    decisions: dict[CharacterField, AssetDecision] = Field(min_length=1)


class CostumeAsset(AssetBase):
    kind: Literal['COSTUME'] = 'COSTUME'
    character_id: Text
    arc_stage: Text
    decisions: dict[CostumeField, AssetDecision] = Field(min_length=1)


class SceneAsset(AssetBase):
    kind: Literal['SCENE'] = 'SCENE'
    scene_id: Text
    decisions: dict[SceneField, AssetDecision] = Field(min_length=1)


SpecializedAsset = Annotated[CharacterAsset | CostumeAsset | SceneAsset, Field(discriminator='kind')]


class SpecializedAssetBible(ContractModel):
    schema_version: Literal['specialized-asset-bible-v1'] = 'specialized-asset-bible-v1'
    work_id: Text
    created_by_capability: Literal['specialized-asset-design'] = 'specialized-asset-design'
    runtime_ref: SourcePin
    style_ref: SourcePin
    approval_ref: SourcePin | None = None
    assets: tuple[SpecializedAsset, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def unique_assets(self) -> Self:
        if len({asset.id for asset in self.assets}) != len(self.assets):
            raise ValueError('DUPLICATE_ASSET_ID')
        return self
