"""E2 exact-author/version/adoption/route offline acceptance."""
from __future__ import annotations

import inspect
import json
from pathlib import Path
import socket

import pytest
from pydantic import ValidationError

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.creative_engine.contracts import (
    Authority, AuthorRequest, CanonDraft, CreativeCheckpoint, DependencyTask, DesignBody, Dialogue,
    FIELD_AUTHORITY, Kind, RevisionRequest, RoutePlan, RouteRequest, SceneBody, ScriptBody,
    ShotBody, SourceBody, VersionRef, WorkBody,
)
from drama_plugin.creative_engine.routes import RouteSelector
from drama_plugin.creative_engine.sources import NativeCreativeSources
from drama_plugin.generation.contracts import AudioExecutionPlan, GenerationPreparation, GenerationTask
from drama_plugin.governance.contracts import GateEffect, HardStopFamily
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.runtime.contracts import ArtifactReference, CapabilityInput, RunMode, RuntimeState

ROOT = Path(__file__).resolve().parents[1]
SOURCE = SourceBody(goal="Observe a choice and its consequences", text="A visitor asks for help. The listener turns away.",
                    spoken_language="en", subtitle_languages=("zh",))


class Authors:
    def __init__(self):
        self.calls = []

    async def author(self, request: AuthorRequest):
        if request.canon is None or (request.revision and request.revision.owner == Authority.CANON):
            self.calls.append("canon")
            return CanonDraft(work=WorkBody(interpretation="A refusal tests responsibility",
                dramatic_intent="Show the consequence of withholding help", character_meaning="Indifference conceals responsibility"),
                script=ScriptBody(screenplay="A visitor asks; the listener turns away."),
                scene=SceneBody(scene_text=request.revision.instruction if request.revision else "The visitor asks for help; the listener leaves.",
                    dialogue=(Dialogue(id="line", speaker="visitor", text="Please help.", must_keep=True),)))
        self.calls.append("direction")
        return ShotBody(purpose="Hold the relationship through the refusal", required_transition="The listener turns away",
            duration_ms=6000, subject_action="The listener turns away while the visitor remains",
            entry_state="Both people face each other", exit_state="The listener faces away",
            coverage="Keep both people visible", blocking_intent="Maintain their separation",
            camera_intent="Observe at eye level", editing_relation="Hold after the turn",
            performance_direction=request.revision.instruction if request.revision else "Delay the response",
            spoken_ids=("line",), professional_domains=tuple(sorted(("CAMERA", "WORLD", "SOUND", "SUBJECTS"))))

    async def design(self, request: AuthorRequest):
        self.calls.append("professional")
        return (DesignBody(domain="SUBJECTS", facts={"character_ref": "visitor", "face_structure": "Approved visible visitor face"}),
            DesignBody(domain="CAMERA", facts={"perspective": "Both people visible", "camera_movement": "Fixed"}),
            DesignBody(domain="WORLD", facts={"location_identity": "A passage with a door", "topology": "Door behind listener"}),
            DesignBody(domain="SOUND", facts={"ambience": "Quiet air", "silence_design": "Hold silence after speech"}))


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("E2 forbids network/provider/legacy creative orchestration")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr("drama_plugin.plugin.load_config", lambda _: DramaPluginConfig())
    monkeypatch.setattr("drama_plugin.hosts.creative_source.CreativeSourceHost.director_handoff", forbidden)
    monkeypatch.setattr("drama_plugin.hosts.director_artifacts.DirectorArtifactStore.transition", forbidden)
    monkeypatch.setattr("drama_plugin.professional.compile_prompt_projection", forbidden)


def plugin(tmp_path, authors=None, **kwargs):
    author = authors or Authors()
    return DramaPlugin.load(ROOT, mock_data=MockDramaData(), ledger_path=tmp_path / "production.sqlite3",
        creative_root=tmp_path / "canon", canon_author=kwargs.pop("canon_author", author),
        direction_author=kwargs.pop("direction_author", author), professional_author=kwargs.pop("professional_author", author), **kwargs)


def refs(p, run_id, kind):
    return tuple(ref for ref in p.creative.state.checkpoint(run_id).refs if p.creative_versions.resolve(ref).kind == kind)


async def finish(p, run):
    done = await p.runtime.run(run.run_id)
    if done.state == RuntimeState.WAITING_USER:
        cp = p.creative.state.checkpoint(run.run_id)
        await p.decide_target_run(run.run_id, decision_id=p.runtime.decision_id(run.run_id), accepted=True, source_ref=cp.candidate_ref)
        done = await p.runtime.run(run.run_id)
    return done


@pytest.mark.parametrize("mode", list(RunMode))
async def test_goal_to_package_single_runtime_and_e1_preparation(tmp_path, mode):
    a, p = Authors(), None
    p = plugin(tmp_path, a)
    calls = []
    execute = p.runtime.executor.execute
    async def recorded(key, inputs):
        calls.append(key)
        return await execute(key, inputs)
    p.runtime.executor.execute = recorded
    run = p.create_film_run(work_id="film", source=SOURCE, mode=mode, run_id="film-run")
    done = await finish(p, run)
    assert done.state == RuntimeState.SUCCEEDED, done
    assert a.calls == ["canon", "direction", "professional"]
    assert all(key.startswith("creative.") for key in calls)
    cp = p.creative.state.checkpoint(run.run_id)
    package = p.production_packages.get(cp.package_ref)
    assert package.scope.scene.version and package.scope.shot.version
    assert all(p.creative_versions.resolve(ref).state == "ADOPTED" for ref in cp.refs
               if mode == RunMode.PRODUCTION and p.creative_versions.resolve(ref).kind != Kind.SOURCE)
    prepared = p.create_generation_run(work_id=run.scope.work_id, scene_id=run.scope.scene_id,
        shot_id=run.scope.shot_id, mode=mode, package_ref=cp.package_ref,
        task=GenerationTask(input_mode="text_to_video"), run_id="prepare")
    result = await p.runtime.run(prepared.run_id)
    assert result.state == RuntimeState.SUCCEEDED, result
    ready = p.generation_artifacts.get(p.generation_artifacts.prepared(result.run_id), GenerationPreparation)
    plan = p.generation_artifacts.get(ready.audio_plan_ref, AudioExecutionPlan)
    assert plan.speech_events[0].language == "en"
    assert not ready.provider_submission_allowed
    with p.ledger.transaction() as db:
        indexes = "\n".join(row[0] for row in db.execute("SELECT value_json FROM ledger_index WHERE index_type LIKE 'creative-%'"))
        assert SOURCE.text not in indexes and "Indifference conceals responsibility" not in indexes
        assert len(list(db.execute("SELECT name FROM sqlite_master WHERE type='table'"))) == 4
    assert SOURCE.text not in p.runtime.serialize(run.run_id)
    assert len({key for key in p.runtime.executor.native_keys if not key.startswith("film.")}) == 25


@pytest.mark.parametrize("owner,cursor", [("canon_author", 1), ("direction_author", 2), ("professional_author", 3)])
async def test_absent_author_waits_then_resumes_correct_owner(tmp_path, owner, cursor):
    a = Authors()
    p = plugin(tmp_path, a, **{owner: None})
    run = p.create_film_run(work_id="film", source=SOURCE, mode=RunMode.EXPERIMENT)
    waiting = await p.runtime.run(run.run_id)
    assert waiting.state == RuntimeState.WAITING_EXTERNAL and waiting.cursor == cursor
    assert waiting.last_result.external_ref.owner == "capability-absence"
    decision = p.gate_findings.decision(p.gate_findings.latest(run.run_id))
    assert decision.effect == GateEffect.CAPABILITY_ABSENT
    if owner == "professional_author":
        p.creative.professional_author.author = a
    else:
        setattr(p.creative, owner, a)
    assert (await p.resume_film_run(run.run_id)).state == RuntimeState.SUCCEEDED


async def test_adoption_exact_hash_dependency_recheck_and_independent_identity(tmp_path):
    p = plugin(tmp_path)
    run = p.create_film_run(work_id="film", source=SOURCE, mode=RunMode.PRODUCTION)
    assert (await p.runtime.run(run.run_id)).state == RuntimeState.WAITING_USER
    cp = p.creative.state.checkpoint(run.run_id)
    candidates = cp.refs
    with pytest.raises(ValueError, match="exact candidate"):
        await p.decide_target_run(run.run_id, decision_id=p.runtime.decision_id(run.run_id), accepted=True,
            source_ref=ArtifactReference(owner="creative-candidate", artifact_ref="other", version=1))
    await p.decide_target_run(run.run_id, decision_id=p.runtime.decision_id(run.run_id), accepted=True, source_ref=cp.candidate_ref)
    done = await p.runtime.run(run.run_id)
    assert done.state == RuntimeState.SUCCEEDED
    adopted = p.creative.state.checkpoint(run.run_id)
    assert candidates[4].identity != adopted.refs[4].identity
    assert p.creative_versions.resolve(candidates[4]).state == "REVIEWED"
    assert p.creative_versions.resolve(adopted.refs[4]).adoption_decision_ref == adopted.decision_ref
    assert not p.creative_versions.stale(candidates[4])


async def test_adoption_stale_candidate_is_blocked(tmp_path):
    p = plugin(tmp_path)
    run = p.create_film_run(work_id="film", source=SOURCE, mode=RunMode.PRODUCTION)
    await p.runtime.run(run.run_id)
    cp = p.creative.state.checkpoint(run.run_id)
    await p.decide_target_run(run.run_id, decision_id=p.runtime.decision_id(run.run_id), accepted=True, source_ref=cp.candidate_ref)
    p.creative_versions.invalidate(cp.refs[3])
    done = await p.runtime.run(run.run_id)
    assert done.state == RuntimeState.BLOCKED
    assert p.creative.state.checkpoint(run.run_id).package_ref is None


@pytest.mark.parametrize("owner,kind,expected", [(Authority.CANON, Kind.SCENE, ["canon", "direction", "professional"]),
    (Authority.DIRECTION, Kind.SHOT, ["direction", "professional"]),
    (Authority.PROFESSIONAL, Kind.PROFESSIONAL, ["professional"])])
async def test_revision_routes_exact_owner_stales_rebuild_and_retains_history(tmp_path, owner, kind, expected):
    a, p = Authors(), None
    p = plugin(tmp_path, a)
    run = p.create_film_run(work_id="film", source=SOURCE, mode=RunMode.PRODUCTION)
    assert (await finish(p, run)).state == RuntimeState.SUCCEEDED
    cp = p.creative.state.checkpoint(run.run_id)
    old_package = p.production_packages.get(cp.package_ref)
    target = refs(p, run.run_id, kind)[0]
    original = p.creative_versions.resolve(target)
    a.calls.clear()
    request = RevisionRequest(owner=owner, target_ref=target,
        finding_ref=ArtifactReference(owner="creative-media-review", artifact_ref="observed-revise", version=1),
        instruction="Make the hesitation observable")
    revision = p.create_creative_revision_run(run.run_id, request)
    assert (await finish(p, revision)).state == RuntimeState.SUCCEEDED
    assert a.calls == expected
    updated = p.creative.state.checkpoint(revision.run_id)
    assert updated.package_ref != cp.package_ref
    assert p.creative_versions.resolve(target) == original
    assert p.creative_versions.stale(target)
    assert (await p.shot_assembler.validate_sources(old_package)).status == "UNRESOLVED"
    for selection in old_package.sources:
        await p.prompt_compiler.reader.resolver.resolve(selection.reference)
    new_target = refs(p, revision.run_id, kind)[0]
    assert new_target.version > target.version


@pytest.mark.parametrize("violation", ["work", "scene", "shot", "professional", "version"])
async def test_wrong_object_or_version_uses_hs1(tmp_path, violation):
    p = plugin(tmp_path)
    run = p.create_film_run(work_id="film", source=SOURCE, mode=RunMode.EXPERIMENT)
    await finish(p, run)
    cp = p.creative.state.checkpoint(run.run_id)
    target = cp.refs[3]
    if violation == "version":
        target = VersionRef(identity=target.identity, version=target.version + 1, fingerprint=target.fingerprint)
        revision = RevisionRequest(owner=Authority.CANON, target_ref=target,
            finding_ref=ArtifactReference(owner="review", artifact_ref="finding"), instruction="Revise")
        new = p.create_film_run(work_id="film", source_ref=p.creative.state.input(run.run_id).source_ref,
            mode=RunMode.EXPERIMENT, revision=revision, base_refs=cp.refs)
    else:
        from drama_plugin.runtime.contracts import RuntimeScope
        scope = RuntimeScope(work_id="wrong" if violation == "work" else "film",
            scene_id="wrong" if violation == "scene" else "film:scene",
            shot_id="wrong" if violation in {"shot", "professional"} else "film:shot")
        artifact = p.creative_versions.resolve(cp.refs[-1] if violation == "professional" else target)
        body = artifact.body
        if violation == "professional":
            # Cross-scope provenance is now rejected at the owner write boundary.
            # A legitimately scoped OTHER object's design still exercises HS1.
            from drama_plugin.professional_design.provenance import creative_facts
            with pytest.raises(ValueError, match="AUTHORITY_MISMATCH"):
                p.creative_versions.write(writer=artifact.authority, kind=artifact.kind, scope=scope,
                    body=body, sources=(), operation="bad-provenance")
            assert isinstance(body, DesignBody)
            facts = creative_facts(body.facts)
            assert isinstance(facts, dict)
            body = DesignBody(domain=body.domain, facts=facts)
        bad = p.creative_versions.write(writer=artifact.authority, kind=artifact.kind, scope=scope,
            body=body, sources=(), operation="bad-scope")
        new = p.create_film_run(work_id="film", source_ref=p.creative.state.input(run.run_id).source_ref,
            mode=RunMode.EXPERIMENT, base_refs=(*cp.refs[:-1], bad))
    done = await p.runtime.run(new.run_id)
    assert done.state == RuntimeState.BLOCKED
    decision = p.gate_findings.decision(p.gate_findings.latest(new.run_id))
    assert decision.risk_families == (HardStopFamily.HS1,)


@pytest.mark.parametrize("input_mode,missing", [("text_to_video", ()), ("image_to_video", ("first_frame",)),
    ("reference_video", ("character_reference", "environment_reference")), ("audio", ())])
def test_routes_choose_only_execution_inputs(input_mode, missing):
    plan = RouteSelector().plan(RouteRequest(input_mode=input_mode))
    assert plan.tasks[0].requires == missing
    assert not plan.capability_available
    assert plan.cost_limit == 0


@pytest.mark.parametrize("tasks,cost", [
    ((DependencyTask(task_id="a", output="image", requires=("b",)), DependencyTask(task_id="b", output="image", requires=("a",))), 0),
    ((DependencyTask(task_id="a", output="image", requires=("absent",)),), 0),
    ((DependencyTask(task_id="a", output="image", estimated_cost=1),), 0),
    (tuple(DependencyTask(task_id=str(i), output="image", requires=(str(i+1),) if i < 5 else ()) for i in range(6)), 0),
])
def test_dependency_cycles_depth_and_cost_rejected(tasks, cost):
    with pytest.raises(ValidationError):
        RoutePlan(route="image_to_video", tasks=tasks, capability_available=False, authorization_required=False, cost_limit=cost)


async def test_missing_references_use_same_runtime_child_and_no_provider(tmp_path):
    p = plugin(tmp_path)
    run = p.create_film_run(work_id="film", source=SOURCE, mode=RunMode.EXPERIMENT,
        route=RouteRequest(input_mode="image_to_video"))
    assert (await finish(p, run)).state == RuntimeState.SUCCEEDED
    cp = p.creative.state.checkpoint(run.run_id)
    assert len(cp.child_runs) == 1
    child = p.runtime.store.load(cp.child_runs[0])
    assert child.state == RuntimeState.WAITING_EXTERNAL and child.workflow_id == "reference-prerequisite:v1"
    assert child.last_result.external_ref.owner == "capability-absence"


@pytest.mark.parametrize("domain,facts", [("SOUND", {"dialogue": "rewrite"}), ("CAMERA", {"ambience": "sound"}),
    ("LIGHTING", {"nested": {"screenplay": "rewrite"}}), ("CANON", {"field": "bad"})])
def test_consumers_and_cross_professional_fields_cannot_author(domain, facts):
    with pytest.raises(ValidationError):
        DesignBody(domain=domain, facts=facts)
    assert FIELD_AUTHORITY["dialogue"] == Authority.CANON


async def test_durable_restart_historical_resolution_and_replay(tmp_path):
    a = Authors()
    p = plugin(tmp_path, a)
    run = p.create_film_run(work_id="film", source=SOURCE, mode=RunMode.PRODUCTION, run_id="durable")
    await p.runtime.run(run.run_id)
    cp = p.creative.state.checkpoint(run.run_id)
    del p
    p = plugin(tmp_path, a)
    await p.decide_target_run(run.run_id, decision_id=p.runtime.decision_id(run.run_id), accepted=True, source_ref=cp.candidate_ref)
    done = await p.runtime.run(run.run_id)
    assert done.state == RuntimeState.SUCCEEDED and a.calls == ["canon", "direction", "professional"]
    for ref in cp.refs:
        assert p.creative_versions.resolve(ref).ref() == ref
    assert await p.runtime.run(run.run_id) == done


async def test_existing_approved_canon_skips_canon_author(tmp_path):
    p = plugin(tmp_path)
    run = p.create_film_run(work_id="film", source=SOURCE, mode=RunMode.PRODUCTION)
    await finish(p, run)
    canon = tuple(r for r in p.creative.state.checkpoint(run.run_id).refs if p.creative_versions.resolve(r).kind in {Kind.WORK, Kind.SCRIPT, Kind.SCENE})
    p.creative.canon_author = None
    new = p.create_film_run(work_id="film", source_ref=p.creative.state.input(run.run_id).source_ref,
        approved_canon_refs=canon, mode=RunMode.PRODUCTION)
    assert (await finish(p, new)).state == RuntimeState.SUCCEEDED


async def test_revision_cycle_and_round_bound(tmp_path):
    p = plugin(tmp_path)
    run = p.create_film_run(work_id="film", source=SOURCE, mode=RunMode.EXPERIMENT)
    await finish(p, run)
    target = refs(p, run.run_id, Kind.SHOT)[0]
    finding = ArtifactReference(owner="review", artifact_ref="cycle-finding")
    request = RevisionRequest(owner=Authority.DIRECTION, target_ref=target, finding_ref=finding, instruction="same correction")
    one = p.create_creative_revision_run(run.run_id, request)
    await finish(p, one)
    two = p.create_creative_revision_run(one.run_id, RevisionRequest(owner=Authority.DIRECTION,
        target_ref=refs(p, one.run_id, Kind.SHOT)[0], finding_ref=finding, instruction="same correction", depth=2))
    done = await p.runtime.run(two.run_id)
    assert done.state == RuntimeState.BLOCKED and done.wait_reason == "REVISION_CYCLE_OR_DEPTH_BOUND"
    new = p.create_film_run(work_id="film", source=SOURCE, mode=RunMode.EXPERIMENT)
    p.creative.state.save(new.run_id, new.scope, CreativeCheckpoint(author_rounds=6))
    bounded = await p.runtime.run(new.run_id)
    assert bounded.state == RuntimeState.BLOCKED and bounded.wait_reason == "AUTHOR_ROUND_BOUND"


def test_no_department_catalog_or_creativity_in_runtime_workflow():
    from drama_plugin.runtime import engine
    from drama_plugin.creative_engine import policy
    from drama_plugin.professional_design.catalog import DEPARTMENT_DOMAINS
    text = inspect.getsource(engine) + inspect.getsource(policy)
    assert not any('"' + name + '"' in text for name in DEPARTMENT_DOMAINS)
    assert not any(name in text for name in ("Dostoevsky", "Petersburg", "S02"))


async def test_experiment_review_to_production_adoption_without_reauthoring(tmp_path):
    a = Authors()
    p = plugin(tmp_path, a)
    run = p.create_film_run(work_id="film", source=SOURCE, mode=RunMode.EXPERIMENT)
    await finish(p, run)
    draft_refs = p.creative.state.checkpoint(run.run_id).refs
    a.calls.clear()
    adoption = p.create_adoption_run(run.run_id)
    assert (await p.runtime.run(adoption.run_id)).state == RuntimeState.WAITING_USER
    assert not a.calls
    cp = p.creative.state.checkpoint(adoption.run_id)
    assert cp.candidate_version_refs == draft_refs
    await p.decide_target_run(adoption.run_id, decision_id=p.runtime.decision_id(adoption.run_id),
        accepted=True, source_ref=cp.candidate_ref)
    assert (await p.runtime.run(adoption.run_id)).state == RuntimeState.SUCCEEDED
    cp = p.creative.state.checkpoint(adoption.run_id)
    assert cp.candidate_version_refs == draft_refs
    for original, adopted in zip(draft_refs[1:], cp.refs[1:], strict=True):
        assert original.identity != adopted.identity
        assert p.creative_versions.resolve(adopted).candidate_origin_ref == original


@pytest.mark.parametrize("owner,kind", [("canon-author", Kind.SCENE), ("creative-direction-author", Kind.SHOT), ("sound-design", Kind.PROFESSIONAL)])
async def test_e1_review_routes_owner_and_never_gives_reviewer_write_access(tmp_path, owner, kind):
    from drama_plugin.creative_engine.feedback import revision_requests
    from drama_plugin.execution.contracts import CreativeMediaReview, ReviewObservation, MediaIdentity
    p = plugin(tmp_path)
    run = p.create_film_run(work_id="film", source=SOURCE, mode=RunMode.PRODUCTION)
    await finish(p, run)
    cp = p.creative.state.checkpoint(run.run_id)
    from drama_plugin.execution.contracts import Authorization, FinishingRecipe
    prepared_run = p.create_generation_run(work_id=run.scope.work_id, scene_id=run.scope.scene_id,
        shot_id=run.scope.shot_id, mode=RunMode.PRODUCTION, package_ref=cp.package_ref, run_id="feedback-prepare")
    assert (await p.runtime.run(prepared_run.run_id)).state == RuntimeState.SUCCEEDED
    ready_ref = p.generation_artifacts.prepared(prepared_run.run_id)
    ready = p.generation_artifacts.get(ready_ref, GenerationPreparation)
    recipe = FinishingRecipe.seal(scope=run.scope, run_id="review", source_package_ref=cp.package_ref,
        preparation_ref=ready_ref, audio_plan_ref=ready.audio_plan_ref, approval_ref=cp.decision_ref, native_policy="PRESERVE")
    execution = p.create_execution_run(run_id="review", mode=RunMode.PRODUCTION, preparation_ref=ready_ref,
        authorization=Authorization(approval_ref=cp.decision_ref, authorized=True, budget_microunits=0, estimated_cost_microunits=0),
        recipe=recipe, route="offline-absent")
    retained = p.execution.reserve(CapabilityInput(run_id=execution.run_id, operation_id="review:0", scope=run.scope))
    media = p.execution.media.retain(b"offline review fixture", kind="VIDEO", mime="video/mp4")
    review = CreativeMediaReview.seal(scope=run.scope, run_id="review", source_package_ref=cp.package_ref,
        operation_ref=retained.operation_ref, attempt_ref=retained.attempt_ref, media=media,
        reviewer="offline-reviewer", policy_version="offline-v1", outcome="REVISE", adoption_recommendation="REVISION_REQUIRED",
        observations=(ReviewObservation(code="OBSERVED_MISMATCH", owner=owner, finding="Observed mismatch", required_revision="Correct the observed hesitation"),))
    # Retain the actual E1 observation contract; E1 does not mutate these creative versions.
    p.execution.store.put(review)
    before = [p.creative_versions.resolve(ref) for ref in cp.refs]
    request = revision_requests(review, review.artifact_reference(), cp.refs, p.creative_versions, depth=1)[0]
    assert p.creative_versions.resolve(request.target_ref).kind == kind
    assert [p.creative_versions.resolve(ref) for ref in cp.refs] == before
    revision = p.route_creative_review(run.run_id, review.artifact_reference())
    assert (await finish(p, revision)).state == RuntimeState.SUCCEEDED
    assert p.creative_versions.stale(request.target_ref)


def test_dependency_children_attempt_count_and_total_are_bounded():
    with pytest.raises(ValidationError):
        DependencyTask(task_id="unbounded", output="image", attempts=3)
    with pytest.raises(ValidationError):
        DependencyTask(task_id="children", output="image", requires=tuple(str(i) for i in range(5)))
    with pytest.raises(ValidationError):
        RoutePlan(route="image_to_video", tasks=tuple(DependencyTask(task_id=str(i), output="image") for i in range(17)),
            capability_available=True, authorization_required=False, cost_limit=0)


async def test_external_source_reference_and_exact_owner_writer(tmp_path):
    p = plugin(tmp_path)
    source = SourceBody(goal="Test designated reference", external_reference="source-owner:designated-reference", spoken_language="ru")
    run = p.create_film_run(work_id="film", source=source, mode=RunMode.EXPERIMENT)
    assert (await finish(p, run)).state == RuntimeState.SUCCEEDED
    scene = refs(p, run.run_id, Kind.SCENE)[0]
    assert p.creative_versions.resolve(scene).source_refs[0] == p.creative.state.input(run.run_id).source_ref
    with pytest.raises(ValueError, match="AUTHORITY"):
        p.creative_versions.write(writer=Authority.DIRECTION, kind=Kind.SCENE, scope=run.scope,
            body=SceneBody(scene_text="unauthorized"), sources=(), operation="wrong-writer")


async def test_missing_professional_artifact_auto_revises_exact_version_with_bound(tmp_path):
    class Incomplete(Authors):
        def __init__(self):
            super().__init__()
            self.requests = []
        async def design(self, request):
            self.requests.append(request)
            designs = await super().design(request)
            return designs[:-1] if len(self.requests) == 1 else designs
    a = Incomplete()
    p = plugin(tmp_path, a)
    run = p.create_film_run(work_id="film", source=SOURCE, mode=RunMode.EXPERIMENT)
    assert (await finish(p, run)).state == RuntimeState.SUCCEEDED
    assert len(a.requests) == 2
    repair = a.requests[1]
    assert repair.revision.owner == Authority.PROFESSIONAL and repair.finding_refs
    assert p.creative_versions.resolve(repair.revision.target_ref).kind == Kind.PROFESSIONAL
    cp = p.creative.state.checkpoint(run.run_id)
    assert cp.author_rounds == 4 and cp.package_ref
    assert p.creative_versions.stale(repair.revision.target_ref)


async def test_professional_incomplete_model_stops_after_two_rounds(tmp_path):
    class Missing(Authors):
        async def design(self, request):
            self.calls.append("professional")
            return ()
    a = Missing()
    p = plugin(tmp_path, a)
    run = p.create_film_run(work_id="film", source=SOURCE, mode=RunMode.EXPERIMENT)
    result = await p.runtime.run(run.run_id)
    assert result.state == RuntimeState.BLOCKED and result.wait_reason == "PROFESSIONAL_OBLIGATION_UNRESOLVED"
    assert a.calls.count("professional") == 2
