from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from drama_plugin import DramaPlugin
from drama_plugin.contracts import BeatDPD, DPDLayerState, LineDPD, SceneDPD
from drama_plugin.dpd import compose_dpd, fingerprint_dpd


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/dpd-core-v1.yaml"


def _load_cases() -> tuple[dict[str, object], list[dict[str, object]]]:
    fixture = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    return fixture["dialogue"], fixture["cases"]


def _snapshot(case: dict[str, object]):
    scene_payload = deepcopy(case["scene"])
    beat_payload = deepcopy(case["beat"])
    line_payload = deepcopy(case["line"])
    scene_id = scene_payload["sceneId"]
    beat_id = beat_payload["beatId"]
    beat_payload.setdefault("sceneId", scene_id)
    dialogue, _ = _load_cases()
    line_payload.setdefault("sceneId", scene_id)
    line_payload.setdefault("beatId", beat_id)
    line_payload.setdefault("spokenContentId", dialogue["spokenContentId"])
    line_payload.setdefault("speaker", dialogue["speakerKey"])
    return compose_dpd(
        SceneDPD.model_validate(scene_payload),
        BeatDPD.model_validate(beat_payload),
        LineDPD.model_validate(line_payload),
    )


def test_deterministic_fixture_gives_same_line_three_distinct_directions() -> None:
    dialogue, cases = _load_cases()
    snapshots = [_snapshot(case) for case in cases]
    assert dialogue["text"] == "你可知道后果？"
    assert len({item.line.spoken_content_id for item in snapshots}) == 1
    assert {item.effective.dramatic_action for item in snapshots} == {
        "warn",
        "probe",
        "caution",
    }
    assert len({item.effective.objective for item in snapshots}) == 3
    assert len({item.effective.authority_position for item in snapshots}) == 3
    assert len({item.fingerprint for item in snapshots}) == 3
    assert [item.fingerprint for item in snapshots] == [
        case["expectedFingerprint"] for case in cases
    ]


def test_scene_beat_line_inheritance_and_line_override_are_isolated() -> None:
    _, cases = _load_cases()
    baseline = _snapshot(cases[0])
    assert baseline.effective.conflict_condition.startswith("a military crisis")
    assert baseline.effective.public_private_context == "public formal proceeding"
    assert baseline.effective.objective == "frighten the listener into obedience"
    assert baseline.effective.internal_activation == "HIGH"
    assert baseline.effective.dramatic_action == "warn"

    changed_payload = deepcopy(cases[0])
    changed_payload["line"]["dramaticAction"] = "probe"
    changed = _snapshot(changed_payload)
    assert changed.effective.dramatic_action == "probe"
    assert changed.scene == baseline.scene
    assert changed.beat == baseline.beat
    assert changed.effective.objective == baseline.effective.objective
    assert changed.fingerprint != baseline.fingerprint


def test_override_null_inheritance_and_list_reset_rules_are_explicit() -> None:
    _, cases = _load_cases()
    changed_payload = deepcopy(cases[0])
    changed_payload["beat"]["direction"]["subtext"] = "an unspoken accusation"
    changed_payload["line"]["direction"] = {
        "objective": "obtain an explicit admission",
        "subtext": None,
        "performanceBoundaries": [],
    }
    changed = _snapshot(changed_payload)
    assert changed.effective.objective == "obtain an explicit admission"
    assert changed.effective.subtext == "an unspoken accusation"
    assert changed.effective.performance_boundaries == ()

    inherited_payload = deepcopy(changed_payload)
    inherited_payload["line"]["direction"]["objective"] = None
    inherited = _snapshot(inherited_payload)
    assert inherited.effective.objective == changed_payload["beat"]["direction"]["objective"]


def test_snapshot_json_round_trip_preserves_semantics_and_fingerprint() -> None:
    _, cases = _load_cases()
    original = _snapshot(cases[0])
    rebuilt = type(original).model_validate(original.model_dump(mode="json", by_alias=True))
    assert rebuilt.effective == original.effective
    assert fingerprint_dpd(rebuilt) == original.fingerprint


def test_fingerprint_is_stable_and_mapping_order_independent() -> None:
    _, cases = _load_cases()
    first = _snapshot(cases[1])
    second = _snapshot(deepcopy(cases[1]))
    reordered = {key: cases[1]["scene"][key] for key in reversed(cases[1]["scene"])}
    reordered_case = deepcopy(cases[1])
    reordered_case["scene"] = reordered
    third = _snapshot(reordered_case)
    assert first.fingerprint == second.fingerprint == third.fingerprint
    assert fingerprint_dpd(first) == first.fingerprint


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"speed": 0.8},
        {"providerPrompt": "speak slowly"},
        {"cameraCloseUp": True},
    ],
)
def test_empty_and_projection_specific_direction_fields_fail_fast(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        DPDLayerState.model_validate(payload)


def test_unsupported_version_scope_and_blank_required_field_fail_fast() -> None:
    _, cases = _load_cases()
    invalid = deepcopy(cases[0])
    invalid["scene"]["schemaVersion"] = "dpd-v2"
    with pytest.raises(ValidationError, match="schemaVersion"):
        _snapshot(invalid)
    invalid = deepcopy(cases[0])
    invalid["scene"]["scope"] = "BEAT"
    with pytest.raises(ValidationError, match="scope"):
        _snapshot(invalid)
    invalid = deepcopy(cases[0])
    invalid["line"]["dramaticAction"] = ""
    with pytest.raises(ValidationError, match="dramaticAction"):
        _snapshot(invalid)


def test_cross_layer_references_fail_fast() -> None:
    _, cases = _load_cases()
    case = deepcopy(cases[0])
    case["beat"]["sceneId"] = "another-scene"
    with pytest.raises(ValueError, match="scene reference mismatch"):
        _snapshot(case)
    case = deepcopy(cases[0])
    case["line"]["beatId"] = "another-beat"
    with pytest.raises(ValueError, match="beat reference mismatch"):
        _snapshot(case)


def test_dpd_contract_is_character_provider_and_modality_neutral() -> None:
    contract_fields = {
        *SceneDPD.model_fields,
        *BeatDPD.model_fields,
        *LineDPD.model_fields,
        *DPDLayerState.model_fields,
    }
    forbidden = {
        "character_profile",
        "voice_id",
        "provider",
        "model",
        "speed",
        "pitch",
        "volume",
        "pause_ms",
        "camera",
        "gesture",
        "gaze",
    }
    assert contract_fields.isdisjoint(forbidden)


def test_dpd_adds_no_business_entity_or_crud_tool() -> None:
    codes = {tool.code for tool in DramaPlugin.load(ROOT).tools.list()}
    assert not any(code.startswith("dpd.") for code in codes)
