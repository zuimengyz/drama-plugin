"""Read-only schema for retained pre-retirement compression artifacts.

No authoring validation, compilation, registration entry or prompt transformation
is provided. Frozen ledger records retain their original hashes and references.
"""
from __future__ import annotations
from typing import Annotated
from pydantic import Field, StrictInt, StringConstraints
from drama_plugin.contracts.creative_asset import Hash
from drama_plugin.generation.contracts import DerivedArtifact
from drama_plugin.runtime.contracts import RuntimeContract, ArtifactReference

Span = tuple[Annotated[StrictInt, Field(ge=0)], Annotated[StrictInt, Field(gt=0)]]


class ExpressionMapping(RuntimeContract):
    source_span: Span
    target_spans: tuple[Span, ...] = Field(min_length=1, max_length=16)
    judgment: Annotated[str, StringConstraints(min_length=1, max_length=1000)]


class PromptExpression(DerivedArtifact):
    owner = 'prompt-expression'
    baseline_final_ref: ArtifactReference
    baseline_text_sha256: Hash
    baseline_task_fingerprint: Hash
    prompt_text: Annotated[str, StringConstraints(min_length=1, max_length=20000)]
    mappings: tuple[ExpressionMapping, ...] = Field(min_length=1, max_length=256)
    reviewer: Annotated[str, StringConstraints(min_length=1, max_length=300)]
    review_basis: Annotated[str, StringConstraints(min_length=1, max_length=3000)]
    excluded_local_labels: tuple[Annotated[str, StringConstraints(min_length=1, max_length=200)], ...] = Field(default=(), max_length=128)
