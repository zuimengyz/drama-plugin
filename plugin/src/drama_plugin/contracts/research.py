from pydantic import Field

from drama_plugin.contracts.base import ContractModel


class ResearchSource(ContractModel):
    title: str
    citation: str
    source_type: str


class ResearchEvidence(ContractModel):
    claim: str
    excerpt: str
    source: ResearchSource
    confidence: float
    tags: list[str] = Field(default_factory=list)


class ClaimAssessment(ContractModel):
    claim: str
    supported: bool
    evidence: list[ResearchEvidence] = Field(default_factory=list)
    rationale: str
