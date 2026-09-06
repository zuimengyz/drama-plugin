"""Local handoff record checks; semantic preservation still requires reading/review."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any


def check_intents(items: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = item.get("id", "")
        if not key or key in seen:
            errors.append("INTENT missing/duplicate id")
        seen.add(key)
        if item.get("priority") not in {"MUST", "SHOULD", "FREE"}:
            errors.append(f"INTENT {key} invalid priority")
        for field in ("sceneIds", "kind", "meaning", "why", "source"):
            if not item.get(field):
                errors.append(f"INTENT {key} missing {field}")
    return errors


def scene_handoff(scene_set: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    """Attach assigned intent to an existing selective scene set, never a global Bible."""
    if check_intents(items):
        raise ValueError("Invalid cinematic intent records")
    sid = scene_set["scope"]
    if [s["id"] for s in scene_set["sceneJobs"]] != [sid]:
        raise ValueError("A single scene working set is required")
    result = deepcopy(scene_set)
    result["cinematicIntent"] = deepcopy([i for i in items if sid in i["sceneIds"]])
    return result


def shot_context(scene_set: dict[str, Any], *, intent_ids: list[str], character_ids: list[str],
                 state_keys: list[str], fact_ids: list[str], action: str) -> dict[str, Any]:
    """Project one shot/group, retaining only explicit relevant scene material."""
    if not action.strip():
        raise ValueError("Current action is required")
    pools = {
        "intent": {i["id"]: i for i in scene_set["cinematicIntent"]},
        "character": scene_set["characters"],
        "state": scene_set["entryState"],
        "fact": {f["id"]: f for f in scene_set["authorConstraints"]},
    }
    for kind, keys in (("intent", intent_ids), ("character", character_ids),
                       ("state", state_keys), ("fact", fact_ids)):
        if not set(keys) <= pools[kind].keys():
            raise ValueError(f"Unknown {kind} selection")
    job = scene_set["sceneJobs"][0]
    return deepcopy({
        "sceneId": scene_set["scope"], "action": action,
        "cinematicIntent": [pools["intent"][k] for k in intent_ids],
        "characters": {k: pools["character"][k] for k in character_ids},
        "entryState": {k: pools["state"][k] for k in state_keys},
        "authorConstraints": [pools["fact"][k] for k in fact_ids],
        "knowledgeAtEntry": {k: job["knowledgeAtEntry"].get(k, []) for k in character_ids},
        "receiptsWithinScene": [r for r in job["receiptsWithinScene"] if r["speaker"] in character_ids],
        "povPolicy": scene_set["povPolicy"],
    })


def review_intents(items: list[dict[str, Any]], shots: list[dict[str, Any]],
                   assessments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize declared semantic review; absent obligations cannot silently pass."""
    if check_intents(items):
        raise ValueError("Invalid cinematic intent records")
    index = {s["id"]: s for s in shots}
    reviewed = {a["intentId"]: a for a in assessments}
    if len(index) != len(shots) or len(reviewed) != len(assessments):
        raise ValueError("Duplicate shot or assessment")
    if not reviewed.keys() <= {i["id"] for i in items}:
        raise ValueError("Unknown intent assessment")
    rows: list[dict[str, Any]] = []
    for item in items:
        a = reviewed.get(item["id"], {})
        status = a.get("status", "N/A" if item["priority"] == "FREE" else "INTENT_LOSS")
        shot_ids = a.get("shotIds", [])
        reason = a.get("evidence", "Not implemented")
        if status not in {"PASS", "ACCEPTABLE_INTERPRETATION", "INTENT_LOSS", "CONFLICT", "N/A"}:
            raise ValueError("Invalid review status")
        if any(s not in index or index[s]["sceneId"] not in item["sceneIds"] for s in shot_ids):
            raise ValueError("Review cites an unknown or unrelated shot")
        if status in {"PASS", "ACCEPTABLE_INTERPRETATION"} and (not shot_ids or not a.get("evidence")):
            status = "INTENT_LOSS"
        if status == "N/A" and item["priority"] != "FREE":
            status = "INTENT_LOSS"
        blocking = status == "CONFLICT" or (item["priority"] == "MUST" and status == "INTENT_LOSS")
        rows.append({"intentId": item["id"], "priority": item["priority"], "status": status,
                     "shotIds": shot_ids, "evidence": reason, "blocking": blocking,
                     "reviewRequired": status == "INTENT_LOSS",
                     "owner": "SHOT_PLANNING" if status in {"INTENT_LOSS", "CONFLICT"} else None})
    return rows


def check_epilogue(epilogue: dict[str, Any], *, body: str, closing: str,
                   claims: dict[str, Any], sources: dict[str, Any]) -> list[str]:
    """Validate attribution records and immutable separation, not source truth/prose."""
    errors: list[str] = []
    if epilogue.get("placement") != "AFTER_DRAMA_END" or not epilogue.get("boundary"):
        errors.append("EPILOGUE must be outside drama")
    for key, value in (("bodySha256", body), ("closingSha256", closing)):
        if epilogue.get(key) != hashlib.sha256(value.encode()).hexdigest():
            errors.append(f"EPILOGUE frozen {key} changed")
    entries = epilogue.get("items", [])
    if not entries or (len(entries) > 5 and not epilogue.get("lengthReason")):
        errors.append("EPILOGUE concise selection required")
    for item in entries:
        claim = claims.get(item.get("claimId"))
        if not claim or not item.get("text"):
            errors.append("EPILOGUE missing historical grounding")
            continue
        evidence = claim.get("evidence", [])
        if not evidence or any(e.get("source") not in sources or not e.get("locator") for e in evidence):
            errors.append("EPILOGUE missing source/locator")
        certainty = item.get("certainty")
        if certainty not in {"Confirmed", "Probable", "Disputed", "Dramatic Reconstruction"}:
            errors.append("EPILOGUE invalid certainty")
        if certainty != claim.get("certainty"):
            errors.append("EPILOGUE cannot promote or relabel source certainty")
        form = item.get("textForm")
        if form not in {"original", "paraphrase", "reconstruction"}:
            errors.append("EPILOGUE missing text form")
        if form == "original" and not any(e.get("excerpt") == item["text"] for e in evidence):
            errors.append("EPILOGUE original text needs matching excerpt")
        if form == "reconstruction" and certainty != "Dramatic Reconstruction":
            errors.append("EPILOGUE reconstruction is not historical fact")
    return errors
