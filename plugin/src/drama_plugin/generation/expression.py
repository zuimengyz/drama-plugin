"""Host-reviewed expression over a complete native prompt; never creative authorship.

The immutable mapping is Host evidence, not a semantic-equivalence proof. Compile
rebuilds the full baseline before accepting any transform. No provider calls here.
"""
from __future__ import annotations

import hashlib
import re
from typing import Annotated
from pydantic import Field, StrictInt, StringConstraints
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.creative_asset import Hash
from drama_plugin.generation.contracts import (
    DerivedArtifact, FinalPromptArtifact, GenerationPreparation, GenerationTask,
    PromptCoverage, CoverageStatus, AudioExecutionPlan, ExecutionDiagnostic,
)
from drama_plugin.runtime.contracts import RuntimeContract, ArtifactReference
from drama_plugin.production.contracts import SourceDomain

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


def _covered(text, spans):
    covered = bytearray(len(text))
    for a, b in spans:
        if not 0 <= a < b <= len(text):
            raise ValueError('EXPRESSION_SPAN_INVALID')
        covered[a:b] = b'\1' * (b-a)
    return all(c.isspace() or covered[i] for i, c in enumerate(text))


def validate_expression(expression, baseline, task, exact_texts=()):
    """Validate pins/spans/text invariants, not the Host's semantic judgments."""
    if (expression.source_package_ref != baseline.source_package_ref
            or expression.baseline_final_ref != baseline.artifact_reference()
            or expression.baseline_task_fingerprint != sha256_canonical(task)
            or expression.baseline_text_sha256 != hashlib.sha256(baseline.prompt_text.encode()).hexdigest()):
        raise ValueError('EXPRESSION_BASELINE_MISMATCH')
    if baseline.expression_ref:
        raise ValueError('EXPRESSION_REQUIRES_FULL_NATIVE_BASELINE')
    if not _covered(baseline.prompt_text, [m.source_span for m in expression.mappings]):
        raise ValueError('EXPRESSION_SOURCE_UNMAPPED')
    if not _covered(expression.prompt_text, [s for m in expression.mappings for s in m.target_spans]):
        raise ValueError('EXPRESSION_TARGET_UNMAPPED')
    # Exact bound provider image/video/audio tokens cannot become local IDs.
    pattern = r'@(?:图片|视频|音频)\d+'
    if set(re.findall(pattern, baseline.prompt_text)) != set(re.findall(pattern, expression.prompt_text)):
        raise ValueError('EXPRESSION_REFERENCE_TOKENS_CHANGED')
    for label in expression.excluded_local_labels:
        if re.search(r'(?<![A-Za-z0-9_])' + re.escape(label) + r'(?![A-Za-z0-9_])', expression.prompt_text):
            raise ValueError('EXPRESSION_LOCAL_LABEL_REMAINS')
    # Speech remains exact, in the same textual ordering; semantic timing remains Host review.
    cursor = 0
    for text in exact_texts:
        position = expression.prompt_text.find(text, cursor)
        if position < 0 or expression.prompt_text.count(text) != baseline.prompt_text.count(text):
            raise ValueError('EXPRESSION_EXACT_SPEECH_CHANGED')
        cursor = position + len(text)


async def compile_expression(compiler, package_ref, task):
    from drama_plugin.generation.compiler import CompilationResult
    from drama_plugin.generation.audio import package_scope
    package = compiler.packages.get(package_ref)
    # Always run native compilation/admission first; this retains the complete text.
    base_task = GenerationTask.model_validate(task.model_copy(update={'prompt_expression_ref': None}).model_dump())
    result = await compiler.compile(package_ref, base_task)
    if result.preparation_ref is None:
        return result
    prepared = compiler.artifacts.get(result.preparation_ref, GenerationPreparation)
    baseline = compiler.artifacts.get(prepared.final_prompt_ref, FinalPromptArtifact)
    audio = compiler.artifacts.get(prepared.audio_plan_ref, AudioExecutionPlan)
    try:
        expression = compiler.artifacts.get(task.prompt_expression_ref, PromptExpression)
        exact_texts = []
        for event in audio.speech_events:
            if event.spoken_content_id:
                value = await compiler.reader.resolver.resolve(event.source_ref)
                if not isinstance(value, dict) or not isinstance(value.get("text"), str):
                    raise ValueError("EXPRESSION_SPEECH_SOURCE_MISSING")
                exact_texts.append(value["text"])
        validate_expression(expression, baseline, base_task, exact_texts)
        original = compiler.artifacts.get(baseline.coverage_ref, PromptCoverage)
        entries = []
        for entry in original.entries:
            if entry.status != CoverageStatus.TEXT_COVERED:
                entries.append(entry)
                continue
            a, b = entry.span
            spans = [s for m in expression.mappings if m.source_span[0] < b and a < m.source_span[1] for s in m.target_spans]
            if not spans:
                raise ValueError('EXPRESSION_FACT_UNMAPPED')
            # Bounding span is explicitly HOST_MAPPED, never verbatim TEXT_COVERED.
            # Exact multi-span judgments remain in the linked expression artifact.
            entries.append(entry.model_copy(update={'status': CoverageStatus.HOST_MAPPED,
                'span': (min(s[0] for s in spans), max(s[1] for s in spans))}))
        coverage = PromptCoverage.seal(source_package_ref=package_ref, entries=tuple(entries))
        coverage_ref = compiler.artifacts.put(coverage)
        final = FinalPromptArtifact.seal(
            task=GenerationTask.model_validate(task.model_dump(exclude={'unit','profile','owners','continuation'})) if task.unit else task,
            task_fingerprint=sha256_canonical(task) if task.unit else None,
            model_family=baseline.model_family, generator_policy_fingerprint=baseline.generator_policy_fingerprint,
            prompt_text=expression.prompt_text, source_package_ref=package_ref,
            prompt_ir_fingerprint=baseline.prompt_ir_fingerprint, coverage_ref=coverage_ref,
            execution_reference_refs=baseline.execution_reference_refs,
            baseline_final_ref=baseline.artifact_reference(), expression_ref=expression.artifact_reference())
        final_ref = compiler.artifacts.put(final)
        key = sha256_canonical([package_ref.model_dump(mode='json'),task.model_dump(mode='json'),baseline.generator_policy_fingerprint])
        compiler.artifacts.register_final(key, final_ref)
        output = GenerationPreparation.seal(source_package_ref=package_ref, task=task,
            final_prompt_ref=final_ref, audio_plan_ref=prepared.audio_plan_ref)
        return CompilationResult(compiler.artifacts.put(output),result.diagnostics_ref,result.prompt_ir_ref,result.audio_plan_ref)
    except (KeyError, ValueError) as error:
        diagnostic = ExecutionDiagnostic(code='EXECUTION_REQUIRED_MISSING', owner='prompt-expression',
            domain=SourceDomain.DIRECTION, required=True)
        # Preserve a bounded diagnostic code in the existing receipt, never allow fallback submission.
        ref = compiler.artifacts.retain_diagnostics((diagnostic,), scope=package_scope(package))
        return CompilationResult(None,ref,result.prompt_ir_ref,result.audio_plan_ref)
