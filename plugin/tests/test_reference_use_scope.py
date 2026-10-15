"""Text-only B3 proofs: immutable bindings -> actual serialized reference request."""
from copy import deepcopy
from hashlib import sha256
import json
import socket
import subprocess

import pytest

from drama_plugin.contracts.media import Media
from drama_plugin.execution.live_transport import TargetHttpTransport
from drama_plugin.generation.audio import package_scope
from drama_plugin.generation.contracts import GenerationPreparation, FinalPromptArtifact, PromptCoverage
from drama_plugin.generation.operation import resolve_profile
from drama_plugin.generation.sources import child
from drama_plugin.production.references import ReferenceExecutionBinding
from drama_plugin.production.contracts import SourceDomain
from test_event_scope_delivery import material, pipeline


@pytest.fixture(autouse=True)
def text_only(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('B3 forbids network, subprocesses and media generation')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)
    monkeypatch.setattr(subprocess, 'Popen', deny)


class ExactMediaRecords:
    """Offline snapshot lookup, not a delivery/URL resolver or fabricated bytes."""
    def __init__(self, records):
        self.records = {m.id:m for m in records}
        self.reads = []

    async def get_media(self, identity):
        self.reads.append(identity)
        return self.records[identity]


def reference_material(purpose):
    req, raw = material(single=True)
    req = req.model_copy(update={'shot':req.shot.model_copy(update={
        'professional_domains':tuple(sorted((*req.shot.professional_domains, SourceDomain.REFERENCE)))})})
    raw.append({'domain':'REFERENCE','facts':{'references':[
        {'priority':'REQUIRED','beatSelections':[1], 'designPurpose':'Use only the approved reference property.',
         'inputDuty':purpose}]}})
    raw[5]['facts']['audio_events'][0]['delivery_mode'] = 'ON_SCREEN'
    return req, raw


async def compile_bound(p, compiler, package, base, bindings, media_records):
    """Use the real selector/resolver/compiler; bypass production admission only
    through the existing volatile preview path, never provenance or hash checks.
    """
    compiler.reader.resolver.references = p.execution_references
    refs = tuple(p.execution_references.register(b) for b in bindings)
    compiler.references.media_reader = ExactMediaRecords(media_records)
    input_ids = set()
    for binding in bindings:
        use = binding.use_ref
        if use and use.path[1:2] == ('references',):
            row = await compiler.reader.resolver.resolve(use.model_copy(update={'path':use.path[:3]}))
            input_ids.add(row['id'])
    unit = base['task'].unit.model_copy(update={'reference_disposition':tuple(
        (identity,'INPUT' if identity in input_ids else disposition)
        for identity,disposition in base['task'].unit.reference_disposition)})
    mode = 'image_to_video' if len(bindings)==1 and bindings[0].role=='FIRST_FRAME' else 'reference'
    profile = resolve_profile(model=base['task'].target_model,
        duration_ms=None if base['task'].profile.duration_mode=='AUTO' else base['task'].profile.requested_duration_ms,
        resolution='720p',ratio='16:9',native_audio=True,mode=mode,policy=compiler.reader.operations.policy)
    task = base['task'].model_copy(update={'unit':unit,'profile':profile,
        'input_mode':mode,'execution_reference_refs':refs})
    result = await compiler.compile(package.artifact_reference(),task)
    assert result.preparation_ref, compiler.artifacts.diagnostics(result.diagnostics_ref)
    ready = compiler.artifacts.get(result.preparation_ref,GenerationPreparation)
    final = compiler.artifacts.get(ready.final_prompt_ref,FinalPromptArtifact)
    wire = json.loads(json.dumps(TargetHttpTransport.preview(ready,final,ledger=p.ledger)))
    assert wire['content'][0]['text']==final.prompt_text
    assert not ready.provider_submission_allowed
    coverage = compiler.artifacts.get(final.coverage_ref,PromptCoverage)
    assert sum(e.status=='REFERENCE_COVERED' for e in coverage.entries)==sum(len(b.duties) for b in bindings)
    assert set(compiler.references.media_reader.reads)=={b.media.media_id for b in bindings}
    return dict(task=task,ready=ready,final=final,wire=wire,coverage=coverage)


def fixture_binding(package, base, purpose, *, role='CHARACTER', kind='image', version=1):
    reference = next(s.reference for s in package.sources if s.domain=='REFERENCE' and s.reference.owner=='professional')
    use = child(reference,'references','0','inputDuty')
    subject = 'courier' if role=='CHARACTER' else 'approved-action'
    semantics = {'CHARACTER':'identity','PERFORMANCE':'motion','COMPOSITION':'camera','CONTINUITY':'continuity'}[role]
    return ReferenceExecutionBinding(binding_id='scoped-use',version=version,scope=package_scope(package),
        media=dict(media_id='retained-reference',version='1',content_hash=sha256(b'text-only-fixture').hexdigest(),
            kind=kind,semantics=(semantics,),width=1280,height=720,duration=4 if kind=='video' else None,
            review_ref='fixture-prior-review'),
        duties=(dict(role=role,necessity='REQUIRED',subject=subject,purpose=purpose),),
        subject_ids=('courier',) if role=='CHARACTER' else (), role='REFERENCE',
        authorization_scope='REVIEWED_TRIAL_INPUT',authority_refs=(use,),use_ref=use,state_ref=base['task'].unit.start_ref)


def fixture_media(binding):
    return Media(id=binding.media.media_id,work_id=binding.scope.work_id,shot_id=binding.origin_scope.shot_id,
        media_type=binding.media.kind.upper(),content_hash=binding.media.content_hash,
        source_ref='OFFLINE_FIXTURE_METADATA_ONLY',mime_type='image/png' if binding.media.kind=='image' else 'video/mp4')


@pytest.mark.parametrize('role,purpose',[
    ('PERFORMANCE','Approved motion and pose reference: retain the receiving-hand release without importing the face or spoken words.'),
    ('COMPOSITION','Approved composition reference: retain the doorway framing and seated pose, without importing identity or completed action.')])
async def test_approved_performance_and_composition_are_not_negated(tmp_path,monkeypatch,role,purpose):
    req,raw=reference_material(purpose)
    p,compiler,package,out=await pipeline(tmp_path,monkeypatch,req,raw)
    try:
        binding=fixture_binding(package,out[0],purpose,role=role,kind='video' if role=='PERFORMANCE' else 'image')
        row=await compile_bound(p,compiler,package,out[0],[binding],[fixture_media(binding)])
        text=row['wire']['content'][0]['text']
        assert purpose in text
        assert 'Do not inherit its background, opening action, pose, lighting, camera progress or completed speech.' not in text
        assert len(row['wire']['content'])==2
        assert row['wire']['content'][1]['role']=='reference_'+binding.media.kind
    finally: await p.aclose()


async def test_identity_reference_keeps_current_speech_and_listener_closed_mouth(tmp_path,monkeypatch):
    purpose='Stable face and body identity only. Costume, pose and vocal delivery follow the selected current design.'
    req,raw=reference_material(purpose)
    raw[0]['facts']['actionPhases'][0]['action']='The courier speaks once while the keeper listens with mouth closed, holding the packet.'
    p,compiler,package,out=await pipeline(tmp_path,monkeypatch,req,raw,duration=None)
    try:
        b=fixture_binding(package,out[0],purpose)
        row=await compile_bound(p,compiler,package,out[0],[b],[fixture_media(b)])
        text=row['wire']['content'][0]['text']
        assert row['wire']['duration']==-1 and row['task'].profile.duration_mode=='AUTO'
        assert 'keeper listens with mouth closed' in text
        assert text.count('{Помогите.}')==1 and purpose in text
        assert b.media.content_hash in json.dumps(row['wire'])
    finally: await p.aclose()


async def test_bad_historical_duty_is_not_silently_rewritten_by_compiler(tmp_path,monkeypatch):
    bad='Identity portrait: courier must keep mouth closed throughout the shot.'
    req,raw=reference_material(bad)
    p,compiler,package,out=await pipeline(tmp_path,monkeypatch,req,raw)
    try:
        b=fixture_binding(package,out[0],bad)
        row=await compile_bound(p,compiler,package,out[0],[b],[fixture_media(b)])
        text=row['wire']['content'][0]['text']
        assert bad in text and '{Помогите.}' in text
        # The contradictory design stays a negative result; no keyword scrubber.
    finally: await p.aclose()


@pytest.mark.parametrize('version',[5,6])
async def test_frozen_reference_policy_recovery_and_cache_isolation(tmp_path,monkeypatch,version):
    from drama_plugin.generation.contracts import AudioExecutionPlan, PromptIR
    from drama_plugin.generation.seedance import ModelPolicyCatalog
    purpose='Approved performance pose; target design controls identity and speech.'
    req,raw=reference_material(purpose)
    p,compiler,package,out=await pipeline(tmp_path,monkeypatch,req,raw)
    try:
        binding=fixture_binding(package,out[0],purpose,role='PERFORMANCE')
        current=await compile_bound(p,compiler,package,out[0],[binding],[fixture_media(binding)])
        task,ready=current['task'],current['ready']
        select=compiler.reader.operations.selected
        async def offline_selected(package,task,reader,**kw):
            return await select(package,task,reader,admission_required=False)
        monkeypatch.setattr(compiler.reader.operations,'selected',offline_selected)
        selected=await offline_selected(package,task,compiler.reader)
        plan=compiler.artifacts.get(ready.audio_plan_ref,AudioExecutionPlan)
        view=await compiler.projection.project(package,task,plan,selected,
            legacy_scope=version==5,legacy_reference_use=version==6)
        old_ir=PromptIR.seal(**{**view.ir.model_dump(exclude={'fingerprint','execution_reference_refs'}),
            'execution_reference_refs':current['final'].execution_reference_refs})
        policy=(ModelPolicyCatalog().legacy_scope_policy(task.target_model) if version==5 else
            ModelPolicyCatalog().legacy_reference_use_policy(task.target_model))
        references=await compiler.references.resolve(package,task,selected,
            subjects={f.subject_id for f in view.ir.facts if f.subject_id})
        old_text=compiler.generator.generate(old_ir,plan,policy=policy,input_mode=task.input_mode,
            references=references.inputs,profile=task.profile if version==6 else None)['prompt']
        assert 'Do not inherit its background, opening action, pose' in old_text
        old_final=FinalPromptArtifact.seal(**{**current['final'].model_dump(exclude={'fingerprint'}),
            'generator_policy_fingerprint':policy.fingerprint,'prompt_ir_fingerprint':old_ir.fingerprint,'prompt_text':old_text})
        old_ready=GenerationPreparation.seal(**{**ready.model_dump(exclude={'fingerprint'}),
            'final_prompt_ref':compiler.artifacts.put(old_final)})
        old_ref=compiler.artifacts.put(old_ready)
        assert (await compiler.prompt_ir(old_ready)).fingerprint==old_ir.fingerprint
        old_wire=json.loads(json.dumps(TargetHttpTransport.preview(old_ready,old_final,ledger=p.ledger)))
        assert old_wire['content'][0]['text']==old_text
        assert old_wire['content'][1:]==current['wire']['content'][1:]
        assert compiler.stale(old_ref,package.artifact_reference(),task)
        rebuilt=await compiler.compile(package.artifact_reference(),task)
        assert compiler.artifacts.get(rebuilt.preparation_ref,GenerationPreparation).final_prompt_ref==ready.final_prompt_ref
        assert (await compiler.prompt_ir(ready)).fingerprint==current['final'].prompt_ir_fingerprint
        bad=FinalPromptArtifact.seal(**{**old_final.model_dump(exclude={'fingerprint'}),'generator_policy_fingerprint':'f'*64})
        bad_ready=GenerationPreparation.seal(**{**old_ready.model_dump(exclude={'fingerprint'}),
            'final_prompt_ref':compiler.artifacts.put(bad)})
        with pytest.raises(ValueError,match='OPERATION_PROJECTION_DRIFT'):
            await compiler.prompt_ir(bad_ready)
    finally: await p.aclose()


async def test_ordinary_reference_cannot_claim_opening_or_video_endpoint(tmp_path,monkeypatch):
    from pydantic import ValidationError
    purpose='Identity only; no opening-state authority.'
    req,raw=reference_material(purpose)
    p,compiler,package,out=await pipeline(tmp_path,monkeypatch,req,raw)
    try:
        b=fixture_binding(package,out[0],purpose)
        raw_binding=b.model_dump()
        raw_binding['duties'][0]['establishes_opening_state']=True
        with pytest.raises(ValidationError,match='A character/look reference alone is not an opening frame'):
            ReferenceExecutionBinding.model_validate(raw_binding)
        raw_binding['duties'][0]['role']='CONTINUITY'
        raw_binding['subject_ids']=()
        raw_binding['role']='FIRST_FRAME'; raw_binding['endpoint_state']='reviewed-start'
        # Metadata contract accepts the correct image role; no claim of real frame review.
        image=ReferenceExecutionBinding.model_validate(raw_binding)
        assert image.role=='FIRST_FRAME' and image.media.kind=='image'
        raw_binding['media']['kind']='video'; raw_binding['media']['duration']=4
        with pytest.raises(ValidationError,match='Endpoint requires an image and reviewed state'):
            ReferenceExecutionBinding.model_validate(raw_binding)
        raw_binding['media']['kind']='image'; raw_binding['media']['duration']=None
        raw_binding['endpoint_state']=None
        with pytest.raises(ValidationError,match='Endpoint requires an image and reviewed state'):
            ReferenceExecutionBinding.model_validate(raw_binding)
        row=await compile_bound(p,compiler,package,out[0],[b],[fixture_media(b)])
        assert row['wire']['content'][1]['role']=='reference_image'
        assert 'first_frame' not in json.dumps(row['wire'])
    finally: await p.aclose()


def test_asset_candidate_producer_does_not_copy_portrait_state_or_make_location(monkeypatch):
    """Existing automatic producer scope only; full asset adoption E2E is B4."""
    from types import SimpleNamespace as NS
    import drama_plugin.film.media_references as module
    import drama_plugin.creative_engine.sources as sources
    from drama_plugin.production.contracts import SourceReference
    from drama_plugin.runtime.contracts import RuntimeScope
    scope=RuntimeScope(work_id='W',scene_id='current-scene',shot_id='current-shot')
    def asset(identity,kind,subject,hash_character):
        return dict(id=identity,assetType=kind,content={'specializedAsset':dict(subjectId=subject,
            stableIdentity=subject,establishedSceneId='origin-scene',
            adoptionRef=dict(key='retained-adoption',fingerprint=hash_character*64),
            state='INCIDENTAL_CLOSED_MOUTH',pose='INCIDENTAL_SEATED_POSE',background='INCIDENTAL_ROOM')},
            resolvedMedia=[dict(mediaId=identity+'-media',version='1',contentHash=hash_character*64,
                mediaType='IMAGE',width=1280,height=720)])
    subjects=NS(scope=scope,body=NS(facts={'presentSubjects':[{'id':'courier'}],
        'assetBindings':[asset('portrait','CHARACTER','courier','a'),asset('other-person','CHARACTER','keeper','b')]}))
    world=NS(scope=scope,body=NS(facts={'locationAssetId':'room','assetBindings':[asset('room','LOCATION','hall','c')]}))
    class Native:
        def __init__(self,*args):pass
        def project(self,original):self.original=original;return self
        def reference(self,*path):return SourceReference(owner='professional',artifact_ref='subjects' if self.original==subjects else 'world',
            version=1,fingerprint='d'*64,path=path)
    monkeypatch.setattr(sources,'NativeCreativeSources',Native)
    monkeypatch.setattr(module,'professional',lambda p,u,d:subjects if d=='SUBJECTS' else world)
    start=SourceReference(owner='professional',artifact_ref='action',version=1,fingerprint='e'*64,path=('content','entryState'))
    selection=NS(start_ref=start,fact_refs=(NS(domain='SUBJECTS',reference=NS(path=('content','presentSubjects','0'))),))
    result=module.asset_reference_candidates(NS(creative_versions=None,execution_references=None),NS(refs=()),selection)
    assert len(result)==2
    assert [b.duties[0].role for b in result]==['CHARACTER','LOCATION']
    assert [b.media.media_id for b in result]==['portrait-media','room-media']
    assert all(b.role=='REFERENCE' and not b.duties[0].establishes_opening_state and b.state_ref==start for b in result)
    text=' '.join(d.purpose for b in result for d in b.duties)
    assert 'INCIDENTAL_' not in text
    assert 'target scene costume, state, lighting and physical location' in text
    assert 'Background is not a location reference' in result[0].duties[0].purpose
    assert 'Accepted physical space' in result[1].duties[0].purpose
    assert result[0].media.review_ref=='asset-adoption:portrait:'+'a'*64
    assert result[1].media.review_ref=='retained-adoption:'+'c'*64
