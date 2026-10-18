"""Offline source refresh -> existing author -> native package -> final wire.

The deterministic author below is a chain fixture, not evidence of creative or
rendered quality. No network, paid author, media generation or deployment.
"""
from copy import deepcopy
import json
import socket

import httpx
import pytest

from drama_plugin.config.video_route import VideoRoutePolicy
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.creative_engine.author_projection import professional_projection
from drama_plugin.creative_engine.contracts import Authority, CreativeCheckpoint, DesignBody, Kind
from drama_plugin.creative_engine.screenplay import ContextOriginal
from drama_plugin.creative_engine.sources import NativeCreativeSources
from drama_plugin.execution.live_transport import TargetHttpTransport
from drama_plugin.generation.compiler import PromptCompiler
from drama_plugin.generation.contracts import FinalPromptArtifact, GenerationPreparation, GenerationTask, OwnerBindings
from drama_plugin.generation.operation import OperationResolver, resolve_profile
from drama_plugin.generation.sources import PackageReader
from drama_plugin.generation.store import GenerationArtifactStore
from drama_plugin.production.assembler import ShotAssembler
from drama_plugin.production.contracts import SourceDomain
from drama_plugin.production.store import ProductionPackageStore
from drama_plugin.professional_design.resolver import ProfessionalDesignResolver
from drama_plugin.runtime.contracts import ArtifactReference, CapabilityInput, RunMode, RuntimeScope
from test_event_scope_delivery import material
from test_formal_author_backends import configured


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('Design refresh tests cannot contact a service')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)


def current_row(versions, ref):
    value = versions.resolve(ref)
    return {'ref': dump_contract(ref), 'domain': value.body.domain.value, 'facts': deepcopy(value.body.facts)}


async def final_wire(p, req, refs):
    native = NativeCreativeSources(p.creative_versions, refs)
    package = (await ShotAssembler(native, ProfessionalDesignResolver(native)).assemble(req.scope,
        mode=RunMode.EXPERIMENT, policy_ref=ArtifactReference(owner='policy', artifact_ref='offline-refresh'))).package
    assert package is not None
    packages, artifacts = ProductionPackageStore(), GenerationArtifactStore()
    operations = OperationResolver(p.creative_versions, p.ledger, VideoRoutePolicy())
    reader = PackageReader(native, operations=operations)
    compiler = PromptCompiler(packages, artifacts, reader, _preview=True)
    pin = SourcePin(key='offline-unadmitted', kind='DESIGN', fingerprint='a' * 64)
    decision = ArtifactReference(owner='offline-unadmitted', artifact_ref='no-production-permission')
    owners = OwnerBindings(adopted_refs=refs, dpd_pin=pin, performance_scope_pin=pin,
        rights_pin=pin, rights_request_ref=decision, rights_decision_ref=decision, adoption_decision_ref=decision)
    unit = await operations.select_unit(package, reader, phase_index=0)
    profile = resolve_profile(model='seedance-2-standard', duration_ms=8000, resolution='720p', ratio='16:9',
        native_audio=True, mode='text_to_video', policy=operations.policy)
    result = await compiler.compile(packages.put(package), GenerationTask(unit=unit, profile=profile,
        owners=owners, native_audio='REQUIRED'))
    assert result.preparation_ref, artifacts.diagnostics(result.diagnostics_ref)
    ready = artifacts.get(result.preparation_ref, GenerationPreparation)
    assert not ready.provider_submission_allowed
    final = artifacts.get(ready.final_prompt_ref, FinalPromptArtifact)
    wire = TargetHttpTransport.preview(ready, final, ledger=p.ledger)
    assert wire['content'][0]['text'] == final.prompt_text
    return wire


@pytest.mark.asyncio
@pytest.mark.parametrize('upstream,change,shot_dependency', [
    *[(source, change, False) for source in ('work', 'scene', 'filmLook', 'locationCandidates') for change in ('replace', 'remove')],
    ('scene', 'replace', True),
])
async def test_changed_selected_design_reauthors_finite_facts_and_changes_final_wire(monkeypatch, tmp_path, upstream, change, shot_dependency):
    p = configured(monkeypatch, tmp_path)
    req, raw = material(single=True)
    req = req.model_copy(update={'shot': req.shot.model_copy(update={
        'professional_domains': tuple(sorted((*req.shot.professional_domains, SourceDomain.LIGHTING)))})})
    run = p.create_film_run(work_id=req.scope.work_id, scene_id=req.scope.scene_id, shot_id=req.scope.shot_id,
        mode=RunMode.EXPERIMENT, source=req.source)
    workshop = p.screenplays
    source_context = workshop.retain_context(ContextOriginal(work_id=req.scope.work_id, label='source',
        status='DESIGNATED_SOURCE', text=req.source.text))
    film_context = workshop.retain_context(ContextOriginal(work_id=req.scope.work_id, label='film',
        status='ADOPTED_FACT', text=req.canon.script.screenplay, authority_ref='selected-film'))
    workshop.begin(session_id='refresh-scene', work_id=req.scope.work_id, scene_id=req.scope.scene_id,
        scope='SCENE', goal='Preserve the complete selected scene', source_refs=(source_context, film_context), full_film_ref=film_context)
    workshop.retain_v1('refresh-scene', req.canon.scene.scene_text)
    workshop.decide('refresh-scene', choice='KEEP_ALL', reason='Selected complete original', expected_revision=1)
    handoff = workshop.bind_selection('refresh-scene', work_id=req.scope.work_id, scene_id=req.scope.scene_id)
    core = [p.creative_versions.write(writer=Authority.SOURCE, kind=Kind.SOURCE,
        scope=RuntimeScope(work_id=req.scope.work_id), body=req.source, sources=(), operation='broad-source')]
    for owner, kind, body in ((Authority.CANON, Kind.WORK, req.canon.work),
            (Authority.CANON, Kind.SCRIPT, req.canon.script), (Authority.CANON, Kind.SCENE, req.canon.scene),
            (Authority.DIRECTION, Kind.SHOT, req.shot)):
        scope = (RuntimeScope(work_id=req.scope.work_id) if kind in {Kind.WORK, Kind.SCRIPT}
            else RuntimeScope(work_id=req.scope.work_id, scene_id=req.scope.scene_id) if kind == Kind.SCENE
            else req.scope)
        core.append(p.creative_versions.write(writer=owner, kind=kind, scope=scope,
            body=body, sources=tuple(core), operation='refresh-core:' + kind.value))
    calls = []
    direction_calls = []
    # Canon is already complete and pinned; this regression exercises existing
    # Direction and Professional authors without requesting new screenplay work.
    p.creative.canon_author = None

    def formal_receive(wire):
        packet = json.loads(wire.content)
        payload = json.loads(packet['messages'][1]['content'])
        if packet['model'] == 'offline-direction-model':
            candidate = payload['shot']
            assert candidate == req.shot.model_dump(mode='json', by_alias=True, exclude={'spoken_ids'})
            upstream_view = payload['visualContinuity']['currentDesigns']
            assert upstream_view == [{'domain': 'LIGHTING', 'facts': {
                'designDecisions': 'The shutter leaves a narrow neutral side strip.'}, 'scope': 'SCENE'}]
            assert 'review that retained Shot against their new meaning' in packet['messages'][0]['content']
            direction_calls.append(candidate)
            body = {**candidate, 'spokenSelections': [0]}
            return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
                'role': 'assistant', 'content': json.dumps(body)}}]})
        context = payload['visualContinuity']
        if upstream in {'work', 'scene'}:
            rows = [row for row in context.get('currentDesigns', []) if row.get('scope') == upstream.upper()]
            text = next((row['facts']['designDecisions'] for row in rows if row['domain'] == 'LIGHTING'),
                'Current Shot daylight without the removed upstream style.')
            assert all('ref' not in row and 'sourcePins' not in row['facts'] for row in rows)
        elif upstream == 'filmLook':
            rows = context['filmLook']
            text = rows[0]['grammarRules'][0]['execution'] if rows else 'Current Shot daylight without the removed upstream style.'
        else:
            rows = context['locationCandidates']
            text = rows[0]['design']['lightingBehavior'] if rows else 'Current Shot daylight without the removed upstream style.'
        calls.append(text)
        # A deterministic local text-wire fixture proves the real Formal author
        # interface and source projection, not independent artistic judgment.
        body = [*deepcopy(raw), {'domain': 'LIGHTING', 'facts': {'sources': [text],
            'directionAndQuality': 'The same local action stays visible.'}}]
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
            'role': 'assistant', 'content': json.dumps(body)}}]})

    p.professional_design.author.client.transport = httpx.MockTransport(formal_receive)
    inputs = CapabilityInput(run_id=run.run_id, scope=req.scope, operation_id='same-unfinished-preparation')
    frozen_wire = None
    fingerprints = []
    texts = ('The shutter leaves a narrow amber side strip.', 'The shutter leaves a narrow neutral side strip.'
        if change == 'replace' else 'Current Shot daylight without the removed upstream style.')
    for index, text in enumerate(texts):
        selected_refs = list(core)
        context_refs = ()
        if index and change == 'remove':
            pass
        elif upstream in {'work', 'scene'}:
            parent = p.creative_versions.write(writer=Authority.PROFESSIONAL, kind=Kind.PROFESSIONAL,
                scope=RuntimeScope(work_id=req.scope.work_id, scene_id=req.scope.scene_id if upstream == 'scene' else None),
                body=DesignBody(domain='LIGHTING', facts={'designDecisions': text}),
                sources=tuple(core[:-1] if upstream == 'scene' else core[:3]), operation='upstream-light:' + str(index))
            selected_refs.append(parent)
            if shot_dependency and not index:
                dependent_shot = p.creative_versions.write(writer=Authority.DIRECTION, kind=Kind.SHOT,
                    scope=req.scope, body=req.shot, sources=(*core[:-1], parent), operation='shot-consumed-upstream')
                core[-1] = dependent_shot
                selected_refs = [*core[:-1], parent, dependent_shot]
        else:
            if upstream == 'filmLook':
                from test_professional_continuity import look
                design = dump_contract(look(req.scope.work_id))
                design['grammarRules'][0]['execution'] = text
            else:
                from test_design_reconciliation import location
                design = dump_contract(location(scenes=(req.scope.scene_id,)))
                design['lightingBehavior'] = text
            ref = p.creative_versions.objects.put('selected-' + upstream, design)
            context_refs = (ref,)
        selected_handoff = await p.tools.invoke('screenplay.bind_professional_context', handoff_ref=handoff,
            work_id=req.scope.work_id, scene_id=req.scope.scene_id, design_refs=context_refs)
        # An unfinished preparation can retain cached output under this operation
        # ID; changing its selected design must not replay that old author body.
        if index:
            selected_refs.extend(ref for ref in previous_refs if p.creative_versions.resolve(ref).kind == Kind.PROFESSIONAL
                and p.creative_versions.resolve(ref).scope == req.scope)
        p.creative.state.save(run.run_id, req.scope, CreativeCheckpoint(refs=tuple(selected_refs), screenplay_ref=selected_handoff))
        if shot_dependency and index:
            # Do not loosen Professional's stale-Shot boundary. The existing
            # Direction author sees the retained Shot intent, consciously keeps
            # it, and binds the newly selected upstream authority first.
            with pytest.raises(ValueError, match='CREATIVE_EXECUTION_INPUT_STALE'):
                p.creative.inspect_professional_execution(inputs)
            direction = inputs.model_copy(update={'operation_id': 'direction-rechecks-new-parent'})
            assert not p.creative.inspect_direction_execution(direction).completed
            assert (await p.runtime.executor.execute('creative.direction:v1', direction)).status == 'SUCCEEDED'
            refreshed = p.creative.state.checkpoint(run.run_id).refs
            current_shot = next(ref for ref in refreshed if p.creative_versions.resolve(ref).kind == Kind.SHOT)
            assert parent in p.creative_versions.resolve(current_shot).source_refs
            assert not p.creative_versions.stale(current_shot)
            assert p.creative_versions.resolve(current_shot).body == req.shot
        current_request = p.creative._request(inputs, Authority.PROFESSIONAL)
        fingerprints.append(p.professional_design.creative_input_fingerprint(current_request))
        if index:
            old_bodies = [p.creative_versions.resolve(ref).body for ref in previous_refs
                if p.creative_versions.resolve(ref).kind == Kind.PROFESSIONAL
                and p.creative_versions.resolve(ref).scope == req.scope]
            assert not p.professional_design.asset_inheritance_current(current_request, old_bodies, p.creative_versions)
        result = await p.runtime.executor.execute('creative.professional:v1', inputs)
        assert result.status == 'SUCCEEDED', result
        previous_refs = p.creative.state.checkpoint(run.run_id).refs
        wire = await final_wire(p, req, previous_refs)
        assert text.rstrip('.') in wire['content'][0]['text']
        assert 'designDecisions' not in wire['content'][0]['text']
        if index:
            assert calls[0].rstrip('.') not in wire['content'][0]['text']
            assert calls[0].rstrip('.') in frozen_wire['content'][0]['text']
        else:
            frozen_wire = deepcopy(wire)
    assert fingerprints[0] != fingerprints[1]
    assert calls == list(texts)
    # A subsequent preparation with the same selected authority simply reuses
    # the current bundle; its own refs must not create an endless refresh loop.
    again = inputs.model_copy(update={'operation_id': 'reuse-current-bundle'})
    assert (await p.runtime.executor.execute('creative.professional:v1', again)).status == 'SUCCEEDED'
    assert len(calls) == 2
    assert len(direction_calls) == int(shot_dependency)
    await p.aclose()


def test_no_design_context_retains_legacy_reuse_and_cache_key(tmp_path):
    from test_formal_author_backends import request
    req = request('professional')
    resolver = ProfessionalDesignResolver(None)
    body = DesignBody(domain='LIGHTING', facts={'sources': 'Existing practical', 'directionAndQuality': 'Side'})
    assert resolver.asset_inheritance_current(req, (body,))
    assert resolver.creative_input_fingerprint(req) is None


def test_explicit_upstream_does_not_reuse_an_unmarked_old_professional(tmp_path):
    from drama_plugin.creative_engine.store import CreativeVersionStore
    from test_formal_author_backends import request
    versions = CreativeVersionStore(tmp_path / 'originals')
    req = request('professional')
    parent = versions.write(writer=Authority.PROFESSIONAL, kind=Kind.PROFESSIONAL,
        scope=RuntimeScope(work_id=req.scope.work_id, scene_id=req.scope.scene_id),
        body=DesignBody(domain='LIGHTING', facts={'designDecisions': 'New selected source'}),
        sources=(), operation='selected-upstream')
    req = req.model_copy(update={'professional_context': {'currentDesigns': [current_row(versions, parent)]}})
    prior = DesignBody(domain='LIGHTING', facts={'sources': 'Old unmarked light', 'directionAndQuality': 'Old direction'})
    assert not ProfessionalDesignResolver(None).asset_inheritance_current(req, (prior,), versions)


def test_upstream_professional_pin_follows_exact_adoption_without_self_dependency(tmp_path):
    from drama_plugin.creative_engine.store import CreativeVersionStore
    from drama_plugin.professional_design.provenance import validate_metadata
    from test_formal_author_backends import request
    versions = CreativeVersionStore(tmp_path / 'originals')
    req = request('professional')
    scene_scope = RuntimeScope(work_id=req.scope.work_id, scene_id=req.scope.scene_id)
    parent = versions.write(writer=Authority.PROFESSIONAL, kind=Kind.PROFESSIONAL, scope=scene_scope,
        body=DesignBody(domain='LIGHTING', facts={'designDecisions': 'Selected day light, no night replay.'}),
        sources=(), operation='scene-design')
    req = req.model_copy(update={'source_refs': (parent,), 'professional_context': {
        'currentDesigns': [current_row(versions, parent)]}})
    resolver = ProfessionalDesignResolver(None)
    child = resolver.persist(versions, req, DesignBody(domain='LIGHTING',
        facts={'sources': ['Narrow window'], 'directionAndQuality': 'Local side light.'}), operation='shot-design')
    assert versions.resolve(child).source_refs == (parent,)
    decision = ArtifactReference(owner='offline-fixture', artifact_ref='not-a-user-approval')
    adopted_parent = versions.write(writer=Authority.PROFESSIONAL, kind=Kind.PROFESSIONAL, scope=scene_scope,
        body=versions.resolve(parent).body, sources=(), operation='adopt-scene',
        adoption_decision=decision, candidate_origin=parent)
    adopted_child = versions.write(writer=Authority.PROFESSIONAL, kind=Kind.PROFESSIONAL, scope=req.scope,
        body=versions.resolve(child).body, sources=(adopted_parent,), operation='adopt-shot',
        adoption_decision=decision, candidate_origin=child)
    adopted = versions.resolve(adopted_child)
    assert adopted.body.facts['continuityDesignRefs'] == [dump_contract(adopted_parent)]
    validate_metadata(adopted.body, versions, req.scope, adopted.source_refs)
    assert versions.resolve(child).body.facts['continuityDesignRefs'] == [dump_contract(parent)]
    own = req.model_copy(update={'source_refs': (child,), 'professional_context': {
        'currentDesigns': [current_row(versions, child)]}})
    replacement = resolver.persist(versions, own, DesignBody(domain='LIGHTING',
        facts={'sources': ['Updated finite original'], 'directionAndQuality': 'Same target scope.'}), operation='replace-shot')
    assert versions.resolve(replacement).source_refs == ()
    assert not versions.stale(replacement)


@pytest.mark.asyncio
@pytest.mark.parametrize('revision', [False, True])
async def test_formal_scope_views_keep_upstream_and_target_beat_maps_distinct(monkeypatch, tmp_path, revision):
    from test_professional_revision_input import fixture
    req, raw, candidate = fixture()
    scene_scope = RuntimeScope(work_id=req.scope.work_id, scene_id=req.scope.scene_id)
    upstream = deepcopy(candidate)
    beat_ids = {row['id'] for design in upstream if design['domain'] == 'PERFORMANCE'
        for row in design['facts']['beats']}

    def scene_ids(value):
        if isinstance(value, dict):
            return {key: scene_ids(child) for key, child in value.items()}
        if isinstance(value, list):
            return [scene_ids(child) for child in value]
        return 'upstream-' + value if isinstance(value, str) and value in beat_ids else value

    upstream = scene_ids(upstream)
    for row in upstream:
        row['facts']['scope'] = dump_contract(scene_scope)
    target = deepcopy(candidate)
    for row in target:
        row['facts']['scope'] = dump_contract(req.scope)
    req = req.model_copy(update={'professional_context': {'currentDesigns': [*upstream, *target]},
        'revision': req.revision if revision else None})
    p = configured(monkeypatch, tmp_path)
    calls = []

    def receive(wire):
        packet = json.loads(wire.content)
        evidence = json.loads(packet['messages'][1]['content'])
        rows = evidence['visualContinuity']['currentDesigns']
        scene_rows = [row for row in rows if row.get('scope') == 'SCENE']
        target_rows = [row for row in rows if 'scope' not in row]
        assert len(scene_rows) == len(upstream)
        assert len(target_rows) == (0 if revision else len(target))
        if revision:
            task = json.loads(packet['messages'][-1]['content'].split('\n', 1)[1])
            target_rows = task['currentDesigns']
            assert len(target_rows) == len(target)
            assert all('scope' not in row for row in target_rows)
        for bundle in (scene_rows, target_rows):
            action = next(row['facts'] for row in bundle if row['domain'] == 'ACTION')
            assert [row['beatSelection'] for row in action['actionPhases']] == [0, 1]
            assert all('beatId' not in row for row in action['actionPhases'])
            assert all('scope' not in row['facts'] for row in bundle)
        encoded = json.dumps([rows, target_rows])
        assert all(identifier not in encoded and 'upstream-' + identifier not in encoded for identifier in beat_ids)
        assert all(key not in encoded for key in ('"workId"', '"sceneId"', '"shotId"', '"sourcePins"'))
        calls.append(packet)
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
            'role': 'assistant', 'content': json.dumps(raw)}}]})

    p.professional_design.author.client.transport = httpx.MockTransport(receive)
    await (p.professional_design.revise(req) if revision else p.professional_design.design(req))
    assert len(calls) == 1
    await p.aclose()
