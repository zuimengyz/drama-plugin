"""Deterministic screenplay → existing performance contracts, without completion.

Structural/source checks are gates, not a claim to automate literary judgement.
The author supplies inspectable speakability and behavior evidence for review.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import re
from typing import Any, Mapping, Sequence

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.dpd import BeatDPD, DPDSnapshot, LineDPD, SceneDPD
from drama_plugin.dpd import compose_dpd

_ABSTRACT = {"sad", "frightened", "alienated", "angry", "lonely", "desperate",
             "悲伤", "恐惧", "孤独", "绝望", "感动", "冷漠", "愤怒", "哲学思考"}
_VOCATIVES = re.compile(r"^(?:(?:妈妈|爸爸|先生|女士|小姐|妈|爸)[\s，,。.!！?？…—、]*)+$")


def exact_text_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _concrete(value: str | None, field: str) -> None:
    if not value or value.strip().lower().strip("。.!！") in _ABSTRACT:
        raise ValueError("UNRESOLVED: " + field)


def validate_beat_playability(scene: Mapping[str, Any], beat: BeatDPD) -> None:
    # Revalidate even model_copy inputs; callers cannot bypass extra=forbid.
    beat = BeatDPD.model_validate(dump_contract(beat))
    witness = beat.playability
    if beat.scene_id != scene["id"] or witness is None:
        raise ValueError("UNRESOLVED: Beat playability / source required")
    if witness.source_scene_hash != sha256_canonical(scene):
        raise ValueError("STALE_SCREENPLAY_PLAYABILITY")
    prose = scene["content"].get("screenplayAction", "")
    audible = [line.get("text", "") for line in scene["content"].get("spokenContent", [])
               if line.get("speakerKey") == beat.actor]
    carriers = [prose, *audible] if isinstance(prose, str) else audible
    if not any(witness.source_excerpt in carrier for carrier in carriers):
        raise ValueError("UNRESOLVED: observable source carrier")
    _concrete(beat.direction.objective, "character objective")
    _concrete(beat.direction.interaction_target, "interaction target")
    _concrete(beat.direction.tactic, "playable tactic")
    for action in (*witness.playable_actions, witness.reaction):
        if action.actor != beat.actor or not action.target:
            raise ValueError("UNRESOLVED: action actor / target")
        _concrete(action.behavior, "playable action")
        if not any(action.behavior in carrier for carrier in carriers):
            raise ValueError("UNRESOLVED: action requires screenplay carrier; return to author")
    if scene['content'].get('dramaturgy') is not None:
        from drama_plugin.scene_dramaturgy import validate_carrier_order
        validate_carrier_order(scene, beat)


def validate_line_playability(scene: Mapping[str, Any], dpd: DPDSnapshot) -> dict[str, Any]:
    dpd = DPDSnapshot.model_validate(dump_contract(dpd))
    validate_beat_playability(scene, dpd.beat)
    if dpd.scene.source_fingerprint != sha256_canonical(scene):
        raise ValueError("STALE_SCREENPLAY_PLAYABILITY")
    if compose_dpd(dpd.scene, dpd.beat, dpd.line) != dpd:
        raise ValueError("STALE_SCREENPLAY_DPD")
    lines = [x for x in scene["content"].get("spokenContent", [])
             if x.get("id") == dpd.line.spoken_content_id]
    if len(lines) != 1:
        raise ValueError("UNRESOLVED: exact single dialogue source")
    line = lines[0]
    receipt = dpd.line.playability
    if not receipt:
        raise ValueError("UNRESOLVED: Dialogue Intent review")
    text = line.get("text")
    if not isinstance(text, str) or not text.strip() or exact_text_hash(text) != receipt.source_text_hash:
        raise ValueError("EXACT_DIALOGUE_TEXT_MISMATCH")
    if line.get("speakerKey") != dpd.line.speaker or dpd.line.speaker != dpd.beat.actor:
        raise ValueError("DIALOGUE_SPEAKER_MISMATCH")
    if not line.get("target") or line["target"] != dpd.effective.interaction_target:
        raise ValueError("DIALOGUE_TARGET_MISMATCH")
    if not line.get("intent") or line["intent"] != dpd.line.dramatic_action:
        raise ValueError("DIALOGUE_INTENT_MISMATCH")
    if not isinstance(line.get("performanceIntent"), str) or not line["performanceIntent"].strip():
        raise ValueError("UNRESOLVED: source dialogue delivery")
    _concrete(dpd.effective.objective, "effective character objective")
    _concrete(dpd.effective.tactic, "effective playable tactic")
    if not dpd.effective.subtext:
        raise ValueError("UNRESOLVED: dialogue subtext (including explicit literal intention)")
    if _VOCATIVES.fullmatch(text.strip()) and receipt.fragmentation != "INTENTIONALLY_UNINTELLIGIBLE":
        raise ValueError("AMBIGUOUS_DIALOGUE: vocatives do not convey the requested action")
    if ("…" in text or "..." in text or "—" in text) and receipt.fragmentation == "CONTINUOUS":
        raise ValueError("UNRESOLVED: fragmentation must be reviewed")
    return deepcopy(line)


def validate_exact_turn(scene: Mapping[str, Any], turn_id: str, dpd: DPDSnapshot) -> dict[str, Any]:
    """Bind a coverage row to its turn, not merely a valid DPD in the same Scene."""
    if (dpd.scene.scene_id, dpd.line.scene_id, dpd.line.spoken_content_id) != (scene['id'], scene['id'], turn_id):
        raise ValueError('EXACT_DIALOGUE_TURN_MISMATCH')
    return validate_line_playability(scene, dpd)


def dialogue_turn_fingerprint(scene: Mapping[str, Any], turn_id: str, dpd: DPDSnapshot) -> str:
    line = validate_exact_turn(scene, turn_id, dpd)
    return sha256_canonical({'scene': sha256_canonical(scene), 'turn': line, 'dpd': dpd.fingerprint})


def map_screenplay_performance(scene: Mapping[str, Any], scene_dpd: SceneDPD,
                               beats: Sequence[BeatDPD], lines: Sequence[LineDPD], *,
                               dramaturgy_review: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Project reviewed author inputs. No guessed objective, action, or dialogue.

    Result reuses BeatDPD / DPDSnapshot / ObservableAction. Body and voice receive
    the same references; exact spokenContent remains the sole dialogue source.
    This mapping is not approval or persistence of a screenplay candidate.
    """
    if scene_dpd.scene_id != scene["id"] or scene_dpd.source_fingerprint != sha256_canonical(scene):
        raise ValueError("STALE_SCREENPLAY_PLAYABILITY")
    by_id = {b.beat_id: b for b in beats}
    if not beats or len(by_id) != len(beats):
        raise ValueError("UNRESOLVED: unique actor-playable beats required")
    for beat in beats:
        validate_beat_playability(scene, beat)
    canonical_ids = [x["id"] for x in scene["content"].get("spokenContent", [])]
    ids = [line.spoken_content_id for line in lines]
    if len(set(canonical_ids)) != len(canonical_ids) or len(ids) != len(set(ids)) or set(ids) != set(canonical_ids):
        raise ValueError("UNRESOLVED: one exact line binding per spokenContent")
    snapshots = []
    spoken = []
    for line in lines:
        if line.beat_id not in by_id:
            raise ValueError("UNRESOLVED: line beat reference")
        dpd = compose_dpd(scene_dpd, by_id[line.beat_id], line)
        spoken.append(validate_line_playability(scene, dpd))
        snapshots.append(dpd)
    receipt: dict[str, Any] = {'status': 'UNRESOLVED', 'repairOwner': 'scene-development',
                              'finding': 'SCENE_DRAMATURGY_REQUIRED', 'productionAuthorized': False}
    if scene['content'].get('dramaturgy') is not None:
        if dramaturgy_review is None:
            raise ValueError('UNRESOLVED:scene-development:DRAMATURGY_REVIEW_REQUIRED')
        from drama_plugin.scene_dramaturgy import review_scene_dramaturgy
        bound: dict[str, DPDSnapshot | BeatDPD] = {b.beat_id: b for b in beats}
        bound.update({d.line.spoken_content_id: d for d in snapshots})
        receipt = review_scene_dramaturgy(scene, bound, dramaturgy_review)
    return {"beats": tuple(b.model_copy(deep=True) for b in beats),
            "dpds": tuple(snapshots), "spokenContent": spoken, 'dramaturgy': receipt,
            'readyForDirection': receipt['status'] == 'PASS'}
