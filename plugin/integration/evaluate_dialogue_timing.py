"""Replay a planning-only fixture, then optionally compare historical measurements.

No network or physical media access. Evaluation data is loaded only after the
plan has been materialized and written; it never feeds back into planning.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.creation import Scene, Shot
from drama_plugin.contracts.dpd import DPDSnapshot
from drama_plugin.dialogue_timing import TransitionIntent, plan_dialogue_timing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    plan = plan_dialogue_timing(
        scene=Scene.model_validate(fixture["scene"]),
        shot=Shot.model_validate(fixture["shot"]),
        dpd_by_spoken_content={
            key: DPDSnapshot.model_validate(value)
            for key, value in fixture["dpdBySpokenContent"].items()
        },
        intents={key: TransitionIntent.model_validate(value) for key, value in fixture["intents"].items()},
    )
    args.output.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(dump_contract(plan), ensure_ascii=False, indent=2) + "\n"
    (args.output / "dialogue-timing-plan.json").write_text(serialized, encoding="utf-8")
    if args.evaluation is not None:
        evaluation = json.loads(args.evaluation.read_text(encoding="utf-8"))
        if evaluation["shotId"] != plan.shot_id:
            raise ValueError("evaluation Shot mismatch")
        turn = next(turn for turn in plan.turns if turn.spoken_content_id == evaluation["spokenContentId"])
        actual = evaluation["actualDialogueDurationMs"]
        anchor = evaluation["previousUserStartMs"]
        if type(actual) is not int or actual <= 0 or type(anchor) is not int or anchor < 0:
            raise ValueError("invalid evaluation measurement")
        result = {
            "planFingerprint": plan.fingerprint,
            "planStatus": plan.status,
            "plannedTargetShotDurationMs": plan.target_shot_duration_ms,
            "actualVideoDurationMs": evaluation["actualVideoDurationMs"],
            "previousUserStartMs": anchor,
            "plannerRecommendedStartMs": turn.planned_start_ms,
            "differenceMs": turn.planned_start_ms - anchor,
            "plannedWindowDurationMs": turn.planned_duration_ms,
            "actualDialogueDurationMs": actual,
            "ACTUAL_D1_FITS_PLANNED_WINDOW": "YES" if actual <= turn.planned_duration_ms else "NO",
            "USER_TIMING_REVIEW": "PENDING",
        }
        (args.output / "evaluation.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
