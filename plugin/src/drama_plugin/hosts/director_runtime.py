"""Bounded Host IO sequencing. Creative decisions remain supplied by Director Core."""
from __future__ import annotations
from typing import Any, Callable, Mapping
from drama_plugin.contracts.director import CapabilityFeedback, CapabilityRequest, DirectorWorkspace
from drama_plugin.contracts.sequence import SourcePin
from drama_plugin.director import DirectorError, validate_feedback
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
from drama_plugin.hosts.director_capabilities import LocalCapabilityBridge

# The callback reads the original Tool/job/result owner, not DirectorWorkspace.
ExecutionLookup = Callable[[CapabilityRequest], CapabilityFeedback | None]
ExecutionRetain = Callable[[CapabilityRequest, CapabilityFeedback], None]


def dispatch_local(store: DirectorArtifactStore, bridge: LocalCapabilityBridge, expected: DirectorWorkspace,
                   input_ref: SourcePin, current: Mapping[str, str], *, retain_execution: ExecutionRetain,
                   approved_refs: tuple[SourcePin, ...] = ()) -> DirectorWorkspace:
    """One invocation, never a loop. Durable DISPATCH precedes any capability call.

    retain_execution must commit to the capability's result owner before returning.
    If it fails/interrupts, resume reconciles there; it never assumes nonexecution.
    """
    w = store.transition(expected, 'DISPATCH', None, current, approved_refs=approved_refs)
    if w.request_ref is None:
        raise DirectorError('INVALID_SOURCE', 'Missing request after dispatch')
    q = CapabilityRequest.model_validate(store.read_ref(w.request_ref))
    f = bridge.run(q, input_ref, current)
    retain_execution(q, f)
    ref = store.retain_feedback(q, f)
    return store.transition(w, 'FEEDBACK', ref, current)


def resume_with_execution(store: DirectorArtifactStore, workspace_id: str, branch_id: str,
                          current: Mapping[str, str], lookup: ExecutionLookup) -> dict[str, Any]:
    state = store.resume(workspace_id, branch_id, current)
    if state['action'] != 'RECONCILE_RESULT':
        return state
    w = store.load(workspace_id, branch_id)
    if not w.request_ref:
        raise DirectorError('INVALID_SOURCE', 'Dispatch checkpoint without request')
    q = CapabilityRequest.model_validate(store.read_ref(w.request_ref))
    f = lookup(q)  # must use request-bound task/result/Media evidence at the original owner
    if f is None or f.execution == 'UNKNOWN':
        return {**state, 'action': 'RECONCILIATION_REQUIRED', 'delegate': False}
    validate_feedback(q, f)
    # Original result bytes and evidence must also be current; never bless stale output.
    from drama_plugin.director import enter
    check = enter(w, current, q, f)
    if check['action'] == 'STALE_SOURCE':
        return {**state, **check}
    ref = store.retain_feedback(q, f)
    store.transition(w, 'FEEDBACK', ref, current)
    return store.resume(workspace_id, branch_id, current)
