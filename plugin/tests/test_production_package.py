"""T2 offline assembly, authority, complexity and recovery acceptance."""
from __future__ import annotations

import json
from pathlib import Path
import socket

import pytest
from pydantic import ValidationError

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.creation import Work, Script, Episode, Scene, Shot
from drama_plugin.production import (
    AssemblyBoundary, DomainReference, PackageContent, ProductionPackage, ProductionPackageStore,
    SourceDomain, SourceOwner,
)
from drama_plugin.production.assembler import ShotAssembler
from drama_plugin.production.sources import SourceReadError
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.runtime import ActionKind, ArtifactReference, RunMode, RuntimeAction, RuntimeState
from drama_plugin.runtime.engine import foundation_workflows

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("T2 forbids network, generation and Prompt projection")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr("drama_plugin.plugin.load_config", lambda _: DramaPluginConfig())
    monkeypatch.setattr("drama_plugin.professional.compile_prompt_projection", forbidden)
    monkeypatch.setattr("drama_plugin.hosts.cinematic_projection.project", forbidden)


@pytest.fixture
def fixture(tmp_path):
    data = MockDramaData.empty()
    data.work = Work(id="work", title="Unit-test-only", content={"approval": {"status": "APPROVED"}})
    data.script = Script(id="script", work_id="work", title="Unit", content={})
    data.episode = Episode(id="episode", script_id="script", episode_no=1, title="Unit", content={})
    data.scene = Scene(id="scene", episode_id="episode", order=1, title="Unit", content={
        "approvedSceneText": "CANON TEXT MUST NEVER BE COPIED INTO A PACKAGE",
        "approval": {"status": "APPROVED"}, "spokenContent": []})
    pins = {}
    def bible(department, records):
        body = {"schemaVersion": "creative-bible-v1", "id": "unit-" + department, "type": department,
            "version": 1, "workRef": "work", "sceneRefs": ["scene"], "shotRefs": [],
            "sourceRefs": [{"key": "work:work", "kind": "CANON", "fingerprint": sha256_canonical(data.work)}],
            "dependsOn": [], "status": "APPROVED", "createdByCapability": department,
            "approvedBy": ["unit-author"], "approvalRefs": [{"key": "unit-approval", "kind": "DESIGN",
                "fingerprint": sha256_canonical({"unit": "approval fixture"})}],
            "content": [{"id": identity, "scopeRefs": ["scene"], "values": values,
                "provenance": "NEW_PROFESSIONAL_ELABORATION", "sourceRefs": [{
                    "key": "work:work", "kind": "CANON", "fingerprint": sha256_canonical(data.work)}]} for identity, values in records],
            "createdAt": "2026-09-01T00:00:00Z", "updatedAt": "2026-09-01T00:00:00Z"}
        (tmp_path / (department + ".json")).write_text(json.dumps(body))
        pins[department] = {"key": "bible:" + body["id"], "kind": "DESIGN", "fingerprint": sha256_canonical(body)}
    bible("director", [("direction", {"cinematic_interpretation": "KEEP ME IN THE ORIGINAL OWNER"})])
    bible("shot-design", [("K01", {"shot_ref": "K01", "purpose": "Observe", "subjects": ["person"]})])
    bible("cinematography", [("CAM-01", {"perspective": "VISIBLE ONLY BY REFERENCE"}),
                             ("CAM-02", {"perspective": "OTHER SHOT, NEVER SELECT"})])
    data.shot = Shot(id="shot", scene_id="scene", shot_no="1", content={"purpose": "Observe",
        "requiredTransition": "Already authored transition", "plannedDurationMs": 4000,
        "coverageCandidateId": "K01", "cameraRecord": "CAM-01", "beatRef": "B01",
        "subjectAction": "Already authored action", "visualEntryState": "Before",
        "visualExitState": "After", "departmentRefs": pins})
    return data, tmp_path


def load(fixture, **kwargs):
    data, directory = fixture
    return DramaPlugin.load(ROOT, mock_data=data, legacy_reads=True, production_artifact_roots=(directory,), **kwargs)


def create(plugin, mode=RunMode.EXPERIMENT, run_id="run"):
    return plugin.runtime.create_run(work_id="work", scene_id="scene", shot_id="shot",
        workflow_id="prepare-shot:v1", mode=mode, run_id=run_id)


async def assembled(plugin, mode=RunMode.EXPERIMENT, run_id="run"):
    run = create(plugin, mode, run_id)
    result = await plugin.runtime.run(run.run_id)
    assert result.state == RuntimeState.SUCCEEDED
    reference = result.last_result.artifact_refs[0]
    return plugin.production_packages.get(reference), result


@pytest.mark.parametrize("mode", list(RunMode))
async def test_plugin_native_e2e_has_one_assembler_no_legacy_dispatch_or_canon_change(fixture, monkeypatch, mode):
    plugin = load(fixture)
    data = fixture[0]
    before = {name: dump_contract(getattr(data, name)) for name in ("work", "scene", "shot", "script", "episode")}
    calls, envelopes = [], []
    original = plugin.runtime.executor.execute
    async def execute(key, inputs):
        calls.append(key);envelopes.append(inputs.model_dump_json())
        return await original(key, inputs)
    async def forbidden(*args, **kwargs):
        pytest.fail("Target assembly cannot invoke LegacyCapabilityBridge, production or a Prompt pipeline")
    monkeypatch.setattr(plugin.runtime.executor, "execute", execute)
    monkeypatch.setattr(plugin.runtime.executor.legacy, "execute", forbidden)
    monkeypatch.setattr(plugin.providers.production, "generate_image", forbidden)
    monkeypatch.setattr(plugin.providers.production, "generate_video", forbidden)
    package, result = await assembled(plugin, mode)
    assert calls == ["production.assemble_package:v1", "production.inspect_package:v1"]
    assert package.boundary.mode == mode and not package.boundary.provider_submission_allowed
    assert (package.scope.work.artifact_ref, package.scope.scene.artifact_ref, package.scope.shot.artifact_ref) == ("work", "scene", "shot")
    assert plugin.shot_assembler.role == "ASSEMBLER" and not plugin.production_packages.creative_authority
    assert len(plugin.tools.list()) == 52 and len(plugin.skills.list()) == 57
    assert before == {name: dump_contract(getattr(data, name)) for name in before}
    assert all("CANON TEXT" not in text and "KEEP ME" not in text for text in envelopes)
    snapshot = plugin.runtime.serialize(result.run_id)
    assert "sources" not in json.loads(snapshot) and package.fingerprint in snapshot
    assert plugin.shot_assembler.sources.legacy.lifecycle == "MIGRATION_ONLY"
    assert plugin.shot_assembler.sources.lifecycle == "TARGET_VERSION_RESOLVER_WITH_MIGRATION_ONLY_READ_BACKEND"
    await plugin.aclose()


async def test_ref_only_frozen_extra_rejection_and_no_vendor_fields(fixture):
    plugin = load(fixture);package, _ = await assembled(plugin)
    encoded = package.model_dump_json(by_alias=True)
    assert "CANON TEXT" not in encoded and "KEEP ME" not in encoded and "VISIBLE ONLY" not in encoded
    assert not any(v in encoded.lower() for v in ("seedance", "vidu", "comfy", "fish", "flux", "prompt_ir"))
    assert ProductionPackage.model_validate_json(encoded) == package
    with pytest.raises(ValidationError):package.fingerprint = "0" * 64
    with pytest.raises(ValidationError):package.sources[0].reference.path = ("other",)
    for key in ("extras", "metadata", "context", "professionalData", "directorPackage", "workContent"):
        with pytest.raises(ValidationError):ProductionPackage.model_validate({**package.model_dump(), key: {"body": "forbidden"}})
    with pytest.raises(ValidationError):AssemblyBoundary(mode=RunMode.EXPERIMENT,
        policy_ref=package.boundary.policy_ref, provider_submission_allowed=True)
    with pytest.raises(ValidationError):
        ProductionPackage.model_validate({**package.model_dump(), "fingerprint": "0" * 64})
    await plugin.aclose()


async def test_deterministic_across_runs_and_canonical_order(fixture):
    plugin = load(fixture)
    first, _ = await assembled(plugin, run_id="first")
    second, _ = await assembled(plugin, run_id="second")
    assert first == second and first.package_id == second.package_id
    raw = first.model_dump(exclude={"package_id", "fingerprint"})
    raw["sources"] = list(reversed(raw["sources"]))
    with pytest.raises(ValidationError, match="canonical order"):PackageContent.model_validate(raw)
    assert await plugin.shot_assembler.validate_sources(first) == await plugin.shot_assembler.validate_sources(second)
    await plugin.aclose()


async def test_source_version_changes_fingerprint_old_package_stale_no_reverse_write(fixture):
    plugin = load(fixture)
    first, _ = await assembled(plugin, run_id="first")
    data, directory = fixture
    body = json.loads((directory/"cinematography.json").read_text());body["version"] = 2
    body["content"][0]["values"]["perspective"] = "OWNER AUTHORED NEW VERSION"
    (directory/"cinematography.json").write_text(json.dumps(body))
    data.shot.content["departmentRefs"]["cinematography"]["fingerprint"] = sha256_canonical(body)
    stale = await plugin.shot_assembler.validate_sources(first)
    assert stale.status == "UNRESOLVED" and any(i.code == "VERSION_MISMATCH" for i in stale.issues)
    second, _ = await assembled(plugin, run_id="second")
    assert first.fingerprint != second.fingerprint and first.package_id != second.package_id
    assert plugin.production_packages.get(first.artifact_reference()) == first
    camera = next(r.reference for r in second.sources if r.domain == "CAMERA")
    assert camera.version == 2
    assert json.loads((directory/"cinematography.json").read_text()) == body
    await plugin.aclose()


@pytest.mark.parametrize("fault,code", [("shot_scene", "SCOPE_MISMATCH"), ("work_chain", "SCOPE_MISMATCH"),
    ("bible_scope", "SCOPE_MISMATCH"), ("wrong_owner", "AUTHORITY_MISMATCH"),
    ("old_pin", "VERSION_MISMATCH"), ("unapproved", "AUTHORITY_MISMATCH"),
    ("missing_file", "MISSING_REQUIRED_SOURCE"), ("missing_camera_record", "MISSING_REQUIRED_SOURCE"),
    ("missing_duration", "MISSING_REQUIRED_SOURCE"), ("missing_purpose", "MISSING_REQUIRED_SOURCE"),
    ("missing_director", "MISSING_REQUIRED_SOURCE")])
async def test_missing_or_invalid_source_returns_unresolved_owner_never_fills(fixture, fault, code):
    data, directory = fixture
    if fault == "shot_scene":data.shot.scene_id = "another-scene"
    elif fault == "work_chain":data.script.work_id = "another-work"
    elif fault == "missing_duration":data.shot.content.pop("plannedDurationMs")
    elif fault == "missing_purpose":data.shot.content.pop("purpose")
    elif fault == "missing_director":data.shot.content["departmentRefs"].pop("director")
    elif fault == "missing_camera_record":data.shot.content["cameraRecord"] = "CAM-UNKNOWN"
    elif fault == "missing_file":(directory/"cinematography.json").unlink()
    else:
        body = json.loads((directory/"cinematography.json").read_text())
        if fault == "bible_scope":body["sceneRefs"] = ["another-scene"]
        elif fault == "wrong_owner":body["createdByCapability"] = "director"
        elif fault == "old_pin":body["version"] = 2
        elif fault == "unapproved":body.update(status="DRAFT", approvedBy=[], approvalRefs=[])
        (directory/"cinematography.json").write_text(json.dumps(body))
        if fault != "old_pin":data.shot.content["departmentRefs"]["cinematography"]["fingerprint"] = sha256_canonical(body)
    original = data.shot.model_dump_json()
    plugin = load(fixture);run = create(plugin)
    blocked = await plugin.runtime.run(run.run_id)
    assert blocked.state == RuntimeState.FAILED and blocked.last_result.code == "ASSEMBLY_UNRESOLVED"
    assert blocked.last_result.recovery_class.value == "HARD_BLOCK"
    assert blocked.step_attempts == 1
    validation = plugin.production_packages.validation(blocked.last_result.artifact_refs[0])
    assert validation.status == "UNRESOLVED" and any(issue.code == code for issue in validation.issues)
    assert all(issue.owner and issue.artifact_ref for issue in validation.issues)
    assert data.shot.model_dump_json() == original
    assert plugin.runtime.next_action(run.run_id).kind == ActionKind.STOP
    assert all(ref.owner != "production-package" for ref in blocked.last_result.artifact_refs)
    await plugin.aclose()


async def test_no_empty_irrelevant_domains_and_huge_unrelated_professional_library_has_no_size_effect(fixture):
    plugin = load(fixture);first, _ = await assembled(plugin, run_id="first")
    data, directory = fixture
    for n in range(150):
        (directory/f"unrelated-{n}.json").write_text(json.dumps({"id":f"unrelated-{n}", "body":"UNRELATED" * 1000}))
    second, _ = await assembled(plugin, run_id="second")
    assert first == second
    assert len(first.model_dump_json().encode()) == len(second.model_dump_json().encode())
    assert not {"LIGHTING", "COLOR", "SUBJECTS", "WORLD", "REFERENCE"} & {ref.domain for ref in second.sources}
    assert len({ref.reference.artifact_ref for ref in second.sources if ref.reference.owner in {"professional", "direction"}}) == 3
    await plugin.aclose()


async def test_large_current_bible_body_does_not_inflate_package(fixture):
    plugin = load(fixture);first, _ = await assembled(plugin, run_id="first")
    data, directory = fixture
    body = json.loads((directory/"cinematography.json").read_text())
    body["content"][0]["values"]["research_notes"] = "LARGE BIBLE ONLY AT ITS OWNER " * 20_000
    (directory/"cinematography.json").write_text(json.dumps(body))
    data.shot.content["departmentRefs"]["cinematography"]["fingerprint"] = sha256_canonical(body)
    second, _ = await assembled(plugin, run_id="second")
    assert first.fingerprint != second.fingerprint
    assert len(first.model_dump_json().encode()) == len(second.model_dump_json().encode())
    assert "research_notes" not in second.model_dump_json()
    await plugin.aclose()


async def test_duplicate_owner_selections_collapsed_conflicting_revision_and_scope_rejected(fixture):
    plugin = load(fixture);package, _ = await assembled(plugin)
    content = package.model_dump(exclude={"package_id", "fingerprint"})
    content["sources"] = [*content["sources"], content["sources"][0]]
    with pytest.raises(ValidationError, match="Duplicate"):PackageContent.model_validate(content)
    content = package.model_dump(exclude={"package_id", "fingerprint"})
    pro = next(i for i,x in enumerate(content["sources"]) if x["reference"]["owner"] == "professional")
    altered = {**content["sources"][pro], "reference": {**content["sources"][pro]["reference"],
        "version":2, "fingerprint":"0"*64, "path":("other",)}}
    content["sources"] = [*content["sources"], altered]
    with pytest.raises(ValidationError, match="Conflicting"):PackageContent.model_validate(content)
    content = package.model_dump(exclude={"package_id", "fingerprint"})
    content["scope"]["shot"]["artifact_ref"] = "another-shot"
    with pytest.raises(ValidationError, match="package scope"):PackageContent.model_validate(content)
    await plugin.aclose()


async def test_scope_contract_rejects_wrong_owner_and_paths_cannot_access_files(fixture):
    plugin = load(fixture);package, _ = await assembled(plugin)
    content = package.model_dump(exclude={"package_id", "fingerprint"})
    content["scope"]["scene"]["owner"] = "work"
    with pytest.raises(ValidationError, match="Scope requires"):PackageContent.model_validate(content)
    ref = package.sources[0].reference
    with pytest.raises(ValidationError):type(ref).model_validate({**ref.model_dump(), "path": ("..", "secret")})
    with pytest.raises(SourceReadError):
        await plugin.shot_assembler.sources.resolve(ref.model_copy(update={"path":("missing",)}))
    await plugin.aclose()


async def test_recovery_after_assembly_forwards_same_ref_without_assembling_again(fixture, monkeypatch):
    plugin = load(fixture);run = create(plugin)
    checkpoint = await plugin.runtime.run(run.run_id, max_ticks=2)
    assert checkpoint.cursor == 1 and checkpoint.state == RuntimeState.READY
    reference = checkpoint.last_result.artifact_refs[0]
    snapshot = plugin.runtime.serialize(run.run_id)
    restored = load(fixture, production_package_store=plugin.production_packages)
    restored.runtime.restore(snapshot)
    assert restored.runtime.next_action(run.run_id) == plugin.runtime.next_action(run.run_id)
    async def forbidden(*args, **kwargs):pytest.fail("Completed assembly must not run after recovery")
    monkeypatch.setattr(restored.shot_assembler, "assemble", forbidden)
    done = await restored.runtime.run(run.run_id)
    assert done.state == RuntimeState.SUCCEEDED and done.last_result.artifact_refs == (reference,)
    assert (await restored.runtime.run(run.run_id)) == done
    await plugin.aclose();await restored.aclose()


async def test_lost_package_store_reports_missing_dependency_without_reassembly(fixture, monkeypatch):
    plugin = load(fixture);run = create(plugin)
    await plugin.runtime.run(run.run_id, max_ticks=2)
    restored = load(fixture);restored.runtime.restore(plugin.runtime.serialize(run.run_id))
    async def forbidden(*args, **kwargs):pytest.fail("Losing a package store cannot rewind completed assembly")
    monkeypatch.setattr(restored.shot_assembler, "assemble", forbidden)
    failed = await restored.runtime.run(run.run_id)
    assert failed.state == RuntimeState.FAILED and failed.last_result.code == "PACKAGE_STORE_RESTORE_REQUIRED"
    await plugin.aclose();await restored.aclose()


async def test_store_is_immutable_idempotent_and_package_json_can_restore_its_same_identity(fixture):
    plugin = load(fixture);package, _ = await assembled(plugin)
    store = ProductionPackageStore()
    reference = store.put(ProductionPackage.model_validate_json(package.model_dump_json()))
    assert store.put(package) == reference == package.artifact_reference()
    assert store.get(reference) == package and store.durability == "IN_MEMORY_TEST_FOUNDATION"
    with pytest.raises(ValueError):store.get(reference.model_copy(update={"owner":"work"}))
    await plugin.aclose()


@pytest.mark.parametrize("kind", [ActionKind.COMPLETE, ActionKind.REQUEST_USER_DECISION])
def test_previous_result_input_is_only_for_capability_actions(kind):
    with pytest.raises(ValidationError):RuntimeAction(kind=kind, input_from_previous=True)


def test_t1_workflow_fingerprint_remains_compatible():
    assert sha256_canonical(foundation_workflows()["inspect-work:v1"]) == "478e5fe755db4823c81695db6ab077df9a94c785da28e97f593e1e2156acea3d"
