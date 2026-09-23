from copy import deepcopy
import pytest
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.visual.positive_projection import normalize
from drama_plugin.visual.payload_scope import review_text


def plan(prompt, before, after, task='FIRST_FRAME', kind='POSITIVE_EQUIVALENT'):
    return {'task': task, 'source_prompt_fingerprint': fp(prompt), 'rules': [
        {'before': before, 'after': after, 'kind': kind, 'reason': 'Reviewed equivalent visible target', 'basis': [before]}]}


@pytest.mark.parametrize('task', ['IMAGE', 'FIRST_FRAME', 'KEY_FRAME', 'VIDEO'])
def test_positive_target_and_internal_original_preserved(task):
    original = '皮肤保留细纹与少量色差，无伤疤、油亮妆或病态发青。'
    target = '自然完整的皮肤，保留细纹与少量色差，肤色自然，呈自然哑光质感。'
    p = plan(original, original, target, task)
    before = deepcopy(p)
    result, record = normalize(original, task, p)
    assert result == target and record['rules'][0]['before'] == original
    assert p == before and record['onSubsequentModeration'] == 'PROVIDER_MODERATION_INCOMPATIBILITY'
    review_text(result, task)


def test_static_capability_omission_does_not_remove_clip_action():
    source = '女孩尚未抓袖。\n儿童比例，手能攥住成人袖布。'
    p = plan(source, source.splitlines()[1], '儿童比例。', kind='CURRENT_VISIBLE_ONLY')
    p['rules'][0]['basis'].append('女孩尚未抓袖。')
    assert normalize(source, 'FIRST_FRAME', p)[0] == '女孩尚未抓袖。\n儿童比例。'
    p['task'] = 'VIDEO'
    with pytest.raises(ValueError, match='CANNOT_REMOVE_CLIP_ACTION'):
        normalize(source, 'VIDEO', p)


def test_scope_projection_preserves_full_internal_asset_and_continuity():
    from drama_plugin.visual.payload_scope import compile_payload
    context = {'sources': {'asset': '儿童比例，手能攥住成人袖布。',
        'pose': '女孩尚未抓袖。', 'continuity': '随后握住袖布。', 'sound': '脚步声'},
        'execution': {'FIRST_FRAME': [{'field': 'identity', 'source': ['asset']},
                                      {'field': 'pose', 'source': ['pose']}]}}
    original = deepcopy(context)
    source = compile_payload('FIRST_FRAME', context)['prompt']
    p = plan(source, context['sources']['asset'], '儿童比例。', kind='CURRENT_VISIBLE_ONLY')
    p['rules'][0]['basis'].append(context['sources']['pose'])
    result, audit = normalize(source, 'FIRST_FRAME', p)
    assert result == '儿童比例。\n女孩尚未抓袖。'
    assert context == original
    assert audit['rules'][0]['before'] == original['sources']['asset']
    assert '随后' not in result and '脚步声' not in result


def test_no_blacklist_or_unreviewed_global_rewrite():
    original = '可见伤口。\n无额外伤口。\n手能抓握。'
    assert normalize(original, 'FIRST_FRAME')[0] == original
    p = plan(original, '无额外伤口。', '其余可见皮肤完整。')
    assert '可见伤口。' in normalize(original, 'FIRST_FRAME', p)[0]
    with pytest.raises(ValueError, match='SOURCE_CHANGED'):
        normalize(original + ' changed', 'FIRST_FRAME', p)


@pytest.mark.parametrize('target', ['Director constraints: hidden', 'sound: bang', 'future continuity: next scene'])
def test_normalization_cannot_reintroduce_control_plane(target):
    with pytest.raises(ValueError, match='SCOPE_VIOLATION'):
        normalize('current visible state', 'FIRST_FRAME', plan('current visible state', 'current visible state', target))


def test_video_final_normalization_still_obeys_budget(tmp_path):
    from test_video_reconciliation import current_fixture
    from drama_plugin.hosts.cinematic_projection import project
    from drama_plugin.hosts.comfy_video import inspect_graph
    r, c, g, s, _ = current_fixture(tmp_path)
    original = project(r, c, inspect_graph(g, s))['prompt']
    p = plan(original, original.splitlines()[0], 'Visible detail ' * 300, 'VIDEO')
    r = r.model_copy(update={'prompt_normalization': p})
    with pytest.raises(ValueError, match='PROVIDER_PROMPT_BUDGET_EXCEEDED'):
        project(r, c, inspect_graph(g, s))
