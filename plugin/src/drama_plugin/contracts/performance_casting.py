"""Role-neutral, local casting artifacts; no new business entity or adoption authority."""
from typing import Any, Literal, Self
from pydantic import Field, model_validator, model_serializer, SerializerFunctionWrapHandler
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text, Hash
from drama_plugin.contracts.casting_discriminants import AudienceAppealFinding, ArchetypeReference, ControlledArchetypalExaggeration

Stage = Literal['FACE', 'SCALE', 'SOCIAL', 'PERFORMANCE']
ReviewStatus = Literal['PASS', 'SHORTLIST', 'PARTIAL', 'REJECT']
ExcavationDimension = Literal['CORE_PERSONALITY', 'IDENTITY_RANK_OCCUPATION', 'SOCIAL_POSITION',
    'HISTORICAL_CULTURAL_ENVIRONMENT', 'EXTERNAL_PERCEPTION', 'STRENGTH_FATALITY_UNITY',
    'CHARACTER_FATE_CONTRAST', 'COUNTER_STEREOTYPE', 'PERFORMANCE_RANGE', 'VISUAL_CASTING_IMPLICATIONS']
EXCAVATION_DIMENSIONS = {'CORE_PERSONALITY', 'IDENTITY_RANK_OCCUPATION', 'SOCIAL_POSITION',
    'HISTORICAL_CULTURAL_ENVIRONMENT', 'EXTERNAL_PERCEPTION', 'STRENGTH_FATALITY_UNITY',
    'CHARACTER_FATE_CONTRAST', 'COUNTER_STEREOTYPE', 'PERFORMANCE_RANGE', 'VISUAL_CASTING_IMPLICATIONS'}

class IdentityEraContext(ContractModel):
    identity: Text
    rank: Text
    occupation: Text
    social_position: Text
    institutional_power: Text
    cultural_historical_context: Text
    habitual_decision_rights: tuple[Text, ...] = Field(min_length=1)
    expected_social_reaction: tuple[Text, ...] = Field(min_length=1)
    situated_values: tuple[Text, ...] = Field(min_length=1)

class CastingImplication(ContractModel):
    stage: Stage
    choice: Text
    observable_test: Text

class ExcavationInsight(ContractModel):
    dimension: ExcavationDimension
    interpretation: Text
    basis: Literal['HISTORICAL_SOURCE_SUPPORTED', 'PROJECT_CHARACTER_INTERPRETATION', 'CINEMATIC_CASTING_IMPLICATION']
    source_refs: tuple[Text, ...] = Field(min_length=1)
    casting_implications: tuple[CastingImplication, ...] = Field(min_length=1)

class ContextSanityCheck(ContractModel):
    status: Literal['PASS', 'FAIL']
    reasoning: Text
    reviewed_fingerprint: Hash

class CharacterExcavation(ContractModel):
    context: IdentityEraContext
    watchability: Text
    insights: tuple[ExcavationInsight, ...] = Field(min_length=10, max_length=10)
    checks: dict[Literal['IDENTITY_LOST', 'ERA_CONTEXT_LOST'], ContextSanityCheck]
    reviewer_boundary: Text

    @model_validator(mode='after')
    def coverage(self) -> Self:
        if {i.dimension for i in self.insights} != EXCAVATION_DIMENSIONS:
            raise ValueError('All ten excavation questions must influence casting')
        if set(self.checks) != {'IDENTITY_LOST', 'ERA_CONTEXT_LOST'}:
            raise ValueError('Identity and era sanity checks are required')
        return self

class SocialPresenceProof(ContractModel):
    participants: tuple[Text, ...] = Field(min_length=2)
    shared_space: Text
    camera_control: Text
    social_relations: tuple[Text, ...] = Field(min_length=1)
    decision_rights: Text
    observable_test: Text
    invalidating_cheats: tuple[Text, ...] = Field(min_length=1)
    limit: Text

class ArchetypeSource(ContractModel):
    ref: Text
    fingerprint: Hash
    basis: Literal['CANON', 'CANDIDATE', 'USER_DIRECTION', 'DESIGN']
    evidence: Text

class PresenceDimension(ContractModel):
    name: Text
    audience_impression: Text
    visible_carriers: tuple[Text, ...] = Field(min_length=1)
    false_signals: tuple[Text, ...] = ()

class FaceArchetype(ContractModel):
    key: Text
    geometry: Text
    presence_choice: Text
    distinction: Text

class BodyArchetype(ContractModel):
    observables: dict[str, Text]
    relative_claim: Text | None = None

class RelativeScaleProof(ContractModel):
    anchors: tuple[Text, ...] = Field(min_length=1)
    shared_plane: Text
    camera_control: Text
    observable_relationship: Text
    invalidating_cheats: tuple[Text, ...] = Field(min_length=1)
    limit: Text

class PerformanceStateProof(ContractModel):
    key: Text
    trigger: Text
    playable_task: Text
    preserved_traits: tuple[Text, ...] = Field(min_length=1)
    visible_change: Text
    avoid: tuple[Text, ...] = ()

class CastingStagePlan(ContractModel):
    stage: Stage
    reason: Text
    conditions: dict[str, Text] = Field(min_length=1)
    criteria: tuple[Text, ...] = Field(min_length=1)
    minimum_candidates: int = Field(ge=1)
    maximum_candidates: int = Field(ge=1)

    @model_validator(mode='after')
    def counts(self) -> Self:
        if self.minimum_candidates > self.maximum_candidates:
            raise ValueError('Invalid stage candidate interval')
        if len(set(self.criteria)) != len(self.criteria):
            raise ValueError('Duplicate review criteria')
        return self

from drama_plugin.contracts.character_package import CharacterPackageRef

class RoleArchetypeProfile(ContractModel):
    character_package: CharacterPackageRef | None = None
    schema_version: Literal['role-archetype-v1'] = 'role-archetype-v1'
    identity: Text
    revision: Text
    archetype_references: tuple[ArchetypeReference, ...] = ()
    archetypal_exaggeration: ControlledArchetypalExaggeration | None = None
    sources: tuple[ArchetypeSource, ...] = Field(min_length=1)
    story_function: Text
    screen_function: Text
    age_band: Text
    gender_expression: Text | None = None
    cultural_world_fit: Text
    attractiveness_policy: Text
    presence: tuple[PresenceDimension, ...] = Field(min_length=1)
    face_archetypes: tuple[FaceArchetype, ...] = ()
    body: BodyArchetype
    relative_scale: RelativeScaleProof | None = None
    excavation: CharacterExcavation | None = None
    social_presence: SocialPresenceProof | None = None
    performance_states: tuple[PerformanceStateProof, ...] = ()
    scene_obligations: tuple[Text, ...] = Field(min_length=1)
    drift_avoidance: tuple[Text, ...] = ()
    approval_scope: Text
    stage_plan: tuple[CastingStagePlan, ...] = Field(min_length=1)
    omitted_stages: dict[Stage, Text] = Field(default_factory=dict)

    @model_serializer(mode='wrap')
    def preserve_legacy_serialization(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data = handler(self)
        if self.character_package is None:
            data.pop('characterPackage', None)
            data.pop('character_package', None)
        if not self.archetype_references:
            data.pop('archetypeReferences', None)
            data.pop('archetype_references', None)
        if self.archetypal_exaggeration is None:
            data.pop('archetypalExaggeration', None)
            data.pop('archetypal_exaggeration', None)
        return data

    @model_validator(mode='after')
    def coherent_plan(self) -> Self:
        if any(r.role_identity != self.identity for r in self.archetype_references):
            raise ValueError('ARCHETYPE_REFERENCE_ROLE_LEAK')
        if len({r.reference_id for r in self.archetype_references}) != len(self.archetype_references):
            raise ValueError('Duplicate archetype reference')
        stages = [s.stage for s in self.stage_plan]
        if len(set(stages)) != len(stages):
            raise ValueError('Each proof stage occurs once')
        required = {'FACE', 'SCALE', 'SOCIAL', 'PERFORMANCE'} if self.excavation or 'SOCIAL' in stages else {'FACE', 'SCALE', 'PERFORMANCE'}
        if set(stages) & self.omitted_stages.keys() or set(stages) | self.omitted_stages.keys() != required:
            raise ValueError('Explain every omitted stage; do not silently waive proofs')
        if 'FACE' in stages and not self.face_archetypes:
            raise ValueError('Face search needs distinct authored archetypes')
        if 'SCALE' in stages and not self.relative_scale:
            raise ValueError('Scale needs an observable relative anchor')
        if 'PERFORMANCE' in stages and not self.performance_states:
            raise ValueError('Performance needs role-specific states')
        if 'SOCIAL' in stages and not self.social_presence:
            raise ValueError('Social presence needs observable relations, not a center-position label')
        if self.excavation:
            refs = {s.ref for s in self.sources}
            if any(not set(i.source_refs) <= refs for i in self.excavation.insights):
                raise ValueError('Excavation must trace to profile sources')
        for keys in ([a.key for a in self.face_archetypes], [s.key for s in self.performance_states], [p.name for p in self.presence]):
            if len(set(keys)) != len(keys):
                raise ValueError('Duplicate role dimension or archetype key')
        return self

class CastingFinding(ContractModel):
    status: ReviewStatus
    observation: Text

class CastingMediaRef(ContractModel):
    media_id: Text
    content_hash: Hash
    task_id: Text
    source_ref: Text

class CastingReview(ContractModel):
    audience_appeal: AudienceAppealFinding | None = None
    candidate_id: Text
    stage: Stage
    profile_fingerprint: Hash
    conditions_fingerprint: Hash
    media: tuple[CastingMediaRef, ...] = Field(min_length=1)
    identity_references: tuple[CastingMediaRef, ...] = ()
    state_media: dict[str, CastingMediaRef] = Field(default_factory=dict)
    findings: dict[str, CastingFinding] = Field(min_length=1)
    status: Literal['PENDING_USER_REVIEW'] = 'PENDING_USER_REVIEW'
    reviewer_boundary: Text

class CastingBudget(ContractModel):
    cap: float = Field(gt=0, allow_inf_nan=False)
    recorded_cost: float = Field(ge=0, allow_inf_nan=False)
    outstanding_reservations: float = Field(ge=0, allow_inf_nan=False)
    requested_reservation: float = Field(ge=0, allow_inf_nan=False)
    cost_limitations: Text
