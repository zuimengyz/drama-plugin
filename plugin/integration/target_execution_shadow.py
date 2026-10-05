"""E1 real S02-K02 preparation + completely offline multi-process execution.

Five independent processes restore the same Ledger. Optional worker/crash modes
exercise concurrent dispatch and true process death after a synthetic send.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.execution.audio import ApprovedAudioConsumer
from drama_plugin.execution.contracts import (
    Authorization, ExecutionOperation, FinishingRecipe, ProviderAttempt, ProviderResult,
    ReviewedAVCandidate,
)
from drama_plugin.execution.review import MockReviewer
from drama_plugin.execution.transport import ReplayTransport
from drama_plugin.generation.contracts import AudioExecutionPlan, FinalPromptArtifact, GenerationPreparation, GenerationTask
from drama_plugin.runtime import ArtifactReference, RunMode, RuntimeState
from drama_plugin.runtime.contracts import CapabilityInput
from drama_plugin.production.contracts import SourceReference
from durable_persistence_shadow import data_from_current_sources, forbidden
from prompt_obligation_reconciliation_shadow import PLUGIN, PROJECT, reconcile

RUN_ID = "e1-s02-k02-execution"
APPROVAL = ArtifactReference(owner="user-decision", artifact_ref="E1-offline-shadow-authorized", version=1)


def synthetic_video(path: Path, duration_ms: int) -> ProviderResult:
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=64x64:r=10",
        "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000", "-t", str(duration_ms / 1000),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(path)], check=True, capture_output=True)
    return ProviderResult(result_id="E1-S02-K02-recorded-synthetic-result", locator=str(path),
        expected_hash=hashlib.sha256(path.read_bytes()).hexdigest())


async def phase(name: str, directory: Path, behavior: str, label: str | None) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    data = data_from_current_sources()
    before = data.work.model_dump_json()
    database = directory / "ledger.sqlite3"
    prior = json.loads((directory / "prepare.json").read_text()) if name != "prepare" else None
    result = ProviderResult.model_validate(prior["providerResult"]) if prior else None
    transport = ReplayTransport(directory / "remote", result, behavior=behavior) if result else None
    with patch("drama_plugin.plugin.load_config", return_value=DramaPluginConfig()), \
         patch.object(socket.socket, "connect", forbidden), patch.object(socket.socket, "connect_ex", forbidden), \
         patch("drama_plugin.professional.compile_prompt_projection", forbidden), \
         patch("drama_plugin.hosts.cinematic_projection.project", forbidden), \
         patch("drama_plugin.visual.video_prompt.compile_request_ir", forbidden):
        async with DramaPlugin.load(PLUGIN, mock_data=data, legacy_reads=True, production_artifact_roots=(PROJECT / "S02-design",),
                ledger_path=database, target_transports={"offline-replay": transport} if transport else {},
                target_reviewer=MockReviewer(), target_audio=ApprovedAudioConsumer()) as plugin:
            assert plugin.execution is not None
            if name == "prepare":
                _, binding, _, _ = reconcile()
                binding_ref = plugin.execution_references.register(binding)
                run = plugin.create_generation_run(work_id=data.work.id, scene_id=data.scene.id,
                    shot_id=data.shot.id, mode=RunMode.EXPERIMENT, run_id="e1-s02-k02-preparation",
                    task=GenerationTask(input_mode="image_to_video", native_audio="REQUIRED"))
                ready = await plugin.runtime.run(run.run_id)
                assert ready.state == RuntimeState.SUCCEEDED
                preparation_ref = plugin.generation_artifacts.prepared(run.run_id)
                prepared = plugin.generation_artifacts.get(preparation_ref, GenerationPreparation)
                plan = plugin.generation_artifacts.get(prepared.audio_plan_ref, AudioExecutionPlan)
                result = synthetic_video(directory / "recorded.mp4", plan.duration_ms)
                transport = ReplayTransport(directory / "remote", result)
                plugin.execution.transports["offline-replay"] = transport
                recipe = FinishingRecipe.seal(scope=plan.scope, run_id=RUN_ID,
                    source_package_ref=prepared.source_package_ref, preparation_ref=preparation_ref,
                    audio_plan_ref=prepared.audio_plan_ref, approval_ref=APPROVAL, native_policy="PRESERVE")
                plugin.create_execution_run(run_id=RUN_ID, mode=RunMode.EXPERIMENT,
                    preparation_ref=preparation_ref, authorization=Authorization(approval_ref=APPROVAL,
                        authorized=True, estimated_cost_microunits=0, budget_microunits=0),
                    recipe=recipe, route="offline-replay")
            else:
                preparation_ref = ArtifactReference.model_validate(prior["preparationRef"])
                binding_ref = SourceReference.model_validate(prior["referenceBindingRef"])
                prepared = plugin.generation_artifacts.get(preparation_ref, GenerationPreparation)
                plan = plugin.generation_artifacts.get(prepared.audio_plan_ref, AudioExecutionPlan)
            run = plugin.runtime.store.load(RUN_ID)
            inputs = CapabilityInput(run_id=RUN_ID, operation_id=RUN_ID + ":0", scope=run.scope)
            if name == "prepare":
                checkpoint = plugin.execution.reserve(inputs)
            else:
                with patch.object(plugin.shot_assembler, "assemble", forbidden), \
                     patch.object(plugin.prompt_compiler.generator, "generate", forbidden), \
                     patch.object(plugin.providers.production, "generate_video", forbidden):
                    if name == "worker":
                        await plugin.execution.execute(inputs)
                        await plugin.execution.intake(inputs)
                    elif name == "provider":
                        recovered = await plugin.runtime.recover_run(RUN_ID)
                        if recovered.state == RuntimeState.BLOCKED:
                            await plugin.runtime.retry(RUN_ID)
                        current = await plugin.runtime.run(RUN_ID, max_ticks=2 if recovered.state == RuntimeState.PLANNED else 1)
                        assert current.cursor == 1 and current.state == RuntimeState.READY, current
                    elif name == "media":
                        current = await plugin.runtime.run(RUN_ID, max_ticks=2)
                        assert current.cursor == 3 and current.state == RuntimeState.READY, current
                    elif name == "finish":
                        current = await plugin.runtime.run(RUN_ID)
                        assert current.state == RuntimeState.SUCCEEDED, current
                    elif name == "terminal":
                        recovered = await plugin.runtime.recover_run(RUN_ID)
                        assert recovered.state == RuntimeState.SUCCEEDED
                        assert await plugin.runtime.run(RUN_ID) == recovered
                operation, _, _ = plugin.execution._approved(inputs)
                checkpoint = plugin.execution.store.checkpoint(operation.artifact_reference())
            operation = plugin.execution.store.get(checkpoint.operation_ref, ExecutionOperation)
            attempt = plugin.execution.store.get(checkpoint.attempt_ref, ProviderAttempt)
            package = plugin.production_packages.get(prepared.source_package_ref)
            final = plugin.generation_artifacts.get(prepared.final_prompt_ref, FinalPromptArtifact)
            fingerprints = {"package": package.fingerprint, "promptIR": final.prompt_ir_fingerprint,
                "finalPrompt": final.fingerprint, "audioPlan": plan.fingerprint,
                "referenceBinding": binding_ref.fingerprint if hasattr(binding_ref, "fingerprint") else prior["fingerprints"]["referenceBinding"]}
            assert final.task.input_mode == "image_to_video" and operation.reference_bindings
            if prior:
                assert fingerprints == prior["fingerprints"]
                assert operation.artifact_reference().model_dump(mode="json") == prior["operationRef"]
                assert attempt.artifact_reference().model_dump(mode="json") == prior["attemptRef"]
            assert data.work.model_dump_json() == before
            candidate = plugin.execution.store.get(checkpoint.progress.candidate_ref, ReviewedAVCandidate) if checkpoint.progress.candidate_ref else None
            state = plugin.runtime.store.load(RUN_ID)
            log = directory / "remote/submissions.jsonl"
            sends = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            assert len(sends) <= 1
            if sends:
                assert sends[0]["promptText"] == final.prompt_text
            payload = {"phase": name, "pid": os.getpid(), "runId": RUN_ID, "state": state.state.value,
                "cursor": state.cursor, "operationState": checkpoint.state.value,
                "preparationRef": preparation_ref.model_dump(mode="json"),
                "referenceBindingRef": binding_ref.model_dump(mode="json"), "fingerprints": fingerprints,
                "operationRef": operation.artifact_reference().model_dump(mode="json"),
                "attemptRef": attempt.artifact_reference().model_dump(mode="json"),
                "receiptRef": checkpoint.receipt_ref.model_dump(mode="json") if checkpoint.receipt_ref else None,
                "progress": checkpoint.progress.model_dump(mode="json"),
                "candidate": candidate.model_dump(mode="json") if candidate else None,
                "providerResult": result.model_dump(mode="json"), "syntheticSubmissions": len(sends),
                "fingerprintsUnchanged": prior is None or fingerprints == prior["fingerprints"],
                "workBytesBefore": len(before.encode()), "workBytesAfter": len(data.work.model_dump_json().encode()),
                "realProviderSubmission": 0, "paidCalls": 0, "liveMediaGeneration": 0}
    (directory / ((label or name) + ".json")).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"phase": name, "state": payload["state"], "operationState": payload["operationState"],
        "syntheticSubmissions": len(sends)}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("all", "prepare", "provider", "media", "finish", "terminal", "worker"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--behavior", default="success")
    parser.add_argument("--label")
    args = parser.parse_args()
    directory = args.directory.resolve()
    if args.phase == "all":
        phases = ("prepare", "provider", "media", "finish", "terminal")
        for name in phases:
            subprocess.run([sys.executable, str(Path(__file__).resolve()), name, "--directory", str(directory)],
                           check=True, timeout=60)
        results = [json.loads((directory / (name + ".json")).read_text()) for name in phases]
        summary = {"end": results[-1]["candidate"]["readiness"], "processIds": [r["pid"] for r in results],
            "syntheticSubmissions": results[-1]["syntheticSubmissions"], "realProviderSubmission": 0,
            "fingerprintsUnchanged": all(r["fingerprintsUnchanged"] for r in results),
            "fingerprints": results[0]["fingerprints"], "operationRef": results[-1]["operationRef"],
            "attemptRef": results[-1]["attemptRef"], "receiptRef": results[-1]["receiptRef"],
            "candidate": results[-1]["candidate"]}
        (directory / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    else:
        asyncio.run(phase(args.phase, directory, args.behavior, args.label))


if __name__ == "__main__":
    main()
