"""Translate T3 decisions into existing Runtime actions; no new Runtime states."""
from drama_plugin.governance.contracts import GateEffect as E
from drama_plugin.governance.policy import (
    ASSESS, BLOCK, REJECT, GovernedPolicy, governed_workflow,
)
from drama_plugin.governance.store import GateFindingStore
from drama_plugin.runtime.contracts import (
    ActionKind as A, ArtifactReference, RunMode, RuntimeAction, RuntimeRun, RuntimeState, RuntimeWorkflow,
)

WORKFLOW = "prepare-generation:v1"
COMPILE = "generation.compile:v1"
REBUILD = "generation.rebuild:v1"
RELEASE = "generation.release:v1"
READY = "generation.ready:v1"


class GenerationPolicy:
    def __init__(self, mode: RunMode, findings: GateFindingStore):
        self.governed = GovernedPolicy(mode, findings)
        self.findings = findings

    @property
    def mode(self):
        return self.governed.mode

    @property
    def policy_id(self):
        return self.governed.policy_id

    @property
    def max_step_attempts(self):
        return self.governed.max_step_attempts

    def next_action(self, run: RuntimeRun, workflow: RuntimeWorkflow) -> RuntimeAction:
        if workflow.workflow_id != WORKFLOW:
            return self.governed.next_action(run, workflow)
        if run.cursor in {1, 2}:
            return self.governed.next_action(run, governed_workflow())
        if run.cursor not in {4, 5, 6} or run.state not in {RuntimeState.READY, RuntimeState.WAITING_USER}:
            return self.governed.foundation.next_action(run, workflow)
        ref = self.findings.latest(run.run_id)
        decision = self.findings.decision(ref)
        if decision.scope != run.scope or decision.mode != run.mode:
            raise ValueError("Execution governance scope/mode mismatch")
        if decision.effect == E.BLOCK:
            return RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=BLOCK, input_refs=(ref,))
        if decision.effect == E.LEGACY_REJECT:
            return RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=REJECT, input_refs=(ref,))
        if decision.effect == E.AUTO_MAINTAIN:
            return RuntimeAction(kind=A.AUTO_MAINTENANCE, capability_key=REBUILD, input_refs=(ref,))
        if decision.effect == E.WAIT_USER:
            return RuntimeAction(kind=A.REQUEST_USER_DECISION, decision=decision.user_decision)
        if decision.effect in {E.CAPABILITY_ABSENT, E.REVIEW_REQUIRED}:
            return RuntimeAction(kind=A.WAIT_EXTERNAL, external_ref=ArtifactReference(
                owner="capability-absence" if decision.effect == E.CAPABILITY_ABSENT else "quality-review",
                artifact_ref=ref.artifact_ref, version=1))
        return RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=READY if run.cursor == 6 else RELEASE,
                             input_refs=(ref,))


def generation_workflow() -> RuntimeWorkflow:
    return RuntimeWorkflow(workflow_id=WORKFLOW, steps=(
        RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=ASSESS),
        RuntimeAction(kind=A.CALL_CAPABILITY, capability_key="governance.resolve:v1"),
        RuntimeAction(kind=A.CALL_CAPABILITY, capability_key="production.inspect_package:v1"),
        RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=COMPILE, input_from_previous=True),
        RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=RELEASE),
        RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=RELEASE),
        RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=READY),
    ))
