"""Target-native dispatch with a named, read-only migration door."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from drama_plugin.runtime.bridge import CapabilityAvailability, CapabilityExecutor
from drama_plugin.runtime.contracts import CapabilityInput, CapabilityResult, ExecutionInspection, ResultStatus
from drama_plugin.runtime.legacy_boundary import (
    LegacyAccessDecision, LegacyAccessRequest, LegacyBoundary, LegacyOrigin, LegacyPurpose,
)


@dataclass(frozen=True)
class TargetCapability:
    handler: Callable[[CapabilityInput], Awaitable[CapabilityResult]]
    replay_safe: bool = False
    inspect_execution: Callable[[CapabilityInput], ExecutionInspection | None] | None = None


class TargetCapabilityRouter:
    lifecycle = "TARGET"

    def __init__(self, native: Mapping[str, TargetCapability], legacy: CapabilityExecutor | None = None,
                 boundary: LegacyBoundary | None = None):
        self._native = dict(native)
        self.legacy = legacy
        self.boundary = boundary if boundary is not None else LegacyBoundary()

    @property
    def native_keys(self) -> frozenset[str]:
        return frozenset(self._native)

    @property
    def migration_keys(self) -> frozenset[str]:
        return self.boundary.migration_reads if self.legacy else frozenset()

    def availability(self, capability_key: str) -> bool:
        if capability_key in self._native:
            return True
        if self.legacy is None or capability_key not in self.migration_keys:
            return False
        if isinstance(self.legacy, CapabilityAvailability):
            return self.legacy.availability(capability_key)
        # Older explicit read-only executors retain their existing contract.
        return True

    async def execute(self, capability_key: str, inputs: CapabilityInput) -> CapabilityResult:
        capability = self._native.get(capability_key)
        if capability is not None:
            return CapabilityResult.model_validate(await capability.handler(inputs))
        decision = self.boundary.decide(LegacyAccessRequest(
            origin=LegacyOrigin.TARGET, work_id=inputs.scope.work_id,
            run_id=inputs.run_id, capability=capability_key, purpose=LegacyPurpose.READ_ONLY))
        if decision == LegacyAccessDecision.ALLOW_READ_ONLY and self.legacy is not None:
            return await self.legacy.execute(capability_key, inputs)
        return CapabilityResult(status=ResultStatus.FAILED, code="LEGACY_GUARD")

    def replay_safe(self, capability_key: str) -> bool:
        capability = self._native.get(capability_key)
        if capability is not None:
            return capability.replay_safe
        return self.legacy is not None and capability_key in self.migration_keys and self.legacy.replay_safe(capability_key)

    def inspect_execution(self, capability_key: str, inputs: CapabilityInput) -> ExecutionInspection | None:
        capability = self._native.get(capability_key)
        if capability is None or capability.inspect_execution is None:
            return None
        inspection = capability.inspect_execution(inputs)
        return ExecutionInspection.model_validate(inspection) if inspection is not None else None
