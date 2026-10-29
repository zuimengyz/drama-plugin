"""Host selections at the existing text-author boundary; no model or author loop."""
from __future__ import annotations
from typing import Any
from copy import deepcopy
from pydantic import JsonValue, TypeAdapter
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.execution.transport import CapabilityAbsent


def without_host_originals(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: without_host_originals(v) for k, v in value.items() if k != 'hostAuthoring'}
    if isinstance(value, list):
        return [without_host_originals(v) for v in value]
    return value


def request_packet(task: str, request: Any, payload: Any, schema: dict[str, JsonValue], instructions: str = "") -> dict[str, Any]:
    source = without_host_originals(payload)
    scope = request.scope.model_dump(mode='json', by_alias=True)
    return {'task': task, 'scope': scope, 'input': source, 'outputSchema': schema, 'instructions': instructions,
        'inputFingerprint': sha256_canonical([task, scope, source, schema, instructions]),
        'actualAuthor': 'HOST', 'formalAdoption': False}


class HostOriginalRequired(CapabilityAbsent):
    """The caller can present this exact request to Host, then bind its answer."""
    code = 'HOST_AUTHOR_ORIGINAL_REQUIRED'
    def __init__(self, packet: dict[str, Any]):
        self.request_packet = deepcopy(packet)
        super().__init__(f"{self.code}:{packet['task']}:{packet['inputFingerprint']}")


def selected_content(request: Any, packet: dict[str, Any], reader: Any = None) -> JsonValue:
    contexts = [getattr(request, k, None) or {} for k in ('screenplay_context', 'professional_context')]
    candidates = [c.get('authorContext', c.get('context', {}).get('authorContext', {})) for c in contexts]
    key = packet['task'] + ':' + packet['inputFingerprint']
    records = [c.get('hostAuthoring', {}).get(key) for c in candidates]
    records = [r for r in records if r is not None]
    if not records and reader is not None:
        selected = reader(packet)
        if selected is not None:
            records = [selected]
    if not records:
        raise HostOriginalRequired(packet)
    if any(r != records[0] for r in records):
        raise ValueError('HOST_AUTHOR_SELECTION_CONFLICT')
    record = records[0]
    original = record['original']
    if (sha256_canonical(original) != record['ref']['fingerprint']
            or original.get('selectedBy') != 'HOST' or original['actualAuthor'] != 'HOST' or original['formalAdoption'] is not False
            or original['inputFingerprint'] != packet['inputFingerprint'] or original['task'] != packet['task']
            or original['workId'] != request.scope.work_id):
        raise ValueError('HOST_AUTHOR_ORIGINAL_MISMATCH')
    return TypeAdapter(JsonValue).validate_python(original['content'])
