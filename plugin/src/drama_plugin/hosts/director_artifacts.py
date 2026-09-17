"""Project-artifact orchestration; IO/locking is supplied by the Host platform adapter."""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path, PureWindowsPath
from typing import Any, Iterator, Literal, Mapping

from drama_plugin.hosts.artifact_io import ArtifactIO, local_root, native_io, reject_link
from drama_plugin.contracts.base import canonical_json, dump_contract, sha256_canonical
from drama_plugin.contracts.director import CapabilityFeedback, CapabilityRequest, DirectorWorkspace
from drama_plugin.contracts.sequence import DirectorReviewFacet, SourcePin
from drama_plugin.director import (DirectorError, bind, dependencies, enter, feedback_pin,
    freshness, pin, request_pin, reviewed_receipt, validate_feedback)


class DirectorArtifactStore:
    """Host-owned IO. Only transition(REVIEW) may advance adoption. No generic workspace save."""

    def __init__(self, root: Path | str, *, io: ArtifactIO | None = None):
        self.io = io if io is not None else native_io()
        raw = str(root)
        if (not Path(raw).is_absolute() and not PureWindowsPath(raw).drive
                and not raw.lower().startswith('file:') and '://' not in raw):
            root = Path(raw).absolute()  # preserve the legacy native relative-root constructor
        self.root = Path(local_root(root)).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, group: str, identity: Any) -> Path:
        directory = self.root / group
        directory.mkdir(exist_ok=True)
        reject_link(directory)
        return directory / (sha256_canonical(identity) + '.json')

    @contextmanager
    def _writer(self) -> Iterator[None]:
        with self.io.guard(self.root / '.writer.lock'):
            yield

    def _write(self, path: Path, value: Any) -> None:
        self.io.write(path, canonical_json(value))

    def _read(self, path: Path) -> dict[str, Any]:
        reject_link(path)
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as error:
            raise DirectorError('INVALID_SOURCE', 'Missing or unreadable artifact') from error
        if not isinstance(data, dict):
            raise DirectorError('INVALID_SOURCE', 'Expected object artifact')
        return data

    def put(self, key: str, value: dict[str, Any]) -> SourcePin:
        """Retain an original sidecar/result. This never changes adoption or a workspace."""
        ref = pin(key, value)
        path = self._path('objects', ref.fingerprint)
        with self._writer():
            if path.exists():
                if sha256_canonical(self._read(path)) != ref.fingerprint:
                    raise DirectorError('INVALID_SOURCE', 'Corrupt immutable object')
            else:
                self._write(path, value)
        return ref

    def read_ref(self, ref: SourcePin) -> dict[str, Any]:
        value = self._read(self._path('objects', ref.fingerprint))
        if sha256_canonical(value) != ref.fingerprint:
            raise DirectorError('INVALID_SOURCE', 'Referenced artifact hash mismatch')
        return value

    def load(self, workspace_id: str, branch_id: str) -> DirectorWorkspace:
        result = DirectorWorkspace.model_validate(self._read(self._path('heads', [workspace_id, branch_id])))
        if (result.workspace_id, result.branch_id) != (workspace_id, branch_id):
            raise DirectorError('INVALID_SOURCE', 'Workspace branch mismatch')
        return result

    def _commit(self, workspace: DirectorWorkspace) -> None:
        value = dump_contract(workspace)
        self._write(self._path('history', sha256_canonical(value)), value)
        self._write(self._path('heads', [workspace.workspace_id, workspace.branch_id]), value)

    def create(self, workspace: DirectorWorkspace) -> DirectorWorkspace:
        workspace = DirectorWorkspace.model_validate(dump_contract(workspace))
        if (workspace.revision or workspace.request_ref or workspace.feedback_ref or workspace.review_ref
                or workspace.adopted_head or workspace.checkpoint != 'READY' or workspace.stale_keys):
            raise DirectorError('INVALID_SOURCE', 'New branch cannot inherit execution, approval or adopted state')
        if workspace.parent_ref:
            parent = DirectorWorkspace.model_validate(self.read_ref(workspace.parent_ref))
            if (parent.workspace_id != workspace.workspace_id or parent.scope_id != workspace.scope_id
                    or parent.branch_id == workspace.branch_id):
                raise DirectorError('INVALID_SOURCE', 'Branch parent must belong to the same workspace/scope and another branch')
        with self._writer():
            if self._path('heads', [workspace.workspace_id, workspace.branch_id]).exists():
                raise DirectorError('REVISION_CONFLICT', 'Workspace already exists; resume it')
            self._commit(workspace)
        return workspace

    def retain_feedback(self, request: CapabilityRequest, feedback: CapabilityFeedback) -> SourcePin:
        """Durable completion index before checkpoint; crash recovery discovers this result."""
        validate_feedback(request, feedback)
        ref = self.put(feedback_pin(feedback).key, dump_contract(feedback))
        path = self._path('completed', dump_contract(request_pin(request)))
        with self._writer():
            if path.exists() and self._read(path) != dump_contract(ref):
                raise DirectorError('REVISION_CONFLICT', 'Completion already retained; use a new request revision')
            self._write(path, dump_contract(ref))
        return ref

    def resume(self, workspace_id: str, branch_id: str, current: Mapping[str, str]) -> dict[str, Any]:
        workspace = self.load(workspace_id, branch_id)
        request = CapabilityRequest.model_validate(self.read_ref(workspace.request_ref)) if workspace.request_ref else None
        feedback = None
        ref = workspace.feedback_ref
        if request and ref is None:
            path = self._path('completed', dump_contract(request_pin(request)))
            if path.exists():
                ref = SourcePin.model_validate(self._read(path))
        if ref:
            feedback = CapabilityFeedback.model_validate(self.read_ref(ref))
        result = enter(workspace, current, request, feedback,
            self.read_ref(workspace.readiness_ref) if workspace.readiness_ref else None)
        return {**result, 'workspace': dump_contract(workspace),
                'recoveredFeedbackRef': dump_contract(ref) if ref else None}

    def transition(self, expected: DirectorWorkspace,
                   event: Literal['REQUEST', 'DISPATCH', 'FEEDBACK', 'REVIEW'],
                   payload_ref: SourcePin | None, current: Mapping[str, str], *,
                   approved_refs: tuple[SourcePin, ...] = (),
                   performance_coverage_bundle: dict[str, Any] | None = None) -> DirectorWorkspace:
        """CAS transition; caller supplies refs, never a replacement head or approval boolean."""
        with self._writer():
            old = self.load(expected.workspace_id, expected.branch_id)
            if sha256_canonical(old) != sha256_canonical(expected):
                raise DirectorError('REVISION_CONFLICT', 'Expected workspace head changed')
            request = CapabilityRequest.model_validate(self.read_ref(old.request_ref)) if old.request_ref else None
            stale = freshness(dependencies(old, request), current)
            if stale or old.stale_keys:
                marked = DirectorWorkspace.model_validate({**dump_contract(old), 'revision': old.revision + 1,
                    'staleKeys': list(stale or old.stale_keys)})
                self._commit(marked)
                raise DirectorError('STALE_SOURCE', 'Retained stale workspace; rebase through a new branch')
            data = dump_contract(old)
            if event == 'REQUEST':
                if old.request_ref and old.checkpoint not in ('REVISION_PENDING', 'READY'):
                    raise DirectorError('REVISION_CONFLICT', 'Resolve current request before replacing it')
                if old.request_ref and not old.review_ref:
                    raise DirectorError('REVISION_CONFLICT', 'Unreviewed request cannot be discarded')
                if payload_ref is None:
                    raise DirectorError('INVALID_SOURCE', 'Missing request')
                new = CapabilityRequest.model_validate(self.read_ref(payload_ref))
                bind(old, new)
                if payload_ref != request_pin(new) or freshness(dependencies(old, new), current):
                    raise DirectorError('STALE_SOURCE', 'New request source/intent/requirements changed')
                if old.request_ref and (new.supersedes != old.request_ref or payload_ref == old.request_ref):
                    raise DirectorError('REVISION_CONFLICT', 'Replacement must explicitly supersede reviewed request')
                data.update(requestRef=dump_contract(payload_ref), feedbackRef=None, reviewRef=None, checkpoint='READY')
            elif event == 'DISPATCH':
                state = self.resume(old.workspace_id, old.branch_id, current)
                if (not state['delegate'] and state['action'] != 'WAITING_APPROVAL') or payload_ref is not None:
                    raise DirectorError('REVISION_CONFLICT', 'Reconcile existing execution; never resubmit blindly')
                if request is None or any(p not in approved_refs for p in request.approval_refs):
                    paused = DirectorWorkspace.model_validate({**data, 'revision': old.revision + 1,
                                                               'checkpoint': 'WAITING_APPROVAL'})
                    self._commit(paused)
                    raise DirectorError('USER_APPROVAL_REQUIRED', 'Original scope/branch approval required')
                data['checkpoint'] = 'DISPATCHED'  # Commit before any Host side effect.
            elif event == 'FEEDBACK':
                if request is None or payload_ref is None or old.review_ref:
                    raise DirectorError('INVALID_SOURCE', 'Feedback requires unresolved request')
                feedback = CapabilityFeedback.model_validate(self.read_ref(payload_ref))
                validate_feedback(request, feedback)
                if payload_ref != feedback_pin(feedback):
                    raise DirectorError('INVALID_SOURCE', 'Feedback identity mismatch')
                if old.feedback_ref and old.feedback_ref != payload_ref:
                    raise DirectorError('REVISION_CONFLICT', 'Retained observation cannot be silently replaced')
                data.update(feedbackRef=dump_contract(payload_ref), checkpoint='REVIEW_PENDING')
            elif event == 'REVIEW':
                if not request or not old.feedback_ref or not payload_ref or old.review_ref:
                    raise DirectorError('INSUFFICIENT_EVIDENCE', 'Review requires an unreviewed observed result')
                feedback = CapabilityFeedback.model_validate(self.read_ref(old.feedback_ref))
                review = self.read_ref(payload_ref)
                receipt = reviewed_receipt(old, request, feedback, review, payload_ref, current, approved_refs, performance_coverage_bundle=performance_coverage_bundle)
                facet = DirectorReviewFacet.model_validate(review['director'])
                if receipt:
                    delta = self.read_ref(facet.adopted_delta_ref) if facet.adopted_delta_ref else {}
                    allowed = {'audience_knowledge', 'relationship_presentation', 'motif_usage', 'sound_strategy', 'character_presentation'}
                    if (set(delta) != {'domain', 'summary', 'presentationOnly'} or delta['domain'] not in allowed
                            or delta['presentationOnly'] is not True or not isinstance(delta['summary'], str) or not delta['summary'].strip()):
                        raise DirectorError('INVALID_SOURCE', 'Only a sparse reviewed presentation delta may be adopted')
                    ref = pin('receipt:' + payload_ref.fingerprint, receipt)
                    self._write(self._path('objects', ref.fingerprint), receipt)
                    data['adoptedHead'] = dump_contract(ref)
                data.update(reviewRef=dump_contract(payload_ref), checkpoint='READY' if facet.disposition == 'APPROVE' else 'REVISION_PENDING')
            else:
                raise DirectorError('INVALID_SOURCE', 'Unknown transition')
            data['revision'] = old.revision + 1
            updated = DirectorWorkspace.model_validate(data)
            self._commit(updated)
            return updated
