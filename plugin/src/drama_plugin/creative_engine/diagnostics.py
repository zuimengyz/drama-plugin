"""Safe author failure evidence, outside creative facts and Runtime contracts.

Never retain exception messages, validation inputs/context, headers, model text or
reasoning. Task-local response metadata follows an author through post-validation.
"""
from contextvars import ContextVar
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from drama_plugin.config.text_composition import AuthorRole
from drama_plugin.creative_engine.contracts import ShotBody
from drama_plugin.execution.transport import CapabilityAbsent


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    field_path: tuple[str | int, ...]
    error_type: str


class AuthorDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    role: AuthorRole = "direction"
    failure_stage: Literal["RESPONSE", "PROVIDER_PROTOCOL", "JSON_PARSE", "DTO_SCHEMA",
        "DIALOGUE_AUTHORITY", "SHOT_POST_VALIDATION", "INCOMPLETE_OUTPUT", "INTERNAL"]
    code: str
    exception_type: str | None = None
    validator: str | None = None
    issues: tuple[ValidationIssue, ...] = ()
    response_hash: str | None = None
    finish_reason: str | None = None
    model: str | None = None
    http_status: int | None = None
    usage: dict[str, int] = {}


# No mutable shared-client "last response" that could mix concurrent run evidence.
response_context: ContextVar[AuthorDiagnostic | None] = ContextVar("author_response_metadata", default=None)


class AuthorResultFailure(ValueError):
    def __init__(self, diagnostic: AuthorDiagnostic):
        super().__init__(diagnostic.code)
        self.diagnostic = diagnostic


class AuthorUnavailable(CapabilityAbsent):
    def __init__(self, diagnostic: AuthorDiagnostic):
        super().__init__(diagnostic.code)
        self.diagnostic = diagnostic


def failure(stage: str, code: str, *, role: AuthorRole = "direction", exception_type: str = "ValueError",
            field_path: tuple[str | int, ...] = (), validator: str | None = None) -> AuthorDiagnostic:
    prior = response_context.get()
    fields = prior.model_dump() if prior else {"role": role}
    return AuthorDiagnostic.model_validate({**fields, "failure_stage": stage, "code": code,
        "exception_type": exception_type, "validator": validator,
        "issues": ({"field_path": field_path, "error_type": code},) if field_path else ()})


def validation_failure(error: ValidationError, *, role: AuthorRole, post: bool = False) -> AuthorDiagnostic:
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
    # Unknown extra keys may themselves contain a secret. Keep a placeholder, not raw loc.
    issues = tuple(ValidationIssue(field_path=tuple(
        min(p, 1_000_000) if isinstance(p, int) else aliases.get(p, p) if p in allowed else "<extra>"
        for p in e["loc"]), error_type=e["type"]) for e in entries[:16])
    base = failure("SHOT_POST_VALIDATION" if post else "DTO_SCHEMA", "AUTHOR_DOMAIN_RESULT_INVALID",
        role=role, exception_type="ValidationError")
    return AuthorDiagnostic.model_validate({**base.model_dump(), "issues": issues})
