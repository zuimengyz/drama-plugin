"""Target-native dispatch with a named, read-only migration door."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from drama_plugin.runtime.bridge import CapabilityExecutor
from drama_plugin.runtime.contracts import CapabilityInput, CapabilityResult, ResultStatus
from drama_plugin.runtime.legacy_boundary import (
    LegacyAccessDecision, LegacyAccessRequest, LegacyBoundary, LegacyOrigin, LegacyPurpose,
)


@dataclass(frozen=True)
class TargetCapability:
    handler: Callable[[CapabilityInput], Awaitable[CapabilityResult]]
    replay_safe: bool = False


class TargetCapabilityRouter:
    lifecycle = "TARGET"

    def __init__(self, native: Mapping[str, TargetCapability], legacy: CapabilityExecutor,
                 boundary: LegacyBoundary | None = None):
        self._native = dict(native)
        self.legacy = legacy
        self.boundary = boundary if boundary is not None else LegacyBoundary()

    @property
    def native_keys(self) -> frozenset[str]:
        return frozenset(self._native)

    @property
    def migration_keys(self) -> frozenset[str]:
        return self.boundary.migration_reads

    async def execute(self, capability_key: str, inputs: CapabilityInput) -> CapabilityResult:
        capability = self._native.get(capability_key)
        if capability is not None:
            return CapabilityResult.model_validate(await capability.handler(inputs))
        decision = self.boundary.decide(LegacyAccessRequest(
            origin=LegacyOrigin.TARGET, work_id=inputs.scope.work_id,
            run_id=inputs.run_id, capability=capability_key, purpose=LegacyPurpose.READ_ONLY))
        if decision == LegacyAccessDecision.ALLOW_READ_ONLY:
            return await self.legacy.execute(capability_key, inputs)
        return CapabilityResult(status=ResultStatus.FAILED, code="LEGACY_GUARD")

    def replay_safe(self, capability_key: str) -> bool:
        capability = self._native.get(capability_key)
        if capability is not None:
            return capability.replay_safe
        return capability_key in self.migration_keys and self.legacy.replay_safe(capability_key)
