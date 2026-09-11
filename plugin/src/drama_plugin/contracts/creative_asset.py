"""Domain content for existing OTHER/AUDIO_INPUT Assets; no new entity or Tool."""
from __future__ import annotations

import re
from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from drama_plugin.contracts.base import ContractModel

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Hash = Annotated[str, StringConstraints(pattern=r'^[0-9a-f]{64}$')]


class Provenance(ContractModel):
    source_type: Text
    source_note: Text


class PatternValidation(ContractModel):
    status: Literal['OBSERVED_PATTERN', 'PROJECT_DERIVED', 'VALIDATED', 'REJECTED']
    evidence_refs: tuple[Text, ...] = ()

    @model_validator(mode='after')
    def evidence_required(self) -> Self:
        if self.status == 'VALIDATED' and not self.evidence_refs:
            raise ValueError('VALIDATED requires evidence references')
        return self


class CinematicPattern(ContractModel):
    narrative: Text | None = None
    performance: Text | None = None
    camera: Text | None = None
    timing: Text | None = None
    lighting: Text | None = None
    environment: Text | None = None
    stability: Text | None = None

    @model_validator(mode='after')
    def neutral_pattern(self) -> Self:
        values = [v for v in self.model_dump().values() if v]
        if not values:
            raise ValueError('At least one meaningful pattern dimension is required')
        if re.search(r'seedance|comfy|bytedance|\bh3\b|\bflux\b', ' '.join(values), re.I):
            raise ValueError('Core pattern must be provider-neutral; put usage evidence in notes')
        return self


class CinematicLanguageContent(ContractModel):
    creative_kind: Literal['CINEMATIC_LANGUAGE'] = 'CINEMATIC_LANGUAGE'
    semantic_key: Annotated[str, StringConstraints(pattern=r'^cinematic-language/[a-z0-9-]+$')]
    title: Text
    purpose: Text
    usage_mode: Literal['REFERENCE_PATTERN'] = 'REFERENCE_PATTERN'
    suitable_for: tuple[Text, ...] = ()
    avoid_when: tuple[Text, ...] = ()
    pattern: CinematicPattern
    adaptation_rules: tuple[Text, ...] = ()
    tags: tuple[Text, ...] = ()
    provenance: Provenance
    validation: PatternValidation
    notes: tuple[Text, ...] = ()


class CinematicLanguageRef(ContractModel):
    asset_id: Text
    content_fingerprint: Hash
    applied_purpose: Text


class MusicRights(ContractModel):
    source: Text | None = None
    license: Text | None = None
    attribution: str | None = None
    commercial_use: bool | None = None
    status: Literal['UNKNOWN', 'VERIFIED', 'RESTRICTED'] = 'UNKNOWN'

    def allows_production(self) -> bool:
        return (self.status == 'VERIFIED' and self.commercial_use is True
                and bool(self.source) and bool(self.license)
                and self.source != 'UNKNOWN' and self.license != 'UNKNOWN'
                and self.attribution is not None)


class MusicMedia(ContractModel):
    media_id: Text
    source_ref: Text
    content_hash: Hash


class Energy(ContractModel):
    start: Text | None = None
    middle: Text | None = None
    end: Text | None = None


class Tempo(ContractModel):
    bpm: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    free_tempo: bool | None = None


class DialogueCompatibility(ContractModel):
    suitable_under_dialogue: bool | None = None
    density: Text | None = None


class MusicUsage(ContractModel):
    loopable: bool | None = None
    preferred_entry: Text | None = None
    preferred_exit: Text | None = None


class BgmContent(ContractModel):
    creative_kind: Literal['MUSIC'] = 'MUSIC'
    role: Literal['BGM'] = 'BGM'
    title: Text
    narrative_functions: tuple[Text, ...] = ()
    mood: tuple[Text, ...] = ()
    energy: Energy = Field(default_factory=Energy)
    instrumentation: tuple[Text, ...] | None = None
    tempo: Tempo = Field(default_factory=Tempo)
    dialogue_compatibility: DialogueCompatibility = Field(default_factory=DialogueCompatibility)
    usage: MusicUsage = Field(default_factory=MusicUsage)
    duration: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    rights: MusicRights
    original_source: Text
    media: MusicMedia | None = None
    tags: tuple[Text, ...] = ()
    production_eligible: bool = False

    @model_validator(mode='after')
    def production_gate(self) -> Self:
        if self.production_eligible and (not self.media or not self.rights.allows_production()):
            raise ValueError('BGM production requires Media and verified commercial rights')
        return self


class BgmSelection(ContractModel):
    asset_id: Text
    asset_fingerprint: Hash
    media_id: Text
    content_hash: Hash
    selected_range: tuple[float, float]
    reason: Text

    @model_validator(mode='after')
    def valid_range(self) -> Self:
        import math
        a, b = self.selected_range
        if not all(math.isfinite(x) for x in (a, b)) or not 0 <= a < b:
            raise ValueError('Invalid BGM source range')
        return self
