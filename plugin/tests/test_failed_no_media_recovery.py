"""Offline terminal-no-media recovery through existing resume/reserve gates."""
from copy import deepcopy
import pytest
from drama_plugin.visual import production as p
from drama_plugin.visual.frame_request import compile_frame
from test_visual_first_pass import material
from test_video_selection import quote


def stage(tmp_path, status='FAILED'):
    frame = compile_frame(*material(tmp_path))
    state = p.new_stage(stage_id='offline', authorization_ref='Existing 2000 credits approval',
        budget_credits=2000, frames=[frame], protected_targets=[])
    attempt = p.reserve(state, 'S1', **quote(frame, 10))
    p.record_result(state, attempt_id=attempt['attempt_id'], status=status,
        job_id=None if status == 'NOT_CREATED' else 'provider-job', evidence='OFFLINE terminal provider receipt',
        execution_receipt=None if status == 'NOT_CREATED' else {'task_id': 'provider-job', 'reason': 'Request Moderated'})
    return state, frame, attempt


def proof(attempt):
    return {'attempt_id': attempt['attempt_id'], 'job_id': attempt['job_id'], 'terminal_failure': True,
        'usable_media_count': 0, 'evidence': 'OFFLINE confirmed terminal failure and empty output listing'}


def test_failed_created_no_media_reserves_without_visual_pass(tmp_path):
    state, frame, old = stage(tmp_path)
    retained = deepcopy(old)
    p.resume(state, reason='Scoped prompt repaired; controlled recovery', no_media_failure=proof(old))
    assert old['review_status'] == old['content_status'] == 'NOT_APPLICABLE_NO_MEDIA'
    assert not p.usable(old) and 'review' not in old
    new = p.reserve(state, 'S1', **quote(frame, 10))
    assert new['status'] == 'RESERVED' and new['retry_of'] == old['attempt_id']
    assert new['technical_retry_count'] == 1 and new['request'] == frame['request']
    for key in ('job_id', 'provider_evidence', 'execution_receipt', 'reserved_credits', 'credits'):
        assert old[key] == retained[key]
    assert state['stage']['budget_credits'] == 2000


@pytest.mark.parametrize('field,value', [('usable_media_count', 1), ('terminal_failure', False),
    ('job_id', 'wrong-task'), ('usable_media_count', None)])
def test_invalid_no_media_evidence_rejected(tmp_path, field, value):
    state, _, old = stage(tmp_path)
    observation = proof(old); observation[field] = value
    with pytest.raises(ValueError, match='CONFIRMED_TERMINAL_FAILURE_WITHOUT_MEDIA_REQUIRED'):
        p.resume(state, reason='recovery', no_media_failure=observation)
    assert 'review_status' not in old


def test_existing_media_keeps_visual_review_gate(tmp_path):
    state, frame, old = stage(tmp_path)
    old['output_hash'] = 'a' * 64
    with pytest.raises(ValueError, match='CONFIRMED_TERMINAL_FAILURE_WITHOUT_MEDIA_REQUIRED'):
        p.resume(state, reason='cannot waive media review', no_media_failure=proof(old))
    p.resume(state, reason='existing review path')
    with pytest.raises(ValueError, match='TECHNICAL_FAILURE_REQUIRES_OUTCOME_RECOVERY'):
        p.reserve(state, 'S1', **quote(frame, 10))


def test_ambiguous_no_media_still_blocks(tmp_path):
    state, _, old = stage(tmp_path, 'UNKNOWN')
    with pytest.raises(ValueError, match='RECOVER_ORIGINAL_SUBMISSION_FIRST'):
        p.resume(state, reason='no new submit', no_media_failure=proof(old))


def test_never_created_retry_unchanged(tmp_path):
    state, frame, old = stage(tmp_path, 'NOT_CREATED')
    attempt = p.retry_not_created(state, attempt_id=old['attempt_id'], evidence='OFFLINE no job created', **quote(frame, 10))
    assert attempt['status'] == 'RESERVED' and attempt['job_id'] is None


def test_no_media_recovery_budget_and_retry_cap(tmp_path):
    state, frame, old = stage(tmp_path)
    p.resume(state, reason='recovery', no_media_failure=proof(old))
    state['stage']['budget_credits'] = 15
    with pytest.raises(ValueError, match='BUDGET'):
        p.reserve(state, 'S1', **quote(frame, 10))
    state['stage']['budget_credits'] = 2000
    for i in range(2):
        new = p.reserve(state, 'S1', **quote(frame, 10))
        p.record_result(state, attempt_id=new['attempt_id'], status='FAILED', job_id=f'job-{i}', evidence='OFFLINE terminal failure')
        p.resume(state, reason='bounded recovery', no_media_failure=proof(new))
    with pytest.raises(ValueError, match='TECHNICAL_RETRIES_EXHAUSTED'):
        p.reserve(state, 'S1', **quote(frame, 10))
