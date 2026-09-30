"""Target native assembly and a ref-only local consumer. STOP AT T2."""
from __future__ import annotations

from drama_plugin.production.assembler import ShotAssembler
from drama_plugin.production.store import ProductionPackageStore
from drama_plugin.runtime.capabilities import TargetCapability
from drama_plugin.runtime.contracts import (
    ActionKind, ArtifactReference, CapabilityInput, CapabilityResult, ResultStatus,
    RuntimeAction, RuntimeWorkflow,
)
from drama_plugin.runtime.store import InMemoryRunStore

ASSEMBLE = "production.assemble_package:v1"
INSPECT = "production.inspect_package:v1"
PREPARE_SHOT = "prepare-shot:v1"


class ProductionPackageCapability:
    """Only runtime mode/identity and package references cross the runtime boundary."""
    def __init__(self, assembler: ShotAssembler, packages: ProductionPackageStore,
                 runs: InMemoryRunStore) -> None:
        self.assembler, self.packages, self.runs = assembler, packages, runs

    async def assemble(self, inputs: CapabilityInput) -> CapabilityResult:
        run = self.runs.load(inputs.run_id)
        if inputs.scope != run.scope or inputs.input_refs:
            return CapabilityResult(status=ResultStatus.FAILED, code="ASSEMBLY_SCOPE_OR_SIDELOAD_INVALID")
        assembled = await self.assembler.assemble(inputs.scope, mode=run.mode,
            policy_ref=ArtifactReference(owner="runtime-policy", artifact_ref=run.policy_id, version=1))
        if assembled.package is None:
            return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="ASSEMBLY_UNRESOLVED",
                artifact_refs=(self.packages.retain_validation(assembled.validation, scope=run.scope),))
        return CapabilityResult(status=ResultStatus.SUCCEEDED,
            artifact_refs=(self.packages.put(assembled.package),))

    async def inspect(self, inputs: CapabilityInput) -> CapabilityResult:
        if len(inputs.input_refs) != 1:
            return CapabilityResult(status=ResultStatus.FAILED, code="PACKAGE_REFERENCE_REQUIRED")
        try:
            package = self.packages.get(inputs.input_refs[0])
        except (KeyError, ValueError):
            return CapabilityResult(status=ResultStatus.FAILED, code="PACKAGE_STORE_RESTORE_REQUIRED")
        run = self.runs.load(inputs.run_id)
        if (package.scope.work.artifact_ref, package.scope.scene.artifact_ref, package.scope.shot.artifact_ref) != (
            inputs.scope.work_id, inputs.scope.scene_id, inputs.scope.shot_id,
        ) or inputs.scope != run.scope or package.boundary.mode != run.mode:
            return CapabilityResult(status=ResultStatus.FAILED, code="PACKAGE_SCOPE_OR_MODE_MISMATCH")
        return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=inputs.input_refs)

    def registrations(self) -> dict[str, TargetCapability]:
        return {ASSEMBLE: TargetCapability(self.assemble, replay_safe=True),
                INSPECT: TargetCapability(self.inspect, replay_safe=True)}


def assembly_workflow() -> RuntimeWorkflow:
    return RuntimeWorkflow(workflow_id=PREPARE_SHOT, steps=(
        RuntimeAction(kind=ActionKind.CALL_CAPABILITY, capability_key=ASSEMBLE),
        RuntimeAction(kind=ActionKind.CALL_CAPABILITY, capability_key=INSPECT, input_from_previous=True),
    ))
