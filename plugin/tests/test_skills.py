from pathlib import Path
import re

import pytest
import yaml

from drama_plugin import DramaPlugin
from drama_plugin.exceptions import SkillLoadError
from drama_plugin.skills import SkillRegistry

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"historical-research", "work-creation", "script-adaptation", "episode-development", "scene-development", "dramatic-performance-direction", "shot-design", "asset-resolution", "shot-production", "audio-production"}
CREATIVE = {
    "work-creation": ("work.create_work", "work.save_work", ("historical_spine_complete", "fact_attribution_valid", "protagonist_scope_alignment", "structure_covers_spine")),
    "script-adaptation": ("script.create_script", "script.save_script", ("historical spine", "fact attribution", "episode architecture", "climax")),
    "episode-development": ("episode.create_episode", "episode.save_episode", ("historical beat coverage", "narrative input", "required transition", "neighbor continuity")),
    "scene-development": ("scene.create_scene", "scene.save_scene", ("historical beat coverage", "narrative input", "scene_state_continuity", "causal_narrative_continuity")),
    "shot-design": ("shot.create_shot", "shot.save_shot", ("character_visual_continuity", "shot_action_continuity", "causal_narrative_continuity", "historical_beat_coverage")),
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
    "episode-development": ("planning.md", "review.md"),
    "scene-development": ("planning.md", "review.md"),
    "shot-design": ("planning.md", "review.md"),
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


def test_professional_references_are_minimal_discoverable_and_stage_routed() -> None:
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


def test_work_professional_method_covers_historical_story_design_and_quality_gate() -> None:
    planning = reference_text("work-creation", "planning.md")
    review = reference_text("work-creation", "review.md")
    assert_concept_groups(
        planning,
        (
            ("Historical Scope", "historicalScope"),
            ("Historical Spine", "historicalSpine"),
            ("actor hierarchy", "Narrative Authority"),
            ("Viewpoint can move downward",),
            ("actor granularity",),
            ("premise", "logline"),
            ("dramatic question", "theme"),
            ("internalNeed", "interpretive"),
            ("Dramatization Deletion Test",),
            ("documented", "dramatic invention space"),
            ("Coverage First", "structureEstimate"),
        ),
    )
    assert planning.count("→") >= 5
    assert "Compare viable protagonist/viewpoint options only within these constraints" in planning
    assert review.count("| PASS evidence | FAIL signal |") == 1
    rubric_rows = [line for line in review.splitlines() if line.startswith("| ") and "---" not in line]
    assert len(rubric_rows) >= 14
    assert_concept_groups(
        review,
        (
            ("Historical Scope", "Historical Spine"),
            ("Fact attribution", "actor granularity"),
            ("Protagonist/scope alignment", "Interesting Supporting Hero"),
            ("Causal promotion", "UNSUPPORTED_CAUSAL_PROMOTION"),
            ("Dramatization deletion", "FAIL_UNSUPPORTED_CAUSAL_EVENT"),
            ("Historical integrity", "Historical Drift"),
            ("Downstream readiness", "formal historical story foundation"),
            ("Re-plan the Work", "Rewrite the full draft"),
        ),
    )
    persist = lifecycle_sections((ROOT / "skills/work-creation/SKILL.md").read_text(encoding="utf-8"))["Persist"]
    assert_concept_groups(persist, (("event summary", "character list"), ("unsupported actor attribution",), ("protagonist/scope mismatch",), ("climax and ending",)))


def test_historical_narrative_hardening_generic_cases_and_gates() -> None:
    fixture = yaml.safe_load(
        (ROOT / "tests/fixtures/creative-quality/historical-narrative-hardening.yaml").read_text(encoding="utf-8")
    )
    assert fixture["version"] == 1
    by_id = {case["id"]: case for case in fixture["cases"]}
    assert set(by_id) == {
        "actor_attribution",
        "protagonist_scope_alignment",
        "scope_narrowing",
        "dramatization_deletion",
        "structure_coverage",
    }
    assert by_id["actor_attribution"]["expected"] == "FAIL"
    assert by_id["protagonist_scope_alignment"]["expected"] == "FAIL"
    assert by_id["scope_narrowing"]["expected"] == "PASS"
    assert by_id["scope_narrowing"]["primaryCausalityReassigned"] is False
    assert by_id["dramatization_deletion"]["spineAfterDeletionIntact"] is True
    assert by_id["structure_coverage"]["expected"] == "FAIL"

    work = (ROOT / "skills/work-creation/SKILL.md").read_text(encoding="utf-8")
    work_review = reference_text("work-creation", "review.md")
    for gate in (
        "HISTORICAL_SPINE_COMPLETE",
        "FACT_ATTRIBUTION_VALID",
        "PROTAGONIST_SCOPE_ALIGNMENT",
        "UNSUPPORTED_CAUSAL_PROMOTION_ABSENT",
        "DRAMATIZATION_NON_CAUSAL",
        "STORY_ARCHITECTURE_SPINE_ALIGNED",
        "STRUCTURE_COVERS_SPINE",
    ):
        assert gate in work and gate in work_review
    assert "FAIL_UNSUPPORTED_CAUSAL_EVENT" in work_review
    assert "Historical Spine → Required Story Beats" in work


def test_scene_and_shot_reviews_separate_narrative_from_visual_continuity() -> None:
    scene = reference_text("scene-development", "review.md")
    shot = reference_text("shot-design", "review.md")
    assert "FAIL_NARRATIVE_TRANSITION" in scene and "FAIL_NARRATIVE_TRANSITION" in shot
    assert "Previous Narrative Output State → Current Narrative Input State" in scene
    for gate in (
        "CHARACTER_VISUAL_CONTINUITY",
        "COSTUME_PERIOD_CONTINUITY",
        "PROP_STATE_CONTINUITY",
        "SHOT_ACTION_CONTINUITY",
        "SCENE_STATE_CONTINUITY",
        "CAUSAL_NARRATIVE_CONTINUITY",
        "HISTORICAL_BEAT_COVERAGE",
        "FULL_STORY_ARC",
    ):
        assert gate in shot


def test_historical_skill_core_has_no_event_specific_business_rules() -> None:
    core = "".join(
        path.read_text(encoding="utf-8")
        for code in ("historical-research", "work-creation", "script-adaptation", "episode-development", "scene-development", "shot-design")
        for path in (ROOT / "skills" / code).rglob("*")
        if path.is_file() and path.suffix in {".md", ".yaml"}
    )
    forbidden = ("潼关", "安史之乱", "哥舒翰", "王思礼", "崔乾祐", "安禄山")
    assert not any(name in core for name in forbidden)


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


def test_episode_professional_method_covers_job_state_turn_and_necessity() -> None:
    planning = reference_text("episode-development", "planning.md")
    review = reference_text("episode-development", "review.md")
    assert_concept_groups(
        planning,
        (
            ("Inherit the series contract", "Script main line"),
            ("one dramatic job", "pressure forces"),
            ("entry and exit state", "material change"),
            ("objective", "obstacle"),
            ("tactic", "counteraction"),
            ("meaningful turn", "changes what characters can do"),
            ("Earn the ending", "produced by the Episode"),
            ("Delete Episode Test", "series would lose"),
            ("short-form", "early pressure"),
            ("Scene development", "without detailed Scene"),
        ),
    )
    assert planning.count("→") >= 6
    rubric_rows = [line for line in review.splitlines() if line.startswith("| ") and "---" not in line]
    assert len(rubric_rows) >= 15
    assert_concept_groups(
        review,
        (
            ("Dramatic job", "Mechanical Split"),
            ("Script fidelity", "upstream Script issue"),
            ("Narrative input state", "Narrative output state"),
            ("Progression and escalation", "Repeated Conflict"),
            ("Turn", "Ending logic"),
            ("Episode necessity", "Delete"),
            ("Downstream readiness", "detailed Scenes"),
            ("Re-plan", "full rubric again"),
        ),
    )
    instructions = (ROOT / "skills/episode-development/SKILL.md").read_text(encoding="utf-8")
    persist = lifecycle_sections(instructions)["Persist"]
    assert_concept_groups(persist, (("mechanical split", "plot summary"), ("dramatic job", "central conflict"), ("turn", "exit-state change"), ("necessity",)))
    assert "upstream Script issue" in instructions and "Do not write detailed Scenes" in instructions


def test_scene_professional_method_covers_conflict_in_action_and_state_change() -> None:
    planning = reference_text("scene-development", "planning.md")
    review = reference_text("scene-development", "review.md")
    assert_concept_groups(
        planning,
        (
            ("Inherit the Episode contract", "Episode dramatic job"),
            ("change-based purpose", "must exist"),
            ("playable objective", "immediate, specific result"),
            ("active opposition", "materially blocks"),
            ("immediate stakes", "failure must matter"),
            ("tactics and beats", "behavior changes"),
            ("conflict-in-action", "action, resistance, and consequence"),
            ("subtext", "spoken meaning"),
            ("playable", "Externalize"),
            ("turn", "cannot simply return"),
            ("Delete Scene Test", "Episode would lose"),
        ),
    )
    assert planning.count("→") >= 3
    rubric_rows = [line for line in review.splitlines() if line.startswith("| ") and "---" not in line]
    assert len(rubric_rows) >= 17
    assert_concept_groups(
        review,
        (
            ("Episode fidelity", "upstream Episode issue"),
            ("Character objective", "Opposing force"),
            ("Tactics and beats", "Conflict-in-action"),
            ("Dialogue/subtext", "Playable action"),
            ("Before/After Gate", "Meaningful state change"),
            ("Delete Scene Test", "Scene necessity"),
            ("Talking Heads", "Interior Summary"),
            ("Re-plan", "both gates again"),
        ),
    )
    instructions = (ROOT / "skills/scene-development/SKILL.md").read_text(encoding="utf-8")
    persist = lifecycle_sections(instructions)["Persist"]
    assert_concept_groups(persist, (("pure exposition", "Characters-plus-location"), ("objective/opposition/turn/state change",), ("removable Scene",)))
    assert "upstream Episode issue" in instructions and "Do not specify framing" in instructions


def test_shot_professional_method_covers_strategy_continuity_feasibility_and_economy() -> None:
    planning = reference_text("shot-design", "planning.md")
    review = reference_text("shot-design", "review.md")
    assert_concept_groups(
        planning,
        (
            ("Inherit the Scene contract", "approved Scene"),
            ("coverage strategy", "camera must primarily express"),
            ("narrative purpose", "Delete or merge"),
            ("subject, action, and blocking", "spatial behavior"),
            ("framing and camera", "information, performance"),
            ("dialogue coverage and rhythm", "listener"),
            ("180-degree axis", "screen direction", "eyeline"),
            ("action and performance continuity", "entry action"),
            ("visual and temporal references", "costume", "time of day"),
            ("generation feasibility", "split, simplified"),
            ("provider-agnostic", "downstream production"),
            ("smallest coherent set", "minimal complete coverage"),
        ),
    )
    rubric_rows = [line for line in review.splitlines() if line.startswith("| ") and "---" not in line]
    assert len(rubric_rows) >= 16
    assert_concept_groups(
        review,
        (
            ("Scene fidelity", "upstream Scene issue"),
            ("Coverage strategy", "One-Line-One-Shot"),
            ("Narrative purpose", "Coverage Explosion"),
            ("Spatial continuity", "axis", "eyeline"),
            ("Action continuity", "Performance continuity"),
            ("Asset/costume/prop continuity", "Temporal continuity"),
            ("Generation feasibility", "Unproducible Shot"),
            ("Coverage economy", "minimal yet sufficient"),
            ("Downstream production readiness", "provider-agnostic"),
            ("Re-plan the Shot group", "full group rubric again"),
        ),
    )
    instructions = (ROOT / "skills/shot-design/SKILL.md").read_text(encoding="utf-8")
    persist = lifecycle_sections(instructions)["Persist"]
    assert_concept_groups(persist, (("minimal necessary", "narratively motivated"), ("continuous", "production-ready"), ("One-line-one-shot", "repeated coverage"), ("unproducible complexity",)))
    assert "upstream Scene issue" in instructions and "do not create or resolve assets" in instructions


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
        assert len(case["episode_expected_dimensions"]) >= 6
        assert len(case["scene_expected_dimensions"]) >= 7
        assert len(case["shot_expected_dimensions"]) >= 7
        assert len(case["episode_failure_examples"]) >= 2
        assert len(case["scene_failure_examples"]) >= 2
        assert len(case["shot_failure_examples"]) >= 2
        assert "Review-PASS Script artifact" in case["episode_prerequisite"]
        assert "Review-PASS Episode artifact" in case["scene_prerequisite"]
        assert "Review-PASS Scene artifact" in case["shot_prerequisite"]
    assert len(fixture["manual_run_checklist"]) >= 8
    purpose = fixture["purpose"].lower()
    assert "real llm result" in purpose and "does not claim" in purpose
    serialized = yaml.safe_dump(fixture, allow_unicode=True).lower()
    assert_concept_groups(
        serialized,
        (
            ("one_dramatic_job", "material_entry_exit_change"),
            ("playable_objective_and_opposition", "tactic_and_beat_progression"),
            ("conflict_in_action", "delete_scene_necessity"),
            ("coherent_coverage_strategy", "narrative_purpose_per_shot"),
            ("reaction_coverage", "generation_feasibility", "coverage_economy"),
        ),
    )
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
        assert set(adapter) == ({"interface", "dependencies"} if directory.name == "shot-production" else {"interface"})
        assert set(adapter["interface"]) == {"display_name", "short_description", "default_prompt"}
        if directory.name == "shot-production":
            assert adapter["dependencies"] == {
                "tools": [
                    {
                        "type": "mcp",
                        "value": "comfy-cloud",
                        "description": "Optional Host-provided visual production capability used only for image or video execution",
                        "transport": "streamable_http",
                        "url": "https://cloud.comfy.org/mcp",
                    }
                ]
            }


def test_shot_production_has_minimal_conditional_visual_provider_contract() -> None:
    instructions = (ROOT / "skills/shot-production/SKILL.md").read_text(encoding="utf-8")
    capability = reference_text("shot-production", "visual-provider.md")
    production_rules = reference_text("shot-production", "production-rules.md")
    host_mapping = (ROOT / "docs/visual-provider-host-integration.md").read_text(encoding="utf-8")

    assert "references/visual-provider.md" in instructions
    assert "references/production-rules.md" in instructions
    assert all(
        code in instructions
        for code in (
            "DRAMA_PROVIDER_UNAVAILABLE",
            "VISUAL_PROVIDER_UNAVAILABLE",
            "VISUAL_PROVIDER_CAPABILITY_MISSING",
            "media.resolve_media",
            "media.import_media",
        )
    )
    assert all(
        name in capability
        for name in (
            "visual.template.discover",
            "visual.input.upload",
            "visual.image.generate",
            "visual.job.wait",
            "visual.output.fetch",
            "referenceCount ∈ {0, 1, 2, 3}",
            "at most one minimal revision",
        )
    )
    assert "runtime provider owns the executable tool schemas" in capability
    assert "Context reads, non-visual planning, research, and creative development remain independent" in capability
    assert all(
        rule in production_rules
        for rule in (
            "MAX_REFERENCE_COUNT = 3",
            "MISSING_STABLE_REFERENCE",
            "Required Visual Evidence",
            "Forbidden Visual Outcome",
            "SEQUENCE_CONTINUITY_REQUIRES_REPLAN",
            "Visual Content Review PASS",
            "Identity Annotation",
        )
    )
    assert all(
        name in host_mapping
        for name in (
            "search_templates",
            "upload_file",
            "run_template",
            "wait_for_job",
            "get_output",
            "image_qwen_image_edit_2511",
            "api_bfl_flux2_max_sofa_swap",
        )
    )
    assert not any(path.name in {"comfy-tools.yaml", "comfy-tool-contract.json", "comfy-mcp-schema.json"} for path in ROOT.rglob("*"))


def test_visual_provider_retry_policy_is_single_source_and_shared_by_consumers() -> None:
    capability = reference_text("shot-production", "visual-provider.md")
    shot = (ROOT / "skills/shot-production/SKILL.md").read_text(encoding="utf-8")
    asset = (ROOT / "skills/asset-resolution/SKILL.md").read_text(encoding="utf-8")

    assert "MAX_TECHNICAL_RETRIES = 2" in capability
    assert "MAX_TOTAL_ATTEMPTS = 3" in capability
    assert "technicalRetryCount" in capability and "generationCount" in capability
    assert "PROVIDER_SUBMISSION_OUTCOME_UNKNOWN" in capability
    assert "VISUAL_PROVIDER_TEMPORARILY_UNAVAILABLE" in capability
    assert "same `jobId`" in capability
    assert "PROVIDER_AUTH_REQUIRED" in capability
    assert "references/visual-provider.md" in shot
    assert "../shot-production/references/visual-provider.md" in asset
    assert "Do not duplicate or weaken that policy here" in asset
    assert "MAX_TECHNICAL_RETRIES" not in asset


def test_shot_production_video_contract_covers_motion_review_and_idempotency() -> None:
    capability = (ROOT / "skills/shot-production/references/visual-provider.md").read_text(encoding="utf-8")
    for phrase in (
        "exactly one stable source Media",
        "exactly one `start_frame_media_id` and one `end_frame_media_id`",
        "same Shot/video target",
        "2,000 characters",
        "representative frames across the clip",
        "technical retry never does",
    ):
        assert phrase in capability


def test_visual_provider_retry_policy_fixture_covers_nine_required_decisions() -> None:
    fixture = yaml.safe_load((ROOT / "tests/fixtures/visual-provider-retry-policy.yaml").read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in fixture["cases"]}

    assert fixture["max_technical_retries"] == 2
    assert fixture["max_total_attempts"] == 3
    assert len(cases) == 9
    assert cases["initialize_transient_then_pass"]["expected"] == {
        "result": "CONTINUE", "technical_retry_count": 1, "generation_count": 0,
    }
    assert cases["initialize_retry_exhausted"]["expected"]["result"] == "VISUAL_PROVIDER_TEMPORARILY_UNAVAILABLE"
    assert cases["initialize_retry_exhausted"]["expected"]["total_attempts"] == 3
    assert cases["status_same_job"]["expected"]["reused_job_id"] == cases["status_same_job"]["job_id"]
    assert cases["status_same_job"]["expected"]["new_generation_submit"] is False
    assert cases["output_same_job"]["expected"]["reused_job_id"] == cases["output_same_job"]["job_id"]
    assert cases["output_same_job"]["expected"]["generation_count_delta"] == 0
    assert cases["signed_url_expired"]["expected"]["new_generation_submit"] is False
    assert cases["submit_outcome_unknown"]["expected"]["blind_resubmit"] is False
    assert cases["visual_review_fail"]["expected"]["technical_retry_count"] == 0
    assert cases["visual_review_fail"]["expected"]["targeted_revise"] is True
    assert cases["missing_stable_reference"]["expected"]["result"] == "ASSET_RESOLUTION"
    assert cases["oauth_required"]["expected"]["technical_retry_count"] == 0
    assert cases["oauth_required"]["expected"]["oauth_recovery_max"] == 1


def batch53_fixture() -> dict:
    return yaml.safe_load((ROOT / "tests/fixtures/shot-production-batch5-3.yaml").read_text(encoding="utf-8"))


def test_shot_production_plans_two_visible_characters_and_scene_with_fixed_maximum() -> None:
    case = batch53_fixture()["shot_a"]
    assert case["visible_entities"] == ["李陵", "苏武", "苏武穹庐"]
    assert case["all_stable_plan"]["count"] == batch53_fixture()["max_reference_count"] == 3
    assert len(case["all_stable_plan"]["selected"]) == 3


def test_shot_production_reports_missing_key_visible_character_reference() -> None:
    plan = batch53_fixture()["shot_a"]["current_plan"]
    assert plan["status"] == "MISSING_STABLE_REFERENCE"
    assert plan["missing_stable_reference"] == ["苏武"]


def test_shot_production_selects_and_explains_three_when_candidates_overflow() -> None:
    fixture = batch53_fixture()
    case = fixture["shot_b"]
    plan = case["all_stable_overflow_plan"]
    assert len(case["candidates"]) == 4
    assert plan["count"] == len(plan["selected"]) == fixture["max_reference_count"]
    assert plan["omitted"] and plan["rationale"]


def test_shot_production_compiles_negative_semantics_to_visible_evidence_and_forbidden_outcomes() -> None:
    delta = batch53_fixture()["shot_a"]["delta"]
    assert len(delta["required_visual_evidence"]) >= 4
    assert len(delta["forbidden_visual_outcome"]) >= 4
    assert any("距离" in item for item in delta["required_visual_evidence"])
    assert any("接触" in item for item in delta["forbidden_visual_outcome"])


def test_shot_production_compiles_over_shoulder_composition_constraint() -> None:
    composition = batch53_fixture()["shot_a"]["delta"]["composition_constraint"]
    assert "肩部" in composition["required"] or "背影" in composition["required"]
    assert "正面并排" in composition["forbidden"]


def test_shot_production_accepts_explicit_prop_state_transition() -> None:
    transition = batch53_fixture()["shot_b"]["prop_transition"]
    assert transition["previous"] != transition["current"]
    assert transition["result"] == "ALLOWED_SHOT_DELTA"


def test_shot_production_compiles_camera_motion_as_static_key_image_intent() -> None:
    intent = batch53_fixture()["static_camera_intent"]
    assert all(intent[name] for name in ("push_in", "tilt_up", "rack_focus"))
    assert intent["temporal_motion_required"] is False


def test_shot_production_cross_shot_review_distinguishes_locked_and_allowed_delta() -> None:
    review = batch53_fixture()["cross_shot_review"]
    assert review["locked"] and review["allowed_delta"] and review["shot_specific_delta"]
    assert review["allowed_delta_is_drift"] is False
    assert review["compare_only_per_shot_pass"] is True


def test_shot_production_keeps_identity_annotation_after_visual_review() -> None:
    order = batch53_fixture()["identity_annotation_order"]
    assert order == ["Provider Output", "Visual Content Review PASS", "Identity Annotation", "Media Import"]


def test_shot_production_does_not_pad_simple_shot_reference_plan() -> None:
    case = batch53_fixture()["shot_c"]
    assert case["count"] == len(case["selected"]) == 2
    assert case["padding_reference"] is None


def test_scene_level_production_combines_one_shared_context_with_named_per_shot_references() -> None:
    fixture = yaml.safe_load((ROOT / "tests/fixtures/scene-level-batch5-5.yaml").read_text(encoding="utf-8"))
    scene = fixture["scene"]
    references = fixture["references"]

    assert scene["id"] and scene["shared_context"]["locked_facts"]
    assert 3 <= len(scene["shots"]) <= 5
    assert len({shot["id"] for shot in scene["shots"]}) == len(scene["shots"])
    assert all(shot["delta"] for shot in scene["shots"])
    assert all(len(shot["reference_ids"]) <= fixture["max_reference_count"] for shot in scene["shots"])
    assert all(reference_id in references for shot in scene["shots"] for reference_id in shot["reference_ids"])
    assert all(
        reference["identity"] and reference["asset_id"] and reference["media_id"] and reference["purpose"]
        for reference in references.values()
    )


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
