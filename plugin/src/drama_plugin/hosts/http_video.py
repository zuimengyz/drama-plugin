"""HTTP execution on the existing Work-owned route/stage and Media closure."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Literal
import hashlib
import json
import asyncio
import httpx

from drama_plugin.contracts.base import sha256_canonical, canonical_json
from drama_plugin.contracts.video import VideoRequest, ProviderTask, request_fingerprint
from drama_plugin.contracts.media import MediaType
from drama_plugin.providers.video.registry import registry, fingerprint, settings, validate_request, ProviderSettings
from drama_plugin.providers.video.adapters import ADAPTERS
from drama_plugin.providers.video.base import SafeProviderError, HttpVideoProvider
from drama_plugin.visual.video_prompt import prompt_compilation
from drama_plugin.visual.video_selection import Requirements, Candidate, Evidence, validate_requirements, verify_decision
from drama_plugin.visual.execution import validate_result_identity, validate_http_binding
from drama_plugin.hosts.route_production import operate
from drama_plugin.media_delivery import MediaIdentity, complete_retained_media, inspect_bytes


def compile_request(r: Requirements, c: Candidate) -> dict[str, Any]:
    validate_requirements(r)
    if r.video_request is None:
        raise ValueError('UNIFIED_VIDEO_REQUEST_REQUIRED')
    provider = c.capability['provider']
    v = validate_request(r.video_request, provider, c.model)
    if c.capability.get('registry_fingerprint') != fingerprint(c.model):
        raise ValueError('REGISTRY_CHANGED_REQUALIFY')
    slots = {x.media_id:f'{field}[{i}]' for field,refs in [('referenceImages',v.reference_images),('referenceVideos',v.reference_videos),('referenceAudios',v.reference_audios)] for i,x in enumerate(refs)}
    if v.first_frame: slots[v.first_frame.media_id] = 'firstFrame'
    if v.last_frame: slots[v.last_frame.media_id] = 'lastFrame'
    if any(d.status == 'FULFILLED' and slots.get(d.media_id or '') != d.provider_slot for d in r.reference_duties):
        raise ValueError('REFERENCE_PROVIDER_SLOT_MISMATCH')
    from drama_plugin.prompt_generators.registry import is_seedance2
    if is_seedance2(c.model) and r.prompt_ir is not None and r.prompt_ir != v.prompt_ir:
        raise ValueError('SEEDANCE_CONFLICTING_IR_AUTHORITIES')
    compilation = prompt_compilation(v, provider=provider, model=c.model) if is_seedance2(c.model) else prompt_compilation(v)
    if r.frozen_creative.get('creative_schema') == 'cinematic-shot-v1':
        if is_seedance2(c.model):
            from drama_plugin.prompt_generators.seedance_2.canonical import verify_cinematic
            verify_cinematic(r, compilation)
        else:
            from drama_plugin.hosts.cinematic_projection import project
            projected = project(r, c, {'class_type':'OfficialHTTP'})
            if v.prompt != projected['prompt'] or v.native_audio != projected['generate_audio']:
                raise ValueError('DIRECTOR_INTENT_MUST_EQUAL_CANONICAL_PROJECTION')
    elif v.prompt != r.frozen_creative.get('motion_prompt'):
        raise ValueError('CANONICAL_PROMPT_CHANGED')
    return {'tool':'video.create_task', 'provider':provider, 'model':c.model,
            'videoRequest':v.model_dump(mode='json', by_alias=True),
            'promptCompilation':compilation}


def seal_execution(r: Requirements, c: Candidate, request: dict[str, Any], host: dict[str, Any]) -> dict[str, Any]:
    expected = compile_request(r,c)
    if 'promptCompilation' not in request:
        # Old seals used this exact prompt composition but had no receipt field.
        # Replay the current compiler; never label the historical snapshot as run.
        expected.pop('promptCompilation')
    if request != expected:
        raise ValueError('REQUEST_DOES_NOT_MATCH_CANONICAL_PROJECTION')
    assert r.video_request is not None
    material = {'schema_fingerprint':fingerprint(c.model), 'request_fingerprint':sha256_canonical(request),
                'continuity_fingerprint':sha256_canonical(r.video_request.continuity),
                'creative_fingerprint':sha256_canonical(r.frozen_creative),
                'qualification_fingerprint':sha256_canonical(c.model_dump(mode='json'))}
    return {**material, 'fingerprint':sha256_canonical(material)}


def verify_execution(decision: dict[str, Any]) -> None:
    verify_decision(decision)
    r, c = Requirements.model_validate(decision['requirements']), Candidate.model_validate(decision['candidate'])
    if (decision['execution']['transport'] != 'HTTP' or decision['execution']['backend']['provider'] != c.capability['provider']
            or decision['execution_contract'] != seal_execution(r,c,decision['request'],{})):
        raise ValueError('HTTP_EXECUTION_CONTRACT_CHANGED')


def candidate(r: Requirements, model: str, *, cost: Any, evidence: Evidence,
              quality: Any, desired_strengths: tuple[str, ...] = ()) -> Candidate:
    """Build a candidate for the existing choose/qualify pipeline. No selection here."""
    m = registry()['models'][model]
    controls: tuple[str, ...] = ('TEXT', 'FIRST_FRAME', 'LAST_FRAME', 'REFERENCE')
    combinations: tuple[tuple[str, ...], ...] = (('TEXT',), ('FIRST_FRAME',), ('FIRST_FRAME','LAST_FRAME'), ('REFERENCE',))
    if m['endpoint_reference_mix']:
        combinations += (('FIRST_FRAME','LAST_FRAME','REFERENCE'), ('FIRST_FRAME','REFERENCE'))
    if True in m['native_audio']:
        controls += ('NATIVE_AUDIO',)
        combinations += tuple(x + ('NATIVE_AUDIO',) for x in combinations)
    layers: dict[Literal['official','interface','template','project'], Evidence] = {'official':evidence,'interface':evidence,'template':evidence,'project':evidence}
    return Candidate(candidate_id=m['provider']+':'+model, model=model, variant=m['vendor_model'], mode=r.mode,
        template='official-http-v1', graph_hash=fingerprint(model), adapter_fingerprint=fingerprint(model),
        parameters={}, capability={'provider':m['provider'], 'model_key':model, 'registry_fingerprint':fingerprint(model)},
        layers=layers, controls=controls,
        combinations=combinations, durations=tuple(m['durations']), aspect_ratios=tuple(m['aspect_ratios']),
        sounds=tuple('NATIVE' if x else 'SILENT' for x in m['native_audio']), quality=quality, cost=cost,
        fit_concerns=tuple('FIT_NOT_ESTABLISHED:'+x for x in desired_strengths if x not in m['strengths']))


class VideoProviderHost:
    def __init__(self, memory: Any, media: Any, asset: Any, cache: Path, *,
                 configuration: dict[str, ProviderSettings] | None = None,
                 http_client: httpx.AsyncClient | None = None, download_client: httpx.AsyncClient | None = None):
        self.memory, self.media, self.asset, self.cache = memory, media, asset, cache
        self.configuration = configuration if configuration is not None else settings()
        self.http_client, self.download_client = http_client, download_client

    def availability(self) -> dict[str, str]:
        return {p:s.status(p) for p,s in self.configuration.items()} | {'comfy_cloud':'MCP_DISCOVERY_REQUIRED'}

    async def _attempt(self, work_id: str, attempt_id: str) -> dict[str, Any]:
        work = await self.memory.get_work(work_id)
        from copy import deepcopy
        from drama_plugin.visual.history import attempt_frame
        state = work.content['productionStage']
        attempt = next(a for a in state['attempts'] if a['attempt_id'] == attempt_id)
        # Hydrated execution view only; never written back to Work history.
        return {**deepcopy(attempt), 'frame_snapshot': deepcopy(attempt_frame(state, attempt))}

    async def _validate_canon(self, work_id: str, r: VideoRequest) -> None:
        work = await self.memory.get_work(work_id)
        pack = work.content.get('continuityPacks', {}).get(r.continuity.segment_id)
        if pack != r.continuity.model_dump(mode='json', by_alias=True):
            raise ValueError('CANONICAL_CONTINUITY_PACK_MISSING_OR_CHANGED')

    async def _provider(self, work_id: str, item: dict[str, Any], *, check_canon: bool = True) -> HttpVideoProvider:
        r = VideoRequest.model_validate(item['videoRequest'])
        if check_canon:
            await self._validate_canon(work_id, r)
        async def resolve(ref: Any) -> str:
            record = await self.media.get_media(ref.media_id)
            if record.work_id != work_id or record.content_hash != ref.content_hash or record.media_type.value.lower() != ref.kind:
                raise ValueError('CANONICAL_REFERENCE_MEDIA_CHANGED')
            resolved = await self.media.resolve_media(ref.media_id)
            # Uses the existing Media Provider's typed resolution, not vendor assets.
            return str(resolved.url)
        cls = ADAPTERS[item['provider']]
        return cls(item['model'], self.configuration[item['provider']], resolve=resolve, client=self.http_client)

    async def bind(self, work_id: str, decision: dict[str, Any]) -> dict[str, Any]:
        verify_execution(decision)
        item = decision['request']; config = self.configuration[item['provider']]
        if config.status(item['provider']) != 'READY':
            raise ValueError('PROVIDER_NOT_CONFIGURED')
        await self._validate_canon(work_id, VideoRequest.model_validate(item['videoRequest']))
        now = datetime.now(timezone.utc)
        return {'execution':decision['execution'], 'provider_schema_fingerprint':fingerprint(item['model']),
                'operation':'video.create_task', 'endpoint_fingerprint':sha256_canonical(config.base_url),
                'evidence':Evidence(source='configured official adapter; offline schema contract', checked_at=now,
                                    expires_at=now+timedelta(hours=1), verified=True).model_dump(mode='json'),
                'authentication_status':'CONFIGURED_NOT_VERIFIED'}

    def _receipt(self, a: dict[str, Any], task: ProviderTask) -> dict[str, Any]:
        return {**a['execution_binding'], 'attempt_id':a['attempt_id'], 'task_id':task.provider_task_id,
                'request_fingerprint':a['request_fingerprint']}

    async def submit(self, work_id: str, attempt_id: str) -> ProviderTask:
        a = await self._attempt(work_id, attempt_id)
        if a['status'] != 'RESERVED' or a.get('job_id'):
            raise ValueError('RECOVER_ORIGINAL_SUBMISSION')
        verify_execution(a['frame_snapshot'])
        binding = await self.bind(work_id, a['frame_snapshot'])
        if any(binding[k] != a['execution_binding'][k] for k in ('execution','endpoint_fingerprint','provider_schema_fingerprint','operation')):
            raise ValueError('HTTP_BINDING_CHANGED')
        p = await self._provider(work_id, a['request'])
        try:
            r = VideoRequest.model_validate(a['request']['videoRequest'])
            # Resolve/read canonical inputs before durably claiming the paid call.
            await p.materialize(r)
            result = await operate(self.memory, work_id, 'begin-submission', {'attempt_id':attempt_id}, media=self.media)
            claimed = next(x for x in result['state']['attempts'] if x['attempt_id'] == attempt_id)
            if claimed['status'] != 'UNKNOWN' or claimed['request'] != a['request']:
                raise ValueError('FORMAL_SUBMISSION_CLAIM_NOT_VERIFIED')
            task = await p.create_task(r, client_request_id=attempt_id)
            # Recoverable provider receipt, not a second canonical stage. A
            # failed Work write must not lose the only acknowledged task ID.
            self.cache.mkdir(parents=True, exist_ok=True)
            journal = self.cache / (attempt_id + '.receipt.json')
            journal.write_text(json.dumps(task.durable(), ensure_ascii=False))
            await self._record(work_id, a, task)
            return task
        finally:
            await p.aclose()

    async def _record(self, work_id: str, a: dict[str, Any], task: ProviderTask) -> None:
        await operate(self.memory, work_id, 'video-task', {'attempt_id':a['attempt_id'], 'task':task.durable(),
                      'receipt':self._receipt(a, task)}, media=self.media)

    async def poll(self, work_id: str, attempt_id: str, *, retain: bool = True) -> ProviderTask:
        a = await self._attempt(work_id, attempt_id)
        if a['status'] == 'RESERVED':
            raise ValueError('TASK_NOT_SUBMITTED')
        r = VideoRequest.model_validate(a['request']['videoRequest'])
        journal = self.cache / (attempt_id + '.receipt.json')
        recovered = json.loads(journal.read_text()) if journal.is_file() else None
        task = ProviderTask.model_validate(a.get('video_task') or recovered) if a.get('video_task') or recovered else ProviderTask(
            provider=a['request']['provider'], model=a['request']['model'], client_request_id=attempt_id,
            request_fingerprint=request_fingerprint(r), provider_task_id=a.get('job_id'), status='UNKNOWN')
        if (task.client_request_id != attempt_id or task.request_fingerprint != request_fingerprint(r)
                or (task.provider,task.model) != (a['request']['provider'],a['request']['model'])):
            raise ValueError('TASK_RECEIPT_SCOPE_CHANGED')
        if task.output_media_id:
            # A retained result still resolves through the Media Service.
            await self.media.resolve_media(task.output_media_id)
            return task
        # A later creative revision cannot prevent recovering the already paid
        # original task. Its immutable frame snapshot still owns the result.
        p = await self._provider(work_id, a['request'], check_canon=False)
        try:
            task = await p.get_task(task)
            await self._record(work_id, a, task)
            if task.status == 'SUCCEEDED' and retain:
                task = await self._retain(work_id, a, p, task)
            return task
        finally:
            await p.aclose()

    async def _download(self, provider: Any, task: ProviderTask, output: Path) -> ProviderTask:
        client = self.download_client or httpx.AsyncClient(timeout=120, follow_redirects=True)
        try:
            for attempt in range(3):
                if not task.output_url or not task.output_url.startswith('https://'):
                    raise SafeProviderError('RESULT_URL_UNAVAILABLE')
                try:
                    # No vendor Authorization is ever forwarded to the media CDN.
                    async with client.stream('GET', task.output_url) as response:
                        if response.status_code in {401,403,404,410} and attempt < 2:
                            task = await provider.fetch_result(task)
                            continue
                        if response.status_code in {429,502,503,504} and attempt < 2:
                            await asyncio.sleep(.2 * 2 ** attempt)
                            continue
                        if response.status_code != 200:
                            raise SafeProviderError('RESULT_DOWNLOAD_FAILED', retryable=response.status_code in {429,502,503,504})
                        size = 0
                        with output.open('wb') as f:
                            async for chunk in response.aiter_bytes():
                                size += len(chunk)
                                if size > 512 * 1024 * 1024:
                                    raise SafeProviderError('RESULT_TOO_LARGE')
                                f.write(chunk)
                    return task
                except httpx.TransportError:
                    if attempt == 2:
                        raise SafeProviderError('RESULT_DOWNLOAD_UNCERTAIN', retryable=True) from None
            raise SafeProviderError('RESULT_URL_EXPIRED', retryable=True)
        finally:
            if self.download_client is None:
                await client.aclose()

    async def _retain(self, work_id: str, a: dict[str, Any], provider: Any, task: ProviderTask) -> ProviderTask:
        root = self.cache / a['attempt_id']; root.mkdir(parents=True, exist_ok=True)
        output = root / 'source.mp4'
        task = await self._download(provider, task, output)
        probe = inspect_bytes(output, MediaType.VIDEO)
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        if a.get('output_hash') and a['output_hash'] != digest:
            raise ValueError('PROVIDER_RESULT_BYTES_CHANGED')
        r = Requirements.model_validate(a['frame_snapshot']['requirements'])
        assert r.video_request is not None
        v = r.video_request
        stream = next(x for x in probe['streams'] if x.get('codec_type') == 'video')
        width, height = int(stream.get('width',0)), int(stream.get('height',0))
        num, den = map(int,v.aspect_ratio.split(':'))
        nominal = int(v.resolution.lower().rstrip('p')) if v.resolution.lower().endswith('p') else None
        checks = {'integrity':'PASS', 'linkage':'PASS',
            'duration':'PASS' if abs(probe.get('durationMs',0)/1000-v.duration) <= .5 else 'FAIL',
            'dimensions':'PASS' if height and abs(width/height-num/den) < .03 and (nominal is None or min(width,height) >= nominal) else 'FAIL',
            'audio':'PASS' if any(x.get('codec_type') == 'audio' for x in probe['streams']) == v.native_audio else 'FAIL',
            'fps':'PASS' if stream.get('avg_frame_rate','0/0') not in {'0/0','0'} else 'FAIL'}
        task.duration = probe.get('durationMs',0)/1000
        task.resolution = f'{width}x{height}'
        receipt = self._receipt(a, task)
        validate_result_identity(a, receipt, task.provider_task_id)
        if a['status'] != 'COMPLETED':
            await operate(self.memory, work_id, 'result', dict(attempt_id=a['attempt_id'], status='COMPLETED',
                          job_id=task.provider_task_id, output_hash=digest, evidence='official task succeeded; downloaded and probed',
                          execution_receipt=receipt), media=self.media)
        expected = MediaIdentity(work_id, MediaType.VIDEO, f"{a['stage_id']}:{a['shot_id']}:{a['attempt_id']}", digest,
                                 shot_id=r.shot_id, purpose='VIDEO_CANDIDATE')
        delivery = await complete_retained_media(self.media, self.memory, self.asset, expected, source=output,
            content={'videoGeneration':task.durable(), 'attemptId':a['attempt_id'], 'requestFingerprint':a['request_fingerprint'],
                     'continuityFingerprint':sha256_canonical(r.video_request.continuity), 'reviewStatus':'PENDING_REVIEW'},
            cache=root, target_id=a['shot_id'], duration_ms=probe.get('durationMs'))
        task.output_media_id = delivery['mediaId']
        task.output_url = None
        await operate(self.memory, work_id, 'video-delivery', {'attempt_id':a['attempt_id'], 'task':task.durable(),
                      'delivery':delivery, 'probe':probe, 'checks':checks}, media=self.media)
        return task


def cost_metrics(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Actual currency buckets only. Unknown invoices are never counted as free."""
    groups: dict[tuple[str,str,str], list[tuple[dict[str,Any],ProviderTask]]] = {}
    for a in attempts:
        if a.get('video_task'):
            t = ProviderTask.model_validate(a['video_task'])
            groups.setdefault((t.provider,t.model,t.currency or 'UNKNOWN'), []).append((a,t))
    results = []
    for (provider,model,currency), rows in groups.items():
        known = all(t.actual_cost is not None for _,t in rows)
        total = sum(t.actual_cost or 0 for _,t in rows) if known else None
        accepted = len({a['shot_id'] for a,t in rows if a.get('review_status','').startswith('PASS')})
        seconds = sum(t.duration or 0 for _,t in rows if t.status == 'SUCCEEDED')
        results.append(dict(provider=provider, model=model, currency=currency, attempts=len(rows), accepted=accepted,
            actual_cost=total, cost_per_generated_second=total/seconds if total is not None and seconds else None,
            cost_per_accepted_shot=total/accepted if total is not None and accepted else None,
            attempts_per_accepted_shot=len(rows)/accepted if accepted else None,
            rejected_reasons=[a.get('current_review', a.get('review')) for a,t in rows if a.get('review_status') == 'FAIL']))
    return results


from drama_plugin.visual import video_selection as _selection, production as _production
_selection.transport_sealers['HTTP'] = seal_execution
_production.transport_verifiers['HTTP'] = verify_execution
