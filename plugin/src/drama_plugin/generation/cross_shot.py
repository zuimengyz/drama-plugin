"""Cross-shot admission within the existing generation owner; no scheduling or IO."""
from drama_plugin.runtime.contracts import ArtifactReference
from drama_plugin.production.references import ReferenceExecutionBinding
from drama_plugin.persistence.stores import DurableReferenceExecutionStore
from drama_plugin.execution.contracts import MediaBinding, CreativeMediaReview
from drama_plugin.execution.store import ExecutionStore
from drama_plugin.generation.operation import continuation_frame


def validate_cross_shot(ledger, scope, task, *, required=False):
    decision = task.cross_shot_continuity
    if decision is None:
        # Existing same-take preparation already pins an explicit Host boundary and endpoint.
        if task.continuation and task.boundary and task.boundary.kind == 'CONTINUE':
            from drama_plugin.generation.operation import validate_continuation
            validate_continuation(ledger, task)
            return
        if required:
            raise ValueError('CROSS_SHOT_HOST_JUDGMENT_REQUIRED')
        return
    if decision.strategy == 'PENDING_PREDECESSOR':
        raise ValueError('CROSS_SHOT_PREDECESSOR_NOT_READY')
    if decision.strategy == 'OPENING':
        if task.continuation or task.boundary:
            raise ValueError('OPENING_PREDECESSOR_CONFLICT')
        return
    if decision.predecessor_shot_id == scope.shot_id and decision.strategy != 'CONTINUE':
        raise ValueError('CROSS_SHOT_PREDECESSOR_IS_TARGET')
    if decision.predecessor_media_ref:
        store = ExecutionStore(ledger)
        source = store.get(decision.predecessor_media_ref, MediaBinding)
        if source.scope.work_id != scope.work_id or source.scope.shot_id != decision.predecessor_shot_id:
            raise ValueError('CROSS_SHOT_PREDECESSOR_SCOPE_MISMATCH')
        cp = store.checkpoint(source.operation_ref)
        review = store.get(cp.progress.video_creative_ref, CreativeMediaReview) if cp.progress.video_creative_ref else None
        if not review or review.outcome != 'PASS' or review.media != source.media:
            raise ValueError('CROSS_SHOT_PREDECESSOR_REVIEW_REQUIRED')
    if decision.strategy == 'INDEPENDENT':
        if task.continuation:
            raise ValueError('INDEPENDENT_CONTINUATION_CONFLICT')
        return
    if decision.strategy == 'CONTINUE':
        if not task.continuation or task.continuation.predecessor_media_ref != decision.predecessor_media_ref:
            raise ValueError('CROSS_SHOT_CONTINUATION_MISMATCH')
        return
    if task.continuation or task.input_mode != 'reference' or decision.reference_ref not in (task.execution_reference_refs or ()):
        raise ValueError('CROSS_SHOT_REFERENCE_NOT_IN_REQUEST')
    binding = ReferenceExecutionBinding.model_validate(DurableReferenceExecutionStore(ledger).resolve(decision.reference_ref))
    if binding.role != 'REFERENCE' or not binding.picture_frame_ref or binding.origin_scope != source.scope:
        raise ValueError('CROSS_SHOT_PICTURE_PROVENANCE_REQUIRED')
    frame, predecessor, _, _ = continuation_frame(ledger, binding.picture_frame_ref, picture_only=True)
    if (frame.predecessor_media_ref != decision.predecessor_media_ref or predecessor != source
            or binding.scope != scope or binding.media.content_hash != frame.media.content_hash
            or binding.media.media_id != frame.media.media_id):
        raise ValueError('CROSS_SHOT_REFERENCE_MEDIA_MISMATCH')
