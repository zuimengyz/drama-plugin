"""The sole Target provider execution owner, plus five domain capabilities.

Runtime owns progression; this owner owns operations/reconciliation. Provider
transports see approved execution artifacts only. Intake retries never call submit.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.execution.audio import AudioConsumer, finish_av, render_audio
from drama_plugin.execution.contracts import (
    AVDerivative, AudioExecution, CreativeMediaReview, ExecutionOperation, FinishingRecipe,
    MediaBinding, MediaIdentity, OperationState, ProviderAttempt, ProviderReceipt,
    ProviderRequest, RequestReference, ReviewedAVCandidate, TechnicalMediaReview,
)
from drama_plugin.execution.media import LocalMediaStore, inspect, probe_intake_bytes
from drama_plugin.execution.review import CreativeReviewer
from drama_plugin.execution.store import ExecutionStore, OperationCheckpoint
from drama_plugin.execution.transport import (
    CapabilityAbsent, DefinitelyNotSubmitted, IntakeTransient, ProviderTransport, serialize_request,
)
from drama_plugin.generation.contracts import AudioExecutionPlan, DerivedArtifact, FinalPromptArtifact, GenerationPreparation
from drama_plugin.governance.contracts import GateCode, GateEffect, GateFinding
from drama_plugin.governance.governor import GateGovernor
from drama_plugin.persistence.stores import DurableGateFindingStore
from drama_plugin.production.references import ReferenceExecutionBinding
from drama_plugin.production.contracts import ProductionPackage
from drama_plugin.runtime.capabilities import TargetCapability
from drama_plugin.runtime.contracts import ArtifactReference, CapabilityInput, CapabilityResult, ResultStatus

EXECUTE = "execution.provider:v1"
INTAKE = "execution.media_intake:v1"
REVIEW = "execution.media_review:v1"
AUDIO = "execution.audio:v1"
FINISH = "execution.av_candidate:v1"
D = TypeVar("D", bound=DerivedArtifact)


class ExecutionScopeMismatch(ValueError):
    """HS1: scope or approved mode differs before any side effect."""


class TargetExecution:
    """Durable single-host execution owner. First-round transport is offline-only."""

    def __init__(self, store: ExecutionStore, media: LocalMediaStore,
                 governor: GateGovernor, findings: DurableGateFindingStore, *,
                 transports: Mapping[str, ProviderTransport] | None = None,
                 reviewer: CreativeReviewer | None = None, audio: AudioConsumer | None = None):
        self.store, self.media, self.governor, self.findings = store, media, governor, findings
        self.transports = dict(transports or {})
        self.reviewer, self.audio = reviewer, audio

    def derived(self, ref: ArtifactReference, model: type[D]) -> D:
        if ref.owner != model.owner or ref.version != 1:
            raise ValueError("Approved execution artifact type mismatch")
        body, _, fingerprint = self.store.ledger.get_artifact(model.owner, ref)
        item = model.model_validate(body)
        if item.artifact_reference() != ref or item.fingerprint != fingerprint:
            raise ValueError("Approved execution artifact identity mismatch")
        return item

    def _govern(self, inputs: CapabilityInput, codes: tuple[GateCode, ...], evidence: ArtifactReference,
                *, owner: str = "target-execution", wait: bool = False) -> CapabilityResult | None:
        run = self.store.ledger.load_run(inputs.run_id)
        package = self.derived(self.store.inputs(run.run_id).preparation_ref, GenerationPreparation).source_package_ref
        decision = self.governor.govern(tuple(GateFinding.classified(code, owner=owner,
            scope=run.scope, evidence_ref=evidence, required=True) for code in codes),
            scope=run.scope, mode=run.mode, package_ref=package)
        ref = self.findings.put_decision(decision, run_id=run.run_id)
        if decision.effect == GateEffect.CONTINUE:
            return None
        if wait or decision.effect in {GateEffect.CAPABILITY_ABSENT, GateEffect.REVIEW_REQUIRED, GateEffect.WAIT_USER}:
            return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL, artifact_refs=(ref,),
                external_ref=ArtifactReference(owner=owner, artifact_ref=evidence.artifact_ref, version=evidence.version))
        return CapabilityResult(status=ResultStatus.FAILED, code=decision.effect.value, artifact_refs=(ref,))

    def _absence(self, inputs: CapabilityInput, ref: ArtifactReference, owner: str) -> CapabilityResult:
        result = self._govern(inputs, (GateCode.CAPABILITY_NOT_IMPLEMENTED,), ref, owner=owner, wait=True)
        assert result is not None
        return result

    def _approved(self, inputs: CapabilityInput) -> tuple[ExecutionOperation, ProviderRequest, FinishingRecipe]:
        bound = self.store.inputs(inputs.run_id)
        run = self.store.ledger.load_run(inputs.run_id)
        if run.scope != inputs.scope:
            raise ExecutionScopeMismatch("Capability Run scope mismatch")
        preparation = self.derived(bound.preparation_ref, GenerationPreparation)
        final = self.derived(preparation.final_prompt_ref, FinalPromptArtifact)
        plan = self.derived(preparation.audio_plan_ref, AudioExecutionPlan)
        recipe = self.store.get(bound.recipe_ref, FinishingRecipe)
        package_body, package_scope, _ = self.store.ledger.get_artifact("production-package", preparation.source_package_ref)
        package = ProductionPackage.model_validate(package_body)
        if (package_scope != run.scope or package.boundary.mode != run.mode or
                plan.scope != run.scope or recipe.scope != run.scope or
                recipe.run_id != run.run_id or recipe.preparation_ref != bound.preparation_ref or
                recipe.audio_plan_ref != preparation.audio_plan_ref or
                recipe.source_package_ref != preparation.source_package_ref or
                final.source_package_ref != preparation.source_package_ref or
                plan.source_package_ref != preparation.source_package_ref or preparation.task != final.task):
            raise ExecutionScopeMismatch("Approved artifacts cross Package/Shot/task/mode")
        references: list[RequestReference] = []
        for ref in final.execution_reference_refs:
            pointer = ArtifactReference(owner=ref.owner.value, artifact_ref=ref.artifact_ref, version=ref.version)
            body, scope, fingerprint = self.store.ledger.get_artifact("reference-execution-binding", pointer)
            binding = ReferenceExecutionBinding.model_validate(body)
            if scope != run.scope or fingerprint != ref.fingerprint or binding.source().reference() != ref:
                raise ValueError("Reference binding identity mismatch")
            references.append(RequestReference(binding_ref=ref, media_id=binding.media.media_id,
                content_hash=binding.media.content_hash, role=binding.role))
        roles = {r.role for r in references}
        if final.task.input_mode == "image_to_video" and "FIRST_FRAME" not in roles:
            raise ValueError("Approved first frame is absent")
        if final.task.input_mode == "first_last_frame" and not {"FIRST_FRAME", "LAST_FRAME"} <= roles:
            raise ValueError("Approved endpoints are absent")
        if final.task.input_mode == "reference" and not references:
            raise ValueError("Approved references are absent")
        operation = ExecutionOperation.seal(scope=run.scope, run_id=run.run_id,
            source_package_ref=preparation.source_package_ref, preparation_ref=bound.preparation_ref,
            final_prompt_ref=preparation.final_prompt_ref, audio_plan_ref=preparation.audio_plan_ref,
            reference_bindings=final.execution_reference_refs, model=final.task.target_model,
            route=bound.route, authorization=bound.authorization)
        request = ProviderRequest(operation_ref=operation.artifact_reference(), model=operation.model,
            input_mode=final.task.input_mode, prompt_text=final.prompt_text, duration_ms=plan.duration_ms,
            native_audio=final.task.native_audio, references=tuple(references))
        serialize_request(request)
        return operation, request, recipe

    def reserve(self, inputs: CapabilityInput) -> OperationCheckpoint:
        """Persist claimable intent. No transport invocation; safe crash boundary A."""
        operation, request, _ = self._approved(inputs)
        transport = self.transports.get(operation.route)
        # The bound route is the provider identity, including when capability is
        # initially absent. Registering capability later cannot mint a new attempt.
        provider = operation.route
        attempt = ProviderAttempt.seal(scope=operation.scope, run_id=operation.run_id,
            source_package_ref=operation.source_package_ref, operation_ref=operation.artifact_reference(),
            provider=provider, request_fingerprint=sha256_canonical(request),
            client_identity=sha256_canonical([operation.artifact_reference().model_dump(mode="json", by_alias=True), provider, 1]))
        return self.store.reserve(operation, attempt)

    async def execute(self, inputs: CapabilityInput) -> CapabilityResult:
        async with self.store.lock(inputs.run_id):
            try:
                operation, request, _ = self._approved(inputs)
            except ExecutionScopeMismatch:
                bound = self.store.inputs(inputs.run_id)
                rejected = self._govern(inputs, (GateCode.PACKAGE_SCOPE_MISMATCH,), bound.preparation_ref)
                assert rejected is not None
                return rejected
            except (ValueError, KeyError):
                bound = self.store.inputs(inputs.run_id)
                rejected = self._govern(inputs, (GateCode.REQUEST_INPUT_MISSING,), bound.preparation_ref)
                assert rejected is not None
                return rejected
            # Route/provider identity is persisted in the attempt before dispatch.
            checkpoint = self.reserve(inputs)
            op_ref = checkpoint.operation_ref
            attempt = self.store.get(checkpoint.attempt_ref, ProviderAttempt)
            if checkpoint.state == OperationState.SUCCEEDED:
                assert checkpoint.receipt_ref is not None
                return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(op_ref, checkpoint.receipt_ref))
            if checkpoint.state == OperationState.FAILED:
                return CapabilityResult(status=ResultStatus.FAILED, code="PROVIDER_DEFINITE_FAILURE", artifact_refs=(op_ref,))
            transport = self.transports.get(operation.route)
            if transport is None or not transport.offline:
                return self._absence(inputs, op_ref, "provider-capability")
            if transport.provider != attempt.provider:
                mismatch = self._govern(inputs, (GateCode.OPERATION_IDENTITY_MISMATCH,), op_ref,
                                        owner="operation-reconciliation", wait=True)
                assert mismatch is not None
                return mismatch
            if checkpoint.state == OperationState.RESERVED:
                codes: list[GateCode] = []
                auth = operation.authorization
                if not auth.authorized:
                    codes.append(GateCode.COST_UNAUTHORIZED)
                if auth.estimated_cost_microunits > auth.budget_microunits:
                    codes.append(GateCode.BUDGET_EXCEEDED)
                # All E1 proof transports are costless, even with live env keys.
                if auth.estimated_cost_microunits != 0:
                    codes.append(GateCode.REQUEST_UNSUPPORTED)
                governed = self._govern(inputs, tuple(codes), op_ref)
                if governed is not None:
                    return governed
                if not self.store.claim_dispatch(op_ref):
                    return self._absence(inputs, op_ref, "operation-reconciliation")
                try:
                    receipt = await transport.submit(operation, attempt, request)
                except DefinitelyNotSubmitted:
                    self.store.definite_not_submitted(op_ref)
                    return CapabilityResult(status=ResultStatus.FAILED, code="DEFINITELY_NOT_SUBMITTED", artifact_refs=(op_ref,))
                except BaseException as error:
                    self.store.unknown(op_ref)
                    if not isinstance(error, Exception):
                        raise
                    receipt = None
            else:
                # SUBMITTING restored after crash is possibly sent. Never claim again.
                if checkpoint.state == OperationState.SUBMITTING:
                    self.store.unknown(op_ref)
                previous = self.store.get(checkpoint.receipt_ref, ProviderReceipt) if checkpoint.receipt_ref else None
                try:
                    receipt = await transport.query(operation, attempt, previous)
                except Exception:
                    self.store.unknown(op_ref)
                    receipt = None
            if receipt is None:
                waiting = self._govern(inputs, (GateCode.SUBMISSION_UNCERTAIN,), op_ref,
                                       owner="operation-reconciliation", wait=True)
                assert waiting is not None
                return waiting
            try:
                receipt_ref = self.store.receipt(op_ref, receipt)
            except ValueError:
                self.store.unknown(op_ref)
                waiting = self._govern(inputs, (GateCode.OPERATION_IDENTITY_MISMATCH,), op_ref,
                                       owner="operation-reconciliation", wait=True)
                assert waiting is not None
                return waiting
            if receipt.state == "RUNNING":
                return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL, artifact_refs=(op_ref, receipt_ref), external_ref=op_ref)
            if receipt.state == "FAILED":
                return CapabilityResult(status=ResultStatus.FAILED, code="PROVIDER_DEFINITE_FAILURE", artifact_refs=(op_ref, receipt_ref))
            return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(op_ref, receipt_ref))

    def _completed(self, inputs: CapabilityInput) -> tuple[ExecutionOperation, OperationCheckpoint, FinishingRecipe]:
        operation, _, recipe = self._approved(inputs)
        checkpoint = self.store.checkpoint(operation.artifact_reference())
        if checkpoint.state != OperationState.SUCCEEDED or checkpoint.receipt_ref is None:
            raise ValueError("Provider result is not confirmed successful")
        return operation, checkpoint, recipe

    async def intake(self, inputs: CapabilityInput) -> CapabilityResult:
        async with self.store.lock(inputs.run_id):
            operation, checkpoint, _ = self._completed(inputs)
            if checkpoint.progress.video_ref:
                return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(checkpoint.progress.video_ref,))
            assert checkpoint.receipt_ref is not None
            receipt = self.store.get(checkpoint.receipt_ref, ProviderReceipt)
            assert receipt.result is not None
            transport = self.transports.get(operation.route)
            if transport is None or not transport.offline:
                return self._absence(inputs, checkpoint.receipt_ref, "media-intake")
            if checkpoint.progress.intake_attempts >= 3:
                return self._absence(inputs, checkpoint.receipt_ref, "media-intake-recovery")
            self.store.progress(checkpoint.operation_ref, intake_attempts=checkpoint.progress.intake_attempts + 1)
            try:
                content = await transport.obtain(receipt.result)
                probe_intake_bytes(content)
                media = self.media.retain(content, kind=receipt.result.kind, mime=receipt.result.mime,
                                          expected_hash=receipt.result.expected_hash)
            except CapabilityAbsent:
                return self._absence(inputs, checkpoint.receipt_ref, "media-probe")
            except (IntakeTransient, OSError):
                return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="MEDIA_INTAKE_TRANSIENT")
            except ValueError:
                return self._absence(inputs, checkpoint.receipt_ref, "media-result-repair")
            binding = MediaBinding.seal(scope=operation.scope, run_id=operation.run_id,
                source_package_ref=operation.source_package_ref, operation_ref=checkpoint.operation_ref,
                attempt_ref=checkpoint.attempt_ref, receipt_ref=checkpoint.receipt_ref,
                provider_result_id=receipt.result.result_id, media=media,
                final_prompt_ref=operation.final_prompt_ref, reference_bindings=operation.reference_bindings)
            ref = self.store.put(binding)
            self.store.progress(checkpoint.operation_ref, video_ref=ref)
            return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(ref,))

    def _technical(self, operation: ExecutionOperation, checkpoint: OperationCheckpoint,
                   media: MediaIdentity, recipe: FinishingRecipe, *, audio_expected: bool) -> TechnicalMediaReview:
        plan = self.derived(operation.audio_plan_ref, AudioExecutionPlan)
        observation, findings = inspect(self.media, media, duration_ms=plan.duration_ms,
            tolerance_ms=recipe.duration_tolerance_ms, audio_expected=audio_expected)
        return TechnicalMediaReview.seal(scope=operation.scope, run_id=operation.run_id,
            source_package_ref=operation.source_package_ref, operation_ref=checkpoint.operation_ref,
            attempt_ref=checkpoint.attempt_ref, media=media, outcome="FAIL" if findings else "PASS",
            observation=observation, findings=findings)

    async def _creative(self, operation: ExecutionOperation, checkpoint: OperationCheckpoint,
                        media: MediaIdentity) -> CreativeMediaReview:
        response = await self.reviewer.review(operation, media,
            mode=self.store.ledger.load_run(operation.run_id).mode) if self.reviewer else None
        outcome = response.outcome if response else "CAPABILITY_ABSENT"
        return CreativeMediaReview.seal(scope=operation.scope, run_id=operation.run_id,
            source_package_ref=operation.source_package_ref, operation_ref=checkpoint.operation_ref,
            attempt_ref=checkpoint.attempt_ref, media=media,
            reviewer=self.reviewer.identity if self.reviewer else "unavailable",
            policy_version=self.reviewer.policy_version if self.reviewer else "creative-review-unavailable-v1",
            outcome=outcome, observations=response.observations if response else (),
            adoption_recommendation={"PASS": "CANDIDATE_ONLY", "REVISE": "REVISION_REQUIRED",
                                     "CAPABILITY_ABSENT": "UNASSESSED"}[outcome])

    async def review(self, inputs: CapabilityInput) -> CapabilityResult:
        async with self.store.lock(inputs.run_id):
            operation, checkpoint, recipe = self._completed(inputs)
            progress = checkpoint.progress
            assert progress.video_ref is not None
            binding = self.store.get(progress.video_ref, MediaBinding)
            try:
                technical = self.store.get(progress.video_technical_ref, TechnicalMediaReview) if progress.video_technical_ref else self._technical(
                    operation, checkpoint, binding.media, recipe,
                    audio_expected=self.derived(operation.audio_plan_ref, AudioExecutionPlan).native_audio_policy == "REQUIRED")
                if binding.media.kind != "VIDEO":
                    technical = TechnicalMediaReview.seal(**{**technical.model_dump(exclude={"fingerprint"}),
                        "outcome": "FAIL", "findings": (*technical.findings, "RESULT_VIDEO_INCOMPATIBLE")})
            except CapabilityAbsent:
                return self._absence(inputs, progress.video_ref, "technical-media-review")
            technical_ref = self.store.put(technical)
            self.store.progress(checkpoint.operation_ref, video_technical_ref=technical_ref)
            if technical.outcome != "PASS":
                return self._absence(inputs, technical_ref, "media-result-repair")
            try:
                creative = self.store.get(progress.video_creative_ref, CreativeMediaReview) if progress.video_creative_ref else await self._creative(operation, checkpoint, binding.media)
            except CapabilityAbsent:
                return self._absence(inputs, progress.video_ref, "creative-media-review")
            creative_ref = self.store.put(creative)
            # Absence is retained evidence, but not a completed review checkpoint.
            if creative.outcome != "CAPABILITY_ABSENT":
                self.store.progress(checkpoint.operation_ref, video_creative_ref=creative_ref)
            if creative.outcome != "PASS":
                owner = creative.observations[0].owner if creative.observations else "creative-media-review"
                return self._absence(inputs, creative_ref, owner)
            return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(technical_ref, creative_ref))

    async def execute_audio(self, inputs: CapabilityInput) -> CapabilityResult:
        async with self.store.lock(inputs.run_id):
            operation, checkpoint, recipe = self._completed(inputs)
            progress = checkpoint.progress
            assert progress.video_ref and progress.video_technical_ref and progress.video_creative_ref
            if self.store.get(progress.video_technical_ref, TechnicalMediaReview).outcome != "PASS" or self.store.get(progress.video_creative_ref, CreativeMediaReview).outcome != "PASS":
                return self._absence(inputs, progress.video_ref, "review-revision")
            video = self.store.get(progress.video_ref, MediaBinding).media
            if not progress.audio_ref:
                if self.audio is None:
                    return self._absence(inputs, operation.audio_plan_ref, "target-audio-consumer")
                plan = self.derived(operation.audio_plan_ref, AudioExecutionPlan)
                try:
                    media, timings = render_audio(self.audio, plan, recipe, video, self.media)
                except CapabilityAbsent:
                    return self._absence(inputs, operation.audio_plan_ref, "target-audio-consumer")
                except ValueError:
                    return self._absence(inputs, operation.audio_plan_ref, "audio-design-revision")
                audio = AudioExecution.seal(scope=operation.scope, run_id=operation.run_id,
                    source_package_ref=operation.source_package_ref, operation_ref=checkpoint.operation_ref,
                    attempt_ref=checkpoint.attempt_ref, audio_plan_ref=operation.audio_plan_ref,
                    recipe_ref=recipe.artifact_reference(), media=media,
                    parent_media=(video, *(p.media for p in (*recipe.placements, *recipe.bed_placements))),
                    timings=timings, subtitle_status="TIMED_PREPARATION" if timings and all(
                        t.spoken_content_id for t in timings) else "UNTIMED")
                audio_ref = self.store.put(audio)
                progress = self.store.progress(checkpoint.operation_ref, audio_ref=audio_ref)
            assert progress.audio_ref
            audio = self.store.get(progress.audio_ref, AudioExecution)
            try:
                qa = self.store.get(progress.audio_technical_ref, TechnicalMediaReview) if progress.audio_technical_ref else self._technical(
                    operation, checkpoint, audio.media, recipe, audio_expected=True)
            except CapabilityAbsent:
                return self._absence(inputs, progress.audio_ref, "technical-media-review")
            qa_ref = self.store.put(qa)
            self.store.progress(checkpoint.operation_ref, audio_technical_ref=qa_ref)
            if qa.outcome != "PASS":
                return self._absence(inputs, qa_ref, "audio-result-repair")
            return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(progress.audio_ref, qa_ref))

    async def finish(self, inputs: CapabilityInput) -> CapabilityResult:
        async with self.store.lock(inputs.run_id):
            operation, checkpoint, recipe = self._completed(inputs)
            progress = checkpoint.progress
            if progress.candidate_ref:
                return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(progress.candidate_ref,))
            assert progress.video_ref and progress.audio_ref and progress.audio_technical_ref
            video = self.store.get(progress.video_ref, MediaBinding).media
            audio = self.store.get(progress.audio_ref, AudioExecution)
            if self.store.get(progress.audio_technical_ref, TechnicalMediaReview).outcome != "PASS":
                return self._absence(inputs, progress.audio_technical_ref, "audio-result-repair")
            if not progress.av_ref:
                try:
                    media = finish_av(video, audio.media, self.media)
                except CapabilityAbsent:
                    return self._absence(inputs, progress.audio_ref, "av-finishing")
                derivative = AVDerivative.seal(scope=operation.scope, run_id=operation.run_id,
                    source_package_ref=operation.source_package_ref, operation_ref=checkpoint.operation_ref,
                    attempt_ref=checkpoint.attempt_ref, recipe_ref=recipe.artifact_reference(),
                    audio_execution_ref=progress.audio_ref, media=media, parent_media=(video, audio.media))
                progress = self.store.progress(checkpoint.operation_ref, av_ref=self.store.put(derivative))
            assert progress.av_ref
            derivative = self.store.get(progress.av_ref, AVDerivative)
            try:
                technical = self.store.get(progress.av_technical_ref, TechnicalMediaReview) if progress.av_technical_ref else self._technical(
                    operation, checkpoint, derivative.media, recipe, audio_expected=True)
            except CapabilityAbsent:
                return self._absence(inputs, progress.av_ref, "technical-media-review")
            technical_ref = self.store.put(technical)
            progress = self.store.progress(checkpoint.operation_ref, av_technical_ref=technical_ref)
            if technical.outcome != "PASS":
                return self._absence(inputs, technical_ref, "av-result-repair")
            creative = self.store.get(progress.av_creative_ref, CreativeMediaReview) if progress.av_creative_ref else await self._creative(operation, checkpoint, derivative.media)
            creative_ref = self.store.put(creative)
            if creative.outcome != "CAPABILITY_ABSENT":
                progress = self.store.progress(checkpoint.operation_ref, av_creative_ref=creative_ref)
            if creative.outcome != "PASS":
                return self._absence(inputs, creative_ref, creative.observations[0].owner if creative.observations else "creative-media-review")
            assert progress.video_technical_ref and progress.video_creative_ref and progress.audio_ref and progress.audio_technical_ref
            candidate = ReviewedAVCandidate.seal(scope=operation.scope, run_id=operation.run_id,
                source_package_ref=operation.source_package_ref, operation_ref=checkpoint.operation_ref,
                attempt_ref=checkpoint.attempt_ref, video_binding_ref=progress.video_ref,
                video_technical_ref=progress.video_technical_ref, video_creative_ref=progress.video_creative_ref,
                audio_execution_ref=progress.audio_ref, audio_technical_ref=progress.audio_technical_ref,
                av_derivative_ref=progress.av_ref, av_technical_ref=technical_ref, av_creative_ref=creative_ref,
                media=derivative.media)
            candidate_ref = self.store.put(candidate)
            self.store.progress(checkpoint.operation_ref, candidate_ref=candidate_ref)
            return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(candidate_ref,))

    def registrations(self) -> dict[str, TargetCapability]:
        return {EXECUTE: TargetCapability(self.execute, replay_safe=True),
                INTAKE: TargetCapability(self.intake, replay_safe=True), REVIEW: TargetCapability(self.review, replay_safe=True),
                AUDIO: TargetCapability(self.execute_audio, replay_safe=True), FINISH: TargetCapability(self.finish, replay_safe=True)}
