"""Execution identity for an already qualified route; never model selection."""
from typing import Any, Literal

from drama_plugin.visual.frame_request import Record, Text
from drama_plugin.contracts.base import sha256_canonical
from pydantic import model_validator


class ExecutionBackend(Record):
    provider: Text
    backend_key: Text


class ExecutionCapability(Record):
    kind: Literal['video_generation', 'image_generation']
    model_key: Text


class MCPRequirement(Record):
    capability_key: Text


class ExecutionRoute(Record):
    transport: Literal['MCP', 'HTTP']
    backend: ExecutionBackend
    capability: ExecutionCapability
    mcp: MCPRequirement | None = None

    @model_validator(mode='after')
    def transport_binding(self) -> 'ExecutionRoute':
        if (self.transport == 'MCP') != (self.mcp is not None):
            raise ValueError('TRANSPORT_BINDING_MISMATCH')
        return self


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
    if decision.get('schema') == 'visual-frame-preflight-v1':
        validate_still_binding(decision, binding)
        return
    if decision.get('execution', {}).get('transport') == 'HTTP':
        validate_http_binding(decision, binding)
        return
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


def still_execution(decision: dict[str, Any]) -> dict[str, Any]:
    """Derive still execution identity without changing the compiled artifact."""
    from drama_plugin.visual.frame_request import verify_compiled
    verify_compiled(decision)
    if decision['request']['tool'] not in {'submit_workflow', 'image.create'}:
        raise ValueError('STILL_MCP_OPERATION_UNSUPPORTED')
    from drama_plugin.visual.image_route import execution_identity
    return ExecutionRoute.model_validate(execution_identity(decision)).model_dump(mode='json')


def validate_still_binding(decision: dict[str, Any], binding: dict[str, Any] | None) -> None:
    if decision.get('template', {}).get('http_provider') == 'ark':
        from drama_plugin.providers.ark_image import validate_binding as validate_ark
        validate_ark(decision, binding)
        return
    from drama_plugin.visual.video_selection import Evidence
    from datetime import datetime, timezone
    required = still_execution(decision)
    if not binding:
        raise ValueError('MCP_CAPABILITY_UNAVAILABLE: still discovery required')
    schema = binding.get('provider_schema')
    if (binding.get('execution') != required or not isinstance(schema, dict)
            or binding.get('provider_schema_fingerprint') != sha256_canonical(schema)
            or binding.get('request_fingerprint') != sha256_canonical(decision['request'])
            or binding.get('operation') != decision['request']['tool']
            or not binding.get('server_id') or not binding.get('tool_name')):
        raise ValueError('STILL_EXECUTION_BINDING_MISMATCH')
    nodes = {n['name']: n for n in schema.get('nodes', [])}
    for node in decision['request']['workflow'].values():
        meta = nodes.get(node['class_type'])
        if not meta or meta.get('deprecated'):
            raise ValueError('STILL_PROVIDER_NODE_UNAVAILABLE')
        fields = {f['name']: f for f in meta.get('input_details', [])}
        for key, value in node['inputs'].items():
            field = fields.get(key) or next((f for f in fields.values() if key in f.get('auto_grow_slots', [])), None)
            if field is None or (field.get('options') and value not in field['options']):
                raise ValueError('STILL_PROVIDER_INPUT_UNSUPPORTED')
    if not Evidence.model_validate(binding['evidence']).current(datetime.now(timezone.utc)):
        raise ValueError('MCP_CAPABILITY_UNAVAILABLE: discovery expired')
    if binding.get('authenticated') is not True:
        raise ValueError('MCP_AUTHENTICATION_REQUIRED')


def validate_http_binding(decision: dict[str, Any], binding: dict[str, Any] | None) -> None:
    # Old HTTP bindings used "authenticated" for credential presence. Translate
    # only that legacy meaning; no offline binding proves provider authentication.
    auth = (binding.get('authentication_status') if binding and 'authentication_status' in binding
            else 'CONFIGURED_NOT_VERIFIED' if binding and binding.get('authenticated') is True else None)
    if (not binding or binding.get('execution') != decision.get('execution')
            or binding.get('provider_schema_fingerprint') != decision['execution_contract']['schema_fingerprint']
            or binding.get('operation') != 'video.create_task' or not binding.get('endpoint_fingerprint')
            or auth != 'CONFIGURED_NOT_VERIFIED'):
        raise ValueError('HTTP_PROVIDER_BINDING_REQUIRED')
    from drama_plugin.visual.video_selection import Evidence
    # This is Host-owned static adapter/config evidence, not a provider-issued
    # token, URL, balance or live quote. The formal Host replays current schema,
    # endpoint, provider/model and sealed request identity before dispatch.
    # Preserve the original attestation timestamps; only content drift invalidates it.
    if not Evidence.model_validate(binding['evidence']).content_verified():
        raise ValueError('HTTP_BINDING_UNVERIFIED')


def validate_result_identity(attempt: dict[str, Any], receipt: dict[str, Any] | None,
                             task_id: str | None) -> None:
    """Correlation comes from the bound MCP invocation and its owned task reply."""
    binding = attempt.get('execution_binding')
    if not binding or not receipt or not task_id:
        raise ValueError('EXECUTION_ROUTE_MISMATCH: missing MCP result identity')
    keys = ('execution', 'endpoint_fingerprint', 'provider_schema_fingerprint', 'operation') if binding.get('execution', {}).get('transport') == 'HTTP' else ('execution', 'server_id', 'tool_name', 'provider_schema_fingerprint', 'operation')
    if (any(receipt.get(key) != binding.get(key) for key in keys)
            or receipt.get('task_id') != task_id
            or receipt.get('attempt_id') != attempt['attempt_id']
            or receipt.get('request_fingerprint') != sha256_canonical(attempt['request'])
            or attempt.get('job_id') not in (None, task_id)):
        raise ValueError('EXECUTION_ROUTE_MISMATCH: provider/model/channel/task')
