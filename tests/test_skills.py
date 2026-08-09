from pathlib import Path

import pytest

from drama_plugin.exceptions import SkillLoadError
from drama_plugin.skills import SkillRegistry


ROOT = Path(__file__).resolve().parents[1]


def test_loads_all_skills() -> None:
    registry = SkillRegistry()
    registry.load_directory(ROOT / "skills")
    assert {skill.code for skill in registry.list()} == {
        "historical-research", "story-skeleton", "episode-writing", "scene-breakdown",
        "visual-asset-planning", "storyboard", "shot-generation", "continuity-review",
    }


def test_duplicate_skill_code_fails() -> None:
    registry = SkillRegistry()
    registry.load_directory(ROOT / "skills")
    with pytest.raises(SkillLoadError, match="Duplicate"):
        registry.register(registry.get("shot-generation"))


def test_invalid_skill_yaml_fails() -> None:
    with pytest.raises(SkillLoadError, match="Invalid skill"):
        SkillRegistry().load_directory(ROOT / "tests" / "fixtures" / "invalid-skills")
