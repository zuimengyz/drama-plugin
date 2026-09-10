"""Replay a shared canonical line over contiguous formal Shot coverage.

This is a planning artifact in existing context, not accepted audio timing.
Bindings stay text/timing-free. Host supplies word boundaries; code never guesses.
"""
from __future__ import annotations
from typing import Any
from drama_plugin.contracts.base import sha256_canonical


def shot_projection(shot: dict[str, Any]) -> dict[str, Any]:
    return {'id': shot['id'], 'scene_id': shot['scene_id'],
            'duration': shot['content']['plannedDurationMs'],
            'bindings': shot['content'].get('spokenContentBindings', [])}


def coverage_intervals(context: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    scene = context['scene']; all_shots = context['sceneShots']
    group = artifact['shots']
    projections = [shot_projection(s) for s in all_shots]
    indexes = [next(i for i, s in enumerate(projections) if s['id'] == g['id']) for g in group]
    if not indexes or indexes != list(range(indexes[0], indexes[0] + len(indexes))):
        raise ValueError('CONTIGUOUS_DIALOGUE_COVERAGE_REQUIRED')
    if group != [projections[i] for i in indexes] or any(s['scene_id'] != scene['id'] for s in group):
        raise ValueError('STALE_DIALOGUE_COVERAGE_SHOTS')
    spoken = {s['id']: s for s in scene['content'].get('spokenContent', [])}
    if artifact['canonicalFingerprint'] != sha256_canonical(scene['content'].get('spokenContent', [])):
        raise ValueError('STALE_CANONICAL_DIALOGUE_COVERAGE')
    if len({t['spokenContentId'] for t in artifact['turns']}) != len(artifact['turns']):
        raise ValueError('DUPLICATE_COVERAGE_TURN')
    offsets = {}; end = 0
    for shot in group:
        offsets[shot['id']] = end; end += shot['duration']
    result: dict[str, Any] = {}; previous_end = 0
    for turn in artifact['turns']:
        sid = turn['spokenContentId']; line = spoken[sid]
        start, stop = turn['startMs'], turn['endMs']
        if not all(type(v) is int for v in (start, stop)) or not previous_end <= start < stop <= end or stop-start < line['estimatedDurationMs']:
            raise ValueError('INVALID_GROUP_DIALOGUE_TIMING')
        previous_end = stop; cursor = 0; slices = turn['slices']
        expected = []
        for shot in group:
            base = offsets[shot['id']]; lo, hi = max(start, base), min(stop, base+shot['duration'])
            if hi <= lo:
                continue
            binding = next((b for b in shot['bindings'] if b['spokenContentId'] == sid), None)
            if not binding:
                raise ValueError('SPOKEN_INTERVAL_WITHOUT_FORMAL_BINDING')
            part = next((s for s in slices if s['shotId'] == shot['id']), None)
            if part is None:
                raise ValueError('MISSING_DIALOGUE_SLICE')
            a, b = part['textRange']
            if type(a) is not int or type(b) is not int or a != cursor or not a < b <= len(line['text']):
                raise ValueError('CANONICAL_TEXT_SLICE_GAP_OR_DUPLICATION')
            cursor = b; expected.append(shot['id'])
            result.setdefault(shot['id'], {})[sid] = {
                'start': (lo-base)/1000, 'end': (hi-base)/1000,
                'canonical_interval': ((lo-start)/1000, (hi-start)/1000),
                'text_range': (a,b), 'coverage_intent': binding['coverageIntent']}
        if cursor != len(line['text']) or [s['shotId'] for s in slices] != expected:
            raise ValueError('INCOMPLETE_CANONICAL_DIALOGUE_COVERAGE')
    return result
