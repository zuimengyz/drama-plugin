"""T5R one-time source reconciliation + Package-only same-mode offline shadow.

Historical files are read ONLY by this migration audit before Runtime starts.
No migration evidence table becomes a Runtime owner. No Canon/media writes.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import hashlib
import json
from pathlib import Path
import socket
from unittest.mock import patch

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.creation import Work, Script, Episode, Scene, Shot
from drama_plugin.contracts.media import Media
from drama_plugin.generation.contracts import AudioExecutionPlan, FinalPromptArtifact, GenerationPreparation, GenerationTask, PromptIR, PromptCoverage
from drama_plugin.production.contracts import SourceOwner, SourceReference
from drama_plugin.production.references import ReferenceExecutionBinding, ReferenceExecutionStore
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.runtime import ArtifactReference, RuntimeScope, RunMode, RuntimeState

PLUGIN = Path(__file__).resolve().parents[1]
PROJECT = PLUGIN.parents[1] / "artifacts/flagship-literary-film-01/test-shoot-01"


def read(file):
    return json.loads(file.read_text())


def reconcile(project: Path = PROJECT):
    """Reconcile retained/reviewed assembly sources, never a VideoRequest contract.

    VideoReference / ReferenceRequirement are reused. R15 is trial approved,
    not final-film adoption. The old 2–6.2s estimate is deliberately excluded.
    """
    context = read(project / "S02-cinematic/K02-context.json")
    scope = RuntimeScope(work_id=context["work"]["id"], scene_id=context["scene"]["id"], shot_id=context["shot"]["id"])
    retained = read(project / "S02-inputs/K02-r15-retention.json")
    review = read(project / "S02-inputs/K02-r15-review.json")
    synced = read(project / "S02-inputs/K02-r15-review-synced.json")["result"]
    identity = read(project / "S02-inputs/r12-shared-reference-asset.json")
    prepared = read(project / "S02-video/K02-prepared.json")
    frozen = read(project / "S02-cinematic/K02-frozen.json")
    dispatch = read(project / "S02-video/K02-dispatch-ready-r15.json")
    assert prepared["requirements"]["mode"] == "SINGLE_IMAGE"
    assert dispatch["request"]["name"] == "api_vidu_q3_image_to_video"
    media_id, media_hash = retained["mediaId"], retained["contentHash"]
    image = project / "S02-inputs/K02-r15.png"
    assert hashlib.sha256(image.read_bytes()).hexdigest() == media_hash == review["output_hash"]
    assert synced["mediaId"] == media_id and synced["review"] == "PASS_WITH_NOTES"
    assert identity["content"]["approval"]["status"] == "USER_APPROVED"
    assert "trial" in review["evidence"] and "not final user adoption" in review["evidence"]
    assert retained["workId"] == scope.work_id and retained["shotId"] == scope.shot_id
    assert frozen["state"] == "CINEMATIC_DIRECTION_FROZEN" and frozen["hostReview"]
    old_input = prepared["requirements"]["inputs"][0]
    assert old_input["media_id"] == media_id and old_input["content_hash"] == media_hash
    assert old_input["role"] == "FIRST_FRAME"
    assert old_input["endpoint_state"] == context["shot"]["content"]["visualEntryState"]
    duties = frozen["spec"]["referenceRequirements"]
    assert [(d["role"],d["subject"],d["purpose"]) for d in duties] == [
        (d["role"],d["subject"],d["purpose"]) for d in prepared["requirements"]["reference_duties"]]
    def pin(name, value):
        return SourceReference(owner=SourceOwner.PROFESSIONAL, artifact_ref="migration-evidence:" + name,
            version=1, fingerprint=sha256_canonical(value))
    binding = ReferenceExecutionBinding(binding_id="opening-r15", version=1, scope=scope,
        media=dict(media_id=media_id, version="R15", content_hash=media_hash, kind="image",
            semantics=("identity", "costume", "environment", "continuity"), width=1280, height=720,
            review_ref="review:" + synced["reviewHash"]), duties=tuple(duties),
        subject_ids=("C_MAN", "C_GIRL"), role="FIRST_FRAME", endpoint_state=old_input["endpoint_state"],
        authorization_scope="REVIEWED_TRIAL_INPUT", authority_refs=(pin("r15-review", review),
            pin("r15-review-synced", synced), pin("r12-user-approved-asset", identity),
            pin("frozen-reference-duties", duties)))
    metadata = Media(id=media_id, work_id=scope.work_id, shot_id=scope.shot_id, media_type="IMAGE",
        purpose="VIDEO_INPUT", source_ref=retained["sourceRef"], content_hash=media_hash,
        mime_type="image/png", file_size=retained["sizeBytes"])
    instruction_table = []
    for kind, projection in (("VISUAL", frozen["spec"]["performance"]["directorPerformance"]),
                              ("VOICE", frozen["spec"]["dialogue"][0]["voicePerformance"])):
        for field, value in projection["instructions"].items():
            exact = kind == "VOICE" and field == "articulation" and value == "保持原词"
            instruction_table.append(dict(legacyInstruction=value, field=field,
                sourceLocator="S02-cinematic/K02-frozen.json#/spec/" +
                    ("performance/directorPerformance" if kind == "VISUAL" else "dialogue/0/voicePerformance") + "/instructions/" + field,
                createdBy="prepare-s02-cinematic.py:31" if kind == "VISUAL" else "prepare-s02-cinematic.py:32",
                currentOwner="screenplay/dialogue" if exact else "legacy host projection",
                classification="AUTHORITATIVE" if exact else "LEGACY_DERIVED",
                targetDisposition="CURRENT_SCENE_EXACT_TEXT" if exact else "EXCLUDED_FROM_REQUIRED_PARITY",
                rationale="精确文字回到正式 Scene spokenContent；不迁入保持原词的旧文案。" if exact else
                    "细粒度文案由旧 Host 脚本写在 projection；冻结的 OFFLINE_EXECUTABILITY 检查没有给它独立艺术批准。当前 owner 已写的动作/表演义务另行保留。"))
    audit = dict(actualOldMode="image_to_video", actualOldModel="vidu-q3-turbo",
        targetShadowMode="image_to_video", targetShadowModel="seedance-2-standard",
        modeEvidence="SINGLE_IMAGE + actual api_vidu_q3_image_to_video + R15 FIRST_FRAME; not stale R13 prepared-ir",
        firstFrame=media_id, lastFrame=None, mediaHash=media_hash, localHashVerified=True,
        authorization="REVIEWED_TRIAL_INPUT, PASS_WITH_NOTES; userAdoption=PENDING is not final-film approval",
        designReferenceIsExecutionReference=False, dutyOwner="Cinematic reference requirements / production assembly",
        mediaOwner="Media", sourceBindingOwner="production-assembly/reference-strategy",
        dialogueTiming=dict(windowSeconds=[2.0,6.2], classification="LEGACY_DERIVED",
            createdBy="prepare-s02-cinematic.py:37,43; start=2 hard-coded, end=2+estimatedDurationMs/1000",
            artifact="S02-cinematic/K02-frozen.json#/spec/dialogue/0",
            approvalEvidence="OFFLINE_EXECUTABILITY_ONLY and general assembly review; no independent absolute timing approval",
            owner="legacy cinematic projection; future authoritative timing owner=Dialogue/Editorial/Audio",
            currentEditorialEvidence="reaction_duration: 当前只有表演估计，无测量音画入出点。",
            disposition="NOT_BOUND; AudioExecutionPlan.windowMs stays null", promotedToCanon=False),
        visualVoiceInstructions=instruction_table,
        legacyDerivedInstructionsPromoted=False)
    return context, binding, metadata, audit


def formal_required(package, ir, coverage, audio, binding, selected, dependencies):
    """Independent source categories, not required flags copied from coverage.

    Current owner leaf obligations plus reviewed CHAR/COMPOSITION bindings;
    Legacy derived timing/instructions are not a formal required source set.
    """
    records = []
    entries = {sha256_canonical(e.source_ref):e for e in coverage.entries}
    # Explicit formal executing fields selected by the approved owners.
    required_fields = {
        "subjectAction", "requiredTransition", "visualEntryState", "visualExitState", "plannedDurationMs",
        "actor_movements", "eye_lines", "physical_relations", "handoffs", "visibleDirection",
        "perspective", "camera_point_of_view", "camera_movement", "lens_intention",
        "architectural_language", "location_identity", "topology", "source_visual_basis",
        "source", "direction", "intensity_relationship", "contrast", "practical_lights", "day_night_continuity",
        "emotional_color_progression", "cut_points", "holds", "temporal_compression", "restraint_principles",
        "foreground_background_relationship", "silence_design", "performanceIntent", "text", "decision",
        "apparent_age", "face_structure", "body_proportion", "body_proportions", "current_visual_state", "hair", "beard", "cut",
        "facial_hair", "skin", "garment_construction_intent", "materials", "wear",
    }
    def obligation(ref, domain):
        entry = entries.get(sha256_canonical(ref))
        assert entry is not None and entry.status in {"TEXT_COVERED", "REFERENCE_COVERED"}, ref
        records.append(dict(id="formal:" + sha256_canonical(ref), classification="AUTHORITATIVE", domain=domain,
            sourceRef=ref.model_dump(mode="json", by_alias=True), status=entry.status.value,
            inputRef=entry.input_ref.model_dump(mode="json") if entry.input_ref else None))
    # Enumerate expected leaves from current owner selections, independently of
    # what IR/coverage happened to retain. Deleting a Lighting receipt must fail.
    for item in selected:
        ref, value = item.selection.reference, item.value
        if isinstance(value, str) and ref.path[-1:] and ref.path[-1] in required_fields:
            obligation(ref, item.selection.domain.value)
        elif isinstance(value, dict) and not ref.artifact_ref.startswith("execution-reference:"):
            for field in required_fields:
                if isinstance(value.get(field), str) and value[field]:
                    obligation(SourceReference(**{**ref.model_dump(), "path": ref.path + (field,)}), item.selection.domain.value)
            if value.get("physical_state", {}).get("dpdOriginal"):
                dependency, body = dependencies.resolve_pin(value["physical_state"]["dpdOriginal"], work_id=package.scope.work.artifact_ref)
                index = value["physical_state"]["actorBeat"]
                obligation(SourceReference(**{**dependency.model_dump(), "path": ("physicalPerformance", str(index), "visibleDirection")}), "PERFORMANCE")
            for index, zone in enumerate(value.get("no_music_zones", ())):
                if zone.get("scene") == package.scope.scene.artifact_ref:
                    obligation(SourceReference(**{**ref.model_dump(), "path": ref.path + ("no_music_zones", str(index), "decision")}), "SOUND")
            if item.selection.domain == "REFERENCE" and "key" in value:
                dependency, body = dependencies.resolve_pin(value, work_id=package.scope.work.artifact_ref)
                obligation(SourceReference(**{**dependency.model_dump(), "path": ("medium",)}), "REFERENCE")
    # Make omission detectable: verify mandatory source refs independently of IR.
    source_checks = [*package.obligations, package.generation_intent.duration_ref]
    for source in package.sources:
        if source.reference.owner == "shot" and source.reference.path[-1:] in {
                ("subjectAction",),("visualEntryState",),("visualExitState",)}:
            source_checks.append(source.reference)
        if source.reference.owner == "scene" and source.reference.path[:2] == ("content","spokenContent"):
            source_checks.append(SourceReference(**{**source.reference.model_dump(),"path":source.reference.path+("text",)}))
    for ref in source_checks:
        entry=entries.get(sha256_canonical(ref))
        if ref.path[-1] == "purpose":
            assert entry and entry.status == "INTERNAL_ONLY"
            records.append(dict(id="formal:"+sha256_canonical(ref),classification="AUTHORITATIVE",domain="DIRECTION",
                sourceRef=ref.model_dump(mode="json",by_alias=True),status="INTERNAL_ONLY",inputRef=None))
        else:
            assert entry and entry.status in {"TEXT_COVERED","REFERENCE_COVERED"}, ref
            obligation(ref,entry.domain.value)
    for index, duty in enumerate(binding.duties):
        if duty.necessity != "REQUIRED":continue
        ref=SourceReference(**{**binding.source().reference().model_dump(),"path":("duties",str(index))})
        entry=entries[sha256_canonical(ref)]
        assert entry.status == "REFERENCE_COVERED" and entry.input_ref.artifact_ref == binding.media.media_id
        records.append(dict(id="formal:reference:"+duty.role,classification="DERIVED_APPROVED",domain="REFERENCE",
            sourceRef=ref.model_dump(mode="json",by_alias=True),status=entry.status.value,
            inputRef=entry.input_ref.model_dump(mode="json")))
    assert audio.speech_events[0].window_ms is None
    records=list({r["id"]:r for r in records}.values())
    formal_refs={sha256_canonical(r["sourceRef"]) for r in records}
    assert all(sha256_canonical(e.source_ref.model_dump(mode="json",by_alias=True)) in formal_refs
               for e in coverage.entries if e.obligation == "EXECUTION_REQUIRED"), "A compiler required source must belong to the independently enumerated formal set"
    assert len(records)>25 and all(r["status"] in {"TEXT_COVERED","REFERENCE_COVERED","INTERNAL_ONLY"} for r in records)
    return dict(scope=ir.scope.model_dump(mode="json"),inputMode="image_to_video", obligations=records,
        requiredUnresolved=0, excluded=["LEGACY_DERIVED timing 2.0–6.2s", "LEGACY_DERIVED projection instructions"],
        parity="FORMAL_REQUIRED_OBLIGATIONS, not equal old/new prompt text")


async def shadow(output: Path, project: Path = PROJECT):
    context, binding, metadata, audit = reconcile(project)
    data=MockDramaData.empty()
    for key, model in (("work",Work),("script",Script),("episode",Episode),("scene",Scene),("shot",Shot)):
        setattr(data,key,model.model_validate(context[key]))
    data.media=[metadata]
    references=ReferenceExecutionStore(); references.register(binding)
    before={key:dump_contract(getattr(data,key)) for key in ("work","scene","shot")}
    sources=[project/"S02-cinematic/K02-context.json",project/"S02-inputs/K02-r15.png",
        project/"S02-inputs/K02-r15-retention.json",project/"S02-inputs/K02-r15-review.json",
        project/"S02-performance-direction.json",*sorted((project/"S02-design").glob("*.json"))]
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    def forbidden(*a,**k):raise AssertionError("T5R forbids Provider/media/Legacy Prompt calls")
    forbidden_paths={project/"S02-cinematic/K02-frozen.json",project/"S02-cinematic/K02-spec.json",
        project/"S02-video/K02-prepared.json",project/"S02-video/K02-provider-prompt-ir.txt",
        project/"S02-video/K02-dispatch-ready-r15.json"}
    read_text=Path.read_text
    def guarded_read(file,*a,**k):
        assert file not in forbidden_paths, "Runtime consumer must not read audit/Legacy inputs"
        return read_text(file,*a,**k)
    with patch("drama_plugin.plugin.load_config",return_value=DramaPluginConfig()), \
         patch.object(socket.socket,"connect",forbidden),patch.object(socket.socket,"connect_ex",forbidden), \
         patch("drama_plugin.hosts.cinematic_projection.project",forbidden), \
         patch("drama_plugin.professional.compile_prompt_projection",forbidden), \
         patch("drama_plugin.visual.video_prompt.compile_request_ir",forbidden),patch.object(Path,"read_text",guarded_read):
        async with DramaPlugin.load(PLUGIN,mock_data=data,legacy_reads=True, production_artifact_roots=(project/"S02-design",),
                reference_execution_store=references) as plugin:
            media_reads=[]; original=plugin.prompt_compiler.references.media_reader.get_media
            async def media_get(identity):media_reads.append(identity);return await original(identity)
            count=0;generate=plugin.prompt_compiler.generator.generate
            def generator(*a,**k):
                nonlocal count
                count+=1;return generate(*a,**k)
            with patch.object(plugin.prompt_compiler.references.media_reader,"get_media",media_get), \
                 patch.object(plugin.prompt_compiler.generator,"generate",generator), \
                 patch.object(plugin.providers.production,"generate_video",forbidden), \
                 patch.object(plugin.providers.production,"generate_image",forbidden):
                run=plugin.create_generation_run(work_id=data.work.id,scene_id=data.scene.id,shot_id=data.shot.id,
                    mode=RunMode.EXPERIMENT,run_id="t5r-S02-K02",
                    task=GenerationTask(input_mode="image_to_video",native_audio="REQUIRED"))
                partial=await plugin.runtime.run(run.run_id,max_ticks=5)
                assert partial.cursor==4 and partial.state==RuntimeState.READY
                prepared_ref=plugin.generation_artifacts.prepared(run.run_id)
                prepared=plugin.generation_artifacts.get(prepared_ref,GenerationPreparation)
                async with DramaPlugin.load(PLUGIN,mock_data=data,legacy_reads=True, production_artifact_roots=(project/"S02-design",),
                        reference_execution_store=references,production_package_store=plugin.production_packages,
                        gate_finding_store=plugin.gate_findings,generation_artifact_store=plugin.generation_artifacts) as restored:
                    restored.runtime.restore(plugin.runtime.serialize(run.run_id))
                    with patch.object(restored.shot_assembler,"assemble",forbidden),patch.object(restored.prompt_compiler.generator,"generate",forbidden):
                        completed=await restored.runtime.run(run.run_id)
                        assert completed.state==RuntimeState.SUCCEEDED
                        assert completed.last_result.artifact_refs==(prepared.final_prompt_ref,prepared.audio_plan_ref,prepared_ref)
                final=plugin.generation_artifacts.get(prepared.final_prompt_ref,FinalPromptArtifact)
                audio=plugin.generation_artifacts.get(prepared.audio_plan_ref,AudioExecutionPlan)
                coverage=plugin.generation_artifacts.get(final.coverage_ref,PromptCoverage)
                ir=plugin.generation_artifacts.get(ArtifactReference(owner="prompt-ir",artifact_ref="prompt-ir:"+final.prompt_ir_fingerprint,version=1),PromptIR)
                package=plugin.production_packages.get(prepared.source_package_ref)
                assert final.task.input_mode==audit["actualOldMode"]=="image_to_video"
                assert "@图片1" in final.prompt_text and "作为首帧" in final.prompt_text and count==1
                assert set(media_reads)=={binding.media.media_id}
                assert before=={key:dump_contract(getattr(data,key)) for key in before}
                assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
                parity=formal_required(package,ir,coverage,audio,binding,
                    await plugin.prompt_compiler.reader.selections(package),plugin.prompt_compiler.reader.dependencies)
                result=dict(scope=ir.scope.model_dump(mode="json"),actualOldMode=audit["actualOldMode"],targetMode=final.task.input_mode,
                    finalChars=len(final.prompt_text),packageBytes=len(package.model_dump_json().encode()),
                    bindingBytes=len(binding.model_dump_json().encode()),coverageCounts=dict(Counter(e.status.value for e in coverage.entries)),
                    packageRef=package.artifact_reference().model_dump(mode="json"),finalPromptRef=prepared.final_prompt_ref.model_dump(mode="json"),
                    referenceBindingRef=binding.source().reference().model_dump(mode="json"),mediaReads=media_reads,
                    requiredUnresolved=0,generatorCalls=count,recoverySameRefs=True,canonUnchanged=True,
                    sourceHashesBefore=hashes,sourceHashesAfter=hashes,providerSubmission=0,paidCalls=0,mediaGeneration=0)
    output.mkdir(parents=True,exist_ok=True)
    for name,value in (("Source-Authority-Audit",audit),("ReferenceExecutionBinding",binding),
            ("MediaMetadata",metadata),("ProductionPackage",package),("PromptIR",ir),("Coverage",coverage),
            ("AudioExecutionPlan",audio),("FinalPromptArtifact",final),("GenerationPreparation",prepared),
            ("FORMAL_REQUIRED_OBLIGATION_SET",parity),("S02-K02-Same-Task-Shadow",result)):
        body=value.model_dump(mode="json",by_alias=True) if hasattr(value,"model_dump") else value
        (output/("T5R-"+name+".json")).write_text(json.dumps(body,ensure_ascii=False,indent=2)+"\n")
    (output/"T5R-S02-K02-Target-FinalPrompt.txt").write_text(final.prompt_text+"\n")
    return {k:result[k] for k in ("actualOldMode","targetMode","finalChars","coverageCounts","requiredUnresolved",
        "generatorCalls","recoverySameRefs","canonUnchanged","providerSubmission")}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();print(json.dumps(asyncio.run(shadow(args.output)),ensure_ascii=False,indent=2))
