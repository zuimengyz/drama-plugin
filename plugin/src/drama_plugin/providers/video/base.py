"""Async provider lifecycle and safe HTTP transport; no creative decisions."""
from __future__ import annotations
import asyncio
import json
import re
import math
from datetime import datetime, timezone, timedelta
from typing import Any, Awaitable, Callable, Protocol
from urllib.parse import quote
import httpx
from drama_plugin.contracts.video import CostEstimate, ProviderTask, VideoRequest, VideoReference, request_fingerprint
from .registry import ProviderSettings, registry, validate_request

ReferenceResolver = Callable[[VideoReference], Awaitable[str]]


class VideoProvider(Protocol):
    provider: str
    model: str
    transport: str
    async def create_task(self, request: VideoRequest, *, client_request_id: str) -> ProviderTask: ...
    async def get_task(self, task: ProviderTask) -> ProviderTask: ...
    async def cancel_task(self, task: ProviderTask) -> ProviderTask | None: ...
    async def fetch_result(self, task: ProviderTask) -> ProviderTask: ...
    def estimate_cost(self, request: VideoRequest) -> CostEstimate | None: ...


class SafeProviderError(Exception):
    """Never retain raw response, request, auth headers or HTTP exception context."""
    def __init__(self, code: str, *, ambiguous: bool = False, retryable: bool = False):
        super().__init__(code)
        self.code, self.ambiguous, self.retryable = code, ambiguous, retryable


def timestamp(value: Any, *, milliseconds: bool = False, china: bool = False) -> datetime | None:
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / (1000 if milliseconds else 1), timezone.utc)
        d = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return d.replace(tzinfo=timezone(timedelta(hours=8)) if china else timezone.utc) if not d.tzinfo else d
    except (ValueError, OverflowError, OSError):
        return None


# Compatibility name; compilation belongs to Creative Core.
from drama_plugin.visual.video_prompt import compile_video_prompt as prompt_text


class HttpVideoProvider:
    transport = 'http'
    provider = ''

    def __init__(self, model: str, settings: ProviderSettings, *, resolve: ReferenceResolver,
                 client: httpx.AsyncClient | None = None, cost_quote: CostEstimate | None = None):
        self.model, self.settings, self.resolve, self.cost_quote = model, settings, resolve, cost_quote
        self.spec = registry()['providers'][self.provider]
        self.model_spec = registry()['models'][model]
        if self.model_spec['provider'] != self.provider:
            raise ValueError('MODEL_PROVIDER_MISMATCH')
        self.client = client or httpx.AsyncClient(timeout=httpx.Timeout(60, connect=15), follow_redirects=False)
        self.owns_client = client is None

    async def aclose(self) -> None:
        if self.owns_client:
            await self.client.aclose()

    async def _http(self, method: str, path: str, *, body: dict[str, Any] | None = None,
                    params: dict[str, str] | None = None) -> dict[str, Any]:
        if self.settings.status(self.provider) != 'READY':
            raise SafeProviderError('PROVIDER_NOT_CONFIGURED')
        assert self.settings.api_key is not None
        headers = {'Authorization': self.spec['auth'] + ' ' + self.settings.api_key.get_secret_value()}
        if self.provider == 'wan' and method == 'POST':
            headers['X-DashScope-Async'] = 'enable'
        for attempt in range(3):
            response = None
            try:
                response = await self.client.request(method, self.settings.base_url + path, json=body, params=params, headers=headers)
            except httpx.TransportError:
                pass
            # Create network/5xx responses are ambiguous, including resets after
            # upload. Retrying reads is safe; a create is never replayed here.
            if response is None:
                if method == 'GET' and attempt < 2:
                    await asyncio.sleep(.2 * 2 ** attempt)
                    continue
                raise SafeProviderError('TRANSPORT_UNCERTAIN', ambiguous=method != 'GET', retryable=method == 'GET') from None
            status = response.status_code
            if status == 429 or method == 'GET' and status in {502, 503, 504}:
                if attempt < 2:
                    await asyncio.sleep(min(5, float(response.headers.get('Retry-After', '1'))) if response.headers.get('Retry-After', '1').isdigit() else 1)
                    continue
            if status >= 300:
                raise SafeProviderError('HTTP_' + str(status), ambiguous=method != 'GET' and (status >= 500 or status == 408),
                                        retryable=status in {429, 502, 503, 504}) from None
            try:
                value = response.json()
                if not isinstance(value, dict):
                    raise ValueError()
            except (ValueError, json.JSONDecodeError):
                raise SafeProviderError('INVALID_PROVIDER_RESPONSE', ambiguous=method != 'GET') from None
            return value
        raise SafeProviderError('RETRY_EXHAUSTED')

    async def materialize(self, request: VideoRequest) -> tuple[VideoRequest, dict[str, str]]:
        r = validate_request(request, self.provider, self.model)
        if len(prompt_text(r)) > self.model_spec['prompt_limit']:
            raise ValueError('CANONICAL_PROMPT_EXCEEDS_PROVIDER_LIMIT')
        urls = {}
        for ref in r.references():
            url = await self.resolve(ref)
            if not url.startswith('https://'):
                raise ValueError('REFERENCE_REQUIRES_RESOLVED_HTTPS_URL')
            urls[ref.media_id] = url
        return r, urls

    def payload(self, r: VideoRequest, urls: dict[str, str], client_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def normalize(self, raw: dict[str, Any], task: ProviderTask) -> ProviderTask:
        raise NotImplementedError

    def create_path(self, r: VideoRequest) -> str:
        path = self.spec['create']
        if isinstance(path, dict):
            path = path[r.input_mode]
        return str(path).format(model=self.model_spec['vendor_model'])

    async def create_task(self, request: VideoRequest, *, client_request_id: str) -> ProviderTask:
        from drama_plugin.visual.video_prompt import compile_request_ir
        compile_request_ir(request)  # Fail before URL resolution or a paid HTTP call.
        r, urls = await self.materialize(request)
        task = ProviderTask(provider=self.provider, model=self.model, client_request_id=client_request_id,
                            request_fingerprint=request_fingerprint(r), status='UNKNOWN', duration=r.duration, resolution=r.resolution)
        estimate = self.estimate_cost(r)
        if estimate:
            task.estimated_cost, task.currency = estimate.amount, estimate.currency
        try:
            raw = await self._http('POST', self.create_path(r), body=self.payload(r, urls, client_request_id))
            returned_model = (raw.get('task') or raw).get('model')
            if returned_model and returned_model not in {self.model_spec['vendor_model'], self.model_spec.get('reference_model')}:
                raise SafeProviderError('PROVIDER_MODEL_CHANGED', ambiguous=True)
            task = self.normalize(raw, task)
            if not task.provider_task_id:
                task.status = 'UNKNOWN'
                task.error_code = 'CREATE_WITHOUT_TASK_ID'
        except SafeProviderError as e:
            task.status = 'UNKNOWN' if e.ambiguous else 'NOT_CREATED'
            task.error_code, task.error_message, task.retryable = e.code, e.code, e.retryable and not e.ambiguous
        except (TypeError, ValueError, KeyError):
            task.status, task.error_code = 'UNKNOWN', 'INVALID_PROVIDER_RESPONSE'
        # Only a documented external-ID lookup can resolve an ambiguous create.
        if task.status == 'UNKNOWN' and self.spec.get('recover_external'):
            return await self.recover_task(task)
        return task

    async def recover_task(self, task: ProviderTask) -> ProviderTask:
        return task

    def check_identity(self, task: ProviderTask) -> None:
        if (task.provider, task.model) != (self.provider, self.model):
            raise ValueError('TASK_PROVIDER_MODEL_MISMATCH')

    async def get_task(self, task: ProviderTask) -> ProviderTask:
        self.check_identity(task)
        if not task.provider_task_id:
            return await self.recover_task(task)
        try:
            path = self.spec['poll'].format(id=quote(task.provider_task_id, safe=''))
            raw = await self._http('GET', path, params={'task_ids': task.provider_task_id} if self.provider == 'kling' else None)
            returned_model = (raw.get('task') or raw).get('model')
            if returned_model and returned_model not in {self.model_spec['vendor_model'], self.model_spec.get('reference_model')}:
                raise SafeProviderError('PROVIDER_MODEL_CHANGED')
            result = self.normalize(raw, task)
        except SafeProviderError as e:
            return task.model_copy(update={'error_code': e.code, 'error_message': e.code, 'retryable': e.retryable})
        except (TypeError, ValueError, KeyError):
            return task.model_copy(update={'error_code':'INVALID_PROVIDER_RESPONSE', 'retryable':False})
        if result.provider_task_id != task.provider_task_id:
            raise SafeProviderError('PROVIDER_TASK_ID_CHANGED')
        return result

    async def cancel_task(self, task: ProviderTask) -> ProviderTask | None:
        self.check_identity(task)
        # Some vendor DELETE operations also delete completed records; P1 does
        # not risk deleting a result racing with cancellation. Optional contract.
        return None

    async def fetch_result(self, task: ProviderTask) -> ProviderTask:
        return await self.get_task(task)

    def estimate_cost(self, request: VideoRequest) -> CostEstimate | None:
        q = self.cost_quote
        now = datetime.now(timezone.utc)
        if q and q.checked_at.tzinfo and q.expires_at.tzinfo and q.checked_at <= now < q.expires_at and q.request_fingerprint == request_fingerprint(request):
            return q
        return None

    def result(self, task: ProviderTask, *, task_id: Any, state: str | None, url: str | None = None,
               created: Any = None, started: Any = None, completed: Any = None, duration: Any = None,
               resolution: Any = None, fps: Any = None, usage: dict[str, Any] | None = None,
               error: Any = None, milliseconds: bool = False, china: bool = False,
               actual_cost: float | None = None, currency: str | None = None) -> ProviderTask:
        states = {'created':'QUEUED','submitted':'QUEUED','queued':'QUEUED','queueing':'QUEUED','pending':'QUEUED',
                  'running':'RUNNING','processing':'RUNNING','succeeded':'SUCCEEDED','success':'SUCCEEDED',
                  'failed':'FAILED','cancelled':'CANCELED','canceled':'CANCELED'}
        status = states.get(str(state).lower(), 'UNKNOWN') if state else ('QUEUED' if task_id else 'UNKNOWN')
        # Raw vendor messages can echo prompts, signed URLs and even credentials.
        # Keep a fixed safe diagnostic and numeric usage only.
        updates = dict(provider_task_id=str(task_id) if task_id else task.provider_task_id,
            status=status, output_url=url, created_at=timestamp(created, milliseconds=milliseconds, china=china) or task.created_at,
            started_at=timestamp(started, milliseconds=milliseconds, china=china) or task.started_at,
            completed_at=timestamp(completed, milliseconds=milliseconds, china=china) if status in {'SUCCEEDED','FAILED','CANCELED'} else None,
            duration=float(duration) if duration is not None else task.duration,
            resolution=str(resolution) if resolution is not None else task.resolution, fps=float(fps) if fps else task.fps,
            usage={k: v for k, v in (usage or {}).items() if re.fullmatch('[a-zA-Z_]+', k) and isinstance(v, (int,float)) and math.isfinite(v)},
            actual_cost=actual_cost if actual_cost is not None else task.actual_cost, currency=currency or task.currency,
            error_code='PROVIDER_TASK_FAILED' if error or status == 'FAILED' else None,
            error_message='Provider rejected or failed the task; inspect the official console.' if error or status == 'FAILED' else None,
            retryable=False)
        return ProviderTask.model_validate(task.model_dump() | updates)
