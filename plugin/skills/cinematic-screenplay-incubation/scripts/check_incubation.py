"""Check a local creative ledger, never artistic quality or historical truth."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

CERTAINTIES = {"Confirmed", "Probable", "Disputed", "Later Tradition", "Dramatic Reconstruction"}


def check(bible: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    grounding = bible["historicalGrounding"]
    sources = grounding["sources"]
    claims = grounding["claims"]
    seen: set[str] = set()
    for claim in claims:
        key = claim["id"]
        if key in seen:
            errors.append(f"HISTORY duplicate claim: {key}")
        for field in ("actor", "time", "location", "cause", "motivation", "knownInformation",
                      "constraint", "decision", "consequence", "evidence", "certainty"):
            if not claim.get(field):
                errors.append(f"HISTORY {key} missing {field}; record unknown explicitly")
        if claim.get("certainty") not in CERTAINTIES:
            errors.append(f"HISTORY {key} invalid certainty")
        if any(source not in sources for source in claim.get("evidence", [])):
            errors.append(f"HISTORY {key} dangling evidence")
        if any(cause not in seen for cause in claim.get("causeIds", [])):
            errors.append(f"HISTORY {key} cause must precede consequence")
        if claim.get("certainty") == "Disputed" and not (
            claim.get("alternatives") and claim.get("adaptationPosition")
        ):
            errors.append(f"HISTORY {key} disputed claim needs alternatives and position")
        seen.add(key)

    characters = set(bible["characters"])
    state = deepcopy(bible["ledger"]["initialState"])
    knowledge = {speaker: set(items) for speaker, items in bible["ledger"]["initialKnowledge"].items()}
    scene_ids: list[str] = []
    for scene in bible["sequence"]:
        sid = scene["id"]
        if sid in scene_ids:
            errors.append(f"CONTINUITY duplicate scene: {sid}")
        scene_ids.append(sid)
        if scene["owner"] not in characters:
            errors.append(f"CHARACTER {sid} unknown owner")
        for change in scene.get("entryChanges", []):
            if not change.get("reason"):
                errors.append(f"CONTINUITY {sid} unexplained entry change")
            state[change["key"]] = change["value"]
        if scene["inputState"] != state:
            errors.append(f"CONTINUITY {sid} input differs from previous output")
        incoming = {speaker: set(items) for speaker, items in scene["knowledgeIn"].items()}
        if incoming != knowledge:
            errors.append(f"KNOWLEDGE {sid} incoming information changed without receipt")
        receipts = scene.get("receipts", [])
        for receipt in receipts:
            if receipt["speaker"] not in characters or not receipt.get("channel"):
                errors.append(f"KNOWLEDGE {sid} invalid receipt")
        for decision in scene.get("decisions", []):
            speaker = decision["speaker"]
            known = incoming.get(speaker, set()) | {
                receipt["information"] for receipt in receipts
                if receipt["speaker"] == speaker and receipt["beforeBeat"] <= decision["beat"]
            }
            if speaker not in characters or not set(decision["uses"]) <= known:
                errors.append(f"KNOWLEDGE {sid} decision uses unavailable information")
        for receipt in receipts:
            knowledge.setdefault(receipt["speaker"], set()).add(receipt["information"])
        state = deepcopy(scene["outputState"])

    for setup in bible["ledger"].get("foreshadow", []):
        start, payoff = setup["setupScene"], setup.get("payoffScene")
        if start not in scene_ids or (payoff and (payoff not in scene_ids or scene_ids.index(payoff) < scene_ids.index(start))):
            errors.append(f"PAYOFF {setup['id']} invalid setup/payoff order")
        if setup.get("status") == "PAID" and not payoff:
            errors.append(f"PAYOFF {setup['id']} paid without payoff")

    review = bible["review"]
    findings = {finding["id"]: finding for finding in review["findings"]}
    if len(findings) != len(review["findings"]):
        errors.append("REVIEW duplicate finding")
    for finding in findings.values():
        for field in ("problem", "severity", "layer", "evidence", "recommendedRevisionScope"):
            if not finding.get(field):
                errors.append(f"REVIEW {finding['id']} missing {field}")
    rounds = review["rounds"]
    if len(rounds) > 2:
        errors.append("REVISION exceeds two corrective rounds")
    previous_after = None
    for number, revision in enumerate(rounds, 1):
        if revision["number"] != number:
            errors.append("REVISION round order mismatch")
        before, after = revision["before"], revision["after"]
        if previous_after is not None and previous_after != before:
            errors.append("REVISION before hashes do not match previous round")
        previous_after = after
        changed = {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
        if changed != set(revision["changedScopes"]):
            errors.append("REVISION changed bodies differ from declared scope")
        scopes: set[str] = set()
        for fid in revision["findingIds"]:
            if fid not in findings:
                errors.append(f"REVISION unknown finding {fid}")
            else:
                scopes.update(findings[fid]["recommendedRevisionScope"])
        if not changed or not changed <= scopes:
            errors.append("REVISION no change or change outside findings")
    if review["freeze"]["status"] == "FROZEN":
        if not review["freeze"].get("revision"):
            errors.append("FREEZE missing exact revision")
        if any(f["severity"] in {"CRITICAL", "MAJOR"} and not f.get("resolved") for f in findings.values()):
            errors.append("FREEZE unresolved severe finding")
    return errors + check_meta(bible)


def affected_scopes(bible: dict[str, Any], changed: list[str]) -> list[str]:
    """Return only explicitly consumed dependencies, including the changed roots."""
    affected = set(changed)
    edges = bible.get("dependencies", [])
    while True:
        expanded = affected | {edge["target"] for edge in edges if edge["source"] in affected}
        if expanded == affected:
            return sorted(affected)
        affected = expanded


def project(bible: dict[str, Any], *, scene_id: str | None = None,
            episode_id: str | None = None) -> dict[str, Any]:
    """Select author constraints separately from time-bound character knowledge."""
    if (scene_id is None) == (episode_id is None):
        raise ValueError("Select exactly one scene or episode")
    scenes = [s for s in bible["sequence"] if s["id"] == scene_id] if scene_id else [
        s for s in bible["sequence"] if s.get("episodeId") == episode_id]
    if not scenes:
        raise ValueError("Unknown working-set scope")
    selection = {key: set().union(*(set(s["context"][key]) for s in scenes)) for key in
                 ("factIds", "characterIds", "relationshipIds", "stateKeys", "setupIds", "lensIds")}
    def select(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        indexed = {item["id"]: item for item in items}
        missing = selection[key] - indexed.keys()
        if missing:
            raise ValueError(f"Unknown {key}: {sorted(missing)}")
        return [deepcopy(indexed[item]) for item in sorted(selection[key])]
    first = scenes[0]
    previous_index = bible["sequence"].index(first) - 1
    previous = bible["sequence"][previous_index]["outputState"] if previous_index >= 0 else bible["ledger"]["initialState"]
    missing_characters = selection["characterIds"] - bible["characters"].keys()
    if missing_characters or not selection["stateKeys"] <= first["inputState"].keys():
        raise ValueError("Unknown character/state reference")
    meta = bible["direction"]["meta"]
    return {
        "scope": scene_id or episode_id,
        "authorConstraints": select(bible["historicalGrounding"]["claims"], "factIds"),
        "characters": {key: {k: deepcopy(v) for k, v in bible["characters"][key].items()
                            if k in {"identity", "behaviorModel", "invariants", "capabilities", "textualVoice", "elasticity"}}
                       for key in sorted(selection["characterIds"])},
        "relationships": select(bible["relationships"], "relationshipIds"),
        "entryState": {key: deepcopy(first["inputState"][key]) for key in sorted(selection["stateKeys"])},
        "previousOutput": {key: deepcopy(previous[key]) for key in sorted(selection["stateKeys"]) if key in previous},
        "sceneJobs": [{"id": s["id"], "job": s["goal"], "turn": s["turn"],
                       "knowledgeAtEntry": {key: deepcopy(s["knowledgeIn"].get(key, [])) for key in sorted(selection["characterIds"])},
                       "receiptsWithinScene": [deepcopy(r) for r in s.get("receipts", []) if r["speaker"] in selection["characterIds"]]}
                      for s in scenes],
        "activeSetups": select(bible["ledger"].get("foreshadow", []), "setupIds"),
        "subjectiveMoments": select(meta["subjectiveLens"]["subjectiveMoments"], "lensIds"),
        "style": deepcopy(bible["direction"]["narrativeTexture"]),
        "povPolicy": deepcopy(meta["povContract"]),
    }


def check_meta(bible: dict[str, Any]) -> list[str]:
    """Optional V2 records; absence preserves the original ledger convention."""
    meta = bible.get("direction", {}).get("meta")
    if meta is None:
        return []
    errors: list[str] = []
    for key in ("historicalSpan", "ensembleSize", "politicalComplexity", "militaryScale", "spatialComplexity",
                "evidenceUncertainty", "informationAsymmetry", "emotionalIntensity", "continuityHorizon",
                "spectacleRequirement", "dialogueDensity", "subjectiveIntensity"):
        if meta["loadProfile"].get(key) not in {"LOW", "MEDIUM", "HIGH", "VERY_HIGH", "N/A"}:
            errors.append(f"META invalid load: {key}")
    for key, use in meta["capabilityUse"].items():
        if use["level"] not in {"N/A", "BASE", "FOCUS"} or not use.get("reason"):
            errors.append(f"META invalid capability use: {key}")
    for key in ("included", "excluded", "startState", "endState", "selectionReason"):
        if not meta["narrativeAperture"].get(key):
            errors.append(f"APERTURE missing {key}")
    pov = meta["povContract"]
    perspectives = set(pov["primaryPOV"] + pov["secondaryPOV"])
    allowed, forbidden = set(pov["allowedOmniscience"]), set(pov["forbiddenOmniscience"])
    if allowed & forbidden or not pov.get("POVTransitionRule"):
        errors.append("POV contradictory permissions or missing transition rule")
    scenes = {s["id"]: s for s in bible["sequence"]}
    for sid, scene in scenes.items():
        if scene.get("pov") not in perspectives or not set(scene.get("omniscience", [])) <= allowed:
            errors.append(f"POV {sid} forbidden perspective/omniscience")
        for deviation in scene.get("deviations", []):
            character = bible["characters"].get(deviation["speaker"], {})
            if not deviation.get("pressureEvidence") or not deviation.get("reason") or not character.get("elasticity"):
                errors.append(f"ELASTICITY {sid} deviation lacks established pressure/reason/model")
        try:
            project(bible, scene_id=sid)
        except (KeyError, ValueError) as exc:
            errors.append(f"CONTEXT {sid}: {exc}")
    lens = meta["subjectiveLens"]
    if not set(lens["allowedOmniscience"]) <= allowed:
        errors.append("LENS cannot expand POV permissions")
    for moment in lens["subjectiveMoments"]:
        if moment["scene"] not in scenes or moment["anchorCharacter"] not in bible["characters"] or moment["anchorCharacter"] not in perspectives or not moment.get("purpose"):
            errors.append("LENS missing scene/anchor/purpose")
        if moment.get("altersFacts"):
            errors.append("LENS cannot override historical facts")
        if moment.get("returnToObjective") not in lens["objectiveMoments"]:
            errors.append("LENS missing objective return")
    episode_ids: set[str] = set()
    forbidden_keys = {"shotList", "cameraNumber", "lens", "frameSize", "duration", "durationMs", "cameraMovement", "workflow", "provider"}
    def has_execution(value: Any) -> bool:
        if isinstance(value, dict):
            return bool(forbidden_keys & value.keys()) or any(has_execution(v) for v in value.values())
        return isinstance(value, list) and any(has_execution(v) for v in value)
    for episode in bible["direction"]["episodeArchitecture"]:
        eid = episode["id"]
        if eid in episode_ids:
            errors.append("EPISODE duplicate identity")
        episode_ids.add(eid)
        group = [s for s in scenes.values() if s.get("episodeId") == eid]
        if not group:
            errors.append(f"EPISODE {eid} missing scenes")
            continue
        for key in ("episodeJob", "startState", "endState", "tensionShape", "majorTurn", "emotionalPeak",
                    "breathingSpace", "afterEffect", "nextEpisodePressure"):
            if not episode.get(key):
                errors.append(f"EPISODE {eid} missing {key}")
        for label, boundary in (("startState", group[0]["inputState"]), ("endState", group[-1]["outputState"])):
            if any(boundary.get(k) != v for k, v in episode[label].items()):
                errors.append(f"EPISODE {eid} {label} contradicts scene state")
        for key in ("openingShotAnchor", "closingShotAnchor"):
            anchor = episode.get(key, {})
            if not all(anchor.get(field) for field in ("perception", "purpose", "derivedFrom")):
                errors.append(f"ANCHOR {eid} missing {key} intention")
            if has_execution(anchor):
                errors.append(f"ANCHOR {eid} contains shot execution")
    if any(s.get("episodeId") not in episode_ids for s in scenes.values()):
        errors.append("EPISODE dangling scene membership")
    for character in bible["characters"].values():
        elasticity = character.get("elasticity")
        if elasticity is not None and not all(elasticity.get(key) for key in (
            "normalBehavior", "pressureResponse", "breakCondition", "possibleDeviation", "recoveryPattern"
        )):
            errors.append("ELASTICITY incomplete bounded model")
    for edge in bible.get("dependencies", []):
        if not edge.get("reason"):
            errors.append("DEPENDENCY missing consumption reason")
    for revision in bible["review"]["rounds"]:
        inv = revision.get("invalidation")
        if not inv:
            errors.append("DEPENDENCY revision missing predeclared invalidation")
            continue
        actual = set(affected_scopes(bible, inv["changedNodes"]))
        if actual != set(inv["affectedScopes"]) or actual & set(inv["unaffectedScopes"]):
            errors.append("DEPENDENCY scope differs from declared consumers")
        if not actual <= set(inv["recheckedScopes"]) or not set(revision["changedScopes"]) <= actual:
            errors.append("DEPENDENCY missing recheck or unrelated edit")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bible", type=Path)
    args = parser.parse_args()
    try:
        errors = check(json.loads(args.bible.read_text(encoding="utf-8")))
    except (KeyError, TypeError, ValueError) as exc:
        errors = [f"Invalid ledger convention: {exc}"]
    print(json.dumps({"recordIntegrity": "FAIL" if errors else "PASS", "errors": errors,
                      "artisticAcceptance": "NOT_EVALUATED"}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
