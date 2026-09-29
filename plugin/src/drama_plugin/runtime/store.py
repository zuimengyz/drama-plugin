"""IN_MEMORY / TEST FOUNDATION, not the future durable ProductionLedger."""
from __future__ import annotations

import asyncio

from drama_plugin.runtime.contracts import RuntimeRun


class InMemoryRunStore:
    """One process/event loop; shared instances serialize access to each run."""
    durability = "IN_MEMORY_TEST_FOUNDATION"

    def __init__(self) -> None:
        self._runs: dict[str, RuntimeRun] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def create(self, run: RuntimeRun) -> RuntimeRun:
        if run.run_id in self._runs:
            raise ValueError("Runtime run already exists")
        validated = RuntimeRun.model_validate(run.model_dump())
        self._runs[run.run_id] = validated
        self._locks[run.run_id] = asyncio.Lock()
        return validated

    def load(self, run_id: str) -> RuntimeRun:
        return self._runs[run_id]

    def lock(self, run_id: str) -> asyncio.Lock:
        return self._locks[run_id]

    def save(self, run: RuntimeRun, *, expected_revision: int) -> RuntimeRun:
        previous = self.load(run.run_id)
        if previous.revision != expected_revision or run.revision != expected_revision + 1:
            raise ValueError("Runtime revision conflict")
        for field in ("scope", "mode", "policy_id", "workflow_id", "workflow_fingerprint", "schema_version"):
            if getattr(previous, field) != getattr(run, field):
                raise ValueError("Runtime identity is immutable")
        validated = RuntimeRun.model_validate(run.model_dump())
        self._runs[run.run_id] = validated
        return validated
