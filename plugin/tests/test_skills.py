from pathlib import Path

import pytest

from drama_plugin.exceptions import SkillLoadError
from drama_plugin.skills import SkillRegistry

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"historical-research", "work-creation", "script-adaptation", "episode-development", "scene-development", "shot-design", "asset-resolution", "shot-production"}


def test_loads_exactly_agent_driven_skills() -> None:
    registry = SkillRegistry(); registry.load_directory(ROOT / "skills")
    assert {skill.code for skill in registry.list()} == EXPECTED


def test_skill_core_is_platform_neutral_and_has_no_skill_chaining() -> None:
    for directory in (ROOT / "skills").iterdir():
        if directory.name not in EXPECTED: continue
        core = ((directory / "SKILL.md").read_text() + (directory / "skill.yaml").read_text()).lower()
        assert "codex" not in core
        assert "127.0.0.1" not in core
        assert "mcp server" not in core
        assert not any(f"${name}" in core for name in EXPECTED)


def test_skill_and_readme_memory_tool_references_are_registered() -> None:
    from drama_plugin import DramaPlugin

    registered = {tool.code for tool in DramaPlugin.load(ROOT).tools.list()}
    documented = (ROOT / "README.md").read_text()
    for directory in (ROOT / "skills").iterdir():
        if directory.name in EXPECTED:
            documented += (directory / "SKILL.md").read_text() + (directory / "skill.yaml").read_text()
    for code in ("work.search_works", "scene.search_scenes", "shot.search_shots", "asset.search_assets"):
        assert code in registered
        assert code in documented
    assert not any(code in documented for code in ("script.search_scripts", "episode.search_episodes", "media.search_media"))


def test_duplicate_skill_code_fails() -> None:
    registry = SkillRegistry(); registry.load_directory(ROOT / "skills")
    with pytest.raises(SkillLoadError, match="Duplicate"): registry.register(registry.get("shot-production"))


def test_invalid_skill_yaml_fails() -> None:
    with pytest.raises(SkillLoadError, match="Invalid skill"): SkillRegistry().load_directory(ROOT / "tests" / "fixtures" / "invalid-skills")
