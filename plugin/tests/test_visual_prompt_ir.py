from copy import deepcopy
import pytest
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.contracts.visual_prompt import VisualPromptIR
from drama_plugin.visual.prompt_ir import compile_ir, require_submission_ir, verify_compilation


def fact(text, priority='CRITICAL', scope='CURRENT'):
    return dict(text=text, priority=priority, scope=scope, source='test:approved-visual-intent')


def visual_ir(task='FIRST_FRAME', provider='Flux.2 [pro]'):
    f = fact
    ir = dict(source_fingerprint='a'*64,
        task=dict(task_type=task, provider_family=provider, visual_medium='LIVE_ACTION',
                  subject_kind='COMPOSITE', input_mode='text'),
        world=dict(era=f('19th century'), location=f('Petersburg'), historical_context=f('historical city street'),
                   environment_rules=[f('Period-compatible street fixtures only')]),
        subjects=[dict(id='man', role=f('man'), apparent_age=f('38–42 years old'), face=f('narrow long face'),
                       hair=f('short dark brown hair'), beard=f('short uneven stubble'), body_proportions=f('ordinary narrow shoulders'),
                       costume=f('old wool coat', 'IMPORTANT'), visible_condition=f('natural skin', 'IMPORTANT'))],
        blocking=dict(positions=f('man left, girl right'), orientation=f('girl faces man'),
                      contact=f('hands separate from sleeve'), visible_relation=f('girl approaches man')),
        action=dict(current_visible_action=f('standing step'), expression=f('restrained expression'),
                    non_current=[f('hand can grip an adult sleeve', scope='CAPABILITY')]),
        environment=dict(architecture=f('plaster facades', 'IMPORTANT'), topology=f('side street junction', 'IMPORTANT'),
                         required_period_objects=f('gas street lamps', 'IMPORTANT')),
        camera=dict(framing=f('two people, left and right', 'IMPORTANT'), shot_size=f('full body', 'IMPORTANT'),
                    readable_details=f('faces and shoes readable', 'IMPORTANT'), perspective=f('eye level', 'IMPORTANT')),
        lighting=dict(time_of_day=f('night', 'IMPORTANT'), light_sources=f('gas lamps', 'IMPORTANT'),
                      contrast=f('readable shadows', 'IMPORTANT'), realism=f('natural textures', 'IMPORTANT')),
        negative_constraints=[dict(constraint=f('no scars'), positive_target=f('intact natural skin'))],
        secondary_details=[f('minor wear on stone ' * 25, 'SECONDARY')])
    if task in {'IMAGE_EDIT', 'REFERENCE_EDIT'}:
        ir['task']['input_mode'] = 'edit' if task == 'IMAGE_EDIT' else 'reference'
        ir['edit_delta'] = [dict(operation='correct', region='man face', source_issue=f('man appears too old'),
                                 target_correction=f('38–42 years old')),
                            dict(operation='replace', region='right background', source_issue=f('modern parking sign'),
                                 target_correction=f('continuous historical plaster facade'))]
        ir['preserve'] = [f('two-person composition, positions, approaching girl, wet stone road')]
    if task == 'VIDEO':
        ir['task']['clip_id'] = 'clip-1'
        ir['video_temporal'] = dict(start_state=f('girl approaches'), action_progression=[f('girl grips sleeve', scope='CLIP')],
            performance=[f('man slowly turns to listen', scope='CLIP')], camera_motion=f('locked camera', scope='CLIP'),
            end_state=f('contact maintained'), audio_requirements=[])
    return ir


@pytest.mark.parametrize('task', ['TEXT_TO_IMAGE', 'FIRST_FRAME', 'KEY_FRAME'])
def test_static_contract_and_preserved_internal_intent(task):
    ir = visual_ir(task); before = deepcopy(ir)
    c = compile_ir(ir, provider_family='Flux.2 [pro]')
    assert 'man: 38–42 years old' in c['prompt']
    for text in ['19th century', 'old wool coat', 'gas street lamps', 'man left, girl right']:
        assert text in c['prompt']
    assert 'hand can grip' not in c['prompt'] and 'no scars' not in c['prompt']
    assert 'intact natural skin' in c['prompt']
    assert ir == before and c['ir']['action']['non_current'] == before['action']['non_current']
    verify_compilation(c, c['prompt'])


@pytest.mark.parametrize('task', ['IMAGE_EDIT', 'REFERENCE_EDIT'])
def test_edit_corrections_survive_positive_projection(task):
    c = compile_ir(visual_ir(task), provider_family='Flux.2 [pro]')
    p = c['prompt']
    assert p.startswith('MUST CHANGE\n')
    assert 'man appears too old → 38–42' in p and 'Correct man face' in p
    assert 'modern parking sign → continuous historical' in p and 'Replace right background' in p
    assert 'PRESERVE' in p and 'wet stone road' in p
    assert p.index('MUST CHANGE') < p.index('PRESERVE') < p.index('TARGET RESULT')
    ir = visual_ir(task); ir['edit_delta'][1]['operation'] = 'remove'
    assert 'Remove right background' in compile_ir(ir, provider_family='Flux.2 [pro]')['prompt']


@pytest.mark.parametrize('mode', ['text', 'single_image', 'first_last', 'reference'])
def test_video_temporal_and_audio_contract(mode):
    ir = visual_ir('VIDEO'); ir['task']['input_mode'] = mode
    ir['video_temporal']['audio_requirements'] = [fact('Dialogue: Please listen', scope='CLIP')]
    with pytest.raises(ValueError, match='AUDIO_UNSUPPORTED'):
        compile_ir(ir, provider_family='Flux.2 [pro]')
    c = compile_ir(ir, provider_family='Flux.2 [pro]', audio_supported=True)
    for field in ['start_state', 'action_progression', 'performance', 'camera_motion', 'end_state', 'audio_requirements']:
        assert 'video.' + field in c['prompt']
    assert 'hand can grip' not in c['prompt']
    assert 'AT CLIP START: hands separate from sleeve' in c['prompt']


def test_priority_budget_protects_all_required_facts():
    ir = visual_ir()
    full = compile_ir(ir, provider_family='Flux.2 [pro]')
    without = deepcopy(ir); without['secondary_details'] = []
    compact = compile_ir(without, provider_family='Flux.2 [pro]')
    limited = compile_ir(ir, provider_family='Flux.2 [pro]', hard_limit=len(compact['prompt']))
    assert limited['prompt'] == compact['prompt']
    assert any(x['reason'] == 'SECONDARY_BUDGET' for x in limited['omitted'])
    assert len(full['prompt']) > len(limited['prompt'])
    with pytest.raises(ValueError, match='PROVIDER_PROMPT_BUDGET_EXCEEDED'):
        compile_ir(ir, provider_family='Flux.2 [pro]', hard_limit=100)
    ir['subjects'][0]['apparent_age']['priority'] = 'SECONDARY'
    with pytest.raises(ValueError, match='PRIORITY_TOO_LOW'):
        compile_ir(ir, provider_family='Flux.2 [pro]')


@pytest.mark.parametrize('mutation', ['age', 'era', 'delta', 'preserve', 'control', 'temporal', 'provider'])
def test_missing_or_wrong_contract_fails_closed(mutation):
    ir = visual_ir('IMAGE_EDIT')
    if mutation == 'age': del ir['subjects'][0]['apparent_age']
    if mutation == 'era': del ir['world']['era']
    if mutation == 'delta': ir['edit_delta'] = []
    if mutation == 'preserve': ir['preserve'] = []
    if mutation == 'control': ir['camera']['framing']['text'] = 'Director constraints: future scene'
    if mutation == 'temporal': ir['video_temporal'] = visual_ir('VIDEO')['video_temporal']
    if mutation == 'provider': ir['task']['provider_family'] = 'other'
    with pytest.raises(ValueError): compile_ir(ir, provider_family='Flux.2 [pro]')


def test_scene_and_character_text_to_image():
    ir = visual_ir('TEXT_TO_IMAGE'); ir['task']['subject_kind'] = 'CHARACTER'
    assert '38–42 years old' in compile_ir(ir, provider_family='Flux.2 [pro]')['prompt']
    ir['task']['subject_kind'] = 'SCENE'; ir['subjects'] = []; ir.pop('action'); ir.pop('blocking')
    assert 'plaster facades' in compile_ir(ir, provider_family='Flux.2 [pro]')['prompt']


def test_frame_integration_and_submission_gate(tmp_path):
    from test_route_image_inputs import image_input
    from drama_plugin.visual.frame_request import compile_frame, verify_compiled
    spec, template = image_input(tmp_path)
    old = compile_frame(spec, template)
    with pytest.raises(ValueError, match='IR_REQUIRED_BEFORE_SUBMISSION'):
        require_submission_ir(old, old['request'])
    ir = visual_ir(); ir['source_fingerprint'] = fp(spec.model_dump(mode='json', exclude={'prompt_ir'}))
    ir['subjects'] = [{**deepcopy(ir['subjects'][0]), 'id': a.entity_key} for a in spec.actors]
    compiled = compile_frame(spec.model_copy(update={'prompt_ir': ir}), template)
    verify_compiled(compiled)
    require_submission_ir(compiled, compiled['request'])
    assert compiled['request']['workflow']['1']['inputs']['prompt'] == compiled['prompt_ir_compilation']['prompt']
    request = deepcopy(compiled['request']); request['workflow']['1']['inputs']['prompt'] += ' extra'
    with pytest.raises(ValueError, match='PAYLOAD_MISMATCH'):
        require_submission_ir(compiled, request)
    ir['source_fingerprint'] = 'b'*64
    with pytest.raises(ValueError, match='IR_SOURCE_CHANGED'):
        compile_frame(spec.model_copy(update={'prompt_ir': ir}), template)


def test_http_rejects_legacy_before_network():
    import asyncio
    from test_official_video_providers import request
    from drama_plugin.visual.video_prompt import compile_request_ir
    with pytest.raises(ValueError, match='IR_REQUIRED_BEFORE_SUBMISSION'):
        compile_request_ir(request().model_copy(update={'prompt_ir': None}))


async def test_http_legacy_rejected_without_resolving_media_or_posting():
    import httpx
    from test_official_video_providers import request, ADAPTERS, MODELS, config
    calls=[]
    async def resolve(ref):
        calls.append('resolve'); raise AssertionError('must not resolve')
    def handler(req):
        calls.append('HTTP'); raise AssertionError('must not submit')
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter=ADAPTERS['seedance'](MODELS['seedance'],config('seedance'),resolve=resolve,client=client)
        with pytest.raises(ValueError,match='IR_REQUIRED_BEFORE_SUBMISSION'):
            await adapter.create_task(request().model_copy(update={'prompt_ir':None}),client_request_id='offline')
    assert calls==[]


def test_reference_edit_frame_preserves_operation_and_rejects_old_normalizer(tmp_path):
    from test_route_image_inputs import image_input
    from drama_plugin.visual.frame_request import compile_frame, verify_compiled
    spec, template=image_input(tmp_path,shared=True)
    ir=visual_ir('REFERENCE_EDIT')
    ir['subjects']=[{**deepcopy(ir['subjects'][0]),'id':a.entity_key} for a in spec.actors]
    ir['source_fingerprint']=fp(spec.model_dump(mode='json',exclude={'prompt_ir'}))
    compiled=compile_frame(spec.model_copy(update={'prompt_ir':ir}),template)
    verify_compiled(compiled)
    require_submission_ir(compiled,compiled['request'])
    assert 'Replace right background' in compiled['prompt_ir_compilation']['prompt']
    with pytest.raises(ValueError,match='POST_REWRITE_FORBIDDEN'):
        compile_frame(spec.model_copy(update={'prompt_ir':ir,'prompt_normalization':{'rules':[]}}),template)
