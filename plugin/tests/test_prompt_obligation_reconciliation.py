"""T5R reviewed execution bindings, source authority and same-task parity."""
import importlib.util
import inspect
import json
from pathlib import Path
import socket

import pytest
from pydantic import ValidationError

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.media import Media
from drama_plugin.generation.contracts import GenerationTask, PromptCoverage, PromptIR, FinalPromptArtifact
from drama_plugin.generation.checks import execution_findings
from drama_plugin.governance.contracts import GateCategory, HardStopFamily, GateEffect
from drama_plugin.production.contracts import SourceOwner, SourceReference, DomainReference, ProductionPackage, PackageContent
from drama_plugin.production.references import ReferenceExecutionBinding, ReferenceExecutionStore
from drama_plugin.runtime import RuntimeScope, RuntimeState, RunMode
from test_prompt_audio_convergence import generation_fixture, fixture, load, prepare, artifacts

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("t5r_shadow",ROOT/"integration/prompt_obligation_reconciliation_shadow.py")
audit_module=importlib.util.module_from_spec(spec); spec.loader.exec_module(audit_module)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*a,**k):pytest.fail("T5R forbids network, media generation and old compilation")
    monkeypatch.setattr(socket.socket,"connect",forbidden);monkeypatch.setattr(socket.socket,"connect_ex",forbidden)
    monkeypatch.setattr("drama_plugin.plugin.load_config",lambda _:DramaPluginConfig())
    monkeypatch.setattr("drama_plugin.professional.compile_prompt_projection",forbidden)
    monkeypatch.setattr("drama_plugin.hosts.cinematic_projection.project",forbidden)
    monkeypatch.setattr("drama_plugin.visual.video_prompt.compile_request_ir",forbidden)


@pytest.fixture
def bound_fixture(generation_fixture):
    data,_=generation_fixture
    media=Media(id="unit-image",work_id="work",shot_id="shot",media_type="IMAGE",source_ref="unit:retained",
        content_hash="a"*64,mime_type="image/png",file_size=123)
    data.media=[media]
    proof=SourceReference(owner=SourceOwner.PROFESSIONAL,artifact_ref="unit-reviewed-input",version=1,fingerprint="b"*64)
    binding=ReferenceExecutionBinding(binding_id="opening",version=1,
        scope=RuntimeScope(work_id="work",scene_id="scene",shot_id="shot"),
        media=dict(media_id=media.id,version="1",content_hash=media.content_hash,kind="image",
            semantics=("identity","costume","continuity"),review_ref="unit-review:approved"),
        duties=(dict(role="CHARACTER",necessity="REQUIRED",subject="A+B",purpose="Fixture identity"),
                dict(role="COMPOSITION",necessity="REQUIRED",subject="shot opening",purpose="Fixture opening",establishes_opening_state=True)),
        subject_ids=("A","B"),role="FIRST_FRAME",endpoint_state=data.shot.content["visualEntryState"],
        authorization_scope="REVIEWED_TRIAL_INPUT",authority_refs=(proof,))
    store=ReferenceExecutionStore();store.register(binding)
    return generation_fixture,store,binding


def bound_load(bound_fixture):
    f,store,_=bound_fixture
    return load(f,reference_execution_store=store)


async def diagnostics(plugin, package_ref, task):
    result=await plugin.prompt_compiler.compile(package_ref,task)
    values=plugin.generation_artifacts.diagnostics(result.diagnostics_ref)
    findings=execution_findings(values,scope=RuntimeScope(work_id="work",scene_id="scene",shot_id="shot"),evidence_ref=result.diagnostics_ref)
    return result,values,findings


@pytest.mark.parametrize("mode",list(RunMode))
async def test_default_scope_entry_same_task_mode_and_reused_generator(bound_fixture,monkeypatch,mode):
    plugin=bound_load(bound_fixture);calls=[];original=plugin.prompt_compiler.generator.generate
    def generate(*a,**k):calls.append(k);return original(*a,**k)
    monkeypatch.setattr(plugin.prompt_compiler.generator,"generate",generate)
    monkeypatch.setattr(plugin.providers.media,"list_media",lambda **k:pytest.fail("No library scan"))
    monkeypatch.setattr(plugin.providers.production,"generate_video",lambda **k:pytest.fail("No Provider"))
    run=await prepare(plugin,mode=mode)
    assert run.state==RuntimeState.SUCCEEDED
    final,audio,ready=artifacts(plugin,run)
    assert final.task.input_mode=="image_to_video" and len(calls)==1
    assert "@图片1" in final.prompt_text and "作为首帧" in final.prompt_text
    assert "<主体1>与<主体2>" in final.prompt_text
    coverage=plugin.generation_artifacts.get(final.coverage_ref,PromptCoverage)
    claims=[e for e in coverage.entries if e.status=="REFERENCE_COVERED"]
    assert len(claims)==2 and all(e.input_ref.artifact_ref=="unit-image" for e in claims)
    assert len(final.execution_reference_refs)==1 and not ready.provider_submission_allowed
    assert audio.speech_events[0].window_ms is None


async def test_real_r15_media_hash_and_authorized_binding():
    context,binding,metadata,audit=audit_module.reconcile()
    assert binding.media.media_id==metadata.id=="media_dcd4a48b4c3448cb8509ced5a72fadd2"
    assert binding.media.content_hash==metadata.content_hash==audit["mediaHash"]
    assert audit["localHashVerified"] and audit["actualOldMode"]=="image_to_video"
    assert {d.role for d in binding.duties}=={"CHARACTER","COMPOSITION"}
    assert binding.authorization_scope=="REVIEWED_TRIAL_INPUT"
    assert len(binding.authority_refs)==4 and binding.media.prompt_binding is None


async def test_real_same_task_shadow_and_required_parity(tmp_path):
    result=await audit_module.shadow(tmp_path)
    assert result["actualOldMode"]==result["targetMode"]=="image_to_video"
    assert result["requiredUnresolved"]==0 and result["coverageCounts"]["REFERENCE_COVERED"]==2
    assert result["generatorCalls"]==1 and result["recoverySameRefs"] and result["canonUnchanged"]
    parity=json.loads((tmp_path/"T5R-FORMAL_REQUIRED_OBLIGATION_SET.json").read_text())
    assert len(parity["obligations"])>25 and all(x["classification"] in {"AUTHORITATIVE","DERIVED_APPROVED"} for x in parity["obligations"])


@pytest.mark.parametrize("corruption",["wrong_subject","wrong_media_work","wrong_media_shot","wrong_endpoint"])
async def test_wrong_binding_identity_is_hs1(bound_fixture,corruption):
    fixture,store,binding=bound_fixture
    if corruption=="wrong_subject":
        store.register(binding.model_copy(update={"version":2,"subject_ids":("A","UNKNOWN")}))
    elif corruption=="wrong_endpoint":
        store.register(binding.model_copy(update={"version":2,"endpoint_state":"Other shot start"}))
    else:
        key="work_id" if corruption=="wrong_media_work" else "shot_id"
        fixture[0].media[0]=fixture[0].media[0].model_copy(update={key:"other"})
    plugin=bound_load(bound_fixture);run=await prepare(plugin)
    assert run.state==RuntimeState.FAILED
    decision=plugin.gate_findings.decision(plugin.gate_findings.latest(run.run_id))
    assert any(plugin.gate_findings.finding(r).risk_family==HardStopFamily.HS1 for r in decision.finding_refs)


@pytest.mark.parametrize("corruption",["missing","hash_missing","identity_semantics_missing"])
async def test_required_media_pending_waits_exact_identity_and_invalid_media_is_hs4(bound_fixture,corruption):
    f,store,binding=bound_fixture
    if corruption=="missing":f[0].media=[]
    elif corruption=="hash_missing":f[0].media[0]=f[0].media[0].model_copy(update={"content_hash":None})
    else:store.register(binding.model_copy(update={"version":2,"media":binding.media.model_copy(update={"semantics":("continuity",)})}))
    plugin=bound_load(bound_fixture);run=await prepare(plugin)
    decision=plugin.gate_findings.decision(plugin.gate_findings.latest(run.run_id))
    if corruption=="missing":
        assert run.state==RuntimeState.WAITING_EXTERNAL
        assert run.last_result.external_ref.artifact_ref==binding.media.media_id
        assert run.last_result.recovery_class.value=="WAIT_EXTERNAL"
        assert not decision.risk_families
    else:
        assert run.state==RuntimeState.FAILED and run.last_result.recovery_class.value=="HARD_BLOCK"
        assert any(plugin.gate_findings.finding(r).risk_family==HardStopFamily.HS4 for r in decision.finding_refs)


async def test_stale_reviewed_binding_auto_reassembles_without_user(bound_fixture,monkeypatch):
    f,store,binding=bound_fixture;plugin=bound_load(bound_fixture)
    first=await prepare(plugin);final,_,_=artifacts(plugin,first)
    effects=[];govern=plugin.gate_governor.govern
    def record(*a,**k):decision=govern(*a,**k);effects.append(decision.effect);return decision
    monkeypatch.setattr(plugin.gate_governor,"govern",record)
    store.register(binding.model_copy(update={"version":2}))
    second=await prepare(plugin,run_id="stale-binding",package_ref=final.source_package_ref)
    assert second.state==RuntimeState.SUCCEEDED and GateEffect.AUTO_MAINTAIN in effects
    new,_,_=artifacts(plugin,second)
    assert new.source_package_ref!=final.source_package_ref and new.execution_reference_refs[0].version==2
    assert all(e!=GateEffect.WAIT_USER for e in effects)


async def test_changed_media_bytes_are_auto_but_never_auto_approved(bound_fixture):
    f,_,binding=bound_fixture;plugin=bound_load(bound_fixture)
    run=await prepare(plugin);ref=artifacts(plugin,run)[0].source_package_ref
    f[0].media[0]=f[0].media[0].model_copy(update={"content_hash":"c"*64})
    result,values,findings=await diagnostics(plugin,ref,GenerationTask(input_mode="image_to_video"))
    assert result.preparation_ref is None
    assert any(d.code=="PACKAGE_STALE" for d in values)
    assert any(f.category==GateCategory.AUTO_MAINTENANCE for f in findings)
    assert binding.media.content_hash=="a"*64


async def test_optional_reference_missing_warns_and_experiment_continues(bound_fixture):
    _,store,binding=bound_fixture
    optional=binding.model_copy(update={"binding_id":"optional","role":"REFERENCE","endpoint_state":None,
        "media":binding.media.model_copy(update={"media_id":"optional-missing"}),
        "duties":(binding.duties[0].model_copy(update={"necessity":"PREFERRED"}),)})
    store.register(optional)
    plugin=bound_load(bound_fixture);run=await prepare(plugin)
    assert run.state==RuntimeState.SUCCEEDED
    decision=plugin.gate_findings.decision(plugin.gate_findings.latest(run.run_id))
    assert any(plugin.gate_findings.finding(r).category==GateCategory.WARNING for r in decision.finding_refs)


async def test_design_reference_is_not_execution_media(generation_fixture):
    plugin=load(generation_fixture);run=await prepare(plugin);ref=artifacts(plugin,run)[0].source_package_ref
    result,_,findings=await diagnostics(plugin,ref,GenerationTask(input_mode="image_to_video"))
    assert result.preparation_ref is None and any(f.risk_family==HardStopFamily.HS4 for f in findings)


async def test_reference_mode_with_reviewed_media(bound_fixture):
    _,store,binding=bound_fixture
    # Explicit source revision chooses reference, not a Compiler override.
    store.register(binding.model_copy(update={"version":2,"role":"REFERENCE","endpoint_state":None,
        "duties":(binding.duties[0],)}))
    plugin=bound_load(bound_fixture);run=await prepare(plugin)
    assert run.state==RuntimeState.SUCCEEDED and artifacts(plugin,run)[0].task.input_mode=="reference"


@pytest.mark.parametrize("field,value",[("temporary_url","https://signed.invalid/input"),("provider_slot",3),("prompt","@图片1")])
def test_binding_rejects_provider_and_unbounded_fields(bound_fixture,field,value):
    binding=bound_fixture[2]
    with pytest.raises(ValidationError):ReferenceExecutionBinding.model_validate({**binding.model_dump(),field:value})


def test_reused_media_and_duty_contracts_are_immutable(bound_fixture):
    binding=bound_fixture[2]
    for obj,field,value in [(binding,"role","REFERENCE"),(binding.media,"content_hash","f"*64),(binding.duties[0],"subject","UNKNOWN")]:
        with pytest.raises(ValidationError):setattr(obj,field,value)
    with pytest.raises(ValueError):bound_fixture[1].register(binding.model_copy(update={"endpoint_state":"changed"}))


def test_nested_temporary_urls_and_data_payloads_cannot_enter_binding(bound_fixture):
    original=bound_fixture[2].model_dump()
    for kind in ("media_data", "evidence_url", "provider_label"):
        value=json.loads(json.dumps(original))
        if kind=="media_data":value["media"]["media_id"]="data:image/png;base64,AAA"
        elif kind=="evidence_url":value["authority_refs"][0]["artifact_ref"]="https://signed.invalid/temporary"
        else:value["media"]["review_ref"]="@视频1"
        with pytest.raises(ValidationError):ReferenceExecutionBinding.model_validate(value)


@pytest.mark.parametrize("case",["media_bytes","temporary_url","old_history","unrelated_1000"])
async def test_package_complexity_identity_and_no_media_scan(bound_fixture,monkeypatch,case):
    f,store,binding=bound_fixture;plugin=bound_load(bound_fixture)
    first=await prepare(plugin);final,audio,_=artifacts(plugin,first)
    original=plugin.production_packages.get(final.source_package_ref)
    if case=="media_bytes":f[0].media[0].content["bytes"]="NEVER_COPY_MEDIA_BYTES"*100000
    elif case=="temporary_url":f[0].media[0].content["url"]="https://signed.invalid/?rotating-token=never-hash"
    elif case=="old_history":
        for key in ("productionHistory","productionStage","productionRoute","promptHistory"):
            f[0].work.content[key]={"unrelatedHistory":["NEVER_COPY_OLD_HISTORY"*10000]*3}
    else:
        for i in range(1000):
            scope=RuntimeScope(work_id="work",scene_id="scene",shot_id=f"other-{i}")
            store.register(binding.model_copy(update={"scope":scope}))
    monkeypatch.setattr(plugin.providers.media,"list_media",lambda **k:pytest.fail("No library scan"))
    second=await prepare(plugin,run_id="complexity")
    new,new_audio,_=artifacts(plugin,second)
    assert new.source_package_ref==final.source_package_ref and new==final and new_audio==audio
    package=plugin.production_packages.get(new.source_package_ref)
    assert package==original and "NEVER_COPY" not in package.model_dump_json()
    assert "@图片" not in package.model_dump_json() and "signed.invalid" not in package.model_dump_json()


def test_timing_and_instruction_authority_classification_and_exclusion():
    _,_,_,audit=audit_module.reconcile()
    assert audit["dialogueTiming"]["classification"]=="LEGACY_DERIVED" and not audit["dialogueTiming"]["promotedToCanon"]
    assert {x["classification"] for x in audit["visualVoiceInstructions"]}<={"AUTHORITATIVE","DERIVED_APPROVED","LEGACY_DERIVED","OBSOLETE"}
    assert len(audit["visualVoiceInstructions"])==31 and not audit["legacyDerivedInstructionsPromoted"]
    assert all(x["targetDisposition"]=="EXCLUDED_FROM_REQUIRED_PARITY" for x in audit["visualVoiceInstructions"] if x["classification"]=="LEGACY_DERIVED")


async def test_final_excludes_old_projection_window_and_instructions(tmp_path):
    await audit_module.shadow(tmp_path)
    text=(tmp_path/"T5R-S02-K02-Target-FinalPrompt.txt").read_text()
    assert "2–6.2" not in text and "先抓住再请求" not in text and "无故作可怜鼻音" not in text
    audio=json.loads((tmp_path/"T5R-AudioExecutionPlan.json").read_text())
    assert audio["speechEvents"][0]["windowMs"] is None


async def test_model_reference_mode_unsupported_is_hs4(bound_fixture,monkeypatch):
    plugin=bound_load(bound_fixture);run=await prepare(plugin);ref=artifacts(plugin,run)[0].source_package_ref
    from importlib import import_module
    module=import_module("drama_plugin.providers.video.registry");original=module.registry
    def catalog():
        value=json.loads(json.dumps(original()));value["models"]["seedance-2-standard"]["input_modes"]=["text_to_video"];return value
    monkeypatch.setattr(module,"registry",catalog)
    result,_,findings=await diagnostics(plugin,ref,GenerationTask(input_mode="image_to_video"))
    assert result.preparation_ref is None and any(f.risk_family==HardStopFamily.HS4 for f in findings)


def test_compiler_contains_no_legacy_audit_or_library_lookup():
    from drama_plugin.generation.compiler import PromptCompiler
    source=inspect.getsource(PromptCompiler)
    for forbidden in ("K02-spec", "K02-frozen", "CinematicShotSpec", "VideoRequest", "provider-prompt", "list_media", "read_text"):
        assert forbidden not in source


async def test_wrong_shot_binding_in_package_is_hs1(bound_fixture):
    f,store,binding=bound_fixture;plugin=bound_load(bound_fixture)
    first=await prepare(plugin);package=plugin.production_packages.get(artifacts(plugin,first)[0].source_package_ref)
    foreign=binding.model_copy(update={"scope":RuntimeScope(work_id="work",scene_id="scene",shot_id="wrong-shot")})
    ref=store.register(foreign)
    selections=[s for s in package.sources if not s.reference.artifact_ref.startswith("execution-reference:")]
    selections.append(DomainReference(domain="REFERENCE",reference=ref))
    selections.sort(key=lambda s:(s.domain,s.reference.owner,s.reference.artifact_ref,s.reference.path,s.use))
    wrong=ProductionPackage.freeze(PackageContent.model_validate({
        **package.model_dump(exclude={"fingerprint","package_id"}),"sources":tuple(selections)}))
    result,_,findings=await diagnostics(plugin,plugin.production_packages.put(wrong),GenerationTask(input_mode="image_to_video"))
    assert result.preparation_ref is None and any(f.risk_family==HardStopFamily.HS1 for f in findings)


async def test_reference_kind_and_content_hash_change_fingerprint(bound_fixture):
    _,store,binding=bound_fixture
    original=binding.source().reference()
    changed=binding.model_copy(update={"version":2,"media":binding.media.model_copy(update={"content_hash":"f"*64})})
    assert store.register(changed).fingerprint!=original.fingerprint


async def test_real_missing_media_cannot_claim_reference_coverage(bound_fixture):
    f,_,_=bound_fixture;plugin=bound_load(bound_fixture);first=await prepare(plugin)
    ref=artifacts(plugin,first)[0].source_package_ref
    f[0].media=[]
    result,_,_=await diagnostics(plugin,ref,GenerationTask(input_mode="image_to_video"))
    assert result.preparation_ref is None  # Cached final must not bypass current media validation.


async def test_last_boundary_optional_reference_warning_continues(bound_fixture):
    _,store,binding=bound_fixture
    store.register(binding.model_copy(update={"binding_id":"optional","role":"REFERENCE","endpoint_state":None,
        "duties":(binding.duties[0].model_copy(update={"necessity":"PREFERRED"}),)}))
    plugin=bound_load(bound_fixture);run=await prepare(plugin)
    assert run.state==RuntimeState.SUCCEEDED


async def test_first_last_uses_authored_end_state_refs(bound_fixture):
    f,store,binding=bound_fixture
    last=binding.model_copy(update={"binding_id":"last","role":"LAST_FRAME",
        "endpoint_state":f[0].shot.content["visualExitState"],
        "media":binding.media.model_copy(update={"media_id":"unit-last"}),
        "duties":(binding.duties[0].model_copy(update={"role":"CONTINUITY","subject":"shot end"}),)})
    f[0].media.append(f[0].media[0].model_copy(update={"id":"unit-last"}));store.register(last)
    plugin=bound_load(bound_fixture);run=await prepare(plugin)
    assert run.state==RuntimeState.SUCCEEDED
    final,_,_=artifacts(plugin,run)
    assert final.task.input_mode=="first_last_frame" and len(final.execution_reference_refs)==2
    assert "作为首帧" in final.prompt_text and "作为尾帧" in final.prompt_text


async def test_formal_parity_detects_missing_source_receipt(tmp_path):
    await audit_module.shadow(tmp_path)
    package=ProductionPackage.model_validate_json((tmp_path/"T5R-ProductionPackage.json").read_text())
    coverage=PromptCoverage.model_validate_json((tmp_path/"T5R-Coverage.json").read_text())
    ir=PromptIR.model_validate_json((tmp_path/"T5R-PromptIR.json").read_text())
    from drama_plugin.generation.contracts import AudioExecutionPlan
    plan=AudioExecutionPlan.model_validate_json((tmp_path/"T5R-AudioExecutionPlan.json").read_text())
    context,binding,media,_=audit_module.reconcile()
    from drama_plugin.contracts.creation import Work,Script,Episode,Scene,Shot
    from drama_plugin.providers.mock import MockDramaData
    data=MockDramaData.empty()
    for key,model in (("work",Work),("script",Script),("episode",Episode),("scene",Scene),("shot",Shot)):setattr(data,key,model.model_validate(context[key]))
    data.media=[media];store=ReferenceExecutionStore();store.register(binding)
    plugin=DramaPlugin.load(ROOT,mock_data=data,legacy_reads=True, production_artifact_roots=(audit_module.PROJECT/"S02-design",),reference_execution_store=store)
    selected=await plugin.prompt_compiler.reader.selections(package)
    incomplete=coverage.model_copy(update={"entries":tuple(e for e in coverage.entries if e.domain!="LIGHTING")})
    with pytest.raises(AssertionError):audit_module.formal_required(package,ir,incomplete,plan,binding,selected,plugin.prompt_compiler.reader.dependencies)
