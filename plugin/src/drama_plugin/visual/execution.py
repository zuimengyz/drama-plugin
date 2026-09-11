"""Execution identity for an already qualified route; never model selection."""
from typing import Any, Literal

from drama_plugin.visual.frame_request import Record, Text
from drama_plugin.contracts.base import sha256_canonical


class ExecutionBackend(Record):
    provider: Text
    backend_key: Text


class ExecutionCapability(Record):
    kind: Literal['video_generation']
    model_key: Text


class MCPRequirement(Record):
    capability_key: Text


class ExecutionRoute(Record):
    transport: Literal['MCP']
    backend: ExecutionBackend
    capability: ExecutionCapability
    mcp: MCPRequirement


def require_execution(raw: Any, model_key: str) -> ExecutionRoute:
    if raw is None:
        raise ValueError('MCP_CAPABILITY_UNAVAILABLE: execution contract required')
    try:
        route = ExecutionRoute.model_validate(raw)
    except ValueError as exc:
        raise ValueError('EXECUTION_ROUTE_MISMATCH: invalid execution contract') from exc
    if route.capability.model_key != model_key:
        raise ValueError('EXECUTION_ROUTE_MISMATCH: selected model')
    return route


def validate_binding(decision: dict[str, Any], binding: dict[str, Any] | None) -> None:
    if not binding:
        raise ValueError('MCP_CAPABILITY_UNAVAILABLE: discover before reservation')
    if (binding.get('execution') != decision.get('execution')
            or binding.get('provider_schema_fingerprint') != decision['execution_contract']['schema_fingerprint']
            or binding.get('operation') != decision['request']['tool']
            or not binding.get('server_id') or not binding.get('tool_name')):
        raise ValueError('EXECUTION_ROUTE_MISMATCH: MCP binding')
    from drama_plugin.visual.video_selection import Evidence
    from datetime import datetime, timezone
    if not Evidence.model_validate(binding['evidence']).current(datetime.now(timezone.utc)):
        raise ValueError('MCP_CAPABILITY_UNAVAILABLE: discovery expired')
    if binding.get('authenticated') is not True:
        raise ValueError('MCP_AUTHENTICATION_REQUIRED')


def validate_result_identity(attempt: dict[str, Any], receipt: dict[str, Any] | None,
                             task_id: str | None) -> None:
    """Correlation comes from the bound MCP invocation and its owned task reply."""
    binding = attempt.get('execution_binding')
    if not binding or not receipt or not task_id:
        raise ValueError('EXECUTION_ROUTE_MISMATCH: missing MCP result identity')
    if (any(receipt.get(key) != binding.get(key) for key in
            ('execution', 'server_id', 'tool_name', 'provider_schema_fingerprint', 'operation'))
            or receipt.get('task_id') != task_id
            or receipt.get('attempt_id') != attempt['attempt_id']
            or receipt.get('request_fingerprint') != sha256_canonical(attempt['request'])
            or attempt.get('job_id') not in (None, task_id)):
        raise ValueError('EXECUTION_ROUTE_MISMATCH: provider/model/channel/task')
