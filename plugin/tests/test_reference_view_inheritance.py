"""Reference inheritance behavior only; no claim of model/image quality."""
from copy import deepcopy
import json

import pytest

from drama_plugin.professional_design.reference_design import (
    COMPOSITION_SOURCE, DesignCompletionRequired, inherit_design, verify_design_delivery)
from drama_plugin.visual.frame_request import compile_frame
from test_target_reference_production import reference_frame


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    import socket
    def denied(*a, **kw):
        raise AssertionError('No network or author/media call is allowed')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)
    monkeypatch.setenv('DRAMA_PLUGIN_ROUTE_IMAGE_MODEL', 'Doubao-Seedream-5.0-pro')


def artwork(proof='Doorframe at one frame edge; bench and board readable'):
    item = dict(assetType='LOCATION', name='Fictional room', subjectId=None,
        designRef=dict(key='view-test', kind='DIRECTION', fingerprint='d' * 64),
        design=dict(architecture='One low room', topology='Door on the front wall',
                    material='Wood and cloth have different local reflectance', proof=proof))
    original = reference_frame(item)
    ir = deepcopy(original.prompt_ir)
    ir['camera']['framing'].update(text='Doorframe at the left edge of the frame; bench readable',
                                  source='reference-author.camera')
    original = original.model_copy(update={
        'composition': 'Doorframe at the left edge of the frame; the bench and board form the visual center',
        'prompt_ir': ir})
    return item, original


def test_view_and_attention_arrive_without_replacing_selected_proof():
    item, original = artwork()
    before = original.model_dump(mode='json')
    frame = inherit_design(original, item)
    assert frame.composition == original.composition
    assert frame.prompt_ir['camera']['framing'] == original.prompt_ir['camera']['framing']
    compiled = compile_frame(frame)
    verify_design_delivery(compiled, item)
    wire = json.loads(json.dumps(compiled['request']['body']))
    for text in (original.composition, original.prompt_ir['camera']['framing']['text'],
                 *item['design'].values()):
        assert text in wire['prompt']
    rows = compiled['prompt_ir_compilation']['retained']
    assert len([r for r in rows if r['source'] == COMPOSITION_SOURCE]) == 1
    assert original.model_dump(mode='json') == before
    again = inherit_design(frame, item)
    assert again == frame
    assert compile_frame(again) == compiled


@pytest.mark.parametrize('proof,view', [
    ('Doorframe at the right edge of the frame', 'Doorframe at the left edge of the frame'),
    ('厚门框留在画面右缘', '厚门框留在画面左缘'),
])
def test_same_object_same_frame_coordinate_conflict_returns_author(proof, view):
    item, original = artwork(proof)
    ir = deepcopy(original.prompt_ir)
    ir['camera']['framing']['text'] = view
    frame = original.model_copy(update={'composition': view, 'prompt_ir': ir})
    before = frame.model_dump(mode='json')
    with pytest.raises(DesignCompletionRequired, match='REFERENCE_VIEW_CONFLICT'):
        inherit_design(frame, item)
    assert frame.model_dump(mode='json') == before


def test_room_left_is_not_picture_left_or_a_conflict():
    item, original = artwork('入口在前墙右侧，门框留在画面一侧；台板可辨。')
    ir = deepcopy(original.prompt_ir)
    ir['camera']['framing']['text'] = '厚门框留在画面左缘，台板可辨。'
    original = original.model_copy(update={'composition': '厚门框留在画面左缘，台板为视觉中心。',
                                            'prompt_ir': ir})
    frame = inherit_design(original, item)
    assert '视觉中心' in compile_frame(frame)['request']['body']['prompt']


@pytest.mark.parametrize('proof,view', [
    ('门框留在画面左缘', '另一门框留在画面右缘'),
    ('禁止门框留在画面左缘', '门框留在画面右缘'),
    ('门框不应留在画面左缘', '门框不应留在画面右缘'),
    ('No doorframe at the left edge of the frame', 'Doorframe at the right edge of the frame'),
    ('Doorframe at the left edge of the frame', 'Another doorframe at the right edge of the frame'),
])
def test_other_objects_and_negative_limits_are_not_positive_conflicts(proof, view):
    item, original = artwork(proof)
    ir = deepcopy(original.prompt_ir)
    ir['camera']['framing']['text'] = view
    frame = original.model_copy(update={'composition': view, 'prompt_ir': ir})
    result = inherit_design(frame, item)
    prompt = compile_frame(result)['request']['body']['prompt']
    assert proof in prompt and view in prompt


def test_author_composition_and_camera_cannot_assert_opposite_edges():
    item, original = artwork()
    original = original.model_copy(update={'composition': 'Doorframe at the right edge of the frame'})
    with pytest.raises(DesignCompletionRequired, match='composition:camera.framing'):
        inherit_design(original, item)


def test_wrapped_composition_keeps_all_facts_and_original_frame():
    item, original = artwork()
    composition = 'Doorframe at the left edge of the frame.\nThe bench and board form the visual center.'
    original = original.model_copy(update={'composition':composition})
    frame = inherit_design(original, item)
    assert frame.composition == original.composition == composition
    prompt = compile_frame(frame)['request']['body']['prompt']
    assert ' '.join(composition.splitlines()) in prompt
    assert inherit_design(frame, item) == frame


@pytest.mark.parametrize('label', ['声音：关门声', 'Sound: a door closes'])
def test_composition_line_wrapping_cannot_hide_nonvisual_source(label):
    item, original = artwork()
    composition = 'Doorframe at the left edge of the frame.\n' + label
    original = original.model_copy(update={'composition':composition})
    with pytest.raises(ValueError, match='SCOPE_VIOLATION:unscoped source text'):
        inherit_design(original, item)
    assert original.composition == composition


def test_existing_generated_proof_has_one_source_and_stays_idempotent():
    item, original = artwork()
    ir = deepcopy(original.prompt_ir)
    ir['camera']['framing'] = dict(text=item['design']['proof'], priority='CRITICAL', scope='CURRENT',
        source='asset-design/' + item['designRef']['fingerprint'] + '/proof')
    frame = original.model_copy(update={'composition': item['design']['proof'], 'prompt_ir': ir})
    current = inherit_design(frame, item)
    compiled = compile_frame(current)
    verify_design_delivery(compiled, item)
    assert current == inherit_design(current, item)
    assert len([r for r in compiled['prompt_ir_compilation']['retained']
                if r['source'].endswith('/proof')]) == 1


def test_old_system_view_refresh_does_not_retain_a_stale_proof():
    item, original = artwork()
    ir = deepcopy(original.prompt_ir)
    old_proof = 'An old view to be reassessed'
    item['inheritedDesign'] = {'proof': old_proof}
    item['inheritedDesignRef'] = {'fingerprint': 'a' * 64}
    ir['camera']['framing'] = dict(text=old_proof, priority='CRITICAL', scope='CURRENT',
                                   source='asset-design/' + 'a' * 64 + '/proof')
    original = original.model_copy(update={'composition': old_proof, 'prompt_ir': ir})
    frame = inherit_design(original, item)
    prompt = compile_frame(frame)['request']['body']['prompt']
    assert old_proof not in prompt
    assert item['design']['proof'] in prompt
    assert inherit_design(frame, item) == frame


def test_unverified_machine_like_source_does_not_erase_an_authored_view():
    item, original = artwork()
    ir = deepcopy(original.prompt_ir)
    ir['camera']['framing']['source'] = 'asset-design/' + '0' * 64 + '/proof'
    original = original.model_copy(update={'prompt_ir': ir})
    result = inherit_design(original, item)
    assert result.prompt_ir['camera']['framing'] == ir['camera']['framing']


@pytest.mark.asyncio
async def test_formal_author_conflict_is_completion_work_not_backend_failure():
    from test_reference_schema_compiler_parity import authored, sample
    item, raw = sample('LOCATION')
    item['design']['proof'] = 'Doorframe at the right edge of the frame'
    raw['composition'] = 'Doorframe at the left edge of the frame'
    raw['prompt_ir']['camera']['framing']['text'] = raw['composition']
    with pytest.raises(DesignCompletionRequired, match='REFERENCE_VIEW_CONFLICT'):
        await authored(item, raw)


@pytest.mark.asyncio
async def test_native_conflict_handoff_returns_reference_author_without_rewriting_assets(tmp_path, monkeypatch):
    from test_target_reference_production import ReferenceAuthor
    from test_asset_sequence import plugin, request_for
    class ConflictingAuthor(ReferenceAuthor):
        async def design_assets(self, request):
            draft = await super().design_assets(request)
            first = draft.assets[0]
            design = {**first.design, 'proof': 'Figure at the left edge of the frame'}
            return draft.model_copy(update={'assets':(first.model_copy(update={'design':design}), *draft.assets[1:])})
        async def design_asset_reference(self, request, item):
            self.reference_requests.append((request,item))
            frame = reference_frame(item)
            ir = deepcopy(frame.prompt_ir)
            ir['camera']['framing']['text'] = 'Figure at the right edge of the frame'
            return frame.model_copy(update={'composition':ir['camera']['framing']['text'], 'prompt_ir':ir})
    author = ConflictingAuthor()
    instance = plugin(tmp_path, monkeypatch, author)
    inputs, _ = request_for(instance, 's-1')
    result = await instance.creative._professional(inputs)
    child = next(r.artifact_ref for r in result.artifact_refs if r.owner=='runtime')
    record = instance.reference_production.get(child)
    assert record.frame is None and record.stage is None
    assert record.required_action.startswith('HOST_COMPLETE_REFERENCE_DESIGN: REFERENCE_VIEW_CONFLICT:')
    assert 'reference-artwork author' in record.required_action
    assert 'design_asset_reference' in record.required_action and 'supply_frame' in record.required_action
    assert 'revise_reference_designs' not in record.required_action
    assert len(author.reference_requests) == 1  # no automatic retry
    item = instance.reference_production.item(record)
    assert item['design']['proof'] == 'Figure at the left edge of the frame'
    await instance.aclose()
