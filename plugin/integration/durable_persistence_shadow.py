"""T6 offline S02-K02 shadow; invoke start/resume/terminal in separate OS processes.

start alone performs T5R's one-time authority reconciliation. Resume reads the
existing Canon/Media fixtures and the Ledger; it does not reconstruct bindings
from old Prompt/VideoRequest evidence or share Python Store objects.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import socket
from unittest.mock import patch

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.creation import Work, Script, Episode, Scene, Shot
from drama_plugin.contracts.media import Media
from drama_plugin.generation.contracts import (
    AudioExecutionPlan, FinalPromptArtifact, GenerationPreparation, GenerationTask,
)
from drama_plugin.production.contracts import SourceDomain, SourceReference
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.runtime import RunMode, RuntimeState

from prompt_obligation_reconciliation_shadow import PROJECT, PLUGIN, reconcile

EVIDENCE = PLUGIN.parents[1] / "未来架构/迁移/evidence"


def data_from_current_sources():
    context = json.loads((PROJECT / "S02-cinematic/K02-context.json").read_text())
    data = MockDramaData.empty()
    for key, model in (("work", Work), ("script", Script), ("episode", Episode),
                       ("scene", Scene), ("shot", Shot)):
        setattr(data, key, model.model_validate(context[key]))
    data.media = [Media.model_validate(json.loads((EVIDENCE / "T5R-MediaMetadata.json").read_text()))]
    return data


def forbidden(*args, **kwargs):
    raise AssertionError("T6 must not use Provider, paid generation or legacy Prompt")


async def phase(name: str, ledger_path: Path, output: Path, run_id: str, prior: Path | None):
    if name == "start":
        context, binding, metadata, audit = reconcile()
        data = data_from_current_sources()
        assert metadata == data.media[0] and audit["actualOldMode"] == "image_to_video"
    else:
        data = data_from_current_sources()
    original_work = data.work.model_dump_json()
    with patch("drama_plugin.plugin.load_config", return_value=DramaPluginConfig()), \
         patch.object(socket.socket, "connect", forbidden), \
         patch.object(socket.socket, "connect_ex", forbidden), \
         patch("drama_plugin.professional.compile_prompt_projection", forbidden), \
         patch("drama_plugin.hosts.cinematic_projection.project", forbidden), \
         patch("drama_plugin.visual.video_prompt.compile_request_ir", forbidden):
        async with DramaPlugin.load(PLUGIN, mock_data=data, legacy_reads=True,
                production_artifact_roots=(PROJECT / "S02-design",), ledger_path=ledger_path) as plugin:
            assert plugin.ledger is not None
            with patch.object(plugin.providers.production, "generate_video", forbidden), \
                 patch.object(plugin.providers.production, "generate_image", forbidden):
                if name == "start":
                    plugin.execution_references.register(binding)
                    calls = {"assembler": 0, "generator": 0}
                    assemble = plugin.shot_assembler.assemble
                    generate = plugin.prompt_compiler.generator.generate
                    async def counted_assembly(*args, **kwargs):
                        calls["assembler"] += 1
                        return await assemble(*args, **kwargs)
                    def counted_generator(*args, **kwargs):
                        calls["generator"] += 1
                        return generate(*args, **kwargs)
                    with patch.object(plugin.shot_assembler, "assemble", counted_assembly), \
                         patch.object(plugin.prompt_compiler.generator, "generate", counted_generator):
                        run = plugin.create_generation_run(work_id=data.work.id,
                            scene_id=data.scene.id, shot_id=data.shot.id, mode=RunMode.EXPERIMENT,
                            run_id=run_id, task=GenerationTask(input_mode="image_to_video",
                                native_audio="REQUIRED"))
                        current = await plugin.runtime.run(run_id, max_ticks=5)
                    assert current.state == RuntimeState.READY and current.cursor == 4
                    assert calls == {"assembler": 1, "generator": 1}
                else:
                    expected = json.loads(prior.read_text())
                    assert expected["runId"] == run_id
                    with patch.object(plugin.shot_assembler, "assemble", forbidden), \
                         patch.object(plugin.prompt_compiler.generator, "generate", forbidden):
                        recovered = await plugin.runtime.recover_run(run_id)
                        assert recovered.revision == expected["revision"]
                        current = await plugin.runtime.run(run_id)
                    if name == "resume":
                        assert recovered.state == RuntimeState.READY
                        assert current.state == RuntimeState.SUCCEEDED
                    else:
                        assert recovered.state == current.state == RuntimeState.SUCCEEDED
                    calls = {"assembler": 0, "generator": 0}
                prepared_ref = plugin.generation_artifacts.prepared(run_id)
                prepared = plugin.generation_artifacts.get(prepared_ref, GenerationPreparation)
                package = plugin.production_packages.get(prepared.source_package_ref)
                final = plugin.generation_artifacts.get(prepared.final_prompt_ref, FinalPromptArtifact)
                audio = plugin.generation_artifacts.get(prepared.audio_plan_ref, AudioExecutionPlan)
                binding_ref = next(s.reference for s in package.sources
                    if s.domain == SourceDomain.REFERENCE and s.reference.artifact_ref.startswith("execution-reference:"))
                selected = plugin.execution_references.resolve(binding_ref)
                assert selected["media"]["mediaId"] == data.media[0].id
                assert selected["media"]["contentHash"] == data.media[0].content_hash
                assert prepared.provider_submission_allowed is False
                refs = {
                    "package": prepared.source_package_ref.model_dump(mode="json"),
                    "finalPrompt": prepared.final_prompt_ref.model_dump(mode="json"),
                    "audioPlan": prepared.audio_plan_ref.model_dump(mode="json"),
                    "preparation": prepared_ref.model_dump(mode="json"),
                    "referenceBinding": binding_ref.model_dump(mode="json"),
                }
                if name != "start":
                    assert refs == expected["refs"]
                assert data.work.model_dump_json() == original_work
                with plugin.ledger.transaction() as db:
                    sizes = {row["artifact_type"]: row["size"] for row in db.execute("""
                        SELECT artifact_type, MAX(length(CAST(body_json AS BLOB))) AS size
                        FROM immutable_artifact GROUP BY artifact_type""")}
                    checkpoint_bytes = db.execute("""SELECT length(CAST(checkpoint_json AS BLOB))
                        FROM production_run WHERE run_id=?""", (run_id,)).fetchone()[0]
                result = {
                    "phase": name, "runId": run_id, "state": current.state.value,
                    "cursor": current.cursor, "revision": current.revision,
                    "refs": refs, "fingerprints": {
                        "package": package.fingerprint, "finalPrompt": final.fingerprint,
                        "audioPlan": audio.fingerprint, "referenceBinding": binding_ref.fingerprint,
                    }, "inputMode": final.task.input_mode,
                    "readiness": prepared.readiness, "providerSubmissionAllowed": prepared.provider_submission_allowed,
                    "mediaId": selected["media"]["mediaId"],
                    "mediaHash": selected["media"]["contentHash"],
                    "calls": calls, "workBytesBefore": len(original_work.encode()),
                    "workBytesAfter": len(data.work.model_dump_json().encode()),
                    "checkpointBytes": checkpoint_bytes, "artifactBodyBytes": sizes,
                    "ledgerCounts": plugin.ledger.counts(),
                    "providerSubmission": 0, "paidCalls": 0, "mediaGeneration": 0,
                }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"phase": name, "state": result["state"], "revision": result["revision"],
        "sameRefs": name == "start" or refs == expected["refs"], "calls": calls}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("start", "resume", "terminal"))
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--prior", type=Path)
    arguments = parser.parse_args()
    asyncio.run(phase(arguments.phase, arguments.ledger, arguments.output,
        arguments.run_id, arguments.prior))
