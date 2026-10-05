"""T4 interface reduction, source authority, deterministic selection and T3 policy."""
from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.professional import CreativeBible
from drama_plugin.governance import GateCategory
from drama_plugin.production import PackageScope, SourceDomain as D
from drama_plugin.professional_design import ProfessionalDesignRequest, ProfessionalDesignSelection, ProfessionalDesignResolver
from drama_plugin.professional_design.catalog import DEPARTMENT_DOMAINS
from drama_plugin.professional_design.legacy import LegacyProfessionalDesignSources
from drama_plugin.runtime import RunMode, RuntimeScope, RuntimeState
from test_production_package import fixture, offline, load, assembled, ROOT


async def query(plugin, *, domains=()):
    work, scene, shot = await plugin.shot_assembler.sources.scope_sources(
        RuntimeScope(work_id="work", scene_id="scene", shot_id="shot"))
    return ProfessionalDesignRequest(scope=PackageScope(work=work.reference(), scene=scene.reference(), shot=shot.reference()),
        domains=domains)


def add_lighting(fixture):
    data, directory = fixture
    body = json.loads((directory / "cinematography.json").read_text())
    body.update(id="unit-lighting-design", type="lighting-design", createdByCapability="lighting-design")
    body["content"] = [body["content"][0]]
    (directory / "lighting-design.json").write_text(json.dumps(body))
    data.shot.content["departmentRefs"]["lighting-design"] = {
        "key": "bible:" + body["id"], "kind": "DESIGN", "fingerprint": sha256_canonical(body)}


async def test_one_facade_and_ref_only_immutable_selection_preserves_owners(fixture):
    plugin = load(fixture)
    request = await query(plugin)
    selection = await plugin.professional_design.resolve(request)
    assert plugin.professional_design is plugin.shot_assembler.professional_design
    assert type(plugin.professional_design) is ProfessionalDesignResolver
    assert not plugin.professional_design.creative_authority and plugin.professional_design.durability == "EPHEMERAL"
    assert plugin.professional_design.backend.legacy.lifecycle == "MIGRATION_ONLY"
    assert plugin.professional_design.backend.lifecycle == "TARGET_VERSION_RESOLVER_WITH_MIGRATION_ONLY_READ_BACKEND"
    assert selection.status == "RESOLVED"
    assert selection.domains == (D.CAMERA, D.DIRECTION)
    assert len(selection.sources) == 3
    assert {s.reference.owner.value for s in selection.sources} == {"professional", "direction"}
    assert set(json.loads(selection.model_dump_json())) == {"domains", "sources", "issues"}
    assert len(request.model_dump_json().encode()) < 1300
    for forbidden in ("CANON TEXT", "KEEP ME", "VISIBLE ONLY", "research_notes", "reason", "review"):
        assert forbidden not in selection.model_dump_json()
    with pytest.raises(ValidationError):
        selection.sources = ()
    with pytest.raises(ValidationError):
        selection.sources[0].reference.path = ("other",)
    await plugin.aclose()


@pytest.mark.parametrize("field", ["extras", "metadata", "context", "professionalData", "cameraBible", "values"])
async def test_unbounded_fields_rejected(fixture, field):
    plugin = load(fixture)
    request = await query(plugin)
    selection = await plugin.professional_design.resolve(request)
    with pytest.raises(ValidationError):
        ProfessionalDesignSelection.model_validate({**selection.model_dump(), field: {"full": "body"}})
    with pytest.raises(ValidationError):
        ProfessionalDesignRequest.model_validate({**request.model_dump(), field: {"full": "body"}})
    await plugin.aclose()


@pytest.mark.parametrize("domains", [(D.CANON,), (D.CAMERA, D.CAMERA), (D.WORLD, D.CAMERA)])
async def test_domain_vocabulary_is_single_canonical_and_not_canon(fixture, domains):
    plugin = load(fixture)
    request = await query(plugin)
    with pytest.raises(ValidationError):
        ProfessionalDesignRequest(scope=request.scope, domains=domains)
    assert len(D) - 1 == 11
    await plugin.aclose()


async def test_domain_query_reads_camera_without_traversing_platform(fixture, monkeypatch):
    plugin = load(fixture)
    reads = []
    read = plugin.shot_assembler.sources.professional
    async def observed(department, pin):
        reads.append(department)
        return await read(department, pin)
    monkeypatch.setattr(plugin.shot_assembler.sources, "professional", observed)
    selection = await plugin.professional_design.resolve(await query(plugin, domains=(D.CAMERA,)))
    assert selection.status == "RESOLVED" and selection.domains == (D.CAMERA,)
    assert reads == ["cinematography"] and len(selection.sources) == 1
    await plugin.aclose()


async def test_case_a_large_unrelated_catalog_and_library_leave_selection_package_and_read_count_unchanged(fixture, monkeypatch):
    plugin = load(fixture)
    first_selection = await plugin.professional_design.resolve(await query(plugin))
    first, _ = await assembled(plugin, run_id="before")
    expanded = {**DEPARTMENT_DOMAINS, **{f"unbound-specialist-{i}": D.WORLD for i in range(1000)}}
    plugin.professional_design.backend = LegacyProfessionalDesignSources(plugin.shot_assembler.sources, catalog=expanded)
    for i in range(200):
        (fixture[1] / f"unbound-specialist-{i}.json").write_text(json.dumps({"id": f"unused-{i}", "values": "unrelated" * 1000}))
    reads = []
    read = plugin.shot_assembler.sources.professional
    async def observed(department, pin):
        reads.append(department)
        return await read(department, pin)
    monkeypatch.setattr(plugin.shot_assembler.sources, "professional", observed)
    second_selection = await plugin.professional_design.resolve(await query(plugin))
    assert len(reads) == 3
    reads.clear()
    second, _ = await assembled(plugin, run_id="after")
    assert len(reads) == 3
    assert first_selection == second_selection and first == second
    assert len(expanded) > 1000 and len({r.reference.artifact_ref for r in second_selection.sources}) == 3
    await plugin.aclose()


async def test_case_b_unmapped_internal_skill_does_not_change_runtime_path(fixture, monkeypatch):
    plugin = load(fixture)
    first, _ = await assembled(plugin, run_id="before")
    # In-memory test only; no actual Skill directory or top-level capability is created.
    plugin.skills.register(plugin.skills.get("cinematography").model_copy(update={"code": "offline-unmapped-specialist"}))
    calls = []
    execute = plugin.runtime.executor.execute
    async def observed(key, inputs):
        calls.append(key)
        return await execute(key, inputs)
    monkeypatch.setattr(plugin.runtime.executor, "execute", observed)
    second, _ = await assembled(plugin, run_id="after")
    assert first == second and len(plugin.skills.list()) == 58
    assert calls == ["production.assemble_package:v1", "production.inspect_package:v1"]
    await plugin.aclose()


async def test_case_c_optional_missing_resolver_reports_owner_and_t3_experiment_continues(fixture):
    add_lighting(fixture)
    plugin = load(fixture)
    package, _ = await assembled(plugin)
    (fixture[1] / "lighting-design.json").unlink()
    missing = await plugin.professional_design.resolve(await query(plugin))
    assert missing.status == "MISSING" and any(i.domain == D.LIGHTING and i.owner == "professional" for i in missing.issues)
    assert "category" not in missing.model_dump_json() and "HARD_STOP" not in missing.model_dump_json()
    run = plugin.create_governed_run(work_id="work", scene_id="scene", shot_id="shot", mode=RunMode.EXPERIMENT,
        run_id="optional-missing", package_ref=package.artifact_reference())
    done = await plugin.runtime.run(run.run_id)
    decision = plugin.gate_findings.decision(plugin.gate_findings.latest(run.run_id))
    assert done.state == RuntimeState.SUCCEEDED and decision.effect == "CONTINUE"
    assert any(plugin.gate_findings.finding(r).category == GateCategory.WARNING for r in decision.finding_refs)
    assert not decision.user_decision and not decision.risk_families
    await plugin.aclose()


@pytest.mark.parametrize("scope_field,bad", [("workRef", "other-work"), ("sceneRefs", ["other-scene"]), ("shotRefs", ["other-shot"])])
async def test_case_d_wrong_professional_scope_stays_hs1_owned_by_governor(fixture, scope_field, bad):
    data, directory = fixture
    body = json.loads((directory / "cinematography.json").read_text())
    body[scope_field] = bad
    (directory / "cinematography.json").write_text(json.dumps(body))
    data.shot.content["departmentRefs"]["cinematography"]["fingerprint"] = sha256_canonical(body)
    plugin = load(fixture)
    selection = await plugin.professional_design.resolve(await query(plugin))
    assert selection.status == "CONFLICT" and any(i.code == "SCOPE_MISMATCH" for i in selection.issues)
    run = plugin.create_governed_run(work_id="work", scene_id="scene", shot_id="shot", mode=RunMode.EXPERIMENT,
        run_id="wrong-scope")
    blocked = await plugin.runtime.run(run.run_id)
    decision = plugin.gate_findings.decision(plugin.gate_findings.latest(run.run_id))
    assert blocked.state == RuntimeState.FAILED and decision.risk_families == ("HS1",)
    assert blocked.last_result.recovery_class.value == "HARD_BLOCK"
    await plugin.aclose()


async def test_determinism_source_immutability_and_large_original_has_no_selection_copy(fixture):
    data, directory = fixture
    body = json.loads((directory / "cinematography.json").read_text())
    body["content"][0]["values"]["research_notes"] = "CREATIVE OWNER ONLY " * 50000
    (directory / "cinematography.json").write_text(json.dumps(body))
    data.shot.content["departmentRefs"]["cinematography"]["fingerprint"] = sha256_canonical(body)
    originals = {p.name: p.read_bytes() for p in directory.glob("*.json")}
    canon = {n: dump_contract(getattr(data, n)) for n in ("work", "script", "episode", "scene", "shot")}
    plugin = load(fixture)
    request = await query(plugin)
    first = await plugin.professional_design.resolve(request)
    second = await plugin.professional_design.resolve(request)
    assert first == second and len(first.model_dump_json().encode()) < 2200
    assert "CREATIVE OWNER ONLY" not in first.model_dump_json() and "research_notes" not in first.model_dump_json()
    assert originals == {p.name: p.read_bytes() for p in directory.glob("*.json")}
    assert canon == {n: dump_contract(getattr(data, n)) for n in canon}
    await plugin.aclose()


async def test_existing_minimal_historical_fixture_uses_same_interface_without_dag(fixture, monkeypatch):
    # Reuse the pre-existing T2 approved fixture, whose CreativeBible wire format is HISTORICAL.
    assert all(CreativeBible.model_validate_json(p.read_text()).source_type == "HISTORICAL"
               for p in fixture[1].glob("*.json"))
    plugin = load(fixture)
    def forbidden(*args, **kwargs):
        pytest.fail("Professional authoring registry / DAG must not run in Target assembly")
    monkeypatch.setattr("drama_plugin.professional.registry", forbidden)
    monkeypatch.setattr("drama_plugin.professional.dependency_order", forbidden)
    package, run = await assembled(plugin)
    assert run.state == RuntimeState.SUCCEEDED
    assert type(plugin.professional_design) is ProfessionalDesignResolver
    assert {s.domain for s in package.sources} >= {D.CAMERA, D.DIRECTION}
    await plugin.aclose()


async def test_real_literary_s02_k02_shadow_equivalent():
    path = ROOT / "integration/professional_consolidation_shadow.py"
    spec = importlib.util.spec_from_file_location("t4_shadow", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = await module.shadow()
    assert result["fingerprintUnchanged"] and result["allReferencesIdentical"] and result["scopeIdentical"]
    assert result["professionalBibleReadCount"] < 47 and result["runtimeProfessionalInterfaceCount"] == 1
    assert result["professionalDagCalls"] == result["professionalAuthoringCalls"] == 0


def test_source_boundaries_no_legacy_names_in_assembler_runtime_governor_and_one_catalog():
    code_root = ROOT / "src/drama_plugin"
    for relative in ("production/assembler.py", "runtime/engine.py", "governance/governor.py",
                     "professional_design/resolver.py", "professional_design/contracts.py"):
        tree = ast.parse((code_root / relative).read_text())
        strings = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        assert not set(DEPARTMENT_DOMAINS) & strings
        assert "departmentRefs" not in strings
    assembler = (code_root / "production/assembler.py").read_text()
    assert "DEPARTMENT_DOMAINS" not in assembler and ".professional(" not in assembler
    resolver = (code_root / "professional_design/resolver.py").read_text()
    assert "GateDecision" not in resolver and "RuntimeState" not in resolver and "Provider" not in resolver
    adapter = (code_root / "professional_design/legacy.py").read_text()
    assert "dependency_order" not in adapter and "registry(" not in adapter and "tools.invoke" not in adapter


async def test_restored_package_validation_does_not_scan_unrelated_library(fixture, monkeypatch):
    plugin = load(fixture)
    package, _ = await assembled(plugin)
    restored = load(fixture, production_package_store=plugin.production_packages)
    original_glob = Path.glob
    def guarded_glob(path, pattern):
        if path == fixture[1] and pattern == "*.json":
            pytest.fail("Use Shot bindings for cold reference lookup, not every Bible")
        return original_glob(path, pattern)
    monkeypatch.setattr(Path, "glob", guarded_glob)
    assert (await restored.shot_assembler.validate_sources(package)).status == "READY"
    await plugin.aclose()
    await restored.aclose()
