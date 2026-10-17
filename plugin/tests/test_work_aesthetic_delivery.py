"""Offline contract/delivery evidence, not model creativity or image quality."""
from copy import deepcopy
import json
import os
from pathlib import Path
import socket

import httpx
import pytest

from drama_plugin.contracts.base import dump_contract
from drama_plugin.creative_engine.contracts import AuthorRequest, Authority, CreativeCheckpoint, Kind
from drama_plugin.creative_engine.author_projection import author_payload
from drama_plugin.professional_design.asset_sequence import AssetPreparationPending
from drama_plugin.production.contracts import SourceDomain
from drama_plugin.runtime.contracts import CapabilityInput, RunMode
from drama_plugin.visual.frame_request import FrameSpec, compile_frame
from test_formal_author_backends import configured, canon, source, shot, response
from test_professional_continuity import look, selected
from test_target_reference_production import reference_frame
from test_visual_prompt_ir import fact
from test_asset_sequence import plugin as sequence_plugin, request_for
from test_event_scope_delivery import material, pipeline

PALETTES = {
    'restrained': 'Slate cloth, pale ash wood, matte iron; distinct neutral skin',
    'celebratory': 'Vermilion cloth, golden wood, polished brass; distinct neutral skin',
}

PROOF_LOOKS = {
    'restrained': {'CHARACTER':'Slate cloth beside distinct neutral skin',
        'LOCATION':'Pale ash wood supports matte iron fittings',
        'PROP':'Matte iron hinges contrast with pale ash wood'},
    'celebratory': {'CHARACTER':'Vermilion cloth beside distinct neutral skin',
        'LOCATION':'Golden wood supports polished brass fittings',
        'PROP':'Polished brass hinges contrast with golden wood'},
}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('No service or media calls are authorized')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)


def evidence(name, value):
    if root := os.environ.get('AESTHETIC_EVIDENCE_DIR'):
        folder = Path(root); folder.mkdir(parents=True, exist_ok=True)
        (folder / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2))


def work_look(work, palette):
    value = dump_contract(look(work))
    value['grammarRules'][0].update(execution=palette, narrativeReason='FICTIONAL_WORK_REASON',
        appliesWhen='Public workroom', exception='Window light changes surface appearance',
        exitCondition='Leave the workroom')
    value['evolution'][0].update(realization='A side view reveals the unchanged object', scopeId='s-1')
    return value


def wire_response(value):
    return httpx.Response(200, json={'choices':[{'finish_reason':'stop','message':{
        'role':'assistant','content':json.dumps(value)}}]})


@pytest.mark.asyncio
async def test_selected_scene_direction_loads_work_method_without_canon_injection(monkeypatch, tmp_path):
    p = configured(monkeypatch, tmp_path)
    work = 'offline-r3-capability'; h = await selected(p, work)
    original = p.screenplays.objects.read_ref(h)
    pin = p.screenplays.objects.put('look', work_look(work, PALETTES['celebratory']))
    bound = await p.tools.invoke('screenplay.bind_professional_context', handoff_ref=h,
        work_id=work, scene_id='scene', design_refs=(pin,))
    run = p.create_film_run(work_id=work, scene_id='scene', shot_id='shot', mode=RunMode.EXPERIMENT,
        source=source(), screenplay_ref=bound)
    refs = [p.creative.state.input(run.run_id).source_ref]
    for kind, body in ((Kind.WORK, canon().work), (Kind.SCRIPT, canon().script), (Kind.SCENE, canon().scene)):
        refs.append(p.creative_versions.write(writer=Authority.CANON, kind=kind, scope=run.scope,
            body=body, sources=tuple(refs), operation='aesthetic:'+kind.value))
    p.creative.state.save(run.run_id, run.scope, CreativeCheckpoint(refs=tuple(refs)))
    inp = CapabilityInput(run_id=run.run_id, scope=run.scope, operation_id='look-direction')
    req = p.creative._request(inp, Authority.DIRECTION)
    assert req.shot is None and set(req.professional_context) == {'filmLook'}
    calls = []
    def receive(wire):
        data = json.loads(wire.content); payload = json.loads(data['messages'][1]['content']); calls.append(payload)
        assert '# Work aesthetic design' in data['messages'][0]['content']
        assert payload['filmLook'][0]['grammarRules'][0]['execution'] == PALETTES['celebratory']
        assert 'sourcePins' not in payload['filmLook'][0]
        return response(shot().model_dump(mode='json', by_alias=True))
    p.creative.direction_author.client.transport = httpx.MockTransport(receive)
    await p.creative.direction_author.author(req)
    canon_payload = author_payload(p.creative._request(inp, Authority.CANON))
    assert 'filmLook' not in json.dumps(canon_payload) and 'professionalDesignRefs' not in json.dumps(canon_payload)
    assert p.screenplays.objects.read_ref(h) == original
    evidence('scene-direction', calls)
    await p.aclose()


def semantic_art(item, palette):
    value = reference_frame(item).model_dump(mode='json')
    for key in ('shot_id','shot_fingerprint','professional_sources','references','reference_lock',
                'reference_members','edit_source','scope_context','prompt_normalization','identity_bootstrap','image_mode'):
        value.pop(key, None)
    value.update(entry_state='Selected asset at rest', composition='Readable identity and construction',
        environment='Approved workroom materials or neutral proof background')
    ir = value['prompt_ir']; ir.pop('source_fingerprint')
    for key in ('provider_family','task_type','input_mode'): ir['task'].pop(key)
    for actor in value['actors']: actor.pop('entity_key')
    for subject in ir['subjects']: subject.pop('id')
    kind = item['assetType']
    details = {'CHARACTER':'Face, brow asymmetry and cloth weave',
        'LOCATION':'Both bays and the fixed left doorway',
        'PROP':'Box silhouette, single hinge and contact surfaces'}[kind]
    architecture = item['design'].get('architecture', 'Plain proof background')
    ir.update(world={'era':fact('Fictional period workroom design'),
        'location':fact(item['name'] if kind=='LOCATION' else 'Neutral proof space'),
        'historical_context':fact('Selected fictional asset proof'),
        'environment_rules':[fact('Only the selected design and its visible structure')]},
        environment={'architecture':fact(architecture,'IMPORTANT'),
            'topology':fact('Two connected bays with the doorway on the left' if kind=='LOCATION' else 'Unobtrusive background','IMPORTANT'),
            'required_period_objects':fact('Only the selected asset','IMPORTANT'),
            'props_vehicles':[fact(item['design']['construction'])] if kind=='PROP' else []},
        camera={'framing':fact('Selected asset fills the view with construction unobscured','IMPORTANT'),
            'shot_size':fact('Face and shoulders' if kind=='CHARACTER' else 'Complete selected structure','IMPORTANT'),
            'readable_details':fact(details,'IMPORTANT'),
            'perspective':fact('Three-quarter view preserves spatial relations','IMPORTANT')},
        lighting={'time_of_day':fact('Daylight proof','IMPORTANT'),
            'light_sources':fact('Broad window source','IMPORTANT'),
            'contrast':fact('Surface details remain readable in shadow','IMPORTANT'),
            'realism':fact('Distinct material responses under the same source','IMPORTANT')},
        preserve=[fact(palette)], secondary_details=[], negative_constraints=[])
    if ir['subjects']:
        ir['subjects'][0]['role'] = fact(item['name'])
        ir['subjects'][0]['costume'] = fact('Selected cloth garment','IMPORTANT')
        ir['action'] = {'current_visible_action':fact('At rest'), 'expression':fact('Resting face'), 'non_current':[]}
    return value


@pytest.mark.asyncio
@pytest.mark.parametrize('theme', PALETTES)
async def test_native_asset_sequence_to_three_final_image_requests(monkeypatch, tmp_path, theme):
    # Formal text transport, actual scene sequence and final image serializer.
    formal = configured(monkeypatch, tmp_path/'formal')
    author = formal.professional_design.author
    p = sequence_plugin(tmp_path/'sequence', monkeypatch, author)
    inp, req = request_for(p, 's-1')
    palette = PALETTES[theme]
    pin = p.screenplays.objects.put('look', work_look(req.scope.work_id, palette))
    req = req.model_copy(update={'professional_context':{'filmLook':[{'ref':dump_contract(pin),
        'design':p.screenplays.objects.read_ref(pin)}]}})
    calls = []
    phase = {'item':None}
    def receive(wire):
        data = json.loads(wire.content); payload = json.loads(data['messages'][1]['content'])
        calls.append({'system':data['messages'][0]['content'], 'payload':payload})
        assert payload['filmLook'][0]['grammarRules'][0]['execution'] == palette
        assert 'shot' not in payload and 'sourcePins' not in payload['filmLook'][0]
        assert 'Essential aesthetics are not optional' in data['messages'][0]['content']
        if phase['item'] is None:
            return wire_response({'assets':[
                {'assetType':'CHARACTER','name':'A','subjectSelection':0,'design':{
                    'face':'Long face with an asymmetric left brow','material':PROOF_LOOKS[theme]['CHARACTER']}},
                {'assetType':'LOCATION','name':'Workshop','design':{'architecture':'Two bays with a fixed left doorway','material':PROOF_LOOKS[theme]['LOCATION']}},
                {'assetType':'PROP','name':'Box','design':{'construction':'Rectangular box with a single hinge','material':PROOF_LOOKS[theme]['PROP']}}],
                'rationale':'FICTIONAL_WORK_REASON, translated into distinguishable durable assets'})
        assert payload['selectedAssetReference']['referenceInputs'] == []
        return wire_response(semantic_art(phase['item'], phase['item']['design']['material']))
    author.client.transport = httpx.MockTransport(receive)
    with pytest.raises(AssetPreparationPending) as pending:
        await p.professional_design.prepare_assets(req)
    packet = p.asset_sequence.objects.read_ref(pending.value.ref)
    assert packet['professionalBasisRefs'] == [dump_contract(pin)]
    scoped = AuthorRequest.model_validate(packet['referenceAuthorContext'])
    assert scoped.shot is None and scoped.scope.shot_id is None
    outputs = []
    before = deepcopy(packet)
    for item in packet['requirements']:
        phase['item'] = item
        spec = FrameSpec.model_validate(await author.design_asset_reference(scoped, item))
        wire = json.loads(json.dumps(compile_frame(spec)['request']['body']))
        assert wire['prompt'].count(item['design']['material']) == 1
        assert 'FICTIONAL_WORK_REASON' not in wire['prompt']
        if item['assetType']=='LOCATION': assert item['design']['architecture'] in wire['prompt']
        if item['assetType']=='PROP': assert item['design']['construction'] in wire['prompt']
        assert 'night' not in wire['prompt']
        if item['assetType']!='CHARACTER':
            assert 'faces and shoes' not in wire['prompt'] and 'full body' not in wire['prompt']
        assert 'image' not in wire and not spec.references
        assert '诺兰美学参考图' not in json.dumps(wire, ensure_ascii=False)
        assert ('Long face with an asymmetric left brow' in wire['prompt']) == (item['assetType']=='CHARACTER')
        outputs.append({'assetType':item['assetType'], 'request':wire})
    assert {r['assetType'] for r in outputs} == {'CHARACTER','LOCATION','PROP'}
    assert packet == before and p.screenplays.objects.read_ref(pin) == work_look(req.scope.work_id,palette)
    evidence('images-'+theme, {'calls':calls, 'finalRequests':outputs})
    await p.aclose(); await formal.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize('theme', PALETTES)
async def test_formal_professionals_to_final_seedance_wire(monkeypatch, tmp_path, theme):
    p = configured(monkeypatch, tmp_path/'formal')
    req, raw = material(single=True)
    palette = PALETTES[theme]
    req = req.model_copy(update={'shot':req.shot.model_copy(update={'professional_domains':tuple(sorted(
        {*req.shot.professional_domains, SourceDomain.COLOR, SourceDomain.LIGHTING}))}),
        'professional_context':{'filmLook':[{'design':work_look(req.scope.work_id,palette)}]}})
    raw += [{'domain':'COLOR','facts':{'scenePalette':palette,
        'arc':'Window reflection reveals the unchanged local colors', 'continuityInterpretation':'FICTIONAL_WORK_REASON'}},
        {'domain':'LIGHTING','facts':{'sources':'Side window illuminates the counter',
            'directionAndQuality':'Broad side light keeps the receiving hand readable'}}]
    camera = next(d['facts'] for d in raw if d['domain']=='CAMERA')
    camera['cameraPosition'] = 'Same side of the counter; listener remains visible behind the receiving hand'
    calls = []
    def receive(wire):
        data = json.loads(wire.content); payload = json.loads(data['messages'][1]['content']); calls.append(payload)
        assert payload['visualContinuity']['filmLook'][0]['grammarRules'][0]['execution'] == palette
        assert 'Interpret the selected Work grammar' in data['messages'][0]['content']
        return wire_response(raw)
    p.professional_design.author.client.transport = httpx.MockTransport(receive)
    designs = await p.professional_design.author.design(req)
    # Pass the actual validated FormalProfessionalAuthor results to the existing
    # test harness's persistence/assembly/compiler; skip its fixture projection.
    monkeypatch.setattr('test_event_scope_delivery.professional_projection',
        lambda _raw, _req: [d.model_dump(mode='json',by_alias=True) for d in designs])
    downstream, _, _, outputs = await pipeline(tmp_path/'delivery', monkeypatch, req, raw)
    wire = outputs[0]['wire']; prompt = wire['content'][0]['text']
    evidence('video-'+theme, {'authorInputs':calls, 'finalRequest':wire})
    for fragment in (*palette.replace(';', ',').split(', '), 'Side window illuminates the counter', 'receiving hand readable',
                     'listener remains visible', 'unchanged local colors'):
        assert fragment in prompt
    assert 'FICTIONAL_WORK_REASON' not in prompt and 'grammarRules' not in prompt
    assert '诺兰美学参考图' not in json.dumps(wire, ensure_ascii=False)
    evidence('video-'+theme, {'authorInputs':calls, 'finalRequest':wire})
    await downstream.aclose(); await p.aclose()


@pytest.mark.asyncio
async def test_film_binding_direction_and_scene_inheritance_are_real_and_story_is_preserved(monkeypatch, tmp_path):
    from drama_plugin.creative_engine.screenplay import ContextOriginal
    from drama_plugin.creative_engine.screenplay_author import native_scene_screenplay
    from drama_plugin.film.contracts import FilmCanon, CanonScene, FilmDirection, DirectedShot, LanguageMetadata, DeliveryProfile
    from test_formal_author_backends import REF
    from test_design_reconciliation import location
    p = configured(monkeypatch, tmp_path)
    work = 'aesthetic-film'
    source_pin = p.screenplays.retain_context(ContextOriginal(work_id=work, label='source',
        status='DESIGNATED_SOURCE', text=source().text))
    p.screenplays.begin(session_id='film', work_id=work, scope='FILM', goal='A complete film', source_refs=(source_pin,))
    p.screenplays.retain_v1('film', canon().script.screenplay)
    p.screenplays.decide('film', choice='KEEP_ALL', reason='Selected whole', expected_revision=1)
    h = p.screenplays.bind_selection('film', work_id=work, scene_id=None)
    original = p.screenplays.objects.read_ref(h)
    pin = p.screenplays.objects.put('look', work_look(work, PALETTES['celebratory']))
    bound = await p.tools.invoke('screenplay.bind_professional_context', handoff_ref=h,
        work_id=work, scene_id=None, design_refs=(pin,))
    # A film binding cannot smuggle another Work or a Scene-specific place.
    bad = p.screenplays.objects.put('wrong-work', work_look('elsewhere', PALETTES['restrained']))
    place = p.screenplays.objects.put('scene-place', dump_contract(location(scenes=('first',), identity='workshop')))
    for invalid in (bad, place):
        with pytest.raises(ValueError):
            await p.tools.invoke('screenplay.bind_professional_context', handoff_ref=h,
                work_id=work, scene_id=None, design_refs=(invalid,))
    run = p.create_source_film_run(work_id=work, run_id=work, source=source(), screenplay_ref=bound,
        languages=LanguageMetadata(source_document_language='en', original_work_language='ru', spoken_language='ru', authority_ref=REF),
        profile=DeliveryProfile(width=1280,height=720), rights_refs=(REF,), route='offline', model='offline-model')
    film = FilmCanon(work=canon().work, script=canon().script,
        scenes=(CanonScene(scene_id='first',scene=canon().scene),))
    p.film.store.put_author(run.run_id, film)
    inp = CapabilityInput(run_id=run.run_id, scope=run.scope, operation_id='film-direction')
    calls = []
    def receive(wire):
        data = json.loads(wire.content); payload = json.loads(data['messages'][1]['content']); calls.append(payload)
        system = data['messages'][0]['content']
        if 'Write the whole independent scene' in system:
            assert 'filmLook' not in json.dumps(payload) and 'professionalDesignRefs' not in json.dumps(payload)
            return wire_response({'text':canon().scene.scene_text})
        if 'You are the same Host author' in system:
            assert 'filmLook' not in json.dumps(payload) and 'professionalDesignRefs' not in json.dumps(payload)
            return wire_response({'choice':'KEEP_ALL','reason':'Retain the entire scene','text':None})
        assert '# Work aesthetic design' in system
        assert payload['filmLook'][0]['grammarRules'][0]['execution'] == PALETTES['celebratory']
        assert 'professionalDesignRefs' not in json.dumps(payload)
        assert 'filmLook' not in payload['hostScreenplay']
        return response(FilmDirection(shots=(DirectedShot(scene_id='first',shot_id='view',shot=shot().model_copy(update={'professional_domains':tuple(SourceDomain(d) for d in ('ACTION','CAMERA','LIGHTING','PERFORMANCE','SOUND','SUBJECTS','WORLD'))})),)).model_dump(mode='json',by_alias=True))
    p.film.direction_author.client.transport = httpx.MockTransport(receive)
    result = await p.film.direction(inp)
    assert result.status.value == 'SUCCEEDED'
    cp = p.film.store.checkpoint(run.run_id)
    context = p.screenplays.objects.read_ref(cp.screenplay_ref)
    handoff = context['selectedSceneScreenplays'][0]
    assert handoff['professionalDesignRefs'] == [dump_contract(pin)]
    assert handoff['screenplay']['text'] == canon().scene.scene_text
    unit = p.film.create_unit(inp, 0)
    child = p.runtime.store.load(unit.creative_run_id)
    p.creative.state.save(child.run_id,child.scope,CreativeCheckpoint(refs=unit.refs))
    child_req = p.creative._request(CapabilityInput(run_id=child.run_id,scope=child.scope,operation_id='verify-child'), Authority.PROFESSIONAL)
    assert child_req.professional_context['filmLook'][0]['ref'] == dump_contract(pin)
    assert author_payload(child_req)['visualContinuity']['filmLook'][0]['grammarRules'][0]['execution'] == PALETTES['celebratory']
    # Rebinding aesthetics after scene selection reuses the same story original.
    replacement = p.screenplays.objects.put('alternative-look', work_look(work, PALETTES['restrained']))
    changed = {**p.screenplays.objects.read_ref(bound), 'professionalDesignRefs':[dump_contract(replacement)]}
    req = p.film.request(inp).model_copy(update={'screenplay_context':changed})
    count = len(calls)
    revised = await native_scene_screenplay(p.screenplays,p.film.canon_author,req,
        operation=inp.operation_id,scene_id='first')
    assert len(calls) == count and revised['screenplayRef'] == handoff['screenplayRef']
    assert revised['professionalDesignRefs'] == [dump_contract(replacement)]
    assert p.screenplays.objects.read_ref(h) == original
    evidence('film-to-scene', {'authorInputs':calls,'childPayload':author_payload(child_req),
        'selectedStoryUnchanged':True, 'rebindDidNotReauthor':True})
    await p.aclose()
