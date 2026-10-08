"""Native source-to-reviewed-media:v1, real compiler and MockTransport only."""
import json
import pytest
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.creative_engine.contracts import Kind, Dialogue, SceneBody
from drama_plugin.film.contracts import CanonScene, DirectedShot
from drama_plugin.generation.contracts import GenerationTask, OwnerBindings, GenerationPreparation, FinalPromptArtifact
from drama_plugin.generation.operation import resolve_profile, validate_segment_progress
from drama_plugin.persistence.review import UserDecisionRecord
from drama_plugin.runtime.contracts import ArtifactReference, DecisionCategory, RuntimeState
from test_continuation_endpoints import scenario, finish, completion, media_files
from test_preparation_lifecycle_repair import ReferenceAuthors
from test_design_reconciliation import location


class BoundaryAuthors(ReferenceAuthors):
    def __init__(self, *, transition='cut', montage=False, voice=False, room_phases=1, school_phases=1):
        super().__init__(); self.transition=transition; self.montage=montage; self.voice=voice
        self.room_phases=room_phases;self.school_phases=school_phases
    def bind_store(self, store):
        raw=location('interior',scenes=('room','return-room'),identity='same-attic').model_dump(mode='json',by_alias=True)
        raw.update(name='Approved attic',timeOfDay='Night',zoneLayout={'A':'armchair','B':'window','C':'door'})
        self.place=store.put('approved-attic',raw)
    async def author_film(self, request):
        value=await super().author_film(request)
        scenes=[]
        for sid in ('room','school','return-room'):
            dialogue=(Dialogue(id='school-voice',speaker='actor',text='Я был смешон.'),) if sid=='school' and self.voice else ()
            scenes.append(CanonScene(scene_id=sid,scene=SceneBody(scene_text='Approved '+sid+' action.',dialogue=dialogue)))
        return value.model_copy(update={'scenes':tuple(scenes)})
    async def direct_film(self, request):
        value=await super().direct_film(request); base=value.shots[0].shot
        shots=[]
        for sid in ('room','school','return-room'):
            spoken=('school-voice',) if sid=='school' and self.voice else ()
            shots.append(DirectedShot(scene_id=sid,shot_id=sid+'-shot',transition=self.transition if sid=='school' else 'cut',
                shot=base.model_copy(update={'spoken_ids':spoken,'editing_relation':'Hard-cut montage of authored ages.' if self.montage and sid=='school' else 'Approved '+self.transition+' at current event.',
                    'required_transition':'Approved '+self.transition+' to '+sid+'.'})))
        return value.model_copy(update={'shots':tuple(shots)})
    async def design(self, request):
        designs=await super().design(request); sid=request.scope.scene_id; result=[]
        phases=['Daylight school environment, boy narrator.','University environment, young narrator.','Adult street environment.'] if self.montage and sid=='school' else ['Night attic room, adult narrator.' if sid=='room' else 'Dawn attic room, adult narrator.' if sid=='return-room' else 'Daylight school environment, boy narrator.']
        if sid=='room': phases=[phases[0]+f' Approved room event {i}.' for i in range(self.room_phases)]
        if sid=='school' and not self.montage: phases=[phases[0]+f' Approved school event {i}.' for i in range(self.school_phases)]
        for d in designs:
            facts=dict(d.facts)
            if d.domain=='ACTION':
                base=facts['actionPhases'][0]
                facts['actionPhases']=[{**base,'entryState':entry,'action':'Execute only '+entry,'observable':'End '+entry,
                    'spokenIds':['school-voice'] if self.voice and sid=='school' and i==0 else []} for i,entry in enumerate(phases)]
            if d.domain=='SUBJECTS':
                facts['identityConstraints']='Same person actor across ages; current face age is not proven by an adult video.'
            if d.domain=='WORLD':
                facts.update(setting='School corridor, university hall, adult urban street.' if sid=='school' else 'Approved attic room.',time='Daylight' if sid=='school' else 'Dawn' if sid=='return-room' else 'Night')
                if sid!='school':
                    facts['locationBinding']={'locationRef':{'locationId':'same-attic','artifactRef':self.place.model_dump(mode='json',by_alias=True)},
                        'localOverride':{'timeOfDay':'Dawn' if sid=='return-room' else 'Night','changeReason':'Current scene narrative time.','continuityNote':'Room structure remains fixed.'}}
            if d.domain=='SOUND':
                facts.update(ambience=[{'design':'School ambience.'},{'design':'University ambience.'},{'design':'Adult street ambience.'}] if sid=='school' else [{'design':'Room quiet.'}],
                    dialogueAndLegibility='Adult retrospective voiceover remains clear above ambience.',acousticSpace='School corridor, university hall, street open air.' if sid=='school' else 'Room quiet.')
            if d.domain=='PERFORMANCE' and self.voice and sid=='school':
                facts['lines']=[{'spokenContentId':'school-voice','beatId':'beat-1','dramaticAction':'Recall childhood from adulthood.','observableIntent':'Reflect without lip-sync.',
                    'continuity':'Adult retrospective voice.','changeFromPrevious':'Current school memory.'}]
                facts['projectionSubjects']=[{**row,'spokenIds':['school-voice']} for row in facts['projectionSubjects']]
            result.append(d.model_copy(update={'facts':facts}))
        return tuple(result)


@pytest.mark.asyncio
async def test_observed_adult_identity_excludes_forbidden_child_age_in_native_cut(tmp_path,monkeypatch,media_files):
    from drama_plugin.film.media_references import observed_identity_ages
    facts={'identityObservationSource':{'sha256':'a'*64},
           'identityConstraints':'同一成年叙述者，约四十岁；从参考视频最后特写识别本场同一主角，沿用无帽短发；不变成少年或另一个人。'}
    assert observed_identity_ages(facts)=={'adult'}
    assert observed_identity_ages({'identityConstraints':facts['identityConstraints']})==set()
    class ObservedAdult(BoundaryAuthors):
        async def design(self,request):
            result=[]
            for d in await super().design(request):
                if request.scope.scene_id=='room' and d.domain=='SUBJECTS':
                    d=d.model_copy(update={'facts':{**d.facts,**facts}})
                if request.scope.scene_id=='room' and d.domain=='ACTION':
                    phases=[{**row,'entryState':'Narrator in the room.','transition':'cut'}
                            for row in d.facts['actionPhases']]
                    d=d.model_copy(update={'facts':{**d.facts,'actionPhases':phases}})
                result.append(d)
            return tuple(result)
    p,r,_,_,creates,auth,_=await scenario(tmp_path,monkeypatch,media_files,authors=ObservedAdult(room_phases=3))
    cp=p.film.store.checkpoint(r);unit=cp.units[0];first=unit.generation_run_id
    await finish(p,first,unit.package_ref);adopt_media(p,r,first);await p.resume_source_film_run(r)
    child,task=await execute(p,r,await descriptor(p,r,unit,1,mode='reference'),unit,auth)
    assert task.boundary.kind=='CUT' and task.continuation is None
    assert task.execution_reference_refs
    assert any(c['type']=='video_url' for c in creates[-1]['content'])
    assert not any(c.get('role')=='first_frame' for c in creates[-1]['content'])
    assert '最后特写' in creates[-1]['content'][0]['text'] and '沿用无帽短发' in creates[-1]['content'][0]['text']
    assert p.runtime.store.load(child).state==RuntimeState.SUCCEEDED


def adopt_media(p,r,child):
    _,cp,_=completion(p,child)
    receipt=UserDecisionRecord.seal(run_id=child,scope=p.runtime.store.load(child).scope,
        decision_id=child+':adopt-current',category=DecisionCategory.ADOPTION,accepted=True,source_ref=cp.progress.video_ref)
    p.reviews.put_user_decision(receipt)


@pytest.mark.asyncio
async def test_user_accepts_known_revise_without_erasing_review_or_requeue(tmp_path,monkeypatch,media_files):
    from drama_plugin.execution.contracts import CreativeMediaReview,ReviewObservation
    from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
    p,r,_,_,_,_,_=await scenario(tmp_path,monkeypatch,media_files,authors=BoundaryAuthors())
    cp=p.film.store.checkpoint(r);first=cp.units[0].generation_run_id
    await finish(p,first,cp.units[0].package_ref)
    p.select_source_film_working_input(r,child_id=first)
    _,check,media=completion(p,first)
    original=p.execution.store.get(check.progress.video_creative_ref,CreativeMediaReview)
    later=CreativeMediaReview.seal(**{**original.model_dump(exclude={'fingerprint'}),
        'reviewer':'HOST-final-playback','policy_version':'final-playback-v2','outcome':'REVISE',
        'adoption_recommendation':'REVISION_REQUIRED','supersedes_ref':check.progress.video_creative_ref,
        'observations':(ReviewObservation(code='MODERN_BACKGROUND',owner='HOST-final-playback',
            finding='Known modern sign.',required_revision='Revise unless this version is explicitly adopted.'),)})
    retained=p.record_source_film_candidate_reassessment(r,child_id=first,review=later)
    assert p.source_film_production_progress(r)['nextUnit']['sceneId']=='room'
    adopt_media(p,r,first)
    from drama_plugin.film.media_units import adoption_receipts
    receipt=next(x for x in adoption_receipts(p) if x.run_id==first)
    record={'scope':media.scope.model_dump(mode='json',by_alias=True),'taskState':'ARCHIVED_AND_CLOSED',
        'formalAdoptionRecords':[{'sourceRef':check.progress.video_ref.model_dump(mode='json',by_alias=True),
            'decisionRef':receipt.artifact_reference().model_dump(mode='json',by_alias=True)}],
        'userAdoption':'USER_SELECTED','russianVerification':'UNVERIFIED','remotePersistence':'LOCAL_ONLY',
        'subtitleDelivery':'COMPLETE_CLEAN','acceptedFindings':[{'code':'MODERN_BACKGROUND'}],
        'revisionDisposition':'CLOSED_BY_USER_KEEP_CURRENT_VERSION'}
    store=DirectorArtifactStore(p.ledger.path.parent/'subtitle-authority')
    store.put('known-findings-user-accepted',record)
    progress=p.source_film_production_progress(r)
    assert progress['scenes'][0]['writtenContentCovered'] and progress['scenes'][0]['productionContentCovered']
    assert progress['nextUnit']['sceneId']=='school'
    row=progress['mediaIndex'][0]
    assert row['adoption']=='USER_SELECTED' and row['creativeReviewOutcome']=='REVISE'
    assert progress['archives'][0]['subtitleDelivery']=='COMPLETE_CLEAN'
    assert progress['archives'][0]['acceptedFindings']==[{'code':'MODERN_BACKGROUND'}]
    assert p.execution.store.get(retained,CreativeMediaReview)==later
    assert p.execution.store.get(check.progress.video_creative_ref,CreativeMediaReview)==original
    assert not progress['filmContentComplete']
    from drama_plugin.film.media_references import select_references
    selection=await p.operation_resolver.select_unit(p.production_packages.get(cp.units[1].package_ref),p.prompt_compiler.reader)
    reuse=select_references(p,r,cp.units[1],selection)
    assert not reuse['candidates']
    assert reuse['excludedSources'][0]['sourceRunId']==first


@pytest.mark.asyncio
@pytest.mark.parametrize('adopted',[False,True])
async def test_native_final_playback_reassessment_preserves_generation_and_prior_review(tmp_path,monkeypatch,media_files,adopted):
    from drama_plugin.execution.contracts import CreativeMediaReview,ReviewObservation
    p,r,_,_,creates,_,_=await scenario(tmp_path,monkeypatch,media_files,authors=BoundaryAuthors())
    cp=p.film.store.checkpoint(r);first=cp.units[0].generation_run_id
    await finish(p,first,cp.units[0].package_ref)
    p.select_source_film_working_input(r,child_id=first)
    _,check,_=completion(p,first)
    original=p.execution.store.get(check.progress.video_creative_ref,CreativeMediaReview)
    frozen=original.model_dump_json();before=p.runtime.store.load(first)
    assert 'supersedesRef' not in original.model_dump(mode='json',by_alias=True)
    later=CreativeMediaReview.seal(**{**original.model_dump(exclude={'fingerprint'}),
        'reviewer':'HOST-final-playback','policy_version':'final-playback-v2','outcome':'REVISE',
        'adoption_recommendation':'REVISION_REQUIRED','supersedes_ref':check.progress.video_creative_ref,
        'observations':(ReviewObservation(code='MODERN_BACKGROUND',owner='HOST-final-playback',
            finding='Final playback exposes a modern sign.',required_revision='Revise this unadopted unit; retain its original evidence.'),)})
    if adopted:
        adopt_media(p,r,first)
        with pytest.raises(ValueError,match='USER_ADOPTED_MEDIA'):
            p.record_source_film_candidate_reassessment(r,child_id=first,review=later)
    else:
        ref=p.record_source_film_candidate_reassessment(r,child_id=first,review=later)
        assert p.record_source_film_candidate_reassessment(r,child_id=first,review=later)==ref
        progress=p.source_film_production_progress(r)
        row=next(v for v in progress['mediaIndex'] if v['runId']==first)
        assert row['generationState']=='SUCCEEDED' and row['productionSelection']=='REVISION_REQUIRED'
        assert row['creativeReviewOutcome']=='REVISE' and row['creativeReviewRef']==ref.model_dump(mode='json',by_alias=True)
        assert not progress['scenes'][0]['productionContentCovered']
        assert progress['nextUnit']['sceneId']=='room'
        with pytest.raises(ValueError,match='REVIEWED_PERSISTED'):
            p.select_source_film_working_input(r,child_id=first)
        wrong=CreativeMediaReview.seal(**{**later.model_dump(exclude={'fingerprint'}),'run_id':'other-child'})
        with pytest.raises(ValueError,match='REASSESSMENT_SCOPE_MISMATCH'):
            p.record_source_film_candidate_reassessment(r,child_id=first,review=wrong)
    assert p.execution.store.get(check.progress.video_creative_ref,CreativeMediaReview).model_dump_json()==frozen
    assert p.runtime.store.load(first)==before and len(creates)==1


async def descriptor(p,r,unit,phase=0,mode='text_to_video',spoken_range=None,allow_unverified_audio=False):
    cp=p.film.store.checkpoint(r); pkg=p.production_packages.get(unit.package_ref)
    base=cp.operation_task
    profile=resolve_profile(model=base.profile.model,duration_ms=4000,resolution='720p',ratio='16:9',native_audio=base.profile.native_audio,mode=mode,policy=p.operation_resolver.policy)
    selection=await p.operation_resolver.select_unit(pkg,p.prompt_compiler.reader,phase_index=phase,spoken_range=spoken_range)
    if any(v=='TECHNICAL_RISK_ACCEPTED' for _,v in selection.reference_disposition):
        acceptance=UserDecisionRecord.seal(run_id=r,scope=p.runtime.store.load(r).scope,
            decision_id=r+':offline-selection-'+selection.terms_hash(unit.package_ref),
            category=DecisionCategory.ART_APPROVAL,accepted=True,source_ref=unit.package_ref,
            terms_hash=selection.terms_hash(unit.package_ref))
        selection=selection.model_copy(update={'scope_decision_ref':p.reviews.put_user_decision(acceptance)})
    shot=next(p.creative_versions.resolve(ref) for ref in unit.refs if p.creative_versions.resolve(ref).kind==Kind.SHOT)
    dpd,projection,snapshots=p.operation_resolver.compose_performance(unit.refs)
    old=p.creative_versions.objects.read_ref(base.owners.rights_pin)
    refs=[ref.model_dump(mode='json',by_alias=True) for ref in unit.refs if p.creative_versions.resolve(ref).kind!=Kind.PROFESSIONAL]
    material={**old,'scope':shot.scope.model_dump(mode='json',by_alias=True),'adoptedRefs':refs,
        'creativeAdoptionDecisionRef':shot.adoption_decision_ref.model_dump(mode='json',by_alias=True),
        'dpdBindingRef':{'owner':'dpd-core','artifactRef':'dpd-binding:'+dpd.fingerprint,'version':1},
        'profile':profile.model_dump(mode='json',by_alias=True),'processingScope':{**old['processingScope'],'mode':mode,**({'allowUnverifiedNativeAudio':True} if allow_unverified_audio else {})}}
    for key in ('requestRef','decisionRef','externalProcessingAuthorized'):material.pop(key,None)
    pin=p.creative_versions.objects.put('offline-rights-'+sha256_canonical(material),material)
    request=ArtifactReference(owner='source-owner',artifact_ref=pin.key,version=1)
    decision=UserDecisionRecord.seal(run_id=r,scope=p.runtime.store.load(r).scope,decision_id=r+':offline-'+pin.fingerprint,
        category=DecisionCategory.ADOPTION,accepted=True,source_ref=request)
    receipt=p.reviews.put_user_decision(decision)
    rights=p.creative_versions.objects.put('offline-approved-'+pin.fingerprint,{**material,'externalProcessingAuthorized':True,
        'requestRef':request.model_dump(mode='json',by_alias=True),'decisionRef':receipt.model_dump(mode='json',by_alias=True)})
    owners=OwnerBindings(adopted_refs=unit.refs,dpd_pin=dpd,performance_scope_pin=projection,snapshot_pins=snapshots,
        rights_pin=rights,rights_request_ref=request,rights_decision_ref=receipt,adoption_decision_ref=shot.adoption_decision_ref)
    return GenerationTask(target_model=profile.model,input_mode=mode,native_audio='REQUIRED' if profile.native_audio else 'DISABLED',profile=profile,unit=selection,owners=owners,return_last_frame=True)


async def execute(p,r,task,unit,auth):
    task=await p.prepare_source_film_unit(r,task=task)
    child=p.create_media_review_run(package_ref=unit.package_ref,task=task,offline_authorization=auth)
    ids=p.queue_source_film_media(r,tasks=(task,));assert child.run_id in ids
    await p.resume_source_film_run(r)
    await finish(p,child.run_id,unit.package_ref)
    adopt_media(p,r,child.run_id)
    await p.resume_source_film_run(r)
    return child.run_id,task


@pytest.mark.asyncio
async def test_native_cut_school_return_location_and_recovery_actual_wire(tmp_path,monkeypatch,media_files):
    import subprocess
    for video in media_files[0]:
        output=video.with_name('audio-'+video.name)
        subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','lavfi','-i','anullsrc=r=48000:cl=stereo',
            '-c:v','copy','-c:a','aac','-shortest','-y',str(output)],check=True,capture_output=True)
        output.replace(video)
    p,r,service,calls,creates,auth,_=await scenario(tmp_path,monkeypatch,media_files,authors=BoundaryAuthors(voice=True))
    cp=p.film.store.checkpoint(r); first=cp.units[0].generation_run_id
    await finish(p,first,cp.units[0].package_ref);adopt_media(p,r,first)
    assert (await p.resume_source_film_run(r)).state==RuntimeState.SUCCEEDED
    old=p.generation_artifacts.get(p.generation_artifacts.prepared(first),GenerationPreparation).model_dump_json()
    progress=p.source_film_production_progress(r)
    assert progress['scenes'][0]['writtenContentCovered'] and not progress['filmContentComplete']
    assert progress['nextUnit']['sceneId']=='school' and progress['nextUnit']['phaseIndex']==0 and progress['nextUnit']['boundary']=='CUT'
    # Native volatile request captures the approved spoken role. Fixture sound
    # is silence, so it never claims actual pronunciation verification.
    rehearsal=await p.preview_source_film_next_unit(r)
    assert rehearsal['speechEvents'][0]['deliveryMode']=='VOICE_OVER'
    assert rehearsal['speechEvents'][0]['visibleStateRef']['path'][-1]=='entryState'
    assert rehearsal['voice']['voiceIdentityVerification']=='UNVERIFIED'
    assert 'UNVERIFIED' not in rehearsal['request']['content'][0]['text']
    school=cp.units[1]; task=await descriptor(p,r,school,mode='text_to_video')
    identity=p.select_source_film_references(r,task=task)
    assert identity['narrativeIdentitySources'][0]['providerInput'] is False
    assert identity['narrativeIdentitySources'][0]['sourceRunId']==first
    child,task=await execute(p,r,task,school,auth)
    assert task.boundary.kind=='CUT' and task.continuation is None
    assert not task.execution_reference_refs
    body=creates[-1];text=body['content'][0]['text']
    assert body['return_last_frame'] and len(body['content'])==1
    assert not any(c.get('role')=='first_frame' for c in body['content'])
    assert 'School corridor' in text and 'University ambience' not in text and 'Adult street ambience' not in text
    assert 'university hall' not in text and 'street open air' not in text
    assert 'NEW SHOT START after a CUT' in text
    assert 'VOICE_OVER by the adult retrospective narrator' in text
    assert 'Visible subjects do not speak or lip-sync' in text
    assert '画外自白' in text and '用ru说道' not in text
    frozen=p.generation_artifacts.inputs(child).task
    posts=len(creates)
    for _ in range(2): await p.resume_source_film_run(r)
    assert len(creates)==posts and p.generation_artifacts.inputs(child).task==frozen
    target=p.source_film_production_progress(r)['nextUnit'];assert target['sceneId']=='return-room'
    room=cp.units[2]; back=await descriptor(p,r,room,mode='reference')
    sources=p.select_source_film_references(r,task=back)
    space=next(row for row in sources['selected'] if 'LOCATION' in row['purposes'])
    assert space['sourceRunId']==first and space['sourceRunId']!=child
    last,bound=await execute(p,r,back,room,auth)
    assert bound.boundary.kind=='CUT'
    assert 'Dawn' in creates[-1]['content'][0]['text'] and "'timeOfDay': 'Night'" not in creates[-1]['content'][0]['text']
    manifest=p.source_film_preview_manifest(r)
    assert manifest.count("file '")==3 and manifest==p.source_film_preview_manifest(r)
    assert p.generation_artifacts.get(p.generation_artifacts.prepared(first),GenerationPreparation).model_dump_json()==old
    assert p.source_film_production_progress(r)['filmContentComplete']
    # Target-use validation is separate from source adoption.
    from drama_plugin.production.references import ReferenceExecutionBinding
    source_binding=sources['candidates'][0]
    wrong_use=p.production_packages.get(room.package_ref).sources
    wrong_use=next(s.reference for s in wrong_use if s.domain=='WORLD').model_copy(update={'path':('content','setting')})
    bad=ReferenceExecutionBinding.model_validate({**source_binding.model_dump(), 'binding_id':'invalid-target-use',
        'use_ref':wrong_use,'authority_refs':(wrong_use,)})
    badref=p.execution_references.register(bad)
    with pytest.raises(ValueError,match='REFERENCE_CHARACTER_USE_UNSUPPORTED'):
        await p.operation_resolver.selected(p.production_packages.get(room.package_ref),
            bound.model_copy(update={'execution_reference_refs':(badref,)}),p.prompt_compiler.reader,admission_required=False)
    # Source/use/hash guards remain active across valid native Shot references.
    from drama_plugin.execution.contracts import RequestReference
    ref=bound.execution_reference_refs[0]; raw=p.execution_references.resolve(ref)
    from drama_plugin.production.references import ReferenceExecutionBinding
    binding=ReferenceExecutionBinding.model_validate(raw)
    with pytest.raises(ValueError,match='CROSS_SCOPE'):
        ReferenceExecutionBinding.model_validate({**raw,'sourceScope':{**raw['sourceScope'],'workId':'different-work'}})
    request=RequestReference(binding_ref=ref,media_id=binding.media.media_id,content_hash='0'*64,role='REFERENCE',kind='video')
    with pytest.raises(ValueError,match='IDENTITY_MISMATCH'):
        await p.execution.transports['seedance'].reference_url(request,completion(p,last)[0])


@pytest.mark.asyncio
@pytest.mark.parametrize('transition',('continuous','match'))
async def test_designed_cross_scene_boundary_not_scene_id_rule(tmp_path,monkeypatch,media_files,transition):
    p,r,_,_,creates,auth,_=await scenario(tmp_path,monkeypatch,media_files,authors=BoundaryAuthors(transition=transition))
    cp=p.film.store.checkpoint(r);first=cp.units[0].generation_run_id
    await finish(p,first,cp.units[0].package_ref);adopt_media(p,r,first)
    await p.resume_source_film_run(r)
    unit=cp.units[1];task=await descriptor(p,r,unit,mode='image_to_video' if transition=='continuous' else 'text_to_video')
    child,bound=await execute(p,r,task,unit,auth)
    if transition=='continuous':
        assert bound.boundary.kind=='CONTINUE' and bound.continuation.predecessor_media_ref==completion(p,first)[1].progress.video_ref
        assert creates[-1]['content'][1]['role']=='first_frame'
        assert creates[-1]['content'][1]['image_url']['url']=='https://result.invalid/tail-0.jpg'
    else:
        assert bound.boundary.kind=='MATCH' and bound.continuation is None
        assert len(creates[-1]['content'])==1
        assert 'Authored match criterion: Approved match to school.' in creates[-1]['content'][0]['text']
    validate_segment_progress(bound.unit,(p.generation_artifacts.inputs(first).task.unit,),allow_new_action=True)
    with pytest.raises(ValueError,match='REPEAT_OR_SKIP'):
        validate_segment_progress(bound.unit,(p.generation_artifacts.inputs(first).task.unit,))


@pytest.mark.asyncio
async def test_same_shot_montage_cuts_do_not_replay_or_require_equal_tail(tmp_path,monkeypatch,media_files):
    import subprocess
    video=tmp_path/'fourth.mp4';tail=tmp_path/'fourth.jpg'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=green:s=1280x720:r=24:d=4','-c:v','libx264','-pix_fmt','yuv420p','-y',str(video)],check=True,capture_output=True)
    subprocess.run(['ffmpeg','-v','error','-i',str(video),'-frames:v','1','-y',str(tail)],check=True,capture_output=True)
    media_files[0].append(video);media_files[1].append(tail)
    for source in media_files[0]:
        with_audio=source.with_name('native-audio-'+source.name)
        subprocess.run(['ffmpeg','-v','error','-i',str(source),'-f','lavfi','-i','anullsrc=r=48000:cl=stereo',
            '-c:v','copy','-c:a','aac','-shortest','-y',str(with_audio)],check=True,capture_output=True)
        with_audio.replace(source)
    class ScopedCrowds(BoundaryAuthors):
        async def design(self,request):
            rows=await super().design(request)
            result=[]
            for d in rows:
                if request.scope.scene_id=='school' and d.domain=='ACTION':
                    last=d.facts['actionPhases'][-1]
                    d=d.model_copy(update={'facts':{**d.facts,'actionPhases':[*d.facts['actionPhases'],
                        {**last,'entryState':'Same adult street, continuing mid-stride.','action':'Continue the same walk.'}]}})
                if request.scope.scene_id=='school' and d.domain=='SOUND':
                    d=d.model_copy(update={'facts':{**d.facts,'silence':'Brief drop in ambience before the adult street segment; silence under the final line.'}})
                if d.domain=='SUBJECTS' and request.scope.scene_id=='school':
                    d=d.model_copy(update={'facts':{**d.facts,'presentSubjects':[*d.facts['presentSubjects'],
                        {'id':'school-crowd','role':'childhood school mockers','inSceneBehaviour':'Laugh.'},
                        {'id':'university-crowd','role':'young university comrades','inSceneBehaviour':'Laugh.'},
                        {'id':'street-crowd','role':'adult urban crowd','inSceneBehaviour':'Pass.'}]}})
                result.append(d)
            return tuple(result)
    p,r,_,_,creates,auth,_=await scenario(tmp_path,monkeypatch,media_files,authors=ScopedCrowds(montage=True,voice=True))
    cp=p.film.store.checkpoint(r); first=cp.units[0].generation_run_id
    await finish(p,first,cp.units[0].package_ref);adopt_media(p,r,first);await p.resume_source_film_run(r)
    unit=cp.units[1]; tasks=[]
    for phase in (0,1,2):
        child,task=await execute(p,r,await descriptor(p,r,unit,phase,mode='text_to_video' if phase<2 else 'reference'),unit,auth);tasks.append(task)
        assert task.boundary.kind=='CUT' and task.continuation is None
        assert not any(c.get('role')=='first_frame' for c in creates[-1]['content'])
        assert p.source_film_production_progress(r)['currentUnit']['phaseIndex']==phase
        if phase==2:
            # School/university media must not prove adult street-crowd identities
            # simply because the whole Shot declares all three groups.
            assert len(task.execution_reference_refs)==1
            assert len(creates[-1]['content'])==2
            assert 'university comrades' not in creates[-1]['content'][0]['text']
    assert 'Execute only University environment' in creates[2]['content'][0]['text']
    assert 'Execute only Daylight school' not in creates[2]['content'][0]['text']
    assert p.source_film_production_progress(r)['nextUnit']['phaseIndex']==3
    final_task=await p.prepare_source_film_unit(r,task=await descriptor(p,r,unit,3,mode='image_to_video'))
    preview=await p.prompt_compiler.preview_request(unit.package_ref,final_task)
    assert preview['request'], preview
    assert preview['request']['content'][1]['role']=='first_frame'
    assert 'Brief drop in ambience before' not in preview['request']['content'][0]['text']
    assert 'silence under the final line' in preview['request']['content'][0]['text']
    assert len(creates)==4
    assert p.source_film_preview_manifest(r).count("file '")==4
    with pytest.raises(ValueError,match='PREDECESSOR'):
        p.queue_source_film_media(r,tasks=(tasks[0],))


def test_direction_model_exposes_existing_native_boundary_vocabulary():
    from drama_plugin.creative_engine.author_projection import direction_schema
    schema=direction_schema(film=True)
    assert schema['properties']['shots']['items']['properties']['transition']['enum']==['cut','continuous','match']


def test_unlabelled_ambience_clauses_keep_authored_place_scope():
    from drama_plugin.generation.unit_scope import scoped_spans
    text='Schoolyard: children; footsteps on hard floor; University: echoing corridor; paper and book handling; Street: wind; uneven footsteps; crowd murmur.'
    spans=scoped_spans(text,{'school'},{'child'},final_phase=False,path=('content','ambience'))
    current='; '.join(text[a:b] for a,b in spans)
    assert 'children' in current and 'footsteps on hard floor' in current
    assert not any(word in current for word in ('echoing','paper','book','wind','uneven','crowd murmur'))
    text='Street: hold before he speaks; Brief drop before the adult street segment; silence under the final line.'
    spans=scoped_spans(text,{'street'},{'adult'},final_phase=True,path=('content','silence'),entered_places={'street'})
    current='; '.join(text[a:b] for a,b in spans)
    assert 'hold before he speaks' in current and 'silence under the final line' in current
    assert 'Brief drop before' not in current


@pytest.mark.asyncio
async def test_long_designed_chain_crosses_action_then_continues_without_phase_reset(tmp_path,monkeypatch,media_files):
    import subprocess
    for i,color in enumerate(('green','yellow')):
        video=tmp_path/f'extra-{i}.mp4';tail=tmp_path/f'extra-{i}.jpg'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color=c={color}:s=1280x720:r=24:d=4','-c:v','libx264','-pix_fmt','yuv420p','-y',str(video)],check=True,capture_output=True)
        subprocess.run(['ffmpeg','-v','error','-i',str(video),'-frames:v','1','-y',str(tail)],check=True,capture_output=True)
        media_files[0].append(video);media_files[1].append(tail)
    p,r,_,_,creates,auth,_=await scenario(tmp_path,monkeypatch,media_files,
        authors=BoundaryAuthors(transition='continuous',room_phases=3,school_phases=2))
    cp=p.film.store.checkpoint(r);first=cp.units[0].generation_run_id
    await finish(p,first,cp.units[0].package_ref);adopt_media(p,r,first)
    for unit,index in ((cp.units[0],1),(cp.units[0],2),(cp.units[1],0),(cp.units[1],1)):
        child,task=await execute(p,r,await descriptor(p,r,unit,index,mode='image_to_video'),unit,auth)
        assert task.boundary.kind=='CONTINUE'
        assert task.unit.action_refs[0].path[-2]==str(index)
        assert creates[-1]['content'][1]['image_url']['url']==f'https://result.invalid/tail-{len(creates)-2}.jpg'
    assert len(creates)==5 and p.source_film_preview_manifest(r).count("file '")==5
    assert p.source_film_production_progress(r)['scenes'][0]['shots'][0]['adoptedPhases']==[0,1,2]


@pytest.mark.asyncio
async def test_native_ninth_batch_keeps_completed_history_and_serial_tail(tmp_path,monkeypatch,media_files):
    from drama_plugin.runtime.contracts import ExecutionBatchResume,CapabilityResult,ResultStatus
    from drama_plugin.persistence.ledger import ProductionLedger
    import sqlite3
    p,r,_,_,creates,auth,_=await scenario(tmp_path,monkeypatch,media_files,
        authors=BoundaryAuthors(room_phases=2))
    cp=p.film.store.checkpoint(r); first=cp.units[0].generation_run_id
    await finish(p,first,cp.units[0].package_ref); adopt_media(p,r,first)
    await p.resume_source_film_run(r)
    completed=p.runtime.store.load(r)
    # Reopen an old 32-KiB database. Its existing state/dispatch/artifact rows
    # must survive the schema upgrade exactly, including operation foreign keys.
    with sqlite3.connect(p.ledger.path) as db:
        schema=db.execute("SELECT sql FROM sqlite_master WHERE name='production_run'").fetchone()[0]
        db.execute(schema.replace('production_run','old_checkpoint_limit',1).replace('1048576','32768'))
        db.execute('INSERT INTO old_checkpoint_limit SELECT * FROM production_run')
        db.execute('DROP TABLE production_run')
        db.execute('ALTER TABLE old_checkpoint_limit RENAME TO production_run')
        prior={name:db.execute('SELECT * FROM '+name+' ORDER BY rowid').fetchall() for name in ('production_run','production_operation','immutable_artifact','ledger_index')}
    ProductionLedger(p.ledger.path)
    with sqlite3.connect(p.ledger.path) as db:
        assert {name:db.execute('SELECT * FROM '+name+' ORDER BY rowid').fetchall() for name in prior}==prior
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        assert db.execute('PRAGMA foreign_key_list(production_operation)').fetchone()[2]=='production_run'
    # A persisted parent already containing eight completed batches, as in the
    # production incident. Exercise the actual ninth-unit native entry next.
    retained=CapabilityResult(status=ResultStatus.SUCCEEDED,artifact_refs=tuple(
        ArtifactReference(owner='runtime',artifact_ref='historical-completion-'+str(i)+'-'+('x'*190)) for i in range(32)))
    history=tuple(ExecutionBatchResume(batch_ref=cp.plan_ref,
        decision_ref=cp.operation_task.owners.rights_decision_ref,continuation_goal_hash=sha256_canonical({'prior':i}),
        completed_revision=completed.revision,completed_cursor=completed.cursor,
        completed_result=retained) for i in range(8))
    seeded=completed.model_copy(update={'execution_batches':history,'revision':completed.revision+1})
    assert len(seeded.model_dump_json().encode())>32768
    p.runtime.store.save(seeded,expected_revision=completed.revision)
    child,task=await execute(p,r,await descriptor(p,r,cp.units[0],1,mode='image_to_video'),cp.units[0],auth)
    latest=p.runtime.store.load(r)
    assert latest.execution_batches[:8]==history and len(latest.execution_batches)==9
    assert p.runtime.store.load(child).state==RuntimeState.SUCCEEDED
    assert task.boundary.kind=='CONTINUE' and len(creates)==2
    assert creates[-1]['content'][1]['image_url']['url']=='https://result.invalid/tail-0.jpg'
    assert p.source_film_preview_manifest(r).count("file '")==2


class SameNarratorAuthors(BoundaryAuthors):
    def __init__(self): super().__init__(voice=True)
    async def author_film(self, request):
        value=await super().author_film(request)
        return value.model_copy(update={'scenes':tuple(s.model_copy(update={'scene':s.scene.model_copy(update={'dialogue':(*s.scene.dialogue,Dialogue(id='school-second',speaker='actor',text='Я знал это с рождения.'))})}) if s.scene_id=='school' else s for s in value.scenes)})
    async def direct_film(self, request):
        value=await super().direct_film(request)
        return value.model_copy(update={'shots':tuple(s.model_copy(update={'shot':s.shot.model_copy(update={'spoken_ids':('school-voice','school-second')})}) if s.scene_id=='school' else s for s in value.shots)})
    async def design(self, request):
        designs=await super().design(request); result=[]
        for design in designs:
            facts=dict(design.facts)
            if request.scope.scene_id=='school':
                if design.domain=='PERFORMANCE':
                    facts['lines']=[*facts['lines'],{**facts['lines'][0],
                        'spokenContentId':'school-second','changeFromPrevious':'Second approved utterance.'}]
                    facts['projectionSubjects']=[*[{**row,'spokenIds':['school-voice','school-second']}
                        for row in facts['projectionSubjects']],{
                        'subjectRef':'a-mockers','sourceTargetLabel':'childhood mockers',
                        'role':'INTERACTIVE_PARTNER','beatIds':['beat-1'],
                        'reciprocalActions':['Laugh and point casually.'],
                        'tactics':['Casual mockery without confrontation.']}]
                if design.domain=='ACTION':
                    facts['actionPhases']=[{**r,'spokenIds':['school-voice','school-second']} for r in facts['actionPhases']]
                if design.domain=='SOUND':
                    facts['speechRelations']=[{'eventId':'school-second','targetEventId':'school-voice','relation':'AFTER'}]
                if design.domain=='SUBJECTS':
                    facts['presentSubjects']=[{'id':'actor','role':'protagonist and voiceover narrator','inSceneBehaviour':'Boy keeps his gaze ahead.'},
                        {'id':'a-mockers','role':'childhood mockers','inSceneBehaviour':'Laugh and point casually.'}]
                    facts['identityConstraints']='Narrator is the same person across ages; groups remain non-individuated.'
                    facts['absences']='No crowd violence; no direct dialogue from mockers.'
            result.append(design.model_copy(update={'facts':facts}))
        return tuple(result)


class MixedNarrationDirectAuthors(SameNarratorAuthors):
    async def design(self, request):
        designs=await super().design(request);result=[]
        for design in designs:
            facts=dict(design.facts)
            if request.scope.scene_id=='school':
                if design.domain=='SOUND':facts['dialogueAndLegibility']='直接台词和旁白保持清晰。'
                if design.domain=='PERFORMANCE':
                    facts['lines']=[{**row,'dramaticAction':'旁白交代回忆。' if row['spokenContentId']=='school-voice' else '当面对他们说，声音平直。'} for row in facts['lines']]
            result.append(design.model_copy(update={'facts':facts}))
        return tuple(result)


@pytest.mark.asyncio
async def test_current_utterance_direct_address_overrides_global_narration_actual_request(tmp_path,monkeypatch,media_files):
    p,r,_,_,creates,_,_=await scenario(tmp_path,monkeypatch,media_files,authors=MixedNarrationDirectAuthors())
    cp=p.film.store.checkpoint(r);unit=cp.units[1]
    voiced=await descriptor(p,r,unit,spoken_range=(0,1))
    direct=await descriptor(p,r,unit,spoken_range=(1,2))
    before=len(creates)
    narration=await p.prompt_compiler.preview_request(unit.package_ref,voiced)
    spoken=await p.prompt_compiler.preview_request(unit.package_ref,direct)
    assert narration['speechEvents'][0]['deliveryMode']=='VOICE_OVER'
    assert 'VOICE_OVER' in narration['request']['content'][0]['text']
    assert not spoken['speechEvents'][0].get('deliveryMode')
    assert 'VOICE_OVER' not in spoken['request']['content'][0]['text']
    assert direct.unit.spoken_ids==('school-second',)
    assert len(creates)==before


@pytest.mark.asyncio
async def test_native_same_narrator_relations_and_unowned_constraints_actual_request(tmp_path,monkeypatch,media_files):
    # Native compiler -> final provider projection; no service submission is needed.
    import subprocess
    for video in media_files[0]:
        target=video.with_name('audio-'+video.name)
        subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-c:v','copy','-c:a','aac','-shortest','-y',str(target)],check=True,capture_output=True)
        target.replace(video)
    p,r,_,_,creates,_,_=await scenario(tmp_path,monkeypatch,media_files,authors=SameNarratorAuthors())
    cp=p.film.store.checkpoint(r);first=cp.units[0].generation_run_id
    await finish(p,first,cp.units[0].package_ref);adopt_media(p,r,first)
    dpd,scope_pin,_=p.operation_resolver.compose_performance(cp.units[1].refs)
    binding=p.creative_versions.objects.read_ref(dpd)
    assert len(binding['partnerBeatBindings'])==1
    partner=binding['partnerBeatBindings'][0]
    assert partner['actor']=='a-mockers' and partner['direction']['objective'] is None
    assert partner['direction']['performanceBoundaries']==['Laugh and point casually.']
    from drama_plugin.performance_coverage import compose_partner_beats,validate_shot_dpd_coverage
    from drama_plugin.professional_design.performance_scope import read_performance_scope
    from drama_plugin.contracts.dpd import BeatDPD,DPDSnapshot
    from drama_plugin.contracts.source_pin import SourcePin
    witness=read_performance_scope(p.creative_versions,scope_pin)
    beats={b.beat_id:b for raw in binding['beatBindings'] for b in (BeatDPD.model_validate(raw),)}
    partners=compose_partner_beats(projection_scope=witness,beats=beats)
    snapshots={s.line.spoken_content_id:s for row in binding['snapshotBindings'] for s in (DPDSnapshot.model_validate(p.creative_versions.objects.read_ref(SourcePin.model_validate(row['snapshotPin']))),)}
    with pytest.raises(ValueError,match='PARTNER_DPD_SOURCE_BINDING_MISMATCH'):
        validate_shot_dpd_coverage(projection_scope=witness,beats=beats,snapshots=snapshots,
            partner_beats=(partners[0].model_copy(update={'actor':'unbound-crowd'}),))
    rehearsal=await p.preview_source_film_next_unit(r)
    assert rehearsal.get('request'), rehearsal
    text=rehearsal['request']['content'][0]['text']
    assert '台词『Я знал это с рождения.』后于台词『Я был смешон.』' in text
    assert '这是这两次发声的关系，不增加或重复台词' in text
    assert 'actor的声音' not in text and 'school-voice' not in text and 'school-second' not in text
    assert '<主体1>身份：Narrator' not in text and '<主体2>身份：Narrator' not in text
    assert 'Narrator is the same person across ages; groups remain non-individuated' in text
    assert '<主体1>身份：childhood mockers' in text, text
    assert '<主体1>身份：Laugh; point casually' in text, text
    assert '<主体2>身份：protagonist; voiceover narrator' in text
    assert 'UNVERIFIED' not in text and 'OFFLINE_PREVIEW' not in text
    assert rehearsal['voice']['voiceIdentityVerification']=='UNVERIFIED'
    assert len(creates)==1  # only the existing mock opening, no preview POST


@pytest.mark.asyncio
async def test_native_whole_line_split_and_host_candidate_progress(tmp_path,monkeypatch,media_files):
    from drama_plugin.film.contracts import FilmMediaBatch
    from drama_plugin.execution.contracts import ReviewObservation
    import subprocess
    for video in media_files[0]:
        target=video.with_name('audio-'+video.name)
        subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-c:v','copy','-c:a','aac','-shortest','-y',str(target)],check=True,capture_output=True)
        target.replace(video)
    class ScopedReferences(SameNarratorAuthors):
        async def design(self,request):
            rows=await super().design(request);result=[]
            for design in rows:
                if design.domain=='REFERENCE':
                    references=[*design.facts['references'],
                        dict(id='current-second-proof',priority='REQUIRED',beatIds=['beat-1'],designPurpose='Current-age context.',inputDuty='Identity continuity of current age'),
                        dict(id='later-adult-proof',priority='REQUIRED',beatIds=['later-beat'],designPurpose='Future adult street.',inputDuty='Identity for future adult street, not current school')]
                    design=design.model_copy(update={'facts':{**design.facts,'references':references}})
                result.append(design)
            return tuple(result)
    p,r,_,_,creates,auth,_=await scenario(tmp_path,monkeypatch,media_files,authors=ScopedReferences())
    cp=p.film.store.checkpoint(r);first=cp.units[0].generation_run_id
    await finish(p,first,cp.units[0].package_ref);adopt_media(p,r,first)
    await p.resume_source_film_run(r)
    cp=p.film.store.checkpoint(r)
    batch=FilmMediaBatch.seal(scope=p.runtime.store.load(r).scope,run_id=r,batch_id='offline-split-test',
        film_version=cp.film_version,
        authorization_ref=cp.operation_task.owners.rights_decision_ref,opening_run_id=first,goal_hash='offline-split-only',
        allow_unverified_audio=False,previous_checkpoint=cp)
    p.film.store.save(r,p.runtime.store.load(r).scope,cp.model_copy(update={'media_batch_ref':p.film.store.put(batch)}))
    school=cp.units[1]
    a=await descriptor(p,r,school,mode='text_to_video',spoken_range=(0,1))
    context=a.unit.execution_context
    a=a.model_copy(update={'unit':a.unit.model_copy(update={'execution_context':context.model_copy(update={
        'fact_spans':tuple(reversed(context.fact_spans)),
        'background_refs':tuple(reversed(context.background_refs))})})})
    disposition=UserDecisionRecord.seal(run_id=r,scope=p.runtime.store.load(r).scope,decision_id=r+':split-fixture-missing-reference',
        category=DecisionCategory.ART_APPROVAL,accepted=True,source_ref=school.package_ref,terms_hash=a.unit.terms_hash(school.package_ref))
    a=a.model_copy(update={'unit':a.unit.model_copy(update={'scope_decision_ref':p.reviews.put_user_decision(disposition)})})
    a=await p.prepare_source_film_unit(r,task=a)
    child=p.create_media_review_run(package_ref=school.package_ref,task=a,offline_authorization=auth)
    p.queue_source_film_media(r,tasks=(a,))
    from drama_plugin.generation.contracts import ExecutionDiagnostic
    from drama_plugin.generation.compiler import CompilationResult
    original=p.prompt_compiler.compile
    async def old_order_failure(package_ref,task):
        ref=p.generation_artifacts.retain_diagnostics((ExecutionDiagnostic(code='SCOPE_MISMATCH',
            owner='production-selection',domain='DIRECTION',required=True),),scope=p.runtime.store.load(child.run_id).scope)
        return CompilationResult(None,ref,None,None)
    monkeypatch.setattr(p.prompt_compiler,'compile',old_order_failure)
    await p.resume_source_film_run(r)
    assert p.runtime.store.load(child.run_id).state==RuntimeState.FAILED
    assert len(creates)==1
    monkeypatch.setattr(p.prompt_compiler,'compile',original)
    await p.resume_source_film_run(r)
    assert p.runtime.store.load(child.run_id).external_repairs
    assert p.generation_artifacts.inputs(child.run_id).task==a
    pending=(ReviewObservation(code='AUDIO_UNVERIFIED',owner='offline-fixture',finding='Synthetic silence; no actual pronunciation claim.'),)
    await finish(p,child.run_id,school.package_ref,observations=pending)
    await p.resume_source_film_run(r);p.select_source_film_working_input(r,child_id=child.run_id)
    progress=p.source_film_production_progress(r)
    assert progress['nextUnit']['sceneId']=='school' and progress['nextUnit']['boundary']=='CONTINUE'
    assert progress['nextUnit']['remainingSpokenIds']==['school-second']
    assert progress['scenes'][1]['shots'][0]['adoptedPhases']==[]
    assert not progress['scenes'][1]['productionContentCovered']
    denied=await descriptor(p,r,school,mode='image_to_video',spoken_range=(1,2))
    with pytest.raises(ValueError,match='CONTINUATION_SPEECH_COMPLETION_UNVERIFIED'):
        await p.prepare_source_film_unit(r,task=denied)
    b=await descriptor(p,r,school,mode='image_to_video',spoken_range=(1,2),allow_unverified_audio=True)
    b=await p.prepare_source_film_unit(r,task=b)
    assert b.continuation.allow_unverified_audio is True
    assert not p.film.store.get(p.film.store.checkpoint(r).media_batch_ref,FilmMediaBatch).allow_unverified_audio
    from drama_plugin.production.references import ReferenceExecutionBinding
    raw=p.ledger.get_artifact('reference-execution-binding',ArtifactReference(owner=b.continuation.global_reference_ref.owner.value,
        artifact_ref=b.continuation.global_reference_ref.artifact_ref,version=b.continuation.global_reference_ref.version))[0]
    global_binding=ReferenceExecutionBinding.model_validate(raw)
    assert len(global_binding.duties)==1
    assert 'Identity continuity of current age' in global_binding.duties[0].purpose
    assert 'future adult street' not in global_binding.duties[0].purpose
    validate_segment_progress(b.unit,(a.unit,))
    for invalid in (a.unit,b.unit.model_copy(update={'spoken_ids':a.unit.spoken_ids})):
        with pytest.raises(ValueError):validate_segment_progress(invalid,(a.unit,))
    later=p.create_media_review_run(package_ref=school.package_ref,task=b,offline_authorization=auth)
    p.queue_source_film_media(r,tasks=(b,));await finish(p,later.run_id,school.package_ref,observations=pending)
    await p.resume_source_film_run(r);p.select_source_film_working_input(r,child_id=later.run_id)
    assert len(creates[1]['content'])==1
    assert creates[2]['content'][1]['role']=='first_frame'
    assert 'task-1' in creates[2]['content'][1]['image_url']['url'] or 'tail-1' in creates[2]['content'][1]['image_url']['url']
    assert '用ru{Я был смешон.}' in creates[1]['content'][0]['text'] and '用ru{Я знал это с рождения.}' not in creates[1]['content'][0]['text']
    assert '用ru{Я знал это с рождения.}' in creates[2]['content'][0]['text'] and '用ru{Я был смешон.}' not in creates[2]['content'][0]['text']
    progress=p.source_film_production_progress(r)
    assert progress['scenes'][1]['productionContentCovered'] and not progress['scenes'][1]['writtenContentCovered']
    assert all(row['adoption']=='PENDING' and row['productionSelection']=='HOST_WORKING_INPUT' and row['soundVerification']=='UNVERIFIED' for row in progress['scenes'][1]['shots'][0]['segments'])
    assert progress['nextUnit']['sceneId']=='return-room'
    before=len(creates);await p.resume_source_film_run(r);assert len(creates)==before

@pytest.mark.asyncio
async def test_native_wrong_age_input_revision_at_later_content_slot_retains_history(tmp_path,monkeypatch,media_files):
    import subprocess
    for i,color in enumerate(('green','yellow','white'),3):
        video=tmp_path/f'extra-{i}.mp4';image=tmp_path/f'extra-{i}.jpg'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color=c={color}:s=1280x720:r=24:d=4',
            '-c:v','libx264','-pix_fmt','yuv420p','-y',str(video)],check=True,capture_output=True)
        subprocess.run(['ffmpeg','-v','error','-i',str(video),'-frames:v','1','-y',str(image)],check=True,capture_output=True)
        media_files[0].append(video);media_files[1].append(image)
    from drama_plugin.production.references import ReferenceExecutionBinding
    from drama_plugin.creative_engine.sources import NativeCreativeSources
    from drama_plugin.execution.contracts import CreativeMediaReview,ReviewObservation
    from drama_plugin.execution.review import ReviewResponse
    p,r,_,_,creates,auth,_=await scenario(tmp_path,monkeypatch,media_files,authors=BoundaryAuthors(room_phases=4))
    cp=p.film.store.checkpoint(r);first=cp.units[0].generation_run_id
    await finish(p,first,cp.units[0].package_ref);adopt_media(p,r,first);await p.resume_source_film_run(r)
    for phase in (1,2,3):
        await execute(p,r,await descriptor(p,r,cp.units[0],phase,mode='image_to_video'),cp.units[0],auth)
    school=cp.units[1];bad=await descriptor(p,r,school,mode='reference')
    _,check,source=completion(p,first)
    original=NativeCreativeSources(p.creative_versions,school.refs,p.execution_references)
    subjects=next(p.creative_versions.resolve(v) for v in school.refs if p.creative_versions.resolve(v).kind==Kind.PROFESSIONAL and p.creative_versions.resolve(v).body.domain=='SUBJECTS')
    use=original.project(subjects).reference('content','identityConstraints')
    ref=p.execution_references.register(ReferenceExecutionBinding(binding_id='historical-wrong-age-reference',version=1,
        scope=p.creative_versions.resolve(school.refs[-1]).scope,source_scope=source.scope,use_ref=use,state_ref=bad.unit.start_ref,
        media=dict(media_id=source.canonical_media_ref.artifact_ref,version='1',content_hash=source.media.content_hash,
            kind='video',semantics=('identity',),duration=4,width=1280,height=720,review_ref=check.progress.video_creative_ref.artifact_ref),
        duties=(dict(role='CHARACTER',necessity='PREFERRED',subject='actor',purpose='Historical cross-age attempt, not a verified childhood face.'),),
        subject_ids=('actor',),role='REFERENCE',authorization_scope='ADOPTED_PRODUCTION_INPUT',authority_refs=(use,)))
    bad=bad.model_copy(update={'execution_reference_refs':(ref,)})
    bad=await p.prepare_source_film_unit(r,task=bad)
    child=p.create_media_review_run(package_ref=school.package_ref,task=bad,offline_authorization=auth)
    p.queue_source_film_media(r,tasks=(bad,));await p.resume_source_film_run(r)
    if p.runtime.store.load(child.run_id).cursor==2:
        await p.decide_target_run(child.run_id,decision_id=p.runtime.decision_id(child.run_id),accepted=True,source_ref=school.package_ref)
        await p.runtime.run(child.run_id)
    assert p.runtime.store.load(child.run_id).state==RuntimeState.WAITING_USER,p.runtime.serialize(child.run_id)
    assert p.runtime.store.load(child.run_id).cursor==9,p.runtime.serialize(child.run_id)
    op,check,media=completion(p,child.run_id)
    context=p.execution.review_context(op,media.media,media.canonical_media_ref)
    await p.provide_human_media_review(child.run_id,media_ref=check.progress.video_ref,context_hash=context,
        response=ReviewResponse('REVISE',(ReviewObservation(code='WRONG_AGE',owner='fixture',finding='Fixture marks the old visual input unsuitable.',required_revision='Correct current-unit input.'),)))
    await p.resume_source_film_run(r)
    original=p.generation_artifacts.get(op.preparation_ref,GenerationPreparation).model_dump_json()
    replacement=await descriptor(p,r,school,mode='text_to_video')
    replacement=replacement.model_copy(update={'boundary':bad.boundary})
    await p.revise_source_film_segment(r,slot=3,task=replacement)
    current=p.film.store.checkpoint(r).scene_media_run_ids[-1]
    assert current!=child.run_id and len(creates)==5
    from test_camera_timing_revision import approve_mock_cost
    p.execution.transports['seedance'].offline=False
    await approve_mock_cost(p,r,current)
    await finish(p,current,school.package_ref)
    assert len(creates)==6 and len(creates[-1]['content'])==1 and creates[-1]['return_last_frame']
    await p.revise_source_film_segment(r,slot=3,task=replacement)
    assert len(creates)==6 and p.film.store.checkpoint(r).scene_media_run_ids[-1]==current
    assert p.generation_artifacts.get(op.preparation_ref,GenerationPreparation).model_dump_json()==original
    retained_review=p.execution.store.checkpoint(op.artifact_reference()).progress.video_creative_ref
    assert p.execution.store.get(retained_review,CreativeMediaReview).outcome=='REVISE'


@pytest.mark.asyncio
async def test_native_parent_transient_query_repair_retains_same_paid_child(tmp_path,monkeypatch,media_files):
    from dataclasses import replace
    import httpx
    p,r,_,_,creates,auth,_=await scenario(tmp_path,monkeypatch,media_files,authors=BoundaryAuthors(room_phases=2))
    cp=p.film.store.checkpoint(r);unit=cp.units[0];first=unit.generation_run_id
    await finish(p,first,unit.package_ref);adopt_media(p,r,first);await p.resume_source_film_run(r)
    task=await p.prepare_source_film_unit(r,task=await descriptor(p,r,unit,1,mode='image_to_video'))
    child=p.create_media_review_run(package_ref=unit.package_ref,task=task,offline_authorization=auth)
    p.queue_source_film_media(r,tasks=(task,));await p.resume_source_film_run(r)
    assert p.runtime.store.load(r).state in {RuntimeState.WAITING_EXTERNAL,RuntimeState.WAITING_USER}
    await finish(p,child.run_id,unit.package_ref)
    count=len(creates);assert count==2
    native=p.runtime.executor._native['film.execute:v1']
    async def timeout(_):raise httpx.ConnectTimeout('Offline read-only fixture')
    p.runtime.executor._native['film.execute:v1']=replace(native,handler=timeout)
    await p.resume_source_film_run(r)
    failed=p.runtime.store.load(r)
    assert failed.state==RuntimeState.FAILED and failed.last_result.code=='EXTERNAL_RECONCILIATION_ERROR'
    assert not failed.last_result.artifact_refs
    p.runtime.executor._native['film.execute:v1']=native
    await p.resume_source_film_run(r)
    restored=p.runtime.store.load(r)
    assert restored.state==RuntimeState.SUCCEEDED,p.runtime.serialize(r)
    assert p.film.store.checkpoint(r).scene_media_run_ids[-1]==child.run_id and len(creates)==count
    record=restored.external_repairs[-1]
    assert record.child_ref.artifact_ref==child.run_id and record.failed_result==failed.last_result
    assert not p.runtime.store.load(child.run_id).external_repairs

class UtteranceScopedCameraAuthors(SameNarratorAuthors):
    async def design(self, request):
        designs=await super().design(request); result=[]
        for design in designs:
            facts=dict(design.facts)
            if request.scope.scene_id=='school' and design.domain=='CAMERA':
                facts['movement']=[{'beatId':'beat-1','spokenIds':['school-voice'],'design':'CURRENT_A: hold for observation.'},
                    {'beatId':'beat-1','spokenIds':['school-second'],'design':'CURRENT_B: move only after the spoken event.'}]
            result.append(design.model_copy(update={'facts':facts}))
        return tuple(result)

@pytest.mark.asyncio
async def test_native_utterance_scoped_structured_camera_reaches_model_request(tmp_path,monkeypatch,media_files):
    p,r,_,_,creates,_,_=await scenario(tmp_path,monkeypatch,media_files,authors=UtteranceScopedCameraAuthors())
    unit=p.film.store.checkpoint(r).units[1]; before=len(creates)
    for span,keep,exclude in (((0,1),'CURRENT_A','CURRENT_B'),((1,2),'CURRENT_B','CURRENT_A')):
        task=await descriptor(p,r,unit,spoken_range=span)
        result=await p.prompt_compiler.preview_request(unit.package_ref,task)
        assert result['request'],result
        text=result['request']['content'][0]['text']
        assert keep in text and exclude not in text
        assert '运镜：' in text
    assert len(creates)==before

@pytest.mark.asyncio
async def test_native_definite_create_rejection_revision_retains_failure_and_resumes(tmp_path,monkeypatch,media_files):
    from drama_plugin.execution.transport import DefinitelyNotSubmitted
    p,r,_,_,creates,auth,_=await scenario(tmp_path,monkeypatch,media_files,authors=BoundaryAuthors())
    cp=p.film.store.checkpoint(r); first=cp.units[0].generation_run_id
    await finish(p,first,cp.units[0].package_ref); adopt_media(p,r,first);await p.resume_source_film_run(r)
    unit=cp.units[1];task=await p.prepare_source_film_unit(r,task=await descriptor(p,r,unit))
    transport=p.execution.transports['seedance'];submit=transport.submit
    async def rejected(*args):raise DefinitelyNotSubmitted('HTTP_400',http_status=400)
    monkeypatch.setattr(transport,'submit',rejected)
    child=p.create_media_review_run(package_ref=unit.package_ref,task=task,offline_authorization=auth)
    p.queue_source_film_media(r,tasks=(task,));await p.resume_source_film_run(r)
    if p.runtime.store.load(child.run_id).state==RuntimeState.WAITING_USER:
        await p.decide_target_run(child.run_id,decision_id=p.runtime.decision_id(child.run_id),accepted=True,source_ref=unit.package_ref)
    await p.runtime.run(child.run_id);await p.resume_source_film_run(r)
    assert p.runtime.store.load(r).state==RuntimeState.FAILED
    failed=p.runtime.store.load(child.run_id);assert failed.last_result.code=='HTTP_400'
    monkeypatch.setattr(transport,'submit',submit)
    material=p.creative_versions.objects.read_ref(task.owners.rights_pin)
    material={k:v for k,v in material.items() if k not in ('requestRef','decisionRef','externalProcessingAuthorized')}
    material['processingScope']={**material['processingScope'],'reason':'Bounded corrected delivery revision.'}
    pin=p.creative_versions.objects.put('rejected-create-rights-request',material)
    req=ArtifactReference(owner='source-owner',artifact_ref=pin.key,version=1)
    decision=UserDecisionRecord.seal(run_id=r,scope=p.runtime.store.load(r).scope,decision_id=r+':rejected-create-revision',category=DecisionCategory.ADOPTION,accepted=True,source_ref=req)
    dr=p.reviews.put_user_decision(decision)
    rights=p.creative_versions.objects.put('rejected-create-rights',{**material,'requestRef':req.model_dump(mode='json',by_alias=True),'decisionRef':dr.model_dump(mode='json',by_alias=True),'externalProcessingAuthorized':True})
    revised=task.model_copy(update={'owners':task.owners.model_copy(update={'rights_pin':rights,'rights_request_ref':req,'rights_decision_ref':dr})})
    preview=await p.prompt_compiler.compile(unit.package_ref,revised);assert preview.preparation_ref
    replacement=p.create_media_review_run(package_ref=unit.package_ref,task=revised,offline_authorization=auth)
    await p.revise_source_film_segment(r,slot=0,task=revised)
    await finish(p,replacement.run_id,unit.package_ref);await p.resume_source_film_run(r)
    assert p.runtime.store.load(child.run_id)==failed
    assert p.runtime.store.load(replacement.run_id).state==RuntimeState.SUCCEEDED
    assert p.runtime.store.load(r).state==RuntimeState.SUCCEEDED
    assert len(creates)==2 # first completed scene + successful revised scene
    assert p.film.store.checkpoint(r).scene_media_revision_refs

@pytest.mark.asyncio
async def test_native_terminal_created_failure_revision_preserves_task_and_paid_count(tmp_path,monkeypatch,media_files):
    import httpx
    from drama_plugin.execution.contracts import ProviderReceipt,ExecutionOperation
    p,r,_,_,creates,auth,_=await scenario(tmp_path,monkeypatch,media_files,authors=BoundaryAuthors())
    cp=p.film.store.checkpoint(r);first=cp.units[0].generation_run_id
    await finish(p,first,cp.units[0].package_ref);adopt_media(p,r,first);await p.resume_source_film_run(r)
    unit=cp.units[1];task=await p.prepare_source_film_unit(r,task=await descriptor(p,r,unit))
    adapter=p.execution.transports['seedance'].adapter;original=adapter.client._transport.handler
    def failed_output(request):
        response=original(request)
        if request.method=='POST':
            body=response.json();body.pop('content',None)
            body.update(status='failed',error={'code':'OutputVideoSensitiveContentDetected.PolicyViolation','message':'Output rejected.'})
            return httpx.Response(200,json=body)
        return response
    adapter.client._transport=httpx.MockTransport(failed_output)
    child=p.create_media_review_run(package_ref=unit.package_ref,task=task,offline_authorization=auth)
    p.queue_source_film_media(r,tasks=(task,));await p.resume_source_film_run(r)
    if p.runtime.store.load(child.run_id).state==RuntimeState.WAITING_USER:
        await p.decide_target_run(child.run_id,decision_id=p.runtime.decision_id(child.run_id),accepted=True,source_ref=unit.package_ref)
    await p.runtime.run(child.run_id);await p.resume_source_film_run(r)
    failed=p.runtime.store.load(child.run_id);assert failed.last_result.code=='PROVIDER_DEFINITE_FAILURE'
    with p.ledger.transaction() as db:
        row=db.execute('SELECT operation_ref_json FROM production_operation WHERE run_id=? AND operation_ref_json IS NOT NULL',(child.run_id,)).fetchone()
    op_ref=ArtifactReference.model_validate_json(row[0]);old=p.execution.store.checkpoint(op_ref)
    receipt=p.execution.store.get(old.receipt_ref,ProviderReceipt)
    assert receipt.state=='FAILED' and receipt.remote_identity=='task-1' and old.progress.video_ref is None
    assert len(creates)==2  # failed task remains an actual create
    adapter.client._transport=httpx.MockTransport(original)
    material=p.creative_versions.objects.read_ref(task.owners.rights_pin)
    material={k:v for k,v in material.items() if k not in ('requestRef','decisionRef','externalProcessingAuthorized')}
    material['processingScope']={**material['processingScope'],'reason':'Explicitly authorized one additional created-task revision; original failure/count retained.'}
    pin=p.creative_versions.objects.put('terminal-failure-revision-request',material)
    req=ArtifactReference(owner='source-owner',artifact_ref=pin.key,version=1)
    decision=UserDecisionRecord.seal(run_id=r,scope=p.runtime.store.load(r).scope,decision_id=r+':terminal-failure-extra-create',category=DecisionCategory.ADOPTION,accepted=True,source_ref=req)
    dr=p.reviews.put_user_decision(decision)
    rights=p.creative_versions.objects.put('terminal-failure-revision-rights',{**material,'requestRef':req.model_dump(mode='json',by_alias=True),'decisionRef':dr.model_dump(mode='json',by_alias=True),'externalProcessingAuthorized':True})
    revised=task.model_copy(update={'owners':task.owners.model_copy(update={'rights_pin':rights,'rights_request_ref':req,'rights_decision_ref':dr})})
    replacement=p.create_media_review_run(package_ref=unit.package_ref,task=revised,offline_authorization=auth)
    await p.revise_source_film_segment(r,slot=0,task=revised)
    await finish(p,replacement.run_id,unit.package_ref);await p.resume_source_film_run(r)
    assert p.runtime.store.load(child.run_id)==failed and p.execution.store.checkpoint(op_ref)==old
    assert p.runtime.store.load(r).state==RuntimeState.SUCCEEDED and len(creates)==3
    assert p.runtime.store.load(r).external_repairs[-1].failed_result.code=='PROVIDER_DEFINITE_FAILURE'
    await p.revise_source_film_segment(r,slot=0,task=revised)
    assert len(creates)==3

@pytest.mark.asyncio
async def test_expired_official_reference_refreshes_exact_task_without_create(tmp_path,monkeypatch,media_files):
    from drama_plugin.execution.store import ExecutionStore
    from drama_plugin.execution.contracts import ProviderReceipt,RequestReference
    p,r,service,calls,creates,auth,_=await scenario(tmp_path,monkeypatch,media_files,authors=BoundaryAuthors())
    unit=p.film.store.checkpoint(r).units[0];first=unit.generation_run_id
    op,check,media,_=await finish(p,first,unit.package_ref);adopt_media(p,r,first);await p.resume_source_film_run(r)
    from test_native_scene_continuation import referenced_task
    from drama_plugin.contracts.media import Media
    check=p.execution.store.checkpoint(op.artifact_reference())
    base=p.generation_artifacts.get(op.preparation_ref,GenerationPreparation).task
    bound=referenced_task(p,p.production_packages.get(unit.package_ref),base,Media.model_validate(service.records[0]),check.progress.video_creative_ref,binding_id='expired-reference',mode='reference')
    ref=bound.execution_reference_refs[0];raw=p.execution_references.resolve(ref)
    from drama_plugin.production.references import ReferenceExecutionBinding
    binding=ReferenceExecutionBinding.model_validate(raw)
    reference=RequestReference(binding_ref=ref,media_id=binding.media.media_id,content_hash=binding.media.content_hash,role='REFERENCE',kind='video')
    old_get=ExecutionStore.get
    original=old_get(p.execution.store,media.receipt_ref,ProviderReceipt)
    def expired(store,ref,kind):
        value=old_get(store,ref,kind)
        if ref==media.receipt_ref and kind==ProviderReceipt:
            return value.model_copy(update={'result':value.result.model_copy(update={'locator':value.result.locator+'?X-Tos-Date=20000101T000000Z&X-Tos-Expires=60'})})
        return value
    monkeypatch.setattr(ExecutionStore,'get',expired)
    before=len(creates)
    url=await p.execution.transports['seedance'].reference_url(reference,op)
    assert url=='https://result.invalid/video-0.mp4'
    assert len(creates)==before
    assert any(c.method=='GET' and c.url.path.endswith('/tasks/task-0') for c in calls)
    assert old_get(p.execution.store,media.receipt_ref,ProviderReceipt)==original

@pytest.mark.asyncio
async def test_derived_package_retains_completed_media_and_formally_recovers_same_child(tmp_path,monkeypatch,media_files):
    from drama_plugin.creative_engine.contracts import Authority,DesignBody
    from drama_plugin.creative_engine.sources import NativeCreativeSources
    from drama_plugin.production.contracts import ProductionPackage,PackageContent
    from drama_plugin.film.contracts import FilmCheckpoint,FilmPlan
    from drama_plugin.film import media_units
    class DerivedCut(BoundaryAuthors):
        async def design(self,request):
            rows=await super().design(request)
            return tuple(d.model_copy(update={'facts':{**d.facts,'actionPhases':[
                {**row,**({'transition':'cut'} if i==1 else {})} for i,row in enumerate(d.facts['actionPhases'])]}})
                if request.scope.scene_id=='room' and d.domain=='ACTION' else d for d in rows)
    p,r,_,_,creates,auth,_=await scenario(tmp_path,monkeypatch,media_files,authors=DerivedCut(room_phases=2))
    cp=p.film.store.checkpoint(r);unit=cp.units[0];first=unit.generation_run_id
    await finish(p,first,unit.package_ref);adopt_media(p,r,first);await p.resume_source_film_run(r)
    frozen=p.generation_artifacts.get(p.generation_artifacts.prepared(first),GenerationPreparation).model_dump_json()
    prior_task=await p.prepare_source_film_unit(r,task=await descriptor(p,r,unit,1,mode='reference'))
    prior_ref=prior_task.execution_reference_refs[0];prior_binding=p.execution_references.resolve(prior_ref)
    old=next(p.creative_versions.resolve(v) for v in unit.refs if p.creative_versions.resolve(v).kind==Kind.PROFESSIONAL and p.creative_versions.resolve(v).body.domain=='WORLD')
    core=tuple(v for v in unit.refs if p.creative_versions.resolve(v).kind!=Kind.PROFESSIONAL)
    facts={k:v for k,v in old.body.facts.items() if k not in ('scope','sourcePins')};facts['time']='Night, current execution context.'
    candidate=p.creative_versions.write(writer=Authority.PROFESSIONAL,kind=Kind.PROFESSIONAL,scope=old.scope,body=DesignBody(domain='WORLD',facts=facts),sources=core,operation=r+':derived-world-candidate')
    original_plan=p.film.store.get(cp.plan_ref,FilmPlan)
    candidate_refs=tuple(candidate if v==old.ref() else v for v in unit.refs)
    adoption_plan=FilmPlan.seal(**{**original_plan.model_dump(exclude={'fingerprint'}),
        'unit_version_refs':(candidate_refs,*original_plan.unit_version_refs[1:])})
    decision=UserDecisionRecord.seal(run_id=r,scope=p.runtime.store.load(r).scope,decision_id=r+':derived-world-adoption',category=DecisionCategory.ADOPTION,accepted=True,source_ref=p.film.store.put(adoption_plan))
    receipt=p.reviews.put_user_decision(decision)
    adopted=p.creative_versions.write(writer=Authority.PROFESSIONAL,kind=Kind.PROFESSIONAL,scope=old.scope,body=p.creative_versions.resolve(candidate).body,sources=core,operation=r+':derived-world-adopted',candidate_origin=candidate,adoption_decision=receipt)
    refs=tuple(adopted if v==old.ref() else v for v in unit.refs);p.creative_versions.remember_selection(old.scope,refs)
    native=NativeCreativeSources(p.creative_versions,refs,p.execution_references);pkg=p.production_packages.get(unit.package_ref)
    sources=tuple(s.model_copy(update={'reference':native.project(p.creative_versions.resolve(adopted)).reference('content')}) if s.domain=='WORLD' else s for s in pkg.sources)
    pr=p.production_packages.put(ProductionPackage.freeze(PackageContent.model_validate({**pkg.model_dump(exclude={'package_id','fingerprint'}),'sources':sources})))
    changed=unit.model_copy(update={'refs':refs,'package_ref':pr});cp=p.film.store.checkpoint(r)
    p.film.store.save(r,p.runtime.store.load(r).scope,FilmCheckpoint.model_validate({**cp.model_dump(),
        'units':(changed,*cp.units[1:]),'scene_media_run_ids':(first,)}))
    task=await p.prepare_source_film_unit(r,task=await descriptor(p,r,changed,1,mode='reference'))
    assert task.execution_reference_refs[0]!=prior_ref
    assert p.execution_references.resolve(prior_ref)==prior_binding
    child=p.create_media_review_run(package_ref=pr,task=task,offline_authorization=auth)
    current_check=media_units.validate_child_package
    def old_equality(plugin,cid,u):
        if plugin.gate_findings.inputs(cid).package_ref!=u.package_ref:raise ValueError('Legacy frozen/current package comparison')
        return current_check(plugin,cid,u)
    monkeypatch.setattr(media_units,'validate_child_package',old_equality)
    p.queue_source_film_media(r,tasks=(task,));await p.resume_source_film_run(r)
    failed=p.runtime.store.load(r).last_result
    assert failed.code=='FILM_AUTHORITY_OR_CONTRACT_INVALID' and len(creates)==1
    assert p.runtime.store.load(child.run_id).state==RuntimeState.PLANNED
    monkeypatch.setattr(media_units,'validate_child_package',current_check)
    await p.resume_source_film_run(r)
    await finish(p,child.run_id,pr);await p.resume_source_film_run(r)
    assert p.runtime.store.load(child.run_id).state==RuntimeState.SUCCEEDED and len(creates)==2
    assert p.runtime.store.load(r).external_repairs[-1].failed_result==failed
    assert p.generation_artifacts.get(p.generation_artifacts.prepared(first),GenerationPreparation).model_dump_json()==frozen
    assert media_units.validate_child_package(p,first,changed)==unit.package_ref
    wrong=changed.model_copy(update={'scene_id':'wrong-scene'})
    with pytest.raises(ValueError,match='SCENE_CONTINUATION_SCOPE_MISMATCH'):media_units.validate_child_package(p,first,wrong)
    await p.resume_source_film_run(r);assert len(creates)==2
