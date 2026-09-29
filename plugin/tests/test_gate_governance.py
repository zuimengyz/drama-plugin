"""Counterexamples to default FAIL->STOP, plus Plugin-native governance and recovery."""
from __future__ import annotations

import inspect
import json

import pytest
from pydantic import ValidationError

from test_production_package import fixture, offline, load  # Reuse the unchanged T2 approved-owner fixture.
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.governance import (
    GateCategory as C, GateCode as K, GateEffect as E, GateFinding, GateGovernor,
    GateFindingStore, GovernanceInput, HardStopFamily,
)
from drama_plugin.governance.policy import WORKFLOW
from drama_plugin.runtime import ArtifactReference, RunMode, RuntimeScope, RuntimeState
from drama_plugin.runtime.engine import RuntimeEngine

SCOPE = RuntimeScope(work_id="work", scene_id="scene", shot_id="shot")
PKG = ArtifactReference(owner="production-package", artifact_ref="unit-package", version=1)
EVIDENCE = ArtifactReference(owner="unit-check", artifact_ref="evidence", version=1)


def finding(code, scope=SCOPE, required=False):
    return GateFinding.classified(code, owner="unit-source", scope=scope, evidence_ref=EVIDENCE, required=required)


@pytest.mark.parametrize("code", [K.OPTIONAL_SOURCE_MISSING, K.QUALITY_COVERAGE_RISK, K.CONTINUITY_RISK])
def test_experiment_warning_cannot_stop_even_when_delivery_quality_required(code):
    decision = GateGovernor(GateFindingStore()).govern((finding(code, required=True),),
        scope=SCOPE, mode=RunMode.EXPERIMENT, package_ref=PKG)
    assert decision.effect == E.CONTINUE and not decision.risk_families and decision.user_decision is None


@pytest.mark.parametrize("code", [K.PACKAGE_STALE, K.HASH_REFRESH, K.BINDING_REFRESH,
    K.RECEIPT_RECONCILIATION, K.CHECKPOINT_REFRESH, K.DERIVED_REFRESH, K.RETRY_BOOKKEEPING])
def test_technical_maintenance_cannot_be_user_decision(code):
    f = finding(code)
    result = GateGovernor(GateFindingStore()).govern((f,), scope=SCOPE, mode=RunMode.EXPERIMENT, package_ref=PKG)
    assert result.effect == E.AUTO_MAINTAIN and result.user_decision is None
    for category in (C.USER_DECISION, C.HARD_STOP):
        with pytest.raises(ValidationError):GateFinding.model_validate({**f.model_dump(), "category":category})


@pytest.mark.parametrize("code,family", [(K.PACKAGE_SCOPE_MISMATCH,"HS1"),
    (K.CANON_AUTHORITY_MISMATCH,"HS1"), (K.BUDGET_EXCEEDED,"HS2"), (K.COST_UNAUTHORIZED,"HS2"),
    (K.SUBMISSION_UNCERTAIN,"HS3"), (K.OPERATION_IDENTITY_MISMATCH,"HS3"),
    (K.REQUEST_INPUT_MISSING,"HS4"), (K.REQUEST_UNSUPPORTED,"HS4"), (K.PROVIDER_HARD_LIMIT,"HS4")])
def test_only_four_real_risk_families_own_hard_stop(code, family):
    result = GateGovernor(GateFindingStore()).govern((finding(code),), scope=SCOPE,
        mode=RunMode.EXPERIMENT, package_ref=PKG)
    assert result.effect == E.BLOCK and result.risk_families == (family,)
    assert len(C) == 6 and len(HardStopFamily) == 4


@pytest.mark.parametrize("mode", list(RunMode))
def test_capability_absence_is_not_ordinary_failed_validation(mode):
    governor = GateGovernor(GateFindingStore())
    required = governor.govern((finding(K.CAPABILITY_NOT_IMPLEMENTED, required=True),),
        scope=SCOPE, mode=mode, package_ref=PKG)
    optional = governor.govern((finding(K.CAPABILITY_NOT_IMPLEMENTED),), scope=SCOPE, mode=mode, package_ref=PKG)
    assert required.effect == E.CAPABILITY_ABSENT and not required.risk_families
    assert optional.effect == E.CONTINUE and optional.finding_refs


def test_production_quality_review_is_not_a_fifth_hard_stop_or_user_approval():
    result = GateGovernor(GateFindingStore()).govern((finding(K.QUALITY_COVERAGE_RISK, required=True),),
        scope=SCOPE, mode=RunMode.PRODUCTION, package_ref=PKG)
    assert result.effect == E.REVIEW_REQUIRED and not result.risk_families and result.user_decision is None


def test_legacy_guard_never_becomes_artistic_decision_and_scope_cannot_hide_in_warning():
    governor = GateGovernor(GateFindingStore())
    legacy = governor.govern((finding(K.LEGACY_ENTRY_REJECTED), finding(K.ART_APPROVAL_REQUIRED)),
        scope=SCOPE, mode=RunMode.EXPERIMENT, package_ref=PKG)
    assert legacy.effect == E.LEGACY_REJECT and legacy.user_decision is None
    wrong = governor.govern((finding(K.QUALITY_COVERAGE_RISK, scope=RuntimeScope(work_id="other")),),
        scope=SCOPE, mode=RunMode.EXPERIMENT, package_ref=PKG)
    assert wrong.effect == E.BLOCK and wrong.risk_families == ("HS1",)


def test_finding_immutable_extra_rejection_no_unknown_stop_code_or_risk():
    f = finding(K.PACKAGE_STALE)
    with pytest.raises(ValidationError):f.owner="other"
    for extra in ("details","metadata","context"):
        with pytest.raises(ValidationError):GateFinding.model_validate({**f.model_dump(),extra:{"body":"forbidden"}})
    with pytest.raises(ValidationError):GateFinding.model_validate({**f.model_dump(),"code":"NEW_STOP_GATE"})
    with pytest.raises(ValidationError):GateFinding.model_validate({**finding(K.REQUEST_INPUT_MISSING).model_dump(),"risk_family":"HS5"})


async def start(plugin, *, mode=RunMode.EXPERIMENT, package_ref=None, findings=(), name="governed"):
    run = plugin.create_governed_run(work_id="work",scene_id="scene",shot_id="shot",
        mode=mode,run_id=name,package_ref=package_ref,
        finding_refs=tuple(plugin.gate_findings.put_finding(f) for f in findings))
    return await plugin.runtime.run(run.run_id)


@pytest.mark.parametrize("mode", list(RunMode))
async def test_native_governed_e2e_default_scope_only_no_canon_or_legacy_execution(fixture, monkeypatch, mode):
    plugin=load(fixture); data=fixture[0]
    before={n:dump_contract(getattr(data,n)) for n in ("work","scene","shot")}
    async def forbidden(*args,**kwargs):pytest.fail("No old entry, Provider, or Canon mutation")
    monkeypatch.setattr(plugin.runtime.executor.legacy,"execute",forbidden)
    monkeypatch.setattr(plugin.providers.production,"generate_image",forbidden)
    monkeypatch.setattr(plugin.providers.production,"generate_video",forbidden)
    done=await start(plugin,mode=mode,findings=(finding(K.QUALITY_COVERAGE_RISK),))
    assert done.state==RuntimeState.SUCCEEDED and done.last_result.artifact_refs[0].owner=="production-package"
    assert plugin.gate_findings.decision(plugin.gate_findings.latest(done.run_id)).effect==E.CONTINUE
    assert before=={n:dump_contract(getattr(data,n)) for n in before}
    snapshot=plugin.runtime.serialize(done.run_id)
    assert "findingRefs" not in snapshot and "CANON TEXT" not in snapshot and "quality" not in snapshot
    assert plugin.gate_governor.role=="POLICY_VALIDATION_GOVERNANCE"
    await plugin.aclose()


async def test_actual_package_stale_auto_reassembles_once_without_host_user_or_owner_write(fixture, monkeypatch):
    plugin=load(fixture); first=await start(plugin,name="first")
    old=first.last_result.artifact_refs[0];data,directory=fixture
    body=json.loads((directory/"cinematography.json").read_text());body["version"]=2
    body["content"][0]["values"]["perspective"]="LEGAL OWNER NEW VERSION"
    (directory/"cinematography.json").write_text(json.dumps(body))
    data.shot.content["departmentRefs"]["cinematography"]["fingerprint"]=sha256_canonical(body)
    before=data.shot.model_dump_json();count=0;original=plugin.shot_assembler.assemble
    async def count_assembly(*args,**kwargs):
        nonlocal count;count+=1;return await original(*args,**kwargs)
    monkeypatch.setattr(plugin.shot_assembler,"assemble",count_assembly)
    done=await start(plugin,package_ref=old,name="stale")
    assert done.state==RuntimeState.SUCCEEDED and count==1
    assert done.last_result.artifact_refs[0]!=old and plugin.production_packages.get(old)
    assert plugin.gate_findings.maintenance_count(done.run_id)==1 and data.shot.model_dump_json()==before
    assert json.loads((directory/"cinematography.json").read_text())==body
    await plugin.aclose()


@pytest.mark.parametrize("code,state,effect", [(K.PACKAGE_SCOPE_MISMATCH,"BLOCKED",E.BLOCK),
    (K.SUBMISSION_UNCERTAIN,"BLOCKED",E.BLOCK),(K.CAPABILITY_NOT_IMPLEMENTED,"WAITING_EXTERNAL",E.CAPABILITY_ABSENT),
    (K.LEGACY_ENTRY_REJECTED,"FAILED",E.LEGACY_REJECT),(K.QUALITY_COVERAGE_RISK,"WAITING_EXTERNAL",E.REVIEW_REQUIRED)])
async def test_runtime_routes_effects_instead_of_generic_gate_failed(fixture,code,state,effect):
    plugin=load(fixture)
    mode=RunMode.PRODUCTION if effect==E.REVIEW_REQUIRED else RunMode.EXPERIMENT
    done=await start(plugin,mode=mode,findings=(finding(code,required=True),))
    assert done.state==state and plugin.gate_findings.decision(plugin.gate_findings.latest(done.run_id)).effect==effect
    if effect==E.BLOCK:
        with pytest.raises(ValueError,match="replay-safe"):await plugin.runtime.retry(done.run_id)
    if effect in {E.CAPABILITY_ABSENT,E.REVIEW_REQUIRED}:
        assert done.last_result.external_ref.owner==("capability-absence" if effect==E.CAPABILITY_ABSENT else "quality-review")
    await plugin.aclose()


async def test_genuine_user_decision_and_restore_reuses_foundation_boundary(fixture):
    plugin=load(fixture)
    waiting=await start(plugin,findings=(finding(K.ART_APPROVAL_REQUIRED),))
    assert waiting.state==RuntimeState.WAITING_USER
    restored=load(fixture,production_package_store=plugin.production_packages,gate_finding_store=plugin.gate_findings)
    restored.runtime.restore(plugin.runtime.serialize(waiting.run_id))
    await restored.runtime.decide(waiting.run_id,decision_id=restored.runtime.decision_id(waiting.run_id),
        accepted=True,decision_ref=ArtifactReference(owner="user-decision",artifact_ref="approved-v1"))
    done=await restored.runtime.run(waiting.run_id)
    assert done.state==RuntimeState.SUCCEEDED and done.last_result.artifact_refs[0].owner=="production-package"
    await plugin.aclose();await restored.aclose()


async def test_unimplemented_maintenance_reports_absence_never_user_or_silent_continue(fixture):
    plugin=load(fixture)
    done=await start(plugin,findings=(finding(K.RECEIPT_RECONCILIATION),))
    assert done.state==RuntimeState.WAITING_EXTERNAL and done.last_result.external_ref.owner=="capability-absence"
    decision=plugin.gate_findings.decision(plugin.gate_findings.latest(done.run_id))
    assert decision.effect==E.CAPABILITY_ABSENT and decision.user_decision is None
    await plugin.aclose()


def test_runtime_engine_has_no_gate_semantics_and_governor_has_no_creative_operations():
    engine=inspect.getsource(RuntimeEngine)
    assert not any(text in engine for text in ("GateCode","GateCategory","GateGovernor","PACKAGE_STALE","LIGHTING","ProductionPackage"))
    governor=inspect.getsource(GateGovernor)
    assert not any(text in governor for text in ("ShotAssembler","generate_video","generate_image","update_work","prompt_ir"))


def test_uncertain_charge_is_not_hidden_as_receipt_maintenance_and_explanations_are_specific():
    governor=GateGovernor(GateFindingStore())
    decision=governor.govern((finding(K.RECEIPT_RECONCILIATION),finding(K.SUBMISSION_UNCERTAIN)),
        scope=SCOPE,mode=RunMode.EXPERIMENT,package_ref=PKG)
    assert decision.effect==E.BLOCK and decision.risk_families==("HS3",)
    assert any("重复收费" in message and "HS3" in message for message in governor.explain(decision))


async def test_stale_checkpoint_restore_repairs_once_and_missing_author_pin_is_not_auto_written(fixture,monkeypatch):
    plugin=load(fixture);done=await start(plugin,name="original");old=done.last_result.artifact_refs[0]
    data,directory=fixture;body=json.loads((directory/"cinematography.json").read_text());body["version"]=2
    (directory/"cinematography.json").write_text(json.dumps(body))
    # The author has not refreshed the Shot pin. Maintenance must not impersonate the author.
    run=plugin.runtime.create_run(work_id="work",scene_id="scene",shot_id="shot",mode=RunMode.EXPERIMENT,
        workflow_id=WORKFLOW,run_id="stale-no-pin")
    plugin.gate_findings.bind(run.run_id,GovernanceInput(package_ref=old))
    checked=await plugin.runtime.run(run.run_id,max_ticks=2)
    assert checked.cursor==1 and checked.state==RuntimeState.READY
    restored=load(fixture,production_package_store=plugin.production_packages,gate_finding_store=plugin.gate_findings)
    restored.runtime.restore(plugin.runtime.serialize(run.run_id))
    original=data.shot.model_dump_json()
    blocked=await restored.runtime.run(run.run_id)
    assert blocked.state==RuntimeState.BLOCKED and blocked.last_result.code=="TECHNICAL_MAINTENANCE_EXHAUSTED"
    assert data.shot.model_dump_json()==original and restored.gate_findings.maintenance_count(run.run_id)==1
    assert restored.gate_findings.decision(restored.gate_findings.latest(run.run_id)).user_decision is None
    await plugin.aclose();await restored.aclose()


@pytest.mark.parametrize("code,category", [(K.ART_APPROVAL_REQUIRED,"ART_APPROVAL"),
    (K.COST_APPROVAL_REQUIRED,"COST_APPROVAL"),(K.MAJOR_ADAPTATION_REQUIRED,"MAJOR_ADAPTATION"),
    (K.ADOPTION_REQUIRED,"ADOPTION"),(K.FINAL_ACCEPTANCE_REQUIRED,"FINAL_ACCEPTANCE")])
def test_only_five_real_user_decision_categories(code,category):
    result=GateGovernor(GateFindingStore()).govern((finding(code),),scope=SCOPE,
        mode=RunMode.EXPERIMENT,package_ref=PKG)
    assert result.effect==E.WAIT_USER and result.user_decision.category==category


@pytest.mark.parametrize("mode",list(RunMode))
def test_art_approval_cannot_silently_approve_an_unrelated_cost_decision(mode):
    result=GateGovernor(GateFindingStore()).govern((finding(K.ART_APPROVAL_REQUIRED),finding(K.COST_APPROVAL_REQUIRED)),
        scope=SCOPE,mode=mode,package_ref=PKG)
    assert result.effect==E.CAPABILITY_ABSENT and result.user_decision is None


async def test_bad_canon_scope_does_not_create_a_second_derived_missing_package_hard_stop(fixture):
    fixture[0].shot.scene_id="wrong-scene"
    plugin=load(fixture);blocked=await start(plugin)
    decision=plugin.gate_findings.decision(plugin.gate_findings.latest(blocked.run_id))
    assert blocked.state==RuntimeState.BLOCKED and decision.risk_families==("HS1",)
    await plugin.aclose()
