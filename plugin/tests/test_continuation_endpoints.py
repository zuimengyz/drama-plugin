"""All creates are MockTransport. Actual wire, native owner and three phase coverage."""
import json
import subprocess
from pathlib import Path
import httpx
import pytest
from pydantic import SecretStr
from drama_plugin.execution.contracts import Authorization,ExecutionOperation,MediaBinding,ProviderAttempt,ContinuationFrame,ReviewObservation
from drama_plugin.execution.formal_media import FormalMediaStore
from drama_plugin.execution.live_transport import TargetHttpTransport,wire_payload
from drama_plugin.execution.review import ReviewResponse
from drama_plugin.film.assembly import scene_segments
from drama_plugin.generation.contracts import GenerationPreparation,FinalPromptArtifact,GenerationTask
from drama_plugin.generation.operation import validate_continuation,validate_segment_progress,validate_observed_speech
from drama_plugin.providers.video.adapters import SeedanceProvider
from drama_plugin.providers.video.registry import ProviderSettings
from drama_plugin.runtime.contracts import ArtifactReference,RuntimeState
from test_preparation_lifecycle_repair import ReferenceAuthors
from test_unified_planning_recovery import load as native_load,adopt_to_rights
from test_unified_mainline import MediaService,FAKE_SECRET
from test_native_scene_continuation import referenced_task


class ThreePhases(ReferenceAuthors):
    async def design(self,request):
        originals=await super().design(request)
        result=[]
        for design in originals:
            if design.domain=='ACTION':
                base=design.facts['actionPhases'][0]
                phases=[{**base,'action':f'Approved phase {i} action.', 'entryState':f'Phase {i} entry.', 'observable':f'Phase {i} exit.'} for i in range(3)]
                design=design.model_copy(update={'facts':{**design.facts,'actionPhases':phases}})
            elif design.domain=='CAMERA':
                design=design.model_copy(update={'facts':{**design.facts,'movement':{'policy':'Wide establishing view, then push closer.'}}})
            result.append(design)
        return tuple(result)


@pytest.fixture
def media_files(tmp_path):
    videos=[];images=[]
    for i,color in enumerate(('black','red','blue')):
        video=tmp_path/f'video-{i}.mp4'; image=tmp_path/f'tail-{i}.jpg'
        subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i',f'color=c={color}:s=1280x720:r=24:d=4',
            '-c:v','libx264','-pix_fmt','yuv420p','-y',str(video)],check=True,capture_output=True)
        subprocess.run(['ffmpeg','-nostdin','-v','error','-sseof','-0.05','-i',str(video),'-frames:v','1','-y',str(image)],check=True,capture_output=True)
        videos.append(video);images.append(image)
    return videos,images


async def scenario(tmp_path,monkeypatch,media_files,*,last_frame=True):
    videos,images=media_files
    p,authors=native_load(tmp_path,monkeypatch,ThreePhases())
    class UniqueMedia(MediaService):
        def handler(self,request):
            if request.url.path=='/media/list':
                source=request.url.params.get('source_ref')
                return httpx.Response(200,json=[r for r in self.records if not source or r['sourceRef']==source])
            response=super().handler(request)
            if request.url.path=='/media/import':
                self.records[-1]['id']=f'canonical-{self.imports}'
                return httpx.Response(200,json=self.records[-1])
            return response
    service=UniqueMedia(videos[0]);p.providers.media=service.provider()
    p.execution.media=FormalMediaStore(p.execution.media.directory,p.providers.media,p.execution.store)
    p.prompt_compiler.references.media_reader=p.providers.media
    calls=[];creates=[]
    def vendor(request):
        calls.append(request)
        if request.method=='POST':
            index=len(creates); creates.append(json.loads(request.content)); service.video=videos[index % len(videos)]
            content={'video_url':f'https://result.invalid/video-{index}.mp4'}
            if last_frame: content['last_frame_url']=f'https://result.invalid/tail-{index}.jpg'
            return httpx.Response(200,json={'id':f'task-{index}','status':'succeeded','content':content})
        if request.url.path.startswith('/video-'):
            return httpx.Response(200,content=videos[int(request.url.path[7:request.url.path.index('.mp4')]) % len(videos)].read_bytes())
        if request.url.path.startswith('/tail-'):
            return httpx.Response(200,content=images[int(request.url.path[6:request.url.path.index('.jpg')]) % len(images)].read_bytes())
        if '/contents/generations/tasks/' in request.url.path:
            index=int(request.url.path[-1]);content={'video_url':f'https://result.invalid/video-{index}.mp4'}
            if last_frame:content['last_frame_url']=f'https://result.invalid/tail-{index}.jpg'
            return httpx.Response(200,json={'id':f'task-{index}','status':'succeeded','content':content})
        raise AssertionError(str(request.url))
    async def no_reference(_):raise AssertionError('No extra reference generation')
    adapter=SeedanceProvider('seedance-2-fast',ProviderSettings(base_url='https://ark.cn-beijing.volces.com/api/v3',api_key=SecretStr(FAKE_SECRET)),
        resolve=no_reference,client=httpx.AsyncClient(transport=httpx.MockTransport(vendor)))
    p.execution.transports['seedance']=TargetHttpTransport(adapter,tmp_path/'acks',ledger=p.ledger,qualification_only=True)
    monkeypatch.setenv('DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS',str(tmp_path))
    run_id=await adopt_to_rights(p)
    parent=await p.runtime.run(run_id);cp=p.film.store.checkpoint(run_id)
    first=cp.units[0].generation_run_id
    auth=Authorization(approval_ref=ArtifactReference(owner='user-decision',artifact_ref='OFFLINE-SIMULATION'),authorized=True,
        budget_microunits=0,estimated_cost_microunits=0)
    p.ledger.put_index('media-proof-authorization',first,auth,scope=p.runtime.store.load(first).scope,once=True)
    await p.decide_target_run(run_id,decision_id=p.runtime.decision_id(run_id),accepted=True,source_ref=cp.units[0].package_ref)
    return p,run_id,service,calls,creates,auth,authors


def completion(p,child):
    with p.ledger.transaction() as db:
        row=db.execute('SELECT operation_ref_json FROM production_operation WHERE run_id=? AND operation_ref_json IS NOT NULL',(child,)).fetchone()
    op_ref=ArtifactReference.model_validate_json(row[0]);op=p.execution.store.get(op_ref,ExecutionOperation)
    cp=p.execution.store.checkpoint(op_ref)
    return op,cp,p.execution.store.get(cp.progress.video_ref,MediaBinding)


async def finish(p,child,package_ref,observations=()):
    run=await p.runtime.run(child)
    if run.state==RuntimeState.WAITING_USER and run.cursor==2:
        await p.decide_target_run(child,decision_id=p.runtime.decision_id(child),accepted=True,source_ref=package_ref)
        run=await p.runtime.run(child)
    assert run.state==RuntimeState.WAITING_USER and run.cursor==9,run.model_dump()
    op,cp,media=completion(p,child)
    context=p.execution.review_context(op,media.media,media.canonical_media_ref)
    done=await p.provide_human_media_review(child,media_ref=cp.progress.video_ref,context_hash=context,response=ReviewResponse('PASS',observations))
    assert done.state==RuntimeState.SUCCEEDED
    return op,cp,media,cp.progress.video_ref


async def following(p,run_id,service,first,phase,*,bind=True):
    cp=p.film.store.checkpoint(run_id);package=p.production_packages.get(cp.units[0].package_ref)
    first_op,first_cp,first_media=completion(p,first)
    from drama_plugin.contracts.media import Media
    base=p.generation_artifacts.get(first_op.preparation_ref,GenerationPreparation).task
    candidate=referenced_task(p,package,base,Media.model_validate(service.records[0]),first_cp.progress.video_creative_ref,
        binding_id='global-opening',mode='image_to_video')
    unit=await p.operation_resolver.select_unit(package,p.prompt_compiler.reader,phase_index=phase)
    unit=unit.model_copy(update={'reference_disposition':tuple((k,'INPUT' if v=='TECHNICAL_RISK_ACCEPTED' else v) for k,v in unit.reference_disposition)})
    candidate=candidate.model_copy(update={'unit':unit})
    return await p.prepare_source_film_continuation(run_id,task=candidate) if bind else candidate


@pytest.mark.asyncio
async def test_three_segments_advance_actual_wire_and_progress_and_idempotent_assembly(tmp_path,monkeypatch,media_files):
    p,r,service,calls,creates,auth,authors=await scenario(tmp_path,monkeypatch,media_files)
    cp=p.film.store.checkpoint(r);first=cp.units[0].generation_run_id;package_ref=cp.units[0].package_ref
    opening=await finish(p,first,package_ref);refs=[opening[3]];tasks=[];children=[]
    original=p.generation_artifacts.get(opening[0].preparation_ref,GenerationPreparation).model_dump_json()
    task=await following(p,r,service,first,1);tasks.append(task)
    later=await following(p,r,service,first,2,bind=False)
    compiled=await p.prompt_compiler.compile(package_ref,task)
    assert compiled.preparation_ref is not None,p.generation_artifacts.diagnostics(compiled.diagnostics_ref)
    child=p.create_media_review_run(package_ref=package_ref,task=task,offline_authorization=auth)
    batch=(task,later)
    ids=p.queue_source_film_media(r,tasks=batch);assert ids==(child.run_id,)
    assert p.queue_source_film_media(r,tasks=batch)==ids
    assert p.film.store.checkpoint(r).scene_media_pending_tasks==(later,)
    children.append(child.run_id)
    result=await finish(p,child.run_id,package_ref);refs.append(result[3])
    original_ready=p.generation_capability.on_ready
    def simulated_offline_authorization(run_id,ref):
        p.ledger.put_index('media-proof-authorization',run_id,auth,scope=p.runtime.store.load(run_id).scope,once=True)
        original_ready(run_id,ref)
    p.generation_capability.on_ready=simulated_offline_authorization
    waiting=await p.resume_source_film_run(r)
    cp=p.film.store.checkpoint(r)
    assert len(cp.scene_media_run_ids)==2 and not cp.scene_media_pending_tasks
    second=cp.scene_media_run_ids[-1];children.append(second)
    tasks.append(p.generation_artifacts.inputs(second).task)
    result=await finish(p,second,package_ref);refs.append(result[3])
    assert (await p.resume_source_film_run(r)).state==RuntimeState.SUCCEEDED
    assert p.queue_source_film_media(r,tasks=batch)==tuple(children)
    for child_id in children:
        posts=len(creates)
        assert (await p.runtime.recover_run(child_id)).state==RuntimeState.SUCCEEDED
        assert (await p.runtime.run(child_id)).state==RuntimeState.SUCCEEDED
        assert len(creates)==posts
    assert creates[0]['return_last_frame'] is True
    for i in (1,2):
        assert creates[i]['content'][1]=={'type':'image_url','image_url':{'url':f'https://result.invalid/tail-{i-1}.jpg'},'role':'first_frame'}
        assert not any(c.get('role')=='reference_video' for c in creates[i]['content'])
        assert creates[i]['return_last_frame'] is True
        assert 'Wide establishing view' not in creates[i]['content'][0]['text']
        assert f'Approved phase {i} action.' in creates[i]['content'][0]['text']
        assert f'Approved phase {i-1} action.' not in creates[i]['content'][0]['text']
    assert tasks[0].continuation.predecessor_media_ref==refs[0]
    assert tasks[1].continuation.predecessor_media_ref==refs[1]
    assert tasks[0].continuation.global_reference_ref==tasks[1].continuation.global_reference_ref
    assert tasks[0].execution_reference_refs!=tasks[1].execution_reference_refs
    assert [b.media.content_hash for _,b in scene_segments((*refs,refs[1],refs[2]),p.execution.store)]==[completion(p,c)[2].media.content_hash for c in (first,*children)]
    preview=p.source_film_preview_manifest(r)
    assert preview==p.source_film_preview_manifest(r) and preview.count("file '")==3
    assert p.generation_artifacts.get(opening[0].preparation_ref,GenerationPreparation).model_dump_json()==original
    assert len(creates)==3 and service.imports==3 and authors.calls==['canon','direction','professional']
    assert len(list((tmp_path/'acks').glob('*.wire.json')))==3
    captured=[json.loads(file.read_text()) for file in (tmp_path/'acks').glob('*.wire.json')]
    assert all(body in captured for body in creates)
    a,b,c=(p.generation_artifacts.get(completion(p,child)[0].preparation_ref,GenerationPreparation).task.unit
        for child in (first,*children))
    a=a.model_copy(update={'spoken_ids':('approved-line-0',)})
    b=b.model_copy(update={'spoken_ids':('approved-line-1',)})
    c=c.model_copy(update={'spoken_ids':('approved-line-2',)})
    validate_segment_progress(c,(b,a))
    with pytest.raises(ValueError,match='SPEECH_COMPLETION_UNVERIFIED'):
        validate_observed_speech(a,(ReviewObservation(code='AUDIO_NOT_VERIFIED',owner='reviewer',finding='Visual-only observation.'),))
    validate_observed_speech(a,(ReviewObservation(code='SPOKEN_CONTENT_COVERAGE_VERIFIED',owner='offline-reviewer',
        finding='Offline speech coverage fixture only.',verified_spoken_ids=a.spoken_ids),))
    with pytest.raises(ValueError,match='CONTENT_OVERLAP'):
        validate_segment_progress(c.model_copy(update={'spoken_ids':('approved-line-0',)}),(b,a))
    with pytest.raises(ValueError,match='PROGRESS_REPEAT_OR_SKIP'):
        validate_segment_progress(c,(a,))
    with pytest.raises(ValueError,match='PROGRESS_REPEAT_OR_SKIP'):
        validate_continuation(p.ledger,tasks[0].model_copy(update={'unit':tasks[1].unit}))
    with pytest.raises(ValueError,match='PREDECESSOR'):
        scene_segments((refs[0],refs[2]),p.execution.store)
    with pytest.raises(ValueError,match='IMMEDIATE_REVIEWED_PREDECESSOR|EXISTING_FILM_EXECUTION_BOUNDARY'):
        p.queue_source_film_media(r,tasks=(tasks[0],))


@pytest.mark.asyncio
async def test_missing_official_tail_does_not_fallback_or_create(tmp_path,monkeypatch,media_files):
    p,r,service,calls,creates,auth,authors=await scenario(tmp_path,monkeypatch,media_files,last_frame=False)
    cp=p.film.store.checkpoint(r);first=cp.units[0].generation_run_id
    await finish(p,first,cp.units[0].package_ref)
    with pytest.raises(RuntimeError,match='PROVIDER_LAST_FRAME_UNAVAILABLE'):
        await following(p,r,service,first,1)
    assert len(creates)==1 and sum(c.method=='GET' and '/contents/generations/tasks/' in c.url.path for c in calls)==1
    assert not p.film.store.checkpoint(r).scene_media_run_ids


@pytest.mark.asyncio
async def test_new_batch_keeps_old_authority_and_uses_only_new_official_endpoints(tmp_path,monkeypatch,media_files):
    from drama_plugin.film.contracts import FilmMediaBatch
    from drama_plugin.contracts.media import Media
    from drama_plugin.runtime.contracts import DecisionCategory
    p,r,service,calls,creates,auth,authors=await scenario(tmp_path,monkeypatch,media_files)
    old_cp=p.film.store.checkpoint(r)
    old_first=old_cp.units[0].generation_run_id
    old_op,old_progress,old_media,_=await finish(p,old_first,old_cp.units[0].package_ref)
    assert (await p.resume_source_film_run(r)).state==RuntimeState.SUCCEEDED
    old_cp=p.film.store.checkpoint(r)
    old_progress=p.execution.store.checkpoint(old_op.artifact_reference())
    old_run=p.runtime.store.load(r)
    old_bytes=old_op.model_dump_json()
    base=p.generation_artifacts.get(old_op.preparation_ref,GenerationPreparation).task
    opening=referenced_task(p,p.production_packages.get(old_cp.units[0].package_ref),base,
        Media.model_validate(service.records[0]),old_progress.progress.video_creative_ref,
        binding_id='test-unused-context',mode='text_to_video')
    opening=opening.model_copy(update={'execution_reference_refs':None,'return_last_frame':True})
    later=[]
    for phase in (1,2):
        candidate=await following(p,r,service,old_first,phase,bind=False)
        later.append(candidate.model_copy(update={'execution_reference_refs':None,'return_last_frame':True}))
    original_ready=p.generation_capability.on_ready
    def offline_authorize(child,ref):
        p.ledger.put_index('media-proof-authorization',child,auth,scope=p.runtime.store.load(child).scope,once=True)
        original_ready(child,ref)
    p.generation_capability.on_ready=offline_authorize
    batch=(opening,*later)
    compiled=await p.prompt_compiler.compile(old_cp.units[0].package_ref,opening)
    cached=p.generation_artifacts.get(compiled.preparation_ref,GenerationPreparation)
    # Shared cache versions must not be selected by a PLANNED child's inspector.
    alternative=GenerationPreparation.seal(**{**cached.model_dump(exclude={'fingerprint'}),
        'final_prompt_ref':ArtifactReference(owner='final-prompt',artifact_ref='offline-other-cache-version',version=1)})
    p.generation_artifacts.put(alternative)
    original_technical=p.execution._technical
    def old_container_policy(op,checkpoint,media,recipe,*,audio_expected):
        from drama_plugin.execution.contracts import TechnicalMediaReview
        result=original_technical(op,checkpoint,media,recipe,audio_expected=audio_expected)
        return TechnicalMediaReview.seal(**{**result.model_dump(exclude={'fingerprint'}),
            'policy_version':'technical-media-v1','outcome':'FAIL','findings':('RESULT_DURATION_MISMATCH',)})
    p.execution._technical=old_container_policy
    failed=await p.restart_source_film_media(r,batch_id='new-official-frame-batch',tasks=batch,allow_unverified_audio=True)
    assert failed.state==RuntimeState.FAILED and failed.last_result.code=='TECHNICAL_MEDIA_FAILURE'
    p.execution._technical=original_technical
    await p.resume_source_film_run(r)
    fresh_first=p.source_film_media_opening(r)
    _,repaired_cp,_=completion(p,fresh_first)
    from drama_plugin.execution.contracts import TechnicalMediaReview
    old_qa=p.execution.store.get(repaired_cp.progress.video_technical_ref,TechnicalMediaReview)
    new_qa=p.execution.store.get(repaired_cp.progress.current_video_technical_ref,TechnicalMediaReview)
    assert old_qa.outcome=='FAIL' and new_qa.outcome=='PASS' and new_qa.supersedes_ref==old_qa.artifact_reference()
    assert p.runtime.store.load(r).external_repairs[-1].failed_result==failed.last_result
    cp=p.film.store.checkpoint(r)
    record=p.film.store.get(cp.media_batch_ref,FilmMediaBatch)
    new_first=p.source_film_media_opening(r)
    assert record.previous_checkpoint==old_cp
    assert new_first != old_first and cp.units==old_cp.units and cp.operation_task==old_cp.operation_task
    assert not cp.scene_media_run_ids and len(cp.scene_media_pending_tasks)==2
    assert p.runtime.store.load(r).execution_batches[0].completed_result==old_run.last_result
    # A restart replay at this approval wait cannot regenerate the opening or freeze the next child.
    before=len(creates)
    await p.restart_source_film_media(r,batch_id='new-official-frame-batch',tasks=batch,allow_unverified_audio=True)
    assert len(creates)==before
    with pytest.raises(ValueError,match='IDENTITY_CHANGED'):
        await p.restart_source_film_media(r,batch_id='new-official-frame-batch',tasks=(opening,*reversed(later)),allow_unverified_audio=True)
    results=[]
    for index in range(3):
        cp=p.film.store.checkpoint(r)
        child=p.source_film_media_opening(r) if index==0 else cp.scene_media_run_ids[-1]
        pending=(ReviewObservation(code='SPOKEN_CONTENT_COVERAGE_UNVERIFIED',owner='offline-observer',finding='Coverage remains pending under explicit bounded policy.'),)
        results.append(await finish(p,child,old_cp.units[0].package_ref,pending if index==0 else ()))
        # Final segment is retained without needing a fourth segment.
        await p.retain_source_film_last_frame(child)
        count=len(creates)
        await p.retain_source_film_last_frame(child)
        assert len(creates)==count
        if index==0:
            # Reproduce the compiler boundary that omitted the authorized policy.
            original_resolve=p.prompt_compiler.references.resolve
            async def omitted_policy(package,task,selected,*,subjects):
                assert task.continuation.allow_unverified_audio
                raise ValueError('CONTINUATION_SPEECH_COMPLETION_UNVERIFIED')
            p.prompt_compiler.references.resolve=omitted_policy
            blocked=await p.resume_source_film_run(r)
            assert blocked.state==RuntimeState.FAILED and blocked.last_result.code=='GOVERNED_HARD_STOP'
            assert len(creates)==count
            p.prompt_compiler.references.resolve=original_resolve
            await p.resume_source_film_run(r)
            repaired=p.runtime.store.load(r)
            assert repaired.external_repairs[-1].failed_result==blocked.last_result
            assert repaired.external_repairs[-1].batch_ref==cp.media_batch_ref
        else:
            await p.resume_source_film_run(r)
    assert p.runtime.store.load(r).state==RuntimeState.SUCCEEDED
    assert len(creates)==4
    assert len(creates[1]['content'])==1 and creates[1]['return_last_frame'] is True
    assert creates[2]['content'][1]['image_url']['url']=='https://result.invalid/tail-1.jpg'
    assert creates[3]['content'][1]['image_url']['url']=='https://result.invalid/tail-2.jpg'
    assert not any('tail-0.jpg' in str(body) or 'video-0.mp4' in str(body) for body in creates[1:])
    assert p.execution.store.get(old_op.artifact_reference(),ExecutionOperation).model_dump_json()==old_bytes
    assert p.film.store.checkpoint(r).units==old_cp.units
    assert p.source_film_preview_manifest(r).count("file '")==3
    assert authors.calls==['canon','direction','professional']
    assert service.imports==3  # Exact repeated mock bytes reuse formal Media; all four logical results remain.
    final_ref=ArtifactReference.model_validate(p.ledger.get_index('continuation-frame',results[-1][3].artifact_ref))
    assert p.execution.store.get(final_ref,ContinuationFrame).media.content_hash==__import__('hashlib').sha256(media_files[1][0].read_bytes()).hexdigest()
    count=len(creates)
    await p.restart_source_film_media(r,batch_id='new-official-frame-batch',tasks=batch,allow_unverified_audio=True)
    await p.resume_source_film_run(r)
    assert len(creates)==count


def test_unverified_audio_requires_explicit_policy_and_does_not_become_verified():
    from types import SimpleNamespace
    from drama_plugin.generation.operation import validate_predecessor_speech
    unit=SimpleNamespace(spoken_ids=('canonical-line',))
    pending=(ReviewObservation(code='SPOKEN_CONTENT_COVERAGE_UNVERIFIED',owner='observer',finding='Unreliable blind observation; coverage remains pending.'),)
    with pytest.raises(ValueError,match='SPEECH_COMPLETION_UNVERIFIED'):
        validate_predecessor_speech(unit,pending)
    validate_predecessor_speech(unit,pending,allow_unverified_audio=True)
    with pytest.raises(ValueError,match='SPEECH_COMPLETION_UNVERIFIED'):
        validate_observed_speech(unit,pending)
    missing=ReviewObservation(code='SPOKEN_CONTENT_MISSING',owner='observer',finding='Reliable observation of omitted canonical words.')
    with pytest.raises(ValueError,match='SPEECH_COMPLETION_UNVERIFIED'):
        validate_predecessor_speech(unit,(*pending,missing),allow_unverified_audio=True)


@pytest.mark.asyncio
async def test_review_protocol_recovery_retains_revise_and_stops_next_create(tmp_path,monkeypatch,media_files):
    p,r,service,calls,creates,auth,authors=await scenario(tmp_path,monkeypatch,media_files)
    old=p.film.store.checkpoint(r);old_first=old.units[0].generation_run_id
    op,_,_,_=await finish(p,old_first,old.units[0].package_ref)
    assert (await p.resume_source_film_run(r)).state==RuntimeState.SUCCEEDED
    from drama_plugin.contracts.media import Media
    base=p.generation_artifacts.get(op.preparation_ref,GenerationPreparation).task
    progress=p.execution.store.checkpoint(op.artifact_reference()).progress
    opening=referenced_task(p,p.production_packages.get(old.units[0].package_ref),base,
        Media.model_validate(service.records[0]),progress.video_creative_ref,binding_id='review-test-unused-context',mode='text_to_video').model_copy(
            update={'execution_reference_refs':None,'return_last_frame':True})
    later=[]
    for i in (1,2):
        later.append((await following(p,r,service,old_first,i,bind=False)).model_copy(
            update={'execution_reference_refs':None,'return_last_frame':True}))
    original_ready=p.generation_capability.on_ready
    def simulated(child,ref):
        p.ledger.put_index('media-proof-authorization',child,auth,scope=p.runtime.store.load(child).scope,once=True)
        original_ready(child,ref)
    p.generation_capability.on_ready=simulated
    await p.restart_source_film_media(r,batch_id='review-protocol-repair',tasks=(opening,*later))
    first=p.source_film_media_opening(r)
    await finish(p,first,old.units[0].package_ref)
    await p.resume_source_film_run(r)
    second=p.film.store.checkpoint(r).scene_media_run_ids[-1]
    class BadResponse:
        identity='scoped-observed-reviewer';policy_version='offline-protocol-test'
        async def review(self,*args,**kwargs):return ReviewResponse('FAIL')
    p.execution.reviewer=BadResponse()
    await p.runtime.reconcile_wait(second)
    await p.runtime.run(second)
    failed=await p.resume_source_film_run(r)
    assert failed.state==RuntimeState.FAILED and failed.last_result.code=='HUMAN_REVIEW_CONTEXT_MISMATCH'
    failed_child=p.runtime.store.load(second)
    count=len(creates)
    class ValidRevision(BadResponse):
        async def review(self,*args,**kwargs):
            return ReviewResponse('REVISE',(ReviewObservation(code='CAMERA_CONTINUITY_REGRESSION',owner='shot-production',
                finding='Actual camera moved wider; stop the next clip.',required_revision='Replace failed generated continuation while preserving the adopted framing and script; do not create the next clip.'),))
    p.execution.reviewer=ValidRevision()
    resumed=await p.resume_source_film_run(r)
    assert resumed.state==RuntimeState.WAITING_USER
    assert len(creates)==count==3  # One old, two new; third new is never created.
    cp=p.film.store.checkpoint(r)
    assert len(cp.scene_media_run_ids)==1 and len(cp.scene_media_pending_tasks)==1
    _,progress,media=completion(p,second)
    from drama_plugin.execution.contracts import CreativeMediaReview
    review=p.execution.store.get(progress.progress.video_creative_ref,CreativeMediaReview)
    assert review.outcome=='REVISE' and review.media==media.media
    assert p.runtime.store.load(second).external_repairs[-1].failed_result==failed_child.last_result
    assert p.runtime.store.load(r).external_repairs[-1].failed_result==failed.last_result
    await p.resume_source_film_run(r)
    assert len(creates)==count


def test_video_duration_check_uses_picture_track_and_checks_av_alignment(monkeypatch):
    from types import SimpleNamespace
    from drama_plugin.execution.contracts import ProbeObservation
    from drama_plugin.execution.media import inspect
    import drama_plugin.execution.media as module
    source=SimpleNamespace(kind='VIDEO',mime='video/mp4')
    store=SimpleNamespace(path=lambda _:Path('/offline-media'))
    observed=ProbeObservation(container='mp4',duration_ms=15104,video_duration_ms=15042,audio_duration_ms=15104,
        width=1280,height=720,video_codec='h264',audio_codec='aac')
    monkeypatch.setattr(module,'probe',lambda _:observed)
    assert inspect(store,source,duration_ms=15000,tolerance_ms=100,audio_expected=True)[1]==()
    observed=observed.model_copy(update={'video_duration_ms':15200})
    assert 'RESULT_DURATION_MISMATCH' in inspect(store,source,duration_ms=15000,tolerance_ms=100,audio_expected=True)[1]
    observed=observed.model_copy(update={'video_duration_ms':15042,'audio_duration_ms':16000})
    assert 'RESULT_AV_DURATION_MISMATCH' in inspect(store,source,duration_ms=15000,tolerance_ms=100,audio_expected=True)[1]
