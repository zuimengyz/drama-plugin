"""Small immutable user decision receipt; never a Creative Canon revision."""
from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import JsonValue, StringConstraints, model_validator

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.creative_asset import Hash
from drama_plugin.runtime.contracts import (
    ArtifactReference, DecisionCategory, Identifier, RuntimeContract, RuntimeScope,
)
from drama_plugin.runtime.contracts import ExtendedRuntimeContract


class UserDecisionRecord(ExtendedRuntimeContract):
    extension_fields = ("terms_hash", "financial_terms")
    schema_version: Literal["user-decision-v1"] = "user-decision-v1"
    run_id: Identifier
    scope: RuntimeScope
    decision_id: Annotated[str, StringConstraints(min_length=1, max_length=260, pattern=r"^\S+$")]
    category: DecisionCategory
    accepted: bool
    source_ref: ArtifactReference | None = None
    fingerprint: Hash
    terms_hash: Hash | None = None
    financial_terms: dict[str, JsonValue] | None = None

    @classmethod
    def seal(cls, *, run_id: str, scope: RuntimeScope, decision_id: str,
             category: DecisionCategory, accepted: bool,
             source_ref: ArtifactReference | None = None, terms_hash: str | None = None,
             financial_terms: dict[str, JsonValue] | None = None) -> UserDecisionRecord:
        fields = dict(run_id=run_id, scope=scope, decision_id=decision_id,
            category=category, accepted=accepted, source_ref=source_ref, terms_hash=terms_hash, financial_terms=financial_terms)
        checked = cls.model_validate({**fields, "fingerprint": "0" * 64}, context="sealing")
        return cls.model_validate({**checked.model_dump(exclude={"fingerprint"}),
            "fingerprint": sha256_canonical(checked.model_dump(mode="json", by_alias=True,
                exclude={"fingerprint"}))})

    @model_validator(mode="after")
    def identity(self, info) -> Self:
        if self.financial_terms is not None:
            from drama_plugin.execution.live_transport import FinancialTerms
            terms = FinancialTerms.model_validate(self.financial_terms)
            if (self.category != DecisionCategory.COST_APPROVAL or self.terms_hash != terms.fingerprint
                    or self.source_ref != terms.preparation_ref):
                raise ValueError("Cost receipt must retain its exact reviewed financial terms")
        if self.decision_id != f"{self.run_id}:{self.decision_id.rsplit(':', 1)[-1]}":
            raise ValueError("User decision identity must belong to its Run")
        if info.context != "sealing" and self.fingerprint != sha256_canonical(
                self.model_dump(mode="json", by_alias=True, exclude={"fingerprint"})):
            raise ValueError("User decision receipt fingerprint mismatch")
        return self

    def artifact_reference(self) -> ArtifactReference:
        return ArtifactReference(owner="user-decision", artifact_ref="user-decision:" + self.fingerprint, version=1)
