"""E2 real designated-source cold-start, three-process Target shadow (offline only)."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.creative_engine.contracts import (
    AuthorRequest, CanonDraft, DesignBody, Dialogue, SceneBody, ScriptBody, ShotBody, SourceBody, WorkBody,
)
from drama_plugin.execution.audio import ApprovedAudioConsumer
from drama_plugin.execution.contracts import Authorization, FinishingRecipe, ProviderResult, ReviewedAVCandidate
from drama_plugin.execution.review import MockReviewer
from drama_plugin.execution.transport import ReplayTransport
from drama_plugin.generation.contracts import AudioExecutionPlan, GenerationPreparation, GenerationTask
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.runtime import RunMode, RuntimeState

ROOT = Path(__file__).resolve().parents[1]
DESIGNATED_SOURCE = Path("/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/source/designated-source.txt")


class OfflineAuthors:
    """Pinned author fixture, never a production model or legacy Host workflow."""
    def __init__(self):
        self.calls: list[str] = []

    async def author(self, request: AuthorRequest) -> CanonDraft | ShotBody:
        if request.canon is None:
            self.calls.append("canon")
            return CanonDraft(work=WorkBody(interpretation="A claim of indifference is contradicted by remembered suffering.",
                dramatic_intent="Expose the gap between denial and responsibility.", character_meaning="Remembering the child reveals an unresolved obligation."),
                script=ScriptBody(screenplay="The child asks for help. The man turns away; the encounter remains in memory."),
                scene=SceneBody(scene_text="On the empty wet street, the child takes the man's elbow. He turns away, and she runs towards another passer-by.",
                    dialogue=(Dialogue(id="child-plea", speaker="child", text="Mammy, mammy!", must_keep=True),)))
        self.calls.append("direction")
        return ShotBody(purpose="Make refusal and the child's persistence visible together",
            required_transition="The man turns away and the child releases his elbow", duration_ms=6000,
            subject_action="The child holds the elbow; the man turns away; she releases it",
            entry_state="The child beside the man, holding his elbow", exit_state="The child releases him and looks towards the passer-by",
            coverage="Retain the child's reaching hand and the man's turn in one view",
            blocking_intent="Keep the physical relation legible", camera_intent="Observe the pair at street level",
            editing_relation="Hold until the hand releases", performance_direction="The turn interrupts the child's appeal",
            spoken_ids=("child-plea",), professional_domains=tuple(sorted(("CAMERA", "WORLD", "SUBJECTS", "SOUND", "LIGHTING"))))

    async def design(self, request: AuthorRequest) -> tuple[DesignBody, ...]:
        self.calls.append("professional")
        return (DesignBody(domain="CAMERA", facts={"perspective": "Both faces and the reaching hand visible", "camera_movement": "Fixed"}),
            DesignBody(domain="WORLD", facts={"location_identity": "An empty wet street", "topology": "Open passage beside the pair"}),
            DesignBody(domain="SUBJECTS", facts={"character_ref": "child", "face_structure": "The frightened child retains the approved fixture appearance"}),
            DesignBody(domain="LIGHTING", facts={"source": "Street lamp", "direction": "From the side"}),
            DesignBody(domain="SOUND", facts={"ambience": "Damp quiet street", "silence_design": "No added score"}))


def offline_guard(*args: object, **kwargs: object) -> None:
    raise AssertionError("E2 forbids network/provider transport and legacy orchestration")


def load(directory: Path) -> tuple[DramaPlugin, OfflineAuthors]:
    import drama_plugin.plugin as module
    module.load_config = lambda _: DramaPluginConfig()
    socket.socket.connect = offline_guard
    socket.socket.connect_ex = offline_guard
    from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
    from drama_plugin.hosts.creative_source import CreativeSourceHost
    DirectorArtifactStore.transition = offline_guard
    CreativeSourceHost.director_handoff = offline_guard
    authors = OfflineAuthors()
    video = directory / "recorded-fixture.mp4"
    transports = {}
    if video.exists():
        result = ProviderResult(result_id="e2-recorded-result", locator=str(video),
            expected_hash=hashlib.sha256(video.read_bytes()).hexdigest())
        transports["offline-replay"] = ReplayTransport(directory / "replay", result)
    p = DramaPlugin.load(ROOT, mock_data=MockDramaData(), ledger_path=directory / "production.sqlite3",
        creative_root=directory / "creative-owner", canon_author=authors, direction_author=authors,
        professional_author=authors, target_transports=transports,
        target_reviewer=MockReviewer(), target_audio=ApprovedAudioConsumer())
    return p, authors


async def phase(directory: Path, number: int) -> None:
    p, authors = load(directory)
    trace: list[str] = []
    execute = p.runtime.executor.execute
    async def record(key, inputs):
        trace.append(key)
        return await execute(key, inputs)
    p.runtime.executor.execute = record
    if number == 1:
        text = DESIGNATED_SOURCE.read_text()
        source = SourceBody(goal="Verify a source-pinned cold-start creative chain for the designated literary work",
            text=text, external_reference=str(DESIGNATED_SOURCE), spoken_language="en", subtitle_languages=("zh",))
        r = p.create_film_run(work_id="e2-source-shadow", source=source, mode=RunMode.PRODUCTION, run_id="cold-start")
        done = await p.runtime.run(r.run_id)
        assert done.state == RuntimeState.WAITING_USER
        assert authors.calls == ["canon", "direction", "professional"]
    elif number == 2:
        cp = p.creative.state.checkpoint("cold-start")
        await p.decide_target_run("cold-start", decision_id=p.runtime.decision_id("cold-start"),
            accepted=True, source_ref=cp.candidate_ref)
        done = await p.runtime.run("cold-start")
        assert done.state == RuntimeState.SUCCEEDED and not authors.calls
        cp = p.creative.state.checkpoint("cold-start")
        r = p.runtime.store.load("cold-start")
        g = p.create_generation_run(work_id=r.scope.work_id, scene_id=r.scope.scene_id, shot_id=r.scope.shot_id,
            mode=RunMode.PRODUCTION, package_ref=cp.package_ref, run_id="prepare",
            task=GenerationTask(input_mode="text_to_video"))
        done = await p.runtime.run(g.run_id)
        assert done.state == RuntimeState.SUCCEEDED, done
    else:
        ready_ref = p.generation_artifacts.prepared("prepare")
        ready = p.generation_artifacts.get(ready_ref, GenerationPreparation)
        audio = p.generation_artifacts.get(ready.audio_plan_ref, AudioExecutionPlan)
        approval = p.creative.state.checkpoint("cold-start").decision_ref
        assert approval is not None
        recipe = FinishingRecipe.seal(scope=audio.scope, run_id="candidate", source_package_ref=ready.source_package_ref,
            preparation_ref=ready_ref, audio_plan_ref=ready.audio_plan_ref, approval_ref=approval, native_policy="PRESERVE")
        r = p.create_execution_run(run_id="candidate", mode=RunMode.PRODUCTION, preparation_ref=ready_ref,
            authorization=Authorization(approval_ref=approval, authorized=True,
                estimated_cost_microunits=0, budget_microunits=0), recipe=recipe, route="offline-replay")
        done = await p.runtime.run(r.run_id)
        assert done.state == RuntimeState.SUCCEEDED, done
        candidate = p.execution.store.get(done.last_result.artifact_refs[0], ReviewedAVCandidate)
        assert candidate.readiness == "REVIEWED_AV_CANDIDATE" and not candidate.final_delivery
        assert not authors.calls
    cp = p.creative.state.checkpoint("cold-start")
    result = {"phase": number, "state": done.state.value, "author_calls": authors.calls,
        "runtime_trace": trace, "creative_refs": [r.model_dump(mode="json", by_alias=True) for r in cp.refs],
        "package_ref": cp.package_ref.model_dump(mode="json") if cp.package_ref else None,
        "EXTERNAL_AGENT_INTERNAL_TOOL_SELECTION": 0, "REAL_PROVIDER_SUBMISSION": 0,
        "PAID_GENERATION_CALLS": 0, "LIVE_MEDIA_GENERATION": 0}
    (directory / f"phase-{number}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--phase", type=int)
    args = parser.parse_args()
    directory = args.directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    if args.phase:
        asyncio.run(phase(directory, args.phase))
        return
    # Local technical replay fixture, not a model/provider generation.
    video = directory / "recorded-fixture.mp4"
    if not video.exists():
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=64x64:r=10",
            "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000", "-t", "6", "-c:v", "libx264",
            "-pix_fmt", "yuv420p", "-c:a", "aac", str(video)], check=True, capture_output=True)
    for number in (1, 2, 3):
        subprocess.run([sys.executable, __file__, "--directory", str(directory), "--phase", str(number)], check=True)
    data = {"fixture": "《一个荒唐人的梦》 designated English source; no inherited visuals/Canon",
        "source_path": str(DESIGNATED_SOURCE), "source_hash": hashlib.sha256(DESIGNATED_SOURCE.read_bytes()).hexdigest(),
        "cold_start_input": "SOURCE_TEXT_ONLY", "source_language_policy": "source_original", "spoken_language": "en",
        "user_decision": "deterministic offline ADOPTION receipt; not a real production approval",
        "phases": [json.loads((directory / f"phase-{n}.json").read_text()) for n in (1, 2, 3)],
        "TARGET_MAIN_CHAIN_END": "APPROVED_PRODUCTION_PACKAGE", "E1_SMOKE_END": "REVIEWED_AV_CANDIDATE",
        "PLUGIN_IS_ENGINE_FOR_SOURCE_TO_REVIEWED_CANDIDATE": "YES", "TARGET_FINAL_DELIVERY_IMPLEMENTED": "NO"}
    (directory / "shadow-summary.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(json.dumps({"E2_shadow": "PASS", "phases": 3, "end": "APPROVED_PRODUCTION_PACKAGE", "smoke": "REVIEWED_AV_CANDIDATE"}))


if __name__ == "__main__":
    main()
