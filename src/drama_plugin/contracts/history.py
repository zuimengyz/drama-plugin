from __future__ import annotations

from drama_plugin.contracts.base import ContractModel


class HistoricalSource(ContractModel):
    id: str
    title: str
    citation: str
    source_type: str


class HistoricalEvidence(ContractModel):
    id: str
    source_id: str
    claim: str
    excerpt: str
    confidence: float
    tags: list[str] = []


class ClaimVerification(ContractModel):
    claim: str
    supported: bool
    evidence_ids: list[str] = []
    rationale: str
