from pathlib import Path
import re

import pytest
import yaml

from drama_plugin import DramaPlugin
from drama_plugin.exceptions import SkillLoadError
from drama_plugin.skills import SkillRegistry

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"historical-research", "work-creation", "script-adaptation", "episode-development", "scene-development", "shot-design", "asset-resolution", "shot-production"}
CREATIVE = {
    "work-creation": ("work.create_work", "work.save_work", ("theme", "viewpoint", "central conflict", "timeline")),
    "script-adaptation": ("script.create_script", "script.save_script", ("main", "character arcs", "pacing", "climax")),
    "episode-development": ("episode.create_episode", "episode.save_episode", ("dramatic job", "opening hook", "information gain", "ending hook")),
    "scene-development": ("scene.create_scene", "scene.save_scene", ("dramatic purpose", "objective", "conflict", "entry/exit")),
    "shot-design": ("shot.create_shot", "shot.save_shot", ("dramatic function", "framing", "camera behavior", "continuity")),
}
LIFECYCLE = (
    "Understand Goal",
    "Gather Context",
    "Plan",
    "Execute Draft",
    "Review",
    "Revise or Re-plan",
    "Persist",
)
PROFESSIONAL_REFERENCES = {
    "work-creation": ("planning.md", "review.md"),
    "script-adaptation": ("planning.md", "review.md"),
}


def lifecycle_sections(instructions: str) -> dict[str, str]:
    matches = list(re.finditer(r"^### \d+\. (.+)$", instructions, flags=re.MULTILINE))
    return {
        match.group(1): instructions[match.end() : matches[index + 1].start() if index + 1 < len(matches) else len(instructions)]
        for index, match in enumerate(matches)
    }


def reference_text(skill_code: str, filename: str) -> str:
    return (ROOT / "skills" / skill_code / "references" / filename).read_text(encoding="utf-8")


def assert_concept_groups(text: str, groups: tuple[tuple[str, ...], ...]) -> None:
    lowered = text.lower()
    assert all(any(term.lower() in lowered for term in alternatives) for alternatives in groups)


def test_loads_exactly_agent_driven_skills() -> None:
    registry = SkillRegistry(); registry.load_directory(ROOT / "skills")
    assert {skill.code for skill in registry.list()} == EXPECTED


def test_skill_core_is_platform_neutral_and_has_no_skill_chaining() -> None:
    forbidden = (
        "codex",
        "mcp server",
        "localhost",
        "127.0.0.1",
        "fastapi",
        "spring boot",
        "java service",
        "comfyui",
        "openai agents sdk",
        "mcpserverstreamablehttp",
    )
    for directory in (ROOT / "skills").iterdir():
        if directory.name not in EXPECTED: continue
        core = ((directory / "SKILL.md").read_text(encoding="utf-8") + (directory / "skill.yaml").read_text(encoding="utf-8")).lower()
        references = directory / "references"
        if references.exists():
            core += "".join(path.read_text(encoding="utf-8").lower() for path in references.glob("*.md"))
        assert not any(term in core for term in forbidden)
        assert not any(f"${name}" in core for name in EXPECTED)


def test_every_declared_logical_tool_is_explicit_in_skill_instructions() -> None:
    registry = SkillRegistry(); registry.load_directory(ROOT / "skills")
    for skill in registry.list():
        references = {*skill.tools.preferred, *skill.tools.allowed}
        assert references
        assert all(code in skill.instructions for code in references)
        assert set(skill.tools.preferred).isdisjoint(skill.tools.allowed)


def test_create_is_first_write_and_save_is_revision_only() -> None:
    persistent_tools = {
        "work-creation": ("work.create_work", "work.save_work"),
        "script-adaptation": ("script.create_script", "script.save_script"),
        "episode-development": ("episode.create_episode", "episode.save_episode"),
        "scene-development": ("scene.create_scene", "scene.save_scene"),
        "shot-design": ("shot.create_shot", "shot.save_shot"),
        "asset-resolution": ("asset.create_asset", "asset.save_asset"),
    }
    registry = SkillRegistry(); registry.load_directory(ROOT / "skills")
    for skill_code, (create_tool, save_tool) in persistent_tools.items():
        skill = registry.get(skill_code)
        instructions = skill.instructions
        assert create_tool in skill.tools.preferred
        assert save_tool in skill.tools.preferred
        assert "complete initial formal state" in instructions
        assert "successful create is the normal first write" in instructions.lower()
        assert f"do not call `{save_tool}` immediately afterward" in instructions.lower()
        assert "unless a concrete revision has actually occurred" in instructions.lower()
        assert "only to revise an already persisted" in instructions
        assert "Stable Envelope" in instructions
        assert "Domain Content" in instructions
        assert "Tool catalog" in instructions
        assert "full replacement" in instructions


def test_core_creative_skills_have_ordered_lifecycle_and_domain_review() -> None:
    registry = SkillRegistry(); registry.load_directory(ROOT / "skills")
    review_bodies: set[str] = set()
    for skill_code, (_, _, review_terms) in CREATIVE.items():
        instructions = registry.get(skill_code).instructions
        sections = lifecycle_sections(instructions)
        assert tuple(sections) == LIFECYCLE
        gather = sections["Gather Context"]
        assert "context sufficiency" in gather.lower()
        assert "state the blocker" in gather
        assert "do not draft or persist" in gather.lower()
        review = sections["Review"]
        assert "Critical checks" in review
        assert "Review PASS" in review and "Review FAIL" in review
        assert all(term in review.lower() for term in review_terms)
        review_bodies.add(review)
    assert len(review_bodies) == len(CREATIVE)


def test_creative_lifecycle_blocks_writes_until_review_pass() -> None:
    registry = SkillRegistry(); registry.load_directory(ROOT / "skills")
    for skill_code, (create_tool, save_tool, _) in CREATIVE.items():
        sections = lifecycle_sections(registry.get(skill_code).instructions)
        plan = sections["Plan"]
        assert "internal" in plan.lower() and "Agent Run Context" in plan
        assert create_tool in plan and save_tool in plan and "Do not call" in plan
        draft = sections["Execute Draft"]
        assert "complete candidate formal" in draft
        assert "Do not persist" in draft
        revise = sections["Revise or Re-plan"]
        assert "On Review FAIL, do not persist" in revise
        assert "Locally revise" in revise and "Re-plan" in revise
        assert "Review Again and PASS" in revise
        persist = sections["Persist"]
        assert "No Review PASS means no create or save" in persist
        assert create_tool in persist and save_tool in persist
        assert all(term in persist for term in ("required context", "plan", "complete draft", "critical checks"))


def test_creative_working_state_is_not_persisted_as_domain_content() -> None:
    registry = SkillRegistry(); registry.load_directory(ROOT / "skills")
    for skill_code in CREATIVE:
        persist = lifecycle_sections(registry.get(skill_code).instructions)["Persist"]
        assert all(term in persist for term in ("draft reasoning", "review notes", "revision notes"))
        assert "Agent Run Context or temporary working state" in persist
        assert "do not put them in" in persist
        assert "Persist only" in persist and "reviewed formal" in persist


def test_creative_research_decision_blocks_unresolved_evidence() -> None:
    registry = SkillRegistry(); registry.load_directory(ROOT / "skills")
    for skill_code in CREATIVE:
        gather = lifecycle_sections(registry.get(skill_code).instructions)["Gather Context"]
        assert "consequential" in gather
        assert "focused research question" in gather or "focused question" in gather
        assert "stop before planning or persistence" in gather


def test_creative_completion_conditions_include_lifecycle_gate() -> None:
    registry = SkillRegistry(); registry.load_directory(ROOT / "skills")
    for skill_code in CREATIVE:
        conditions = registry.get(skill_code).completion.conditions
        assert len(conditions) == 3
        gate = conditions[-1].lower()
        assert all(term in gate for term in ("persistence", "sufficient context", "plan", "draft", "passing", "review"))


def test_work_and_script_references_are_minimal_discoverable_and_stage_routed() -> None:
    registry = SkillRegistry(); registry.load_directory(ROOT / "skills")
    for skill_code, expected_files in PROFESSIONAL_REFERENCES.items():
        directory = ROOT / "skills" / skill_code / "references"
        assert tuple(sorted(path.name for path in directory.glob("*.md"))) == expected_files
        sections = lifecycle_sections(registry.get(skill_code).instructions)
        planning_link = "references/planning.md"
        review_link = "references/review.md"
        assert planning_link in sections["Plan"] and review_link not in sections["Plan"]
        assert review_link in sections["Review"] and planning_link not in sections["Review"]
        assert len(reference_text(skill_code, "planning.md").splitlines()) < 120
        assert len(reference_text(skill_code, "review.md").splitlines()) < 100


def test_work_professional_method_covers_story_design_and_quality_gate() -> None:
    planning = reference_text("work-creation", "planning.md")
    review = reference_text("work-creation", "review.md")
    assert_concept_groups(
        planning,
        (
            ("Convert event into story", "story engine"),
            ("external goal", "active goal"),
            ("internal need", "blind spot"),
            ("opposition", "capacity to act"),
            ("escalating stakes", "higher cost"),
            ("premise", "logline"),
            ("dramatic question", "theme"),
            ("relationship", "final state"),
            ("irreversible choice", "irreversible decision"),
            ("documented", "dramatic invention space"),
            ("short-drama scale", "short-form suitability"),
        ),
    )
    assert planning.count("→") >= 5
    assert "briefly compare more than one viable option" in planning
    assert review.count("| PASS evidence | FAIL signal |") == 1
    rubric_rows = [line for line in review.splitlines() if line.startswith("| ") and "---" not in line]
    assert len(rubric_rows) >= 14
    assert_concept_groups(
        review,
        (
            ("Story identity", "Historical Summary"),
            ("Protagonist", "Passive Protagonist"),
            ("Opposition", "Villain Flattening"),
            ("Dramatic causality", "Chronology Dump"),
            ("Character arc", "Relationship arc"),
            ("Historical integrity", "Historical Drift"),
            ("Downstream readiness", "formal story foundation"),
            ("Re-plan the Work", "Rewrite the full draft"),
        ),
    )
    persist = lifecycle_sections((ROOT / "skills/work-creation/SKILL.md").read_text(encoding="utf-8"))["Persist"]
    assert_concept_groups(persist, (("event summary", "character list"), ("passive protagonist",), ("climax and ending",)))


def test_script_professional_method_covers_adaptation_and_screenability_gate() -> None:
    planning = reference_text("script-adaptation", "planning.md")
    review = reference_text("script-adaptation", "review.md")
    assert_concept_groups(
        planning,
        (
            ("adaptation contract", "must inherit"),
            ("main dramatic line", "causal progression"),
            ("secondary lines", "serve"),
            ("observable progression", "visible evidence"),
            ("information reveal", "what the audience"),
            ("higher cost", "narrowing options"),
            ("episode architecture", "dramatic job"),
            ("short-form pacing", "Enter pressure early"),
            ("screenable", "observable or audible"),
            ("dialogue", "subtext"),
        ),
    )
    assert planning.count("→") >= 4
    assert "without creating Episode entities" in planning
    assert_concept_groups(
        review,
        (
            ("Work fidelity", "upstream Work issue"),
            ("Main line", "Event List"),
            ("Conflict escalation", "Flat Escalation"),
            ("Information reveal", "Exposition Dialogue"),
            ("Episode architecture", "Mechanical Episode Split"),
            ("Screenability", "Unfilmable Interior Prose"),
            ("Climax and payoff", "Ending fidelity"),
            ("Re-plan the Script", "Rewrite the full draft"),
        ),
    )
    persist = lifecycle_sections((ROOT / "skills/script-adaptation/SKILL.md").read_text(encoding="utf-8"))["Persist"]
    assert_concept_groups(persist, (("plot summary", "event list"), ("episode architecture",), ("unfilmable prose",), ("Work drift",)))


def test_creative_quality_fixtures_cover_distinct_topics_without_claiming_llm_pass() -> None:
    fixture = yaml.safe_load((ROOT / "tests/fixtures/creative-quality/work-script-evaluations.yaml").read_text(encoding="utf-8"))
    cases = fixture["cases"]
    assert fixture["version"] == 1
    assert {case["mode"] for case in cases} == {"political_event", "relationship_driven"}
    assert len(cases) == 2
    for case in cases:
        assert len(case["work_expected_dimensions"]) >= 6
        assert len(case["script_expected_dimensions"]) >= 6
        assert len(case["work_failure_examples"]) >= 2
        assert len(case["script_failure_examples"]) >= 2
        assert "Review-PASS Work artifact" in case["script_prerequisite"]
    assert len(fixture["manual_run_checklist"]) >= 6
    serialized = yaml.safe_dump(fixture, allow_unicode=True).lower()
    assert "real llm result" in serialized and "does not claim" in serialized
    production_text = "".join(
        (ROOT / "skills" / skill / relative).read_text(encoding="utf-8")
        for skill in PROFESSIONAL_REFERENCES
        for relative in ("SKILL.md", "references/planning.md", "references/review.md")
    )
    assert all(topic not in production_text for topic in ("神龙政变", "唐太宗", "魏征"))


def test_media_registration_is_not_duplicated_after_generation() -> None:
    registry = SkillRegistry(); registry.load_directory(ROOT / "skills")
    asset_resolution = registry.get("asset-resolution")
    assert "media.create_media" in asset_resolution.tools.allowed
    assert "never register an already stable `mediaId` again" in asset_resolution.instructions
    assert "media.save_media" not in asset_resolution.instructions


def test_openai_adapters_are_optional_interface_metadata_only() -> None:
    for directory in (ROOT / "skills").iterdir():
        if directory.name not in EXPECTED: continue
        adapter = yaml.safe_load((directory / "agents" / "openai.yaml").read_text(encoding="utf-8"))
        assert set(adapter) == {"interface"}
        assert set(adapter["interface"]) == {"display_name", "short_description", "default_prompt"}


def test_skill_and_readme_memory_tool_references_are_registered() -> None:
    registered = {tool.code for tool in DramaPlugin.load(ROOT).tools.list()}
    documented = (ROOT / "README.md").read_text(encoding="utf-8")
    for directory in (ROOT / "skills").iterdir():
        if directory.name in EXPECTED:
            documented += (directory / "SKILL.md").read_text(encoding="utf-8") + (directory / "skill.yaml").read_text(encoding="utf-8")
    for code in ("work.search_works", "scene.search_scenes", "shot.search_shots", "asset.search_assets"):
        assert code in registered
        assert code in documented
    assert not any(code in documented for code in ("script.search_scripts", "episode.search_episodes", "media.search_media"))


def test_duplicate_skill_code_fails() -> None:
    registry = SkillRegistry(); registry.load_directory(ROOT / "skills")
    with pytest.raises(SkillLoadError, match="Duplicate"): registry.register(registry.get("shot-production"))


def test_invalid_skill_yaml_fails() -> None:
    with pytest.raises(SkillLoadError, match="Invalid skill"): SkillRegistry().load_directory(ROOT / "tests" / "fixtures" / "invalid-skills")
