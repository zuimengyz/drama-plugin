"""Explicit Host reconciliation of independently reviewed temporal observations.

This adapter checks provenance and aligns evidence; it does not infer facts, run a
model, authenticate reviewers, or authorize canonical Media. Caller isolation and
independent factual verification are Host responsibilities, not string checks.
"""
from __future__ import annotations

from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Any

from drama_plugin.contracts.base import sha256_canonical

DOMAINS = {'visible_subjects', 'actions', 'action_order', 'spatial_relations',
           'prop_relations', 'body_state', 'gaze', 'environmental_events'}
MANIFEST_KEYS = {'mediaId', 'mediaPath', 'sourceHash', 'duration', 'timebase',
                 'windows', 'inputFields', 'neutralInstruction'}


def file_hash(path: str) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def _range(start: Any, end: Any, duration: float) -> None:
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool)
               and isfinite(x) for x in (start, end)):
        raise ValueError('Nonfinite time')
    if not 0 <= start <= end <= duration:
        raise ValueError('Time outside source')


def reconcile(manifest: dict[str, Any], visual: dict[str, Any],
              audio: dict[str, Any] | None, verification: dict[str, Any],
              *, manifest_file_hash: str) -> dict[str, Any]:
    """Fail closed; accepted facts must be independently confirmed by exact hash.

    A full-audio receipt must contain reviewed semantic events, never merely VAD
    or ASR. Synthetic test receipts exercise validation, not observer capability.
    """
    if set(manifest) != MANIFEST_KEYS or manifest['inputFields'] != [
            'media', 'orderedSamples', 'neutralObservationSchema']:
        raise ValueError('Blind input allowlist violated')
    if (verification.get('inputContextAudited') is not True
            or verification.get('observerIsIndependent') is not True):
        raise ValueError('Independent blind context audit required')
    if verification.get('providedUpstreamAnswers') != []:
        raise ValueError('Prompt contamination')
    if visual.get('inputManifestHash') != manifest_file_hash:
        raise ValueError('Blind manifest fingerprint mismatch')
    source_hash = file_hash(manifest['mediaPath'])
    if any(v != source_hash for v in (manifest['sourceHash'],
           visual['sourceHash'], verification['sourceHash'])):
        raise ValueError('Source hash mismatch')
    if verification.get('visualFingerprint') != sha256_canonical(visual):
        raise ValueError('Stale factual review')
    duration = float(manifest['duration'])
    _range(0, duration, duration)
    samples: dict[str, Any] = {}
    last = -1.0
    orders = [w['order'] for w in manifest['windows']]
    if orders != sorted(set(orders)):
        raise ValueError('Unordered windows')
    for window in manifest['windows']:
        for sample in window['samples']:
            t = sample['timestamp']
            _range(t, t, duration)
            if t <= last or sample['id'] in samples:
                raise ValueError('Unordered or duplicate frames')
            if last >= 0 and t - last > .5:
                raise ValueError('Temporal sampling gap requires review')
            if file_hash(sample['file']) != sample['sha256']:
                raise ValueError('Visual evidence hash mismatch')
            samples[sample['id']] = sample
            last = t
    if not samples or next(iter(samples.values()))['timestamp'] > .5 or duration-last > .5:
        raise ValueError('Visual timeline incomplete')
    cursor = 0.0
    facts: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []
    ids: set[str] = set()
    verified = set(verification.get('confirmedVisualIds', []))
    for window in visual['windows']:
        _range(window['start'], window['end'], duration)
        if abs(window['start'] - cursor) > .00001:
            raise ValueError('Observation windows incomplete or unordered')
        cursor = window['end']
        for fact in window['facts']:
            _range(fact['start'], fact['end'], duration)
            if not window['start'] <= fact['start'] <= fact['end'] <= window['end']:
                raise ValueError('Fact outside observation window')
            if fact['id'] in ids or fact['domain'] not in DOMAINS:
                raise ValueError('Duplicate fact or invalid domain')
            ids.add(fact['id'])
            confidence = fact['confidence']
            if not isinstance(confidence, (float, int)) or not isfinite(confidence) or not 0 <= confidence <= 1:
                raise ValueError('Invalid observation confidence')
            refs = fact.get('visualEvidenceRefs', [])
            if not refs or any(r not in samples for r in refs):
                raise ValueError('Missing visual evidence')
            if any(not fact['start'] <= samples[r]['timestamp'] <= fact['end'] for r in refs):
                raise ValueError('Evidence outside fact time')
            ref_times = [samples[r]['timestamp'] for r in refs]
            if ref_times != sorted(set(ref_times)):
                raise ValueError('Fact evidence must retain sample order')
            if fact['domain'] in ('actions', 'action_order') and len(set(refs)) < 2:
                raise ValueError('Temporal action needs ordered evidence')
            if fact['id'] not in verified or confidence < .5:
                unknown.append({**fact, 'status': 'UNKNOWN',
                                'reason': 'Not independently confirmed at sufficient confidence'})
            else:
                facts.append({**fact, 'confidenceLevel': 'HIGH' if confidence >= .9 else 'MEDIUM'})
    if abs(cursor-duration) > .00001:
        raise ValueError('Observation does not cover source duration')
    for item in visual.get('uncertainObservations', []):
        _range(item['start'], item['end'], duration)
        if not item.get('visualEvidenceRefs') or any(r not in samples for r in item['visualEvidenceRefs']):
            raise ValueError('Unknown observation still needs evidence')
        unknown.append({**item, 'status': 'UNKNOWN'})
    audio_events: list[dict[str, Any]] = []
    audio_aligned = False
    if audio:
        if audio['sourceHash'] != source_hash or file_hash(audio['audioRef']) != audio['audioHash']:
            raise ValueError('Audio source/evidence hash mismatch')
        offset = audio['timebase']['offsetSeconds']
        _range(offset, offset + audio['decodedDuration'], duration)
        audio_aligned = verification.get('audioTimebaseVerified') is True
        if audio.get('method') == 'TEMPORAL_AUDIO_SEMANTIC':
            if verification.get('audioFingerprint') != sha256_canonical(audio):
                raise ValueError('Stale audio review')
            reviewed = set(verification.get('confirmedAudioIds', []))
            for event in audio.get('semanticEvents', []):
                _range(event['start'], event['end'], duration)
                if not offset <= event['start'] <= event['end'] <= offset+audio['decodedDuration']:
                    raise ValueError('Audio event outside audio stream')
                if event.get('audioEvidenceRefs') != [audio['audioHash']]:
                    raise ValueError('Missing audio event evidence')
                if event.get('layer') not in {'SPEECH','PERFORMANCE_SOUND','ENVIRONMENT_AMBIENCE','OTHER_SOUND_EVENT','SUBJECTIVE_AUDIO_CHANGE'}:
                    raise ValueError('Unknown audio layer')
                if event.get('confidence') not in {'HIGH','MEDIUM','LOW'}:
                    raise ValueError('Invalid audio confidence')
                if event['id'] in reviewed and event['confidence'] != 'LOW':
                    audio_events.append(event)
    domains = {f['domain'] for f in facts}
    actions = [f for f in facts if f['domain'] in {'actions','action_order'}]
    visual_pass = 'visible_subjects' in domains and len({f['start'] for f in actions}) >= 2
    gates = {'VISUAL': 'PASS' if visual_pass else 'FAIL',
             'SPATIAL': 'PASS' if domains & {'spatial_relations','prop_relations'} else 'FAIL',
             'AUDIO': 'PASS' if audio_events and audio_aligned else 'FAIL',
             'UNCERTAINTY': 'PASS' if unknown else 'FAIL', 'BLINDNESS': 'PASS',
             'TEMPORAL_ALIGNMENT': 'PASS' if audio_aligned else 'FAIL'}
    passed = all(v == 'PASS' for v in gates.values())
    events = []
    for fact in facts:
        matched = [e for e in audio_events if max(e['start'], fact['start']) < min(e['end'], fact['end'])]
        events.append({'id': fact['id'], 'start': fact['start'], 'end': fact['end'],
                       'visual': fact, 'audio': matched or 'UNRESOLVED',
                       'alignmentMeaning': 'time overlap only; no causal/source identity inference',
                       'confidence': fact['confidenceLevel'], 'audioConfidence': 'UNRESOLVED' if not matched else 'REVIEWED'})
    return {'sourceHash': source_hash, 'duration': duration, 'gates': gates,
            'LV0': 'PASS' if passed else 'PARTIAL_CAPABILITY' if visual_pass and gates['AUDIO']=='FAIL' else 'FAIL_ATTESTATION',
            'runtimeStatus': 'VALIDATED' if passed else 'NOT_VALIDATED',
            'events': events, 'unknown': unknown, 'audioEvents': audio_events,
            'provenance': {'visualFingerprint': sha256_canonical(visual),
                           'verificationFingerprint': sha256_canonical(verification),
                           'method': 'TEMPORAL_VISUAL', 'runtime': visual['method'],
                           'observerVersion': visual['version']},
            'fullAVSemanticFusion': passed,
            'formalMediaAuthorized': False, 'writes': 0}
