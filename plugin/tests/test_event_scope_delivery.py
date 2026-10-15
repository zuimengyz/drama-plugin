"""Offline DTO -> package -> selection -> Seedance wire. Fixtures are not real authors."""
from copy import deepcopy
import json
import socket

import pytest

from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.creative_engine.author_projection import professional_projection
from drama_plugin.creative_engine.backends import validate_professional_facts
from drama_plugin.creative_engine.contracts import Authority, DesignBody, Kind, SceneBody
from drama_plugin.creative_engine.diagnostics import AuthorResultFailure
from drama_plugin.creative_engine.sources import NativeCreativeSources
from drama_plugin.execution.live_transport import TargetHttpTransport
from drama_plugin.generation.compiler import PromptCompiler
from drama_plugin.generation.contracts import (GenerationTask, OwnerBindings, GenerationPreparation,
    FinalPromptArtifact, PromptCoverage)
from drama_plugin.generation.operation import OperationResolver, resolve_profile
from drama_plugin.generation.sources import PackageReader
from drama_plugin.generation.store import GenerationArtifactStore
from drama_plugin.config.video_route import VideoRoutePolicy
from drama_plugin.production.assembler import ShotAssembler
from drama_plugin.production.contracts import SourceDomain
from drama_plugin.production.store import ProductionPackageStore
from drama_plugin.professional_design.resolver import ProfessionalDesignResolver
from drama_plugin.runtime.contracts import ArtifactReference, RunMode
from test_formal_author_backends import configured, request


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*a, **kw):
        raise AssertionError('Event-scope tests cannot call a model or provider')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)


def material(*, single=False, scoped_sound=True):
    req = request('professional')
    scene = SceneBody.model_validate({'sceneText':'A courier and a keeper wait, then pass a packet.',
        'subjects':[{'id':'courier','name':'Courier','meaning':'Asks the keeper.'},
                    {'id':'keeper','name':'Keeper','meaning':'Receives the packet.'}],
        'dialogue':[{'id':'call','speaker':'courier','text':'Помогите.'}]})
    domains = tuple(sorted(SourceDomain(d) for d in ('ACTION','PERFORMANCE','CAMERA','WORLD','SUBJECTS','SOUND','EDITORIAL')))
    req = req.model_copy(update={'canon':req.canon.model_copy(update={'scene':scene}),
        'shot':req.shot.model_copy(update={'professional_domains':domains,'spoken_ids':('call',),'duration_ms':8000})})
    start = {'beatSelection':0,'spokenSelections':[],'entryState':'Both stand at the counter.',
        'action':'0–2s: both wait without touching the packet.','observable':'The packet stays on the counter.'}
    contact = {'beatSelection':1,'spokenSelections':[0],'entryState':'Both remain at the counter.',
        'action':'0–2s: the keeper supports the packet while the courier loosens the grip; 2–5s: the courier speaks while the keeper holds it still.',
        'observable':'5–8s: the packet is supported by the keeper; listening continues without a second transfer.'}
    phases = [contact] if single else [start, contact]
    phase = 0 if single else 1
    beats = [{'actorSelection':actor,'targetSelection':1-actor,'objective':'Complete the approved exchange',
        'obstacle':'The other person is occupied','tactic':'Make room for the exchange',
        'note':'No invented response','transitionTrigger':'The partner is ready',
        'direction':{'tactic':'Make room for the exchange'},'physicalExpression':text} for actor,text in (
            (0,'The courier waits without another gesture.'), (0,'The courier releases only after support.'),
            (1,'The keeper listens while holding the packet.'))]
    performance = {'sceneDPD':{'dramaticPurpose':'An appeal accompanies a handoff.',
        'conflictCondition':'The recipient is occupied.','powerStructure':'Neither can rush the other.',
        'direction':{'objective':'Complete the exchange','interactionTargetSelection':1,'tactic':'Wait for readiness',
            'authorityPosition':'Requester','relationshipStance':'Attend to the partner','internalActivation':'MEDIUM',
            'externalControl':'HIGH','publicPrivateContext':'At a shared counter'}},
        'beats':beats,'lines':[{'spokenSelection':0,'beatSelection':1,'dramaticAction':'Appeal',
            'observableIntent':'Address the keeper','continuity':'The keeper continues supporting the packet',
            'changeFromPrevious':'Work accompanies speech'}],
        'projectionSubjects':[{'subjectSelection':0,'role':'INTERACTIVE_PARTNER','beatSelections':[0,1]},
            {'subjectSelection':1,'role':'INTERACTIVE_PARTNER','beatSelections':[2]}]}
    camera = {'policy':'WHOLE_CAMERA_POLICY: wait, then approach the pair.', 'phaseDirections':[
        {'phaseIndex':i,'inheritedState':'Counter view on the same side of the axis.',
        'decision':'HOLD' if i == 0 and not single else 'START',
        'trigger':'0–2s: begin only on the receiving hand taking the weight.' if i == phase else 'Wait for readiness.',
        'motivation':'Read the transfer without losing the listener.', 'trajectory':'Same side, small approach.' if i == phase else 'No displacement.',
        'amplitude':'Small' if i == phase else 'None','endState':'2–8s: hold the resulting view.' if i == phase else 'Same counter view.',
        'sceneContext':'WHOLE_CAMERA_CONTEXT','precedingBeatContext':'PAST_CAMERA_EVENT','followingBeatContext':'FUTURE_CAMERA_EVENT'}
        for i in range(len(phases))]}
    raw = [{'domain':'ACTION','facts':{'actionPhases':phases,'physicalStateConstraints':'The counter stays fixed.'}},
        {'domain':'PERFORMANCE','facts':performance}, {'domain':'CAMERA','facts':{'movement':camera}},
        {'domain':'WORLD','facts':{'setting':'A counter and a door on its left.','physicalWorldRules':'The door does not move between views.'}},
        {'domain':'SUBJECTS','facts':{'presentSubjects':[
            {'subjectSelection':0,'role':'Courier','inSceneBehaviour':'WHOLE_COURIER_BEHAVIOR'},
            {'subjectSelection':1,'role':'Keeper','inSceneBehaviour':'WHOLE_KEEPER_BEHAVIOR'}]}},
        {'domain':'SOUND','facts':{'ambience':[{'design':'PERSISTENT_WIND'}], 'orderingRules':[],
            'contactTiedSound':[{'phaseIndex':phase,'design':'0–2s: one cloth contact at the receiving grip; no second impact.'}] if scoped_sound else 'UNSCOPED_CONTACT',
            'audio_events':[{'spokenSelection':0,'delivery_mode':'OFF_SCREEN',
                'performance':'2–5s: speak once over the continuing handoff.',
                'continuity':'5–8s: listen; do not repeat the line.'}]}},
        {'domain':'EDITORIAL','facts':{'temporalStructure':'WHOLE_TIME_SEQUENCE: wait then exchange.',
            'protectedEvents':[{'phaseIndex':phase,'design':'End after the receiving grip is secure and the appeal is heard; retain listening, no repeated transfer.'}]}}]
    return req,raw


async def pipeline(tmp_path, monkeypatch, req, raw, duration=8000):
    p = configured(monkeypatch,tmp_path)
    before = deepcopy(raw)
    designs = tuple(DesignBody.model_validate(d) for d in professional_projection(raw,req))
    validate_professional_facts(designs,req)
    assert raw == before
    refs=[]
    for kind,body,owner in ((Kind.SOURCE,req.source,Authority.SOURCE),(Kind.WORK,req.canon.work,Authority.CANON),
            (Kind.SCRIPT,req.canon.script,Authority.CANON),(Kind.SCENE,req.canon.scene,Authority.CANON),
            (Kind.SHOT,req.shot,Authority.DIRECTION)):
        refs.append(p.creative_versions.write(writer=owner,kind=kind,scope=req.scope,body=body,
            sources=tuple(refs),operation='scope-fixture:'+kind.value))
    core=tuple(refs)
    for design in designs:
        refs.append(p.creative_versions.write(writer=Authority.PROFESSIONAL,kind=Kind.PROFESSIONAL,
            scope=req.scope,body=design,sources=core,operation='scope-fixture:'+design.domain.value))
    native=NativeCreativeSources(p.creative_versions,tuple(refs))
    assembly=await ShotAssembler(native,ProfessionalDesignResolver(native)).assemble(req.scope,
        mode=RunMode.EXPERIMENT,policy_ref=ArtifactReference(owner='policy',artifact_ref='offline-fixture'))
    assert assembly.package, assembly.validation
    packages,artifacts=ProductionPackageStore(),GenerationArtifactStore()
    package=assembly.package; package_ref=packages.put(package)
    operations=OperationResolver(p.creative_versions,p.ledger,VideoRoutePolicy())
    reader=PackageReader(native,operations=operations)
    compiler=PromptCompiler(packages,artifacts,reader,_preview=True)
    pin=SourcePin(key='offline-unadmitted',kind='DESIGN',fingerprint='a'*64)
    decision=ArtifactReference(owner='offline-unadmitted',artifact_ref='no-production-permission')
    owners=OwnerBindings(adopted_refs=tuple(refs),dpd_pin=pin,performance_scope_pin=pin,rights_pin=pin,
        rights_request_ref=decision,rights_decision_ref=decision,adoption_decision_ref=decision)
    outputs=[]
    action=next(d for d in raw if d['domain']=='ACTION')['facts']['actionPhases']
    for phase in range(len(action)):
        profile=resolve_profile(model='seedance-2-standard',duration_ms=duration[phase] if isinstance(duration,list) else duration,resolution='720p',ratio='16:9',
            native_audio=True,mode='text_to_video',policy=operations.policy)
        unit=await operations.select_unit(package,reader,phase_index=phase)
        task=GenerationTask(unit=unit,profile=profile,owners=owners,native_audio='REQUIRED')
        result=await compiler.compile(package_ref,task)
        assert result.preparation_ref, artifacts.diagnostics(result.diagnostics_ref)
        ready=artifacts.get(result.preparation_ref,GenerationPreparation)
        final=artifacts.get(ready.final_prompt_ref,FinalPromptArtifact)
        wire=json.loads(json.dumps(TargetHttpTransport.preview(ready,final,ledger=p.ledger)))
        assert wire['content'][0]['text']==final.prompt_text
        assert not ready.provider_submission_allowed
        coverage=artifacts.get(final.coverage_ref,PromptCoverage)
        assert not any(e.status=='UNRESOLVED' for e in coverage.entries)
        outputs.append({'wire':wire,'ready':ready,'final':final,'coverage':coverage,'task':task})
    return p,compiler,package,outputs


@pytest.mark.asyncio
@pytest.mark.parametrize('single,scoped',[(False,True),(False,False),(True,False)])
async def test_final_wire_respects_scope_without_losing_identity_ambience_or_concurrency(tmp_path,monkeypatch,single,scoped):
    req,raw=material(single=single,scoped_sound=scoped)
    p,compiler,package,out=await pipeline(tmp_path,monkeypatch,req,raw)
    try:
        for i,row in enumerate(out):
            prompt=row['wire']['content'][0]['text']
            assert row['wire']['duration']==8 and '本段生成时长8秒' in prompt
            assert 'Courier' in prompt and 'Keeper' in prompt and prompt.count('PERSISTENT_WIND')==1
            assert ('WHOLE_COURIER_BEHAVIOR' in prompt)==single
            assert ('UNSCOPED_CONTACT' in prompt)==(single and not scoped)
            assert 'WHOLE_CAMERA_POLICY' not in prompt and 'FUTURE_CAMERA_EVENT' not in prompt
            assert ('WHOLE_TIME_SEQUENCE' in prompt)==single
            current=single or i==1
            assert ('{Помогите.}' in prompt)==current
            assert ('receiving grip; no second impact' in prompt)==(current and scoped)
            if current:
                assert prompt.count('{Помогите.}')==1
                assert '0–2s: the keeper supports' in prompt and '2–5s: the courier speaks while' in prompt
                assert '5–8s: the packet is supported' in prompt
                assert '2–5s: speak once' in prompt and '5–8s: listen' in prompt
                assert 'End after the receiving grip' in prompt
                assert '画外声音' in prompt
            else:
                assert '0–2s: both wait' in prompt
                assert 'while the courier loosens' not in prompt and 'End after the receiving grip' not in prompt
                assert any(e.status=='INTERNAL_ONLY' and e.source_ref.path[-1:] == ('inSceneBehaviour',) for e in row['coverage'].entries)
    finally: await p.aclose()


@pytest.mark.asyncio
async def test_single_policy_camera_and_automatic_duration_are_preserved(tmp_path,monkeypatch):
    req,raw=material(single=True)
    next(d for d in raw if d['domain']=='CAMERA')['facts']['movement'].pop('phaseDirections')
    p,compiler,package,out=await pipeline(tmp_path,monkeypatch,req,raw,duration=None)
    try:
        text=out[0]['wire']['content'][0]['text']
        assert 'WHOLE_CAMERA_POLICY' in text and '自动时长范围4–15秒' in text
        assert out[0]['wire']['duration']==-1 and '本段生成时长15秒' not in text
    finally: await p.aclose()


@pytest.mark.parametrize('fault',['top-performance','nested-subject','audio-window'])
def test_formal_contract_remains_closed(fault):
    req,raw=material()
    if fault=='top-performance': raw[1]['facts']['physicalExpression']='Invented extra lane'
    elif fault=='nested-subject': raw[4]['facts']['presentSubjects'][0]['inSceneBehaviour']={'phaseIndex':1,'design':'action'}
    else: raw[5]['facts']['audio_events'][0]['window_ms']=[0,4000]
    with pytest.raises(AuthorResultFailure): professional_projection(raw,req)


@pytest.mark.asyncio
async def test_explicit_current_behavior_and_sustained_contacts_keep_their_scopes(tmp_path,monkeypatch):
    req,raw=material()
    subjects=next(d for d in raw if d['domain']=='SUBJECTS')['facts']['presentSubjects']
    subjects.append({'subjectSelection':1,'role':'Keeper','phaseIndex':1,'inSceneBehaviour':'CURRENT_KEEPER_LISTENING'})
    sound=next(d for d in raw if d['domain']=='SOUND')['facts']
    sound['contactTiedSound'] += [{'phaseIndex':i,'design':'CONTINUOUS_APPROVED_CONTACT'} for i in (0,1)]
    # Two units can share the same primary Beat without sharing a contact sound.
    raw[0]['facts']['actionPhases'][0]['beatSelection']=1
    p,compiler,package,out=await pipeline(tmp_path,monkeypatch,req,raw)
    try:
        for i,row in enumerate(out):
            text=row['wire']['content'][0]['text']
            assert ('CURRENT_KEEPER_LISTENING' in text)==(i==1)
            assert text.count('CONTINUOUS_APPROVED_CONTACT')==1
            assert 'Keeper' in text and 'Courier' in text
            assert ('receiving grip; no second impact' in text)==(i==1)
    finally: await p.aclose()


@pytest.mark.asyncio
async def test_frozen_v5_read_view_and_new_cache_are_separate_without_relaxing_drift(tmp_path,monkeypatch):
    from drama_plugin.generation.contracts import AudioExecutionPlan
    from drama_plugin.generation.seedance import ModelPolicyCatalog
    req,raw=material()
    p,compiler,package,out=await pipeline(tmp_path,monkeypatch,req,raw)
    try:
        current=out[0]; task=current['task']; ready=current['ready']
        select=compiler.reader.operations.selected
        # Preview has deliberately unadmitted owners. Keep the real selection
        # and source comparison, bypass only production admission in this fixture.
        async def offline_selected(package,task,reader,**kw):
            return await select(package,task,reader,admission_required=False)
        monkeypatch.setattr(compiler.reader.operations,'selected',offline_selected)
        selected=await offline_selected(package,task,compiler.reader)
        plan=compiler.artifacts.get(ready.audio_plan_ref,AudioExecutionPlan)
        old_view=await compiler.projection.project(package,task,plan,selected,legacy_scope=True)
        old_policy=ModelPolicyCatalog().legacy_scope_policy(task.target_model)
        old_text=compiler.generator.generate(old_view.ir,plan,policy=old_policy,input_mode=task.input_mode)['prompt']
        assert 'WHOLE_COURIER_BEHAVIOR' in old_text and '本段生成时长' not in old_text
        old_final=FinalPromptArtifact.seal(**{**current['final'].model_dump(exclude={'fingerprint'}),
            'generator_policy_fingerprint':old_policy.fingerprint,'prompt_ir_fingerprint':old_view.ir.fingerprint,
            'prompt_text':old_text})
        old_ready=GenerationPreparation.seal(**{**ready.model_dump(exclude={'fingerprint'}),
            'final_prompt_ref':compiler.artifacts.put(old_final)})
        old_ref=compiler.artifacts.put(old_ready)
        assert (await compiler.prompt_ir(old_ready)).fingerprint==old_view.ir.fingerprint
        assert TargetHttpTransport.preview(old_ready,old_final,ledger=p.ledger)['content'][0]['text']==old_text
        assert compiler.stale(old_ref,package.artifact_reference(),task)
        rebuilt=await compiler.compile(package.artifact_reference(),task)
        assert compiler.artifacts.get(rebuilt.preparation_ref,GenerationPreparation).final_prompt_ref==ready.final_prompt_ref
        assert (await compiler.prompt_ir(ready)).fingerprint==current['final'].prompt_ir_fingerprint
        bad=FinalPromptArtifact.seal(**{**old_final.model_dump(exclude={'fingerprint'}),
            'generator_policy_fingerprint':'f'*64})
        bad_ready=GenerationPreparation.seal(**{**old_ready.model_dump(exclude={'fingerprint'}),
            'final_prompt_ref':compiler.artifacts.put(bad)})
        with pytest.raises(ValueError,match='OPERATION_PROJECTION_DRIFT'):
            await compiler.prompt_ir(bad_ready)
    finally: await p.aclose()
