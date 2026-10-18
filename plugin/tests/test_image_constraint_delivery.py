"""Constraint meaning reaches the actual Ark JSON without network or media.

Cases are controlled contract facts, not evidence that a model obeyed them.
The edit case uses an existing metadata-only symbolic reference helper.
"""
from copy import deepcopy
import json

import pytest

from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.visual.frame_request import compile_frame, verify_compiled
from drama_plugin.visual.prompt_ir import compile_ir, verify_compilation
from test_seedream_image_modes import reference_spec, symbolic_input
from test_target_reference_production import reference_frame
from test_visual_prompt_ir import fact


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    import socket

    def denied(*args, **kwargs):
        raise AssertionError('OFFLINE_TEST_NETWORK_FORBIDDEN')

    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket.socket, 'connect_ex', denied)


LIMIT = '画面不出现字幕、图解标注或指示箭头。'
UNRELATED = '自然材质与背景服从观察任务。'
EQUIVALENT = '纯图像参考，画内没有字幕文字、图解标注及指示箭头。'


def frame_with_limits(*pairs, task='TEXT_TO_IMAGE'):
    item = {'subjectId': 'selected-person',
            'designRef': {'key': 'approved', 'kind': 'CANON', 'fingerprint': 'a' * 64},
            'assetType': 'CHARACTER', 'name': 'Selected person',
            'design': {'face': 'Approved narrow face'}}
    frame = reference_frame(item)
    ir = deepcopy(frame.prompt_ir)
    ir['task']['task_type'] = task
    ir['negative_constraints'] = [dict(constraint=fact(source), positive_target=fact(target))
                                  for source, target in pairs]
    return frame.model_copy(update={'prompt_ir': ir})


def ark_json(frame):
    compiled = compile_frame(frame)
    verify_compiled(compiled)
    # This is the real current Ark serializer body, not a replacement formatter.
    request = json.loads(json.dumps(compiled['request'], ensure_ascii=False))
    assert request['tool'] == 'image.create' and request['provider'] == 'ark'
    assert 'negative_prompt' not in request['body']
    assert request['body']['prompt'] == compiled['prompt_ir_compilation']['prompt']
    return compiled, request['body']['prompt']


@pytest.mark.parametrize('task', ['TEXT_TO_IMAGE', 'FIRST_FRAME', 'KEY_FRAME'])
@pytest.mark.parametrize('target', [UNRELATED, EQUIVALENT])
def test_current_limit_cannot_be_replaced_by_unrelated_positive_prose(task, target):
    frame = frame_with_limits((LIMIT, target), task=task)
    before = frame.model_dump(mode='json')
    compiled, prompt = ark_json(frame)
    assert LIMIT in prompt and target in prompt
    assert frame.model_dump(mode='json') == before
    kept = {r['path']: r for r in compiled['prompt_ir_compilation']['retained']}
    assert kept['constraint[0]']['text'] == LIMIT
    assert kept['constraint[0]']['priority'] == 'CRITICAL'
    assert kept['constraint[0]']['required'] is True
    assert not any(r['path'] == 'constraint[0]' for r in compiled['prompt_ir_compilation']['omitted'])


def test_exact_equivalent_and_repeated_limit_render_once_but_keep_source_rows():
    compiled, prompt = ark_json(frame_with_limits((LIMIT, LIMIT), (LIMIT, LIMIT)))
    assert prompt.count(LIMIT) == 1
    retained = compiled['prompt_ir_compilation']['retained']
    assert {r['path'] for r in retained if r['text'] == LIMIT} == {
        'constraint[0]', 'positive_target[0]', 'constraint[1]', 'positive_target[1]'}


@pytest.mark.parametrize('scope', ['FUTURE', 'INTERNAL', 'CAPABILITY', 'CLIP'])
def test_noncurrent_limits_do_not_become_static_execution(scope):
    frame = frame_with_limits((LIMIT, UNRELATED))
    ir = deepcopy(frame.prompt_ir)
    ir['negative_constraints'][0]['constraint']['scope'] = scope
    with pytest.raises(ValueError, match='VISUAL_PROMPT_NEGATIVE_NOT_CURRENT'):
        compile_frame(frame.model_copy(update={'prompt_ir': ir}))


def test_current_constraint_cannot_receive_noncurrent_target():
    frame = frame_with_limits((LIMIT, UNRELATED))
    ir = deepcopy(frame.prompt_ir)
    ir['negative_constraints'][0]['positive_target']['scope'] = 'FUTURE'
    with pytest.raises(ValueError, match='REQUIRED_FIELD_NOT_EXECUTABLE:positive_target'):
        compile_frame(frame.model_copy(update={'prompt_ir': ir}))


def test_constraint_priority_and_budget_are_preserved_without_optional_fallback():
    frame = frame_with_limits((LIMIT, UNRELATED))
    ir = deepcopy(frame.prompt_ir)
    ir['secondary_details'] = []
    provider = ir['task']['provider_family']
    baseline = compile_ir(ir, provider_family=provider)
    ir['secondary_details'] = [fact('Optional backdrop texture. ' * 500, 'SECONDARY')]
    compact = compile_ir(ir, provider_family=provider, hard_limit=len(baseline['prompt']))
    assert compact['prompt'] == baseline['prompt'] and LIMIT in compact['prompt']
    assert any(r['reason'] == 'SECONDARY_BUDGET' for r in compact['omitted'])
    with pytest.raises(ValueError, match='PROVIDER_PROMPT_BUDGET_EXCEEDED'):
        compile_ir(ir, provider_family=provider, hard_limit=len(baseline['prompt']) - 1)
    ir['negative_constraints'][0]['positive_target']['priority'] = 'IMPORTANT'
    with pytest.raises(ValueError, match='NEGATIVE_PRIORITY_LOSS'):
        compile_ir(ir, provider_family=provider)


def test_reference_edit_preserves_limit_and_operations_in_ark_body(tmp_path, monkeypatch):
    _, ref = symbolic_input(tmp_path, monkeypatch)
    frame = reference_spec(ref)
    ir = deepcopy(frame.prompt_ir)
    ir['negative_constraints'] = [dict(constraint=fact(LIMIT), positive_target=fact(UNRELATED))]
    compiled, prompt = ark_json(frame.model_copy(update={'prompt_ir': ir}))
    assert LIMIT in prompt and UNRELATED in prompt
    assert 'MUST CHANGE' in prompt and 'Replace costume:' in prompt and 'PRESERVE' in prompt
    assert compiled['request']['body']['image'].startswith('data:image/png;base64,')
    assert not any(r['path'] == 'constraint[0]' for r in compiled['prompt_ir_compilation']['omitted'])


def test_edit_asset_source_limit_is_not_repeated_in_inherited_design(tmp_path, monkeypatch):
    _, ref = symbolic_input(tmp_path, monkeypatch)
    frame = reference_spec(ref)
    ir = deepcopy(frame.prompt_ir)
    limit = {**fact(LIMIT), 'source': 'asset-design/selected/constraint'}
    ir['negative_constraints'] = [dict(constraint=limit, positive_target=deepcopy(limit))]
    _, prompt = ark_json(frame.model_copy(update={'prompt_ir': ir}))
    assert prompt.count(LIMIT) == 1


def test_frozen_old_request_replays_exactly_and_new_preparation_retains_limit():
    frame = frame_with_limits((LIMIT, UNRELATED))
    # Reproduce the pre-fix sealed record only through the explicit replay mode.
    old = compile_frame(frame, _legacy_ir_replay=True)
    sealed = deepcopy(old)
    old_wire = json.dumps(old['request'], ensure_ascii=False, sort_keys=True)
    assert LIMIT not in old['request']['body']['prompt']
    verify_compiled(old)
    verify_compilation(old['prompt_ir_compilation'], old['request']['body']['prompt'])
    assert old == sealed
    assert json.dumps(old['request'], ensure_ascii=False, sort_keys=True) == old_wire
    new, prompt = ark_json(frame)
    assert LIMIT in prompt and new['fingerprint'] != old['fingerprint']
    modified = deepcopy(old)
    modified['request']['body']['prompt'] += ' arbitrary replacement'
    with pytest.raises(ValueError, match='STALE_OR_MODIFIED_FRAME_REQUEST'):
        verify_compiled(modified)
    modified_ir = deepcopy(old['prompt_ir_compilation'])
    modified_ir['prompt'] += ' arbitrary replacement'
    with pytest.raises(ValueError, match='VISUAL_PROMPT_IR_COMPILATION_CHANGED'):
        verify_compilation(modified_ir, modified_ir['prompt'])
    # Keeping the source fingerprint is necessary but not a substitute for the
    # complete retained-row/prose equality checked by the real verifier.
    assert fp(new['prompt_ir_compilation']['ir']) == fp(old['prompt_ir_compilation']['ir'])


def test_complete_historical_record_can_replay_when_new_source_limit_needs_author_clarification():
    # Previously constraint.text was internal and unreviewed. It must not be
    # newly submitted as unscoped source text or rewrite an exact old artifact.
    frame = frame_with_limits(('future scene: internal author note', UNRELATED))
    old = compile_frame(frame, _legacy_ir_replay=True)
    sealed = deepcopy(old)
    with pytest.raises(ValueError, match='PAYLOAD_SCOPE_VIOLATION'):
        compile_frame(frame)
    verify_compiled(old)
    verify_compilation(old['prompt_ir_compilation'], old['request']['body']['prompt'])
    assert old == sealed
