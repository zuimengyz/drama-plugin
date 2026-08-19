from copy import deepcopy
from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/creative-quality/dialogue-layer.yaml"
ITEM_FIELDS = {
    "id", "kind", "speakerKey", "text", "intent", "mustKeep",
    "performanceIntent", "provenance", "estimatedDurationMs",
}
RELATIONS = {"DIRECT_QUOTE", "ADAPTED", "DRAMATIZED", "FUNCTIONAL"}
COVERAGE = {"ON_SCREEN_SPEAKER", "REACTION", "OFF_SCREEN", "VOICE_OVER"}
ALIASES = {"dialogues", "dialogueLines", "spokenLines", "speech", "spokenContentRefs"}


def _normalized_quote(value: str) -> str:
    return re.sub(r"[^\w]+", "", value, flags=re.UNICODE).casefold()


def _valid_item(item: dict, speaker_keys: set[str]) -> tuple[bool, str | None]:
    if set(item) != ITEM_FIELDS or not all(item.get(key) not in (None, "") for key in ITEM_FIELDS - {"mustKeep"}):
        return False, "SPOKEN_ITEM_SCHEMA"
    if item["kind"] not in {"DIALOGUE", "NARRATION"}:
        return False, "SPOKEN_KIND"
    if item["kind"] == "DIALOGUE" and item["speakerKey"] not in speaker_keys:
        return False, "SPEAKER_IDENTITY"
    if item["kind"] == "NARRATION" and not item["speakerKey"].startswith("narrator:"):
        return False, "SPEAKER_IDENTITY"
    duration = item["estimatedDurationMs"]
    if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
        return False, "DURATION_ESTIMATE"
    provenance = item["provenance"]
    relation = provenance.get("relation")
    if relation not in RELATIONS:
        return False, "PROVENANCE_RELATION"
    if relation == "DIRECT_QUOTE":
        if not all(isinstance(provenance.get(key), str) and provenance[key].strip() for key in ("sourceRef", "locator", "excerpt")):
            return False, "DIRECT_QUOTE_EVIDENCE"
        if _normalized_quote(item["text"]) != _normalized_quote(provenance["excerpt"]):
            return False, "DIRECT_QUOTE_EVIDENCE"
    if relation == "ADAPTED" and (not provenance.get("sourceRefs") or not provenance.get("adaptationNote")):
        return False, "ADAPTED_EVIDENCE"
    return True, None


def _valid_scene(items: list[dict], speaker_keys: set[str]) -> tuple[bool, str | None]:
    ids: set[str] = set()
    for item in items:
        valid, code = _valid_item(item, speaker_keys)
        if not valid:
            return valid, code
        if item["id"] in ids:
            return False, "DUPLICATE_SPOKEN_ID"
        ids.add(item["id"])
    return True, None


def _valid_binding(shot: dict, item_ids: set[str]) -> tuple[bool, str | None]:
    duration = shot.get("plannedDurationMs")
    if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
        return False, "PLANNED_DURATION"
    if "spokenContent" in shot or any(alias in shot for alias in ALIASES):
        return False, "SHOT_DIALOGUE_COPY"
    for binding in shot.get("spokenContentBindings", []):
        if set(binding) != {"spokenContentId", "coverageIntent"}:
            return False, "SHOT_DIALOGUE_COPY"
        if binding["spokenContentId"] not in item_ids:
            return False, "UNRESOLVED_SPOKEN_BINDING"
        if binding["coverageIntent"] not in COVERAGE:
            return False, "COVERAGE_INTENT"
    return True, None


def _duration_result(items: list[dict], shots: list[dict], groups: list[list[int]]) -> tuple[bool, str | None]:
    estimates = {item["id"]: item["estimatedDurationMs"] for item in items}
    for group in groups:
        bound_ids = {
            binding["spokenContentId"]
            for index in group
            for binding in shots[index]["spokenContentBindings"]
        }
        if sum(estimates[item_id] for item_id in bound_ids) > sum(shots[index]["plannedDurationMs"] for index in group):
            return False, "DURATION_FEASIBILITY"
    return True, None


def test_dialogue_layer_fixture_has_required_generic_cases_and_expected_results() -> None:
    fixture = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["version"] == 1
    assert len(fixture["cases"]) >= 18
    assert not any("yizhao" in str(case).lower() for case in fixture["cases"])

    speaker_keys = {entry["speakerKey"] for entry in fixture["work"]["historicalActorHierarchy"]}
    results: dict[str, tuple[str, str | None]] = {}
    for case in fixture["cases"]:
        rule = case["rule"]
        if rule == "scene":
            valid, code = _valid_scene(case["spokenContent"], speaker_keys)
        elif rule == "direct-quote":
            valid, code = _valid_item(case["item"], speaker_keys)
        elif rule == "binding":
            valid, code = _valid_binding(case["shot"], {item["id"] for item in case["sceneItems"]})
        elif rule == "duration":
            valid, code = _duration_result(case["sceneItems"], case["shots"], case["groups"])
        elif rule == "revision":
            before_ids = [item["id"] for item in case["before"]]
            after_ids = [item["id"] for item in case["after"]]
            valid, code = before_ids == after_ids, "UNSTABLE_SPOKEN_ID"
        elif rule == "split":
            before_ids = {item["id"] for item in case["before"]}
            after_ids = {item["id"] for item in case["after"]}
            valid = set(case["retiredIds"]) <= before_ids - after_ids and set(case["unaffectedIds"]) <= before_ids & after_ids
            code = None if valid else "UNSTABLE_UNAFFECTED_ID"
        elif rule == "speaker-stability":
            observed: dict[str, str] = {}
            valid = True
            for scene in case["scenes"]:
                for speaker in scene:
                    previous = observed.setdefault(speaker["speakerName"], speaker["speakerKey"])
                    valid &= previous == speaker["speakerKey"] and speaker["speakerKey"] in speaker_keys
            code = None if valid else "SPEAKER_IDENTITY"
        elif rule == "provider-mutation":
            valid = deepcopy(case["before"]) == case["after"]
            code = None if valid else "SPOKEN_SOURCE_MUTATION"
        elif rule == "alias":
            valid = "spokenContent" in case["scene"] and not (set(case["scene"]) & ALIASES)
            code = None if valid else "NON_CANONICAL_DIALOGUE_FIELD"
        else:
            raise AssertionError(f"unhandled fixture rule: {rule}")

        actual = "PASS" if valid else "FAIL"
        results[case["id"]] = (actual, code)
        assert actual == case["expected"], case["id"]
        if actual == "FAIL":
            assert code == case["code"], case["id"]

    assert results["silent_scene"][0] == "PASS"
    assert results["direct_quote_without_exact_evidence"] == ("FAIL", "DIRECT_QUOTE_EVIDENCE")
    assert results["duration_conflict_blocks_production"] == ("FAIL", "DURATION_FEASIBILITY")
    assert results["provider_cannot_rewrite_scene_source"] == ("FAIL", "SPOKEN_SOURCE_MUTATION")


def test_dialogue_convention_is_routed_through_authoring_design_and_production_skills() -> None:
    convention = (ROOT / "docs/dialogue-layer-content-convention.md").read_text(encoding="utf-8")
    assert "Scene.content.spokenContent" in convention
    assert "Shot.content.spokenContentBindings" in convention
    assert "DIRECT_QUOTE" in convention and "exact `locator`" in convention
    assert "DURATION_FEASIBILITY" in convention

    for skill_code in ("scene-development", "shot-design", "shot-production"):
        instructions = (ROOT / "skills" / skill_code / "SKILL.md").read_text(encoding="utf-8")
        assert "dialogue-layer-content-convention.md" in instructions
    production = (ROOT / "skills/shot-production/SKILL.md").read_text(encoding="utf-8")
    assert "must not rewrite, delete, split, merge, or replace" in production
