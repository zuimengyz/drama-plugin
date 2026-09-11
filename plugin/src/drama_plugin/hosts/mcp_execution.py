"""Host-neutral discovery/invocation boundary for the existing sealed request.

Registry entries must be built from connected MCP server identity, tools/list and
current provider metadata. Local applications are not registry capabilities.
This module neither generates prompts nor chooses a model/backend.
"""
from collections.abc import Awaitable, Callable, Sequence
from copy import deepcopy
from typing import Any, Protocol

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.visual.execution import ExecutionRoute, validate_binding, validate_result_identity
from drama_plugin.visual.frame_request import Hash, Record, Text
from drama_plugin.visual.video_selection import Evidence, verify_decision


class MCPBinding(Record):
    execution: ExecutionRoute
    server_id: Text
    tool_name: Text
    operation: Text
    provider_schema_fingerprint: Hash
    evidence: Evidence
    authenticated: bool


class MCPRegistry(Protocol):
    async def discover(self) -> Sequence[dict[str, Any]]: ...

    async def invoke(self, binding: MCPBinding, request: dict[str, Any],
                     attempt_id: str) -> dict[str, Any]: ...


async def resolve_mcp(decision: dict[str, Any], registry: MCPRegistry, *,
                      allow_dry_run: bool = False) -> MCPBinding:
    verify_decision(decision, allow_dry_run=allow_dry_run)
    required = decision.get('execution')
    if required is None:
        raise ValueError('MCP_CAPABILITY_UNAVAILABLE: sealed execution required')
    matches = []
    for raw in await registry.discover():
        # Ignore every non-MCP surface, including a desktop advertising the model.
        if raw.get('execution') != required or raw.get('operation') != decision['request']['tool']:
            continue
        binding = MCPBinding.model_validate(raw)
        validate_binding(decision, binding.model_dump(mode='json'))
        matches.append(binding)
    if not matches:
        raise ValueError('MCP_CAPABILITY_UNAVAILABLE')
    if len(matches) != 1:
        raise ValueError('MCP_CAPABILITY_UNAVAILABLE: ambiguous connected capability')
    return matches[0]


async def invoke_reserved(attempt: dict[str, Any], registry: MCPRegistry, *,
                          verify_request: Callable[[dict[str, Any]], None],
                          claim_submission: Callable[[str], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
    """Invoke once after formal reservation; exceptions never trigger resubmission.

The registry adapter returns identity observed through the bound channel and the
owned task reply. It must not fill conflicting returned identities from the route.
An ambiguous call leaves the original reservation for task/billing recovery.
"""
    if attempt['status'] != 'RESERVED' or attempt.get('job_id') is not None:
        raise ValueError('PERSISTED_UNUSED_RESERVATION_REQUIRED')
    decision = attempt['frame_snapshot']
    verify_request(decision)
    if (attempt['frame_fingerprint'] != decision['fingerprint']
            or attempt['request'] != decision['request']
            or attempt['request_fingerprint'] != sha256_canonical(attempt['request'])):
        raise ValueError('EXECUTION_ROUTE_MISMATCH: reserved request')
    binding = await resolve_mcp(decision, registry)
    saved = attempt.get('execution_binding')
    validate_binding(decision, saved)
    assert saved is not None
    # Authentication can be refreshed without changing the sealed route/request.
    for key in ('execution', 'server_id', 'tool_name', 'operation', 'provider_schema_fingerprint'):
        if saved.get(key) != binding.model_dump(mode='json')[key]:
            raise ValueError('EXECUTION_ROUTE_MISMATCH: reserved MCP identity changed')
    # The callback uses formal route_preflight begin-submission and verified
    # readback. A reused/stale reservation cannot pass the durable claim twice.
    claimed = await claim_submission(attempt['attempt_id'])
    if (claimed.get('status') != 'UNKNOWN' or claimed.get('submission_started') is not True
            or any(claimed.get(key) != attempt.get(key) for key in
                   ('attempt_id', 'frame_fingerprint', 'request', 'request_fingerprint', 'execution_binding'))):
        raise ValueError('FORMAL_SUBMISSION_CLAIM_NOT_VERIFIED')
    result = await registry.invoke(binding, deepcopy(attempt['request']), attempt['attempt_id'])
    validate_result_identity(attempt, result, result.get('task_id'))
    return result
