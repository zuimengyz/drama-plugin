"""Real author boundary and existing audio consumer; offline, no media service."""
from copy import deepcopy
import json

import httpx
import pytest

from drama_plugin.creative_engine.author_projection import professional_projection
from drama_plugin.creative_engine.contracts import CanonDraft, Dialogue, SceneBody
from drama_plugin.creative_engine.diagnostics import AuthorResultFailure, AuthorUnavailable
from drama_plugin.production.contracts import SourceDomain
from test_formal_author_backends import configured, request, SKILLS


@pytest.mark.parametrize('domain,paths', [
    ('ACTION', ('blocking', 'action-choreography')),
    ('SOUND', ('voice-direction', 'sound-design')),
    ('WORLD', ('specialized-asset-design', 'scene-layout')),
    ('PERFORMANCE', ('dramatic-performance-direction',)),
    ('CAMERA', ('cinematography',)),
    ('EDITORIAL', ('editorial-design',)),
    ('REFERENCE', ('reference-strategy',)),
])
async def test_formal_wire_reads_scoped_current_method_files(monkeypatch, tmp_path, domain, paths):
    p = configured(monkeypatch, tmp_path)
    author = p.professional_design.author
    root = tmp_path / 'knowledge'
    for name in (*paths, 'unrequested-department'):
        dest = root / name / 'SKILL.md'; dest.parent.mkdir(parents=True)
        dest.write_text((SKILLS / name / 'SKILL.md').read_text() if name in paths else 'UNREQUESTED_SENTINEL')
    author.skills_root = root
    req = request('professional')
    req = req.model_copy(update={'shot':req.shot.model_copy(update={'professional_domains':(SourceDomain(domain),)})})
    wire = []
    def receive(r):
        wire.append(json.loads(r.content))
        return httpx.Response(503)
    author.client.transport = httpx.MockTransport(receive)
    before = author.execution_fingerprint(req)
    with pytest.raises(AuthorUnavailable):
        await p.professional_design.design(req)
    for name in paths:
        assert (root / name / 'SKILL.md').read_text() in wire[-1]['messages'][0]['content']
    assert 'UNREQUESTED_SENTINEL' not in wire[-1]['messages'][0]['content']
    assert json.loads(wire[-1]['messages'][1]['content'])['shot']['subjectAction'] == req.shot.subject_action
    dest = root / paths[0] / 'SKILL.md'
    dest.write_text(dest.read_text() + '\nFRESH_METHOD_REVISION\n')
    assert author.execution_fingerprint(req) != before
    with pytest.raises(AuthorUnavailable):
        await p.professional_design.design(req)
    assert 'FRESH_METHOD_REVISION' in wire[-1]['messages'][0]['content']
    assert len(wire) == 2
    await p.aclose()


def sound_request():
    req = request('professional')
    scene = SceneBody(scene_text='A remembered date precedes the present appeal.', dialogue=(
        Dialogue(id='date', speaker='traveler', text='В тот день.'),
        Dialogue(id='appeal', speaker='traveler', text='Помогите.')))
    return req.model_copy(update={'canon':CanonDraft(work=req.canon.work, script=req.canon.script, scene=scene),
        'shot':req.shot.model_copy(update={'professional_domains':(SourceDomain.SOUND,), 'spoken_ids':('date','appeal')})})


def sound_model():
    return [{'domain':'SOUND','facts':{'ambience':[{'design':'Rain continues.'}], 'orderingRules':[],
        'audio_events':[
            {'spokenSelection':0, 'delivery_mode':'VOICE_OVER', 'performance':'Matter-of-fact recollection.',
                'space':'Outside pictured room.', 'attention':'The date is clear.', 'continuity':'Yield to the appeal.'},
            {'spokenSelection':1, 'delivery_mode':'ON_SCREEN', 'performance':'Address the listener without a second pause.'}],
        'speechRelations':[{'spokenSelection':0,'targetSpokenSelection':1,'relation':'BEFORE'}]}}]


async def test_formal_author_binds_existing_per_line_audio_without_inventing_words(monkeypatch,tmp_path):
    p = configured(monkeypatch,tmp_path)
    raw = sound_model(); original = deepcopy(raw)
    p.professional_design.author.client.transport = httpx.MockTransport(lambda r:httpx.Response(200,json={
        'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(raw)}}]}))
    req = sound_request(); before = req.model_dump_json()
    designs = await p.professional_design.design(req)
    events = designs[0].facts['audio_events']
    assert [(e['event_id'],e['spoken_content_id'],e['speaker_key'],e['delivery_mode']) for e in events] == [
        ('date','date','traveler','VOICE_OVER'),('appeal','appeal','traveler','ON_SCREEN')]
    assert events[0]['performance'] == raw[0]['facts']['audio_events'][0]['performance']
    assert designs[0].facts['speechRelations'] == [{'eventId':'date','targetEventId':'appeal','relation':'BEFORE'}]
    assert req.model_dump_json() == before and raw == original
    await p.aclose()


@pytest.mark.parametrize('change', ['foreign-line','invented-speaker','rewritten-words','invented-timing','invalid-delivery'])
def test_audio_author_cannot_replace_canon_or_invent_timing(change):
    raw = sound_model(); event = raw[0]['facts']['audio_events'][0]
    key,value = {'foreign-line':('spokenSelection',2),'invented-speaker':('speaker_key','other'),
        'rewritten-words':('text','New speech'),'invented-timing':('window_ms',[0,1000]),
        'invalid-delivery':('delivery_mode','INVENTED')}[change]
    event[key] = value
    with pytest.raises(AuthorResultFailure):professional_projection(raw,sound_request())


def test_audio_declarations_remain_optional_for_existing_silent_and_simple_designs():
    req = sound_request()
    raw = sound_model(); del raw[0]['facts']['audio_events']
    assert 'audio_events' not in professional_projection(raw,req)[0]['facts']


@pytest.mark.parametrize('invalid', [None, 'wrong-speaker', 'duplicate-event'])
async def test_formal_audio_output_reaches_native_package_projection_and_compiler(monkeypatch, tmp_path, invalid):
    from drama_plugin.creative_engine.contracts import Authority, DesignBody, Kind
    from drama_plugin.creative_engine.sources import NativeCreativeSources
    from drama_plugin.generation.compiler import PromptCompiler
    from drama_plugin.generation.contracts import AudioExecutionPlan, FinalPromptArtifact, GenerationPreparation, PromptCoverage, GenerationTask, OwnerBindings
    from drama_plugin.generation.operation import OperationResolver, resolve_profile
    from drama_plugin.config.video_route import VideoRoutePolicy
    from drama_plugin.contracts.source_pin import SourcePin
    from drama_plugin.generation.sources import PackageReader
    from drama_plugin.generation.store import GenerationArtifactStore
    from drama_plugin.production.assembler import ShotAssembler
    from drama_plugin.production.store import ProductionPackageStore
    from drama_plugin.professional_design.resolver import ProfessionalDesignResolver
    from drama_plugin.runtime.contracts import ArtifactReference, RunMode

    p = configured(monkeypatch, tmp_path)
    p.professional_design.author.client.transport = httpx.MockTransport(lambda r: httpx.Response(200, json={
        'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': json.dumps(sound_model())}}]}))
    req = sound_request()
    sound = (await p.professional_design.design(req))[0]
    if invalid == 'wrong-speaker':
        sound.facts['audio_events'][0]['speaker_key'] = 'someone-else'
    elif invalid == 'duplicate-event':
        sound.facts['audio_events'].append(deepcopy(sound.facts['audio_events'][0]))
    shot = req.shot.model_copy(update={'professional_domains': tuple(SourceDomain(d) for d in
        ('ACTION', 'CAMERA', 'PERFORMANCE', 'SOUND', 'SUBJECTS', 'WORLD'))})
    refs = []
    for kind, body, owner in ((Kind.SOURCE, req.source, Authority.SOURCE),
            (Kind.WORK, req.canon.work, Authority.CANON), (Kind.SCRIPT, req.canon.script, Authority.CANON),
            (Kind.SCENE, req.canon.scene, Authority.CANON), (Kind.SHOT, shot, Authority.DIRECTION)):
        refs.append(p.creative_versions.write(writer=owner, kind=kind, scope=req.scope, body=body,
            sources=tuple(refs), operation='offline-craft:' + kind.value))
    core = tuple(refs)
    subjects = DesignBody(domain='SUBJECTS', facts={'presentSubjects':[
        {'id':'traveler', 'appearance':'Approved traveler in a worn coat.'}]})
    action = DesignBody(domain='ACTION', facts={'physicalStateConstraints': [
        'The door remains on its hinges.', 'His feet stay outside the threshold.'], 'actionPhases': [{'beatId':'beat-0',
        'spokenIds':['date','appeal'], 'entryState':'At the closed door.',
        'action':'The traveler calls once and waits.', 'observable':'The door remains closed.'}]})
    other = (DesignBody(domain='CAMERA', facts={'movement':'Fixed view of the doorway.'}),
        DesignBody(domain='WORLD', facts={'setting':'A closed wooden door at the room entrance.'}),
        DesignBody(domain='PERFORMANCE', facts={'physicalExpression':'He listens for a response, keeping his hand still.'}))
    for design in (sound, subjects, action, *other):
        refs.append(p.creative_versions.write(writer=Authority.PROFESSIONAL, kind=Kind.PROFESSIONAL,
            scope=req.scope, body=design, sources=core, operation='offline-craft:' + design.domain.value))
    native = NativeCreativeSources(p.creative_versions, tuple(refs))
    assembled = await ShotAssembler(native, ProfessionalDesignResolver(native)).assemble(req.scope,
        mode=RunMode.EXPERIMENT, policy_ref=ArtifactReference(owner='policy', artifact_ref='offline-craft'))
    assert assembled.validation.status == 'READY'
    packages, artifacts = ProductionPackageStore(), GenerationArtifactStore()
    package_ref = packages.put(assembled.package)
    operations = OperationResolver(p.creative_versions, p.ledger, VideoRoutePolicy())
    reader = PackageReader(native, operations=operations)
    selection = await operations.select_unit(assembled.package, reader)
    profile = resolve_profile(model='seedance-2-standard', duration_ms=4000, resolution='720p', ratio='16:9',
        native_audio=True, mode='text_to_video', policy=operations.policy)
    # Preview explicitly does not admit production. These isolated contract references
    # are never resolved as approvals, and are not copied into production state.
    pin = SourcePin(key='offline-unadmitted', kind='DESIGN', fingerprint='a'*64)
    decision = ArtifactReference(owner='offline-unadmitted', artifact_ref='no-production-permission')
    owners = OwnerBindings(adopted_refs=tuple(refs), dpd_pin=pin, performance_scope_pin=pin, rights_pin=pin,
        rights_request_ref=decision, rights_decision_ref=decision, adoption_decision_ref=decision)
    task = GenerationTask(unit=selection, profile=profile, owners=owners, native_audio='REQUIRED')
    compiler = PromptCompiler(packages, artifacts, reader, _preview=True)
    if invalid is None:
        selected = await operations.selected(assembled.package, task, reader, admission_required=False)
        audio_result = compiler.audio.assemble(assembled.package, task, selected)
        assert audio_result.plan is not None
        projected = await compiler.projection.project(assembled.package, task, audio_result.plan, selected)
        assert projected.ir is not None, projected.diagnostics
        constraints = [f for f in projected.ir.facts if f.source_ref.path[1:2] == ('physicalStateConstraints',)]
        assert len(constraints) == 2 and all(f.slot == 'preserve.physical_state' for f in constraints)
    compiled = await compiler.compile(package_ref, task)
    if invalid:
        assert compiled.preparation_ref is None
        assert any(d.code == 'DIALOGUE_IDENTITY_MISMATCH' for d in artifacts.diagnostics(compiled.diagnostics_ref))
    else:
        assert compiled.preparation_ref is not None, artifacts.diagnostics(compiled.diagnostics_ref)
        ready = artifacts.get(compiled.preparation_ref, GenerationPreparation)
        audio = artifacts.get(ready.audio_plan_ref, AudioExecutionPlan)
        final = artifacts.get(ready.final_prompt_ref, FinalPromptArtifact)
        coverage = artifacts.get(final.coverage_ref, PromptCoverage)
        assert [(e.event_id, e.delivery_mode) for e in audio.speech_events] == [('date','VOICE_OVER'), ('appeal','ON_SCREEN')]
        for text in ('{В тот день.}', '{Помогите.}', 'Matter-of-fact recollection.', 'Outside pictured room.',
                     'The date is clear.', 'Yield to the appeal.', 'Address the listener without a second pause.'):
            assert final.prompt_text.count(text) == 1
        assert any(e.source_ref.path[-3:] == ('audio_events','0','performance') and e.status == 'TEXT_COVERED'
            for e in coverage.entries)
        assert '事件2' not in final.prompt_text
        assert final.prompt_text.count('The door remains on its hinges.') == 1
        assert final.prompt_text.count('His feet stay outside the threshold.') == 1
        assert not ready.provider_submission_allowed
        assert native.version(Kind.SCENE).body == req.canon.scene
    await p.aclose()
