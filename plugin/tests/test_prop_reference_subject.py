"""Independent PROP proof contracts only; no model calls or image evidence."""
from copy import deepcopy
from types import SimpleNamespace
import socket
import subprocess

import pytest
from jsonschema import Draft202012Validator, ValidationError as SchemaError

from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.professional_design.reference_production import TargetReferenceProduction
from drama_plugin.visual.frame_request import (
    compile_frame, prop_reference_bootstrap, prop_reference_subject, verify_compiled)
from test_reference_schema_compiler_parity import sample, authored
from test_visual_first_pass import material


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('No network, subprocess or media generation in contract tests')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)
    monkeypatch.setattr(subprocess, 'Popen', deny)
    monkeypatch.setenv('DRAMA_PLUGIN_ROUTE_IMAGE_MODEL', 'Doubao-Seedream-5.0-pro')


async def proof():
    item, raw = sample('PROP')
    item['stableIdentity'] = 'fictional-prop:hinged-box'
    item['referenceRequired'] = True
    raw['props'] = [dict(entity_key='author-label-not-a-reference',
        state='Closed, resting on its base', geometry='Rectangular box with a single hinge',
        placement='Centre, all edges visible', forbidden=['People', 'Extra boxes'])]
    frame, schema = await authored(item, raw)
    return item, raw, frame, schema


def restamp(frame, **updates):
    value = frame.model_copy(update=updates)
    ir = deepcopy(value.prompt_ir)
    ir['source_fingerprint'] = fp(value.model_dump(mode='json', exclude={'prompt_ir'}))
    return value.model_copy(update={'prompt_ir': ir})


@pytest.mark.asyncio
async def test_formal_prop_subject_is_source_bound_without_deleting_or_omitting_it():
    item, raw, frame, schema = await proof()
    Draft202012Validator(schema).validate(raw)
    assert schema['properties']['props']['maxItems'] == 1
    assert frame.props[0].entity_key == item['stableIdentity']
    assert frame.identity_bootstrap == prop_reference_bootstrap(item['stableIdentity'], item['designRef']['fingerprint'])
    assert prop_reference_subject(frame) == item['stableIdentity']
    assert frame.omitted == raw.get('omitted', {}) and not frame.references and not frame.reference_lock
    for key in ('state', 'geometry', 'placement', 'forbidden'):
        assert getattr(frame.props[0], key) == (tuple(raw['props'][0][key]) if key == 'forbidden' else raw['props'][0][key])
    compiled = compile_frame(frame); verify_compiled(compiled)
    assert 'image' not in compiled['request']['body']
    assert frame.identity_bootstrap not in compiled['request']['body']['prompt']
    assert not any(r.startswith('OMITTED_PROP:') for r in compiled['risks'])
    owner = SimpleNamespace(item=lambda value: item)
    TargetReferenceProduction.validate_frame(owner, SimpleNamespace(requirement_key=item['designRef']['fingerprint']), frame)


@pytest.mark.asyncio
@pytest.mark.parametrize('bootstrap', [None, 'An arbitrary bootstrap is not a PROP reference exemption'])
async def test_plain_bootstrap_does_not_account_for_unreferenced_prop(bootstrap):
    _, _, frame, _ = await proof()
    with pytest.raises(ValueError, match='FOCAL_PROP_REFERENCE_UNACCOUNTED_FOR'):
        compile_frame(restamp(frame, identity_bootstrap=bootstrap))


@pytest.mark.asyncio
@pytest.mark.parametrize('change', ['shot', 'fingerprint', 'subject', 'empty', 'duplicate', 'marker', 'actor', 'task'])
async def test_partial_or_inconsistent_subject_binding_cannot_open_reference_checks(change):
    _, _, frame, _ = await proof()
    updates = {}
    if change == 'shot': updates['shot_id'] = 'ordinary-shot'
    if change == 'fingerprint': updates['shot_fingerprint'] = 'b' * 64
    if change == 'subject': updates['props'] = (frame.props[0].model_copy(update={'entity_key': 'another-prop'}),)
    if change == 'empty': updates['props'] = ()
    if change == 'duplicate': updates['props'] = frame.props * 2
    if change == 'marker': updates['identity_bootstrap'] = frame.identity_bootstrap.split(' for ')[0]
    if change in {'actor', 'task'}:
        ir = deepcopy(frame.prompt_ir)
        if change == 'actor': ir['subjects'] = [{'id': 'not-a-prop'}]
        else: ir['task']['task_type'] = 'REFERENCE_EDIT'
        updates['prompt_ir'] = ir
    with pytest.raises(ValueError, match='REFERENCE_PROP_SUBJECT_BINDING_MISMATCH'):
        compile_frame(restamp(frame, **updates))


@pytest.mark.asyncio
async def test_additional_unbound_prop_still_needs_its_own_reference_accounting():
    _, _, frame, _ = await proof()
    other = frame.props[0].model_copy(update={'entity_key': 'another-prop'})
    with pytest.raises(ValueError, match='FOCAL_PROP_REFERENCE_UNACCOUNTED_FOR'):
        compile_frame(restamp(frame, props=(*frame.props, other)))


@pytest.mark.asyncio
async def test_prop_bootstrap_cannot_be_used_for_image_conditioning_or_missing_primary():
    _, _, frame, _ = await proof()
    with pytest.raises(ValueError, match='REFERENCE_PROP_SUBJECT_BINDING_MISMATCH'):
        prop_reference_subject(frame.model_copy(update={'image_mode': 'image_to_image'}))
    with pytest.raises(ValueError, match='REFERENCE_PROP_SUBJECT_BINDING_MISMATCH'):
        prop_reference_subject(frame.model_copy(update={'reference_lock': {'invented': 'a' * 64}}))


@pytest.mark.asyncio
async def test_ambiguous_author_subjects_are_rejected_instead_of_guessing_or_deleting():
    item, raw, _, schema = await proof()
    raw['props'].append({**raw['props'][0], 'entity_key': 'other-author-label'})
    with pytest.raises(SchemaError): Draft202012Validator(schema).validate(raw)
    from drama_plugin.creative_engine.diagnostics import AuthorResultFailure
    with pytest.raises(AuthorResultFailure): await authored(item, raw)


@pytest.mark.asyncio
@pytest.mark.parametrize('change', ['type', 'identity', 'design'])
async def test_native_owner_compares_binding_to_exact_selected_original(change):
    item, _, frame, _ = await proof()
    invalid = deepcopy(item)
    if change == 'type': invalid['assetType'] = 'LOCATION'
    elif change == 'identity': invalid['stableIdentity'] = 'different-selected-prop'
    else: invalid['designRef']['fingerprint'] = 'b' * 64
    owner = SimpleNamespace(item=lambda value: invalid)
    with pytest.raises(ValueError, match='REFERENCE_FRAME_.*MISMATCH'):
        TargetReferenceProduction.validate_frame(owner, SimpleNamespace(requirement_key=frame.shot_fingerprint), frame)


@pytest.mark.parametrize('change, error', [
    ('missing', 'FOCAL_PROP_REFERENCE_UNACCOUNTED_FOR'),
    ('kind', 'FOCAL_PROP_BOUND_TO_WRONG_REFERENCE_KIND'),
    ('state', 'PROP_REFERENCE_STATE_CONFLICT'),
    ('hash', 'REFERENCE_LOCAL_HASH_MISMATCH'),
    ('lock', 'REFERENCE_VERSION_NOT_LOCKED'),
])
def test_ordinary_shot_prop_reference_checks_remain_active(tmp_path, change, error):
    frame, template = material(tmp_path)
    refs = list(frame.references)
    if change == 'missing':
        frame = frame.model_copy(update={'props': (frame.props[0].model_copy(update={'entity_key': 'unbound-prop'}),)})
    elif change == 'kind': refs[-1] = refs[-1].model_copy(update={'kind': 'CHARACTER'})
    elif change == 'state': frame = frame.model_copy(update={'props': (frame.props[0].model_copy(update={'state': 'Changed'}),)})
    elif change == 'hash': refs[-1] = refs[-1].model_copy(update={'content_hash': 'b' * 64})
    elif change == 'lock': frame = frame.model_copy(update={'reference_lock': {}})
    if change == 'hash':
        locks = dict(frame.reference_lock); ref = refs[-1]
        locks[f'{ref.asset_id}/{ref.media_id}/{ref.version}'] = ref.content_hash
        frame = frame.model_copy(update={'reference_lock': locks})
    if change != 'missing': frame = frame.model_copy(update={'references': tuple(refs)})
    with pytest.raises(ValueError, match=error): compile_frame(frame, template)


def test_ordinary_selected_prop_and_state_delta_still_compile(tmp_path):
    frame, template = material(tmp_path)
    verify_compiled(compile_frame(frame, template))
    props = (frame.props[0].model_copy(update={'state': 'Changed', 'reference_delta': 'Approved opening state'}),)
    compiled = compile_frame(frame.model_copy(update={'props': props}), template)
    assert any(r.startswith('STATE_TRANSITION:') for r in compiled['risks'])
