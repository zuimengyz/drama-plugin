"""The sole Target provider execution owner, plus five domain capabilities.

Runtime owns progression; this owner owns operations/reconciliation. Provider
transports see approved execution artifacts only. Intake retries never call submit.
"""
from __future__ import annotations
from drama_plugin.generation.policy import MEDIA_WORKFLOWS, media_cursor

from collections.abc import Mapping, Callable, Awaitable
import time
from typing import TypeVar

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.execution.audio import AudioConsumer, finish_av, render_audio
from drama_plugin.execution.contracts import (
    AVDerivative, AudioExecution, CreativeMediaReview, ExecutionOperation, FinishingRecipe,
    MediaBinding, MediaIdentity, OperationState, ProviderAttempt, ProviderReceipt,
    ProviderRequest, RequestReference, ReviewedAVCandidate, TechnicalMediaReview,
)
from drama_plugin.execution.media import LocalMediaStore, inspect, probe_intake_bytes
from drama_plugin.execution.review import CreativeReviewer, HumanReviewer, ReviewResponse
from drama_plugin.execution.store import ExecutionStore, OperationCheckpoint, ExecutionIntegrityError
from drama_plugin.execution.transport import (
    CapabilityAbsent, DefinitelyNotSubmitted, IntakeTransient, PossiblySubmitted, ProviderTransport, serialize_request,
)
from drama_plugin.generation.contracts import AudioExecutionPlan, DerivedArtifact, FinalPromptArtifact, GenerationPreparation, ExecutionDiagnostic
from drama_plugin.generation.operation import OperationResolver
from drama_plugin.governance.contracts import GateCode, GateEffect, GateFinding
from drama_plugin.governance.governor import GateGovernor
from drama_plugin.persistence.stores import DurableGateFindingStore, DurableGenerationArtifactStore
from drama_plugin.production.references import ReferenceExecutionBinding
from drama_plugin.production.contracts import ProductionPackage, SourceDomain
from drama_plugin.runtime.capabilities import TargetCapability
from drama_plugin.runtime.contracts import (ArtifactReference, CapabilityInput, CapabilityResult, ResultStatus,
    RuntimeState, RecoveryClass, UserDecisionRequest, DecisionCategory, ExecutionInspection, ExecutionRevision)

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
                 reviewer: CreativeReviewer | None = None, audio: AudioConsumer | None = None,
                 operations: OperationResolver | None = None):
        self.store, self.media, self.governor, self.findings = store, media, governor, findings
        self.transports = dict(transports or {})
        self.reviewer, self.audio = reviewer, audio
        self.operations = operations

    def _diagnostic(self, inputs: CapabilityInput, code: str) -> ArtifactReference:
        return DurableGenerationArtifactStore(self.store.ledger).retain_diagnostics((ExecutionDiagnostic(
            code=code, owner="target-execution", domain=SourceDomain.REFERENCE, required=True),), scope=inputs.scope)

    def _hard(self, inputs: CapabilityInput, code: str, *refs: ArtifactReference) -> CapabilityResult:
        return CapabilityResult(status=ResultStatus.FAILED, code=code,
            recovery_class=RecoveryClass.HARD_BLOCK, artifact_refs=(*refs, self._diagnostic(inputs, code)))

    def _external(self, inputs: CapabilityInput, ref: ArtifactReference, code: str,
                  *refs: ArtifactReference) -> CapabilityResult:
        return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL, external_ref=ref,
            recovery_class=RecoveryClass.WAIT_EXTERNAL,
            artifact_refs=(*refs, self._diagnostic(inputs, code)))

    def _cost_wait(self, inputs: CapabilityInput, ref: ArtifactReference, code: str) -> CapabilityResult:
        return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL, external_ref=ref,
            recovery_class=RecoveryClass.USER_DECISION,
            user_decision=UserDecisionRequest(category=DecisionCategory.COST_APPROVAL,
                question="Approve the exact current operation and financial terms before any paid submission."),
            artifact_refs=(ref, self._diagnostic(inputs, code)))

    def _schema_diagnostics(self, inputs: CapabilityInput, error: Exception) -> tuple[ArtifactReference, ...]:
        """Only DTO-owned field names/validator codes, never remote input/body."""
        from pydantic import ValidationError
        from drama_plugin.contracts.media import Media, MediaResolveResult
        import re
        cause = error.__cause__
        if not isinstance(cause, ValidationError):
            return ()
        fields = {name for model in (Media,MediaResolveResult) for name in model.model_fields}
        fields.update(field.alias for model in (Media,MediaResolveResult) for field in model.model_fields.values() if field.alias)
        refs: list[ArtifactReference] = []
        for detail in cause.errors(include_input=False,include_context=False,include_url=False)[:8]:
            loc = detail.get("loc", ())
            path = tuple(str(part) for part in loc if isinstance(part,int) or isinstance(part,str) and part in fields)
            validator = detail["type"]
            if not isinstance(validator,str) or re.fullmatch(r"[a-z_]{1,64}",validator) is None:
                validator = "schema_validation"
            code = "FORMAL_MEDIA_DTO:" + (".".join(path[:4]) or "response") + ":" + validator
            refs.append(self._diagnostic(inputs,code))
        return tuple(refs)

    @staticmethod
    def _remote_code(error: Exception) -> str:
        from drama_plugin.exceptions import RemoteServiceError
        if isinstance(error, RemoteServiceError):
            safe_codes = {"INVALID_ARGUMENT", "UNAUTHORIZED", "NOT_FOUND", "CONFLICT", "INTERNAL_ERROR",
                "IMPORT_SOURCE_UNREADABLE", "STORAGE_ERROR", "UNRESOLVABLE_MEDIA", "CONTENT_HASH_MISMATCH", "OBJECT_CONFLICT"}
            if error.error_code in safe_codes:
                return "FORMAL_MEDIA_" + str(error.error_code)
            if error.status_code:
                return "FORMAL_MEDIA_HTTP_" + str(error.status_code)
        return "FORMAL_MEDIA_READ_TRANSIENT"

    @staticmethod
    def _remote_permanent(error: Exception) -> bool:
        from drama_plugin.exceptions import RemoteServiceError
        if isinstance(error, RemoteServiceError) and error.error_code == "STORAGE_ERROR":
            return False  # Same canonical source/claim can be queried after storage recovery.
        return isinstance(error, RemoteServiceError) and (error.status_code in {400,401,403,404,409,422}
            or error.error_code in {"INVALID_ARGUMENT", "UNAUTHORIZED", "NOT_FOUND", "CONFLICT",
                "UNRESOLVABLE_MEDIA", "CONTENT_HASH_MISMATCH", "OBJECT_CONFLICT"})

    @staticmethod
    def _capability_code(error: CapabilityAbsent, fallback: str) -> str:
        allowed = {"FORMAL_MEDIA_NATIVE_OWNER_AUTHENTICATION_ABSENT", "FORMAL_MEDIA_NATIVE_OWNER_ADAPTER_REQUIRED",
            "PROVIDER_NOT_CONFIGURED", "TARGET_HTTP_REFERENCE_SERIALIZER_ABSENT", "PROVIDER_DURATION_UNSUPPORTED",
            "PROVIDER_PROFILE_OR_PROMPT_LIMIT_UNSUPPORTED", "REQUIRED_NATIVE_AUDIO_UNSUPPORTED",
            "PROVIDER_REQUIRED_NATIVE_AUDIO_UNSUPPORTED", "TARGET_PROVIDER_SERIALIZER_ABSENT", "MEDIA_PROBE_ABSENT",
            "FORMAL_MOCK_REVIEW_FORBIDDEN"}
        code = error.args[0] if error.args else None
        return code if isinstance(code, str) and code in allowed else fallback

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

    def _approved(self, inputs: CapabilityInput) -> tuple[ExecutionOperation, ProviderRequest, FinishingRecipe | None]:
        bound = self.store.inputs(inputs.run_id)
        run = self.store.ledger.load_run(inputs.run_id)
        if run.scope != inputs.scope:
            raise ExecutionScopeMismatch("Capability Run scope mismatch")
        preparation = self.derived(bound.preparation_ref, GenerationPreparation)
        final = self.derived(preparation.final_prompt_ref, FinalPromptArtifact)
        plan = self.derived(preparation.audio_plan_ref, AudioExecutionPlan)
        recipe = self.store.get(bound.recipe_ref, FinishingRecipe) if bound.recipe_ref else None
        if recipe is None and (not preparation.task.unit or run.workflow_id not in {"package-to-reviewed-media:v1", "package-to-reviewed-media:v2"}):
            raise ExecutionScopeMismatch("Finishing requires an approved recipe")
        package_body, package_scope, _ = self.store.ledger.get_artifact("production-package", preparation.source_package_ref)
        package = ProductionPackage.model_validate(package_body)
        operation = ExecutionOperation.seal(scope=run.scope, run_id=run.run_id,
            source_package_ref=preparation.source_package_ref, preparation_ref=bound.preparation_ref,
            final_prompt_ref=preparation.final_prompt_ref, audio_plan_ref=preparation.audio_plan_ref,
            reference_bindings=final.execution_reference_refs, model=final.task.target_model,
            route=bound.route, authorization=bound.authorization)
        known_external = False
        try:
            prior = self.store.checkpoint(operation.artifact_reference())
            if prior.state not in {OperationState.RESERVED,OperationState.FAILED}:
                transport = self.transports.get(operation.route)
                prior_receipt = self.store.get(prior.receipt_ref,ProviderReceipt) if prior.receipt_ref else None
                prior_attempt = self.store.get(prior.attempt_ref,ProviderAttempt)
                known_external = transport is not None and transport.can_reconcile(prior_attempt,prior_receipt)
        except KeyError:
            pass
        if preparation.task.unit:
            if self.operations is None:
                raise ExecutionScopeMismatch("Formal operation owner resolver missing")
            try:
                self.operations.validate(package, preparation.task, require_current_profile=not known_external)
            except (KeyError, ValueError, OSError) as error:
                raise ExecutionScopeMismatch("Formal owner/profile/rights admission failed") from error
            assert preparation.task.profile
            if bound.route != preparation.task.profile.provider:
                raise ExecutionScopeMismatch("Frozen provider differs from execution route")
            if plan.duration_ms != preparation.task.profile.requested_duration_ms:
                raise ExecutionScopeMismatch("Audio plan differs from frozen operation duration")
        if (package_scope != run.scope or package.boundary.mode != run.mode or
                plan.scope != run.scope or (recipe is not None and (recipe.scope != run.scope or
                recipe.run_id != run.run_id or recipe.preparation_ref != bound.preparation_ref or
                recipe.audio_plan_ref != preparation.audio_plan_ref or
                recipe.source_package_ref != preparation.source_package_ref)) or
                final.source_package_ref != preparation.source_package_ref or
                plan.source_package_ref != preparation.source_package_ref or not final.matches_task(preparation.task)):
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
        request = ProviderRequest(operation_ref=operation.artifact_reference(), model=operation.model,
            input_mode=final.task.input_mode, prompt_text=final.prompt_text, duration_ms=plan.duration_ms,
            native_audio=final.task.native_audio, references=tuple(references), profile=preparation.task.profile)
        serialize_request(request)
        return operation, request, recipe

    def reserve(self, inputs: CapabilityInput) -> OperationCheckpoint:
        """Persist claimable intent. No transport invocation; safe crash boundary A."""
        operation, request, _ = self._approved(inputs)
        try:
            return self.store.checkpoint(operation.artifact_reference())
        except KeyError:
            pass
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
                return self._hard(inputs, "EXECUTION_SCOPE_MISMATCH", *rejected.artifact_refs)
            except (ValueError, KeyError):
                bound = self.store.inputs(inputs.run_id)
                rejected = self._govern(inputs, (GateCode.REQUEST_INPUT_MISSING,), bound.preparation_ref)
                assert rejected is not None
                return self._hard(inputs, "EXECUTION_INPUT_IDENTITY_INVALID", *rejected.artifact_refs)
            # Admission is a pure projection until the exact current financial
            # decision has passed. A renewed cost decision must not conflict with
            # an operation reserved under obsolete terms.
            op_ref = operation.artifact_reference()
            try:
                checkpoint = self.store.checkpoint(op_ref)
            except KeyError:
                checkpoint = None
            evidence = op_ref if checkpoint else operation.preparation_ref
            if checkpoint and checkpoint.state == OperationState.SUCCEEDED:
                assert checkpoint.receipt_ref is not None
                return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(op_ref, checkpoint.receipt_ref))
            if checkpoint and checkpoint.state == OperationState.FAILED:
                return self._hard(inputs, checkpoint.progress.query_last_code or "PROVIDER_DEFINITE_FAILURE", op_ref)
            transport = self.transports.get(operation.route)
            if transport is None or (not transport.offline and operation.authorization.execution_mode == "OFFLINE_ONLY"):
                governed = self._govern(inputs,(GateCode.CAPABILITY_NOT_IMPLEMENTED,),evidence,owner="provider-capability")
                assert governed is not None
                return self._hard(inputs, "PROVIDER_CAPABILITY_ABSENT", evidence,*governed.artifact_refs)
            if transport.provider != operation.route:
                mismatch = self._govern(inputs, (GateCode.OPERATION_IDENTITY_MISMATCH,), evidence,
                                        owner="operation-reconciliation", wait=True)
                assert mismatch is not None
                return self._hard(inputs, "PROVIDER_OPERATION_IDENTITY_MISMATCH", *mismatch.artifact_refs)
            from drama_plugin.execution.live_transport import TargetHttpTransport, ControlledLiveGrant, FinancialAuthorizationError
            previous = self.store.get(checkpoint.receipt_ref, ProviderReceipt) if checkpoint and checkpoint.receipt_ref else None
            if checkpoint and checkpoint.state == OperationState.SUBMITTING:
                self.store.unknown(op_ref)
                checkpoint = self.store.checkpoint(op_ref)
            if (checkpoint and checkpoint.state == OperationState.UNKNOWN
                    and not transport.can_reconcile(self.store.get(checkpoint.attempt_ref, ProviderAttempt), previous)):
                attempt = self.store.get(checkpoint.attempt_ref, ProviderAttempt)
                # Finite read recovery precedes any authorized supplementary POST.
                used = checkpoint.progress.unknown_lookup_attempts or 0
                limit = 2 * attempt.ordinal
                while used < limit:
                    used += 1
                    self.store.progress(op_ref, unknown_lookup_attempts=used)
                    try:
                        recovered = await transport.recover_unknown(operation, attempt) if isinstance(transport, TargetHttpTransport) else None
                        self.store.progress(op_ref, unknown_lookup_last_code='EXACT_ACK_RECOVERED' if recovered else 'NO_EXACT_TASK_RECOVERED')
                    except Exception:
                        recovered = None
                        self.store.progress(op_ref, unknown_lookup_last_code='TASK_LOOKUP_TRANSIENT')
                    if recovered:
                        self.store.receipt(op_ref, recovered)
                        previous = recovered
                        break
                checkpoint = self.store.checkpoint(op_ref)
                if previous is None:
                    if attempt.ordinal == 1 and isinstance(transport, TargetHttpTransport):
                        from drama_plugin.execution.live_transport import FinancialTerms
                        from drama_plugin.persistence.review import UserDecisionRecord
                        try:
                            approval_ref = ArtifactReference.model_validate(self.store.ledger.get_index('execution-recovery-authorization', operation.run_id))
                            body, scope, _ = self.store.ledger.get_artifact('user-decision', approval_ref)
                            approved = UserDecisionRecord.model_validate(body)
                            terms = FinancialTerms.model_validate(approved.financial_terms)
                            terms.validate_current()
                            if (not approved.accepted or scope != operation.scope or approved.run_id != operation.run_id
                                    or not terms.supplemental or terms.recovery_operation_ref != op_ref
                                    or terms.prior_attempt_ref != checkpoint.attempt_ref or terms.profile != request.profile
                                    or terms.wire_payload_hash != sha256_canonical(transport.approved_payload(request))):
                                raise ValueError('SUPPLEMENTAL_AUTHORIZATION_DRIFT')
                            supplement = ProviderAttempt.seal(scope=operation.scope, run_id=operation.run_id,
                                source_package_ref=operation.source_package_ref, operation_ref=op_ref,
                                provider=operation.route, request_fingerprint=sha256_canonical(request), ordinal=2,
                                client_identity=sha256_canonical([op_ref.model_dump(mode='json', by_alias=True), operation.route, 2]),
                                previous_attempt_ref=checkpoint.attempt_ref, approval_ref=approval_ref)
                            checkpoint = self.store.supplement(op_ref, supplement,
                                reserved_unknown_microunits=terms.reserved_unknown_microunits)
                        except KeyError:
                            return self._external(inputs, op_ref, 'UNKNOWN_SUBMISSION_RECOVERY_PENDING', op_ref)
                        except FinancialAuthorizationError as error:
                            return self._cost_wait(inputs, operation.preparation_ref, error.code)
                        except ValueError:
                            return self._hard(inputs, 'SUPPLEMENTAL_AUTHORIZATION_DRIFT', op_ref)
                    else:
                        return self._external(inputs, op_ref, 'UNKNOWN_SUBMISSION_RECOVERY_PENDING', op_ref)
            if checkpoint is None or checkpoint.state == OperationState.RESERVED:
                # Already dispatched tasks reconcile their exact task identity;
                # quote expiry cannot turn a safe GET into another paid POST.
                if isinstance(transport, TargetHttpTransport):
                    if transport.adapter.settings.status(transport.provider) != "READY":
                        return self._hard(inputs,"PROVIDER_NOT_CONFIGURED",evidence)
                    try:
                        transport.approved_payload(request)
                    except CapabilityAbsent as error:
                        return self._hard(inputs, self._capability_code(error,"REQUEST_UNSUPPORTED"), evidence)
                    except (ValueError, KeyError):
                        return self._hard(inputs, "PROVIDER_FROZEN_PROFILE_MISMATCH", evidence)
                codes: list[GateCode] = []
                financial_code = "EXACT_COST_AUTHORIZATION_REQUIRED"
                grant: ControlledLiveGrant | None = None
                auth = operation.authorization
                if not auth.authorized:
                    codes.append(GateCode.COST_UNAUTHORIZED)
                if auth.estimated_cost_microunits > auth.budget_microunits:
                    codes.append(GateCode.BUDGET_EXCEEDED)
                if transport.offline and auth.estimated_cost_microunits != 0:
                    codes.append(GateCode.REQUEST_UNSUPPORTED)
                if not transport.offline:
                    if not isinstance(transport, TargetHttpTransport) or auth.execution_mode != "CONTROLLED_LIVE":
                        codes.append(GateCode.COST_UNAUTHORIZED)
                    else:
                        try:
                            if request.profile:
                                from drama_plugin.execution.live_transport import FinancialTerms
                                from pydantic import ValidationError
                                try:
                                    terms = FinancialTerms.model_validate(self.store.ledger.get_index("media-proof-cost-terms",operation.run_id))
                                except ValidationError:
                                    raise FinancialAuthorizationError("INVALID_OR_EXPIRED_FINANCIAL_TERMS") from None
                                terms.validate_current()
                                # This grant is the accepted decision's projection,
                                # not another financial authority or paid intent.
                                current_attempt = self.store.get(checkpoint.attempt_ref, ProviderAttempt) if checkpoint else None
                                supplemental = current_attempt is not None and current_attempt.ordinal == 2
                                transport.grant = ControlledLiveGrant(scope=operation.scope,operation_ref=op_ref,
                                    decision_ref=current_attempt.approval_ref if supplemental else auth.approval_ref,
                                    attempt_ref=current_attempt.artifact_reference() if supplemental else None,
                                    max_paid_operations=terms.max_paid_operations,provider=terms.profile.provider,
                                    model=terms.profile.model,budget_microunits=terms.budget_microunits,
                                    cost_quote=terms.cost_quote,currency=terms.cost_quote.currency,
                                    resolution=terms.profile.resolution,aspect_ratio=terms.profile.aspect_ratio,terms=terms)
                            transport._grant(operation, request)
                            assert transport.grant
                            grant = transport.grant
                        except FinancialAuthorizationError as error:
                            financial_code = error.code
                            codes.append(GateCode.COST_UNAUTHORIZED)
                        except CapabilityAbsent as error:
                            if error.args == ("EXPLICIT_CONTROLLED_LIVE_GRANT_REQUIRED",):
                                codes.append(GateCode.COST_UNAUTHORIZED)
                            else:
                                return self._hard(inputs,self._capability_code(error,"LIVE_EXECUTION_ADMISSION_ABSENT"),evidence)
                        except (ValueError,KeyError):
                            return self._hard(inputs,"FINANCIAL_AUTHORITY_IDENTITY_INVALID",evidence)
                governed = self._govern(inputs, tuple(codes), evidence)
                if governed is not None:
                    if GateCode.REQUEST_UNSUPPORTED in codes:
                        return self._hard(inputs, "REQUEST_UNSUPPORTED", *governed.artifact_refs)
                    return self._cost_wait(inputs, operation.preparation_ref, financial_code)
                checkpoint = self.reserve(inputs)
                attempt = self.store.get(checkpoint.attempt_ref, ProviderAttempt)
                if grant is not None:
                    # Only the execution owner persists the consumed decision's
                    # projection, after approval and before its single dispatch.
                    try:
                        self.store.ledger.put_artifact(grant.owner, grant.artifact_reference(),
                            operation.scope, grant.fingerprint, grant)
                        self.store.ledger.put_index("execution-live-grant", grant.decision_ref.artifact_ref,
                            grant.artifact_reference(), scope=operation.scope, once=True)
                        if request.profile:
                            owners = self.derived(operation.preparation_ref,GenerationPreparation).task.owners
                            assert owners
                            rights_key = "rights:"+owners.rights_decision_ref.artifact_ref + (':attempt:2' if attempt.ordinal == 2 else '')
                            self.store.ledger.put_index("execution-live-grant", rights_key,
                                grant.artifact_reference(),scope=operation.scope,once=True)
                    except ValueError:
                        return self._hard(inputs,"FINANCIAL_AUTHORITY_ALREADY_CONSUMED",op_ref)
                if not self.store.claim_dispatch(op_ref):
                    return self._external(inputs, op_ref, "PROVIDER_DISPATCH_ALREADY_CLAIMED", op_ref)
                try:
                    receipt = await transport.submit(operation, attempt, request)
                except DefinitelyNotSubmitted as error:
                    self.store.definite_not_submitted(op_ref)
                    self.store.progress(op_ref, query_last_code=error.code)
                    return self._hard(inputs, error.code, op_ref)
                except BaseException as error:
                    self.store.unknown(op_ref)
                    if not isinstance(error, Exception):
                        raise
                    self.store.progress(op_ref, query_last_code=error.code if isinstance(error, PossiblySubmitted) else "PROVIDER_SUBMISSION_UNCERTAIN")
                    receipt = None
            else:
                assert checkpoint is not None
                attempt = self.store.get(checkpoint.attempt_ref, ProviderAttempt)
                # SUBMITTING restored after crash is possibly sent. Never claim again.
                if checkpoint.state == OperationState.SUBMITTING:
                    self.store.unknown(op_ref)
                previous = self.store.get(checkpoint.receipt_ref, ProviderReceipt) if checkpoint.receipt_ref else None
                if not transport.can_reconcile(attempt, previous):
                    return self._external(inputs, op_ref, "UNKNOWN_SUBMISSION_RECOVERY_PENDING", op_ref)
                now = round(time.time() * 1000)
                started = checkpoint.progress.query_started_at_ms or now
                if checkpoint.progress.query_attempts >= 60 or now - started >= 1_800_000:
                    return self._hard(inputs, "PROVIDER_QUERY_RETRY_EXHAUSTED", op_ref)
                self.store.progress(op_ref, query_started_at_ms=started,
                    query_attempts=checkpoint.progress.query_attempts + 1)
                try:
                    receipt = await transport.query(operation, attempt, previous)
                except (ValueError, KeyError):
                    return self._hard(inputs, "PROVIDER_RECEIPT_IDENTITY_INVALID", op_ref)
                except Exception:
                    self.store.unknown(op_ref)
                    self.store.progress(op_ref, query_last_code="PROVIDER_QUERY_TRANSIENT")
                    receipt = None
            if receipt is None:
                governed = self._govern(inputs, (GateCode.SUBMISSION_UNCERTAIN,), op_ref,
                    owner="operation-reconciliation", wait=True)
                assert governed is not None
                if not transport.can_reconcile(attempt, previous):
                    return self._external(inputs, op_ref, "UNKNOWN_SUBMISSION_RECOVERY_PENDING", op_ref, *governed.artifact_refs)
                return self._external(inputs, op_ref, "PROVIDER_QUERY_PENDING", op_ref, *governed.artifact_refs)
            try:
                receipt_ref = self.store.receipt(op_ref, receipt)
            except ValueError:
                self.store.unknown(op_ref)
                return self._hard(inputs, "PROVIDER_RECEIPT_IDENTITY_MISMATCH", op_ref)
            if receipt.query_code:
                self.store.progress(op_ref, query_last_code=receipt.query_code)
                if receipt.query_code in {"HTTP_400", "HTTP_401", "HTTP_403", "HTTP_404", "HTTP_422", "PROVIDER_MODEL_CHANGED", "PROVIDER_TASK_ID_CHANGED"}:
                    return self._hard(inputs, receipt.query_code, op_ref, receipt_ref)
            if receipt.state == "RUNNING":
                return self._external(inputs, op_ref, receipt.query_code or "PROVIDER_TASK_RUNNING", op_ref, receipt_ref)
            if receipt.state == "FAILED":
                self.store.progress(op_ref,query_last_code=receipt.failure_code or "PROVIDER_DEFINITE_FAILURE")
                return self._hard(inputs, "PROVIDER_DEFINITE_FAILURE", op_ref, receipt_ref)
            return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(op_ref, receipt_ref))

    def _completed(self, inputs: CapabilityInput) -> tuple[ExecutionOperation, OperationCheckpoint, FinishingRecipe | None]:
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
            if (checkpoint.progress.intake_attempts>=3
                    and checkpoint.progress.intake_last_code=="FORMAL_MEDIA_LOCAL_IO_TRANSIENT"):
                return self._hard(inputs,"MEDIA_INTAKE_RETRY_EXHAUSTED",checkpoint.receipt_ref,
                    self._diagnostic(inputs,"FORMAL_MEDIA_LOCAL_IO_TRANSIENT"))
            transport = self.transports.get(operation.route)
            if transport is None:
                return self._hard(inputs, "MEDIA_INTAKE_CAPABILITY_ABSENT", checkpoint.receipt_ref)
            media = checkpoint.progress.intake_media
            if media:
                try:
                    self.media.path(media)
                except (OSError, ValueError):
                    media = None  # Only the exact completed result may refill this cache.
            read_attempted=False
            if media is None:
                if checkpoint.progress.intake_attempts >= 3:
                    return self._hard(inputs, "MEDIA_INTAKE_RETRY_EXHAUSTED", checkpoint.receipt_ref)
                self.store.progress(checkpoint.operation_ref, intake_attempts=checkpoint.progress.intake_attempts + 1)
                read_attempted=True
                try:
                    content = await transport.obtain(receipt.result)
                    probe_intake_bytes(content)
                    media = self.media.retain(content, kind=receipt.result.kind, mime=receipt.result.mime,
                                              expected_hash=receipt.result.expected_hash)
                except CapabilityAbsent:
                    return self._hard(inputs, "MEDIA_PROBE_ABSENT", checkpoint.receipt_ref)
                except (IntakeTransient, OSError):
                    self.store.progress(checkpoint.operation_ref, intake_last_code="MEDIA_INTAKE_TRANSIENT")
                    if checkpoint.progress.intake_attempts + 1 >= 3:
                        return self._hard(inputs, "MEDIA_INTAKE_RETRY_EXHAUSTED", checkpoint.receipt_ref)
                    return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="MEDIA_INTAKE_TRANSIENT",
                        recovery_class=RecoveryClass.RETRY_SAME_STEP, retry_limit=3,
                        artifact_refs=(self._diagnostic(inputs, "MEDIA_INTAKE_TRANSIENT"),))
                except ValueError:
                    self.store.progress(checkpoint.operation_ref, intake_last_code="MEDIA_RESULT_IDENTITY_INVALID")
                    return self._hard(inputs, "MEDIA_RESULT_IDENTITY_INVALID", checkpoint.receipt_ref)
                self.store.progress(checkpoint.operation_ref, intake_media=media)
            from drama_plugin.exceptions import RemoteServiceError, ContractValidationError, ConfigurationError, MediaImportSourceError
            from drama_plugin.execution.formal_media import FormalMediaPending
            try:
                canonical = await self._register_media(operation, checkpoint, media)
            except FormalMediaPending:
                self.store.progress(checkpoint.operation_ref, media_last_code="FORMAL_MEDIA_IMPORT_RECONCILIATION_REQUIRED")
                return self._external(inputs, checkpoint.operation_ref, "FORMAL_MEDIA_IMPORT_RECONCILIATION_REQUIRED", checkpoint.operation_ref)
            except MediaImportSourceError:
                self.store.progress(checkpoint.operation_ref, media_last_code="FORMAL_MEDIA_IMPORT_SOURCE_CONFIGURATION")
                return self._external(inputs, checkpoint.operation_ref, "FORMAL_MEDIA_IMPORT_SOURCE_CONFIGURATION", checkpoint.operation_ref)
            except RemoteServiceError as error:
                code = self._remote_code(error)
                self.store.progress(checkpoint.operation_ref, media_last_code=code)
                if self._remote_permanent(error):
                    return self._hard(inputs, code, checkpoint.operation_ref)
                return self._external(inputs, checkpoint.operation_ref, code, checkpoint.operation_ref)
            except ContractValidationError as error:
                return self._external(inputs, checkpoint.operation_ref, "FORMAL_MEDIA_RESPONSE_SCHEMA_INVALID",
                    checkpoint.operation_ref,*self._schema_diagnostics(inputs,error))
            except CapabilityAbsent as error:
                return self._hard(inputs,self._capability_code(error,"FORMAL_MEDIA_CAPABILITY_ABSENT"),checkpoint.operation_ref)
            except ConfigurationError:
                return self._hard(inputs, "FORMAL_MEDIA_CAPABILITY_ABSENT", checkpoint.operation_ref)
            except (ValueError, KeyError):
                return self._hard(inputs, "FORMAL_MEDIA_IDENTITY_INVALID", checkpoint.operation_ref)
            except OSError:
                current=self.store.checkpoint(checkpoint.operation_ref)
                attempts=current.progress.intake_attempts + (0 if read_attempted else 1)
                self.store.progress(checkpoint.operation_ref,intake_attempts=attempts,
                    intake_last_code="FORMAL_MEDIA_LOCAL_IO_TRANSIENT")
                if attempts>=3:
                    return self._hard(inputs,"MEDIA_INTAKE_RETRY_EXHAUSTED",checkpoint.receipt_ref,
                        self._diagnostic(inputs,"FORMAL_MEDIA_LOCAL_IO_TRANSIENT"))
                return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="FORMAL_MEDIA_LOCAL_IO_TRANSIENT",
                    recovery_class=RecoveryClass.RETRY_SAME_STEP, retry_limit=3,
                    artifact_refs=(self._diagnostic(inputs, "FORMAL_MEDIA_LOCAL_IO_TRANSIENT"),))
            if not canonical:
                return self._hard(inputs, "FORMAL_MEDIA_CAPABILITY_ABSENT", checkpoint.operation_ref)
            binding = MediaBinding.seal(scope=operation.scope, run_id=operation.run_id,
                source_package_ref=operation.source_package_ref, operation_ref=checkpoint.operation_ref,
                attempt_ref=checkpoint.attempt_ref, receipt_ref=checkpoint.receipt_ref,
                provider_result_id=receipt.result.result_id, media=media,
                final_prompt_ref=operation.final_prompt_ref, reference_bindings=operation.reference_bindings,
                canonical_media_ref=canonical if isinstance(canonical, ArtifactReference) else None)
            ref = self.store.put(binding)
            self.store.progress(checkpoint.operation_ref, video_ref=ref)
            return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(ref,))

    async def _register_media(self, operation: ExecutionOperation, checkpoint: OperationCheckpoint,
                              media: MediaIdentity, parents: tuple[MediaIdentity, ...] = ()) -> ArtifactReference | bool:
        from drama_plugin.execution.formal_media import FormalMediaStore
        if isinstance(self.media, FormalMediaStore):
            prepared = self.derived(operation.preparation_ref, GenerationPreparation)
            return await self.media.register(media, scope=operation.scope, source_ref=checkpoint.operation_ref,
                attempt_ref=checkpoint.attempt_ref, package_ref=operation.source_package_ref, parents=parents,
                owners=prepared.task.owners)
        return True

    def _technical(self, operation: ExecutionOperation, checkpoint: OperationCheckpoint,
                   media: MediaIdentity, recipe: FinishingRecipe | None, *, audio_expected: bool) -> TechnicalMediaReview:
        plan = self.derived(operation.audio_plan_ref, AudioExecutionPlan)
        profile = self.derived(operation.preparation_ref, GenerationPreparation).task.profile
        observation, findings = inspect(self.media, media, duration_ms=profile.requested_duration_ms if profile else plan.duration_ms,
            tolerance_ms=recipe.duration_tolerance_ms if recipe else FinishingRecipe.model_fields["duration_tolerance_ms"].default, audio_expected=audio_expected,
            resolution=profile.resolution if profile else None, aspect_ratio=profile.aspect_ratio if profile else None)
        return TechnicalMediaReview.seal(scope=operation.scope, run_id=operation.run_id,
            source_package_ref=operation.source_package_ref, operation_ref=checkpoint.operation_ref,
            attempt_ref=checkpoint.attempt_ref, media=media, outcome="FAIL" if findings else "PASS",
            observation=observation, findings=findings)

    async def _creative(self, operation: ExecutionOperation, checkpoint: OperationCheckpoint,
                        media: MediaIdentity) -> CreativeMediaReview:
        from drama_plugin.execution.review import MockReviewer
        prepared = self.derived(operation.preparation_ref, GenerationPreparation)
        key = operation.artifact_reference().artifact_ref + ":" + media.content_hash
        if isinstance(self.reviewer, HumanReviewer):
            try:
                ref = ArtifactReference.model_validate(self.store.ledger.get_index("human-media-review", key))
                review = self.store.get(ref, CreativeMediaReview)
                binding = self.store.get(checkpoint.progress.video_ref, MediaBinding) if checkpoint.progress.video_ref else None
                expected = self.review_context(operation, media, binding.canonical_media_ref if binding else None)
                if review.review_context_hash != expected or review.preparation_ref != operation.preparation_ref or review.media != media:
                    raise ValueError("HUMAN_REVIEW_CONTEXT_MISMATCH")
                return review
            except KeyError:
                # Recover a committed exact human receipt if only its index was lost.
                binding = self.store.get(checkpoint.progress.video_ref, MediaBinding) if checkpoint.progress.video_ref else None
                expected = self.review_context(operation, media, binding.canonical_media_ref if binding else None)
                with self.store.ledger.transaction() as db:
                    rows = db.execute("""SELECT artifact_id,version FROM immutable_artifact
                        WHERE artifact_type='creative-media-review' AND work_id=? AND scene_id IS ? AND shot_id IS ?
                        AND json_extract(body_json,'$.runId')=? AND json_extract(body_json,'$.reviewContextHash')=? LIMIT 2""",
                        (operation.scope.work_id,operation.scope.scene_id,operation.scope.shot_id,operation.run_id,expected)).fetchall()
                if len(rows) > 1:
                    raise ValueError("HUMAN_REVIEW_CONTEXT_MISMATCH")
                if rows:
                    ref = ArtifactReference(owner=CreativeMediaReview.owner,artifact_ref=rows[0]["artifact_id"],version=rows[0]["version"])
                    review = self.store.get(ref,CreativeMediaReview)
                    if review.media != media or review.preparation_ref != operation.preparation_ref or review.reviewer != "USER":
                        raise ValueError("HUMAN_REVIEW_CONTEXT_MISMATCH")
                    self.store.ledger.put_index("human-media-review",key,ref,scope=operation.scope,once=True)
                    return review
        if (operation.authorization.execution_mode == "CONTROLLED_LIVE" or prepared.task.unit) and isinstance(self.reviewer, MockReviewer):
            raise CapabilityAbsent("FORMAL_MOCK_REVIEW_FORBIDDEN")
        else:
            reviewer = self.reviewer
        response = await reviewer.review(operation, media,
            mode=self.store.ledger.load_run(operation.run_id).mode) if reviewer else None
        outcome = response.outcome if response else "CAPABILITY_ABSENT"
        return CreativeMediaReview.seal(scope=operation.scope, run_id=operation.run_id,
            source_package_ref=operation.source_package_ref, operation_ref=checkpoint.operation_ref,
            attempt_ref=checkpoint.attempt_ref, media=media,
            reviewer=self.reviewer.identity if self.reviewer else "unavailable",
            policy_version=self.reviewer.policy_version if self.reviewer else "creative-review-unavailable-v1",
            outcome=outcome, observations=response.observations if response else (),
            adoption_recommendation={"PASS": "CANDIDATE_ONLY", "REVISE": "REVISION_REQUIRED",
                                     "CAPABILITY_ABSENT": "UNASSESSED"}[outcome])

    def review_context(self, operation: ExecutionOperation, media: MediaIdentity,
                       canonical_ref: ArtifactReference | None) -> str:
        prepared = self.derived(operation.preparation_ref, GenerationPreparation)
        return sha256_canonical([v.model_dump(mode="json",by_alias=True) if v is not None else None for v in
            (operation.artifact_reference(), media, canonical_ref, operation.source_package_ref,
             operation.final_prompt_ref, operation.preparation_ref, prepared.task)])

    def record_human_review(self, run_id: str, *, media_ref: ArtifactReference, context_hash: str,
                            response: ReviewResponse) -> ArtifactReference:
        from drama_plugin.execution.review import HumanReviewer
        if not isinstance(self.reviewer, HumanReviewer):
            raise ValueError("HUMAN_REVIEW_CONSUMER_REQUIRED")
        inputs = self.store.inputs(run_id)
        run = self.store.ledger.load_run(run_id)
        if run.workflow_id not in MEDIA_WORKFLOWS or run.state not in {RuntimeState.WAITING_EXTERNAL,RuntimeState.WAITING_USER} or media_cursor(run.workflow_id, run.cursor) != 11:
            raise ValueError("NO_PENDING_HUMAN_OPERATION_REVIEW")
        operation, _, _ = self._approved(CapabilityInput(run_id=run_id,operation_id=run_id+":review",scope=run.scope))
        cp = self.store.checkpoint(operation.artifact_reference())
        if cp.progress.video_ref != media_ref or not cp.progress.video_technical_ref:
            raise ValueError("EXACT_TECHNICALLY_REVIEWED_MEDIA_REQUIRED")
        if self.store.get(cp.progress.video_technical_ref, TechnicalMediaReview).outcome != "PASS":
            raise ValueError("TECHNICAL_REVIEW_NOT_PASSED")
        binding = self.store.get(media_ref, MediaBinding)
        expected = self.review_context(operation, binding.media, binding.canonical_media_ref)
        if context_hash != expected or self.derived(inputs.preparation_ref, GenerationPreparation).task.profile and binding.canonical_media_ref is None:
            raise ValueError("HUMAN_REVIEW_CONTEXT_MISMATCH")
        record = CreativeMediaReview.seal(scope=run.scope,run_id=run_id,source_package_ref=operation.source_package_ref,
            operation_ref=operation.artifact_reference(),attempt_ref=cp.attempt_ref,media=binding.media,
            reviewer=self.reviewer.identity,policy_version=self.reviewer.policy_version,outcome=response.outcome,
            observations=response.observations,adoption_recommendation="CANDIDATE_ONLY" if response.outcome=="PASS" else "REVISION_REQUIRED",
            preparation_ref=operation.preparation_ref,canonical_media_ref=binding.canonical_media_ref,review_context_hash=expected)
        ref = self.store.put(record)
        self.store.ledger.put_index("human-media-review", operation.artifact_reference().artifact_ref+":"+binding.media.content_hash,
            ref,scope=run.scope,once=True)
        self.store.progress(cp.operation_ref, video_creative_ref=ref)
        return ref

    async def review(self, inputs: CapabilityInput) -> CapabilityResult:
        async with self.store.lock(inputs.run_id):
            operation, checkpoint, recipe = self._completed(inputs)
            progress = checkpoint.progress
            assert progress.video_ref is not None
            binding = self.store.get(progress.video_ref, MediaBinding)
            from drama_plugin.execution.formal_media import FormalMediaStore
            if isinstance(self.media, FormalMediaStore):
                from drama_plugin.exceptions import RemoteServiceError, ConfigurationError, ContractValidationError
                try:
                    await self.media.restore(operation.scope, binding.media)
                except RemoteServiceError as error:
                    code = self._remote_code(error)
                    if self._remote_permanent(error):
                        return self._hard(inputs, code, progress.video_ref)
                    return self._external(inputs, binding.canonical_media_ref or progress.video_ref, code, progress.video_ref)
                except ContractValidationError as error:
                    return self._external(inputs, binding.canonical_media_ref or progress.video_ref,
                        "FORMAL_MEDIA_RESPONSE_SCHEMA_INVALID", progress.video_ref,*self._schema_diagnostics(inputs,error))
                except CapabilityAbsent as error:
                    return self._hard(inputs,self._capability_code(error,"FORMAL_MEDIA_CAPABILITY_ABSENT"),progress.video_ref)
                except ConfigurationError:
                    return self._hard(inputs, "FORMAL_MEDIA_CAPABILITY_ABSENT", progress.video_ref)
                except (ValueError, KeyError):
                    return self._hard(inputs, "FORMAL_MEDIA_IDENTITY_INVALID", progress.video_ref)
                except OSError:
                    return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="MEDIA_CACHE_IO_TRANSIENT",
                        recovery_class=RecoveryClass.RETRY_SAME_STEP,retry_limit=3,
                        artifact_refs=(self._diagnostic(inputs,"MEDIA_CACHE_IO_TRANSIENT"),))
            try:
                profile = self.derived(operation.preparation_ref, GenerationPreparation).task.profile
                technical = self.store.get(progress.video_technical_ref, TechnicalMediaReview) if progress.video_technical_ref else self._technical(
                    operation, checkpoint, binding.media, recipe,
                    audio_expected=(profile.native_audio if profile else
                        self.derived(operation.audio_plan_ref, AudioExecutionPlan).native_audio_policy == "REQUIRED"))
                if binding.media.kind != "VIDEO":
                    technical = TechnicalMediaReview.seal(**{**technical.model_dump(exclude={"fingerprint"}),
                        "outcome": "FAIL", "findings": (*technical.findings, "RESULT_VIDEO_INCOMPATIBLE")})
            except CapabilityAbsent:
                return self._hard(inputs, "MEDIA_PROBE_ABSENT", progress.video_ref)
            technical_ref = self.store.put(technical)
            self.store.progress(checkpoint.operation_ref, video_technical_ref=technical_ref)
            if technical.outcome != "PASS":
                return self._hard(inputs, "TECHNICAL_MEDIA_FAILURE", technical_ref)
            try:
                creative = self.store.get(progress.video_creative_ref, CreativeMediaReview) if progress.video_creative_ref else await self._creative(operation, checkpoint, binding.media)
            except CapabilityAbsent as error:
                return self._hard(inputs,self._capability_code(error,"FORMAL_CREATIVE_REVIEW_CAPABILITY_ABSENT"),progress.video_ref)
            except (ValueError, KeyError):
                return self._hard(inputs, "HUMAN_REVIEW_CONTEXT_MISMATCH", progress.video_ref)
            creative_ref = self.store.put(creative)
            # Absence is retained evidence, but not a completed review checkpoint.
            if creative.outcome != "CAPABILITY_ABSENT":
                self.store.progress(checkpoint.operation_ref, video_creative_ref=creative_ref)
            elif isinstance(self.reviewer, HumanReviewer):
                return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL,artifact_refs=(technical_ref,progress.video_ref),
                    external_ref=progress.video_ref,recovery_class=RecoveryClass.USER_DECISION,
                    user_decision=UserDecisionRequest(category=DecisionCategory.ART_APPROVAL,
                        question="Review this exact technically passed operation Media and select PASS or REVISE."))
            if creative.outcome == "REVISE" and operation.preparation_ref and self.store.ledger.load_run(inputs.run_id).workflow_id in MEDIA_WORKFLOWS:
                return CapabilityResult(status=ResultStatus.SUCCEEDED,artifact_refs=(technical_ref,creative_ref))
            if creative.outcome != "PASS":
                if creative.outcome == "CAPABILITY_ABSENT":
                    return self._hard(inputs,"FORMAL_CREATIVE_REVIEW_CAPABILITY_ABSENT",creative_ref)
                # Historical E1 revisions remain explicitly scoped user review; no paid retry.
                return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL,external_ref=creative_ref,
                    artifact_refs=(creative_ref,),recovery_class=RecoveryClass.USER_DECISION,
                    user_decision=UserDecisionRequest(category=DecisionCategory.ART_APPROVAL,
                        question="Review the scoped revision observations before further production."))
            return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(technical_ref, creative_ref))

    async def execute_audio(self, inputs: CapabilityInput) -> CapabilityResult:
        async with self.store.lock(inputs.run_id):
            operation, checkpoint, recipe = self._completed(inputs)
            if recipe is None:
                raise ExecutionScopeMismatch("Audio/finishing requires an approved recipe")
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
                if not await self._register_media(operation, checkpoint, media, (video,)):
                    return self._absence(inputs, checkpoint.operation_ref, "formal-media-reconciliation")
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
            if recipe is None:
                raise ExecutionScopeMismatch("Audio/finishing requires an approved recipe")
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
                if not await self._register_media(operation, checkpoint, media, (video, audio.media)):
                    return self._absence(inputs, checkpoint.operation_ref, "formal-media-reconciliation")
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

    def inspect_execution(self, key: str, inputs: CapabilityInput) -> ExecutionInspection | None:
        """Witness exact committed owner output, never grant another side effect.

        A durable task receipt proves submission already happened; subsequent
        calls reconcile that identity. Verified intake cache and review refs are
        similarly committed work, while their own read/query limits remain live.
        """
        try:
            operation, request, _ = self._approved(inputs)
        except (ValueError,KeyError):
            return None  # Existing owner emits its governed exact failure.
        revision=ExecutionRevision(fingerprint=sha256_canonical([
                "target-execution-reconciliation-v1",key,ProviderRequest.model_json_schema(),
                request.profile.model_dump(mode="json",by_alias=True) if request.profile else None]),
            input_fingerprint=sha256_canonical([
                ref.model_dump(mode="json",by_alias=True) for ref in (
                    operation.artifact_reference(),operation.preparation_ref,
                    operation.source_package_ref,operation.final_prompt_ref)
            ]+[request.model_dump(mode="json",by_alias=True)]))
        completed=False
        try:
            cp=self.store.checkpoint(operation.artifact_reference())
            if key==EXECUTE and cp.state not in {OperationState.RESERVED,OperationState.FAILED}:
                attempt=self.store.get(cp.attempt_ref,ProviderAttempt)
                receipt=self.store.get(cp.receipt_ref,ProviderReceipt) if cp.receipt_ref else None
                transport=self.transports.get(operation.route)
                completed=transport is not None and transport.can_reconcile(attempt,receipt)
            elif key==INTAKE:
                if cp.progress.video_ref:
                    binding=self.store.get(cp.progress.video_ref,MediaBinding)
                    completed=binding.operation_ref==cp.operation_ref and binding.scope==operation.scope
                elif cp.progress.intake_media:
                    self.media.path(cp.progress.intake_media)  # Exact physical bytes/hash.
                    completed=True
            elif key==REVIEW and cp.progress.video_ref and cp.progress.video_technical_ref:
                binding=self.store.get(cp.progress.video_ref,MediaBinding)
                technical=self.store.get(cp.progress.video_technical_ref,TechnicalMediaReview)
                completed=(technical.operation_ref==cp.operation_ref and technical.media==binding.media
                    and technical.scope==operation.scope and binding.operation_ref==cp.operation_ref)
        except (KeyError,OSError):
            pass
        run=self.store.ledger.load_run(inputs.run_id)
        if (key in {INTAKE,REVIEW} and run.state!=RuntimeState.RUNNING and run.last_result is not None
                and run.last_result.status==ResultStatus.RETRYABLE_FAILURE
                and run.last_result.recovery_class==RecoveryClass.RETRY_SAME_STEP
                and run.executing_action is not None and run.executing_action.capability_key==key):
            # Committed Media/QA refs do not refresh the finite local read/commit
            # retry budget. A true interrupted invocation or
            # external import claim still reconciles its exact committed witness.
            completed=False
        return ExecutionInspection(revision=revision,completed=completed)

    def registrations(self) -> dict[str, TargetCapability]:
        def protected(key: str, handler: Callable[[CapabilityInput], Awaitable[CapabilityResult]]) -> TargetCapability:
            async def invoke(inputs: CapabilityInput) -> CapabilityResult:
                try:
                    return await handler(inputs)
                except ExecutionIntegrityError as error:
                    return self._hard(inputs,error.code)
                except (ValueError,KeyError):
                    return self._hard(inputs,"EXECUTION_IMMUTABLE_INPUT_INVALID")
            return TargetCapability(invoke,replay_safe=True,inspect_execution=lambda inputs:self.inspect_execution(key,inputs))
        return {EXECUTE: protected(EXECUTE,self.execute),
                INTAKE: protected(INTAKE,self.intake), REVIEW: protected(REVIEW,self.review),
                AUDIO: TargetCapability(self.execute_audio, replay_safe=True), FINISH: TargetCapability(self.finish, replay_safe=True)}
