"""Target transport reuses vendor serializers/parsers, never their Host workflow.

Qualification mode accepts only an in-process MockTransport. Live submission
requires an exact persisted cost decision and a one-operation grant, independently
of whether credentials exist. Query never creates an operation.
"""
from __future__ import annotations
from pathlib import Path
from typing import Literal, ClassVar
from collections.abc import Mapping
from urllib.parse import urlsplit
import httpx
from pydantic import Field, JsonValue, TypeAdapter
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.video import ProviderTask, CostEstimate
from drama_plugin.execution.contracts import ExecutionOperation, ProviderAttempt, ProviderRequest, ProviderReceipt, ProviderResult
from drama_plugin.execution.transport import CapabilityAbsent, DefinitelyNotSubmitted, PossiblySubmitted, IntakeTransient
from drama_plugin.execution.media import atomic_write
from drama_plugin.providers.video.base import HttpVideoProvider, SafeProviderError
from drama_plugin.providers.video.registry import registry
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeContract, ExtendedRuntimeContract, DecisionCategory, RuntimeScope
from drama_plugin.generation.contracts import ExecutionProfile, GenerationPreparation, FinalPromptArtifact
from drama_plugin.persistence.review import UserDecisionRecord
from drama_plugin.persistence.ledger import ProductionLedger

def wire_payload(request: ProviderRequest, *, provider: str, resolution: str, aspect_ratio: str) -> dict[str, JsonValue]:
    if request.input_mode!='text_to_video' or request.references:
        raise CapabilityAbsent('TARGET_HTTP_REFERENCE_SERIALIZER_ABSENT')
    spec=registry()['models'][request.model]
    if request.duration_ms%1000 or request.duration_ms//1000 not in spec.get('durations',[request.duration_ms//1000]):
        raise CapabilityAbsent('PROVIDER_DURATION_UNSUPPORTED')
    if resolution not in spec['resolutions'] or aspect_ratio not in spec['aspect_ratios'] or len(request.prompt_text)>spec['prompt_limit']:
        raise CapabilityAbsent('PROVIDER_PROFILE_OR_PROMPT_LIMIT_UNSUPPORTED')
    if provider != spec['provider']:
        raise ValueError('MODEL_PROVIDER_MISMATCH')
    if request.profile and (request.profile.model != request.model or request.profile.provider != provider
            or request.profile.requested_duration_ms != request.duration_ms
            or request.profile.vendor_model_id != spec['vendor_model']
            or request.profile.mode != request.input_mode or request.profile.resolution != resolution
            or request.profile.aspect_ratio != aspect_ratio or request.profile.catalog_fingerprint != sha256_canonical(spec)):
        raise ValueError('FROZEN_PROFILE_MISMATCH')
    model=str(spec['vendor_model'])
    seconds=request.duration_ms//1000
    audio=request.profile.native_audio if request.profile else request.native_audio!='DISABLED' and True in spec['native_audio']
    if request.native_audio=='REQUIRED' and not audio:
        raise CapabilityAbsent('REQUIRED_NATIVE_AUDIO_UNSUPPORTED')
    text=request.prompt_text  # PromptCompiler has already translated the package.
    if provider in ('seedance','minimax'):
        body:dict[str,JsonValue]={'model':model,'content':[{'type':'text','text':text}],
            'duration':seconds,'resolution':resolution,'ratio':aspect_ratio}
        if provider=='seedance':
            body.update(generate_audio=audio,watermark=False)
        elif audio:
            raise CapabilityAbsent('PROVIDER_REQUIRED_NATIVE_AUDIO_UNSUPPORTED')
        return body
    if provider=='vidu':
        return {'model':model,'prompt':text,'duration':seconds,'resolution':resolution,'aspect_ratio':aspect_ratio,'audio':audio}
    if provider=='wan':
        return {'model':model,'input':{'prompt':text},'parameters':{'duration':seconds,'resolution':resolution.upper(),'ratio':aspect_ratio,'audio':audio,'prompt_extend':False}}
    raise CapabilityAbsent('TARGET_PROVIDER_SERIALIZER_ABSENT')


class FinancialTerms(RuntimeContract):
    preparation_ref: ArtifactReference
    wire_payload_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    profile: ExecutionProfile
    cost_quote: CostEstimate
    budget_microunits: int = Field(gt=0)
    max_paid_operations: Literal[1] = 1

    @property
    def fingerprint(self) -> str:
        return sha256_canonical(self)

    def validate_current(self) -> None:
        from datetime import datetime, timezone
        from math import ceil
        q = self.cost_quote
        if (not q.checked_at.tzinfo or not q.expires_at.tzinfo
                or not q.checked_at <= datetime.now(timezone.utc) < q.expires_at
                or q.request_fingerprint != self.wire_payload_hash or q.amount <= 0
                or ceil(q.amount * 1000000) > self.budget_microunits):
            raise ValueError('INVALID_OR_EXPIRED_FINANCIAL_TERMS')


class ControlledLiveGrant(ExtendedRuntimeContract):
    extension_fields = ('terms',)
    owner: ClassVar[str] = 'controlled-live-grant'
    schema_version: Literal['controlled-live-grant-v1'] = 'controlled-live-grant-v1'
    scope: RuntimeScope
    operation_ref: ArtifactReference
    decision_ref: ArtifactReference
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    budget_microunits: int = Field(gt=0)
    cost_quote: CostEstimate
    resolution: str
    aspect_ratio: str
    currency: str = Field(min_length=1)
    max_paid_operations: Literal[1] = 1
    terms: FinancialTerms | None = None
    @property
    def fingerprint(self) -> str:
        return sha256_canonical(self)
    def artifact_reference(self) -> ArtifactReference:
        return ArtifactReference(owner=self.owner,artifact_ref=self.owner+':'+self.fingerprint,version=1)

class TargetHttpTransport:
    def __init__(self, adapter: HttpVideoProvider, receipt_root: Path, *, ledger: ProductionLedger,
                 grant: ControlledLiveGrant | None = None, qualification_only: bool = False,
                 resolution: str = "720p", aspect_ratio: str = "16:9", environment: Mapping[str,str] | None = None):
        self.adapter,self.provider=adapter,adapter.provider
        self.resolution,self.aspect_ratio,self.environment=resolution,aspect_ratio,environment
        self.offline=qualification_only
        self.root,self.ledger,self.grant=receipt_root.resolve(),ledger,grant
        self.root.mkdir(parents=True,exist_ok=True)
        if qualification_only and not isinstance(adapter.client._transport,httpx.MockTransport):
            raise ValueError('Offline qualification must use an in-process HTTP fake')
    def approved_payload(self, request: ProviderRequest) -> dict[str,JsonValue]:
        if request.model != self.adapter.model:
            raise ValueError('Configured model differs from approved request')
        if request.profile and (request.profile.provider != self.provider or request.profile.model != self.adapter.model
                or request.profile.resolution != self.resolution or request.profile.aspect_ratio != self.aspect_ratio):
            raise ValueError('FROZEN_PROFILE_MISMATCH')
        return wire_payload(request, provider=self.provider, resolution=self.resolution, aspect_ratio=self.aspect_ratio)

    @staticmethod
    def preview(prepared: GenerationPreparation, final: FinalPromptArtifact) -> dict[str, JsonValue]:
        profile = prepared.task.profile
        if profile is None or prepared.final_prompt_ref != final.artifact_reference() or prepared.task != final.task:
            raise ValueError('EXACT_PREPARATION_REQUIRED')
        return wire_payload(ProviderRequest(model=profile.model, input_mode=profile.mode, profile=profile,
            prompt_text=final.prompt_text, duration_ms=profile.requested_duration_ms,
            native_audio=prepared.task.native_audio), provider=profile.provider,
            resolution=profile.resolution, aspect_ratio=profile.aspect_ratio)

    def _grant(self, operation:ExecutionOperation, request:ProviderRequest|None = None) -> None:
        from drama_plugin.config.video_route import require_runtime_route
        if self.offline:
            return
        if self.environment is not None:
            from drama_plugin.config.loader import load_config
            from drama_plugin.providers.video.registry import model_enabled
            configured=load_config(environment=self.environment)
            require_runtime_route(self.provider,operation.model,policy=configured.video_route_policy)
            if not model_enabled(operation.model,self.environment):
                raise ValueError('External model policy disables this operation')
        else:
            require_runtime_route(self.provider,operation.model)
        grant=self.grant
        if grant is None or grant.operation_ref!=operation.artifact_reference() or grant.decision_ref!=operation.authorization.approval_ref or (grant.provider,grant.model)!=(self.provider,operation.model):
            raise CapabilityAbsent('EXPLICIT_CONTROLLED_LIVE_GRANT_REQUIRED')
        body,scope,_=self.ledger.get_artifact('user-decision',grant.decision_ref)
        decision=UserDecisionRecord.model_validate(body)
        if not decision.accepted or decision.category!=DecisionCategory.COST_APPROVAL or scope!=operation.scope or decision.run_id!=operation.run_id or decision.source_ref!=operation.preparation_ref:
            raise ValueError('Exact cost decision required before live submission')
        if request and request.profile:
            terms = grant.terms
            if terms is None:
                raise ValueError('EXACT_FINANCIAL_TERMS_REQUIRED')
            terms.validate_current()
            if (decision.terms_hash != terms.fingerprint or terms.preparation_ref != operation.preparation_ref
                    or terms.profile != request.profile or terms.cost_quote != grant.cost_quote
                    or terms.budget_microunits != grant.budget_microunits
                    or terms.budget_microunits != operation.authorization.budget_microunits
                    or terms.wire_payload_hash != sha256_canonical(self.approved_payload(request))):
                raise ValueError('APPROVED_FINANCIAL_TERMS_DRIFT')
        if grant.scope!=operation.scope or (grant.resolution,grant.aspect_ratio)!=(self.resolution,self.aspect_ratio):
            raise ValueError('Controlled proof scope/output profile differs from approval')
        from datetime import datetime, timezone
        from math import ceil
        quote=grant.cost_quote
        now=datetime.now(timezone.utc)
        if not quote.checked_at.tzinfo or not quote.expires_at.tzinfo or not quote.checked_at<=now<quote.expires_at or quote.currency!=grant.currency:
            raise ValueError('Current exact cost quote required')
        auth=operation.authorization
        if quote.amount<=0 or ceil(quote.amount*1000000)!=auth.estimated_cost_microunits:
            raise ValueError('Live cost estimate must match the approved quote')
        if auth.execution_mode!='CONTROLLED_LIVE' or not auth.authorized or auth.estimated_cost_microunits>min(auth.budget_microunits,grant.budget_microunits):
            raise ValueError('Controlled proof exceeds approved budget')
        if request is not None:
            if request.operation_ref!=operation.artifact_reference():
                raise ValueError('Operation request mismatch')
            if quote.request_fingerprint!=sha256_canonical(self.approved_payload(request)):
                raise ValueError('Cost quote differs from final wire request')
            if self.adapter.settings.status(self.provider)!='READY':
                raise CapabilityAbsent('PROVIDER_NOT_CONFIGURED')
    def _path(self,attempt:ProviderAttempt)->Path:
        return self.root/(attempt.client_identity+'.json')
    def receipt(self,operation:ExecutionOperation,attempt:ProviderAttempt,task:ProviderTask)->ProviderReceipt:
        if not task.provider_task_id or task.status in ('UNKNOWN','NOT_CREATED'):
            raise PossiblySubmitted('REMOTE_IDENTITY_UNRESOLVED')
        state='SUCCEEDED' if task.status=='SUCCEEDED' else 'FAILED' if task.status in ('FAILED','CANCELED') else 'RUNNING'
        if state=='SUCCEEDED' and not task.output_url:
            raise CapabilityAbsent('PROVIDER_RESULT_LOCATOR_ABSENT')
        result = ProviderResult(result_id=task.provider_task_id,locator=task.output_url) if state=='SUCCEEDED' and task.output_url else None
        return ProviderReceipt.seal(scope=operation.scope,run_id=operation.run_id,source_package_ref=operation.source_package_ref,
            operation_ref=operation.artifact_reference(),attempt_ref=attempt.artifact_reference(),provider=self.provider,
            client_identity=attempt.client_identity,request_fingerprint=attempt.request_fingerprint,remote_identity=task.provider_task_id,
            state=state,result=result,
            failure_code=task.error_code or 'PROVIDER_FAILED' if state=='FAILED' else None)
    async def submit(self,operation:ExecutionOperation,attempt:ProviderAttempt,request:ProviderRequest)->ProviderReceipt:
        self._grant(operation,request)
        if not self.offline:
            from drama_plugin.execution.store import ExecutionStore
            from drama_plugin.execution.contracts import OperationState
            assert self.grant
            checkpoint=ExecutionStore(self.ledger).checkpoint(operation.artifact_reference())
            registered=self.ledger.get_index('execution-live-grant',self.grant.decision_ref.artifact_ref)
            if checkpoint.state!=OperationState.SUBMITTING or checkpoint.attempt_ref!=attempt.artifact_reference() or registered!=self.grant.artifact_reference().model_dump(mode='json',by_alias=True):
                raise CapabilityAbsent('TARGET_EXECUTION_DISPATCH_CLAIM_REQUIRED')
        path=self._path(attempt)
        if path.exists():
            prior=ProviderReceipt.model_validate_json(path.read_bytes())
            result=await self.query(operation,attempt,prior)
            assert result
            return result
        if request.operation_ref!=operation.artifact_reference() or sha256_canonical(request)!=attempt.request_fingerprint:
            raise ValueError('Operation request mismatch')
        body=self.approved_payload(request)
        if not self.offline and self.grant and self.grant.cost_quote.request_fingerprint!=sha256_canonical(body):
            raise ValueError('Cost quote differs from final wire request')
        spec=registry()['providers'][self.provider]
        endpoint=spec['create']
        if isinstance(endpoint,dict):
            endpoint=endpoint[request.input_mode]
        if self.adapter.settings.status(self.provider)!='READY':
            raise CapabilityAbsent('PROVIDER_NOT_CONFIGURED')
        assert self.adapter.settings.api_key
        headers={'Authorization':str(spec['auth'])+' '+self.adapter.settings.api_key.get_secret_value()}
        if self.provider=='wan':
            headers['X-DashScope-Async']='enable'
        # Exactly one HTTP POST. All ambiguity is reconciled by TargetExecution.
        try:
            response=await self.adapter.client.post(self.adapter.settings.base_url+str(endpoint),json=body,headers=headers)
        except httpx.TransportError:
            raise PossiblySubmitted('TRANSPORT_UNCERTAIN') from None
        if response.status_code>=500 or response.status_code==408:
            raise PossiblySubmitted('PROVIDER_RESPONSE_UNCERTAIN')
        if response.status_code>=300:
            raise DefinitelyNotSubmitted('PROVIDER_REJECTED')
        try:
            raw=TypeAdapter(dict[str,JsonValue]).validate_python(response.json())
            task=ProviderTask(provider=self.provider,model=operation.model,client_request_id=attempt.client_identity,
                request_fingerprint=attempt.request_fingerprint,status='UNKNOWN')
            task=self.adapter.normalize(raw,task)
            receipt=self.receipt(operation,attempt,task)
        except (ValueError,TypeError,KeyError):
            raise PossiblySubmitted('PROVIDER_ACK_INVALID') from None
        # Preserve real task identity before returning ACK to execution owner.
        atomic_write(path,receipt.model_dump_json(by_alias=True).encode())
        return receipt
    async def query(self,operation:ExecutionOperation,attempt:ProviderAttempt,receipt:ProviderReceipt|None)->ProviderReceipt|None:
        if receipt is None and self._path(attempt).exists():
            receipt=ProviderReceipt.model_validate_json(self._path(attempt).read_bytes())
        if receipt is None:
            # Providers without external-id lookup cannot recover an unknown ACK.
            return None
        if receipt.operation_ref!=operation.artifact_reference() or receipt.attempt_ref!=attempt.artifact_reference() or receipt.provider!=self.provider or receipt.client_identity!=attempt.client_identity or receipt.request_fingerprint!=attempt.request_fingerprint:
            raise ValueError('Receipt crosses operation')
        task=ProviderTask(provider=self.provider,model=operation.model,provider_task_id=receipt.remote_identity,
            client_request_id=attempt.client_identity,request_fingerprint=attempt.request_fingerprint,status='RUNNING')
        task=await self.adapter.get_task(task) # Pure query primitive; no Host workflow.
        if task.status=='UNKNOWN':
            return None
        return self.receipt(operation,attempt,task)
    async def obtain(self,result:ProviderResult)->bytes:
        url=urlsplit(result.locator)
        if url.scheme!='https' or not url.hostname or url.username or url.password:
            raise ValueError('Provider result requires HTTPS')
        try:
            # Auth headers for Provider API must never be sent to result/object storage.
            response=await self.adapter.client.get(result.locator,headers={'Authorization':''},follow_redirects=False)
            response.raise_for_status()
            if len(response.content)>256*1024*1024:
                raise ValueError('Result exceeds bounded intake size')
            return response.content
        except httpx.HTTPError:
            raise IntakeTransient('RESULT_DOWNLOAD_FAILED') from None


def configured_http_transport(*, model:str, receipt_root:Path, ledger:ProductionLedger,
                              resolution:str, aspect_ratio:str, environment:Mapping[str,str]|None=None,
                              grant:ControlledLiveGrant|None=None) -> TargetHttpTransport:
    """Configuration chooses a model/provider; this factory never selects a fallback."""
    from drama_plugin.config.loader import load_config
    from drama_plugin.config.video_route import require_runtime_route
    from drama_plugin.providers.video.registry import settings, model_enabled
    from drama_plugin.providers.video.adapters import SeedanceProvider, ViduProvider, WanProvider, MiniMaxProvider
    spec=registry()['models'].get(model)
    if spec is None:
        raise CapabilityAbsent('MODEL_CAPABILITY_ABSENT')
    provider=str(spec['provider'])
    policy=load_config(environment=environment).video_route_policy
    require_runtime_route(provider,model,policy=policy)
    if not model_enabled(model,environment):
        raise CapabilityAbsent('MODEL_DISABLED')
    configuration=settings(environment)
    if provider not in configuration or configuration[provider].status(provider)!='READY':
        raise CapabilityAbsent('PROVIDER_NOT_CONFIGURED')
    adapters: dict[str,type[HttpVideoProvider]]={'seedance':SeedanceProvider,'vidu':ViduProvider,'wan':WanProvider,'minimax':MiniMaxProvider}
    if provider not in adapters:
        raise CapabilityAbsent('TARGET_SERIALIZER_ABSENT')
    async def no_reference(_:object)->str:
        raise CapabilityAbsent('TARGET_HTTP_REFERENCE_SERIALIZER_ABSENT')
    adapter=adapters[provider](model,configuration[provider],resolve=no_reference)
    return TargetHttpTransport(adapter,receipt_root,ledger=ledger,resolution=resolution,
        aspect_ratio=aspect_ratio,environment=environment,grant=grant)
