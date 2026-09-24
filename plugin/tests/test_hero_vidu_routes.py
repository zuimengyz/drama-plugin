from copy import deepcopy
import pytest
from test_route_image_inputs import image_input
from test_visual_prompt_ir import visual_ir, fact
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.visual.frame_request import compile_frame, verify_compiled
from drama_plugin.visual.prompt_ir import compile_ir, require_submission_ir


@pytest.mark.parametrize('task', ['TEXT_TO_IMAGE', 'FIRST_FRAME', 'KEY_FRAME', 'REFERENCE_EDIT'])
def test_default_formal_frame_route_is_gpt_image2_without_fallback(tmp_path, task):
    spec, old_template = image_input(tmp_path, shared=task == 'REFERENCE_EDIT')
    ir = visual_ir(task)
    ir['subjects'] = [{**deepcopy(ir['subjects'][0]), 'id': a.entity_key} for a in spec.actors]
    ir['source_fingerprint'] = fp(spec.model_dump(mode='json', exclude={'prompt_ir'}))
    spec = spec.model_copy(update={'prompt_ir': ir}); before = deepcopy(spec.model_dump())
    new = compile_frame(spec)
    assert new['template']['model'] == 'gpt-image-2'
    node = new['request']['workflow']['271']
    assert node['class_type'] == 'OpenAIGPTImageNodeV2'
    assert node['inputs']['model'] == 'gpt-image-2' and node['inputs']['n'] == 1
    assert node['inputs']['model.quality'] == 'high'
    assert spec.model_dump() == before
    verify_compiled(new); require_submission_ir(new, new['request'])
    old = compile_frame(spec, old_template)
    verify_compiled(old)  # history can still replay, but cannot authorize new frame dispatch
    with pytest.raises(ValueError, match='HERO_KEYFRAME_ROUTE_REQUIRES_GPT_IMAGE2'):
        require_submission_ir(old, old['request'])


@pytest.mark.parametrize('mutation', ['model', 'dimensions', 'count', 'extra_node'])
def test_gpt_graph_rejects_uninspected_changes(tmp_path, mutation):
    from drama_plugin.visual.image_route import select_frame_template
    spec, _ = image_input(tmp_path); template = select_frame_template(spec)
    api = deepcopy(template.api_workflow); inputs = api['271']['inputs']
    if mutation == 'model': inputs['model'] = 'gpt-image-2.5-flare'
    if mutation == 'dimensions': inputs['model.custom_width'] = 1024
    if mutation == 'count': inputs['n'] = 2
    if mutation == 'extra_node': api['extra'] = {'class_type': 'Flux2ImageNode', 'inputs': {}}
    with pytest.raises(ValueError): compile_frame(spec, template.model_copy(update={'api_workflow': api}))


def test_vidu_compact_temporal_and_authority_facts_survive():
    ir = visual_ir('VIDEO', 'Vidu Q3 Turbo'); ir['task']['input_mode'] = 'single_image'
    ir['continuity'] = [fact('locked garment anchor')]
    ir['video_temporal']['audio_requirements'] = [fact('Exact dialogue: 妈妈……先生，妈妈……', scope='CLIP')]
    before = deepcopy(ir)
    c = compile_ir(ir, provider_family='Vidu Q3 Turbo', audio_supported=True, hard_limit=2000)
    assert len(c['prompt']) <= 2000 and ir == before
    assert c['ir']['subjects'][0]['hair'] == before['subjects'][0]['hair']
    for key in ['START STATE', 'ACTION', 'PERFORMANCE', 'CAMERA', 'END STATE', 'AUDIO', 'locked garment anchor']:
        assert key in c['prompt']
    for v in ir['video_temporal'].values():
        for f in v if isinstance(v, list) else [v]: assert f['text'] in c['prompt']
    assert 'short dark brown hair' not in c['prompt']
    assert 'hand can grip' not in c['prompt'] and 'CRITICAL' not in c['prompt']
    with pytest.raises(ValueError, match='AUDIO_UNSUPPORTED'):
        compile_ir(ir, provider_family='Vidu Q3 Turbo', hard_limit=2000)
    ir['video_temporal']['performance'] = [fact('must preserve acting direction ' * 200, scope='CLIP')]
    with pytest.raises(ValueError, match='PROVIDER_PROMPT_BUDGET_EXCEEDED'):
        compile_ir(ir, provider_family='Vidu Q3 Turbo', audio_supported=True, hard_limit=2000)


def test_text_video_has_no_reference_assumed():
    ir = visual_ir('VIDEO', 'Vidu Q3 Turbo')
    c = compile_ir(ir, provider_family='Vidu Q3 Turbo')
    assert 'short dark brown hair' in c['prompt'] and 'side street junction' in c['prompt']
