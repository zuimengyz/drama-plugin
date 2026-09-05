"""Single-Shot planning: reviewed DPD semantics -> deterministic milliseconds.

No I/O, provider, Audio/Video or accepted-timing dependency. The two small input
models below are transient planner values, not business entities or new APIs.
"""

from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import ConfigDict, model_validator

from drama_plugin.contracts.base import ContractModel, dump_contract, sha256_canonical
from drama_plugin.contracts.creation import Scene, Shot
from drama_plugin.contracts.dialogue_timing import (
    DialogueTimingPlan, DialogueTurnTiming, Fingerprint, NonBlank, PositiveMs, Transition,
)
from drama_plugin.contracts.dpd import DPDSnapshot
from drama_plugin.dpd.core import compose_dpd


class DialogueTimingPolicy(ContractModel):
    """Platform planning choices, not film-industry standards or speech estimates."""

    model_config = ConfigDict(frozen=True)
    version: NonBlank = "dialogue-timing-policy-v1"
    pre_dialogue_hold_ms: PositiveMs = 500
    post_dialogue_hold_ms: PositiveMs = 500
    minimum_inter_turn_separation_ms: PositiveMs = 100
    short_reaction_ms: PositiveMs = 350
    deliberate_reaction_ms: PositiveMs = 800

    @model_validator(mode="after")
    def validate_bands(self) -> DialogueTimingPolicy:
        if not (self.minimum_inter_turn_separation_ms < self.short_reaction_ms
                < self.deliberate_reaction_ms):
            raise ValueError("reaction bands must increase from immediate to deliberate")
        return self


class TransitionIntent(ContractModel):
    """Agent semantic decision pinned to the complete planning context; no ms."""

    context_fingerprint: Fingerprint
    transition: Transition | Literal["OVERLAP"]
    rationale: NonBlank


_SHOT_TIMING_FIELDS = (
    "narrativePurpose", "narrativeInputState", "requiredTransition",
    "narrativeOutputState", "subjectActionBlocking", "visualEntryState", "visualExitState",
)
_SCENE_TIMING_FIELDS = (
    "purpose", "objective", "opposition", "stakes", "turn", "tacticsAndBeats",
    "requiredTransition", "narrativeInputState", "narrativeOutputState",
)
_SPOKEN_FIELDS = (
    "id", "kind", "speakerKey", "text", "intent", "mustKeep", "performanceIntent",
    "provenance", "estimatedDurationMs",
)


def _nonblank(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value


def dialogue_timing_context(
    *, scene: Scene, shot: Shot, dpd_by_spoken_content: Mapping[str, DPDSnapshot],
) -> dict[str, Any]:
    """Resolve canonical order/identity and expose one auditable Agent context.

    The Shot fingerprint is a planning projection, not a hash of open content
    that could contain realized media. Array order is preserved, never inferred
    from names, dict iteration, Scene order, camera or former AV placement.
    """

    if shot is None or not shot.id.strip():
        raise ValueError("SHOT_REQUIRED")
    if scene is None or not scene.id.strip() or shot.scene_id != scene.id:
        raise ValueError("SCENE_SHOT_IDENTITY_MISMATCH")
    bindings = shot.content.get("spokenContentBindings")
    if not isinstance(bindings, list) or not bindings:
        raise ValueError("DIALOGUE_ORDER_REQUIRED")
    canonical = scene.content.get("spokenContent")
    if not isinstance(canonical, list):
        raise ValueError("SPOKEN_CONTENT_REQUIRED")
    items: dict[str, dict[str, Any]] = {}
    for item in canonical:
        if not isinstance(item, dict):
            raise ValueError("INVALID_SPOKEN_CONTENT")
        key = _nonblank(item.get("id"), "SPOKEN_CONTENT_ID_REQUIRED")
        if key in items:
            raise ValueError("DUPLICATE_SPOKEN_CONTENT")
        items[key] = item
    target = shot.content.get("plannedDurationMs")
    if target is not None and (type(target) is not int or target <= 0):
        raise ValueError("INVALID_SHOT_DURATION")
    resolved: list[dict[str, Any]] = []
    seen: set[str] = set()
    for sequence, binding in enumerate(bindings, 1):
        if not isinstance(binding, dict) or set(binding) != {"spokenContentId", "coverageIntent"}:
            raise ValueError("INVALID_SPOKEN_BINDING: only canonical coverage fields allowed")
        key = _nonblank(binding.get("spokenContentId"), "SPOKEN_CONTENT_ID_REQUIRED")
        if key in seen:
            raise ValueError("DUPLICATE_SPOKEN_CONTENT")
        seen.add(key)
        if binding["coverageIntent"] not in (
            "ON_SCREEN_SPEAKER", "REACTION", "OFF_SCREEN", "VOICE_OVER",
        ):
            raise ValueError("INVALID_COVERAGE_INTENT")
        if key not in items:
            raise ValueError("SPOKEN_CONTENT_NOT_IN_SCENE")
        item = items[key]
        speaker = _nonblank(item.get("speakerKey"), "SPEAKER_REQUIRED")
        _nonblank(item.get("text"), "CANONICAL_TEXT_REQUIRED")
        estimate = item.get("estimatedDurationMs")
        if estimate is None:
            raise ValueError("DURATION_ESTIMATE_REQUIRED: obtain an upstream planning estimate")
        if type(estimate) is not int or estimate <= 0:
            raise ValueError("INVALID_DURATION_ESTIMATE")
        if key not in dpd_by_spoken_content:
            raise ValueError("DPD_REQUIRED")
        snapshot = DPDSnapshot.model_validate(dump_contract(dpd_by_spoken_content[key]))
        recomposed = compose_dpd(snapshot.scene, snapshot.beat, snapshot.line)
        if snapshot != recomposed:
            raise ValueError("STALE_DPD_SNAPSHOT")
        effective = snapshot.effective
        if (effective.scene_id != scene.id or effective.spoken_content_id != key
                or effective.speaker != speaker or effective.actor != speaker):
            raise ValueError("DPD_IDENTITY_MISMATCH")
        resolved.append({
            "spokenContentId": key, "speakerKey": speaker, "sequence": sequence,
            "coverageIntent": binding["coverageIntent"],
            "spokenContentFingerprint": sha256_canonical({
                field: item.get(field) for field in _SPOKEN_FIELDS
            }),
            "estimatedDurationMs": estimate,
            "dpdFingerprint": snapshot.fingerprint,
            # Retain the full composed action/relationship context for semantic
            # review. No single HIGH/LOW field or emotion keyword is classified.
            "direction": dump_contract(effective),
        })
    if set(dpd_by_spoken_content) != seen:
        raise ValueError("DPD_SCOPE_MISMATCH: exactly one Shot's complete lines required")
    shot_material = {
        "schemaVersion": "shot-timing-source-v1", "shotId": shot.id,
        "sceneId": scene.id, "targetShotDurationMs": target,
        "orderedBindings": bindings,
        "timingContext": {key: shot.content.get(key) for key in _SHOT_TIMING_FIELDS},
    }
    return {
        "schemaVersion": "dialogue-timing-context-v1",
        "sceneId": scene.id, "shotId": shot.id,
        "shotFingerprint": sha256_canonical(shot_material),
        "targetShotDurationMs": target,
        "shotTimingContext": shot_material["timingContext"],
        "sceneTimingContext": {key: scene.content.get(key) for key in _SCENE_TIMING_FIELDS},
        "turns": resolved,
    }


def plan_dialogue_timing(
    *, scene: Scene, shot: Shot, dpd_by_spoken_content: Mapping[str, DPDSnapshot],
    intents: Mapping[str, TransitionIntent],
    policy: DialogueTimingPolicy | None = None,
) -> DialogueTimingPlan:
    """Materialize reviewed semantics. Never shrink speech or holds to fit.

    Agent reasoning must consider adjacent turns' action, objective, tactic,
    relationship, authority, activation/control and continuity/change together.
    The context fingerprint prevents reuse of that judgment after inputs change.
    """

    context = dialogue_timing_context(
        scene=scene, shot=shot, dpd_by_spoken_content=dpd_by_spoken_content,
    )
    context_fingerprint = sha256_canonical(context)
    policy = DialogueTimingPolicy.model_validate(dump_contract(policy or DialogueTimingPolicy()))
    if set(intents) != {item["spokenContentId"] for item in context["turns"]}:
        raise ValueError("TIMING_INTENT_REQUIRED: decide each turn from current DPD context")
    holds = {
        "IMMEDIATE_RESPONSE": policy.minimum_inter_turn_separation_ms,
        "SHORT_REACTION": policy.short_reaction_ms,
        "DELIBERATE_REACTION": policy.deliberate_reaction_ms,
    }
    turns: list[DialogueTurnTiming] = []
    pre_hold = policy.pre_dialogue_hold_ms
    cursor = 0
    for item in context["turns"]:
        intent = TransitionIntent.model_validate(dump_contract(intents[item["spokenContentId"]]))
        if intent.context_fingerprint != context_fingerprint:
            raise ValueError("STALE_TIMING_INTENT: review the changed DPD/planning context")
        if intent.transition == "OVERLAP":
            raise ValueError("OVERLAPPING_DIALOGUE_NOT_SUPPORTED")
        if not turns:
            if intent.transition not in ("OPENING", "IMMEDIATE_RESPONSE"):
                raise ValueError("INVALID_OPENING_TRANSITION")
            if intent.transition == "IMMEDIATE_RESPONSE":
                pre_hold = 0
            cursor = pre_hold
            hold = 0
        else:
            if intent.transition == "OPENING":
                raise ValueError("INVALID_OPENING_TRANSITION")
            hold = holds[intent.transition]
            cursor += hold
        duration = item["estimatedDurationMs"]
        turns.append(DialogueTurnTiming(
            spoken_content_id=item["spokenContentId"], speaker_key=item["speakerKey"],
            sequence=item["sequence"], spoken_content_fingerprint=item["spokenContentFingerprint"],
            dpd_fingerprint=item["dpdFingerprint"], intent_context_fingerprint=context_fingerprint,
            planned_start_ms=cursor, planned_duration_ms=duration, planned_end_ms=cursor + duration,
            transition_from_previous=intent.transition, transition_hold_ms=hold,
            transition_reason=intent.rationale,
        ))
        cursor += duration
    minimum = cursor + policy.post_dialogue_hold_ms
    target = context["targetShotDurationMs"]
    total = max(minimum, target or 0)
    conflict = target is not None and minimum > target
    material = {
        "schemaVersion": "dialogue-timing-plan-v1", "sceneId": scene.id, "shotId": shot.id,
        "shotFingerprint": context["shotFingerprint"], "sourceFingerprint": context_fingerprint,
        "policyVersion": policy.version, "policyFingerprint": sha256_canonical(policy),
        "targetShotDurationMs": target, "turns": [dump_contract(turn) for turn in turns],
        "preDialogueHoldMs": pre_hold, "minimumPostDialogueHoldMs": policy.post_dialogue_hold_ms,
        "postDialogueHoldMs": total - cursor, "recommendedMinimumShotDurationMs": minimum,
        "plannedDurationMs": total, "status": "CONFLICT" if conflict else "PLANNED",
        "diagnostic": "TIMING_CONFLICT" if conflict else None,
    }
    return DialogueTimingPlan.model_validate({**material, "fingerprint": sha256_canonical(material)})


def validate_dialogue_timing_plan(
    plan: DialogueTimingPlan, *, scene: Scene, shot: Shot,
    dpd_by_spoken_content: Mapping[str, DPDSnapshot], intents: Mapping[str, TransitionIntent],
    policy: DialogueTimingPolicy | None = None,
) -> None:
    """Validate serialized structure and replay against current sources before reuse."""

    checked = DialogueTimingPlan.model_validate(dump_contract(plan))
    current = plan_dialogue_timing(
        scene=scene, shot=shot, dpd_by_spoken_content=dpd_by_spoken_content,
        intents=intents, policy=policy,
    )
    if checked != current:
        raise ValueError("STALE_DIALOGUE_TIMING_PLAN")


def derive_visual_execution_timing(
    *, plan: DialogueTimingPlan, actual_durations_ms: Mapping[str, int], target_video_duration_ms: int,
) -> dict[str, Any]:
    """Derive this production's windows; never mutate creative estimates."""
    plan = DialogueTimingPlan.model_validate(dump_contract(plan))
    if plan.status != "PLANNED" or set(actual_durations_ms) != {t.spoken_content_id for t in plan.turns}:
        raise ValueError("COMPLETE_CURRENT_AUDIO_REQUIRED")
    if type(target_video_duration_ms) is not int or target_video_duration_ms <= 0:
        raise ValueError("INVALID_EXECUTION_TARGET")
    if any(type(d) is not int or d <= 0 for d in actual_durations_ms.values()):
        raise ValueError("INVALID_ACTUAL_AUDIO_DURATION")
    cursor = plan.pre_dialogue_hold_ms
    turns: list[dict[str, Any]] = []
    for turn in plan.turns:
        cursor += turn.transition_hold_ms
        duration = actual_durations_ms[turn.spoken_content_id]
        turns.append({"spokenContentId": turn.spoken_content_id, "speakerKey": turn.speaker_key,
                      "startMs": cursor, "endMs": cursor + duration, "durationMs": duration})
        cursor += duration
    if cursor + plan.minimum_post_dialogue_hold_ms > target_video_duration_ms:
        raise ValueError("TIMING_CONFLICT")
    material = {"schemaVersion": "visual-execution-material-v1", "sourcePlanFingerprint": plan.fingerprint,
                "targetVideoDurationMs": target_video_duration_ms, "turns": turns,
                "postHoldMs": target_video_duration_ms - cursor}
    return {**material, "fingerprint": sha256_canonical(material)}
