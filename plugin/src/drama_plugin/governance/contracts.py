"""Six finding categories, four risk families; no unbounded diagnostic payloads."""
from __future__ import annotations

from enum import Enum
from typing import Self

from pydantic import Field, model_validator

from drama_plugin.runtime.contracts import (
    ArtifactReference, DecisionCategory, Identifier, RunMode, RuntimeContract,
    RuntimeScope, UserDecisionRequest, ExtendedRuntimeContract,
)


class GateCategory(str, Enum):
    HARD_STOP = "HARD_STOP"
    AUTO_MAINTENANCE = "AUTO_MAINTENANCE"
    WARNING = "WARNING"
    USER_DECISION = "USER_DECISION"
    CAPABILITY_ABSENT = "CAPABILITY_ABSENT"
    LEGACY_GUARD = "LEGACY_GUARD"


class HardStopFamily(str, Enum):
    HS1 = "HS1"
    HS2 = "HS2"
    HS3 = "HS3"
    HS4 = "HS4"


class GateCode(str, Enum):
    PACKAGE_SCOPE_MISMATCH = "PACKAGE_SCOPE_MISMATCH"
    CANON_AUTHORITY_MISMATCH = "CANON_AUTHORITY_MISMATCH"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    COST_UNAUTHORIZED = "COST_UNAUTHORIZED"
    SUBMISSION_UNCERTAIN = "SUBMISSION_UNCERTAIN"
    OPERATION_IDENTITY_MISMATCH = "OPERATION_IDENTITY_MISMATCH"
    REQUEST_INPUT_MISSING = "REQUEST_INPUT_MISSING"
    REQUEST_UNSUPPORTED = "REQUEST_UNSUPPORTED"
    PROVIDER_HARD_LIMIT = "PROVIDER_HARD_LIMIT"
    PACKAGE_STALE = "PACKAGE_STALE"
    HASH_REFRESH = "HASH_REFRESH"
    BINDING_REFRESH = "BINDING_REFRESH"
    RECEIPT_RECONCILIATION = "RECEIPT_RECONCILIATION"
    CHECKPOINT_REFRESH = "CHECKPOINT_REFRESH"
    DERIVED_REFRESH = "DERIVED_REFRESH"
    RETRY_BOOKKEEPING = "RETRY_BOOKKEEPING"
    OPTIONAL_SOURCE_MISSING = "OPTIONAL_SOURCE_MISSING"
    QUALITY_COVERAGE_RISK = "QUALITY_COVERAGE_RISK"
    CONTINUITY_RISK = "CONTINUITY_RISK"
    ART_APPROVAL_REQUIRED = "ART_APPROVAL_REQUIRED"
    COST_APPROVAL_REQUIRED = "COST_APPROVAL_REQUIRED"
    MAJOR_ADAPTATION_REQUIRED = "MAJOR_ADAPTATION_REQUIRED"
    ADOPTION_REQUIRED = "ADOPTION_REQUIRED"
    FINAL_ACCEPTANCE_REQUIRED = "FINAL_ACCEPTANCE_REQUIRED"
    CAPABILITY_NOT_IMPLEMENTED = "CAPABILITY_NOT_IMPLEMENTED"
    LEGACY_ENTRY_REJECTED = "LEGACY_ENTRY_REJECTED"


# Only this closed vocabulary can grant stopping or user-decision authority.
RULES: dict[GateCode, tuple[GateCategory, HardStopFamily | None, DecisionCategory | None]] = {}
codes: tuple[GateCode, ...]
for family, codes in (
    (HardStopFamily.HS1, (GateCode.PACKAGE_SCOPE_MISMATCH, GateCode.CANON_AUTHORITY_MISMATCH)),
    (HardStopFamily.HS2, (GateCode.BUDGET_EXCEEDED, GateCode.COST_UNAUTHORIZED)),
    (HardStopFamily.HS3, (GateCode.SUBMISSION_UNCERTAIN, GateCode.OPERATION_IDENTITY_MISMATCH)),
    (HardStopFamily.HS4, (GateCode.REQUEST_INPUT_MISSING, GateCode.REQUEST_UNSUPPORTED, GateCode.PROVIDER_HARD_LIMIT)),
):
    for code in codes:
        RULES[code] = (GateCategory.HARD_STOP, family, None)
for category, codes in (
    (GateCategory.AUTO_MAINTENANCE, (GateCode.PACKAGE_STALE, GateCode.HASH_REFRESH,
        GateCode.BINDING_REFRESH, GateCode.RECEIPT_RECONCILIATION, GateCode.CHECKPOINT_REFRESH,
        GateCode.DERIVED_REFRESH, GateCode.RETRY_BOOKKEEPING)),
    (GateCategory.WARNING, (GateCode.OPTIONAL_SOURCE_MISSING, GateCode.QUALITY_COVERAGE_RISK, GateCode.CONTINUITY_RISK)),
    (GateCategory.CAPABILITY_ABSENT, (GateCode.CAPABILITY_NOT_IMPLEMENTED,)),
    (GateCategory.LEGACY_GUARD, (GateCode.LEGACY_ENTRY_REJECTED,)),
):
    for code in codes:
        RULES[code] = (category, None, None)
for code, decision in (
    (GateCode.ART_APPROVAL_REQUIRED, DecisionCategory.ART_APPROVAL),
    (GateCode.COST_APPROVAL_REQUIRED, DecisionCategory.COST_APPROVAL),
    (GateCode.MAJOR_ADAPTATION_REQUIRED, DecisionCategory.MAJOR_ADAPTATION),
    (GateCode.ADOPTION_REQUIRED, DecisionCategory.ADOPTION),
    (GateCode.FINAL_ACCEPTANCE_REQUIRED, DecisionCategory.FINAL_ACCEPTANCE),
):
    RULES[code] = (GateCategory.USER_DECISION, None, decision)


class GateFinding(RuntimeContract):
    code: GateCode
    category: GateCategory
    owner: Identifier
    scope: RuntimeScope
    evidence_ref: ArtifactReference
    risk_family: HardStopFamily | None = None
    # Required delivery quality may need review; it never acquires HARD_STOP authority.
    required: bool = False

    @model_validator(mode="after")
    def authority(self) -> Self:
        category, family, _ = RULES[self.code]
        if (self.category, self.risk_family) != (category, family):
            raise ValueError("Finding code cannot acquire another category or stopping authority")
        return self

    @classmethod
    def classified(cls, code: GateCode, *, owner: str, scope: RuntimeScope,
                   evidence_ref: ArtifactReference, required: bool = False) -> GateFinding:
        category, family, _ = RULES[code]
        return cls(code=code, category=category, risk_family=family, owner=owner,
                   scope=scope, evidence_ref=evidence_ref, required=required)


class GateEffect(str, Enum):
    CONTINUE = "CONTINUE"
    AUTO_MAINTAIN = "AUTO_MAINTAIN"
    WAIT_USER = "WAIT_USER"
    BLOCK = "BLOCK"
    CAPABILITY_ABSENT = "CAPABILITY_ABSENT"
    LEGACY_REJECT = "LEGACY_REJECT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class GateDecision(RuntimeContract):
    scope: RuntimeScope
    mode: RunMode
    effect: GateEffect
    finding_refs: tuple[ArtifactReference, ...] = Field(default=(), max_length=32)
    risk_families: tuple[HardStopFamily, ...] = Field(default=(), max_length=4)
    package_ref: ArtifactReference | None = None
    user_decision: UserDecisionRequest | None = None

    @model_validator(mode="after")
    def decision_shape(self) -> Self:
        if (self.effect == GateEffect.BLOCK) != bool(self.risk_families):
            raise ValueError("Only HARD_STOP decisions may name risk families")
        if tuple(sorted(set(self.risk_families))) != self.risk_families:
            raise ValueError("Risk families must be unique and canonical")
        if (self.effect == GateEffect.WAIT_USER) != (self.user_decision is not None):
            raise ValueError("Only genuine user decisions can request approval")
        if self.effect == GateEffect.CONTINUE and self.package_ref is None:
            raise ValueError("Continuation needs its production package")
        return self


class GovernanceInput(ExtendedRuntimeContract):
    extension_fields = ("decision_ref",)
    package_ref: ArtifactReference | None = None
    finding_refs: tuple[ArtifactReference, ...] = Field(default=(), max_length=24)
    decision_ref: ArtifactReference | None = None
