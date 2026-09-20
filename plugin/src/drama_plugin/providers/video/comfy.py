"""Lifecycle facade over the existing bound MCP invocation, without replacing it."""
from typing import Any, Awaitable, Callable
from drama_plugin.contracts.video import VideoRequest, ProviderTask, CostEstimate, request_fingerprint
from drama_plugin.hosts.mcp_execution import MCPRegistry, invoke_reserved
from drama_plugin.hosts.comfy_video import verify_execution
from drama_plugin.providers.video.registry import continuity_errors


class ComfyCloudProvider:
    provider = 'comfy_cloud'
    transport = 'mcp'

    def __init__(self, *, attempt: dict[str, Any], registry: MCPRegistry,
                 claim_submission: Callable[[str], Awaitable[dict[str, Any]]],
                 read_task: Callable[[ProviderTask], Awaitable[ProviderTask]],
                 cancel: Callable[[ProviderTask], Awaitable[ProviderTask]] | None = None):
        self.attempt, self.registry, self.claim, self.read_task, self.cancel = attempt, registry, claim_submission, read_task, cancel
        self.model = attempt['frame_snapshot']['execution']['capability']['model_key']

    async def create_task(self, request: VideoRequest, *, client_request_id: str) -> ProviderTask:
        frame = self.attempt['frame_snapshot']
        r = frame['requirements']
        errors = continuity_errors(request, self.provider, self.model)
        if (errors or request.prompt != r['frozen_creative']['motion_prompt'] or request.duration != r['duration_seconds']
                or request.aspect_ratio != r['aspect_ratio'] or request.native_audio != (r['sound'] != 'SILENT')
                or {x.media_id:x.content_hash for x in request.references()} != {x['media_id']:x['content_hash'] for x in r['inputs']}
                or client_request_id != self.attempt['attempt_id']):
            raise ValueError('COMFY_CANONICAL_CONTRACT_MISMATCH')
        # Exact image counts, input roles, graph and provider schema remain owned
        # and checked by the existing Comfy compiler/verifier and MCP registry.
        receipt = await invoke_reserved(self.attempt, self.registry, verify_request=verify_execution, claim_submission=self.claim)
        return ProviderTask(provider=self.provider, model=self.model, client_request_id=client_request_id,
                            request_fingerprint=request_fingerprint(request), provider_task_id=receipt['task_id'],
                            status='QUEUED', duration=request.duration, resolution=request.resolution)

    async def get_task(self, task: ProviderTask) -> ProviderTask:
        if (task.provider,task.model) != (self.provider,self.model) or not task.provider_task_id:
            raise ValueError('COMFY_TASK_IDENTITY_MISMATCH')
        result = await self.read_task(task)
        if any(getattr(task,k) != getattr(result,k) for k in ('provider','model','provider_task_id','client_request_id','request_fingerprint')):
            raise ValueError('COMFY_TASK_IDENTITY_CHANGED')
        return result

    async def cancel_task(self, task: ProviderTask) -> ProviderTask | None:
        if (task.provider,task.model) != (self.provider,self.model):
            raise ValueError('COMFY_TASK_IDENTITY_MISMATCH')
        return await self.cancel(task) if self.cancel else None

    async def fetch_result(self, task: ProviderTask) -> ProviderTask:
        return await self.get_task(task)

    def estimate_cost(self, request: VideoRequest) -> CostEstimate | None:
        return None  # Existing graph quote/reservation remains authoritative.
