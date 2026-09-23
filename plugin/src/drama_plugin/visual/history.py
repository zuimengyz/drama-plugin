"""Content-addressed history inside the existing stage, without duplicating current frames."""
from copy import deepcopy
from typing import Any
from drama_plugin.contracts.base import sha256_canonical as digest


def resolve(state: dict[str, Any], ref: str, kind: str = 'frame') -> dict[str, Any]:
    current = state.get('frames', {}).values() if kind == 'frame' else [state.get('production_route')]
    for value in current:
        if value is not None and digest(value) == ref:
            return value
    value = state.get('history_' + kind + 's', {}).get(ref)
    if value is None or digest(value) != ref:
        raise ValueError('PRODUCTION_HISTORY_REFERENCE_MISSING_OR_CHANGED:' + ref)
    return value


def attempt_frame(state: dict[str, Any] | None, attempt: dict[str, Any]) -> dict[str, Any]:
    if attempt.get('frame_ref'):
        frame = (attempt['frame_snapshot'] if state is None and attempt.get('frame_snapshot') is not None
                 else resolve(state or {}, attempt['frame_ref']))
        if digest(frame) != attempt['frame_ref']:
            raise ValueError('PRODUCTION_HISTORY_FRAME_HASH_CHANGED')
        if attempt.get('frame_snapshot') is not None and frame != attempt['frame_snapshot']:
            raise ValueError('PRODUCTION_HISTORY_INLINE_REFERENCE_CONFLICT')
    else:
        frame = attempt.get('frame_snapshot')
        if frame is None:
            raise ValueError('PRODUCTION_HISTORY_FRAME_REQUIRED')
    if attempt.get('frame_fingerprint') not in (None, frame.get('fingerprint')):
        raise ValueError('PRODUCTION_HISTORY_FRAME_FINGERPRINT_CHANGED')
    return frame


def remember(state: dict[str, Any], value: dict[str, Any], kind: str = 'frame') -> str:
    ref = digest(value)
    # Callers retain a departing canonical revision before changing it. Compact
    # removes this temporary duplicate if it is still current at the save boundary.
    archive = state.setdefault('history_' + kind + 's', {})
    if ref not in archive:
        archive[ref] = deepcopy(value)
    elif archive[ref] != value:
        raise ValueError('PRODUCTION_HISTORY_ARCHIVE_CHANGED')
    return ref


def compact(state: dict[str, Any]) -> None:
    """Migrate legacy history on the next write. Keep every distinct old revision.

    Build on a copy so a missing/corrupt reference never partially rewrites state.
    Current frames, their fingerprints and the plan fingerprint stay unchanged.
    """
    result = deepcopy(state)
    for kind, entries, inline, reference in (
        ('frame', result.get('attempts', []), 'frame_snapshot', 'frame_ref'),
        ('frame', result.get('remediations', []), 'previous_frame', 'previous_frame_ref'),
        ('route', result.get('route_revisions', []), 'previous_route', 'previous_route_ref'),
    ):
        for entry in entries:
            value = entry.get(inline)
            if value is not None:
                ref = digest(value)
                if entry.get(reference) not in (None, ref):
                    raise ValueError('PRODUCTION_HISTORY_INLINE_REFERENCE_CONFLICT')
                remember(result, value, kind)
                entry[reference] = ref
            entry.pop(inline, None)
    # Check all references before pruning canonical duplicates; never discard
    # old evidence just because no retained event happens to point at it today.
    for entry in result.get('attempts', []):
        if entry.get('frame_ref') or entry.get('frame_snapshot'):
            attempt_frame(result, entry)
    for entries, key, kind in ((result.get('remediations', []), 'previous_frame_ref', 'frame'),
                               (result.get('route_revisions', []), 'previous_route_ref', 'route')):
        for entry in entries:
            if entry.get(key):
                resolve(result, entry[key], kind)
    for kind in ('frame', 'route'):
        current = result.get('frames', {}).values() if kind == 'frame' else [result.get('production_route')]
        hashes = {digest(v) for v in current if v is not None}
        archive = result.get('history_' + kind + 's', {})
        for key, value in archive.items():
            if digest(value) != key:
                raise ValueError('PRODUCTION_HISTORY_ARCHIVE_CHANGED')
        archive = {key: value for key, value in archive.items() if key not in hashes}
        if archive:
            result['history_' + kind + 's'] = archive
        else:
            result.pop('history_' + kind + 's', None)
    state.clear(); state.update(result)
