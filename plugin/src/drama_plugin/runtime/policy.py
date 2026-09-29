"""Mode/policy boundary. T1 does not migrate any existing production Gate policy."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from drama_plugin.runtime.contracts import (
    ActionKind, RunMode, RuntimeAction, RuntimeRun, RuntimeState, RuntimeWorkflow,
)


class RuntimePolicy(Protocol):
    @property
    def mode(self) -> RunMode: ...

    @property
    def policy_id(self) -> str: ...

    @property
    def max_step_attempts(self) -> int: ...

    def next_action(self, run: RuntimeRun, workflow: RuntimeWorkflow) -> RuntimeAction: ...


@dataclass(frozen=True)
class FoundationPolicy:
    mode: RunMode
    max_step_attempts: int = 2

    def __post_init__(self) -> None:
        if not isinstance(self.mode, RunMode) or self.max_step_attempts < 1:
            raise ValueError("Policy requires a RunMode and positive attempt bound")

    @property
    def policy_id(self) -> str:
        return f"runtime-t1:{self.mode.value.lower()}:v1:attempts-{self.max_step_attempts}"

    def next_action(self, run: RuntimeRun, workflow: RuntimeWorkflow) -> RuntimeAction:
        if run.mode != self.mode or run.policy_id != self.policy_id:
            raise ValueError("Runtime policy identity mismatch")
        if run.state == RuntimeState.SUCCEEDED:
            return RuntimeAction(kind=ActionKind.COMPLETE)
        if run.state in {RuntimeState.FAILED, RuntimeState.BLOCKED}:
            return RuntimeAction(kind=ActionKind.STOP, reason=run.wait_reason or "RUN_FAILED")
        if run.state == RuntimeState.RUNNING:
            return RuntimeAction(kind=ActionKind.STOP, reason="CAPABILITY_IN_FLIGHT")
        if run.state == RuntimeState.WAITING_EXTERNAL:
            assert run.last_result is not None
            return RuntimeAction(kind=ActionKind.WAIT_EXTERNAL, external_ref=run.last_result.external_ref)
        if run.cursor == len(workflow.steps):
            return RuntimeAction(kind=ActionKind.COMPLETE)
        return workflow.steps[run.cursor]


def default_policies() -> dict[RunMode, RuntimePolicy]:
    return {mode: FoundationPolicy(mode) for mode in RunMode}
