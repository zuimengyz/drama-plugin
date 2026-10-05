"""M01–M11, current immutable adopted authority + temporary owners/ledger only.

All new scope/review/cost decisions below are offline simulations, never a live
user decision. HTTP POSTs terminate in MockTransport; socket use is forbidden.
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
import socket
import subprocess
import httpx
import pytest
from pydantic import SecretStr, ValidationError

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig, ServiceConfig
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.media import Media
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.contracts.video import CostEstimate
from drama_plugin.creative_engine.contracts import Kind
from drama_plugin.execution.contracts import Authorization, MediaBinding, ExecutionOperation, TechnicalMediaReview, CreativeMediaReview, ProviderAttempt, ProviderRequest
from drama_plugin.execution.formal_media import FormalMediaStore
from drama_plugin.execution.live_transport import TargetHttpTransport, FinancialTerms, ControlledLiveGrant, wire_payload
from drama_plugin.execution.media import inspect
from drama_plugin.execution.review import HumanReviewer, MockReviewer, ReviewResponse
from drama_plugin.execution.transport import CapabilityAbsent
from drama_plugin.generation.contracts import GenerationTask, GenerationPreparation, FinalPromptArtifact, PromptIR, PromptCoverage, AudioExecutionPlan, OwnerBindings, OperationSelection
from drama_plugin.generation.operation import resolve_profile
from drama_plugin.production.contracts import ProductionPackage, DomainReference
from drama_plugin.providers.http.client import HttpProviderClient
from drama_plugin.providers.http.providers import HttpMediaProvider
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.providers.video.adapters import SeedanceProvider
from drama_plugin.providers.video.registry import ProviderSettings
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeRun, RuntimeScope, RuntimeState, CapabilityInput
from drama_plugin.persistence.review import UserDecisionRecord

FIXTURE = Path(__file__).parent / 'fixtures/e3-m2-adopted.json'
ROOT = Path(__file__).resolve().parents[1]
FAKE_SECRET = 'OFFLINE-CONTRACT-ONLY-NOT-A-CREDENTIAL'


@pytest.fixture(autouse=True)
def no_external_calls(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('No actual network/creative author/legacy production in M2')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(socket.socket,'connect_ex',forbidden)
    monkeypatch.setattr('drama_plugin.creative_engine.backends.TextCompositionBackend.complete',forbidden)
    monkeypatch.setattr('drama_plugin.hosts.http_video.VideoProviderHost.generate',forbidden,raising=False)
    monkeypatch.setattr('drama_plugin.professional.compile_prompt_projection',forbidden)
    monkeypatch.setattr('drama_plugin.runtime.bridge.LegacyCapabilityBridge.execute',forbidden)
    monkeypatch.setattr('drama_plugin.hosts.route_production.operate',forbidden)
    monkeypatch.setattr('drama_plugin.config.loader.load_config',lambda *args,**kwargs:DramaPluginConfig())
    monkeypatch.setattr('drama_plugin.plugin.load_config',lambda *args,**kwargs:DramaPluginConfig())


@pytest.fixture(scope='module')
def video(tmp_path_factory):
    path=tmp_path_factory.mktemp('m2-physical')/'fixture.mp4'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=c=black:s=1280x720:r=24:d=4',
        '-f','lavfi','-i','sine=frequency=220:duration=4','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',
        '-shortest','-y',str(path)],check=True,capture_output=True)
    return path


class MediaService:
    """Real multipart/request shape; only service/transport endpoint is simulated."""
    def __init__(self, video):
        self.video=video; self.records=[]; self.imports=0; self.downloads=0
    def handler(self,request):
        assert request.headers.get('Authorization')=='Bearer '+FAKE_SECRET
        if request.url.path=='/media/list':
            return httpx.Response(200,json=self.records)
        if request.url.path=='/media/import':
            metadata=json.loads(re.search(rb'name="metadata"\r\nContent-Type: application/json\r\n\r\n(.*?)\r\n--',request.content,re.S).group(1))
            claim=metadata['content']['targetNativeScope'];origin=json.loads(claim['originJson'])
            assert hmac.compare_digest(claim['signature'],hmac.new(FAKE_SECRET.encode(),claim['originJson'].encode(),hashlib.sha256).hexdigest())
            assert origin['scope']['workId']==metadata['work_id'] and origin['scope']['shotId']==metadata['shot_id']
            assert {r['identity'].split(':')[0] for r in origin['adoptedRefs']} >= {'creative-source','creative-work','creative-script','creative-scene','creative-shot'}
            assert origin['contentSha256']==hashlib.sha256(self.video.read_bytes()).hexdigest()
            self.imports+=1
            item=Media(id='canonical-service-media-1',work_id=metadata['work_id'],shot_id=metadata['shot_id'],
                source_ref=metadata['source_ref'],media_type='VIDEO',mime_type='video/mp4',
                file_size=self.video.stat().st_size,content_hash=origin['contentSha256'],duration_ms=metadata['duration_ms'],content=metadata['content'])
            self.records.append(item.model_dump(mode='json',by_alias=True))
            return httpx.Response(200,json=self.records[-1])
        if request.url.path=='/media/resolve':
            return httpx.Response(200,json={'mediaId':'canonical-service-media-1','url':'/media/content',
                'expiresAt':(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()})
        if request.url.path=='/media/content':
            self.downloads+=1
            return httpx.Response(200,content=self.video.read_bytes())
        raise AssertionError(str(request.url))
    def provider(self):
        cfg=ServiceConfig(base_url='https://service.invalid',api_token=FAKE_SECRET,operations={
            'list_media':'/media/list','import_media':'/media/import','resolve_media':'/media/resolve'})
        return HttpMediaProvider(HttpProviderClient(cfg,httpx.AsyncClient(base_url=cfg.base_url,
            headers={'Authorization':'Bearer '+FAKE_SECRET},transport=httpx.MockTransport(self.handler))))


def load(tmp_path, monkeypatch, video, *, restore=False, service=None, vendor_calls=None):
    fixture=json.loads(FIXTURE.read_text()); owner=tmp_path/'owners'
    if not restore:
        for relative,content in fixture['ownerFiles'].items():
            file=owner/relative;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(content)
    p=DramaPlugin.load(root=ROOT, mock_data=MockDramaData.empty(),ledger_path=tmp_path/'ledger.sqlite',
        creative_root=owner,target_media_root=tmp_path/'cache',target_reviewer=HumanReviewer())
    if not restore:
        for row in fixture['runs']:
            p.runtime.store.create(RuntimeRun.model_validate_json(row['checkpoint_json']))
        for row in fixture['artifacts']:
            p.ledger.put_artifact(row['artifact_type'],ArtifactReference(owner=row['artifact_type'],artifact_ref=row['artifact_id'],version=row['version']),
                RuntimeScope(work_id=row['work_id'],scene_id=row['scene_id'],shot_id=row['shot_id']),row['fingerprint'],json.loads(row['body_json']))
    service=service or MediaService(video);p.providers.media=service.provider()
    vendor_calls=vendor_calls if vendor_calls is not None else []
    def vendor(request):
        vendor_calls.append(request)
        if request.method=='POST':
            return httpx.Response(200,json={'id':'offline-contract-task','status':'succeeded','content':{'video_url':'https://result.invalid/clip.mp4'}})
        return httpx.Response(200,content=video.read_bytes())
    async def no_reference(_): raise AssertionError('No reference generation')
    adapter=SeedanceProvider('seedance-2-fast',ProviderSettings(base_url='https://ark.cn-beijing.volces.com/api/v3',api_key=SecretStr(FAKE_SECRET)),
        resolve=no_reference,client=httpx.AsyncClient(transport=httpx.MockTransport(vendor)))
    p.execution.transports['seedance']=TargetHttpTransport(adapter,tmp_path/'acks',ledger=p.ledger,qualification_only=True)
    monkeypatch.setenv('DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS',str(tmp_path))
    package=ProductionPackage.model_validate(json.loads(next(r['body_json'] for r in fixture['artifacts'] if r['artifact_type']=='production-package')))
    return p,package,service,vendor_calls


def task_for(p,package):
    fixture=json.loads(FIXTURE.read_text()); rights=fixture['rightsBinding'];dpd=fixture['dpdBinding']
    dpd_pin=SourcePin.model_validate(dpd['manifestPin']);manifest=p.creative_versions.objects.read_ref(dpd_pin)
    refs=fixture['adoption']['afterCheckpoint']['refs']
    owners=OwnerBindings(adopted_refs=refs,dpd_pin=dpd_pin,performance_scope_pin=manifest['projectionScopePin'],
        snapshot_pins=tuple(row['snapshotPin'] for row in manifest['snapshotBindings']),rights_pin=rights['rightsPin'],
        rights_request_ref=rights['requestRef'],rights_decision_ref=rights['decisionRef'],adoption_decision_ref=fixture['adoption']['decisionRef'])
    def leaf(domain,*path):
        parent=next(s.reference for s in package.sources if s.domain==domain and s.reference.owner=='professional')
        return type(parent)(**{**parent.model_dump(),'path':parent.path+path})
    # A bounded production selection of the already-authored opening preparation,
    # not a substitute ending or a compression of the encounter.
    selected=(('ACTION',('actionPhases','0','action')),('PERFORMANCE',('beats','0','tactic')),
        ('CAMERA',('movement','policy')),('CAMERA',('height',)),('WORLD',('setting',)),
        ('WORLD',('weather','ground')),('SUBJECTS',('presentSubjects','0','role')),
        ('SUBJECTS',('presentSubjects','0','inSceneBehaviour')),('SOUND',('ambience','0','design')),
        ('SOUND',('orderingRules','0')),('LIGHTING',('directionAndQuality','0')),
        ('COLOR',('arc','0','colorDecision')),('EDITORIAL',('temporalStructure',)))
    reference=p.creative_versions.resolve(next(r for r in owners.adopted_refs if p.creative_versions.resolve(r).kind==Kind.PROFESSIONAL
        and p.creative_versions.resolve(r).body.domain=='REFERENCE'))
    unit=OperationSelection(beat_ids=('beat-1',),action_refs=(leaf('ACTION','actionPhases','0','action'),),spoken_ids=(),
        start_ref=next(s.reference for s in package.sources if s.reference.path[-1:]==('visualEntryState',)),
        end_ref=leaf('ACTION','actionPhases','0','observable'),
        fact_refs=tuple(DomainReference(domain=d,reference=leaf(d,*path)) for d,path in selected),
        reference_disposition=tuple((r['id'],'TECHNICAL_RISK_ACCEPTED') for r in reference.body.facts['references']))
    profile=resolve_profile(model='seedance-2-fast',duration_ms=4000,resolution='720p',ratio='16:9',native_audio=True,policy=p.config.video_route_policy)
    return GenerationTask(target_model=profile.model,input_mode=profile.mode,native_audio='REQUIRED',unit=unit,profile=profile,owners=owners)


async def prepare_goal(p,package,task, *, offline=True, quote_available=True):
    auth=Authorization(approval_ref=ArtifactReference(owner='user-decision',artifact_ref='offline-proof-simulation'),
        authorized=True,budget_microunits=0,estimated_cost_microunits=0) if offline else None
    run=p.create_media_review_run(package_ref=package.artifact_reference(),task=task,offline_authorization=auth)
    if not offline and quote_available:
        def simulated_cost_owner(run_id, ref):
            prepared=p.generation_artifacts.get(ref,GenerationPreparation)
            final=p.generation_artifacts.get(prepared.final_prompt_ref,FinalPromptArtifact)
            digest=sha256_canonical(TargetHttpTransport.preview(prepared,final));now=datetime.now(timezone.utc)
            quote=CostEstimate(amount=1,currency='CNY',source='OFFLINE_CONTRACT_ONLY_NOT_REAL_QUOTE',checked_at=now,
                expires_at=now+timedelta(minutes=10),request_fingerprint=digest)
            terms=FinancialTerms(preparation_ref=ref,wire_payload_hash=digest,profile=prepared.task.profile,
                cost_quote=quote,budget_microunits=1000000)
            p.ledger.put_index('media-proof-cost-terms',run_id,terms,scope=p.runtime.store.load(run_id).scope,once=True)
        p.generation_capability.on_ready=simulated_cost_owner
    waiting=await p.runtime.run(run.run_id)
    assert waiting.state==RuntimeState.WAITING_USER and waiting.cursor==2
    # This receipt exists solely in the temporary offline ledger.
    await p.decide_target_run(run.run_id,decision_id=p.runtime.decision_id(run.run_id),accepted=True,source_ref=package.artifact_reference())
    return await p.runtime.run(run.run_id)


@pytest.mark.asyncio
async def test_unified_adopted_package_to_real_contract_media_and_human_boundary(tmp_path,monkeypatch,video):
    p,package,service,calls=load(tmp_path,monkeypatch,video);task=task_for(p,package)
    before=package.model_dump_json();versions={f:f.read_bytes() for f in (tmp_path/'owners/objects').glob('*.json')}
    run=await prepare_goal(p,package,task)
    assert run.state==RuntimeState.WAITING_USER and run.cursor==9,run.model_dump()
    assert package.generation_intent.duration_ms==60000 and package.model_dump_json()==before
    prepared=p.generation_artifacts.get(p.generation_artifacts.prepared(run.run_id),GenerationPreparation)
    final=p.generation_artifacts.get(prepared.final_prompt_ref,FinalPromptArtifact)
    plan=p.generation_artifacts.get(prepared.audio_plan_ref,AudioExecutionPlan)
    ir=await p.prompt_compiler.prompt_ir(prepared)
    assert final.task.unit is None and final.task.owners is None and final.task.profile is None
    assert final.matches_task(prepared.task)
    assert not final.matches_task(prepared.task.model_copy(update={"unit":prepared.task.unit.model_copy(update={"beat_ids":("drift",)})}))
    assert p.execution.store.inputs(run.run_id).recipe_ref is None
    with p.ledger.transaction() as db:
        assert db.execute("SELECT count(*) FROM immutable_artifact WHERE artifact_type='finishing-recipe'").fetchone()[0] == 0
    assert not list((tmp_path/'ledger.sqlite.formal-media-refs').glob('*.registration.json'))
    with pytest.raises(KeyError):
        p.generation_artifacts.get(ArtifactReference(owner="prompt-ir",artifact_ref="prompt-ir:"+ir.fingerprint,version=1),PromptIR)
    assert ir.duration_ms==plan.duration_ms==4000 and plan.speech_events==()
    assert {'ACTION','CAMERA','WORLD','SUBJECTS','PERFORMANCE','SOUND','LIGHTING','COLOR','EDITORIAL'} <= {f.domain for f in ir.facts}
    assert len(prepared.task.owners.snapshot_pins)==4
    assert len(prepared.task.unit.reference_disposition)==11
    coverage=p.generation_artifacts.get(final.coverage_ref,PromptCoverage)
    duties=[c for c in coverage.entries if c.fact_id.startswith('reference-duty:')]
    assert len(duties)==11 and sum(c.obligation=='EXECUTION_REQUIRED' for c in duties)==7
    assert all(c.input_ref==prepared.task.unit.scope_decision_ref for c in duties)
    assert len(final.prompt_text)<=5000
    preview=TargetHttpTransport.preview(prepared,final)
    submitted=json.loads(next(r.content for r in calls if r.method=='POST'))
    assert preview==submitted and submitted['content'][0]['text']==final.prompt_text
    assert len([r for r in calls if r.method=='POST'])==1 and service.imports==1
    cp=p.execution.store.checkpoint(p.execution._approved(CapabilityInput(run_id=run.run_id,scope=run.scope,operation_id=run.run_id+':check'))[0].artifact_reference())
    binding=p.execution.store.get(cp.progress.video_ref,MediaBinding)
    qa=p.execution.store.get(cp.progress.video_technical_ref,TechnicalMediaReview)
    assert qa.outcome=='PASS' and abs(qa.observation.duration_ms-4000)<100
    assert binding.canonical_media_ref.artifact_ref=='canonical-service-media-1'
    assert service.records[0]['content']['targetNativeScope']['owner']=='TARGET_CREATIVE_VERSION_OWNER'
    # Process-equivalent restore, cache loss, same canonical bytes, no regeneration/import.
    p.execution.media.path(binding.media).unlink()
    restored,_,_,_=load(tmp_path,monkeypatch,video,restore=True,service=service,vendor_calls=calls)
    recovered=await restored.resume_execution_run(run.run_id)
    assert recovered.state==RuntimeState.WAITING_USER
    await restored.execution.media.restore(run.scope,binding.media)
    assert service.downloads==1 and service.imports==1
    operation=restored.execution.store.get(cp.operation_ref,ExecutionOperation)
    context=restored.execution.review_context(operation,binding.media,binding.canonical_media_ref)
    with pytest.raises(ValueError,match='CONTEXT'):
        restored.execution.record_human_review(run.run_id,media_ref=cp.progress.video_ref,context_hash='0'*64,response=ReviewResponse('PASS'))
    completed=await restored.provide_human_media_review(run.run_id,media_ref=cp.progress.video_ref,context_hash=context,response=ReviewResponse('PASS'))
    assert completed.state==RuntimeState.SUCCEEDED and completed.cursor==10
    cp=restored.execution.store.checkpoint(cp.operation_ref)
    review=restored.execution.store.get(cp.progress.video_creative_ref,CreativeMediaReview)
    assert review.reviewer=='USER' and review.review_context_hash==context
    assert not cp.progress.audio_ref and not cp.progress.av_ref and not cp.progress.candidate_ref
    assert all(f.read_bytes()==content for f,content in versions.items())
    assert restored.creative_versions.resolve(task.owners.adopted_refs[4]).body.duration_ms==60000


@pytest.mark.asyncio
async def test_no_scope_no_cost_no_paid_post(tmp_path,monkeypatch,video):
    p,package,service,calls=load(tmp_path,monkeypatch,video);task=task_for(p,package)
    run=await prepare_goal(p,package,task,offline=False,quote_available=False)
    assert run.state==RuntimeState.WAITING_EXTERNAL and run.cursor==5
    assert run.last_result.external_ref.owner=='generation-preparation'
    prepared=p.generation_artifacts.get(p.generation_artifacts.prepared(run.run_id),GenerationPreparation)
    assert TargetHttpTransport.preview(prepared,p.generation_artifacts.get(prepared.final_prompt_ref,FinalPromptArtifact))
    assert calls==[] and service.imports==0
    with pytest.raises(KeyError):p.execution.store.inputs(run.run_id)


@pytest.mark.parametrize('change',['wrong-work','wrong-shot','stale-version','dpd-missing','profile-drift','reference-drop','metadata-leaf'])
@pytest.mark.asyncio
async def test_owner_and_selection_admission_rejects_before_post(tmp_path,monkeypatch,video,change):
    p,package,service,calls=load(tmp_path,monkeypatch,video);task=task_for(p,package)
    if change in ('wrong-work','wrong-shot','stale-version'):
        refs=list(task.owners.adopted_refs);index=1 if change=='wrong-work' else 4
        refs[index]=refs[index].model_copy(update={'version':2 if change=='stale-version' else 1,'fingerprint':'a'*64})
        task=task.model_copy(update={'owners':task.owners.model_copy(update={'adopted_refs':tuple(refs)})})
    elif change=='dpd-missing':task=task.model_copy(update={'owners':task.owners.model_copy(update={'snapshot_pins':task.owners.snapshot_pins[:-1]})})
    elif change=='profile-drift':task=task.model_copy(update={'profile':task.profile.model_copy(update={'catalog_fingerprint':'a'*64})})
    else:
        unit=task.unit.model_copy(update={'reference_disposition':()} if change=='reference-drop' else
            {'fact_refs':(DomainReference(domain='WORLD',reference=task.unit.fact_refs[4].reference.model_copy(update={'path':('content','sourcePins','0','identity')})),)})
        task=task.model_copy(update={'unit':unit})
    with pytest.raises((ValueError,KeyError,RuntimeError)):
        if change in ('reference-drop','metadata-leaf'):
            await p.operation_resolver.selected(package,task,p.prompt_compiler.reader)
        else:p.create_media_review_run(package_ref=package.artifact_reference(),task=task)
    assert calls==[] and service.imports==0


@pytest.mark.asyncio
async def test_mock_cannot_formal_review_and_qa_uses_resolved_profile(tmp_path,monkeypatch,video):
    p,package,service,calls=load(tmp_path,monkeypatch,video);p.execution.reviewer=MockReviewer()
    run=await prepare_goal(p,package,task_for(p,package))
    assert run.state==RuntimeState.FAILED
    assert run.last_result.code=='FORMAL_MOCK_REVIEW_FORBIDDEN'
    op,_,_=p.execution._approved(CapabilityInput(run_id=run.run_id,scope=run.scope,operation_id=run.run_id+':check'))
    cp=p.execution.store.checkpoint(op.artifact_reference());binding=p.execution.store.get(cp.progress.video_ref,MediaBinding)
    assert p.execution.store.get(cp.progress.video_technical_ref,TechnicalMediaReview).outcome=='PASS'
    assert cp.progress.video_creative_ref is None
    _,failures=inspect(p.execution.media,binding.media,duration_ms=60000,tolerance_ms=500,audio_expected=True,resolution='1080p',aspect_ratio='9:16')
    assert {'RESULT_DURATION_MISMATCH','RESULT_RESOLUTION_MISMATCH','RESULT_ASPECT_RATIO_MISMATCH'} <= set(failures)


def test_budget_and_profile_terms_are_bounded_and_legacy_receipts_unchanged():
    fixture=json.loads(FIXTURE.read_text())
    for row in fixture['artifacts']:
        if row['artifact_type']=='user-decision':
            receipt=UserDecisionRecord.model_validate_json(row['body_json'])
            assert receipt.fingerprint==row['fingerprint'] and 'termsHash' not in receipt.model_dump(mode='json',by_alias=True)
    profile=resolve_profile(model='seedance-2-fast',duration_ms=4000,resolution='720p',ratio='16:9',native_audio=True,policy=DramaPluginConfig().video_route_policy)
    now=datetime.now(timezone.utc)
    quote=CostEstimate(amount=1,currency='CNY',source='OFFLINE_CONTRACT_ONLY',checked_at=now,expires_at=now+timedelta(minutes=5),request_fingerprint='a'*64)
    prep=ArtifactReference(owner='generation-preparation',artifact_ref='generation-preparation:'+'a'*64,version=1)
    terms=FinancialTerms(preparation_ref=prep,wire_payload_hash='a'*64,profile=profile,cost_quote=quote,budget_microunits=1000000)
    terms.validate_current()
    with pytest.raises(ValidationError):FinancialTerms.model_validate({**terms.model_dump(),'max_paid_operations':2})
    for changed in ({'budget_microunits':1},{'wire_payload_hash':'b'*64},
        {'cost_quote':quote.model_copy(update={'expires_at':now-timedelta(seconds=1)})}):
        with pytest.raises(ValueError):terms.model_copy(update=changed).validate_current()

@pytest.mark.asyncio
async def test_cross_process_human_revise_cache_recovery_without_paid_retry(tmp_path,monkeypatch,video):
    import sys
    p,package,service,calls=load(tmp_path,monkeypatch,video)
    run=await prepare_goal(p,package,task_for(p,package))
    op,_,_=p.execution._approved(CapabilityInput(run_id=run.run_id,scope=run.scope,operation_id=run.run_id+':read'))
    cp=p.execution.store.checkpoint(op.artifact_reference())
    binding=p.execution.store.get(cp.progress.video_ref,MediaBinding)
    p.execution.media.path(binding.media).unlink()
    import shutil
    shutil.rmtree(tmp_path/'ledger.sqlite.formal-media-refs')
    records=tmp_path/'canonical-records.json';records.write_text(json.dumps(service.records))
    script='''
import asyncio, importlib.util, json, pathlib, sys, pytest
spec=importlib.util.spec_from_file_location("m2_tests",sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
mp=pytest.MonkeyPatch();m.no_external_calls.__wrapped__(mp)
root=pathlib.Path(sys.argv[2]);video=pathlib.Path(sys.argv[3]);service=m.MediaService(video)
service.records=json.loads((root/"canonical-records.json").read_text())
p,package,service,calls=m.load(root,mp,video,restore=True,service=service)
async def main():
 run=await p.resume_execution_run(sys.argv[4])
 op,_,_=p.execution._approved(m.CapabilityInput(run_id=run.run_id,scope=run.scope,operation_id=run.run_id+":read"))
 cp=p.execution.store.checkpoint(op.artifact_reference());binding=p.execution.store.get(cp.progress.video_ref,m.MediaBinding)
 await p.execution.media.restore(run.scope,binding.media)
 context=p.execution.review_context(op,binding.media,binding.canonical_media_ref)
 from drama_plugin.execution.contracts import ReviewObservation
 result=await p.provide_human_media_review(run.run_id,media_ref=cp.progress.video_ref,context_hash=context,
  response=m.ReviewResponse("REVISE",(ReviewObservation(code="PERFORMANCE_REVISE",owner="professional",finding="Offline human boundary exercise.",required_revision="Return exact referenced professional version to its owner."),)))
 print(json.dumps(dict(state=result.state.value,cursor=result.cursor,post=len([r for r in calls if r.method=="POST"]),imports=service.imports,downloads=service.downloads)))
asyncio.run(main())
'''
    child=subprocess.run([sys.executable,'-c',script,str(Path(__file__).resolve()),str(tmp_path),str(video),run.run_id],
        check=True,capture_output=True,text=True,timeout=45)
    result=json.loads(child.stdout.strip().splitlines()[-1])
    assert result==dict(state='SUCCEEDED',cursor=10,post=0,imports=0,downloads=1)
    recovered=p.execution.store.checkpoint(cp.operation_ref)
    review=p.execution.store.get(recovered.progress.video_creative_ref,CreativeMediaReview)
    assert review.outcome=='REVISE' and review.media==binding.media
    assert len([r for r in calls if r.method=='POST'])==1
    assert not recovered.progress.audio_ref and not recovered.progress.av_ref

@pytest.mark.asyncio
async def test_exact_financial_preview_and_drift_never_reserve_or_submit(tmp_path,monkeypatch,video):
    p,package,service,calls=load(tmp_path,monkeypatch,video)
    run=await prepare_goal(p,package,task_for(p,package),offline=False)
    prep=p.generation_artifacts.get(p.generation_artifacts.prepared(run.run_id),GenerationPreparation)
    final=p.generation_artifacts.get(prep.final_prompt_ref,FinalPromptArtifact)
    preview=TargetHttpTransport.preview(prep,final);now=datetime.now(timezone.utc)
    quote=CostEstimate(amount=1,currency='CNY',source='OFFLINE_CONTRACT_ONLY_NOT_REAL_QUOTE',checked_at=now,
        expires_at=now+timedelta(minutes=10),request_fingerprint=sha256_canonical(preview))
    terms=FinancialTerms(preparation_ref=prep.artifact_reference(),wire_payload_hash=sha256_canonical(preview),
        profile=prep.task.profile,cost_quote=quote,budget_microunits=1000000)
    for bad in (terms.model_copy(update={'profile':terms.profile.model_copy(update={'model':'seedance-2'})}),
                terms.model_copy(update={'wire_payload_hash':'b'*64}),
                terms.model_copy(update={'cost_quote':quote.model_copy(update={'request_fingerprint':'b'*64})}),
                terms.model_copy(update={'cost_quote':quote.model_copy(update={'expires_at':now-timedelta(seconds=1)})}),
                terms.model_copy(update={'budget_microunits':1})):
        with pytest.raises(ValueError):await p.provide_media_cost_terms(run.run_id,bad)
        assert p.runtime.store.load(run.run_id).cursor==6
    waiting=await p.provide_media_cost_terms(run.run_id,terms)
    assert waiting.state==RuntimeState.WAITING_USER and waiting.cursor==6
    # No accepted cost, grant or reserved operation even with exact terms ready.
    assert calls==[] and service.imports==0
    with pytest.raises(KeyError):p.execution.store.inputs(run.run_id)
    request=ProviderRequest(model=prep.task.profile.model,input_mode='text_to_video',prompt_text=final.prompt_text,
        duration_ms=4000,native_audio='REQUIRED',profile=prep.task.profile)
    for profile in (request.profile.model_copy(update={'provider':'vidu'}),
                    request.profile.model_copy(update={'vendor_model_id':'wrong-vendor-id'})):
        with pytest.raises(ValueError):wire_payload(request.model_copy(update={'profile':profile}),provider='seedance',resolution='720p',aspect_ratio='16:9')
    with pytest.raises(CapabilityAbsent):wire_payload(request.model_copy(update={'prompt_text':'x'*5001}),provider='seedance',resolution='720p',aspect_ratio='16:9')
    assert calls==[]


def test_reference_mode_has_one_execution_spelling_and_historical_input_remains_readable():
    from drama_plugin.creative_engine.contracts import RouteRequest
    from drama_plugin.creative_engine.routes import RouteSelector
    selector=RouteSelector()
    legacy=RouteRequest(input_mode='reference_video',available_inputs=('character_reference','environment_reference'),available_capabilities=('reference_video',))
    modern=RouteRequest(input_mode='reference',available_inputs=legacy.available_inputs,available_capabilities=('reference',))
    assert selector.plan(legacy)==selector.plan(modern)
    assert selector.plan(legacy).route=='reference' and legacy.input_mode=='reference_video'


@pytest.mark.asyncio
async def test_exact_derived_owner_indexes_recover_without_author_or_new_post(tmp_path,monkeypatch,video):
    p,package,service,calls=load(tmp_path,monkeypatch,video)
    run=await prepare_goal(p,package,task_for(p,package))
    assert run.state==RuntimeState.WAITING_USER
    prep_ref=p.generation_artifacts.prepared(run.run_id)
    prepared=p.generation_artifacts.get(prep_ref,GenerationPreparation)
    final=p.generation_artifacts.get(prepared.final_prompt_ref,FinalPromptArtifact)
    gate_ref=p.gate_findings.latest(run.run_id)
    key=sha256_canonical([prepared.source_package_ref.model_dump(mode='json'),
        prepared.task.model_dump(mode='json'),final.generator_policy_fingerprint])
    post_count=len([r for r in calls if r.method=='POST'])
    with p.ledger.transaction(write=True) as db:
        db.execute("DELETE FROM ledger_index WHERE index_type='prepared' AND index_key=?",(run.run_id,))
        db.execute("DELETE FROM ledger_index WHERE index_type='latest-decision' AND index_key=?",(run.run_id,))
        db.execute("DELETE FROM ledger_index WHERE index_type='final-prompt-key' AND index_key=?",(key,))
    restored,_,_,_=load(tmp_path,monkeypatch,video,restore=True,service=service,vendor_calls=calls)
    assert restored.gate_findings.latest(run.run_id)==gate_ref
    assert restored.generation_artifacts.prepared(run.run_id)==prep_ref
    assert restored.generation_artifacts.final_for(key)==prepared.final_prompt_ref
    assert (await restored.resume_execution_run(run.run_id)).state==RuntimeState.WAITING_USER
    assert len([r for r in calls if r.method=='POST'])==post_count==1
    assert service.imports==1

@pytest.mark.asyncio
async def test_simulated_exact_cost_receipt_is_the_only_financial_authority(tmp_path,monkeypatch,video):
    """Live admission code with MockTransport only; no real decision/quote/grant."""
    p,package,service,calls=load(tmp_path,monkeypatch,video)
    run=await prepare_goal(p,package,task_for(p,package),offline=False)
    prep=p.generation_artifacts.get(p.generation_artifacts.prepared(run.run_id),GenerationPreparation)
    final=p.generation_artifacts.get(prep.final_prompt_ref,FinalPromptArtifact);now=datetime.now(timezone.utc)
    digest=sha256_canonical(TargetHttpTransport.preview(prep,final))
    quote=CostEstimate(amount=1,currency='CNY',source='OFFLINE_CONTRACT_ONLY_NOT_REAL_QUOTE',checked_at=now,
        expires_at=now+timedelta(minutes=10),request_fingerprint=digest)
    terms=FinancialTerms(preparation_ref=prep.artifact_reference(),wire_payload_hash=digest,profile=prep.task.profile,
        cost_quote=quote,budget_microunits=1000000)
    await p.provide_media_cost_terms(run.run_id,terms)
    # All decisions here exist only inside pytest's temporary ledger.
    await p.decide_target_run(run.run_id,decision_id=p.runtime.decision_id(run.run_id),accepted=True,source_ref=prep.artifact_reference())
    assert calls==[]
    adapter=p.execution.transports['seedance'].adapter
    p.execution.transports['seedance']=TargetHttpTransport(adapter,tmp_path/'acks',ledger=p.ledger,qualification_only=False)
    reviewed=await p.runtime.run(run.run_id)
    assert reviewed.state==RuntimeState.WAITING_USER and reviewed.cursor==9
    transport=p.execution.transports['seedance'];grant=transport.grant
    receipt=UserDecisionRecord.model_validate(p.ledger.get_artifact('user-decision',grant.decision_ref)[0])
    assert receipt.terms_hash==terms.fingerprint and grant.terms==terms
    assert grant.budget_microunits==terms.budget_microunits
    rights_claim='rights:'+prep.task.owners.rights_decision_ref.artifact_ref
    assert ArtifactReference.model_validate(p.ledger.get_index('execution-live-grant',rights_claim))==grant.artifact_reference()
    with pytest.raises(ValueError,match='already set'):
        p.ledger.put_index('execution-live-grant',rights_claim,
            ArtifactReference(owner='controlled-live-grant',artifact_ref='controlled-live-grant:'+'b'*64,version=1),scope=run.scope,once=True)
    assert len([r for r in calls if r.method=='POST'])==1
