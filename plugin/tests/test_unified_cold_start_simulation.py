"""Entire fresh Target path; all decisions and side effects stay in temporary mock owners."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import socket

import httpx
import pytest
from pydantic import SecretStr
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.video import CostEstimate
from drama_plugin.execution.contracts import CreativeMediaReview, MediaBinding, TechnicalMediaReview
from drama_plugin.execution.live_transport import FinancialTerms, TargetHttpTransport
from drama_plugin.execution.review import HumanReviewer, ReviewResponse
from drama_plugin.generation.contracts import GenerationPreparation, FinalPromptArtifact
from drama_plugin.providers.video.adapters import SeedanceProvider
from drama_plugin.providers.video.registry import ProviderSettings
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeState
from test_unified_planning_recovery import load, create
from test_unified_mainline import MediaService, FAKE_SECRET, video


@pytest.mark.asyncio
async def test_source_entry_crash_reentry_recovers_one_source_and_run(tmp_path,monkeypatch):
    p,_=load(tmp_path,monkeypatch)
    original=p.film.store.bind
    def interrupted(*args,**kwargs):
        raise RuntimeError('simulated entry interruption after Source commit')
    monkeypatch.setattr(p.film.store,'bind',interrupted)
    with pytest.raises(RuntimeError):create(p)
    source_ops=list((tmp_path/'owners/creative-index').glob('operation-*.json'))
    assert len(source_ops)==1
    fixed=source_ops[0].read_bytes()
    monkeypatch.setattr(p.film.store,'bind',original)
    run=create(p)
    assert create(p)==run and run.state==RuntimeState.PLANNED
    assert source_ops[0].read_bytes()==fixed
    assert len(list((tmp_path/'owners/creative-index').glob('operation-*.json')))==1
    with p.ledger.transaction() as db:
        assert db.execute('SELECT COUNT(*) FROM production_run').fetchone()[0]==1
    with pytest.raises(ValueError,match='immutable|binding|conflict'):
        p.create_source_film_run(work_id='wrong-work',run_id=run.run_id,source=p.creative_versions.resolve(p.film.store.input(run.run_id).source_ref).body,
            languages=p.film.store.input(run.run_id).languages,profile=p.film.store.input(run.run_id).profile,
            rights_refs=p.film.store.input(run.run_id).rights_refs,route='seedance',model='seedance-2-fast')


@pytest.mark.asyncio
@pytest.mark.parametrize('human_outcome,provider_pending',[('PASS',False),('REVISE',False),('PASS',True)])
async def test_empty_source_to_canonical_media_and_exact_human_receipt(tmp_path,monkeypatch,video,human_outcome,provider_pending):
    p,authors=load(tmp_path,monkeypatch)
    service=MediaService(video);p.providers.media=service.provider();p.execution.reviewer=HumanReviewer()
    vendor_calls=[]
    def vendor(request):
        vendor_calls.append(request)
        if request.method=='POST':
            if provider_pending:
                return httpx.Response(200,json={'id':'fresh-offline-task','status':'running'})
            return httpx.Response(200,json={'id':'fresh-offline-task','status':'succeeded','content':{'video_url':'https://result.invalid/proof.mp4'}})
        if request.url.host=='ark.cn-beijing.volces.com':
            return httpx.Response(200,json={'id':'fresh-offline-task','status':'succeeded','content':{'video_url':'https://result.invalid/proof.mp4'}})
        return httpx.Response(200,content=video.read_bytes())
    async def no_reference(_):raise AssertionError('No reference generation in fresh proof')
    adapter=SeedanceProvider('seedance-2-fast',ProviderSettings(base_url='https://ark.cn-beijing.volces.com/api/v3',api_key=SecretStr(FAKE_SECRET)),
        resolve=no_reference,client=httpx.AsyncClient(transport=httpx.MockTransport(vendor)))
    p.execution.transports['seedance']=TargetHttpTransport(adapter,tmp_path/'ack',ledger=p.ledger,qualification_only=False)
    monkeypatch.setenv('DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS',str(tmp_path))
    original=p.generation_capability.on_ready
    def mock_cost_owner(run_id,preparation_ref):
        # Deterministic external quote fixture, supplied by the test owner only.
        prepared=p.generation_artifacts.get(preparation_ref,GenerationPreparation)
        final=p.generation_artifacts.get(prepared.final_prompt_ref,FinalPromptArtifact)
        digest=sha256_canonical(TargetHttpTransport.preview(prepared,final))
        now=datetime.now(timezone.utc)
        quote=CostEstimate(currency='CNY',amount=1,source='OFFLINE_COST_FIXTURE_NO_PAID_ACTION',
            checked_at=now,expires_at=now+timedelta(hours=1),request_fingerprint=digest)
        terms=FinancialTerms(preparation_ref=preparation_ref,profile=prepared.task.profile,
            wire_payload_hash=digest,cost_quote=quote,budget_microunits=1000000,max_paid_operations=1)
        p.ledger.put_index('media-proof-cost-terms',run_id,terms,scope=p.runtime.store.load(run_id).scope,once=True)
        if original:original(run_id,preparation_ref)
    p.generation_capability.on_ready=mock_cost_owner
    run=create(p);run=await p.runtime.run(run.run_id)
    assert run.state==RuntimeState.WAITING_USER and run.cursor==3
    cp=p.film.store.checkpoint(run.run_id)
    await p.decide_target_run(run.run_id,decision_id=p.runtime.decision_id(run.run_id),accepted=True,source_ref=cp.plan_ref)
    run=await p.runtime.run(run.run_id)
    assert run.state==RuntimeState.WAITING_USER and run.cursor==5
    rights=p.film.pending_decision(run.run_id)[1]
    await p.decide_target_run(run.run_id,decision_id=p.runtime.decision_id(run.run_id),accepted=True,source_ref=rights)
    run=await p.runtime.run(run.run_id)
    assert run.state==RuntimeState.WAITING_USER,run.model_dump_json()
    child_id=next(r.artifact_ref for r in run.last_result.artifact_refs if r.owner=='runtime')
    child=p.runtime.store.load(child_id)
    assert p.runtime.next_action(child_id).decision.category.value=='COST_APPROVAL'
    preparation_ref=p.generation_artifacts.prepared(child_id)
    prepared=p.generation_artifacts.get(preparation_ref,GenerationPreparation)
    package=p.production_packages.get(prepared.source_package_ref)
    assert package.generation_intent.duration_ms==60000
    assert prepared.task.profile.requested_duration_ms==4000 and not prepared.task.profile.native_audio
    assert prepared.task.unit.spoken_ids==()
    assert prepared.task.owners.dpd_pin is not None
    assert not vendor_calls
    await p.decide_target_run(run.run_id,decision_id=p.runtime.decision_id(run.run_id),accepted=True,source_ref=preparation_ref)
    run=await p.runtime.run(run.run_id)
    if provider_pending:
        child=p.runtime.store.load(child_id)
        assert run.state==child.state==RuntimeState.WAITING_EXTERNAL
        assert run.last_result.external_ref==child.last_result.external_ref
        assert len([r for r in vendor_calls if r.method=='POST'])==1
        run=await p.resume_source_film_run(run.run_id)
    child=p.runtime.store.load(child_id)
    assert run.state==RuntimeState.WAITING_USER,child.model_dump_json()
    assert child.state==RuntimeState.WAITING_USER and child.last_result.user_decision.category.value=='ART_APPROVAL'
    media_ref=next(r for r in child.last_result.artifact_refs if r.owner=='media-binding')
    binding=p.execution.store.get(media_ref,MediaBinding)
    with p.ledger.transaction() as db:
        row=db.execute("SELECT artifact_id FROM immutable_artifact WHERE artifact_type='execution-operation' AND json_extract(body_json,'$.runId')=?",(child_id,)).fetchone()
    from drama_plugin.execution.contracts import ExecutionOperation
    operation=p.execution.store.get(ArtifactReference(owner='execution-operation',artifact_ref=row[0],version=1),ExecutionOperation)
    checkpoint=p.execution.store.checkpoint(operation.artifact_reference())
    qa=p.execution.store.get(checkpoint.progress.video_technical_ref,TechnicalMediaReview)
    assert qa.outcome=='PASS' and abs(qa.observation.duration_ms-4000)<100
    assert binding.canonical_media_ref.artifact_ref=='canonical-service-media-1'
    final=p.generation_artifacts.get(prepared.final_prompt_ref,FinalPromptArtifact)
    posted=[request for request in vendor_calls if request.method=='POST']
    assert len(posted)==1 and json.loads(posted[0].content)['content'][0]['text']==final.prompt_text
    assert service.imports==1 and authors.calls==['canon','direction','professional']
    context=p.execution.review_context(operation,binding.media,binding.canonical_media_ref)
    from drama_plugin.execution.contracts import ReviewObservation
    observations=(ReviewObservation(code='PERFORMANCE_REVISE',owner='professional',finding='Offline human observation.',
        required_revision='Review the exact approved performance version.'),) if human_outcome=='REVISE' else ()
    result=await p.provide_human_media_review(run.run_id,media_ref=media_ref,context_hash=context,response=ReviewResponse(human_outcome,observations))
    assert result.state==RuntimeState.SUCCEEDED,result.model_dump()
    review=p.execution.store.get(result.last_result.artifact_refs[0],CreativeMediaReview)
    assert review.outcome==human_outcome and review.reviewer=='USER'
    assert review.review_context_hash==context and review.preparation_ref==preparation_ref
    assert not checkpoint.progress.audio_ref and not checkpoint.progress.av_ref
    assert len([request for request in vendor_calls if request.method=='POST'])==1 and service.imports==1
    assert authors.calls==['canon','direction','professional']
