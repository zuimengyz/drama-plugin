"""Lossless encoding of existing historical archive values, not a new ledger.

All counters, attempts and current execution values remain ordinary JSON. Decode
before domain consumption so original source/revision seals retain their meaning.
"""
from copy import deepcopy
import base64
import json
import zlib
from typing import Any, Iterator
from drama_plugin.contracts.base import canonical_json, sha256_canonical

ENCODING = 'history-json-zlib-v1'
MAX_DECODED_BYTES = 32 * 1024 * 1024


def decode(value: dict[str, Any]) -> dict[str, Any]:
    if value.get('encoding') != ENCODING:
        return value
    size = value.get('decoded_bytes')
    if type(size) is not int or not 0 < size <= MAX_DECODED_BYTES:
        raise ValueError('INVALID_HISTORY_ENCODING_SIZE')
    try:
        packed = base64.b64decode(value['data'], validate=True)
        decoder = zlib.decompressobj()
        raw = decoder.decompress(packed, size + 1)
        if len(raw) != size or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError('INVALID_HISTORY_ENCODING')
        result = json.loads(raw)
        if not isinstance(result, dict) or sha256_canonical(result) != value['sha256']:
            raise ValueError('HISTORY_ENCODING_HASH_CHANGED')
        return result
    except (KeyError, TypeError, zlib.error) as exc:
        raise ValueError('INVALID_HISTORY_ENCODING') from exc


def encode(value: dict[str, Any]) -> dict[str, Any]:
    raw = canonical_json(value).encode('utf-8')
    if len(raw) > MAX_DECODED_BYTES:
        raise ValueError('HISTORY_ENCODING_TOO_LARGE')
    return {'encoding': ENCODING, 'sha256': sha256_canonical(value),
            'decoded_bytes': len(raw), 'data': base64.b64encode(zlib.compress(raw, 9)).decode('ascii')}


def stages(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        if isinstance(value.get('attempts'), list) and isinstance(value.get('frames'), dict) and 'plan_fingerprint' in value:
            yield value
            return
        for child in value.values():
            yield from stages(child)
    elif isinstance(value, list):
        for child in value:
            yield from stages(child)


def hydrate(content: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(content)
    for stage in stages(result):
        for kind in ('frame', 'route'):
            for key, value in stage.get('history_' + kind + 's', {}).items():
                decoded = decode(value)
                if decoded is not value:
                    if sha256_canonical(decoded) != key:
                        raise ValueError('PRODUCTION_HISTORY_ARCHIVE_CHANGED')
                    stage['history_' + kind + 's'][key] = decoded
    return result


def candidates(content: dict[str, Any]) -> Iterator[tuple[dict[str, Any], str]]:
    """Oldest completed nonselected history first; never encode current frames."""
    ordered = sorted(stages(content), key=lambda s: min(
        (str(a.get('quote', {}).get('evidence', {}).get('checked_at', '')) for a in s['attempts']), default=''))
    for stage in ordered:
        selected = {v.get('attempt_id') for v in stage.get('input_selections', {}).values()}
        # A retained selection event is historical after an explicit failed
        # reassessment; keep the event/attempt, but its old frame is not live input.
        selected -= {a.get('attempt_id') for a in stage['attempts'] if a.get('review_status') == 'FAIL'}
        protected = {a.get('frame_ref') for a in stage['attempts']
                     if a.get('status') != 'COMPLETED' or a.get('attempt_id') in selected}
        protected.add(stage['attempts'][-1].get('frame_ref') if stage['attempts'] else None)
        archive = stage.get('history_frames', {})
        seen = set()
        for attempt in stage['attempts']:
            ref = attempt.get('frame_ref')
            if ref in archive and ref not in protected and ref not in seen and attempt.get('status') == 'COMPLETED':
                seen.add(ref)
                yield archive, ref
        # A known current route stays raw even while a new reservation is being
        # saved. Older immutable revisions may encode losslessly; no attempt,
        # active request or current route is replaced by an archive marker.
        terminal = bool(stage['attempts']) and all(a.get('status') == 'COMPLETED' or
                (a.get('status') == 'FAILED' and a.get('review_status') == 'NOT_APPLICABLE_NO_MEDIA')
                or (a.get('status') == 'NOT_CREATED' and not a.get('job_id')
                    and a.get('video_task', {}).get('status') == 'NOT_CREATED')
                for a in stage['attempts'])
        current_route = stage.get('production_route')
        if terminal or isinstance(current_route, dict) and current_route.get('route_id'):
            protected_routes = {sha256_canonical(current_route)} if current_route else set()
            for a in stage['attempts']:
                if a.get('attempt_id') in selected or a.get('status') in {'RESERVED','UNKNOWN'}:
                    frame = archive.get(a.get('frame_ref'))
                    if frame is None:
                        frame = next((f for f in stage['frames'].values() if sha256_canonical(f) == a.get('frame_ref')), None)
                    if frame and frame.get('production_route'):
                        protected_routes.add(sha256_canonical(frame['production_route']))
            routes = stage.get('history_routes', {})
            for revision in stage.get('route_revisions', []):
                ref = revision.get('previous_route_ref')
                if ref in routes and ref not in protected_routes:
                    yield routes, ref


def materialization_candidates(content: dict[str, Any]) -> list[tuple[dict[str, Any], str]]:
    """Newest superseded archives first; live/recovery snapshots stay materialized.

    Existing archive hashes and journals supply identity/order. Only these two
    content-addressed archive maps participate; attempts and arbitrary evidence
    fields never do. Encoding retains the full bytes behind each existing ref.
    """
    result = []
    eligible = {(id(archive), key) for archive, key in candidates(content)}
    ordered = sorted(stages(content), key=lambda s: max(
        (str(a.get('quote', {}).get('evidence', {}).get('checked_at', ''))
         for a in s['attempts']), default=''), reverse=True)
    for stage in ordered:
        protected_frames = {sha256_canonical(f) for f in stage['frames'].values()}
        protected_frames.update(a.get('frame_ref') for a in stage['attempts'])
        # A departing pre-dispatch repair frame is no longer an attempt's live
        # frame. Its existing revision journal proves that it is superseded.
        for event in stage.get('route_revisions', []) + stage.get('remediations', []):
            key = event.get('previous_frame_ref')
            archive = stage.get('history_frames', {})
            if key in archive and key not in protected_frames:
                eligible.add((id(archive), key))
        # Map insertion order is the retained creation order; journal references
        # explicitly identify later replacements, without inventing timestamps.
        order = [('frame', k) for k in stage.get('history_frames', {})]
        order += [('route', k) for k in stage.get('history_routes', {})]
        events = stage.get('remediations', []) + stage.get('route_revisions', [])
        for event in sorted(events, key=lambda e: e.get('after_attempt', -1)):
            for kind in ('frame', 'route'):
                key = event.get('previous_' + kind + '_ref')
                if key:
                    pair = (kind, key)
                    if pair in order:
                        order.remove(pair)
                    order.append(pair)
        for kind, key in reversed(order):
            archive = stage.get('history_' + kind + 's', {})
            if key in archive and (id(archive), key) in eligible:
                if sha256_canonical(decode(archive[key])) != key:
                    raise ValueError('PRODUCTION_HISTORY_ARCHIVE_CHANGED')
                result.append((archive, key))
    return result
