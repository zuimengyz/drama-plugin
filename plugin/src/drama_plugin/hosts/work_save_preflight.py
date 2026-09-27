"""Bound the actual serialized MCP tools/call envelope before network dispatch."""
from copy import deepcopy
from typing import Any, Callable
from drama_plugin.visual.history_encoding import encode, hydrate, materialization_candidates

MAX_WORK_SAVE_REQUEST_BYTES = 8 * 1024 * 1024


def prepare(envelope: dict[str, Any], serialize: Callable[[dict[str, Any]], bytes]) -> tuple[bytes, dict[str, Any]]:
    raw = serialize(envelope)
    before = len(raw)
    report: dict[str, Any] = {'before':before, 'after':before, 'limit':MAX_WORK_SAVE_REQUEST_BYTES,
              'archivesEncoded':0, 'attemptsSummarized':0, 'headroom':0}
    if before <= MAX_WORK_SAVE_REQUEST_BYTES:
        return raw, report
    result = deepcopy(envelope)
    arguments = result['params']['arguments']
    field = 'changes' if result['params']['name'] == 'work.patch_work' else 'content'
    original = arguments[field]
    arguments[field] = hydrate(original)
    slots = materialization_candidates(arguments[field])
    # Required state stays full. Keep all optional archive contents losslessly
    # under their existing hashes, then admit the newest full snapshots until
    # the next one would cross the actual serialized envelope limit.
    snapshots = [(archive, key, archive[key]) for archive, key in slots]
    for archive, key, value in snapshots:
        encoded = encode(value)
        if len(serialize({'value':encoded})) < len(serialize({'value':value})):
            archive[key] = encoded
    raw = serialize(result)
    if len(raw) > MAX_WORK_SAVE_REQUEST_BYTES:
        raise ValueError('WORK_PATCH_REQUEST_TOO_LARGE' if field == 'changes' else
                         'WORK_SAVE_REQUEST_TOO_LARGE_NO_SAFE_HISTORY_COMPACTION')
    retained = 0
    for archive, key, value in snapshots:
        encoded = archive[key]
        archive[key] = value
        candidate = serialize(result)
        if len(candidate) > MAX_WORK_SAVE_REQUEST_BYTES:
            archive[key] = encoded
            break
        raw = candidate
        retained += 1
    raw = serialize(result)
    if hydrate(arguments[field]) != hydrate(original):
        raise ValueError('WORK_HISTORY_SEMANTICS_CHANGED')
    report.update(after=len(raw), archivesEncoded=len(snapshots)-retained,
                  optionalSnapshots=len(snapshots), fullHistoryDepthRetained=retained,
                  mode='BOUNDED_HISTORICAL_MATERIALIZATION')
    return raw, report
