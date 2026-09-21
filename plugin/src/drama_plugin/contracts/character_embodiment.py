"""Source-bound observable reasoning; no anatomy, provider or archetype defaults."""
from datetime import datetime
from typing import Literal, Self
from pydantic import Field, model_validator
from .base import ContractModel
from .creative_asset import Text, Hash

class EmbodimentSource(ContractModel):
    pointer: Text
    value_hash: Hash

class ObservableEvidence(ContractModel):
    body: tuple[Text, ...] = ()
    face: tuple[Text, ...] = ()
    posture: tuple[Text, ...] = ()
    space: tuple[Text, ...] = ()
    object_relationship: tuple[Text, ...] = ()
    kinetic: tuple[Text, ...] = ()
    social: tuple[Text, ...] = ()
    pressure: tuple[Text, ...] = ()

    @model_validator(mode='after')
    def observable(self) -> Self:
        if not any(self.model_dump().values()): raise ValueError('OBSERVABLE_EVIDENCE_REQUIRED')
        return self

class EmbodimentRule(ContractModel):
    id: Text
    dimension: Literal['presence','body','face','posture','space','object','kinetic','social','pressure']
    source: tuple[EmbodimentSource, ...] = Field(min_length=1)
    interpretation: tuple[Text, ...] = Field(min_length=1)
    observable_evidence: ObservableEvidence
    conditions: Text
    avoid: tuple[Text, ...] = ()
    equipment_required: bool = False

class PhysicalThesis(ContractModel):
    id: Text
    statement: Text
    rule_ids: tuple[Text, ...] = Field(min_length=1)
    observation_test: Text

class EmbodimentContrast(ContractModel):
    comparator: Text
    source: tuple[EmbodimentSource, ...] = Field(min_length=1)
    shared_archetype: Text
    authority: Text
    decisions: Text
    body_logic: Text
    space: Text
    pressure: Text
    social: Text
    copying_prohibited: Literal[True] = True
    projection_use: Literal['REASONING_ONLY_EXCLUDE_FROM_PROMPT'] = 'REASONING_ONLY_EXCLUDE_FROM_PROMPT'

class CounterfactualReview(ContractModel):
    substitution: Text
    nearly_interchangeable: bool
    discriminating_rule_ids: tuple[Text, ...] = ()
    rationale: Text

class BodyIndependenceReview(ContractModel):
    removed: tuple[Literal['armor','weapon','cape','battlefield','costume','camera'], ...]
    surviving_rule_ids: tuple[Text, ...] = ()
    rationale: Text

class EmbodimentProvenance(ContractModel):
    source_character_package: Text
    source_version: Text
    source_checksum: Hash
    source_work: Text
    source_revision: Text
    driver_directive_hash: Hash
    directive_ref: Text
    host: Text
    created_at: datetime
    derived_from: tuple[Literal['core','dramaticIdentity','relationships','actionSignature','antiDrift','performance'], ...] = Field(min_length=1)

class CharacterEmbodiment(ContractModel):
    schema_version: Literal['character-embodiment-v1'] = 'character-embodiment-v1'
    depth: Literal['FULL','LIGHTWEIGHT','NONE','ARCHETYPE']
    rationale: Text
    rules: tuple[EmbodimentRule, ...] = ()
    visual_theses: tuple[PhysicalThesis, ...] = ()
    contrasts: tuple[EmbodimentContrast, ...] = ()
    counterfactual: CounterfactualReview | None = None
    body_independence: BodyIndependenceReview | None = None
    provenance: EmbodimentProvenance

    @model_validator(mode='after')
    def completeness(self) -> Self:
        ids={r.id for r in self.rules}
        if len(ids)!=len(self.rules): raise ValueError('DUPLICATE_EMBODIMENT_RULE')
        if len({t.id for t in self.visual_theses})!=len(self.visual_theses): raise ValueError('DUPLICATE_THESIS')
        if self.depth in ('NONE','ARCHETYPE') and (self.rules or self.visual_theses or self.contrasts):
            raise ValueError('DEPTH_MUST_NOT_HIDE_CHARACTER_DESIGN')
        if self.depth in ('FULL','LIGHTWEIGHT') and not self.rules: raise ValueError('CHARACTER_CORE_INSUFFICIENT')
        if self.depth=='FULL':
            if {r.dimension for r in self.rules} != {'presence','body','face','posture','space','object','kinetic','social','pressure'}:
                raise ValueError('FULL_EMBODIMENT_DIMENSIONS_REQUIRED')
            if not 3<=len(self.visual_theses)<=7 or not self.contrasts or not self.counterfactual or not self.body_independence:
                raise ValueError('FULL_EMBODIMENT_REVIEW_REQUIRED')
        references=[i for t in self.visual_theses for i in t.rule_ids]
        if self.counterfactual: references+=list(self.counterfactual.discriminating_rule_ids)
        if self.body_independence: references+=list(self.body_independence.surviving_rule_ids)
        if not set(references)<=ids: raise ValueError('UNKNOWN_EMBODIMENT_RULE')
        return self

    def review_findings(self) -> tuple[str, ...]:
        """Validate recorded Host judgments, not automated aesthetic recognition."""
        findings=[]
        if self.depth in ('FULL','LIGHTWEIGHT'):
            if not self.counterfactual or self.counterfactual.nearly_interchangeable or not self.counterfactual.discriminating_rule_ids:
                findings.append('DISTINCTIVENESS_INSUFFICIENT')
            b=self.body_independence
            independent={r.id for r in self.rules if not r.equipment_required and any((r.observable_evidence.body,r.observable_evidence.face,r.observable_evidence.posture,r.observable_evidence.space,r.observable_evidence.kinetic,r.observable_evidence.social,r.observable_evidence.pressure))}
            if not b or not {'armor','weapon','cape','battlefield','costume','camera'}<=set(b.removed) or not b.surviving_rule_ids or not set(b.surviving_rule_ids)<=independent:
                findings.append('EMBODIMENT_FAILS_BODY_INDEPENDENCE')
        return tuple(findings)
