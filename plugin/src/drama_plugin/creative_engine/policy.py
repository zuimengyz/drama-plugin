"""Registered E2 actions; this policy selects owners, never creative content."""
from drama_plugin.creative_engine.capability import PREFIX
from drama_plugin.generation.policy import GenerationPolicy
from drama_plugin.runtime.contracts import (
    ActionKind as A, DecisionCategory, RunMode, RuntimeAction, RuntimeRun, RuntimeState,
    RuntimeWorkflow, UserDecisionRequest,
)

WORKFLOW = "source-to-approved-package:v1"
CHILD_WORKFLOW = "reference-prerequisite:v1"


def creative_workflow() -> RuntimeWorkflow:
    steps = tuple(RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=PREFIX + key + ":v1")
                  for key in ("source", "canon", "direction", "professional", "route", "review"))
    return RuntimeWorkflow(workflow_id=WORKFLOW, steps=(*steps,
        RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=PREFIX + "review:v1"),
        RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=PREFIX + "adoption:v1"),
        RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=PREFIX + "package:v1")))


def dependency_workflow() -> RuntimeWorkflow:
    return RuntimeWorkflow(workflow_id=CHILD_WORKFLOW, steps=(
        RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=PREFIX + "prerequisite:v1"),))


class CreativePolicy(GenerationPolicy):
    def next_action(self, run: RuntimeRun, workflow: RuntimeWorkflow) -> RuntimeAction:
        if workflow.workflow_id != WORKFLOW:
            return super().next_action(run, workflow)
        if run.cursor == 6 and run.mode == RunMode.EXPERIMENT and run.state == RuntimeState.READY:
            return RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=PREFIX + "review:v1")
        if run.cursor == 6 and run.mode == RunMode.PRODUCTION and run.state in {RuntimeState.READY, RuntimeState.WAITING_USER}:
            decision = self.findings.decision(self.findings.latest(run.run_id))
            if decision.scope != run.scope or decision.user_decision is None:
                raise ValueError("Adoption decision scope/category mismatch")
            return RuntimeAction(kind=A.REQUEST_USER_DECISION, decision=decision.user_decision)
        return self.governed.foundation.next_action(run, workflow)
