"""Scope classification examples; these do not stand in for author delivery."""
from copy import deepcopy

import pytest

from drama_plugin.visual.payload_scope import review_text
from drama_plugin.visual.prompt_ir import compile_ir
from test_visual_prompt_ir import fact, visual_ir


@pytest.mark.parametrize('text', [
    '本图的临时姿态、暖灰背景和白昼照明只服务参考证明，不成为角色永久属性或后续镜头指令。',
    '此参考图不作为下一场的要求。',
    '参考照明不应继承为未来场景规则。',
    'This reference pose does not become a later scene instruction.',
    'The reference lighting must not be inherited as a future continuity requirement.',
    'This reference image is not a future scene constraint.',
])
def test_closed_noninheritance_is_not_a_future_action(text):
    # Classification is not text cleaning: the input and compiled fact survive.
    before = deepcopy(text)
    review_text(text, 'IMAGE')
    ir = visual_ir('TEXT_TO_IMAGE')
    ir['continuity'] = [fact(text)]
    result = compile_ir(ir, provider_family='Flux.2 [pro]')
    assert text == before
    assert text in result['prompt']
    assert result['ir']['continuity'][0]['text'] == text


@pytest.mark.parametrize('text', [
    '后续镜头中，人物起身走向门口。',
    '下一场人物不离开房间。',
    '不成为后续镜头中起身的指令。',
    '不成为后续镜头指令并要求人物起身。',
    '并非不成为后续镜头指令。',
    '不是不成为后续镜头指令。',
    '不成为后续镜头指令，但下一场人物起身。',
    '不成为后续镜头指令；后续镜头保持这个姿态。',
    '本图不表现下一场人物起身的动作。',
    'The later scene shows him walking away.',
    'This reference pose does not become a later scene instruction to stand up.',
    'This reference pose is not a later scene instruction unless he stands.',
    'It is not true that this reference pose is not a later scene instruction.',
    'This reference pose is not a later scene instruction; future action: he stands.',
    'Do not use the later scene action in this image.',
])
def test_future_or_unrecognised_mixed_statements_remain_rejected(text):
    with pytest.raises(ValueError, match='SCOPE_VIOLATION:unscoped source text'):
        review_text(text, 'IMAGE')


@pytest.mark.parametrize('suffix', [
    '\nDirector constraints: approved only',
    '\n声音：关门声',
    '\napproval_metadata: APPROVED',
])
def test_noninheritance_does_not_exempt_control_or_sound(suffix):
    with pytest.raises(ValueError, match='SCOPE_VIOLATION:unscoped source text'):
        review_text('不成为后续镜头指令。' + suffix, 'IMAGE')


@pytest.mark.parametrize('scope', ['CURRENT', 'FUTURE', 'INTERNAL'])
def test_real_future_action_cannot_be_mislabelled_into_required_field(scope):
    ir = visual_ir('TEXT_TO_IMAGE')
    ir['continuity'] = [fact('下一场，人物走向门口。', scope=scope)]
    expected = 'SCOPE_VIOLATION' if scope == 'CURRENT' else 'REQUIRED_FIELD_NOT_EXECUTABLE'
    with pytest.raises(ValueError, match=expected):
        compile_ir(ir, provider_family='Flux.2 [pro]')


def test_non_current_source_actions_still_do_not_enter_static_prompt():
    ir = visual_ir('TEXT_TO_IMAGE')
    future = '下一场，人物走向门口。'
    ir['action']['non_current'] = [fact(future, scope='FUTURE')]
    before = deepcopy(ir)
    result = compile_ir(ir, provider_family='Flux.2 [pro]')
    assert ir == before
    assert result['ir']['action']['non_current'] == before['action']['non_current']
    assert future not in result['prompt']
    assert {'path': 'action.non_current[0]', 'reason': 'NON_CURRENT_SOURCE_ONLY'} in result['omitted']


@pytest.mark.parametrize('text', ['当前无人、无棺木。', '无人物，门仍保持关闭。',
                                  'The current empty room contains no coffin.'])
def test_current_visible_absence_is_not_future_execution(text):
    review_text(text, 'IMAGE')
