from __future__ import annotations

from typing import Any

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.dpd import (
    BeatDPD,
    DPDLayerState,
    DPDSnapshot,
    EffectiveDPD,
    LineDPD,
    SceneDPD,
)


_INHERITED_FIELDS = tuple(DPDLayerState.model_fields)
_REQUIRED_EFFECTIVE_FIELDS = (
    "objective",
    "interaction_target",
    "tactic",
    "authority_position",
    "relationship_stance",
    "internal_activation",
    "external_control",
    "public_private_context",
)


def _merge_layers(*layers: DPDLayerState | None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for layer in layers:
        if layer is None:
            continue
        for field_name in _INHERITED_FIELDS:
            value = getattr(layer, field_name)
            if value is not None:
                merged[field_name] = value
    return merged


def compose_effective_dpd(
    scene: SceneDPD,
    beat: BeatDPD,
    line: LineDPD,
) -> EffectiveDPD:
    """Compose Scene → Beat → Line with deterministic last-writer precedence."""

    if beat.scene_id != scene.scene_id or line.scene_id != scene.scene_id:
        raise ValueError("DPD scene reference mismatch")
    if line.beat_id != beat.beat_id:
        raise ValueError("DPD beat reference mismatch")

    inherited = _merge_layers(scene.direction, beat.direction, line.direction)
    missing = [name for name in _REQUIRED_EFFECTIVE_FIELDS if inherited.get(name) is None]
    if missing:
        raise ValueError(f"DPD required effective fields missing: {', '.join(missing)}")
    if inherited.get("performance_boundaries") is None:
        inherited["performance_boundaries"] = ()

    return EffectiveDPD(
        scene_id=scene.scene_id,
        beat_id=beat.beat_id,
        spoken_content_id=line.spoken_content_id,
        actor=beat.actor,
        speaker=line.speaker,
        dramatic_purpose=scene.dramatic_purpose,
        conflict_condition=scene.conflict_condition,
        power_structure=scene.power_structure,
        emotional_climate=scene.emotional_climate,
        urgency_context=scene.urgency_context,
        information_asymmetry=scene.information_asymmetry,
        social_constraints=scene.social_constraints,
        obstacle=beat.obstacle,
        transition_trigger=beat.transition_trigger,
        dramatic_action=line.dramatic_action,
        observable_intent=line.observable_intent,
        continuity=line.continuity,
        change_from_previous=line.change_from_previous,
        **inherited,
    )


def _snapshot_material(
    scene: SceneDPD,
    beat: BeatDPD,
    line: LineDPD,
    effective: EffectiveDPD,
) -> dict[str, Any]:
    return {
        "schemaVersion": "dpd-snapshot-v1",
        "scene": dump_contract(scene),
        "beat": dump_contract(beat),
        "line": dump_contract(line),
        "effective": dump_contract(effective),
    }


def fingerprint_dpd(snapshot: DPDSnapshot) -> str:
    """Return the material fingerprint, excluding the stored fingerprint itself."""

    return sha256_canonical(
        _snapshot_material(
            snapshot.scene,
            snapshot.beat,
            snapshot.line,
            snapshot.effective,
        )
    )


def compose_dpd(scene: SceneDPD, beat: BeatDPD, line: LineDPD) -> DPDSnapshot:
    effective = compose_effective_dpd(scene, beat, line)
    fingerprint = sha256_canonical(_snapshot_material(scene, beat, line, effective))
    return DPDSnapshot(
        scene=scene.model_copy(deep=True),
        beat=beat.model_copy(deep=True),
        line=line.model_copy(deep=True),
        effective=effective,
        fingerprint=fingerprint,
    )
