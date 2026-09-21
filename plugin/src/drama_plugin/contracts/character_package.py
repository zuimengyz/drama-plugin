"""Portable character authorship, independent of prompts, hosts and rendering providers."""
from typing import Literal, Self, Any
from datetime import datetime
import re
from pydantic import Field, model_validator, model_serializer
from .character_embodiment import CharacterEmbodiment
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text, Hash

Route = Literal['live_action_realist', 'realistic_cg', 'heroic_cinematic_cg']
Status = Literal['DRAFT','DESIGN_REVIEW','VISUAL_TESTING','USER_APPROVED','PRODUCTION_READY','DEPRECATED']
Category = Literal['PRIMARY_CHARACTER','SUPPORTING_CHARACTER','RECURRING_CHARACTER','ROLE_ARCHETYPE_ONLY','BACKGROUND_GROUP']

class CharacterPackageRef(ContractModel):
    character_package_ref: Text  # characters/<project>/<character>
    character_package_version: Text
    checksum: Hash

    @model_validator(mode='after')
    def safe_ref(self) -> Self:
        if not re.fullmatch(r'characters/[a-z0-9][a-z0-9_-]*/[a-z0-9][a-z0-9_-]*',self.character_package_ref):
            raise ValueError('INVALID_CHARACTER_PACKAGE_REF')
        if not re.fullmatch(r'v[0-9]+(?:\.[0-9]+)*',self.character_package_version):
            raise ValueError('EXPLICIT_CHARACTER_PACKAGE_VERSION_REQUIRED')
        return self

class PackageManifest(ContractModel):
    schema_version: Literal['character-package-v1','character-package-v2'] = 'character-package-v1'
    package_id: Text
    character_id: Text
    project_id: Text
    version: Text
    status: Status
    created_at: datetime
    updated_at: datetime
    source_work: Text
    source_revision: Text
    source_fingerprint: Hash
    supported_routes: tuple[Route,...] = Field(min_length=1)
    publisher: Text
    license: Text
    authors: tuple[Text,...] = Field(min_length=1)
    compatibility: dict[str,Text]
    dependencies: tuple[CharacterPackageRef,...] = ()
    checksum: Hash
    file_checksums: dict[str,Hash]

class CharacterCore(ContractModel):
    identity: Text
    historical_role: Text
    life_stage: Text
    dramatic_role: Text
    personality_core: tuple[Text,...] = Field(min_length=1)
    desire: Text
    fear: Text
    belief: Text
    contradiction: Text
    decision_pattern: Text
    dramatic_arc: Text

    @model_validator(mode='after')
    def no_visual_implementation(self) -> Self:
        terms = re.compile(r'low angle|black armor|cg material|photorealistic|低机位|黑色甲胄|写实人体比例',re.I)
        if terms.search(str(self.model_dump())):
            raise ValueError('VISUAL_IMPLEMENTATION_DOES_NOT_BELONG_IN_CORE')
        return self

class CharacterContrast(ContractModel):
    comparator: Text
    shared_archetype: Text
    distinction: Text
    source_basis: Text
    copying_prohibited: Literal[True] = True

class DramaticIdentity(ContractModel):
    authorial_statement: Text
    self_image: Text
    social_position: Text
    pressure: Text
    distinctive_choices: tuple[Text,...] = Field(min_length=1)
    same_archetype_comparisons: tuple[CharacterContrast,...] = Field(min_length=2)
    unresolved_questions: tuple[Text,...] = ()

class VisualEnvelope(ContractModel):
    visual_route: Literal['live_action_realist','stylized_cinematic_cg']
    visual_language: Literal['LIVE_ACTION_REALIST','REALISTIC_CG','HEROIC_CINEMATIC_CG']
    proportion_policy: Literal['REAL_HUMAN','GROUNDED_DESIGNED','HEROIC_GROUNDED']
    performance_policy: Literal['HUMAN_PERFORMABLE','CG_AUTHORED']
    equipment_policy: Literal['WEARABLE_EXECUTABLE','FUNCTIONAL_GROUNDED']
    camera_policy: Text
    design_intent: Text
    identity_anchors: tuple[Text,...] = Field(min_length=1)
    forbidden_drifts: tuple[Text,...] = ()
    unresolved_visual_choices: tuple[Text,...] = ()

    @model_validator(mode='after')
    def isolated(self) -> Self:
        if self.visual_language=='LIVE_ACTION_REALIST':
            if (self.visual_route,self.proportion_policy,self.performance_policy,self.equipment_policy) != ('live_action_realist','REAL_HUMAN','HUMAN_PERFORMABLE','WEARABLE_EXECUTABLE'):
                raise ValueError('LIVE_ACTION_ENVELOPE_CONTAMINATION')
        elif self.visual_route!='stylized_cinematic_cg' or self.performance_policy!='CG_AUTHORED' or self.equipment_policy!='FUNCTIONAL_GROUNDED':
            raise ValueError('CG_ROUTE_REQUIRED')
        if self.visual_language=='REALISTIC_CG' and self.proportion_policy!='GROUNDED_DESIGNED':
            raise ValueError('REALISTIC_CG_MUST_NOT_UPGRADE')
        return self

class VisualExpression(ContractModel):
    routes: dict[Route,VisualEnvelope]
    @model_validator(mode='after')
    def matching(self) -> Self:
        for key,value in self.routes.items():
            if key.upper()!=value.visual_language:raise ValueError('EXPRESSION_ROUTE_KEY_MISMATCH')
        return self

class ActionSignature(ContractModel):
    movement_character: Text
    decision_tempo: Text
    power_source: Text
    weapon_relationship: Text
    mobility_style: Text
    combat_rhythm: Text
    recovery_style: Text
    forbidden_drifts: tuple[Text,...]
    event_boundary: Text

class Performance(ContractModel):
    baseline: Text
    states: dict[str,Text] = Field(min_length=3)
    relational_variations: dict[str,Text]
    continuity_limits: tuple[Text,...] = Field(min_length=1)

class DialogueVoice(ContractModel):
    sentence_form: Text
    length_and_explanation: Text
    directness: Text
    rhetoric: Text
    emotional_exposure: Text
    power_language: Text
    relational_variations: dict[str,Text]
    provider_binding: Literal['UNBOUND'] = 'UNBOUND'

class AntiDrift(ContractModel):
    avoid: dict[str,Text] = Field(min_length=1)
    scope: Literal['THIS_CHARACTER_ONLY'] = 'THIS_CHARACTER_ONLY'
    review_tests: tuple[Text,...] = Field(min_length=1)

class Relationship(ContractModel):
    target_character_id: Text
    power: Text
    trust: Text
    emotion: Text
    debt: Text
    fear_or_contempt: Text
    dependence: Text
    surface: Text
    internal: Text
    evidence_refs: tuple[Text,...] = Field(min_length=1)

class Relationships(ContractModel):
    edges: tuple[Relationship,...] = ()

class HistoricalBasis(ContractModel):
    documented_facts: tuple[Text,...]
    strong_inferences: tuple[Text,...]
    artistic_interpretations: tuple[Text,...]
    uncertain_elements: tuple[Text,...]
    source_refs: tuple[Text,...] = Field(min_length=1)

class Provenance(ContractModel):
    source_work: Text
    source_files: dict[str,Hash] = Field(min_length=1)
    historical_sources: tuple[Text,...]
    host: Text
    created_at: datetime
    revision: Text
    user_feedback: tuple[dict[str,Any],...]
    reference_assets: tuple[dict[str,Any],...]
    license: Text
    authorship_boundary: Text
    approval_evidence: tuple[Text,...] = ()

class CharacterPackage(ContractModel):
    manifest: PackageManifest
    core: CharacterCore
    dramatic_identity: DramaticIdentity
    visual_expression: VisualExpression
    action_signature: ActionSignature
    performance: Performance
    dialogue_voice: DialogueVoice
    anti_drift: AntiDrift
    relationships: Relationships
    historical_basis: HistoricalBasis
    provenance: Provenance
    embodiment: CharacterEmbodiment | None = None

    @model_serializer(mode='wrap')
    def legacy_shape(self, handler):
        payload=handler(self)
        if self.embodiment is None: payload.pop('embodiment',None)
        return payload

    @model_validator(mode='after')
    def consistent(self) -> Self:
        m=self.manifest
        if (m.schema_version=='character-package-v2') != (self.embodiment is not None):
            raise ValueError('EMBODIMENT_SCHEMA_VERSION_MISMATCH')
        CharacterPackageRef(character_package_ref=f'characters/{m.project_id}/{m.character_id}',character_package_version=m.version,checksum=m.checksum)
        if set(m.supported_routes)!=set(self.visual_expression.routes):raise ValueError('SUPPORTED_ROUTES_MISMATCH')
        if m.source_work!=self.provenance.source_work or m.version!=self.provenance.revision:raise ValueError('PACKAGE_PROVENANCE_MISMATCH')
        if m.license!=self.provenance.license:raise ValueError('PACKAGE_LICENSE_MISMATCH')
        if m.status in ('USER_APPROVED','PRODUCTION_READY') and not self.provenance.approval_evidence:raise ValueError('USER_APPROVAL_EVIDENCE_REQUIRED')
        if m.updated_at<m.created_at:raise ValueError('PACKAGE_TIME_ORDER')
        return self

class CharacterDesignAuthorization(ContractModel):
    capability: Literal['character-external-driver']
    operation: Literal['CREATE_VERSION'] = 'CREATE_VERSION'
    source_work: Text
    source_revision: Text
    directive_ref: Text
    directive_hash: Hash
    allowed_package_refs: tuple[Text,...] = Field(min_length=1)
