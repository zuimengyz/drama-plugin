"""Projection receipts, not a second story or professional decision contract."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

AtomPriority = Literal['CRITICAL', 'IMPORTANT', 'SUPPORTING', 'OPTIONAL', 'NON_PROJECTED']


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class ReferenceCoverage(Record):
    """Reviewed reference-to-existing-IR leaf mapping, stored in Canon's reference."""
    path: str = Field(min_length=1)
    source: str = Field(min_length=1)
    text_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    duty: Literal['FACE_IDENTITY', 'HAIR', 'BODY', 'COSTUME', 'SCENE', 'OBJECT']


class ReferenceBinding(Record):
    # This annotation lives inside VideoReference, hence existing Canon equality,
    # version/hash and review gates cover it. A request cannot invent coverage.
    subject_id: str | None = None
    coverage: tuple[ReferenceCoverage, ...] = ()
    must_not_carry: tuple[Literal['pose', 'lighting', 'composition', 'expression'], ...] = ()


class PromptAtom(Record):
    obligation_id: str
    path: str
    source: str
    owner: str
    scope: str
    subject: tuple[str, ...]
    target: str
    # Opaque complete propositions preserve unparsed targets, negations and time.
    # Uncertainty is KEEP, never guessed NLP equivalence.
    relation_action_state: str
    temporal_meaning: str
    negation: str
    reference_duty: str
    priority: AtomPriority
    required: bool
    text: str


class CoverageReceipt(Record):
    obligation_id: str
    status: Literal['TEXT_COVERED', 'REFERENCE_COVERED', 'MEDIA_COVERED']
    span: tuple[int, int]
    input_tag: str | None = None
    input_hash: str | None = None
    input_version: str | None = None
    duty: str | None = None


class AudioBinding(Record):
    """Exact IR audio leaf, with its already approved speaker and language."""
    path: str
    source: str
    text_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    kind: Literal['DIALOGUE', 'BGM', 'SFX']
    speaker: str | None = None
    language: str | None = None
    timing: str | None = None


class ProjectionAnnotations(Record):
    # No alternate creative text is accepted here. The existing IR owns all text.
    audio: tuple[AudioBinding, ...] = ()
    camera_conflict: bool = False
    approved_compound_camera_source: str | None = None
