from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest
from pydantic import ValidationError

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.creation import Scene, Shot
from drama_plugin.contracts.dialogue_timing import DialogueTimingPlan, DialogueTurnTiming
from drama_plugin.contracts.dpd import BeatDPD, DPDLayerState, DPDSnapshot, LineDPD, PerformanceLevel, SceneDPD
from drama_plugin.dialogue_timing import (
    DialogueTimingPolicy, TransitionIntent, dialogue_timing_context,
    plan_dialogue_timing, validate_dialogue_timing_plan,
)
from drama_plugin.dpd.core import compose_dpd


ROOT = Path(__file__).resolve().parents[1]
REAL_FIXTURE = ROOT / "tests/fixtures/dialogue-timing-72.json"


def fixture_inputs(*, single=False, immediate=False, target=6500):
    """A–D: whole-line offline fixtures with different playable DPD actions."""
    items = [
        {"id": "request", "speakerKey": "speaker:a", "text": "请先核实军报。", "estimatedDurationMs": 1800},
        {"id": "reply", "speakerKey": "speaker:b", "text": "我去核实。", "estimatedDurationMs": 1600},
    ][:1 if single else 2]
    for item in items:
        item.update(kind="DIALOGUE", intent="seek verification", mustKeep=True,
                    performanceIntent="keep the decision legible", provenance={"relation": "FUNCTIONAL"})
    scene = Scene(id="scene-test", episode_id="episode-test", order=1, title="Awaiting a dispatch",
                  content={"spokenContent": items, "turn": "an uncertain report becomes a task to verify"})
    shot = Shot(id="shot-test", scene_id=scene.id, shot_no="1", content={
        "plannedDurationMs": target,
        "spokenContentBindings": [{"spokenContentId": item["id"], "coverageIntent": "ON_SCREEN_SPEAKER"}
                                  for item in items],
        "visualEntryState": "a dispatch has just been read",
        "visualExitState": "the listener commits to verification",
    })
    scene_dpd = SceneDPD(
        scene_id=scene.id, source_fingerprint=sha256_canonical(dump_contract(scene)),
        dramatic_purpose="turn uncertain information into a verifiable task",
        conflict_condition="acting on the unverified report could expose the position",
        power_structure="two officers need agreement before action",
        direction=DPDLayerState(public_private_context="private consultation"),
    )
    dpds = {}
    for index, item in enumerate(items):
        reply = index == 1
        beat = BeatDPD(
            scene_id=scene.id, beat_id=f"beat-{index}", actor=item["speakerKey"],
            obstacle="no verified dispatch is available",
            transition_trigger=("answer as soon as the request finishes" if immediate and reply
                                else "the preceding information has been fully heard"),
            direction=DPDLayerState(
                objective="commit to immediate verification" if immediate and reply else "weigh the task before committing",
                interaction_target="speaker:a" if reply else "speaker:b",
                tactic="take the turn at once" if immediate and reply else "consider the implication then accept",
                authority_position="peer officer", relationship_stance="cooperative but responsible for the risk",
                internal_activation="HIGH", external_control="HIGH",
            ),
        )
        line = LineDPD(
            scene_id=scene.id, beat_id=beat.beat_id, spoken_content_id=item["id"], speaker=item["speakerKey"],
            dramatic_action="commit" if reply else "request",
            observable_intent="take responsibility for verifying the report",
            continuity="immediate response after the completed request" if immediate and reply else "listen then judge the proposal",
            change_from_previous="convert the request directly to action" if immediate and reply else "move from uncertainty to a considered commitment",
        )
        dpds[item["id"]] = compose_dpd(scene_dpd, beat, line)
    inputs = {"scene": scene, "shot": shot, "dpd_by_spoken_content": dpds}
    context = sha256_canonical(dialogue_timing_context(**inputs))
    inputs["intents"] = {
        item["id"]: TransitionIntent(
            context_fingerprint=context,
            transition="OPENING" if index == 0 else "IMMEDIATE_RESPONSE" if immediate else "DELIBERATE_REACTION",
            rationale=("The prior request finishes; commit/act-at-once objective and tactic, peer cooperation, "
                       "shared risk, HIGH activation/control and direct request-to-action continuity support "
                       "an immediate non-overlapping answer." if immediate and index else
                       "The request/commit action, weighed objective/tactic, responsible peer relationship, "
                       "equal authority, HIGH activation/control and listen-to-judgment continuity call for "
                       "a readable establishment or judgment beat."),
        ) for index, item in enumerate(items)
    }
    return inputs


def refresh_intents(inputs):
    context = sha256_canonical(dialogue_timing_context(**{k: v for k, v in inputs.items() if k != "intents"}))
    inputs["intents"] = {key: intent.model_copy(update={"context_fingerprint": context})
                         for key, intent in inputs["intents"].items()}


def load_real():
    raw = json.loads(REAL_FIXTURE.read_text(encoding="utf-8"))
    return {
        "scene": Scene.model_validate(raw["scene"]), "shot": Shot.model_validate(raw["shot"]),
        "dpd_by_spoken_content": {key: DPDSnapshot.model_validate(value) for key, value in raw["dpdBySpokenContent"].items()},
        "intents": {key: TransitionIntent.model_validate(value) for key, value in raw["intents"].items()},
    }


def resign(payload):
    payload["fingerprint"] = sha256_canonical({k: v for k, v in payload.items() if k != "fingerprint"})
    return payload


def test_fixture_a_single_speaker_pre_speech_post():
    inputs = fixture_inputs(single=True, target=4000)
    before = deepcopy(inputs)
    plan = plan_dialogue_timing(**inputs)
    assert inputs == before
    assert plan.status == "PLANNED"
    assert plan.pre_dialogue_hold_ms == 500
    assert (plan.turns[0].planned_start_ms, plan.turns[0].planned_end_ms) == (500, 2300)
    assert plan.post_dialogue_hold_ms == 1700
    assert plan.recommended_minimum_shot_duration_ms == 2800
    assert plan.planned_duration_ms == 4000


def test_fixture_b_two_speakers_keep_order_reaction_and_estimates():
    inputs = fixture_inputs()
    plan = plan_dialogue_timing(**inputs)
    assert [turn.spoken_content_id for turn in plan.turns] == ["request", "reply"]
    assert [turn.speaker_key for turn in plan.turns] == ["speaker:a", "speaker:b"]
    assert plan.turns[1].planned_start_ms - plan.turns[0].planned_end_ms == 800
    assert [turn.planned_duration_ms for turn in plan.turns] == [1800, 1600]
    assert plan.turns[-1].planned_end_ms + plan.post_dialogue_hold_ms == 6500
    validate_dialogue_timing_plan(plan, **inputs)


def test_fixture_c_action_and_continuity_give_shorter_immediate_response():
    deliberate = plan_dialogue_timing(**fixture_inputs())
    immediate = plan_dialogue_timing(**fixture_inputs(immediate=True))
    assert immediate.turns[1].transition_hold_ms == 100 < deliberate.turns[1].transition_hold_ms
    assert immediate.turns[1].planned_start_ms >= immediate.turns[0].planned_end_ms
    assert immediate.fingerprint != deliberate.fingerprint
    assert immediate.turns[1].planned_duration_ms == deliberate.turns[1].planned_duration_ms


def test_fixture_d_conflict_preserves_speech_reaction_and_post_hold():
    inputs = fixture_inputs(target=3000)
    before = deepcopy(inputs)
    plan = plan_dialogue_timing(**inputs)
    assert plan.status == "CONFLICT" and plan.diagnostic == "TIMING_CONFLICT"
    assert plan.recommended_minimum_shot_duration_ms == plan.planned_duration_ms == 5200
    assert plan.post_dialogue_hold_ms == 500
    assert plan.turns[1].transition_hold_ms == 800
    assert sum(turn.planned_duration_ms for turn in plan.turns) == 3400
    assert inputs == before
    assert DialogueTimingPlan.model_validate_json(plan.model_dump_json()) == plan


def test_fixture_e_current_72_plan_then_comparison():
    plan = plan_dialogue_timing(**load_real())
    assert plan.target_shot_duration_ms == 10500
    assert [(t.planned_start_ms, t.planned_end_ms) for t in plan.turns] == [(500, 5500), (6300, 9500)]
    assert plan.post_dialogue_hold_ms == 1000
    assert plan.recommended_minimum_shot_duration_ms == 10000
    evaluation = json.loads((ROOT / "tests/fixtures/dialogue-timing-72-evaluation.json").read_text())
    assert plan.turns[1].planned_start_ms - evaluation["previousUserStartMs"] == 1100
    assert evaluation["actualDialogueDurationMs"] > plan.turns[1].planned_duration_ms
    assert plan.turns[1].dpd_fingerprint == "2d826a70c27da23aded5eda30082931b5c122115dd932ce104b3fb590ec90e1b"
    assert "此事若行" not in plan.model_dump_json()


def test_same_input_and_recursive_dictionary_reorder_preserve_plan_and_hash():
    def reverse(value):
        if isinstance(value, dict):
            return {key: reverse(value[key]) for key in reversed(value)}
        if isinstance(value, list):
            return [reverse(item) for item in value]
        return value
    inputs = load_real()
    original = plan_dialogue_timing(**inputs)
    assert original == plan_dialogue_timing(**deepcopy(inputs))
    inputs["scene"] = Scene.model_validate(reverse(dump_contract(inputs["scene"])))
    inputs["shot"] = Shot.model_validate(reverse(dump_contract(inputs["shot"])))
    inputs["dpd_by_spoken_content"] = {key: DPDSnapshot.model_validate(reverse(dump_contract(value)))
                                      for key, value in reversed(inputs["dpd_by_spoken_content"].items())}
    assert original == plan_dialogue_timing(**inputs)


@pytest.mark.parametrize("change", ["text", "speaker", "estimate", "order", "duration", "dpd", "action"])
def test_material_changes_invalidate_intent_and_old_plan(change):
    inputs = fixture_inputs()
    old = plan_dialogue_timing(**inputs)
    if change == "text":
        inputs["scene"].content["spokenContent"][1]["text"] += "请等候。"
    elif change == "estimate":
        inputs["scene"].content["spokenContent"][1]["estimatedDurationMs"] += 100
    elif change == "order":
        inputs["shot"].content["spokenContentBindings"].reverse()
        inputs["intents"]["request"] = inputs["intents"]["request"].model_copy(update={"transition": "SHORT_REACTION"})
        inputs["intents"]["reply"] = inputs["intents"]["reply"].model_copy(update={"transition": "OPENING"})
    elif change == "duration":
        inputs["shot"].content["plannedDurationMs"] += 100
    elif change == "action":
        inputs["shot"].content["subjectActionBlocking"] = "the listener must finish a task before answering"
    else:
        snapshot = inputs["dpd_by_spoken_content"]["reply"]
        if change == "speaker":
            inputs["scene"].content["spokenContent"][1]["speakerKey"] = "speaker:c"
            snapshot.beat.actor = snapshot.line.speaker = "speaker:c"
        else:
            snapshot.line.continuity = "a new obstacle calls for renewed assessment"
        inputs["dpd_by_spoken_content"]["reply"] = compose_dpd(snapshot.scene, snapshot.beat, snapshot.line)
    with pytest.raises(ValueError, match="STALE_TIMING_INTENT"):
        plan_dialogue_timing(**inputs)
    refresh_intents(inputs)  # simulated new Agent review, never done by production replay
    new = plan_dialogue_timing(**inputs)
    assert old.fingerprint != new.fingerprint
    with pytest.raises(ValueError, match="STALE_DIALOGUE_TIMING_PLAN"):
        validate_dialogue_timing_plan(old, **inputs)
    if change == "order":
        assert [turn.spoken_content_id for turn in new.turns] == ["reply", "request"]


def test_policy_material_and_version_are_fingerprinted_and_replayed():
    inputs = fixture_inputs()
    old = plan_dialogue_timing(**inputs)
    changed = DialogueTimingPolicy(deliberate_reaction_ms=900)
    new = plan_dialogue_timing(**inputs, policy=changed)
    assert new.turns[1].planned_start_ms - old.turns[1].planned_start_ms == 100
    assert new.policy_fingerprint != old.policy_fingerprint
    with pytest.raises(ValueError, match="STALE_DIALOGUE_TIMING_PLAN"):
        validate_dialogue_timing_plan(old, **inputs, policy=changed)
    version = plan_dialogue_timing(**inputs, policy=DialogueTimingPolicy(version="reviewed-v2"))
    assert version.fingerprint != old.fingerprint


def test_emotion_or_control_alone_does_not_select_reaction_milliseconds():
    inputs = fixture_inputs()
    original = plan_dialogue_timing(**inputs)
    for snapshot in inputs["dpd_by_spoken_content"].values():
        snapshot.scene.emotional_climate = "anger"
        snapshot.beat.direction.external_control = PerformanceLevel.LOW
    inputs["dpd_by_spoken_content"] = {key: compose_dpd(s.scene, s.beat, s.line)
                                      for key, s in inputs["dpd_by_spoken_content"].items()}
    refresh_intents(inputs)
    current = plan_dialogue_timing(**inputs)
    assert current.turns[1].transition_hold_ms == original.turns[1].transition_hold_ms
    assert current.fingerprint != original.fingerprint


def test_explicit_immediate_opening_and_short_response():
    inputs = fixture_inputs()
    inputs["intents"]["request"] = inputs["intents"]["request"].model_copy(update={"transition": "IMMEDIATE_RESPONSE"})
    inputs["intents"]["reply"] = inputs["intents"]["reply"].model_copy(update={"transition": "SHORT_REACTION"})
    plan = plan_dialogue_timing(**inputs)
    assert plan.pre_dialogue_hold_ms == plan.turns[0].planned_start_ms == 0
    assert plan.turns[1].transition_hold_ms == 350


def test_missing_target_does_not_borrow_actual_video_duration():
    inputs = fixture_inputs()
    del inputs["shot"].content["plannedDurationMs"]
    inputs["shot"].content["videoDurationMs"] = 9000
    refresh_intents(inputs)
    plan = plan_dialogue_timing(**inputs)
    assert plan.target_shot_duration_ms is None
    assert plan.planned_duration_ms == plan.recommended_minimum_shot_duration_ms == 5200


@pytest.mark.parametrize("value", [0, -1, 1.5, True, "3200"])
def test_invalid_duration_estimate(value):
    inputs = fixture_inputs()
    inputs["scene"].content["spokenContent"][1]["estimatedDurationMs"] = value
    with pytest.raises(ValueError, match="INVALID_DURATION_ESTIMATE"):
        plan_dialogue_timing(**inputs)


def test_missing_estimate_demands_upstream_authority():
    inputs = fixture_inputs()
    del inputs["scene"].content["spokenContent"][1]["estimatedDurationMs"]
    with pytest.raises(ValueError, match="DURATION_ESTIMATE_REQUIRED"):
        plan_dialogue_timing(**inputs)


@pytest.mark.parametrize("case, error", [
    ("shot", "SHOT_REQUIRED"), ("scene", "SCENE_SHOT_IDENTITY_MISMATCH"),
    ("order", "DIALOGUE_ORDER_REQUIRED"), ("unordered", "DIALOGUE_ORDER_REQUIRED"),
    ("speaker", "SPEAKER_REQUIRED"), ("duplicateBinding", "DUPLICATE_SPOKEN_CONTENT"),
    ("duplicateSpoken", "DUPLICATE_SPOKEN_CONTENT"), ("wrongScene", "SCENE_SHOT_IDENTITY_MISMATCH"),
    ("unknownSpoken", "SPOKEN_CONTENT_NOT_IN_SCENE"), ("dpd", "DPD_REQUIRED"),
    ("dpdIdentity", "DPD_IDENTITY_MISMATCH"), ("extraDpd", "DPD_SCOPE_MISMATCH"),
    ("staleDpd", "STALE_DPD_SNAPSHOT"), ("intent", "TIMING_INTENT_REQUIRED"),
    ("bindingField", "INVALID_SPOKEN_BINDING"), ("invalidTarget", "INVALID_SHOT_DURATION"),
])
def test_input_authority_failures(case, error):
    inputs = fixture_inputs()
    shot = inputs["shot"]
    items = inputs["scene"].content["spokenContent"]
    if case == "shot": inputs["shot"] = None
    elif case == "scene": inputs["scene"] = None
    elif case == "order": del shot.content["spokenContentBindings"]
    elif case == "unordered": shot.content["spokenContentBindings"] = {"reply": {}, "request": {}}
    elif case == "speaker": del items[1]["speakerKey"]
    elif case == "duplicateBinding": shot.content["spokenContentBindings"].append(shot.content["spokenContentBindings"][0])
    elif case == "duplicateSpoken": items.append(deepcopy(items[0]))
    elif case == "wrongScene": shot.scene_id = "other-scene"
    elif case == "unknownSpoken": shot.content["spokenContentBindings"][1]["spokenContentId"] = "missing"
    elif case == "dpd": inputs["dpd_by_spoken_content"].pop("reply")
    elif case == "dpdIdentity": inputs["dpd_by_spoken_content"]["reply"] = inputs["dpd_by_spoken_content"]["request"]
    elif case == "extraDpd": inputs["dpd_by_spoken_content"]["other"] = inputs["dpd_by_spoken_content"]["reply"]
    elif case == "staleDpd": inputs["dpd_by_spoken_content"]["reply"].effective.tactic = "invented"
    elif case == "intent": inputs["intents"].pop("reply")
    elif case == "bindingField": shot.content["spokenContentBindings"][1]["sequence"] = 1
    elif case == "invalidTarget": shot.content["plannedDurationMs"] = True
    with pytest.raises(ValueError, match=error):
        plan_dialogue_timing(**inputs)


def test_explicit_overlap_intent_is_rejected_without_shortening_or_overlap():
    inputs = fixture_inputs()
    inputs["intents"]["reply"] = inputs["intents"]["reply"].model_copy(update={"transition": "OVERLAP"})
    with pytest.raises(ValueError, match="OVERLAPPING_DIALOGUE_NOT_SUPPORTED"):
        plan_dialogue_timing(**inputs)


@pytest.mark.parametrize("case, error", [
    ("schema", "schemaVersion"), ("shot", "shotId"), ("speaker", "speakerKey"),
    ("duplicateSequence", "DUPLICATE_SEQUENCE"), ("missingSequence", "DIALOGUE_ORDER_REQUIRED"),
    ("duplicateSpoken", "DUPLICATE_SPOKEN_CONTENT"), ("negative", "plannedStartMs"),
    ("endBeforeStart", "INVALID_TURN_WINDOW"), ("overlap", "OVERLAPPING_DIALOGUE_NOT_SUPPORTED"),
    ("overflow", "TIMING_CONFLICT"), ("hold", "TRANSITION_HOLD_MISMATCH"),
    ("pre", "PRE_DIALOGUE_HOLD_MISMATCH"), ("post", "POST_DIALOGUE_HOLD_MISMATCH"),
    ("diagnostic", "TIMING_DIAGNOSTIC_MISMATCH"), ("total", "SHOT_DURATION_MISMATCH"),
    ("minimum", "MINIMUM_DURATION_MISMATCH"),
    ("intentContext", "INTENT_CONTEXT_MISMATCH"),
])
def test_contract_rejects_invalid_even_when_payload_is_rehashed(case, error):
    payload = dump_contract(plan_dialogue_timing(**fixture_inputs()))
    first, last = payload["turns"]
    if case == "schema": payload["schemaVersion"] = "dialogue-timing-plan-v2"
    elif case == "shot": del payload["shotId"]
    elif case == "speaker": del last["speakerKey"]
    elif case == "duplicateSequence": first["sequence"] = 2; first["transitionFromPrevious"] = "SHORT_REACTION"; first["transitionHoldMs"] = 100
    elif case == "missingSequence": last["sequence"] = 3
    elif case == "duplicateSpoken": last["spokenContentId"] = first["spokenContentId"]
    elif case == "negative": last["plannedStartMs"] = -1
    elif case == "endBeforeStart": last["plannedEndMs"] = last["plannedStartMs"] - 1
    elif case == "overlap": last["plannedStartMs"] = first["plannedEndMs"] - 1; last["plannedEndMs"] = last["plannedStartMs"] + last["plannedDurationMs"]
    elif case == "overflow": payload["targetShotDurationMs"] = 1000
    elif case == "hold": last["transitionHoldMs"] += 1
    elif case == "pre": payload["preDialogueHoldMs"] += 1
    elif case == "post": payload["postDialogueHoldMs"] += 1
    elif case == "diagnostic": payload["diagnostic"] = "TIMING_CONFLICT"
    elif case == "total": payload["plannedDurationMs"] += 1
    elif case == "minimum": payload["recommendedMinimumShotDurationMs"] += 1
    elif case == "intentContext": last["intentContextFingerprint"] = "0" * 64
    with pytest.raises(ValidationError, match=error):
        DialogueTimingPlan.model_validate(resign(payload))


@pytest.mark.parametrize("field", ["provider", "Fish", "Comfy", "ffmpeg", "Sync", "MinIO", "videoMediaId", "exactText", "pauseMs"])
def test_unknown_provider_and_actual_fields_cannot_enter_contract_or_intent(field):
    plan = plan_dialogue_timing(**fixture_inputs())
    for model, payload in [(DialogueTimingPlan, dump_contract(plan)),
                           (DialogueTurnTiming, dump_contract(plan.turns[0])),
                           (TransitionIntent, dump_contract(fixture_inputs()["intents"]["reply"]))]:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            model.model_validate({**payload, field: "injected"})


def test_tampered_hash_and_wrong_identity_fail_reuse():
    inputs = fixture_inputs()
    plan = plan_dialogue_timing(**inputs)
    bad = plan.model_copy(update={"fingerprint": "0" * 64})
    with pytest.raises(ValidationError, match="FINGERPRINT_INVALID"):
        validate_dialogue_timing_plan(bad, **inputs)
    for field in ("sceneId", "shotId"):
        payload = dump_contract(plan)
        payload[field] = "wrong"
        bad = DialogueTimingPlan.model_validate(resign(payload))
        with pytest.raises(ValueError, match="STALE_DIALOGUE_TIMING_PLAN"):
            validate_dialogue_timing_plan(bad, **inputs)


def test_camera_and_post_production_data_are_not_planning_material(monkeypatch):
    inputs = load_real()
    before = plan_dialogue_timing(**inputs)
    inputs["shot"].content.update({
        "cameraBehavior": "different camera", "framing": "CLOSE_UP", "videoContentHash": "b" * 64,
        "actualDurationMs": 4107, "dialogueStartMs": 5200, "timingAuthority": "USER_REVIEW",
        "RealizedPerformanceSnapshot": {"mouthActivity": "KNOWN"}, "VisualPerformanceBrief": {},
        "FinalShot": {}, "Comfy": {}, "timestamp": "tomorrow", "host": "other",
    })
    def forbidden(*args, **kwargs):
        raise AssertionError("planner attempted network I/O")
    monkeypatch.setattr(socket, "socket", forbidden)
    assert before == plan_dialogue_timing(**inputs)


def test_offline_runner_separates_evaluation_and_preserves_plan(tmp_path):
    fixture = ROOT / "tests/fixtures/dialogue-timing-72-evaluation.json"
    base = [sys.executable, str(ROOT / "integration/evaluate_dialogue_timing.py"),
            "--fixture", str(REAL_FIXTURE), "--output", str(tmp_path)]
    subprocess.run(base, check=True, capture_output=True)
    before = (tmp_path / "dialogue-timing-plan.json").read_bytes()
    subprocess.run([*base, "--evaluation", str(fixture)], check=True, capture_output=True)
    assert before == (tmp_path / "dialogue-timing-plan.json").read_bytes()
    evaluation = json.loads(fixture.read_text())
    evaluation.update(actualDialogueDurationMs=100, previousUserStartMs=25, actualVideoDurationMs=90000)
    changed = tmp_path / "changed-evaluation.json"
    changed.write_text(json.dumps(evaluation))
    subprocess.run([*base, "--evaluation", str(changed)], check=True, capture_output=True)
    assert before == (tmp_path / "dialogue-timing-plan.json").read_bytes()
    assert json.loads((tmp_path / "evaluation.json").read_text())["ACTUAL_D1_FITS_PLANNED_WINDOW"] == "YES"
