"""Film user boundaries use only the existing GateGovernor and decision categories."""
from drama_plugin.creative_engine.policy import CreativePolicy
from drama_plugin.film.capability import KEYS, WORKFLOW, REVISION_KEYS, REVISION_WORKFLOW, MEDIA_KEYS, MEDIA_WORKFLOW
from drama_plugin.film.store import FilmStore
from drama_plugin.governance.contracts import GateFinding, GateCode
from drama_plugin.governance.governor import GateGovernor
from drama_plugin.governance.store import FindingStore
from drama_plugin.runtime.contracts import ActionKind, RunMode, RuntimeAction, RuntimeRun, RuntimeState, RuntimeWorkflow

def film_workflow() -> RuntimeWorkflow:
    return RuntimeWorkflow(workflow_id=WORKFLOW,steps=tuple(RuntimeAction(kind=ActionKind.CALL_CAPABILITY,
        capability_key='film.'+key+':v1') for key in KEYS))

def film_media_workflow() -> RuntimeWorkflow:
    return RuntimeWorkflow(workflow_id=MEDIA_WORKFLOW,steps=tuple(RuntimeAction(kind=ActionKind.CALL_CAPABILITY,
        capability_key='film.'+key+':v1') for key in MEDIA_KEYS))

def film_revision_workflow() -> RuntimeWorkflow:
    return RuntimeWorkflow(workflow_id=REVISION_WORKFLOW,steps=tuple(RuntimeAction(kind=ActionKind.CALL_CAPABILITY,
        capability_key='film.'+key+':v1') for key in REVISION_KEYS))

class FilmPolicy(CreativePolicy):
    def __init__(self,mode:RunMode,findings:FindingStore,store:FilmStore,governor:GateGovernor):
        super().__init__(mode,findings)
        self.film_store,self.film_governor=store,governor
    def next_action(self,run:RuntimeRun,workflow:RuntimeWorkflow)->RuntimeAction:
        if workflow.workflow_id not in (WORKFLOW,REVISION_WORKFLOW,MEDIA_WORKFLOW):
            return super().next_action(run,workflow)
        adoption = workflow.workflow_id in (WORKFLOW,MEDIA_WORKFLOW) and run.cursor == 3
        final = workflow.workflow_id != MEDIA_WORKFLOW and run.cursor == (8 if workflow.workflow_id == WORKFLOW else 3)
        if (adoption or final) and run.state in (RuntimeState.READY,RuntimeState.WAITING_USER):
            cp=self.film_store.checkpoint(run.run_id)
            if final and cp.acceptance_ref and cp.revision_child_run_id:
                return RuntimeAction(kind=ActionKind.CALL_CAPABILITY,capability_key='film.decision:v1')
            target=cp.plan_ref if adoption else cp.final_ref
            if target is None:
                raise ValueError('Film user decision lacks fixed candidate')
            finding=GateFinding.classified(GateCode.ADOPTION_REQUIRED if adoption else GateCode.FINAL_ACCEPTANCE_REQUIRED,
                owner='film-adoption' if adoption else 'final-acceptance',scope=run.scope,evidence_ref=target)
            decision=self.film_governor.govern((finding,),scope=run.scope,mode=run.mode,package_ref=None)
            self.findings.put_decision(decision,run_id=run.run_id)
            assert decision.user_decision
            return RuntimeAction(kind=ActionKind.REQUEST_USER_DECISION,decision=decision.user_decision)
        return self.governed.foundation.next_action(run,workflow)
