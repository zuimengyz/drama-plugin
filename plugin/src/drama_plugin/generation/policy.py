"""Translate T3 decisions into existing Runtime actions; no new Runtime states."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from drama_plugin.persistence.ledger import ProductionLedger
from drama_plugin.governance.contracts import GateEffect as E
from drama_plugin.governance.policy import (
    ASSESS, BLOCK, REJECT, GovernedPolicy, governed_workflow,
)
from drama_plugin.governance.store import GateFindingStore
from drama_plugin.runtime.contracts import (
    ActionKind as A, ArtifactReference, RunMode, RuntimeAction, RuntimeRun, RuntimeState, RuntimeWorkflow,
)

WORKFLOW = "prepare-generation:v1"
MEDIA_WORKFLOW = "package-to-reviewed-media:v1"
COMPILE = "generation.compile:v1"
REBUILD = "generation.rebuild:v1"
RELEASE = "generation.release:v1"
READY = "generation.ready:v1"


class GenerationPolicy:
    def __init__(self, mode: RunMode, findings: GateFindingStore):
        self.governed = GovernedPolicy(mode, findings)
        self.findings = findings
        self.mainline_ledger: ProductionLedger | None = None

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
        if workflow.workflow_id == MEDIA_WORKFLOW and run.cursor in {7, 8} and run.state in {RuntimeState.READY, RuntimeState.WAITING_USER}:
            from drama_plugin.runtime.contracts import DecisionCategory, UserDecisionRequest
            if self.mainline_ledger is None:
                raise ValueError("Durable production goal policy required")
            def optional(key: str) -> object | None:
                assert self.mainline_ledger
                try:
                    return self.mainline_ledger.get_index(key,run.run_id)
                except KeyError:
                    return None
            offline = optional("media-proof-authorization")
            terms = optional("media-proof-cost-terms")
            ref = self.mainline_ledger.get_index("prepared", run.run_id)
            if offline is None and terms is None:
                return RuntimeAction(kind=A.WAIT_EXTERNAL, external_ref=ArtifactReference.model_validate(ref))
            if run.cursor == 8 and (offline is None or run.state == RuntimeState.WAITING_USER):
                return RuntimeAction(kind=A.REQUEST_USER_DECISION, decision=UserDecisionRequest(
                    category=DecisionCategory.COST_APPROVAL,question="Approve the exact preparation, wire payload, quote and one-operation budget terms?"))
            return RuntimeAction(kind=A.CALL_CAPABILITY,capability_key=RELEASE,input_refs=(self.findings.latest(run.run_id),))
        if workflow.workflow_id not in {WORKFLOW, MEDIA_WORKFLOW}:
            return self.governed.next_action(run, workflow)
        if workflow.workflow_id == MEDIA_WORKFLOW and run.cursor >= 9:
            return self.governed.foundation.next_action(run, workflow)
        if run.cursor in {1, 2}:
            return self.governed.next_action(run, governed_workflow())
        if run.cursor not in {4, 5, 6} or run.state not in {RuntimeState.READY, RuntimeState.WAITING_USER}:
            return self.governed.foundation.next_action(run, workflow)
        ref = self.findings.latest(run.run_id)
        decision = self.findings.decision(ref)
        if workflow.workflow_id == MEDIA_WORKFLOW and run.cursor == 5 and decision.effect == E.WAIT_USER and run.last_result and run.last_result.artifact_refs != (ref,):
            return RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=COMPILE)
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


def media_review_workflow() -> RuntimeWorkflow:
    from drama_plugin.execution.capability import EXECUTE, INTAKE, REVIEW
    return RuntimeWorkflow(workflow_id=MEDIA_WORKFLOW, steps=(*generation_workflow().steps,
        RuntimeAction(kind=A.CALL_CAPABILITY,capability_key=RELEASE),
        RuntimeAction(kind=A.CALL_CAPABILITY,capability_key=RELEASE),
        *(RuntimeAction(kind=A.CALL_CAPABILITY,capability_key=k) for k in (EXECUTE,INTAKE,REVIEW))))
