"""Frozen R3C inputs; all adversarial edits are isolated test copies."""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.dpd import BeatDPD, DPDSnapshot, SceneDPD, LineDPD
from drama_plugin.contracts.scene_dramaturgy import SceneDramaturgy, DramaturgyReview
from drama_plugin.dpd import compose_dpd
from drama_plugin.scene_dramaturgy import scene_body_hash, dramaturgy_subject, carrier_text, review_scene_dramaturgy

FIXTURE = Path(__file__).parent / 'fixtures/r3b_r'


def load_case(index: int) -> dict[str, Any]:
    raw: dict[str, Any] = json.loads((FIXTURE / 'screenplay-r3-dramaturgy-sidecar.json').read_text())['scenes'][index]
    scene = raw['source']
    scene['content']['dramaturgy'] = dump_contract(SceneDramaturgy.model_validate(scene['content']['dramaturgy']))
    # Keep the exact original source serialization for the frozen recheck; this
    # normalized copy is exclusively for synthetic mutation fixtures.
    return raw


def snapshots(entry: dict[str, Any]) -> dict[str, DPDSnapshot | BeatDPD]:
    return {k: DPDSnapshot.model_validate(v) if 'effective' in v else BeatDPD.model_validate(v)
            for k, v in entry['dpds'].items()}


def repin(entry: dict[str, Any]) -> None:
    """Re-author test evidence so negative cases test semantics, not stale hashes."""
    scene = entry['source']; facet = scene['content']['dramaturgy']
    facet['sourceBodyHash'] = scene_body_hash(scene)
    for c in facet['carriers']:
        c['textHash'] = sha256(carrier_text(scene, c['ref']).encode()).hexdigest()
    sd = SceneDPD.model_validate(entry['sceneDpd']).model_copy(update={'source_fingerprint': fp(scene)})
    entry['sceneDpd'] = dump_contract(sd)
    carriers = {c['ref']: c for c in facet['carriers']}
    lines = {line['id']: line for line in scene['content']['spokenContent']}
    for key, d in snapshots(entry).items():
        beat = d.beat if isinstance(d, DPDSnapshot) else d
        assert beat.playability is not None
        witness = dump_contract(beat.playability)
        witness['sourceSceneHash'] = fp(scene)
        for action, ref in zip(witness['playableActions'], witness['actionCarrierRefs']):
            c = carriers[ref]
            action.update(actor=c['actor'], target=c['target'], behavior=carrier_text(scene, ref))
        c = carriers[witness['reactionCarrierRef']]
        witness['reaction'].update(actor=c['actor'], target=c['target'], behavior=carrier_text(scene, c['ref']))
        witness['sourceExcerpt'] = witness['playableActions'][0]['behavior']
        payload = dump_contract(beat); payload['playability'] = witness
        beat = BeatDPD.model_validate(payload)
        if isinstance(d, DPDSnapshot):
            line = lines[d.line.spoken_content_id]
            ld = dump_contract(d.line)
            ld['dramaticAction'] = line['intent']
            ld['playability'].update(sourceTextHash=sha256(line['text'].encode()).hexdigest(), literalMeaning=line['intent'])
            d = compose_dpd(sd, beat, LineDPD.model_validate(ld))
        else:
            d = beat
        entry['dpds'][key] = dump_contract(d)
    entry['beats'] = [dump_contract(d.beat if isinstance(d, DPDSnapshot) else d) for d in snapshots(entry).values()]
    entry['lines'] = [dump_contract(d.line) for d in snapshots(entry).values() if isinstance(d, DPDSnapshot)]
    review = dump_contract(DramaturgyReview.model_validate(entry['dramaturgyReview']))
    review['subjectHash'] = dramaturgy_subject(scene, snapshots(entry))
    entry['dramaturgyReview'] = review


def turn(entry: dict[str, Any], lid: str) -> DPDSnapshot:
    return DPDSnapshot.model_validate(entry['dpds'][lid])


def result(entry: dict[str, Any]) -> dict[str, Any]:
    return review_scene_dramaturgy(entry['source'], snapshots(entry), entry['dramaturgyReview'])


def codes(entry: dict[str, Any]) -> set[str]:
    return {f['finding'] for f in result(entry)['findings'] if f['status'] != 'PASS'}
