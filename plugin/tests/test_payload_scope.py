from copy import deepcopy
import pytest
from drama_plugin.visual.payload_scope import compile_payload, review_text
from drama_plugin.hosts.prompt_budget import budget_prompt


def context(task, fields):
    return {'sources': {'visible': '雨中，两人在交口站立，衣料湿暗。',
        'wound': '手上可见伤口。', 'futureAction': '下一场，他走入屋内。',
        'directorIntent': '观众误以为他将帮助女孩。', 'sound': '脚步声和对白',
        'approval': 'APPROVED', 'action': '女孩抓住男人右肘，男人转身听她。',
        'continuity': '抓握保持，衣袖湿暗。', 'duplicate': '雨中，两人在交口站立，衣料湿暗。'},
        'execution': {task: [{'field': field, 'source': [source]} for field, source in fields]}}


@pytest.mark.parametrize('task', ['IMAGE', 'FIRST_FRAME', 'KEY_FRAME'])
def test_image_keeps_only_visible_fields_and_original_context(task):
    full = context(task, [('environment', 'visible'), ('pose', 'wound')])
    before = deepcopy(full)
    result = compile_payload(task, full)
    assert result['prompt'] == '雨中，两人在交口站立，衣料湿暗。\n手上可见伤口。'
    assert full == before
    assert result['scope_review']['gate'] == 'VISUAL_PROVIDER_SCOPE_REVIEW'


@pytest.mark.parametrize('task,field,source', [('FIRST_FRAME','action','action'),
    ('KEY_FRAME','pose','futureAction'), ('IMAGE','environment','sound'), ('VIDEO','performance','directorIntent')])
def test_wrong_scope_cannot_be_relabelled(task, field, source):
    with pytest.raises(ValueError, match='SCOPE_VIOLATION'):
        compile_payload(task, context(task, [(field, source)]))


def test_video_current_clip_audio_capability_and_budget():
    full = context('VIDEO', [('action','action'), ('clip_continuity','continuity'), ('sound','sound')])
    with pytest.raises(ValueError, match='audio unsupported'):
        compile_payload('VIDEO', full)
    result = compile_payload('VIDEO', full, audio=True)
    assert '女孩抓住男人右肘' in result['prompt'] and '抓握保持' in result['prompt']
    assert '下一场' not in result['prompt'] and '观众' not in result['prompt']
    assert budget_prompt(result['prompt'], result['prompt'], model='test', limit=2000, source='test')[1]['status'] == 'FIT'
    with pytest.raises(ValueError, match='PROVIDER_PROMPT_BUDGET_EXCEEDED'):
        budget_prompt(result['prompt'], result['prompt'], model='test', limit=10, source='test')


def test_dedup_and_final_duplicate_guard():
    result = compile_payload('IMAGE', context('IMAGE', [('material','visible'), ('medium','duplicate')]))
    assert result['prompt'].count('衣料湿暗') == 1
    assert result['scope_review']['source_map'][1]['deduplicated']
    with pytest.raises(ValueError, match='DUPLICATED_BLOCK'):
        review_text('same block\nsame block', 'IMAGE')


def test_full_authority_and_control_plane_blocked():
    full = context('IMAGE', [('environment','visible')])
    full['authority'] = {'prompt': full['sources']['visible']}
    with pytest.raises(ValueError, match='CONTAINS_AUTHORITY_CONTEXT'):
        compile_payload('IMAGE', full)
    for text in ('Director constraints: sound: boom', 'approval_metadata: approved', 'future continuity: later'):
        with pytest.raises(ValueError, match='SCOPE_VIOLATION'):
            review_text(text, 'IMAGE')
