"""Pure Director handoff/adoption guards. No IO, creative auto-judgment or capability calls."""
from __future__ import annotations

from typing import Any, Literal, Mapping
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.director import CapabilityFeedback, CapabilityRequest, DirectorWorkspace
from drama_plugin.contracts.sequence import DirectorReviewFacet, FilmReview, SourcePin
from drama_plugin.sequence import film_review_verdict

Failure = Literal['INVALID_SOURCE', 'STALE_SOURCE', 'INSUFFICIENT_EVIDENCE',
    'CAPABILITY_LIMITATION', 'USER_APPROVAL_REQUIRED', 'UPSTREAM_REVIEW_REQUIRED',
    'EXECUTION_FAILURE', 'REVISION_CONFLICT']


class DirectorError(ValueError):
    def __init__(self, code: Failure, detail: str):
        self.code = code
        super().__init__(f'{code}: {detail}')


REPAIR_RESPONSIBILITY = {
    'REVISE_EXECUTION': 'execution', 'REVISE_PERFORMANCE': 'performance',
    'REVISE_BLOCKING': 'blocking', 'REVISE_COVERAGE': 'coverage', 'REVISE_EDIT': 'edit',
    'REVISE_SOUND': 'sound', 'REPLAN_SCENE': 'scene planning',
    'REQUEST_SCRIPT_REVIEW': 'script review', 'ESCALATE_PRODUCTION_METHOD': 'production method',
    'INSUFFICIENT_EVIDENCE': 'observation', 'APPROVE': 'adoption gate',
}


def pin(key: str, value: Any) -> SourcePin:
    return SourcePin(key=key, kind='DIRECTION', fingerprint=sha256_canonical(value))


def request_pin(request: CapabilityRequest) -> SourcePin:
    return pin('request:' + request.request_id, request)


def feedback_pin(feedback: CapabilityFeedback) -> SourcePin:
    return pin('feedback:' + feedback.request_ref.key, feedback)


def freshness(pins: tuple[SourcePin, ...], current: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(p.key for p in pins if current.get(p.key) != p.fingerprint))


def dependencies(workspace: DirectorWorkspace, request: CapabilityRequest | None = None) -> tuple[SourcePin, ...]:
    refs = workspace.source_pins + workspace.intent_refs
    if workspace.route_ref:
        refs += (workspace.route_ref,)
    if request:
        refs += request.source_pins + request.intent_refs + request.approval_refs + request.requirement_refs
    return refs


def bind(workspace: DirectorWorkspace, request: CapabilityRequest) -> None:
    for name in ('workspace_id', 'scope_id', 'branch_id', 'route_ref', 'source_pins'):
        if getattr(workspace, name) != getattr(request, name):
            raise DirectorError('INVALID_SOURCE', 'Request binding mismatch: ' + name)
    if not set((p.key, p.fingerprint) for p in request.intent_refs) <= set((p.key, p.fingerprint) for p in workspace.intent_refs):
        raise DirectorError('INVALID_SOURCE', 'Request intent is outside workspace')


def validate_feedback(request: CapabilityRequest, feedback: CapabilityFeedback) -> None:
    if feedback.request_ref != request_pin(request) or feedback.source_pins != request.source_pins:
        raise DirectorError('INVALID_SOURCE', 'Feedback is not bound to this exact request')


def enter(workspace: DirectorWorkspace, current: Mapping[str, str],
          request: CapabilityRequest | None = None,
          feedback: CapabilityFeedback | None = None) -> dict[str, Any]:
    """One start/resume entry; a dispatched unknown is reconciled, never resubmitted."""
    workspace = DirectorWorkspace.model_validate(dump_contract(workspace))
    if workspace.request_ref and request is None:
        raise DirectorError('INVALID_SOURCE', 'Missing referenced request')
    if request:
        request = CapabilityRequest.model_validate(dump_contract(request))
        bind(workspace, request)
        if workspace.request_ref != request_pin(request):
            raise DirectorError('INVALID_SOURCE', 'Request revision mismatch')
    stale = freshness(dependencies(workspace, request), current)
    if stale or workspace.stale_keys:
        return {'action': 'STALE_SOURCE', 'staleKeys': list(stale or workspace.stale_keys), 'delegate': False}
    if feedback:
        if not request:
            raise DirectorError('INVALID_SOURCE', 'Feedback without request')
        validate_feedback(request, feedback)
        changed = freshness(feedback.result_refs + feedback.evidence_refs, current)
        if changed:
            return {'action': 'STALE_SOURCE', 'staleKeys': list(changed), 'delegate': False}
    action: str
    if workspace.checkpoint == 'REVISION_PENDING':
        action = workspace.checkpoint
    elif workspace.review_ref:
        action = 'NEXT_DECISION'
    elif feedback or workspace.feedback_ref:
        action = 'REVIEW_PENDING'
    elif workspace.checkpoint == 'WAITING_APPROVAL':
        action = 'WAITING_APPROVAL'
    elif workspace.checkpoint == 'DISPATCHED':
        action = 'RECONCILE_RESULT'
    elif request:
        action = 'READY_TO_DELEGATE'
    else:
        action = 'INTERPRET_AND_INTEND'
    return {'action': action, 'delegate': action == 'READY_TO_DELEGATE'}


def reviewed_receipt(workspace: DirectorWorkspace, request: CapabilityRequest,
                     feedback: CapabilityFeedback, review: dict[str, Any], review_ref: SourcePin,
                     current: Mapping[str, str], approved_refs: tuple[SourcePin, ...] = ()) -> dict[str, Any] | None:
    """Validate an original review; return a sparse Bible receipt only after all gates.

    approved_refs are current, branch-scoped attestations resolved by the original gate
    owner, NOT a Director approval flag. This function cannot authenticate their issuer.
    """
    bind(workspace, request)
    validate_feedback(request, feedback)
    if workspace.request_ref != request_pin(request) or workspace.feedback_ref != feedback_pin(feedback):
        raise DirectorError('INVALID_SOURCE', 'Review is not for the current observed result')
    if review_ref.fingerprint != sha256_canonical(review):
        raise DirectorError('INVALID_SOURCE', 'Review bytes changed')
    if request.result_kind == 'MEDIA':
        film = FilmReview.model_validate(review)
        facet = film.director
    else:
        if set(review) != {'subjectKind', 'director', 'findings'} or review['subjectKind'] != 'DESIGN_ONLY':
            raise DirectorError('INVALID_SOURCE', 'Design review must remain a Bible design review')
        facet = DirectorReviewFacet.model_validate(review['director'])
        if not set(facet.finding_keys) <= {f['id'] for f in review['findings']}:
            raise DirectorError('INVALID_SOURCE', 'Missing Bible finding')
    if facet is None:
        raise DirectorError('INSUFFICIENT_EVIDENCE', 'Director facet is required on the opt-in path')
    for name in ('workspace_id', 'scope_id', 'branch_id', 'route_ref', 'source_pins', 'intent_refs'):
        if getattr(facet, name) != getattr(request, name):
            raise DirectorError('INVALID_SOURCE', 'Review binding mismatch: ' + name)
    if facet.request_ref != request_pin(request) or facet.feedback_ref != feedback_pin(feedback):
        raise DirectorError('INVALID_SOURCE', 'Review belongs to a different request/result')
    refs = dependencies(workspace, request) + feedback.result_refs + feedback.evidence_refs
    if facet.adopted_delta_ref:
        refs += (facet.adopted_delta_ref,)
    stale = freshness(refs, current)
    if stale or workspace.stale_keys:
        raise DirectorError('STALE_SOURCE', ', '.join(stale or workspace.stale_keys))
    if facet.disposition != 'APPROVE':
        return None  # Disposition is retained; no retry and no adoption.
    if request.result_kind == 'DESIGN_ONLY' and any(
            f.get('severity') in ('MAJOR', 'CRITICAL', 'SEVERE') and not f.get('resolved', False)
            for f in review['findings']):
        raise DirectorError('UPSTREAM_REVIEW_REQUIRED', 'Unresolved severe Bible finding')
    if feedback.execution != 'COMPLETED':
        raise DirectorError('EXECUTION_FAILURE', 'No completed candidate')
    if feedback.feasibility not in ('SUPPORTED', 'SUPPORTED_WITH_CONSTRAINTS'):
        raise DirectorError('CAPABILITY_LIMITATION', feedback.feasibility)
    if (feedback.unmet or not feedback.evidence_refs or
            not set(request.required_evidence) <= set(feedback.fulfilled) or
            'INSUFFICIENT_EVIDENCE' in feedback.conditions):
        raise DirectorError('INSUFFICIENT_EVIDENCE', 'Required obligations are not evidenced')
    if feedback.conditions:
        raise DirectorError('USER_APPROVAL_REQUIRED', 'Resolve cost/approval conditions at the original owner first')
    if any(p not in approved_refs for p in request.approval_refs):
        raise DirectorError('USER_APPROVAL_REQUIRED', 'Original scoped approval is absent')
    if request.result_kind == 'MEDIA':
        media = [p for p in feedback.result_refs if p.kind == 'MEDIA' and p.fingerprint == film.media_hash]
        if not media:
            raise DirectorError('INVALID_SOURCE', 'Review does not bind returned Media')
        if film_review_verdict(film, film.media_hash)['status'] != 'CONTENT_REVIEW_COMPLETE_PENDING_USER_ADOPTION':
            raise DirectorError('INSUFFICIENT_EVIDENCE', 'Technical/normal AV/persistence gate incomplete')
    if not facet.adopted_delta_ref:
        return None  # Valid local approval need not create a cross-scene receipt.
    return {'kind': 'presentation-receipt', 'subjectKind': request.result_kind,
            'workspaceId': workspace.workspace_id, 'branchId': workspace.branch_id,
            'parent': dump_contract(workspace.adopted_head) if workspace.adopted_head else None,
            'reviewRef': dump_contract(review_ref), 'deltaRef': dump_contract(facet.adopted_delta_ref),
            'sourcePins': [dump_contract(p) for p in request.source_pins],
            'userApproval': 'UNCHANGED'}


def trace_intent(items: list[dict[str, Any]], item_id: str) -> tuple[str, ...]:
    """Validate existing cinematic-intent optional parent pins, without copying its meaning."""
    indexed = {i['id']: i for i in items}
    if len(indexed) != len(items):
        raise DirectorError('INVALID_SOURCE', 'Duplicate intent identity')
    chain: list[str] = []
    levels = {'FILM': None, 'EPISODE': 'FILM', 'SCENE': 'EPISODE', 'SHOT': 'SCENE', 'COVERAGE_GROUP': 'SCENE'}
    current = item_id
    while True:
        if current in chain or current not in indexed:
            raise DirectorError('INVALID_SOURCE', 'Cyclic or missing intent parent')
        item = indexed[current]
        chain.append(current)
        level = item.get('scopeLevel')
        if level not in levels:
            raise DirectorError('INVALID_SOURCE', 'Unknown intent scope')
        if level == 'FILM':
            if item.get('parentRef'):
                raise DirectorError('INVALID_SOURCE', 'Film scope cannot have an intent parent')
            return tuple(chain)
        parent = SourcePin.model_validate(item.get('parentRef'))
        target = indexed.get(parent.key)
        if not target or target.get('scopeLevel') != levels[level] or parent.fingerprint != sha256_canonical(target):
            raise DirectorError('STALE_SOURCE', 'Intent parent is missing, changed or at the wrong level')
        current = parent.key
