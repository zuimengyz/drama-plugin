"""Offline behavior tests, not evidence of model creativity or rendered quality."""
from copy import deepcopy
import json
import pytest
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.professional_design.reference_design import inherit_design, verify_design_delivery
from drama_plugin.visual.frame_request import FrameSpec, compile_frame, verify_compiled
from drama_plugin.visual.prompt_ir import require_submission_ir
from drama_plugin.visual.production import Review, Finding
from test_target_reference_production import (prepared, reference_frame, quote_and_approve,
    fake_submission, fake_persistence)


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    import socket
    def deny(*args, **kwargs):
        raise AssertionError('Offline regression cannot contact a service or model')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)


LIGHT = dict(time_of_day='Overcast morning', light_sources='One small side window; stove is local',
    contrast='Bench bright, far bed dim; readable lower work area', realism='Weak bounce from worn dark boards')


@pytest.mark.asyncio
async def test_change_only_design_native_reentry_inherits_all_facts(tmp_path, monkeypatch):
    p, inp, child, prior, author = await prepared(tmp_path, monkeypatch)
    old = deepcopy(prior.frame)
    design = dict(face='An older round face with a short chin', costume='Soft worn collar and one elbow repair',
        material='Dull woven linen with local wear', proof='Complete ordinary standing figure',
        referenceLighting=LIGHT, sourceBoundary='INTERNAL_NOT_FOR_IMAGE')
    # User edits only the original, not FrameSpec, IR, compiler or wire.
    following = await p.tools.invoke('specialized_assets.revise_reference_designs',
        preparation_ref=prior.preparation_ref, designs={prior.requirement_key: design})
    assert following != prior.preparation_ref
    result = await p.reference_production.pending(following, inp.run_id, author.reference_requests[0][0])
    new_child = next(r.artifact_ref for r in result.artifact_refs if r.owner == 'runtime')
    current = p.reference_production.get(new_child)
    item = p.reference_production.item(current)
    wire = json.loads(json.dumps(current.frame['request']['body']))
    for fact in [design[k] for k in ('face','costume','material','proof')] + list(LIGHT.values()):
        assert fact in wire['prompt']
    assert 'INTERNAL_NOT_FOR_IMAGE' not in wire['prompt']
    assert 'Approved worn wool' not in wire['prompt']
    assert 'Broad window source' not in wire['prompt']
    assert current.quote is None and current.cost_ref is None and current.stage is None
    assert new_child != child and p.reference_production.get(child).frame == old
    verify_compiled(current.frame); require_submission_ir(current.frame, current.frame['request'])
    verify_design_delivery(current.frame, item)
    with pytest.raises(ValueError, match='PREPARATION_AUTHORITY_MISMATCH'):
        await p.reference_production.revise_designs(prior.preparation_ref,{prior.requirement_key:design})
    await p.aclose()


@pytest.mark.asyncio
async def test_manual_supply_cannot_replace_design_and_sealed_history_does_not_change(tmp_path, monkeypatch):
    p, inp, child, value, author = await prepared(tmp_path, monkeypatch)
    item = p.reference_production.item(value)
    spec = reference_frame(item)
    # Replaying raw old artwork cannot overwrite the sealed, inherited result.
    with pytest.raises(ValueError, match='ALREADY_SEALED'):
        await p.reference_production.supply_frame(child,spec)
    assert await p.reference_production.supply_frame(child,FrameSpec.model_validate(value.frame['spec'])) == value
    # A self-consistent generic compilation still fails selected-design delivery.
    with pytest.raises(ValueError,match='NOT_DELIVERED'):
        verify_design_delivery(compile_frame(spec),item)
    await p.aclose()


@pytest.mark.asyncio
async def test_revision_does_not_interrupt_reserved_spend(tmp_path, monkeypatch):
    p, inp, child, prior, author = await prepared(tmp_path, monkeypatch)
    await quote_and_approve(p,child)
    from drama_plugin.runtime.contracts import CapabilityInput
    await p.reference_production.reserve(CapabilityInput(run_id=child,scope=prior.scope,operation_id='reserve-only'))
    with pytest.raises(ValueError,match='IN_FLIGHT'):
        await p.reference_production.revise_designs(prior.preparation_ref,{prior.requirement_key:{'face':'Different face'}})
    assert p.reference_production.item(p.reference_production.get(child))['requirementKey']==prior.requirement_key
    await p.aclose()


@pytest.mark.asyncio
async def test_rejected_output_revision_retains_media_and_does_not_submit(tmp_path, monkeypatch):
    p, inp, child, prior, author = await prepared(tmp_path, monkeypatch)
    calls=[];fake_submission(monkeypatch,calls);fake_persistence(monkeypatch,p)
    await quote_and_approve(p,child)
    await p.reference_production.resume(child)
    value=p.reference_production.get(child);attempt=value.stage['attempts'][0]
    await p.reference_production.review_reference(child,Review(attempt_id=attempt['attempt_id'],
        output_hash=attempt['output_hash'],reviewer='OFFLINE_TEST',evidence='Synthetic rejection state',
        checks={'IDENTITY':'FAIL'},findings=(Finding(category='IDENTITY',severity='MAJOR',
        evidence='Synthetic rejection, no rendered evaluation',remedy='REGENERATE'),)))
    rejected=p.reference_production.get(child)
    following=await p.reference_production.revise_designs(prior.preparation_ref,
        {prior.requirement_key:{'face':'A revised individual face','costume':'A patched linen shirt'}})
    result=await p.reference_production.pending(following,inp.run_id,author.reference_requests[0][0])
    current=p.reference_production.get(next(r.artifact_ref for r in result.artifact_refs if r.owner=='runtime'))
    assert p.reference_production.get(child)==rejected and current.stage is None
    assert len(calls)==1 and not await p.providers.asset.list_assets()
    await p.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize('unfinished,issue', [
    ({'face':'Same face','unmappedLook':'Important shape'}, 'UNMAPPED_FIELD:unmappedLook'),
    ({'face':'Same face','referenceLighting':{'contrast':'Local light'}}, 'LIGHTING_FIELDS_REQUIRED'),
    ({'face':'Same face','identity':'Other face'}, 'AMBIGUOUS_FIELDS'),
    ({'rationale':'Reason without a visible design'}, 'VISIBLE_FACTS_REQUIRED'),
])
async def test_host_completes_original_and_parent_reentry_compiles(tmp_path, monkeypatch, unfinished, issue):
    from drama_plugin.runtime.contracts import RuntimeState, ResultStatus, RecoveryClass
    p, inp, child, prior, author = await prepared(tmp_path, monkeypatch)
    original = deepcopy(prior.frame)
    pending = await p.tools.invoke('specialized_assets.revise_reference_designs',
        preparation_ref=prior.preparation_ref, designs={prior.requirement_key:unfinished})
    calls = len(author.reference_requests)
    result = await p.creative._professional(inp)
    current_id = next(r.artifact_ref for r in result.artifact_refs if r.owner=='runtime')
    current = p.reference_production.get(current_id)
    run = p.runtime.store.load(current_id)
    assert run.state == RuntimeState.WAITING_EXTERNAL
    assert run.last_result.status == ResultStatus.WAITING_EXTERNAL
    assert run.last_result.recovery_class == RecoveryClass.WAIT_EXTERNAL
    assert run.last_result.user_decision is None
    assert current.required_action.startswith('HOST_COMPLETE_REFERENCE_DESIGN:')
    assert issue in current.required_action and current.frame is None
    assert len(author.reference_requests) == calls  # no wasted reference author call
    assert current.stage is None and current.cost_ref is None
    # This step represents Host authorship, not an autonomous model creativity test.
    # The Host supplies only a completed original, never an IR or Prompt patch.
    completed = {'face':'Same face','costume':'A worn linen collar',
                 'geometry':'Individual broad cheekbones', 'referenceLighting':LIGHT}
    updated = await p.tools.invoke('specialized_assets.revise_reference_designs',
        preparation_ref=pending, designs={current.requirement_key:completed})
    result = await p.creative._professional(inp)  # same parent professional entry
    following = p.reference_production.get(next(r.artifact_ref for r in result.artifact_refs if r.owner=='runtime'))
    assert following.preparation_ref == updated
    assert following.required_action == 'CURRENT_REFERENCE_QUOTE_REQUIRED'
    assert following.frame and following.stage is None
    assert all(text in following.frame['request']['body']['prompt']
               for text in [completed['face'],completed['costume'],completed['geometry'],*LIGHT.values()])
    assert p.reference_production.get(child).frame == original
    await p.aclose()


@pytest.mark.asyncio
async def test_incomplete_initial_design_remains_host_work_not_failed_run(tmp_path, monkeypatch):
    from test_target_reference_production import ReferenceAuthor
    from test_asset_sequence import plugin, request_for
    from drama_plugin.runtime.contracts import RuntimeState
    author = ReferenceAuthor()
    design_assets = author.design_assets
    async def incomplete(request):
        draft = await design_assets(request)
        first = draft.assets[0].model_copy(update={'design':{'face':'Same face', 'referenceLighting':{'contrast':'Dim'}}})
        return draft.model_copy(update={'assets':(first, *draft.assets[1:])})
    author.design_assets = incomplete
    p = plugin(tmp_path,monkeypatch,author)
    inp, _ = request_for(p,'s-1')
    result = await p.creative._professional(inp)
    child = next(r.artifact_ref for r in result.artifact_refs if r.owner=='runtime')
    value = p.reference_production.get(child)
    assert p.runtime.store.load(child).state == RuntimeState.WAITING_EXTERNAL
    assert 'HOST_COMPLETE_REFERENCE_DESIGN' in value.required_action
    assert not author.reference_requests and value.frame is None
    assert p.reference_production.item(value)['design']['referenceLighting']=={'contrast':'Dim'}
    await p.aclose()


@pytest.mark.asyncio
async def test_location_and_prop_are_not_a_character_template(tmp_path,monkeypatch):
    p, inp, child, value, author=await prepared(tmp_path,monkeypatch)
    item=p.reference_production.item(value)
    for kind,design in [('LOCATION',dict(architecture='Old single room',topology='Door opposite a shared bed',
        workArea='Scarred bench with clear foot space',material='Worn paths and stove-local ash',
        proof='Room view showing entrance and bench',referenceLighting=LIGHT)),
        ('PROP',dict(construction='Wood body with inclined iron and separate wedge',
        materials='Worn wood with a maintained steel edge',proof='Static side view with one detached shaving'))]:
        selected={**item,'assetType':kind,'subjectId':None,'design':design,
            'designRef':{**item['designRef'],'fingerprint':fp(design)}}
        compiled=compile_frame(inherit_design(reference_frame(selected),selected))
        verify_design_delivery(compiled,selected)
        assert 'SUBJECTS' not in compiled['request']['body']['prompt']
        assert 'INTERNAL' not in compiled['request']['body']['prompt']
    await p.aclose()


def test_reference_edit_keeps_selected_design_after_edit_serializer():
    # No image reading: test the actual IR edit serializer in isolation.
    from test_visual_prompt_ir import visual_ir, fact
    from drama_plugin.visual.prompt_ir import compile_ir
    raw=visual_ir('TEXT_TO_IMAGE','ark')
    from drama_plugin.visual.frame_request import Actor
    spec=FrameSpec(shot_id='a',shot_fingerprint='a'*64,entry_state='Standing',composition='Single person',
        environment='Neutral',actors=(Actor(entity_key=raw['subjects'][0]['id'],label='A',identity='A',costume='A',
        position='Centre',pose='Standing',action='Standing',gaze='Front'),),required=('Face',),forbidden=('Extra people',),
        references=(),reference_lock={},
        identity_bootstrap='Design proof',shot_type='SINGLE_STATIC',target_size=(1536,2560),seed=1)
    raw['source_fingerprint']=fp(spec.model_dump(mode='json',exclude={'prompt_ir'}))
    item={'assetType':'CHARACTER','subjectId':raw['subjects'][0]['id'],'designRef':{'fingerprint':'b'*64},
        'design':{'face':'Selected face','hair':'Short grey hair','proof':'Three-quarter full figure','referenceLighting':LIGHT}}
    inherited=inherit_design(spec.model_copy(update={'prompt_ir':raw}),item).prompt_ir
    inherited['task'].update(task_type='REFERENCE_EDIT',input_mode='reference')
    inherited['edit_delta']=[dict(operation='replace',region='shirt',source_issue=fact('White shirt'),target_correction=fact('Patched shirt'))]
    inherited['preserve']=[fact('Keep the remaining source image')]
    out=compile_ir(inherited,provider_family='ark')
    verify_design_delivery({'prompt_ir_compilation':out,'request':{'body':{'prompt':out['prompt']}}},item)
    assert all(v in out['prompt'] for v in LIGHT.values())


@pytest.mark.asyncio
async def test_missing_wire_facts_are_filled_before_quote_without_prompt_edit(tmp_path, monkeypatch):
    from test_target_reference_production import evidence
    from drama_plugin.providers.ark_image import binding
    p, inp, child, value, author = await prepared(tmp_path, monkeypatch)
    item = p.reference_production.item(value)
    # Retain a valid pre-inheritance request to exercise upgrade of unapproved work.
    generic = compile_frame(reference_frame(item))
    legacy = p.reference_production.save(value, frame=generic)
    old_ref = legacy.artifact_reference()
    calls = len(author.reference_requests)
    current = await p.tools.invoke('specialized_assets.quote_reference', run_id=child,
        quote={'request_fingerprint':fp(generic['request'])}, balance={}, budget=1,
        execution_binding=binding(generic,evidence()))
    assert current.frame != generic and current.required_action == 'CURRENT_REFERENCE_QUOTE_REQUIRED'
    verify_design_delivery(current.frame,item)
    assert current.quote is None and current.stage is None
    assert len(author.reference_requests) == calls  # deterministic repair, no model
    retained, _, _ = p.ledger.get_artifact('asset-reference-production',old_ref)
    assert retained['frame'] == generic  # prior evidence immutable
    await quote_and_approve(p,child)  # normal request-bound spending path still works
    assert p.reference_production.get(child).frame == current.frame
    await p.aclose()


@pytest.mark.asyncio
async def test_formal_author_loads_full_methods_and_cannot_override_selected_facts(tmp_path,monkeypatch):
    from pathlib import Path
    import httpx
    from test_formal_author_backends import configured
    from test_work_aesthetic_delivery import semantic_art, wire_response
    formal = configured(monkeypatch,tmp_path/'formal')
    author = formal.professional_design.author
    p, inp, child, value, fixture = await prepared(tmp_path/'sequence',monkeypatch)
    item = p.reference_production.item(value)
    item = {**item, 'design':{'face':'Individual broad forehead and short chin',
        'costume':'An unbleached patched shirt', 'material':'Matte woven linen', 'referenceLighting':LIGHT}}
    request = fixture.reference_requests[0][0]
    skills = Path(__file__).parents[1]/'skills'
    loaded = []
    def receive(wire):
        data = json.loads(wire.content)
        system = data['messages'][0]['content']
        # Whole on-disk methods must be in the real formal author's outgoing call.
        assert (skills/'specialized-asset-design/SKILL.md').read_text() in system
        payload = json.loads(data['messages'][1]['content'])
        if 'selectedAssetReference' not in payload:
            assert (skills/'asset-resolution/SKILL.md').read_text() in system
            loaded.append('design')
            return wire_response({'assets':[{'assetType':'CHARACTER','name':'A',
                'subjectSelection':0,'design':item['design']}], 'rationale':'Offline authored fixture'})
        loaded.append('reference')
        raw = semantic_art(item,'Generic smooth material')
        raw['prompt_ir']['subjects'][0]['face']['text'] = 'Generic face from artist'
        raw['actors'][0]['identity'] = 'Generic face from artist'
        return wire_response(raw)
    author.client.transport = httpx.MockTransport(receive)
    draft = await author.design_assets(request)
    assert draft.assets[0].design == item['design']
    spec = FrameSpec.model_validate(await author.design_asset_reference(request,item))
    compiled = compile_frame(spec)
    verify_design_delivery(compiled,item)
    assert loaded == ['design','reference']
    assert 'Generic face from artist' not in compiled['request']['body']['prompt']
    assert 'Broad window source' not in compiled['request']['body']['prompt']
    await p.aclose(); await formal.aclose()
