"""T2: read an existing real Shot fixture, assemble via Plugin, compare without production."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import socket
from typing import Any
from unittest.mock import patch

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.creation import Work, Script, Episode, Scene, Shot
from drama_plugin.production import ProductionPackage
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.runtime import RunMode, RuntimeState
from drama_plugin.runtime.engine import foundation_workflows

PLUGIN = Path(__file__).resolve().parents[1]
PROJECT = PLUGIN.parents[1] / "artifacts/flagship-literary-film-01/test-shoot-01"


def forbidden(*args: Any, **kwargs: Any) -> Any:
    raise AssertionError("T2 forbids network, Prompt compilation and Provider submission")


async def shadow(context: Path, professional_root: Path, legacy_spec: Path) -> dict[str, Any]:
    raw = json.loads(context.read_text(encoding="utf-8"))
    data = MockDramaData.empty()
    for name, model in (("work", Work), ("script", Script), ("episode", Episode), ("scene", Scene), ("shot", Shot)):
        setattr(data, name, model.model_validate(raw[name]))
    assert data.work is not None and data.scene is not None and data.shot is not None
    paths = [context, legacy_spec, *sorted(professional_root.glob("*.json"))]
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    original_files = {str(path): digest(path) for path in paths}
    original_canon = {name: dump_contract(getattr(data, name)) for name in ("work", "script", "episode", "scene", "shot")}
    calls: list[str] = []
    assembly_count = 0
    with patch("drama_plugin.plugin.load_config", return_value=DramaPluginConfig()), \
         patch.object(socket.socket, "connect", forbidden), patch.object(socket.socket, "connect_ex", forbidden), \
         patch("drama_plugin.hosts.cinematic_projection.project", forbidden), \
         patch("drama_plugin.professional.compile_prompt_projection", forbidden):
        async with DramaPlugin.load(PLUGIN, mock_data=data, legacy_reads=True, production_artifact_roots=(professional_root,)) as plugin:
            original_execute = plugin.runtime.executor.execute
            original_assemble = plugin.shot_assembler.assemble

            async def execute(key: str, inputs: Any) -> Any:
                calls.append(key)
                return await original_execute(key, inputs)

            async def assemble(*args: Any, **kwargs: Any) -> Any:
                nonlocal assembly_count
                assembly_count += 1
                return await original_assemble(*args, **kwargs)

            with patch.object(plugin.runtime.executor, "execute", execute), \
                 patch.object(plugin.shot_assembler, "assemble", assemble), \
                 patch.object(plugin.providers.production, "generate_image", forbidden), \
                 patch.object(plugin.providers.production, "generate_video", forbidden):
                run = plugin.runtime.create_run(work_id=data.work.id, scene_id=data.scene.id,
                    shot_id=data.shot.id, mode=RunMode.EXPERIMENT, workflow_id="prepare-shot:v1",
                    run_id="t2-real-shadow")
                ready = await plugin.runtime.run(run.run_id, max_ticks=2)
                assert ready.state == RuntimeState.READY and ready.cursor == 1 and ready.last_result is not None
                reference = ready.last_result.artifact_refs[0]
                package = plugin.production_packages.get(reference)
                current = await plugin.shot_assembler.validate_sources(package)
                assert current.status == "READY", current
                snapshot = plugin.runtime.serialize(run.run_id)
                before_action = plugin.runtime.next_action(run.run_id)
                async with DramaPlugin.load(PLUGIN, mock_data=data, legacy_reads=True, production_artifact_roots=(professional_root,),
                        production_package_store=plugin.production_packages) as restored_plugin:
                    restored_plugin.runtime.restore(snapshot)
                    assert restored_plugin.runtime.next_action(run.run_id) == before_action
                    with patch.object(restored_plugin.shot_assembler, "assemble", forbidden):
                        completed = await restored_plugin.runtime.run(run.run_id)
                        assert completed.state == RuntimeState.SUCCEEDED and completed.last_result is not None
                        assert completed.last_result.artifact_refs == (reference,)
                    runtime_json = restored_plugin.runtime.serialize(run.run_id)
                encoded = package.model_dump_json(by_alias=True)
                assert ProductionPackage.model_validate_json(encoded) == package
                spec = json.loads(legacy_spec.read_text(encoding="utf-8"))
                spec = spec.get("spec", spec)
                comparisons = {
                    "Work相同": spec["workId"] == package.scope.work.artifact_ref,
                    "Scene相同": spec["sceneId"] == package.scope.scene.artifact_ref,
                    "Shot相同": spec["shotId"] == package.scope.shot.artifact_ref,
                    "时长一致": round(spec["durationSeconds"] * 1000) == package.generation_intent.duration_ms,
                    "Camera仅当前记录": [ref.reference.path for ref in package.sources if ref.domain == "CAMERA"] == [("content", "1", "values")],
                    "有表演原件": any(ref.domain == "PERFORMANCE" and "dramatic-performance-direction" in ref.reference.artifact_ref for ref in package.sources),
                    "没有平台全集": all(ref.reference.artifact_ref not in {"bible:F01-S02-animal-design", "bible:F01-S02-story-architecture", "bible:F01-S02-literary-source-input", "bible:F01-S02-prop-design"} for ref in package.sources),
                    "无供应商内容": not any(name.lower() in encoded.lower() for name in ("Vidu", "Seedance", "Comfy", "Fish", "Flux")),
                    "原文未复制": data.scene.content["approvedSceneText"] not in encoded and spec["narrativeIntent"] not in encoded,
                    "Runtime仅有Package引用": package.fingerprint in runtime_json and "approvedSceneText" not in runtime_json and "sources" not in json.loads(runtime_json),
                    "只组装一次且恢复同Ref": assembly_count == 1 and completed.last_result.artifact_refs == (reference,),
                    "T1默认workflow身份不变": sha256_canonical(foundation_workflows()["inspect-work:v1"]) == "478e5fe755db4823c81695db6ab077df9a94c785da28e97f593e1e2156acea3d",
                }
                assert all(comparisons.values()), comparisons
    assert original_files == {str(path): digest(path) for path in paths}
    assert original_canon == {name: dump_contract(getattr(data, name)) for name in original_canon}
    return {"level": "OFFLINE_REAL_SHOT_SHADOW_ASSEMBLY", "fixture": str(context),
        "legacySpec": str(legacy_spec), "sourceFileHashes": original_files, "canonUnchanged": True,
        "comparisons": comparisons, "nativeCallsBeforeCheckpoint": calls, "assemblyCount": assembly_count,
        "packageRef": reference.model_dump(mode="json", by_alias=True),
        "package": package.model_dump(mode="json", by_alias=True), "packageBytes": len(encoded.encode()),
        "sourceReferenceCount": len(package.sources), "runtimeCheckpoint": json.loads(snapshot),
        "runtimeFinal": json.loads(runtime_json), "providerSubmission": 0, "paidGenerationCalls": 0,
        "mediaGeneration": 0, "formalWrites": 0, "packageStore": plugin.production_packages.durability}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", type=Path, default=PROJECT / "S02-cinematic/K02-context.json")
    parser.add_argument("--professional-root", type=Path, default=PROJECT / "S02-design")
    parser.add_argument("--legacy-spec", type=Path, default=PROJECT / "S02-cinematic/K02-spec.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = asyncio.run(shadow(args.context, args.professional_root, args.legacy_spec))
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key not in {
        "package", "sourceFileHashes", "runtimeCheckpoint", "runtimeFinal"}}, ensure_ascii=False, indent=2))
