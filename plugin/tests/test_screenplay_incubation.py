"""Ledger integrity and compatibility; these tests do not score creative quality."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from typing import Any

import pytest

from drama_plugin import DramaPlugin

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/cinematic-screenplay-incubation"
spec = importlib.util.spec_from_file_location("incubation_checker", SKILL / "scripts/check_incubation.py")
assert spec and spec.loader
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def ledger() -> dict[str, Any]:
    claim = dict.fromkeys(("actor", "time", "location", "cause", "motivation", "knownInformation",
                           "constraint", "decision", "consequence"), "explicit fixture fact")
    claim.update(id="event", certainty="Confirmed", evidence=["source"])
    scene = {"id": "s1", "owner": "speaker:one", "inputState": {"place": "gate"},
             "outputState": {"place": "gate"}, "knowledgeIn": {"speaker:one": []},
             "receipts": [{"speaker": "speaker:one", "information": "order", "beforeBeat": 2, "channel": "courier"}],
             "decisions": [{"speaker": "speaker:one", "beat": 3, "uses": ["order"]}]}
    return {"historicalGrounding": {"sources": {"source": "fixture"}, "claims": [claim]},
            "characters": {"speaker:one": {}}, "sequence": [scene],
            "ledger": {"initialState": {"place": "gate"}, "initialKnowledge": {"speaker:one": []}},
            "review": {"findings": [], "rounds": [], "freeze": {"status": "FROZEN", "revision": "draft-1"}}}


def test_real_registry_discovers_incubation_without_changing_tool_surface() -> None:
    plugin = DramaPlugin.load(ROOT)
    skill = plugin.skills.get("cinematic-screenplay-incubation")
    assert len(plugin.tools.list()) == 50
    assert skill.context.refresh_after == []
    assert not any("create" in code or "save" in code or "generate" in code for code in [*skill.tools.preferred, *skill.tools.allowed])
    assert {"work-creation", "script-adaptation", "scene-development"} <= {item.code for item in plugin.skills.list()}


def test_recorded_receipt_before_decision_is_valid() -> None:
    assert checker.check(ledger()) == []


def test_later_receipt_cannot_authorize_earlier_decision() -> None:
    data = ledger()
    data["sequence"][0]["decisions"][0]["beat"] = 1
    assert any("unavailable information" in error for error in checker.check(data))


def test_next_scene_must_inherit_knowledge_and_state() -> None:
    data = ledger()
    second = deepcopy(data["sequence"][0])
    second.update(id="s2", receipts=[], decisions=[], inputState={"place": "court"})
    data["sequence"].append(second)
    errors = checker.check(data)
    assert any("CONTINUITY" in error for error in errors)
    assert any("incoming information" in error for error in errors)
    second["knowledgeIn"] = {"speaker:one": ["order"]}
    second["entryChanges"] = [{"key": "place", "value": "court", "reason": "several days of travel"}]
    assert checker.check(data) == []


@pytest.mark.parametrize("mutation, expected", [
    ({"evidence": ["missing"]}, "dangling evidence"),
    ({"causeIds": ["event"]}, "cause must precede"),
    ({"certainty": "Disputed"}, "alternatives and position"),
    ({"certainty": "Certain"}, "invalid certainty"),
])
def test_evidence_and_causal_integrity(mutation: dict[str, Any], expected: str) -> None:
    data = ledger()
    data["historicalGrounding"]["claims"][0].update(mutation)
    assert any(expected in error for error in checker.check(data))


def revision_ledger() -> dict[str, Any]:
    data = ledger()
    data["review"]["findings"] = [{"id": "f1", "problem": "shared facts explained to informed listener",
        "severity": "MAJOR", "layer": "SUBTEXT", "evidence": "s1 line 4", "recommendedRevisionScope": ["s1"], "resolved": True}]
    data["review"]["rounds"] = [{"number": 1, "findingIds": ["f1"], "changedScopes": ["s1"],
        "before": {"s1": "before", "s2": "unchanged"}, "after": {"s1": "after", "s2": "unchanged"}}]
    return data


def test_targeted_revision_preserves_unaffected_scope() -> None:
    data = revision_ledger()
    assert checker.check(data) == []
    data["review"]["rounds"][0]["after"]["s2"] = "silently rewritten"
    errors = checker.check(data)
    assert any("declared scope" in error for error in errors)
    assert any("outside findings" in error for error in errors)


def test_round_budget_and_false_freeze_are_blocked() -> None:
    data = revision_ledger()
    data["review"]["rounds"] *= 3
    data["review"]["findings"][0]["resolved"] = False
    errors = checker.check(data)
    assert any("two corrective rounds" in error for error in errors)
    assert any("unresolved severe" in error for error in errors)


def test_payoff_cannot_precede_setup_or_claim_nonexistent_payoff() -> None:
    data = ledger()
    data["ledger"]["foreshadow"] = [{"id": "prop", "setupScene": "s1", "status": "PAID"}]
    assert any("paid without payoff" in error for error in checker.check(data))


def test_skill_reference_links_resolve() -> None:
    import re
    for path in [SKILL / "SKILL.md", *SKILL.glob("references/*.md")]:
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            assert (path.parent / target).exists(), (path, target)
