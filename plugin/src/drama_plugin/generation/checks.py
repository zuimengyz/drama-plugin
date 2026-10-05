"""Execution findings use the existing T3 closed policy vocabulary."""
from drama_plugin.generation.contracts import ExecutionDiagnostic
from drama_plugin.governance.contracts import GateCode as C, GateFinding
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeScope

MAPPING = {
    "SCOPE_DECISION_REQUIRED": C.ART_APPROVAL_REQUIRED,
    "PACKAGE_STALE": C.PACKAGE_STALE, "PROMPT_STALE": C.DERIVED_REFRESH,
    "SCOPE_MISMATCH": C.PACKAGE_SCOPE_MISMATCH, "DIALOGUE_IDENTITY_MISMATCH": C.CANON_AUTHORITY_MISMATCH,
    "GENERATOR_ABSENT": C.CAPABILITY_NOT_IMPLEMENTED, "TTS_CAPABILITY_ABSENT": C.CAPABILITY_NOT_IMPLEMENTED,
    "EXECUTION_REQUIRED_MISSING": C.REQUEST_INPUT_MISSING, "CREATIVE_SOURCE_INSUFFICIENT": C.REQUEST_INPUT_MISSING,
    "REFERENCE_MEDIA_PENDING": C.BINDING_REFRESH, "REFERENCE_INPUT_UNRESOLVED": C.REQUEST_INPUT_MISSING, "REQUEST_UNSUPPORTED": C.REQUEST_UNSUPPORTED,
    "HARD_LIMIT_OVERFLOW": C.PROVIDER_HARD_LIMIT, "OPTIONAL_COVERAGE": C.QUALITY_COVERAGE_RISK,
    "OPTIONAL_REFERENCE_UNRESOLVED": C.OPTIONAL_SOURCE_MISSING,
    "OPTIONAL_AMBIENCE_MISSING": C.OPTIONAL_SOURCE_MISSING,
}


def execution_findings(diagnostics: tuple[ExecutionDiagnostic, ...], *, scope: RuntimeScope,
                       evidence_ref: ArtifactReference) -> tuple[GateFinding, ...]:
    return tuple(GateFinding.classified(MAPPING[d.code], owner=d.owner, scope=scope, evidence_ref=evidence_ref,
        required=d.required) for d in diagnostics)
