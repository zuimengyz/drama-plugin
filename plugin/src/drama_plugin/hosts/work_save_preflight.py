"""Bound the actual serialized MCP tools/call envelope before network dispatch."""
from copy import deepcopy
from typing import Any, Callable
from drama_plugin.visual.history_encoding import candidates, encode, hydrate

MAX_WORK_SAVE_REQUEST_BYTES = 8 * 1024 * 1024


def prepare(envelope: dict[str, Any], serialize: Callable[[dict[str, Any]], bytes]) -> tuple[bytes, dict[str, Any]]:
    raw = serialize(envelope)
    before = len(raw)
    report = {'before':before, 'after':before, 'limit':MAX_WORK_SAVE_REQUEST_BYTES,
              'archivesEncoded':0, 'attemptsSummarized':0}
    if before <= MAX_WORK_SAVE_REQUEST_BYTES:
        return raw, report
    result = deepcopy(envelope)
    arguments = result['params']['arguments']
    original = arguments['content']
    arguments['content'] = {}
    # Two real envelope overheads plus maximum integer-ID growth: measured on
    # this exact caller/title/description, not a guessed Work-content allowance.
    headroom = 2 * len(serialize(result)) + 20
    arguments['content'] = hydrate(original)
    report['headroom'] = headroom
    for archive, key in candidates(arguments['content']):
        value = archive[key]
        if value.get('encoding') == 'history-json-zlib-v1':
            continue
        encoded = encode(value)
        if len(serialize({'value':encoded})) >= len(serialize({'value':value})):
            continue
        archive[key] = encoded
        raw = serialize(result)
        report['archivesEncoded'] += 1
        report['after'] = len(raw)
        if len(raw) <= MAX_WORK_SAVE_REQUEST_BYTES - headroom:
            # Byte-for-byte semantics are restored, including every hash/seal.
            if hydrate(arguments['content']) != hydrate(original):
                raise ValueError('WORK_HISTORY_SEMANTICS_CHANGED')
            return raw, report
    raise ValueError('WORK_SAVE_REQUEST_TOO_LARGE_NO_SAFE_HISTORY_COMPACTION')
