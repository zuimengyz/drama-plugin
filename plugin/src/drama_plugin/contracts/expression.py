"""Route-owned expression, distinct from shared narrative identity and providers."""
from typing import Annotated, Literal, Self
from pydantic import Field, model_validator
from drama_plugin.contracts.base import ContractModel, sha256_canonical
from drama_plugin.contracts.creative_asset import Text, Hash

Intensity = Literal['restrained', 'elevated', 'heroic', 'legendary']
ActionIntensity = Literal['grounded', 'cinematic', 'heroic', 'extreme_heroic']
Strength = Literal['low', 'medium', 'high', 'dominant']


class CharacterCoreProfile(ContractModel):
    identity: Text
    revision: Text
    archetype: Text
    personality_core: tuple[Text, ...] = Field(min_length=1)
    historical_position: Text
    story_facts: tuple[Text, ...] = Field(min_length=1)
    source_pins: dict[Text, Hash] = Field(min_length=1)


class RealismBase(ContractModel):
    anatomy: Literal['grounded_articulating_human'] = 'grounded_articulating_human'
    material_physics: Literal['grounded'] = 'grounded'
    gravity: Literal['grounded'] = 'grounded'
    equipment_function: Literal['grounded'] = 'grounded'
    supernatural_effects: Literal['NONE'] = 'NONE'


class ExpressionDesign(ContractModel):
    """Owner-authored visible decisions. No inference of anatomy from personality."""
    face: Text
    body: Text
    costume: Text
    posture: Text
    camera: Text
    action_signature: Text


class LiveActionExpressionProfile(ContractModel):
    route: Literal['live_action_realist']
    character: Text
    core_fingerprint: Hash
    revision: Text
    visual_language: Literal['LIVE_ACTION_REALIST']
    proportions: Literal['real_human']
    performance_range: Literal['human_performable']
    equipment_range: Literal['wearable_executable']
    camera_range: Literal['restrained_motivated']
    max_action_intensity: Literal['grounded', 'cinematic']
    design: ExpressionDesign
    realism_base: RealismBase = Field(default_factory=RealismBase)
    # There are deliberately NO heroic/exaggeration controls on this branch.


class CGExpressionProfile(ContractModel):
    route: Literal['stylized_cinematic_cg']
    character: Text
    core_fingerprint: Hash
    revision: Text
    visual_language: Literal['REALISTIC_CG', 'HEROIC_CINEMATIC_CG']
    heroic_exaggeration: Intensity
    silhouette_strength: Strength
    physical_presence: Strength
    facial_intensity: Strength
    costume_iconicity: Strength
    kinetic_potential: Strength
    cinematic_scale: Strength
    martial_aura: Strength
    imperial_presence: Strength
    max_action_intensity: ActionIntensity
    design: ExpressionDesign
    realism_base: RealismBase = Field(default_factory=RealismBase)

    @model_validator(mode='after')
    def coherent_language(self) -> Self:
        if self.visual_language == 'REALISTIC_CG' and (
                self.heroic_exaggeration not in ('restrained', 'elevated')
                or self.max_action_intensity not in ('grounded', 'cinematic')):
            raise ValueError('REALISTIC_CG_CANNOT_INHERIT_HEROIC_ENVELOPE')
        return self


RouteExpressionProfile = Annotated[LiveActionExpressionProfile | CGExpressionProfile, Field(discriminator='route')]


class CharacterExpressionProfiles(ContractModel):
    character_core_profile: CharacterCoreProfile
    live_action_expression_profile: LiveActionExpressionProfile | None = None
    cg_expression_profile: CGExpressionProfile | None = None

    @model_validator(mode='after')
    def shared_core_only(self) -> Self:
        for profile in (self.live_action_expression_profile, self.cg_expression_profile):
            if profile and (profile.character != self.character_core_profile.identity
                    or profile.core_fingerprint != sha256_canonical(self.character_core_profile)):
                raise ValueError('EXPRESSION_CORE_IDENTITY_OR_REVISION_MISMATCH')
        return self


class ActionPhases(ContractModel):
    anticipation: Text
    acceleration: Text
    impact: Text
    follow_through: Text
    environmental_reaction: Text


class DirectorExpressionDecision(ContractModel):
    authority: Literal['DIRECTOR']
    source_ref: Text
    action_source_ref: Text
    camera_source_ref: Text
    work_id: Text
    scene_id: Text
    shot_id: Text
    scene_function: Literal['quiet', 'routine', 'action', 'climax']
    dramatic_reason: Text
    action_intensity: ActionIntensity
    rhythm_intent: Text
    # Phase directions are authored by Action/Camera, chosen rather than invented by Shot.
    phases: ActionPhases
    camera_language: Text


class ActionExpressionBinding(ContractModel):
    core: CharacterCoreProfile
    profile: RouteExpressionProfile
    director: DirectorExpressionDecision
    source_action_fingerprint: Hash
    facts_policy: Literal['PRESERVE_SOURCE_ACTIONS'] = 'PRESERVE_SOURCE_ACTIONS'

    @model_validator(mode='after')
    def route_and_level(self) -> Self:
        levels = ('grounded', 'cinematic', 'heroic', 'extreme_heroic')
        if self.profile.character != self.core.identity or self.profile.core_fingerprint != sha256_canonical(self.core):
            raise ValueError('ACTION_CHARACTER_CORE_MISMATCH')
        if levels.index(self.director.action_intensity) > levels.index(self.profile.max_action_intensity):
            raise ValueError('DIRECTOR_ACTION_EXCEEDS_CHARACTER_ROUTE_ENVELOPE')
        if self.director.scene_function in ('quiet', 'routine') and self.director.action_intensity not in ('grounded', 'cinematic'):
            raise ValueError('QUIET_SCENE_CANNOT_INHERIT_HEROIC_ACTION')
        if self.director.action_intensity == 'extreme_heroic' and self.director.scene_function != 'climax':
            raise ValueError('EXTREME_HEROIC_REQUIRES_SCOPED_CLIMAX')
        return self
