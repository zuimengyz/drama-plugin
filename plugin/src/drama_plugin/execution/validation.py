"""Typed lineage admission at the Ledger boundary, including exact review targets."""
from __future__ import annotations

from collections.abc import Callable

from drama_plugin.execution.contracts import (
    AVDerivative, AudioExecution, CreativeMediaReview, ExecutionArtifact, ExecutionOperation,
    FinishingRecipe, MediaBinding, ProviderAttempt, ProviderReceipt, ReviewedAVCandidate,
    TechnicalMediaReview,
)
from drama_plugin.generation.contracts import AudioExecutionPlan, DerivedArtifact, FinalPromptArtifact, GenerationPreparation
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeContract

LINK_TYPES: dict[str, type[RuntimeContract]] = {
    "preparation_ref": GenerationPreparation, "final_prompt_ref": FinalPromptArtifact,
    "audio_plan_ref": AudioExecutionPlan, "operation_ref": ExecutionOperation,
    "attempt_ref": ProviderAttempt, "receipt_ref": ProviderReceipt,
    "recipe_ref": FinishingRecipe, "audio_execution_ref": AudioExecution,
    "video_binding_ref": MediaBinding, "video_technical_ref": TechnicalMediaReview,
    "video_creative_ref": CreativeMediaReview, "audio_technical_ref": TechnicalMediaReview,
    "av_derivative_ref": AVDerivative, "av_technical_ref": TechnicalMediaReview,
    "av_creative_ref": CreativeMediaReview,
}


def validate_links(item: ExecutionArtifact, resolve: Callable[[ArtifactReference], RuntimeContract]) -> None:
    parents: dict[str, RuntimeContract] = {}
    for field, model in LINK_TYPES.items():
        ref = getattr(item, field, None)
        if not isinstance(ref, ArtifactReference):
            continue
        parent = resolve(ref)
        if type(parent) is not model or not isinstance(parent, DerivedArtifact):
            raise ValueError("Execution lineage type mismatch")
        if parent.source_package_ref != item.source_package_ref or parent.artifact_reference() != ref:
            raise ValueError("Execution lineage Package/identity mismatch")
        if isinstance(parent, ExecutionArtifact) and (parent.run_id != item.run_id or parent.scope != item.scope):
            raise ValueError("Execution lineage Run/Shot mismatch")
        parents[field] = parent
    operation = parents.get("operation_ref")
    attempt = parents.get("attempt_ref")
    recipe = parents.get("recipe_ref")
    if isinstance(operation, ExecutionOperation):
        if isinstance(attempt, ProviderAttempt) and attempt.operation_ref != operation.artifact_reference():
            raise ValueError("Execution attempt belongs to another logical operation")
        if isinstance(recipe, FinishingRecipe) and (recipe.preparation_ref != operation.preparation_ref or
                recipe.audio_plan_ref != operation.audio_plan_ref):
            raise ValueError("Execution recipe/preparation mismatch")
    if isinstance(item, ExecutionOperation):
        preparation = parents["preparation_ref"]
        final = parents["final_prompt_ref"]
        assert isinstance(preparation, GenerationPreparation) and isinstance(final, FinalPromptArtifact)
        if (preparation.final_prompt_ref != item.final_prompt_ref or preparation.audio_plan_ref != item.audio_plan_ref or
                not final.matches_task(preparation.task) or final.task.target_model != item.model or
                final.execution_reference_refs != item.reference_bindings):
            raise ValueError("Operation changes approved execution inputs")
    if isinstance(item, FinishingRecipe):
        preparation = parents["preparation_ref"]
        assert isinstance(preparation, GenerationPreparation)
        if preparation.audio_plan_ref != item.audio_plan_ref:
            raise ValueError("Recipe changes approved audio plan")
    if isinstance(item, ProviderReceipt):
        assert isinstance(attempt, ProviderAttempt)
        if (item.provider, item.client_identity, item.request_fingerprint) != (
                attempt.provider, attempt.client_identity, attempt.request_fingerprint):
            raise ValueError("Receipt changes attempt identity/request")
    if isinstance(item, MediaBinding):
        receipt = parents["receipt_ref"]
        assert isinstance(receipt, ProviderReceipt) and isinstance(operation, ExecutionOperation)
        if (receipt.state != "SUCCEEDED" or receipt.result is None or receipt.result.result_id != item.provider_result_id or
                receipt.operation_ref != item.operation_ref or receipt.attempt_ref != item.attempt_ref or
                item.final_prompt_ref != operation.final_prompt_ref or item.reference_bindings != operation.reference_bindings or
                receipt.result.expected_hash is not None and receipt.result.expected_hash != item.media.content_hash):
            raise ValueError("Media result/provenance mismatch")
    if isinstance(item, AudioExecution):
        assert isinstance(recipe, FinishingRecipe)
        if item.audio_plan_ref != recipe.audio_plan_ref:
            raise ValueError("Audio result changes approved plan")
    if isinstance(item, AVDerivative):
        audio = parents["audio_execution_ref"]
        assert isinstance(audio, AudioExecution)
        if (audio.operation_ref != item.operation_ref or audio.attempt_ref != item.attempt_ref or
                audio.recipe_ref != item.recipe_ref or item.parent_media[1] != audio.media or
                item.parent_media[0] != audio.parent_media[0]):
            raise ValueError("AV derivative parent identity mismatch")
    if isinstance(item, ReviewedAVCandidate):
        video = parents["video_binding_ref"]
        audio = parents["audio_execution_ref"]
        av = parents["av_derivative_ref"]
        assert isinstance(video, MediaBinding) and isinstance(audio, AudioExecution) and isinstance(av, AVDerivative)
        if (item.media != av.media or av.parent_media != (video.media, audio.media) or
                av.audio_execution_ref != item.audio_execution_ref):
            raise ValueError("Candidate media/derivative mismatch")
        for field, expected_media in (("video_technical_ref", video.media), ("video_creative_ref", video.media),
                                      ("audio_technical_ref", audio.media), ("av_technical_ref", av.media),
                                      ("av_creative_ref", av.media)):
            review = parents[field]
            assert isinstance(review, (TechnicalMediaReview, CreativeMediaReview))
            if (review.media != expected_media or review.outcome != "PASS" or
                    review.operation_ref != item.operation_ref or review.attempt_ref != item.attempt_ref):
                raise ValueError("Candidate requires PASS review of its exact media/operation/attempt")
