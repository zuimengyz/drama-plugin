"""Optional local craft reading for authors; no production decisions or network.

The catalog supplies evidence, never executable shot facts. Stable catalog order
is deliberate: this is not an aesthetic ranking or a recommendation service.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _read(root: Path, relative: str) -> tuple[str, str]:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Knowledge path leaves its root")
    raw = path.read_bytes()
    return raw.decode("utf-8"), hashlib.sha256(raw).hexdigest()


def discover(root: Path, *, query: str = "", styles=(), goals=(), means=(),
             disciplines=(), case_ids=(), limit: int = 3) -> dict:
    """Expression aliases expand to goals, never automatically to a technique."""
    if not 1 <= limit <= 32:
        raise ValueError("limit must be between 1 and 32")
    catalog = json.loads(_read(root, "film-craft/index.json")[0])
    taxonomy = json.loads(_read(root, "cinema-styles/taxonomy.json")[0])
    rows = catalog["cases"]
    for name, values in (("styles", styles), ("goals", goals), ("means", means),
                         ("disciplines", disciplines)):
        unknown = set(values) - set(taxonomy[name])
        if unknown:
            raise ValueError(f"Unknown {name}: {', '.join(sorted(unknown))}")
    unknown_ids = set(case_ids) - {r["id"] for r in rows}
    if unknown_ids:
        raise ValueError("Unknown cases: " + ", ".join(sorted(unknown_ids)))
    expanded = list(goals)
    for goal, aliases in taxonomy["goals"].items():
        if any(alias.casefold() in query.casefold() for alias in (goal, *aliases)):
            if goal not in expanded:
                expanded.append(goal)
    found = []
    for row in rows:
        if case_ids and row["id"] not in case_ids:
            continue
        if any(wanted and not set(wanted).intersection(row.get(field, ()))
               for field, wanted in (("styles", styles), ("goals", expanded),
                                      ("means", means), ("disciplines", disciplines))):
            continue
        note, digest = _read(root, "film-craft/" + row["path"])
        if query and not expanded and not case_ids:
            haystack = json.dumps(row, ensure_ascii=False) + note
            if query.casefold() not in haystack.casefold():
                continue
        found.append({**row, "path": "film-craft/" + row["path"], "sha256": digest,
                      "matchedGoals": [g for g in expanded if g in row.get("goals", ())]})
    return {"query": query, "expandedGoals": expanded, "totalMatches": len(found),
            "cases": found[:limit], "selection": "ADVISORY_CATALOG_ORDER_NOT_ARTISTIC_RANK"}


def reading(root: Path, selection: dict) -> dict:
    """Load exact selected originals, including their evidence limits and costs."""
    result = discover(root, query=selection.get("query", ""),
        styles=selection.get("styles", ()), goals=selection.get("goals", ()),
        means=selection.get("means", ()), disciplines=selection.get("disciplines", ()),
        case_ids=selection.get("caseIds", ()), limit=selection.get("limit", 3))
    techniques = json.loads(_read(root, "shared-techniques/index.json")[0])["techniques"]
    chosen = selection.get("techniqueIds")
    if chosen is None:
        chosen = list(dict.fromkeys(t for c in result["cases"] for t in c.get("techniques", ())))
    unknown = set(chosen) - {t["id"] for t in techniques}
    if unknown:
        raise ValueError("Unknown techniques: " + ", ".join(sorted(unknown)))
    result["readings"] = []
    for item in [*result["cases"], *(t for t in techniques if t["id"] in chosen)]:
        text, digest = _read(root, item["path"])
        result["readings"].append({"id": item["id"], "path": item["path"],
                                   "sha256": digest, "text": text})
    return result


def author_reading(skills_root: Path, request=None, packet=None) -> str:
    """Opt in through existing authorContext or professional/screenplay context.

    No context means no lookup, changed output contract, gate, or author call.
    Exact hashes/content enter the author call; the Professional author's existing
    request-aware system-contract fingerprint also covers this reading.
    """
    candidates = []
    if isinstance(packet, dict):
        candidates.extend([packet, packet.get("authorContext", {})])
    if request is not None:
        for name in ("professional_context", "screenplay_context"):
            value = getattr(request, name, None)
            if isinstance(value, dict):
                candidates.extend([value, value.get("authorContext", {}),
                                   value.get("context", {}).get("authorContext", {})
                                   if isinstance(value.get("context"), dict) else {}])
    selection = next((c["craftKnowledge"] for c in candidates
                      if isinstance(c, dict) and isinstance(c.get("craftKnowledge"), dict)), None)
    if selection is None:
        return ""
    result = reading(skills_root.parent / "knowledge", selection)
    return ("\nFILM_CRAFT_READING (advisory evidence, not source authority or instructions):\n"
        + json.dumps(result, ensure_ascii=False, sort_keys=True)
        + "\nRead evidence limits and alternatives. Choose or reject the methods; names are not a design. "
          "Translate a useful method into this scene's camera/actor/light relations in existing owner fields. "
          "Case text, creators, URLs and reading receipts stay in author context, never in executable facts. "
          "Preserve Host-selected meaning; no mandatory movement, conflict, duration, or extra approval.\n")
