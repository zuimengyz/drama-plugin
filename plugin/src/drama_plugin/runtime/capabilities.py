"""Explicit target-native dispatch with a separate migration-only legacy fallback."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from drama_plugin.runtime.bridge import CapabilityExecutor
from drama_plugin.runtime.contracts import CapabilityInput, CapabilityResult


@dataclass(frozen=True)
class TargetCapability:
    handler: Callable[[CapabilityInput], Awaitable[CapabilityResult]]
    replay_safe: bool = False


class TargetCapabilityRouter:
    lifecycle = "TARGET_NATIVE"

    def __init__(self, native: Mapping[str, TargetCapability], legacy: CapabilityExecutor):
        self._native = dict(native)
        self.legacy = legacy

    async def execute(self, capability_key: str, inputs: CapabilityInput) -> CapabilityResult:
        capability = self._native.get(capability_key)
        if capability is not None:
            return CapabilityResult.model_validate(await capability.handler(inputs))
        return await self.legacy.execute(capability_key, inputs)

    def replay_safe(self, capability_key: str) -> bool:
        capability = self._native.get(capability_key)
        return capability.replay_safe if capability is not None else self.legacy.replay_safe(capability_key)
