"""Literary sidecars only; no dialogue, Canon, media or adoption writes."""
from typing import Literal, Self
from pydantic import Field, model_validator
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text, Hash

Qualification = Literal['QUALIFIED', 'PARTIAL', 'NOT_QUALIFIED']
GATE_DIMENSIONS = ('NARRATIVE_WEIGHT', 'AUDIENCE_EMOTIONAL_INVESTMENT', 'ARC_COMPLETION',
                   'HISTORICAL_WEIGHT', 'RESONANCE_SURPLUS', 'VISUAL_SUFFICIENCY',
                   'REDUNDANCY_SCARCITY', 'OVER_EXPLANATION_RISK')
LITERARY_FORMS = ('NO_AUTHORIAL_INTERVENTION', 'NO_TEXT_VISUAL_CODA',
    'EPITAPH_LIKE_INSCRIPTION', 'ELEGY', 'DIRGE', 'PRAISE', 'HISTORIAN_COMMENT',
    'CHRONICLE_NOTE', 'CODA_POEM', 'INSCRIPTION', 'MEMORIAL_TEXT', 'EPISODE_TITLE',
    'LETTER_FRAGMENT', 'PROCLAMATION', 'SHORT_AUTHORIAL_SENTENCE', 'CUSTOM_FORM')

class SourcePin(ContractModel):
    ref: Text
    fingerprint: Hash

class GateFinding(ContractModel):
    status: Qualification
    reason: Text
    source_refs: tuple[Text, ...] = Field(min_length=1)

class LiteraryIntent(ContractModel):
    why_now: Text
    characters_cannot_say: Text
    image_already_says: Text
    what_remains_unsaid: Text
    desired_aftertaste: Text
    why_this_form: Text
    why_not_silence: Text

class AuthorialInterventionGate(ContractModel):
    work_id: Text
    node_id: Text
    event_kind: Text  # Open: death, exile, victory, regime turn, letter completion...
    source_pins: tuple[SourcePin, ...] = Field(min_length=1)
    findings: dict[str, GateFinding] = Field(default_factory=dict)
    visual_sufficient: bool = True
    world_voice_exhausted: bool = False
    literary_coda_eligibility: Qualification = 'NOT_QUALIFIED'
    eligibility_reason: Text = 'No earned need for authorial speech established.'
    intent: LiteraryIntent | None = None
    review_basis: Literal['SCRIPT_DRY_RUN', 'REVIEWED_SEQUENCE'] = 'SCRIPT_DRY_RUN'

    @model_validator(mode='after')
    def evidence(self) -> Self:
        refs = {p.ref for p in self.source_pins}
        if set(self.findings) - set(GATE_DIMENSIONS):
            raise ValueError('Unknown gate dimension')
        if any(not set(f.source_refs) <= refs for f in self.findings.values()):
            raise ValueError('Gate finding must trace to pinned context')
        return self

class LiteraryProvenance(ContractModel):
    relation: Literal['HISTORICAL_QUOTE', 'ADAPTED_HISTORICAL_TEXT', 'ORIGINAL_PROJECT_TEXT']
    epistemic_status: Literal['SOURCE_QUOTATION', 'PROJECT_ADAPTATION', 'AUTHORIAL_INTERPRETATION']
    source_pins: tuple[SourcePin, ...] = ()
    source_excerpt: str | None = None
    adaptation_note: str | None = None
    canonical_fact: Literal[False] = False

    @model_validator(mode='after')
    def source_boundary(self) -> Self:
        expected = {'HISTORICAL_QUOTE': 'SOURCE_QUOTATION',
                    'ADAPTED_HISTORICAL_TEXT': 'PROJECT_ADAPTATION',
                    'ORIGINAL_PROJECT_TEXT': 'AUTHORIAL_INTERPRETATION'}
        if self.epistemic_status != expected[self.relation]:
            raise ValueError('Original/adapted literature cannot masquerade as historical quotation')
        if self.relation != 'ORIGINAL_PROJECT_TEXT' and (not self.source_pins or not self.source_excerpt):
            raise ValueError('Historical text needs a pinned source and verified excerpt')
        if self.relation == 'ADAPTED_HISTORICAL_TEXT' and not self.adaptation_note:
            raise ValueError('Adaptation must explain changes')
        return self

class LiteraryCandidate(ContractModel):
    key: Text
    voice: Literal['AUTHORIAL'] = 'AUTHORIAL'
    form: Text  # Extensible; custom forms need a rationale, not a new enum release.
    form_rationale: Text
    text: str = ''
    provenance: LiteraryProvenance | None = None
    semantic_position: Text
    semantic_motifs: tuple[Text, ...] = ()
    emotional_function: Text
    character_ids: tuple[Text, ...] = ()
    verdict_mode: Literal['PRESERVE_AMBIGUITY', 'OPEN_QUESTION', 'RECORD_IMAGE', 'EXPLICIT_PROJECT_VIEW'] = 'PRESERVE_AMBIGUITY'
    status: Literal['PENDING_USER_REVIEW'] = 'PENDING_USER_REVIEW'
    character_dialogue_mutation: Literal[False] = False
    canon_mutation: Literal[False] = False

    @model_validator(mode='after')
    def text_boundary(self) -> Self:
        silent = self.form in {'NO_AUTHORIAL_INTERVENTION', 'NO_TEXT_VISUAL_CODA'}
        if silent and (self.text or self.provenance):
            raise ValueError('Silence cannot carry hidden narration')
        if not silent and (not self.text.strip() or self.provenance is None):
            raise ValueError('Literary text needs provenance')
        if self.provenance and self.provenance.relation == 'HISTORICAL_QUOTE' and self.text != self.provenance.source_excerpt:
            raise ValueError('Historical quote must equal the verified source excerpt')
        return self

class PriorIntervention(ContractModel):
    key: Text
    form: Text
    semantic_motifs: tuple[Text, ...] = ()
    emotional_function: Text
    source_pin: SourcePin
    character_ids: tuple[Text, ...] = ()

class AuthorialVoiceBudget(ContractModel):
    work_id: Text
    recent_interventions: tuple[PriorIntervention, ...] = ()
    # Each actual use creates a new contextual justification duty, not a fixed quota.
    distinct_contribution_against: dict[str, Text] = Field(default_factory=dict)
    repetition_explanations: dict[str, Text] = Field(default_factory=dict)
    # Caller identifies dramatic proximity from the current cut, not a time quota.
    nearby_intervention_keys: tuple[Text, ...] = ()

    @model_validator(mode='after')
    def known_nearby_uses(self) -> Self:
        if not set(self.nearby_intervention_keys) <= {p.key for p in self.recent_interventions}:
            raise ValueError('Nearby intervention must refer to the actual-use ledger')
        return self
