from types import SimpleNamespace
import pytest
from drama_plugin.generation.contracts import GenerationTask, CrossShotContinuity
from drama_plugin.generation.cross_shot import validate_cross_shot
from drama_plugin.runtime.contracts import RuntimeScope

scope = RuntimeScope(work_id='w', scene_id='s', shot_id='k2')

def decision(strategy, **extra):
    return CrossShotContinuity(strategy=strategy, reason='Lens and viewpoint change',
        camera_relation='70mm detail to 40mm reveal', inherited_state='Hand already clear of money',
        target_state='Reveal the coffin without repeating payment', **extra)

def test_new_goal_requires_host_decision_but_historical_recovery_does_not():
    task = GenerationTask()
    validate_cross_shot(None, scope, task)
    with pytest.raises(ValueError, match='CROSS_SHOT_HOST_JUDGMENT_REQUIRED'):
        validate_cross_shot(None, scope, task, required=True)

def test_pending_replacement_cannot_compile_or_submit():
    task = GenerationTask(cross_shot_continuity=decision('PENDING_PREDECESSOR', predecessor_shot_id='k1'))
    with pytest.raises(ValueError, match='CROSS_SHOT_PREDECESSOR_NOT_READY'):
        validate_cross_shot(None, scope, task)

def test_cut_can_explicitly_skip_picture_reference():
    task = GenerationTask(cross_shot_continuity=decision('INDEPENDENT', predecessor_shot_id='k1'))
    validate_cross_shot(None, scope, task, required=True)

def test_tail_return_flag_does_not_count_as_decision():
    with pytest.raises(ValueError, match='CROSS_SHOT_HOST_JUDGMENT_REQUIRED'):
        validate_cross_shot(None, scope, GenerationTask(return_last_frame=True), required=True)

def test_opening_cannot_masquerade_as_predecessor_reference():
    with pytest.raises(ValueError, match='OPENING_HAS_NO_PREDECESSOR'):
        decision('OPENING', predecessor_shot_id='k1')

def test_reference_requires_exact_source_and_binding():
    with pytest.raises(ValueError, match='EXACT_PREDECESSOR_MEDIA_REQUIRED'):
        decision('FRAME_REFERENCE', predecessor_shot_id='k1')


@pytest.mark.parametrize('boundary_kind', [None, 'CONTINUE', 'WRONG_PREDECESSOR'])
def test_same_shot_cut_needs_exact_authored_boundary(boundary_kind):
    from drama_plugin.runtime.contracts import ArtifactReference
    ref=ArtifactReference(owner='media-binding',artifact_ref='prior')
    boundary=None if boundary_kind is None else SimpleNamespace(
        kind='CUT' if boundary_kind=='WRONG_PREDECESSOR' else boundary_kind,
        predecessor_media_ref=ref.model_copy(update={'artifact_ref':'other'}) if boundary_kind=='WRONG_PREDECESSOR' else ref)
    task=SimpleNamespace(cross_shot_continuity=decision('INDEPENDENT',
        predecessor_shot_id=scope.shot_id,predecessor_media_ref=ref),boundary=boundary,continuation=None)
    with pytest.raises(ValueError,match='CROSS_SHOT_PREDECESSOR_IS_TARGET'):
        validate_cross_shot(None,scope,task,required=True)
