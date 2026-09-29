"""Translate governed effects into existing Runtime actions; one loop for both modes."""
from __future__ import annotations

from drama_plugin.governance.contracts import GateEffect as E
from drama_plugin.governance.store import GateFindingStore
from drama_plugin.runtime.contracts import (
    ActionKind as A, ArtifactReference, RunMode, RuntimeAction, RuntimeRun, RuntimeState,
    RuntimeWorkflow,
)
from drama_plugin.runtime.policy import FoundationPolicy

WORKFLOW = "govern-shot:v1"
ASSESS = "governance.assess_package:v1"
RESOLVE = "governance.resolve:v1"
MAINTAIN = "governance.reassemble_package:v1"
RELEASE = "governance.release_package:v1"
BLOCK = "governance.block:v1"
REJECT = "governance.reject_legacy:v1"


class GovernedPolicy:
    def __init__(self, mode: RunMode, findings: GateFindingStore):
        self.foundation = FoundationPolicy(mode)
        self.findings = findings

    @property
    def mode(self) -> RunMode:
        return self.foundation.mode

    @property
    def policy_id(self) -> str:
        return self.foundation.policy_id  # Preserve T1/T2 checkpoint and Package policy identities.

    @property
    def max_step_attempts(self) -> int:
        return self.foundation.max_step_attempts

    def next_action(self, run: RuntimeRun, workflow: RuntimeWorkflow) -> RuntimeAction:
        if workflow.workflow_id != WORKFLOW or run.cursor not in {1, 2} or run.state not in {
            RuntimeState.READY, RuntimeState.WAITING_USER,
        }:
            return self.foundation.next_action(run, workflow)
        ref = self.findings.latest(run.run_id)
        decision = self.findings.decision(ref)
        if decision.scope != run.scope or decision.mode != run.mode:
            raise ValueError("Governance decision belongs to another scope or mode")
        # Cursor two follows a resolved maintenance, real user decision, or external dependency.
        resolved_dependency = decision.effect in {E.WAIT_USER, E.CAPABILITY_ABSENT, E.REVIEW_REQUIRED} and (
            run.last_result is not None and run.last_result.artifact_refs != (ref,))
        if run.cursor == 2 and (decision.effect == E.CONTINUE or resolved_dependency):
            return RuntimeAction(kind=A.CALL_CAPABILITY, capability_key="production.inspect_package:v1",
                                 input_refs=(decision.package_ref,) if decision.package_ref else ())
        if decision.effect == E.BLOCK:
            return RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=BLOCK, input_refs=(ref,))
        if decision.effect == E.LEGACY_REJECT:
            return RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=REJECT, input_refs=(ref,))
        if decision.effect == E.AUTO_MAINTAIN:
            return RuntimeAction(kind=A.AUTO_MAINTENANCE, capability_key=MAINTAIN, input_refs=(ref,))
        if decision.effect == E.WAIT_USER:
            return RuntimeAction(kind=A.REQUEST_USER_DECISION, decision=decision.user_decision)
        if decision.effect in {E.CAPABILITY_ABSENT, E.REVIEW_REQUIRED}:
            owner = "capability-absence" if decision.effect == E.CAPABILITY_ABSENT else "quality-review"
            return RuntimeAction(kind=A.WAIT_EXTERNAL,
                external_ref=ArtifactReference(owner=owner, artifact_ref=ref.artifact_ref, version=1))
        return RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=RELEASE, input_refs=(ref,))


def governed_workflow() -> RuntimeWorkflow:
    return RuntimeWorkflow(workflow_id=WORKFLOW, steps=(
        RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=ASSESS),
        RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=RESOLVE),
        RuntimeAction(kind=A.CALL_CAPABILITY, capability_key="production.inspect_package:v1"),
    ))
