"""Translate T3 decisions into existing Runtime actions; no new Runtime states."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from drama_plugin.persistence.ledger import ProductionLedger
from drama_plugin.governance.contracts import GateEffect as E
from drama_plugin.governance.policy import (
    ASSESS, BLOCK, REJECT, RESOLVE, GovernedPolicy, governed_workflow,
)
from drama_plugin.governance.store import FindingStore
from drama_plugin.runtime.contracts import (
    ActionKind as A, ArtifactReference, RunMode, RuntimeAction, RuntimeRun, RuntimeState, RuntimeWorkflow,
)

WORKFLOW = "prepare-generation:v1"
MEDIA_WORKFLOW = "package-to-reviewed-media:v2"
HISTORICAL_MEDIA_WORKFLOW = "package-to-reviewed-media:v1"
MEDIA_WORKFLOWS = frozenset({MEDIA_WORKFLOW, HISTORICAL_MEDIA_WORKFLOW})

def media_cursor(workflow_id: str, cursor: int) -> int:
    """Translate only immutable workflow positions, never stored Runtime state."""
    return cursor if workflow_id != MEDIA_WORKFLOW or cursor == 0 else cursor + 2
COMPILE = "generation.compile:v1"
REBUILD = "generation.rebuild:v1"
RELEASE = "generation.release:v1"
READY = "generation.ready:v1"


class GenerationPolicy:
    def __init__(self, mode: RunMode, findings: FindingStore):
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
        if workflow.workflow_id == MEDIA_WORKFLOW:
            if run.cursor == 1 and run.state in {RuntimeState.READY, RuntimeState.WAITING_USER}:
                decision = self.findings.decision(self.findings.latest(run.run_id))
                if decision.effect != E.CONTINUE:
                    return self.governed.next_action(run, governed_workflow())
            if media_cursor(workflow.workflow_id,run.cursor) == 7 and self.mainline_ledger is not None:
                for namespace in ("media-proof-authorization", "media-proof-cost-terms"):
                    try:
                        self.mainline_ledger.get_index(namespace,run.run_id)
                        break
                    except KeyError:
                        continue
                else:
                    return RuntimeAction(kind=A.CALL_CAPABILITY,capability_key=RELEASE,input_refs=(self.findings.latest(run.run_id),))
            historical_run = run.model_copy(update={"workflow_id": HISTORICAL_MEDIA_WORKFLOW,
                "cursor": media_cursor(workflow.workflow_id, run.cursor)})
            return self.next_action(historical_run, media_review_workflow(HISTORICAL_MEDIA_WORKFLOW))
        if workflow.workflow_id == HISTORICAL_MEDIA_WORKFLOW and run.cursor in {7, 8} and run.state in {RuntimeState.READY, RuntimeState.WAITING_USER}:
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
                if workflow.workflow_id == HISTORICAL_MEDIA_WORKFLOW and run.workflow_id == HISTORICAL_MEDIA_WORKFLOW:
                    # Existing historical wait checkpoints remain readable. New v2
                    # runs report a missing price authority in the existing owner.
                    return RuntimeAction(kind=A.WAIT_EXTERNAL, external_ref=ArtifactReference.model_validate(ref))
                return RuntimeAction(kind=A.CALL_CAPABILITY,capability_key=RELEASE,input_refs=(self.findings.latest(run.run_id),))
            if run.cursor == 8 and (offline is None or run.state == RuntimeState.WAITING_USER):
                return RuntimeAction(kind=A.REQUEST_USER_DECISION, decision=UserDecisionRequest(
                    category=DecisionCategory.COST_APPROVAL,question="Approve the exact preparation, wire payload, quote and one-operation budget terms?"))
            return RuntimeAction(kind=A.CALL_CAPABILITY,capability_key=RELEASE,input_refs=(self.findings.latest(run.run_id),))
        if workflow.workflow_id not in {WORKFLOW, HISTORICAL_MEDIA_WORKFLOW}:
            return self.governed.next_action(run, workflow)
        if workflow.workflow_id == HISTORICAL_MEDIA_WORKFLOW and run.cursor >= 9:
            return self.governed.foundation.next_action(run, workflow)
        if run.cursor in {1, 2}:
            return self.governed.next_action(run, governed_workflow())
        if run.cursor not in {4, 5, 6} or run.state not in {RuntimeState.READY, RuntimeState.WAITING_USER}:
            return self.governed.foundation.next_action(run, workflow)
        ref = self.findings.latest(run.run_id)
        decision = self.findings.decision(ref)
        if workflow.workflow_id == HISTORICAL_MEDIA_WORKFLOW and run.cursor == 5 and decision.effect == E.WAIT_USER and run.last_result and run.last_result.artifact_refs != (ref,):
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
            return RuntimeAction(kind=A.CALL_CAPABILITY, capability_key=BLOCK, input_refs=(ref,))
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


def media_review_workflow(workflow_id: str = MEDIA_WORKFLOW) -> RuntimeWorkflow:
    from drama_plugin.execution.capability import EXECUTE, INTAKE, REVIEW
    preparation = generation_workflow().steps
    if workflow_id == MEDIA_WORKFLOW:
        # ASSESS and COMPILE already consume exact Package inputs; resolver release
        # and inspect were deterministic envelopes, not separate decisions.
        preparation = (preparation[0], *preparation[3:])
    elif workflow_id != HISTORICAL_MEDIA_WORKFLOW:
        raise ValueError("Unknown immutable media workflow")
    return RuntimeWorkflow(workflow_id=workflow_id, steps=(*preparation,
        RuntimeAction(kind=A.CALL_CAPABILITY,capability_key=RELEASE),
        RuntimeAction(kind=A.CALL_CAPABILITY,capability_key=RELEASE),
        *(RuntimeAction(kind=A.CALL_CAPABILITY,capability_key=k) for k in (EXECUTE,INTAKE,REVIEW))))
