"""E3-A uses physical offline media; fixture decisions are never live acceptance."""
from pathlib import Path
import hashlib
import subprocess
import pytest
from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.creative_engine.contracts import SourceBody, WorkBody, ScriptBody, SceneBody, ShotBody, DesignBody, AuthorRequest, CanonDraft
from drama_plugin.film.contracts import (FilmCanon, FilmDirection, CanonScene, DirectedShot, LanguageMetadata, DeliveryProfile,
    FinalCreativeReview, FinalFilmCandidate, FinalDelivery, FilmCheckpoint, FilmAuthorRequest)
from drama_plugin.execution.contracts import Authorization, FinishingRecipe, ProviderResult
from drama_plugin.execution.transport import ReplayTransport
from drama_plugin.execution.review import MockReviewer
from drama_plugin.execution.audio import ApprovedAudioConsumer
from drama_plugin.runtime.contracts import ArtifactReference, RunMode, RuntimeState, DecisionCategory

REF=ArtifactReference(owner='source-owner',artifact_ref='fixture-rights-and-language',version=1)

class Authors:
    def __init__(self, scenes=2,shots=2):
        self.scenes,self.shots=scenes,shots
        self.calls=[]
    async def author_film(self, request:FilmAuthorRequest)->FilmCanon:
        self.calls.append('film-canon')
        return FilmCanon(work=WorkBody(interpretation='An interrupted appeal exposes denied responsibility.',dramatic_intent='Follow a refusal into remembered concern.',character_meaning='An indifferent claim is unstable.'),
            script=ScriptBody(screenplay='An encounter is followed by its remembered consequence.'),
            scenes=tuple(CanonScene(scene_id=f'canon-scene-{i}',scene=SceneBody(scene_text=f'Approved causal beat {i} from the designated source')) for i in range(self.scenes)))
    async def direct_film(self,request:FilmAuthorRequest)->FilmDirection:
        self.calls.append('film-direction')
        assert request.canon
        return FilmDirection(shots=tuple(DirectedShot(scene_id=s.scene_id,shot_id=f'{s.scene_id}-view-{j}',shot=self.body()) for s in request.canon.scenes for j in range(self.shots)))
    def body(self):
        return ShotBody(purpose='Observe the approved beat',required_transition='Complete the approved action',duration_ms=4000,
            subject_action='An observable gesture ends',entry_state='Before the gesture',exit_state='After the gesture',coverage='One legible relation',
            blocking_intent='Maintain the relation',camera_intent='Observe the gesture',editing_relation='Cut after the gesture',performance_direction='Complete the gesture',
            professional_domains=tuple(sorted(('CAMERA','LIGHTING','SOUND','SUBJECTS','WORLD'))))
    async def author(self,request:AuthorRequest):
        self.calls.append('revision:'+('canon' if request.canon is None else 'direction'))
        if request.revision and request.revision.owner.value=='canon-author':
            assert request.canon
            return CanonDraft(work=request.canon.work,script=request.canon.script,scene=SceneBody(scene_text=request.canon.scene.scene_text+'; revised'))
        return self.body().model_copy(update={'purpose':'Revised approved intent'})
    async def design(self,request:AuthorRequest):
        self.calls.append('professional:'+request.scope.shot_id)
        return (DesignBody(domain='CAMERA',facts={'perspective':'Legible relation','camera_movement':'Fixed'}),
            DesignBody(domain='LIGHTING',facts={'source':'Approved visible source','direction':'Side'}),
            DesignBody(domain='SOUND',facts={'ambience':'Approved quiet bed','silence_design':'No additional score'}),
            DesignBody(domain='SUBJECTS',facts={'character_ref':'source-person','face_structure':'Approved subject identity'}),
            DesignBody(domain='WORLD',facts={'location_identity':'Source location','topology':'Open passage'}))

class Recipes:
    def recipe(self,**values):
        return FinishingRecipe.seal(scope=values['scope'],run_id=values['run_id'],source_package_ref=values['package_ref'],
            preparation_ref=values['preparation_ref'],audio_plan_ref=values['audio_plan_ref'],approval_ref=REF,native_policy='PRESERVE')
    def authorization(self,package_ref):
        return Authorization(approval_ref=REF,authorized=True,budget_microunits=0,estimated_cost_microunits=0)

class Reviewer:
    async def review_film(self,candidate):
        return FinalCreativeReview.seal(scope=candidate.scope,run_id=candidate.run_id,film_version=candidate.film_version,
            candidate_ref=candidate.artifact_reference(),media_hash=candidate.media.content_hash,reviewer='offline-fixture-reviewer',
            qualification='OFFLINE_FIXTURE',outcome='PASS')

@pytest.fixture
def video(tmp_path):
    path=tmp_path/'fixture.mp4'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=c=black:s=160x90:r=24:d=4',
        '-f','lavfi','-i','sine=frequency=220:duration=4','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest','-y',str(path)],check=True)
    return path

def load(tmp_path,monkeypatch,video,authors=None,**kwargs):
    import drama_plugin.plugin as module
    monkeypatch.setattr(module,'load_config',lambda _:DramaPluginConfig())
    a=authors or Authors()
    p=DramaPlugin.load(mock_data=MockDramaData(),ledger_path=tmp_path/'film.sqlite',creative_root=tmp_path/'creative',
        target_media_root=tmp_path/'media',canon_author=a,direction_author=a,professional_author=a,
        film_canon_author=a,film_direction_author=a,film_reviewer=Reviewer(),film_recipes=Recipes(),
        target_audio=ApprovedAudioConsumer(),target_reviewer=MockReviewer(),
        target_transports={'offline-replay':ReplayTransport(tmp_path/'remote',ProviderResult(result_id='physical-offline-fixture',locator=str(video),expected_hash=hashlib.sha256(video.read_bytes()).hexdigest()))},**kwargs)
    return p,a

def create(p,run_id='film'):
    return p.create_source_film_run(work_id='film-work',run_id=run_id,source=SourceBody(goal='Bounded film adaptation',text='Designated source text.',spoken_language='ru'),
        languages=LanguageMetadata(source_document_language='en',original_work_language='ru',spoken_language='ru',authority_ref=REF),
        profile=DeliveryProfile(width=160,height=90),rights_refs=(REF,),route='offline-replay',model='seedance-2-standard')

async def approve(p,run_id,ref):
    await p.decide_target_run(run_id,decision_id=p.runtime.decision_id(run_id),accepted=True,source_ref=ref)
    run = await p.runtime.run(run_id)
    if run.workflow_id in {'source-to-final-film:v1','final-film-revision:v1'} and run.state == RuntimeState.WAITING_EXTERNAL and run.last_result.external_ref.owner == 'execution-child':
        run = await p.resume_source_film_run(run_id)
    return run

@pytest.mark.asyncio
async def test_source_multiple_scenes_shots_final_delivery_restore(tmp_path,monkeypatch,video):
    p,a=load(tmp_path,monkeypatch,video)
    before=p.providers.memory.data.work.model_dump_json()
    run=create(p)
    run=await p.runtime.run(run.run_id)
    assert run.state==RuntimeState.WAITING_USER,run
    cp=p.film.store.checkpoint(run.run_id)
    assert len(cp.units)==4 and len({u.scene_id for u in cp.units})==2
    assert a.calls.count('film-canon')==a.calls.count('film-direction')==1
    p2,a2=load(tmp_path,monkeypatch,video)
    run=await approve(p2,run.run_id,cp.plan_ref)
    assert run.state==RuntimeState.WAITING_USER,run
    cp=p2.film.store.checkpoint(run.run_id)
    assert cp.final_ref and cp.qa_ref and cp.review_ref
    assert all(u.candidate_ref for u in cp.units)
    assert not a2.calls
    final=p2.film.store.get(cp.final_ref,FinalFilmCandidate)
    assert len(final.shots)==4 and final.duration_ms>=16000
    p3,a3=load(tmp_path,monkeypatch,video)
    done=await approve(p3,run.run_id,cp.final_ref)
    assert done.state==RuntimeState.SUCCEEDED,done
    cp=p3.film.store.checkpoint(run.run_id)
    delivery=p3.film.store.get(cp.delivery_ref,FinalDelivery)
    assert delivery.media==final.media and delivery.candidate_ref==cp.final_ref
    body,scope,_=p3.ledger.get_artifact('user-decision',delivery.acceptance_ref)
    assert body['category']==DecisionCategory.FINAL_ACCEPTANCE.value
    assert p.providers.memory.data.work.model_dump_json()==before
    assert len(p3.runtime.store.load('film').model_dump_json())<32768
    assert len(cp.model_dump_json())<32768
    assert len((tmp_path/'remote'/'submissions.jsonl').read_text().splitlines())==4
    await p3.resume_source_film_run('film')
    assert len((tmp_path/'remote'/'submissions.jsonl').read_text().splitlines())==4
    assert not a3.calls

@pytest.mark.asyncio
@pytest.mark.parametrize('owner',['canon_author','direction_author','professional_author'])
async def test_film_missing_author_waits_no_fallback(tmp_path,monkeypatch,video,owner):
    p,a=load(tmp_path,monkeypatch,video)
    from drama_plugin.execution.transport import CapabilityAbsent
    with pytest.raises(CapabilityAbsent,match='SOURCE_ORIGINAL_WORK_LANGUAGE_METADATA_ABSENT'):
        p.create_source_film_run(work_id='film-work',run_id='missing-language',
            source=SourceBody(goal='Unknown original language',text='Translated source',spoken_language='en'),
            profile=DeliveryProfile(width=160,height=90),rights_refs=(REF,),route='offline-replay',model='seedance-2-standard')
    if owner=='professional_author':
        p.creative.professional_author.author=None
    else:
        setattr(p.film,owner,None)
    run=create(p)
    run=await p.runtime.run(run.run_id)
    assert run.state==RuntimeState.WAITING_EXTERNAL,run
    assert not (tmp_path/'remote'/'submissions.jsonl').exists()

@pytest.mark.asyncio
async def test_exact_film_decision_scope_hash(tmp_path,monkeypatch,video):
    p,a=load(tmp_path,monkeypatch,video)
    run=await p.runtime.run(create(p).run_id)
    with pytest.raises(ValueError,match='exact immutable'):
        await approve(p,run.run_id,REF)
    assert p.runtime.store.load(run.run_id).state==RuntimeState.WAITING_USER

@pytest.mark.parametrize('changes',[{'original_work_language':''},{'spoken_language':'en'},{'source_document_language':''}])
def test_language_never_infers_original_from_translation(changes):
    with pytest.raises(ValueError):
        LanguageMetadata.model_validate({'source_document_language':'en','original_work_language':'ru','spoken_language':'ru','authority_ref':REF,**changes})

@pytest.mark.asyncio
async def test_final_subtitle_without_measured_speech_waits(tmp_path,monkeypatch,video):
    p,a=load(tmp_path,monkeypatch,video)
    run=create(p)
    inp=p.film.store.input(run.run_id)
    from drama_plugin.film.contracts import FilmInput
    p.ledger.put_index('film-input',run.run_id,FilmInput.model_validate({**inp.model_dump(),'profile':DeliveryProfile(width=160,height=90,subtitle_required=True), 'languages':inp.languages.model_copy(update={'subtitle_language':'ru'})}),scope=run.scope)
    run=await p.runtime.run(run.run_id)
    run=await approve(p,run.run_id,p.film.store.checkpoint(run.run_id).plan_ref)
    assert run.state==RuntimeState.WAITING_EXTERNAL and run.cursor==6,run
    assert p.film.store.checkpoint(run.run_id).final_ref is None

@pytest.mark.asyncio
async def test_final_rejection_rebuilds_one_shot_only(tmp_path,monkeypatch,video):
    from drama_plugin.film.contracts import FilmRevisionFeedback
    from drama_plugin.creative_engine.contracts import Authority, Kind, RevisionRequest
    p,a=load(tmp_path,monkeypatch,video)
    run=await p.runtime.run(create(p).run_id)
    run=await approve(p,'film',p.film.store.checkpoint('film').plan_ref)
    assert run.state==RuntimeState.WAITING_USER
    original=p.film.store.checkpoint('film')
    rejected=await p.decide_target_run('film',decision_id=p.runtime.decision_id('film'),accepted=False,source_ref=original.final_ref)
    rejection_ref=rejected.last_result.artifact_refs[0]
    target=next(r for r in original.units[0].refs if p.creative_versions.resolve(r).kind==Kind.SHOT)
    feedback=FilmRevisionFeedback.seal(scope=run.scope,run_id='film',film_version=1,candidate_ref=original.final_ref,
        decision_or_review_ref=rejection_ref,requests=(RevisionRequest(owner=Authority.DIRECTION,target_ref=target,
            finding_ref=rejection_ref,instruction='Clarify the approved gesture without changing dialogue',depth=1),))
    revision=p.film.revision_run('film',feedback,'film-revised')
    waiting=await p.runtime.run(revision.run_id)
    assert waiting.state==RuntimeState.WAITING_EXTERNAL,waiting
    unit=p.film.store.checkpoint(revision.run_id).units[0]
    child=p.runtime.store.load(unit.production_run_id)
    assert child.state==RuntimeState.WAITING_USER,child
    childcp=p.creative.state.checkpoint(child.run_id)
    await approve(p,child.run_id,childcp.candidate_ref)
    resumed=await p.resume_source_film_run(revision.run_id)
    assert resumed.state==RuntimeState.WAITING_USER,resumed
    new=p.film.store.checkpoint(revision.run_id)
    assert new.units[0].candidate_ref!=original.units[0].candidate_ref
    assert [u.candidate_ref for u in new.units[1:]]==[u.candidate_ref for u in original.units[1:]]
    assert len((tmp_path/'remote'/'submissions.jsonl').read_text().splitlines())==5
    done=await approve(p,revision.run_id,new.final_ref)
    assert done.state==RuntimeState.SUCCEEDED,done
    assert p.film.store.get(p.film.store.checkpoint(revision.run_id).delivery_ref,FinalDelivery).film_version==2

@pytest.mark.asyncio
async def test_shared_scene_version_is_really_shared_and_wrong_feedback_rejected(tmp_path,monkeypatch,video):
    from drama_plugin.creative_engine.contracts import Kind
    p,a=load(tmp_path,monkeypatch,video)
    await p.runtime.run(create(p).run_id)
    cp=p.film.store.checkpoint('film')
    scene_refs=[next(r for r in u.refs if p.creative_versions.resolve(r).kind==Kind.SCENE) for u in cp.units]
    assert scene_refs[0]==scene_refs[1] and scene_refs[2]==scene_refs[3] and scene_refs[0]!=scene_refs[2]
    work_refs=[next(r for r in u.refs if p.creative_versions.resolve(r).kind==Kind.WORK) for u in cp.units]
    assert len(set(work_refs))==1

class SpeakingAuthors(Authors):
    async def author_film(self,request):
        from drama_plugin.creative_engine.contracts import Dialogue
        from drama_plugin.film.contracts import SubtitleLocalization
        from drama_plugin.contracts.base import sha256_canonical
        base=await super().author_film(request)
        return FilmCanon(work=base.work,script=base.script,scenes=tuple(CanonScene(scene_id=s.scene_id,
            scene=SceneBody(scene_text=s.scene.scene_text,dialogue=(Dialogue(id='spoken-line',speaker='fixture-speaker',text='Фраза.',must_keep=True),)),
            subtitle_localizations=(SubtitleLocalization(dialogue_id='spoken-line',source_text_hash=sha256_canonical('Фраза.'),language='zh',text='句子。'),)) for s in base.scenes))
    def body(self):
        return super().body().model_copy(update={'spoken_ids':('spoken-line',)})
    async def design(self,request):
        designs=await super().design(request)
        return tuple(DesignBody(domain='SOUND',facts={'silence_design':'No additional sound bed'}) if d.domain.value=='SOUND' else DesignBody(domain='SUBJECTS',facts={'character_ref':'fixture-speaker','face_structure':'Approved speaker identity'}) if d.domain.value=='SUBJECTS' else d for d in designs)

class SpeakingRecipes(Recipes):
    def __init__(self,plugin,tmp_path):
        self.plugin,self.tmp_path=plugin,tmp_path
    def recipe(self,**values):
        from drama_plugin.generation.contracts import AudioExecutionPlan
        from drama_plugin.execution.contracts import AudioPlacement
        plan=self.plugin.generation_artifacts.get(values['audio_plan_ref'],AudioExecutionPlan)
        clip=self.tmp_path/'measured-speech.wav'
        if not clip.exists():
            subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=1.25','-y',str(clip)],check=True)
        media=self.plugin.execution.media.retain(clip.read_bytes(),kind='AUDIO',mime='audio/wav')
        placements=tuple(AudioPlacement(event_id=e.event_id,source_ref=e.source_ref,media=media,start_ms=0,gain_db=0) for e in plan.speech_events)
        return FinishingRecipe.seal(scope=values['scope'],run_id=values['run_id'],source_package_ref=values['package_ref'],
            preparation_ref=values['preparation_ref'],audio_plan_ref=values['audio_plan_ref'],approval_ref=REF,native_policy='REPLACE',placements=placements)

@pytest.mark.asyncio
@pytest.mark.parametrize('subtitle_language',['ru','zh'])
async def test_subtitles_use_actual_speech_duration_and_final_av_offset(tmp_path,monkeypatch,video,subtitle_language):
    from drama_plugin.film.contracts import FilmInput
    p,a=load(tmp_path,monkeypatch,video,authors=SpeakingAuthors(scenes=2,shots=1))
    p.film.recipes=SpeakingRecipes(p,tmp_path)
    run=create(p)
    original=p.film.store.input(run.run_id)
    languages=original.languages.model_copy(update={'subtitle_language':subtitle_language})
    updated=FilmInput.model_validate({**original.model_dump(),'languages':languages,
        'profile':DeliveryProfile(width=160,height=90,subtitle_required=True)})
    p.ledger.put_index('film-input',run.run_id,updated,scope=run.scope)
    await p.runtime.run(run.run_id)
    done=await approve(p,run.run_id,p.film.store.checkpoint(run.run_id).plan_ref)
    assert done.state==RuntimeState.WAITING_USER,done
    cp=p.film.store.checkpoint(run.run_id)
    final=p.film.store.get(cp.final_ref,FinalFilmCandidate)
    assert final.subtitle_ref
    digest=final.subtitle_ref.artifact_ref.rsplit(':',1)[1]
    srt=(p.execution.media.directory/(digest+'.srt')).read_text()
    assert ('句子。' if subtitle_language=='zh' else 'Фраза.') in srt
    assert '00:00:00,000 --> 00:00:01,250' in srt
    assert '00:00:04,010' in srt or '00:00:04,000' in srt or '00:00:04,023' in srt
    qa=p.film.store.get(cp.qa_ref,__import__('drama_plugin.film.contracts',fromlist=['FinalTechnicalQA']).FinalTechnicalQA)
    assert qa.outcome=='PASS' and 'subtitle_presence' in qa.checks and 'av_sync' in qa.checks

@pytest.mark.asyncio
async def test_shared_canon_revision_routes_once_then_rebuilds_affected_scene(tmp_path,monkeypatch,video):
    from drama_plugin.film.contracts import FilmRevisionFeedback
    from drama_plugin.creative_engine.contracts import Authority, Kind, RevisionRequest
    p,a=load(tmp_path,monkeypatch,video)
    await p.runtime.run(create(p).run_id)
    run=await approve(p,'film',p.film.store.checkpoint('film').plan_ref)
    old=p.film.store.checkpoint('film')
    declined=await p.decide_target_run('film',decision_id=p.runtime.decision_id('film'),accepted=False,source_ref=old.final_ref)
    decision_ref=declined.last_result.artifact_refs[0]
    target=next(r for r in old.units[0].refs if p.creative_versions.resolve(r).kind==Kind.SCENE)
    feedback=FilmRevisionFeedback.seal(scope=run.scope,run_id='film',film_version=1,candidate_ref=old.final_ref,
        decision_or_review_ref=decision_ref,requests=(RevisionRequest(owner=Authority.CANON,target_ref=target,
            finding_ref=decision_ref,instruction='Clarify this Scene dramatic intent',depth=1),))
    revised=p.film.revision_run('film',feedback,'scene-revision')
    done=await p.runtime.run(revised.run_id)
    for _ in range(3):
        cp=p.film.store.checkpoint(revised.run_id)
        waiting=[p.runtime.store.load(u.production_run_id) for u in cp.units if u.package_ref is None]
        for child in waiting:
            if child.state==RuntimeState.WAITING_USER:
                await approve(p,child.run_id,p.creative.state.checkpoint(child.run_id).candidate_ref)
        done=await p.resume_source_film_run(revised.run_id)
        if done.state==RuntimeState.WAITING_USER:
            break
    assert done.state==RuntimeState.WAITING_USER,done
    new=p.film.store.checkpoint(revised.run_id)
    assert [u.candidate_ref for u in old.units[2:]]==[u.candidate_ref for u in new.units[2:]]
    assert all(u.candidate_ref!=old.units[i].candidate_ref for i,u in enumerate(new.units[:2]))
    scene_refs=[next(r for r in u.refs if p.creative_versions.resolve(r).kind==Kind.SCENE) for u in new.units[:2]]
    assert scene_refs[0]==scene_refs[1] and scene_refs[0]!=target
    assert len((tmp_path/'remote'/'submissions.jsonl').read_text().splitlines())==6
    assert sum(call.startswith('revision:') for call in a.calls)==3  # One Canon, two Shot revisions.

@pytest.mark.asyncio
async def test_final_delivery_cannot_borrow_wrong_acceptance_or_review(tmp_path,monkeypatch,video):
    p,a=load(tmp_path,monkeypatch,video,authors=Authors(scenes=1,shots=1))
    await p.runtime.run(create(p).run_id)
    await approve(p,'film',p.film.store.checkpoint('film').plan_ref)
    cp=p.film.store.checkpoint('film')
    await approve(p,'film',cp.final_ref)
    cp=p.film.store.checkpoint('film')
    item=p.film.store.get(cp.delivery_ref,FinalDelivery)
    bad=FinalDelivery.seal(**{**item.model_dump(exclude={'fingerprint'}),'acceptance_ref':cp.adoption_ref})
    with pytest.raises(ValueError,match='Final acceptance'):
        p.film.store.put(bad)
    candidate=p.film.store.get(cp.final_ref,FinalFilmCandidate)
    wrong_ref=candidate.shots[0].shot_ref.model_copy(update={'version':999})
    wrong_shot=candidate.shots[0].model_copy(update={'shot_ref':wrong_ref})
    wrong_candidate=FinalFilmCandidate.seal(**{**candidate.model_dump(exclude={'fingerprint'}),'shots':(wrong_shot,)})
    with pytest.raises(ValueError,match='unapproved Shot version'):
        p.film.store.put(wrong_candidate)

@pytest.mark.asyncio
async def test_final_review_auto_routes_exact_owner_and_parent_resumes(tmp_path,monkeypatch,video):
    from drama_plugin.execution.contracts import ReviewObservation
    class RevisingReviewer(Reviewer):
        async def review_film(self,candidate):
            if ':final-revision:' in candidate.run_id:
                return await super().review_film(candidate)
            return FinalCreativeReview.seal(scope=candidate.scope,run_id=candidate.run_id,film_version=candidate.film_version,
                candidate_ref=candidate.artifact_reference(),media_hash=candidate.media.content_hash,reviewer='offline-fixture-reviewer',
                qualification='OFFLINE_FIXTURE',outcome='REVISE',affected_shots=(candidate.shots[0].shot_id,),
                observations=(ReviewObservation(code='SHOT_INTENT',owner='shot',finding='One gesture needs clarification',required_revision='Clarify this gesture'),))
    p,a=load(tmp_path,monkeypatch,video)
    p.film.reviewer=RevisingReviewer()
    await p.runtime.run(create(p).run_id)
    run=await approve(p,'film',p.film.store.checkpoint('film').plan_ref)
    assert run.state==RuntimeState.WAITING_EXTERNAL
    for _ in range(5):
        for decision_run in p.pending_film_decisions('film'):
            if decision_run.workflow_id=='source-to-approved-package:v1':
                target=p.creative.state.checkpoint(decision_run.run_id).candidate_ref
            else:
                target=p.film.store.checkpoint(decision_run.run_id).final_ref
            await approve(p,decision_run.run_id,target)
        run=await p.resume_source_film_run('film')
        if run.state==RuntimeState.SUCCEEDED:
            break
    assert run.state==RuntimeState.SUCCEEDED,run
    assert p.film.store.get(p.film.store.checkpoint('film').delivery_ref,FinalDelivery).film_version==2
    assert len((tmp_path/'remote'/'submissions.jsonl').read_text().splitlines())==5
