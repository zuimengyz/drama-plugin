"""Safe author failure evidence, outside creative facts and Runtime contracts.

Never retain exception messages, validation inputs/context, headers, model text or
reasoning. Task-local response metadata follows an author through post-validation.
"""
from contextvars import ContextVar
from typing import Literal, TYPE_CHECKING
from collections.abc import Awaitable, Callable
import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError, JsonValue, TypeAdapter

from drama_plugin.config.text_composition import AuthorRole
from drama_plugin.creative_engine.contracts import ShotBody
from drama_plugin.execution.transport import CapabilityAbsent
from drama_plugin.director import DirectorError
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.runtime.contracts import (ArtifactReference, CapabilityInput, CapabilityResult,
    RecoveryClass, ResultStatus, RuntimeRun, Identifier)
from drama_plugin.creative_engine.contracts import VersionRef
from drama_plugin.production.contracts import SourceDomain
from drama_plugin.runtime.policy import AUTHOR_CONTENT_ATTEMPT_LIMIT
if TYPE_CHECKING:
    from drama_plugin.creative_engine.store import CreativeVersionStore


FailureStage = Literal["RESPONSE", "PROVIDER_PROTOCOL", "JSON_PARSE", "DTO_SCHEMA",
    "DIALOGUE_AUTHORITY", "SHOT_POST_VALIDATION", "INCOMPLETE_OUTPUT", "INTERNAL"]
CoverageReason = Literal["BEAT_ACTOR_MISSING", "CANON_SPEAKER_MISSING"]
MAX_SAFE_FINDINGS = 256


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    field_path: tuple[str | int, ...] = Field(serialization_alias="fieldPath")
    error_type: str
    stage: FailureStage | None = None
    code: Identifier | None = None
    validator: Identifier | None = None
    reason: CoverageReason | None = None
    missing_subject_id: Identifier | None = Field(default=None, serialization_alias="missingSubjectId")
    beat_id: Identifier | None = Field(default=None, serialization_alias="beatId")
    spoken_id: Identifier | None = Field(default=None, serialization_alias="spokenId")
    expected_coverage_role: Literal["INTERACTIVE_PARTNER"] | None = Field(default=None, serialization_alias="expectedCoverageRole")
    allowed_spoken_ids: tuple[Identifier, ...] | None = Field(default=None, max_length=100, serialization_alias="allowedSpokenIds")
    domain: SourceDomain | None = None


class AuthorDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    role: AuthorRole = "direction"
    failure_stage: FailureStage
    code: str
    exception_type: str | None = None
    validator: str | None = None
    reason: CoverageReason | None = None
    missing_subject_id: Identifier | None = None
    beat_id: Identifier | None = None
    spoken_id: Identifier | None = None
    expected_coverage_role: Literal["INTERACTIVE_PARTNER"] | None = None
    issues: tuple[ValidationIssue, ...] = Field(default=(), max_length=MAX_SAFE_FINDINGS)
    omitted_issue_count: int = Field(default=0, ge=0)
    response_hash: str | None = None
    finish_reason: str | None = None
    model: str | None = None
    http_status: int | None = None
    usage: dict[str, int] = {}
    provider: str | None = None
    execution_fingerprint: str | None = None
    attempt: int | None = None
    execution_revision: str | None = None
    recovery_class: RecoveryClass = RecoveryClass.RETRY_SAME_STEP


# No mutable shared-client "last response" that could mix concurrent run evidence.
response_context: ContextVar[AuthorDiagnostic | None] = ContextVar("author_response_metadata", default=None)
structural_feedback: ContextVar[AuthorDiagnostic | None] = ContextVar("author_structural_feedback", default=None)


class AuthorResultFailure(ValueError):
    def __init__(self, diagnostic: AuthorDiagnostic):
        super().__init__(diagnostic.code)
        self.diagnostic = diagnostic


class AuthorUnavailable(CapabilityAbsent):
    def __init__(self, diagnostic: AuthorDiagnostic):
        super().__init__(diagnostic.code)
        self.diagnostic = diagnostic


def retain_author_diagnostic(versions: "CreativeVersionStore", inputs: CapabilityInput,
                             diagnostic: AuthorDiagnostic, *, author_round: int,
                             version_refs: tuple[VersionRef, ...]) -> ArtifactReference:
    body = {"schemaVersion": "author-failure-diagnostic-v1", "runId": inputs.run_id,
        "operationId": inputs.operation_id, "scope": inputs.scope.model_dump(mode="json", by_alias=True),
        "authorRound": author_round, "versionRefs": [r.model_dump(mode="json", by_alias=True) for r in version_refs],
        "diagnostic": diagnostic.model_dump(mode="json")}
    pin = versions.objects.put("author-diagnostic:" + sha256_canonical(body), body)
    return ArtifactReference(owner="creative-diagnostic", artifact_ref="author-diagnostic:" + pin.fingerprint, version=1)


def failure(stage: str, code: str, *, role: AuthorRole = "direction", exception_type: str = "ValueError",
            field_path: tuple[str | int, ...] = (), validator: str | None = None,
            recovery_class: RecoveryClass | None = None,
            reason: CoverageReason | None = None,
            missing_subject_id: str | None = None, beat_id: str | None = None,
            spoken_id: str | None = None,
            expected_coverage_role: Literal["INTERACTIVE_PARTNER"] | None = None,
            allowed_spoken_ids: tuple[str, ...] | None = None,
            domain: SourceDomain | None = None) -> AuthorDiagnostic:
    prior = response_context.get()
    fields = prior.model_dump() if prior else {"role": role}
    return AuthorDiagnostic.model_validate({**fields, "failure_stage": stage, "code": code,
        "exception_type": exception_type, "validator": validator,
        "reason": reason, "missing_subject_id": safe_subject_identity(missing_subject_id),
        "beat_id": safe_subject_identity(beat_id), "spoken_id": safe_subject_identity(spoken_id),
        "expected_coverage_role": expected_coverage_role,
        "issues": ({"field_path": field_path, "error_type": code, "stage": stage,
            "code": code, "validator": validator, "reason": reason,
            "missing_subject_id": safe_subject_identity(missing_subject_id),
            "beat_id": safe_subject_identity(beat_id), "spoken_id": safe_subject_identity(spoken_id),
            "expected_coverage_role": expected_coverage_role,
            "allowed_spoken_ids": allowed_spoken_ids, "domain": domain},) if field_path else (),
        "omitted_issue_count": 0,
        "recovery_class": recovery_class or (RecoveryClass.HARD_BLOCK if stage == "INTERNAL" else RecoveryClass.RETRY_SAME_STEP)})


def aggregate_failures(findings: tuple[AuthorDiagnostic, ...]) -> AuthorDiagnostic:
    """Reuse one safe diagnostic; integrity/internal failures are never aggregated."""
    if not findings:
        raise ValueError("No author findings")
    issues: list[ValidationIssue] = []
    seen: set[str] = set()
    omitted = 0
    for diagnostic in findings:
        if diagnostic.recovery_class != RecoveryClass.RETRY_SAME_STEP:
            raise AuthorResultFailure(diagnostic)
        omitted += diagnostic.omitted_issue_count
        for issue in diagnostic.issues:
            enriched = ValidationIssue.model_validate({**issue.model_dump(),
                "stage": issue.stage or diagnostic.failure_stage,
                "code": issue.code or diagnostic.code,
                "validator": issue.validator or diagnostic.validator})
            identity = enriched.model_dump_json()
            if identity in seen:
                continue
            seen.add(identity)
            if len(issues) < MAX_SAFE_FINDINGS:
                issues.append(enriched)
            else:
                omitted += 1
    # Primary fields preserve existing single-failure consumers and feedback.
    return AuthorDiagnostic.model_validate({**findings[0].model_dump(),
        "issues": tuple(issues), "omitted_issue_count": omitted})


def safe_subject_identity(value: str | None) -> str | None:
    """Keep exact typed identifiers, never truncate or infer a prose actor label."""
    if value is None:
        return None
    try:
        return TypeAdapter(Identifier).validate_python(value)
    except ValidationError:
        return None


def safe_identity(value: str) -> str | None:
    """Provider/model names only; never URLs, arbitrary remote strings or credentials."""
    return value if re.fullmatch(r"[A-Za-z0-9_.:/-]{1,160}", value) and "://" not in value else None


def previous_diagnostic(versions: "CreativeVersionStore", inputs: CapabilityInput,
                        run: RuntimeRun) -> AuthorDiagnostic | None:
    if run.last_result is None:
        return None
    from drama_plugin.contracts.source_pin import SourcePin
    for ref in run.last_result.artifact_refs:
        if ref.owner != "creative-diagnostic" or not ref.artifact_ref.startswith("author-diagnostic:"):
            continue
        digest = ref.artifact_ref.split(":", 1)[1]
        body = versions.objects.read_ref(SourcePin(key=ref.artifact_ref, kind="CANON", fingerprint=digest))
        if body.get("runId") != inputs.run_id or body.get("operationId") != inputs.operation_id:
            continue
        diagnostic = AuthorDiagnostic.model_validate(body["diagnostic"])
        repair = run.active_repair()
        repaired_previous = (repair is not None and repair.exhausted.evidence_ref == ref and
            diagnostic.execution_fingerprint == repair.exhausted.revision.fingerprint)
        if (diagnostic.recovery_class == RecoveryClass.RETRY_SAME_STEP and
                (run.execution_revision is None or diagnostic.execution_fingerprint == run.execution_revision.fingerprint
                    or repaired_previous)):
            return diagnostic
    return None


async def run_author_capability(handler: Callable[[CapabilityInput], Awaitable[CapabilityResult]], *,
        role: AuthorRole, versions: "CreativeVersionStore", inputs: CapabilityInput,
        run: RuntimeRun, version_refs: tuple[VersionRef, ...], author_round: int) -> CapabilityResult:
    """One author invocation; Runtime alone consumes the total content allowance."""
    fingerprint = run.execution_revision.fingerprint if run.execution_revision else None
    context_token = response_context.set(AuthorDiagnostic(role=role, failure_stage="RESPONSE",
        code="AUTHOR_CAPABILITY_STARTED", attempt=run.step_attempts,
        execution_revision=fingerprint, execution_fingerprint=fingerprint))
    feedback_token = structural_feedback.set(None)
    try:
        structural_feedback.set(previous_diagnostic(versions, inputs, run))
        return await handler(inputs)
    except Exception as error:
        if isinstance(error, (AuthorResultFailure, AuthorUnavailable)):
            diagnostic = error.diagnostic
        elif isinstance(error, CapabilityAbsent):
            known = {"FORMAL_AUTHOR_CONFIGURATION_ABSENT", "FORMAL_AUTHOR_REASONING_POLICY_UNSUPPORTED",
                "SOURCE_LANGUAGE_AUTHORITY_ABSENT", "AUTHOR_INPUT_BOUND_EXCEEDED", "FORMAL_AUTHOR_SKILL_ABSENT",
                "DIRECTION_CANON_PREREQUISITE_ABSENT", "PROFESSIONAL_SHOT_PREREQUISITE_ABSENT"}
            code = str(error) if str(error) in known else "AUTHOR_CAPABILITY_ABSENT"
            diagnostic = failure("PROVIDER_PROTOCOL", code, role=role,
                exception_type=type(error).__name__, recovery_class=RecoveryClass.HARD_BLOCK)
        elif isinstance(error, OSError):
            # Owner IO has no external side effect. Retry the durable commit, not
            # an author's text request; accepted output is recovered by the handler.
            committed = versions.has_author_output(inputs.operation_id, role)
            diagnostic = failure("INTERNAL", "AUTHOR_OWNER_COMMIT_INTERRUPTED" if committed else "AUTHOR_OWNER_STORAGE_UNAVAILABLE", role=role,
                exception_type=type(error).__name__, recovery_class=RecoveryClass.AUTO_RECOVER if committed else RecoveryClass.HARD_BLOCK)
        elif isinstance(error, (DirectorError, ValueError, KeyError)):
            diagnostic = failure("INTERNAL", "AUTHOR_IMMUTABLE_INPUT_OR_OWNER_INVALID", role=role,
                exception_type=type(error).__name__, validator="CreativeVersionStore.authoritative_input_and_owner",
                recovery_class=RecoveryClass.HARD_BLOCK)
        else:
            # Author DTO errors must be raised at the producer boundary. A store/input
            # validation error here cannot be made safe by re-authoring creative facts.
            diagnostic = failure("INTERNAL", "UNEXPECTED_AUTHOR_CAPABILITY_FAILURE", role=role,
                exception_type=type(error).__name__, recovery_class=RecoveryClass.HARD_BLOCK)
        ref = retain_author_diagnostic(versions, inputs, diagnostic,
            author_round=author_round, version_refs=version_refs)
        retry = diagnostic.recovery_class in {RecoveryClass.RETRY_SAME_STEP, RecoveryClass.AUTO_RECOVER}
        return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE if retry else ResultStatus.FAILED,
            code="CAPABILITY_EXECUTION_ERROR" if retry else diagnostic.code,
            artifact_refs=(ref,), recovery_class=diagnostic.recovery_class,
            retry_limit=(run.step_retry_limit or AUTHOR_CONTENT_ATTEMPT_LIMIT) if retry else None,
            failure_stage="CAPABILITY_EXECUTION",
            exception_type=diagnostic.exception_type)
    finally:
        structural_feedback.reset(feedback_token)
        response_context.reset(context_token)


def validation_failure(error: ValidationError, *, role: AuthorRole, post: bool = False,
                       output_schema: dict[str, JsonValue] | None = None) -> AuthorDiagnostic:
    entries = error.errors(include_input=False, include_context=False, include_url=False)
    if any(e["type"] == "json_invalid" for e in entries):
        return failure("JSON_PARSE", "AUTHOR_DOMAIN_JSON_INVALID", role=role,
            exception_type="ValidationError", field_path=("$",))
    # Exact, existing validator messages only. Do not retain arbitrary model/input messages.
    validators = {
        "Value error, Required professional domains must be canonical": "SHOT_PROFESSIONAL_DOMAINS_NOT_CANONICAL",
        "Value error, Professional author cannot own Canon or Shot intent": "SHOT_PROFESSIONAL_DOMAIN_AUTHORITY",
    }
    match = next((validators[e["msg"]] for e in entries if e["msg"] in validators), None)
    if match is not None and role == "direction":
        return failure("SHOT_POST_VALIDATION", match, exception_type="ValidationError",
            field_path=("professionalDomains",), validator="ShotBody.domains")
    aliases = {name: field.alias or name for name, field in ShotBody.model_fields.items()}
    allowed = set(aliases) | set(aliases.values())
    # Canon/Film field paths come from the trusted DTO schema, never model keys.
    def schema_fields(value: JsonValue) -> None:
        if isinstance(value, dict):
            properties = value.get("properties")
            if isinstance(properties, dict):
                allowed.update(properties)
            for child in value.values():
                schema_fields(child)
        elif isinstance(value, list):
            for child in value:
                schema_fields(child)
    if output_schema is not None:
        schema_fields(output_schema)
    # Unknown extra keys may themselves contain a secret. Keep a placeholder, not raw loc.
    issues = tuple(ValidationIssue(field_path=tuple(
        min(p, 1_000_000) if isinstance(p, int) else aliases.get(p, p) if p in allowed else "<extra>"
        for p in e["loc"]), error_type=e["type"]) for e in entries[:MAX_SAFE_FINDINGS])
    base = failure("SHOT_POST_VALIDATION" if post else "DTO_SCHEMA", "AUTHOR_DOMAIN_RESULT_INVALID",
        role=role, exception_type="ValidationError")
    return AuthorDiagnostic.model_validate({**base.model_dump(), "issues": issues,
        "omitted_issue_count": max(0, len(entries) - MAX_SAFE_FINDINGS)})
