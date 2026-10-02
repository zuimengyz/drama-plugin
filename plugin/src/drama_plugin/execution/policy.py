"""One existing Runtime loop for experiment/production; five domain actions."""
from drama_plugin.execution.capability import AUDIO, EXECUTE, FINISH, INTAKE, REVIEW
from drama_plugin.runtime.contracts import ActionKind, RuntimeAction, RuntimeWorkflow

WORKFLOW = "execute-reviewed-candidate:v1"


def execution_workflow() -> RuntimeWorkflow:
    return RuntimeWorkflow(workflow_id=WORKFLOW, steps=tuple(RuntimeAction(
        kind=ActionKind.CALL_CAPABILITY, capability_key=key)
        for key in (EXECUTE, INTAKE, REVIEW, AUDIO, FINISH)))
