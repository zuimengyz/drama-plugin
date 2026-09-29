"""MIGRATION_ONLY: explicitly opt safe legacy capabilities into the new loop."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

from drama_plugin.runtime.contracts import (
    ArtifactReference, CapabilityInput, CapabilityResult, ResultStatus,
)
from drama_plugin.tools.registry import ToolRegistry


class CapabilityExecutor(Protocol):
    async def execute(self, capability_key: str, inputs: CapabilityInput) -> CapabilityResult: ...

    def replay_safe(self, capability_key: str) -> bool: ...


@dataclass(frozen=True)
class LegacyCapability:
    handler: Callable[[CapabilityInput], Awaitable[CapabilityResult]]
    replay_safe: bool = False


class LegacyCapabilityBridge:
    """No wildcard tools/paid dispatch; each handler returns pointers, never Canon text.

    Registrations are trusted Plugin code. replay_safe is a declaration by that
    adapter, not a claim that arbitrary user functions can be sandboxed here.
    """
    lifecycle = "MIGRATION_ONLY"

    def __init__(self, capabilities: Mapping[str, LegacyCapability]) -> None:
        self._capabilities = dict(capabilities)

    def replay_safe(self, capability_key: str) -> bool:
        capability = self._capabilities.get(capability_key)
        return capability is not None and capability.replay_safe

    async def execute(self, capability_key: str, inputs: CapabilityInput) -> CapabilityResult:
        capability = self._capabilities.get(capability_key)
        if capability is None:
            return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="CAPABILITY_NOT_REGISTERED")
        result = await capability.handler(inputs)
        # Revalidate even constructed or incorrectly typed adapter output.
        return CapabilityResult.model_validate(result)

    @classmethod
    def from_tools(cls, tools: ToolRegistry) -> LegacyCapabilityBridge:
        async def read_work(inputs: CapabilityInput) -> CapabilityResult:
            work = await tools.invoke("work.get_work", work_id=inputs.scope.work_id)
            if work.id != inputs.scope.work_id:
                return CapabilityResult(status=ResultStatus.FAILED, code="WORK_IDENTITY_MISMATCH")
            return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(
                ArtifactReference(owner="work", artifact_ref=work.id, version=work.version),
            ))

        return cls({"work.get_work": LegacyCapability(read_work, replay_safe=True)})
