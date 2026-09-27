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
        # Historical route revisions can only compact in terminal stages, never
        # while any attempt still needs outcome/recovery. Selected inputs stay raw.
        if stage['attempts'] and all(a.get('status') == 'COMPLETED' or
                (a.get('status') == 'FAILED' and a.get('review_status') == 'NOT_APPLICABLE_NO_MEDIA')
                for a in stage['attempts']):
            protected_routes = set()
            for a in stage['attempts']:
                if a.get('attempt_id') in selected:
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
