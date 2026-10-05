"""T5 real Package-only offline shadow; no Provider request or creative write."""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import hashlib
import json
from pathlib import Path
import socket
from unittest.mock import patch
from types import SimpleNamespace

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.creation import Work, Script, Episode, Scene, Shot
from drama_plugin.generation.contracts import AudioExecutionPlan, FinalPromptArtifact, GenerationPreparation, PromptCoverage, PromptIR
from drama_plugin.generation.seedance import ExactPromptTransfer
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.providers.video.adapters import content_items
from drama_plugin.runtime import ArtifactReference, RunMode, RuntimeState

PLUGIN = Path(__file__).resolve().parents[1]
PROJECT = PLUGIN.parents[1] / "artifacts/flagship-literary-film-01/test-shoot-01"


def forbidden(*args, **kwargs):
    raise AssertionError("T5 forbids network, Provider submission, media generation and old Prompt compilation")


async def shadow(output: Path, project: Path = PROJECT):
    context = project / "S02-cinematic/K02-context.json"
    original = json.loads(context.read_text())
    data = MockDramaData.empty()
    for key, model in (("work", Work), ("script", Script), ("episode", Episode), ("scene", Scene), ("shot", Shot)):
        setattr(data, key, model.model_validate(original[key]))
    before_canon = {key: dump_contract(getattr(data, key)) for key in ("work", "scene", "shot", "script", "episode")}
    source_files = [context, project / "S02-performance-direction.json", *sorted((project / "S02-design").glob("*.json"))]
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    hashes = {str(path): digest(path) for path in source_files}
    calls, read_refs = [], []
    assembly_calls = generator_calls = 0
    with patch("drama_plugin.plugin.load_config", return_value=DramaPluginConfig()), \
         patch.object(socket.socket, "connect", forbidden), patch.object(socket.socket, "connect_ex", forbidden), \
         patch("drama_plugin.hosts.cinematic_projection.project", forbidden), \
         patch("drama_plugin.professional.compile_prompt_projection", forbidden), \
         patch("drama_plugin.visual.video_prompt.compile_request_ir", forbidden):
        async with DramaPlugin.load(PLUGIN, mock_data=data, legacy_reads=True, production_artifact_roots=(project / "S02-design",)) as plugin:
            execute = plugin.runtime.executor.execute
            assemble = plugin.shot_assembler.assemble
            generate = plugin.prompt_compiler.generator.generate
            resolver = plugin.prompt_compiler.reader.resolver
            async def record_call(key, inputs):
                calls.append(key)
                return await execute(key, inputs)
            async def record_assembly(*args, **kwargs):
                nonlocal assembly_calls
                assembly_calls += 1
                return await assemble(*args, **kwargs)
            def record_generation(*args, **kwargs):
                nonlocal generator_calls
                generator_calls += 1
                return generate(*args, **kwargs)
            class RecordedReferences:
                async def resolve(self, ref):
                    read_refs.append(ref)
                    assert ref.path and ref.path[-1] != "approvedSceneText"
                    return await resolver.resolve(ref)
            plugin.prompt_compiler.reader.resolver = RecordedReferences()
            with patch.object(plugin.runtime.executor, "execute", record_call), \
                 patch.object(plugin.shot_assembler, "assemble", record_assembly), \
                 patch.object(plugin.prompt_compiler.generator, "generate", record_generation), \
                 patch.object(plugin.providers.production, "generate_video", forbidden), \
                 patch.object(plugin.providers.production, "generate_image", forbidden):
                run = plugin.create_generation_run(work_id=data.work.id, scene_id=data.scene.id, shot_id=data.shot.id,
                    mode=RunMode.EXPERIMENT, run_id="t5-real-S02-K02")
                current = await plugin.runtime.run(run.run_id, max_ticks=5)
                assert current.state == RuntimeState.READY and current.cursor == 4
                checkpoint = plugin.runtime.serialize(run.run_id)
                prepared_ref = plugin.generation_artifacts.prepared(run.run_id)
                prepared = plugin.generation_artifacts.get(prepared_ref, GenerationPreparation)
                async with DramaPlugin.load(PLUGIN, mock_data=data, legacy_reads=True, production_artifact_roots=(project / "S02-design",),
                        production_package_store=plugin.production_packages, gate_finding_store=plugin.gate_findings,
                        generation_artifact_store=plugin.generation_artifacts) as restored:
                    restored.runtime.restore(checkpoint)
                    with patch.object(restored.shot_assembler, "assemble", forbidden), \
                         patch.object(restored.prompt_compiler.generator, "generate", forbidden):
                        completed = await restored.runtime.run(run.run_id)
                        assert completed.state == RuntimeState.SUCCEEDED
                        assert completed.last_result.artifact_refs == (prepared.final_prompt_ref, prepared.audio_plan_ref, prepared_ref)
                final = plugin.generation_artifacts.get(prepared.final_prompt_ref, FinalPromptArtifact)
                audio = plugin.generation_artifacts.get(prepared.audio_plan_ref, AudioExecutionPlan)
                coverage = plugin.generation_artifacts.get(final.coverage_ref, PromptCoverage)
                ir = plugin.generation_artifacts.get(ArtifactReference(owner="prompt-ir",
                    artifact_ref="prompt-ir:" + final.prompt_ir_fingerprint, version=1), PromptIR)
                package = plugin.production_packages.get(prepared.source_package_ref)
                assert ExactPromptTransfer.prompt(final) == final.prompt_text
                # Exercise the existing transport primitive's explicit compiled-text
                # branch offline, without creating/calling a Provider or supplying
                # creative fields. No references are used by this text-only task.
                transport_items = content_items(SimpleNamespace(references=lambda: ()), {},
                    compiled_prompt=ExactPromptTransfer.prompt(final))
                assert json.loads(json.dumps(transport_items, ensure_ascii=False))[0]['text'] == final.prompt_text
                assert assembly_calls == generator_calls == 1
                assert "妈妈……先生，妈妈……" in final.prompt_text
                assert "妈妈……先生，妈妈……" not in audio.model_dump_json()
                assert not any(e.status == "UNRESOLVED" and e.obligation == "EXECUTION_REQUIRED" for e in coverage.entries)
                old_file = project / "S02-video/K02-provider-prompt-ir.txt"
                old_text = old_file.read_text().strip()
                per_domain = {domain: dict(Counter(e.status.value for e in coverage.entries if e.domain.value == domain))
                              for domain in sorted({e.domain.value for e in coverage.entries})}
                scope = package.scope.model_dump(mode="json", by_alias=True)
                results = {
                    "level": "OFFLINE_REAL_CURRENT_SHOT_TARGET_PROMPT_AUDIO_SHADOW",
                    "fixture": str(context), "scope": scope,
                    "packageRef": prepared.source_package_ref.model_dump(mode="json"),
                    "packageFingerprint": package.fingerprint, "packageBytes": len(package.model_dump_json(by_alias=True).encode()),
                    "finalChars": len(final.prompt_text), "hardLimit": plugin.prompt_compiler.catalog.policy(final.task.target_model).hard_limit,
                    "coverageCounts": dict(Counter(e.status.value for e in coverage.entries)), "domainCoverage": per_domain,
                    "requiredUnresolved": 0, "generatorCalls": generator_calls, "assemblerCalls": assembly_calls,
                    "consumerReadRefs": [r.model_dump(mode="json", by_alias=True) for r in read_refs],
                    "consumerReadsOnlyPackageSelections": set(read_refs) <= ({s.reference for s in package.sources} | set(package.obligations)),
                    "nativeRuntimeCallsBeforeCheckpoint": calls, "checkpoint": json.loads(checkpoint),
                    "restoredFinal": json.loads(restored.runtime.serialize(run.run_id)),
                    "recoverySameRefs": True, "sourceHashesBefore": hashes,
                    "sourceHashesAfter": {str(path): digest(path) for path in source_files},
                    "canonUnchanged": before_canon == {key: dump_contract(getattr(data, key)) for key in before_canon},
                    "oldPrompt": dict(path=str(old_file), chars=len(old_text), sha256=digest(old_file),
                        exactCurrentFactMatches=sum(f.text in old_text for f in ir.facts), currentFactCount=len(ir.facts)),
                    "legacyOnlyDetails": [
                        "旧 CinematicShotSpec 的 2.0–6.2s planning window 未进入 T2 Package 的来源关系；新计划没有猜造这一窗。",
                        "旧 Visual/Voice PerformanceProjection 的细粒度 instructions 未直接绑定于当前 Package；仅沿已批准 DPD pin 读取当前 actorBeat 的 visibleDirection。",
                        "旧 CHARACTER/COMPOSITION 媒体职责属于旧 route/reference 输入；本次 text_to_video 只表达已有原件事实，没有虚报图片 reference-covered。",
                    ],
                    "providerSubmission": 0, "paidCalls": 0, "mediaGeneration": 0, "formalWrites": 0,
                    "stores": plugin.generation_artifacts.durability,
                }
                results['exactTransferIntoExistingTransportPrimitive'] = True
                results['targetProviderSubmissionConnected'] = False
                assert results["canonUnchanged"] and results["sourceHashesBefore"] == results["sourceHashesAfter"]
                assert results["consumerReadsOnlyPackageSelections"]
                output.mkdir(parents=True, exist_ok=True)
                def save(name, value):
                    (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
                save("T5-S02-K02-Shadow.json", results)
                save("T5-S02-K02-PromptIR.json", ir.model_dump(mode="json", by_alias=True))
                save("T5-S02-K02-PromptIR-summary.json", {"fingerprint": ir.fingerprint, "factCount": len(ir.facts),
                    "domainCounts": dict(Counter(f.domain.value for f in ir.facts)), "slots": sorted({f.slot for f in ir.facts}),
                    "artifactBytes": len(ir.model_dump_json(by_alias=True).encode())})
                save("T5-S02-K02-Coverage.json", coverage.model_dump(mode="json", by_alias=True))
                save("T5-S02-K02-AudioExecutionPlan.json", audio.model_dump(mode="json", by_alias=True))
                save("T5-S02-K02-FinalPromptArtifact.json", final.model_dump(mode="json", by_alias=True))
                save("T5-S02-K02-GenerationPreparation.json", prepared.model_dump(mode="json", by_alias=True))
                (output / "T5-S02-K02-Target-FinalPrompt.txt").write_text(final.prompt_text + "\n")
                return {key: results[key] for key in ("finalChars", "hardLimit", "coverageCounts", "requiredUnresolved",
                    "assemblerCalls", "generatorCalls", "canonUnchanged", "recoverySameRefs", "providerSubmission", "paidCalls", "mediaGeneration")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project", type=Path, default=PROJECT)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(shadow(args.output, args.project)), ensure_ascii=False, indent=2))
