"""IN_MEMORY_TEST_FOUNDATION; findings stay outside RuntimeRun and Creative Canon."""
from __future__ import annotations

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.governance.contracts import GateDecision, GateFinding, GovernanceInput
from drama_plugin.runtime.contracts import ArtifactReference


class GateFindingStore:
    durability = "IN_MEMORY_TEST_FOUNDATION"
    creative_authority = False

    def __init__(self) -> None:
        self._findings: dict[str, GateFinding] = {}
        self._decisions: dict[str, GateDecision] = {}
        self._inputs: dict[str, GovernanceInput] = {}
        self._latest: dict[str, ArtifactReference] = {}
        self._maintenance: dict[str, int] = {}

    def put_finding(self, finding: GateFinding) -> ArtifactReference:
        finding = GateFinding.model_validate(finding.model_dump())
        identity = "gate-finding:" + sha256_canonical(finding)
        self._findings[identity] = finding
        return ArtifactReference(owner="gate-finding", artifact_ref=identity, version=1)

    def finding(self, ref: ArtifactReference) -> GateFinding:
        if ref.owner != "gate-finding" or ref.version != 1:
            raise ValueError("Expected a finding reference")
        return self._findings[ref.artifact_ref]

    def put_decision(self, decision: GateDecision, *, run_id: str) -> ArtifactReference:
        decision = GateDecision.model_validate(decision.model_dump())
        identity = "gate-decision:" + sha256_canonical(decision)
        self._decisions[identity] = decision
        ref = ArtifactReference(owner="gate-decision", artifact_ref=identity, version=1)
        self._latest[run_id] = ref
        return ref

    def decision(self, ref: ArtifactReference) -> GateDecision:
        if ref.owner != "gate-decision" or ref.version != 1:
            raise ValueError("Expected a decision reference")
        return self._decisions[ref.artifact_ref]

    def latest(self, run_id: str) -> ArtifactReference:
        return self._latest[run_id]

    def bind(self, run_id: str, inputs: GovernanceInput) -> None:
        if run_id in self._inputs:
            raise ValueError("Governance inputs are already bound")
        self._inputs[run_id] = GovernanceInput.model_validate(inputs.model_dump())

    def inputs(self, run_id: str) -> GovernanceInput:
        return self._inputs.get(run_id, GovernanceInput())

    def set_package(self, run_id: str, ref: ArtifactReference) -> None:
        self._inputs[run_id] = GovernanceInput(package_ref=ref,
            finding_refs=self.inputs(run_id).finding_refs)

    def claim_maintenance(self, run_id: str) -> bool:
        if self._maintenance.get(run_id, 0) >= 1:
            return False
        self._maintenance[run_id] = 1
        return True

    def maintenance_count(self, run_id: str) -> int:
        return self._maintenance.get(run_id, 0)
