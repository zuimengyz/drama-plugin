"""Fictional contract examples only, never real-author or image-effect evidence.

The transport is an in-memory fixture. The author projection, FrameSpec validator,
image compiler and Ark body serializer are the existing implementation under test.
No old recorded business response is repaired or used as a passing sample here.
"""
from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess

import httpx
from jsonschema import Draft202012Validator, ValidationError as SchemaError
import pytest

from drama_plugin.config.text_composition import TextCompositionConfig
from drama_plugin.creative_engine.backends import FormalProfessionalAuthor, TextCompositionBackend
from drama_plugin.creative_engine.contracts import AuthorRequest
from drama_plugin.creative_engine.diagnostics import AuthorResultFailure
from drama_plugin.runtime.contracts import RuntimeScope
from drama_plugin.visual.frame_request import compile_frame
from test_formal_author_backends import canon, source
from test_visual_prompt_ir import fact
from test_work_aesthetic_delivery import PALETTES, PROOF_LOOKS, semantic_art


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('No network, subprocess, model or media call is authorized')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)
    monkeypatch.setattr(subprocess, 'Popen', deny)
    monkeypatch.setenv('DRAMA_PLUGIN_ROUTE_IMAGE_MODEL', 'Doubao-Seedream-5.0-pro')


def sample(kind):
    """Reuse the existing fictional asset-delivery examples, not this film."""
    stable = {
        'CHARACTER': {'face': 'Long face with an asymmetric left brow'},
        'LOCATION': {'architecture': 'Two bays with a fixed left doorway'},
        'PROP': {'construction': 'Rectangular box with a single hinge'},
    }[kind]
    item = dict(assetType=kind, name={'CHARACTER': 'A', 'LOCATION': 'Workshop', 'PROP': 'Box'}[kind],
        subjectId='fictional-A' if kind == 'CHARACTER' else None,
        designRef=dict(key='fictional-selected-proof', kind='DIRECTION', fingerprint='a' * 64),
        design={**stable, 'material': PROOF_LOOKS['restrained'][kind]},
        variantReason='Fictional contract exercise only.')
    raw = semantic_art(item, PALETTES['restrained'])
    if kind == 'CHARACTER':
        item['design']['costume'] = raw['prompt_ir']['subjects'][0]['costume']['text']
    item['design'].update(proof=raw['prompt_ir']['camera']['framing']['text'],
        referenceLighting={key: value['text'] for key, value in raw['prompt_ir']['lighting'].items()})
    if kind != 'CHARACTER':
        # Unoccupied location/object artwork must not need a dummy person or
        # human state simply to satisfy a general FrameSpec schema.
        raw.pop('actors')
        for key in ('subjects', 'blocking', 'action'):
            raw['prompt_ir'].pop(key, None)
    return item, raw


async def authored(item, raw):
    observed = []
    before = deepcopy(raw)

    def receive(request):
        wire = json.loads(request.content)
        knowledge = Path(__file__).resolve().parents[1] / 'skills/specialized-asset-design/references/relational-aesthetics.md'
        assert knowledge.read_text() in wire['messages'][0]['content']
        schema = json.loads(wire['messages'][0]['content'].split('\nOutput JSON schema:\n')[-1])
        observed.append(schema)
        # The fixture is deliberately not validated here: negative tests must
        # also exercise the existing formal projection, not a mock validator.
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
            'role': 'assistant', 'content': json.dumps(raw)}}]})

    cfg = TextCompositionConfig(provider='offline', base_url='https://author.invalid/v1',
        api_key='offline-secret', professional_model='offline-professional-model')
    author = FormalProfessionalAuthor(TextCompositionBackend(cfg, transport=httpx.MockTransport(receive)),
        Path(__file__).resolve().parents[1] / 'skills')
    request = AuthorRequest(scope=RuntimeScope(work_id='fictional-parity', scene_id='scene'),
        source=source(), source_refs=(), canon=canon())
    result = await author.design_asset_reference(request, item)
    assert len(observed) == 1 and raw == before
    return result, observed[0]


def serialized(frame):
    compiled = compile_frame(frame)
    request = json.loads(json.dumps(compiled['request'], ensure_ascii=False))
    assert request['body']['prompt'] == compiled['prompt_ir_compilation']['prompt']
    assert request['body']['prompt']
    return request['body'], compiled


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['CHARACTER', 'LOCATION', 'PROP'])
async def test_formal_projection_to_ark_body_keeps_selected_relationships(kind):
    item, raw = sample(kind)
    frame, schema = await authored(item, raw)
    Draft202012Validator(schema).validate(raw)
    body, compiled = serialized(frame)
    selected = item['design']
    for text in [selected['material'], selected['proof'], *selected['referenceLighting'].values(),
                 PALETTES['restrained']]:
        assert text in body['prompt']
    if kind == 'CHARACTER':
        assert frame.actors[0].entity_key == item['subjectId']
        assert frame.prompt_ir['subjects'][0]['id'] == item['subjectId']
        assert selected['face'] in body['prompt']
        assert frame.actors[0].costume == selected['costume']
        assert selected['costume'] in body['prompt']
    else:
        assert not frame.actors and not frame.prompt_ir['subjects']
        assert frame.prompt_ir['blocking'] is None and frame.prompt_ir['action'] is None
        for key in ('actors',):
            assert key not in schema['required']
            assert schema['properties'][key]['maxItems'] == 0
        ir_schema = schema['properties']['prompt_ir']
        assert not {'subjects', 'blocking', 'action'} & set(ir_schema['required'])
        assert ir_schema['properties']['subjects']['maxItems'] == 0
        assert selected.get('architecture', selected.get('construction')) in body['prompt']
    assert any(row['text'] == PALETTES['restrained'] and row['path'].startswith('preserve[')
               for row in compiled['prompt_ir_compilation']['retained'])
    assert frame.prompt_ir['lighting']['realism']['priority'] == 'CRITICAL'  # selected exact leaf
    assert frame.prompt_ir['camera']['shot_size']['priority'] == 'IMPORTANT'  # author not promoted


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['LOCATION', 'PROP'])
@pytest.mark.parametrize('field', ['actors', 'subjects'])
async def test_unoccupied_asset_rejects_invented_person_in_schema_and_projection(kind, field):
    item, raw = sample(kind)
    _, schema = await authored(item, raw)
    _, person = sample('CHARACTER')
    if field == 'actors':
        raw['actors'] = person['actors']
    else:
        raw['prompt_ir']['subjects'] = person['prompt_ir']['subjects']
        raw['prompt_ir']['blocking'] = person['prompt_ir']['blocking']
        raw['prompt_ir']['action'] = person['prompt_ir']['action']
    with pytest.raises(SchemaError):
        Draft202012Validator(schema).validate(raw)
    # The existing safe backend wraps projection ValueError; it must still
    # reject the invalid result without filling or deleting a person.
    with pytest.raises(AuthorResultFailure) as rejected:
        await authored(item, raw)
    assert rejected.value.diagnostic.exception_type == 'ValueError'


@pytest.mark.asyncio
@pytest.mark.parametrize('constraint,target', [
    ('CRITICAL', 'CRITICAL'), ('IMPORTANT', 'IMPORTANT'),
    ('SECONDARY', 'SECONDARY'), ('SECONDARY', 'IMPORTANT'),
])
async def test_current_negative_preserves_its_existing_priority(constraint, target):
    item, raw = sample('LOCATION')
    raw['prompt_ir']['negative_constraints'] = [dict(
        constraint=fact('No captions', constraint),
        positive_target=fact('An image without captions', target))]
    frame, schema = await authored(item, raw)
    Draft202012Validator(schema).validate(raw)
    body, compiled = serialized(frame)
    negative = frame.prompt_ir['negative_constraints'][0]
    assert negative['constraint']['priority'] == constraint
    assert negative['positive_target']['priority'] == target
    assert 'No captions' in body['prompt'] and 'An image without captions' in body['prompt']
    rows = {r['path']: r for r in compiled['prompt_ir_compilation']['retained']}
    assert rows['constraint[0]']['priority'] == constraint
    assert rows['positive_target[0]']['priority'] == target


@pytest.mark.asyncio
@pytest.mark.parametrize('defect', ['constraint_scope', 'target_scope', 'priority_loss'])
async def test_invalid_negative_is_rejected_by_author_schema_and_compiler(defect):
    item, raw = sample('LOCATION')
    raw['prompt_ir']['negative_constraints'] = [dict(
        constraint=fact('No captions', 'IMPORTANT'),
        positive_target=fact('An image without captions', 'IMPORTANT'))]
    frame, schema = await authored(item, raw)
    invalid_raw = deepcopy(raw)
    ir = deepcopy(frame.prompt_ir)
    for negative in (invalid_raw['prompt_ir']['negative_constraints'][0], ir['negative_constraints'][0]):
        if defect == 'constraint_scope':
            negative['constraint']['scope'] = 'CAPABILITY'
        elif defect == 'target_scope':
            negative['positive_target']['scope'] = 'FUTURE'
        else:
            negative['positive_target']['priority'] = 'SECONDARY'
    with pytest.raises(SchemaError):
        Draft202012Validator(schema).validate(invalid_raw)
    with pytest.raises(ValueError, match='NEGATIVE_NOT_CURRENT|NEGATIVE_PRIORITY_LOSS|REQUIRED_FIELD_NOT_EXECUTABLE'):
        compile_frame(frame.model_copy(update={'prompt_ir': ir}))


@pytest.mark.asyncio
async def test_noncurrent_knowledge_is_retained_as_source_not_in_final_image_body():
    item, raw = sample('CHARACTER')
    capability = fact('Fixture capability retained for a later operation', scope='CAPABILITY')
    future = fact('Fixture optional detail for a future scene', 'SECONDARY', 'FUTURE')
    raw['prompt_ir']['action']['non_current'] = [capability]
    raw['prompt_ir']['secondary_details'] = [future]
    frame, schema = await authored(item, raw)
    Draft202012Validator(schema).validate(raw)
    body, compiled = serialized(frame)
    assert frame.prompt_ir['action']['non_current'] == [capability]
    assert frame.prompt_ir['secondary_details'] == [future]
    assert capability['text'] not in body['prompt'] and future['text'] not in body['prompt']
    assert {row['reason'] for row in compiled['prompt_ir_compilation']['omitted']} >= {
        'NON_CURRENT_SOURCE_ONLY', 'FUTURE'}


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['CHARACTER', 'LOCATION', 'PROP'])
async def test_internal_reference_notes_do_not_erase_current_visible_limits(kind):
    item, raw = sample(kind)
    internal = ('The object department owns the coffin design; the temporary reference '
        'illumination is not an instruction for a later scene.')
    visible = ('No additional person or coffin appears in this current proof; '
        'only the selected asset and its unobscured structure are pictured.')
    raw['omitted'] = {'reference applicability and department responsibility': internal}
    raw['prompt_ir']['world']['environment_rules'].append(fact(visible))
    frame, schema = await authored(item, raw)
    Draft202012Validator(schema).validate(raw)
    body, compiled = serialized(frame)
    # This is a fictional, correctly separated handoff through real projection
    # and compilation, not a claim that old mixed prose was repaired or that a
    # model obeyed the new author instructions.
    assert frame.omitted == raw['omitted']
    assert internal not in body['prompt']
    assert visible in body['prompt']
    row = next(r for r in compiled['prompt_ir_compilation']['retained'] if r['text'] == visible)
    assert row['path'].startswith('world.environment_rules[')
    assert row['priority'] == 'CRITICAL'
    assert next(f for f in frame.prompt_ir['world']['environment_rules']
        if f['text'] == visible)['scope'] == 'CURRENT'


@pytest.mark.asyncio
@pytest.mark.parametrize('group,key,attribute,value', [
    ('world', 'era', 'priority', 'IMPORTANT'),
    ('blocking', 'positions', 'scope', 'CAPABILITY'),
    ('environment', 'topology', 'priority', 'SECONDARY'),
    ('lighting', 'realism', 'scope', 'FUTURE'),
])
async def test_executable_minimum_and_scope_match_existing_compiler(group, key, attribute, value):
    item, raw = sample('CHARACTER')
    frame, schema = await authored(item, raw)
    invalid_raw = deepcopy(raw)
    invalid_raw['prompt_ir'][group][key][attribute] = value
    ir = deepcopy(frame.prompt_ir)
    ir[group][key][attribute] = value
    with pytest.raises(SchemaError):
        Draft202012Validator(schema).validate(invalid_raw)
    with pytest.raises(ValueError, match='PRIORITY_TOO_LOW|REQUIRED_FIELD_NOT_EXECUTABLE'):
        compile_frame(frame.model_copy(update={'prompt_ir': ir}))
