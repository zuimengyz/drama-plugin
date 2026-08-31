"""Bounded B0/D1 validation. Prepare is read-only; --live requires the storage gate.

Use the normal plugin env only. The service env is inspected, never sourced.
No Comfy, Voice creation, rebind, alternate TTS, absolute speech timing or AV mux.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import shlex
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from drama_plugin.audio.foundation import audio_input_fingerprint, text_hash
from drama_plugin.audio.intelligibility import analyze_pcm_wav
from drama_plugin.audio.projection import compile_projected_speech_request
from drama_plugin.audio.video_conditioning import condition_audio_on_video
from drama_plugin.contracts import DPDSnapshot, Media, RealizedPerformanceSnapshot, RoleDubbingRequest, VoiceProfile
from drama_plugin.contracts.audio import ProviderVoiceMapping, TargetTimingPolicy
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.plugin import DramaPlugin
from drama_plugin.providers.speech.fish_audio import compile_fish_tts_payload, map_audio_performance_to_fish
from drama_plugin.providers.speech.role_dubbing import FishRoleDubbingProvider


def cloud_configuration_gate(workspace: Path, config_dir: Path) -> dict:
    """Only report ownership/classes, never endpoints or credentials."""
    spec = importlib.util.spec_from_file_location("env_ownership", workspace / "scripts/runtime-env-ownership.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = {"status": "RECONCILIATION_REQUIRED", "owner": "DRAMA_SERVICE", "ownership": {}}
    for owner in ("mcp-host", "drama-plugin", "drama-service"):
        try:
            module.validate(owner, config_dir / f"{owner}.env")
            result["ownership"][owner] = "PASS"
        except (ValueError, OSError) as exc:
            result["ownership"][owner] = "FAIL"
            # Ownership validator contains key names only, never values.
            result.setdefault("diagnostics", []).append(f"{owner}: {type(exc).__name__}")
    endpoints = []
    for line in (config_dir / "drama-service.env").read_text().splitlines():
        # Do not parse credential values. Ownership above examines assignment keys only.
        assignment = line.lstrip().removeprefix("export ").split("=", 1)[0].strip()
        if assignment != "DRAMA_MEDIA_STORAGE_ENDPOINT":
            continue
        tokens = shlex.split(line, comments=True)
        if tokens and tokens[0] == "export":
            tokens = tokens[1:]
        if tokens and tokens[0].startswith("DRAMA_MEDIA_STORAGE_ENDPOINT="):
            endpoints.append(tokens[0].split("=", 1)[1])
    result["endpointAssignmentCount"] = len(endpoints)
    result["endpointClasses"] = ["LOCAL" if urlsplit(value).hostname in
        {"localhost", "127.0.0.1", "::1", "0.0.0.0", "host.docker.internal"} else "NON_LOCAL" for value in endpoints]
    if (len(endpoints) == 1 and result["endpointClasses"] == ["NON_LOCAL"]
            and urlsplit(endpoints[0]).scheme in {"http", "https"}
            and urlsplit(endpoints[0]).hostname
            and all(value == "PASS" for value in result["ownership"].values())):
        result["status"] = "PASS"
    return result


async def verified_object(*, invoke, client, kind: str, metadata: dict, service_url: str,
                          destination: Path | None = None, trusted_restore: Path | None = None) -> dict:
    """Get bytes through the service owner. Missing objects never become new identities."""
    async def download():
        resolved = await invoke(f"{kind}.resolve_{kind}", {f"{kind}_id": metadata["id"]})
        expected, actual = urlsplit(service_url), urlsplit(resolved["url"])
        same_host = actual.hostname == expected.hostname or {actual.hostname, expected.hostname} <= {"localhost", "127.0.0.1", "::1"}
        if not (same_host and actual.scheme == expected.scheme and actual.port == expected.port):
            raise RuntimeError("STORAGE_OWNER_MISMATCH")
        if kind == "voice" and resolved.get("contentHash") != metadata["contentHash"]:
            raise RuntimeError("VOICE_RESOLVE_HASH_MISMATCH")
        response = await client.get(resolved["url"])
        return response

    response = await download()
    restored = False
    if response.status_code == 404:
        if kind != "media" or trusted_restore is None or not trusted_restore.is_file():
            raise RuntimeError("STORAGE_MIGRATION_RECONCILIATION_REQUIRED")
        if hashlib.sha256(trusted_restore.read_bytes()).hexdigest() != metadata["contentHash"]:
            raise RuntimeError("STORAGE_MIGRATION_RECONCILIATION_REQUIRED: untrusted restore hash")
        value = await invoke("media.restore_media_object", {
            "media_id": metadata["id"], "source_uri": trusted_restore.resolve().as_uri()})
        if value["mediaId"] != metadata["id"] or value["contentHash"] != metadata["contentHash"]:
            raise RuntimeError("RESTORE_IDENTITY_MISMATCH")
        restored = True
        response = await download()
    if response.status_code == 404:
        raise RuntimeError("STORAGE_MIGRATION_RECONCILIATION_REQUIRED")
    if response.status_code != 200:
        raise RuntimeError(f"STORAGE_DOWNLOAD_FAILED: HTTP {response.status_code}")
    digest = hashlib.sha256(response.content).hexdigest()
    if digest != metadata["contentHash"] or len(response.content) != metadata["fileSize"]:
        raise RuntimeError("STORAGE_DOWNLOAD_HASH_OR_SIZE_MISMATCH")
    if destination:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)
    return {"status": "PASS", "resolve": "PASS", "download": "PASS", "hash": "PASS",
        "id": metadata["id"], "contentHash": digest, "sizeBytes": len(response.content),
        "httpStatus": 200, "urlOwner": "DRAMA_SERVICE", "restoredSameIdentity": restored}


async def run(args):
    # MCP is a host/integration dependency, not required to import/test the core or storage checks.
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    from run_batch7_3b_fish_live import call_tool, work_voice_id, write_json
    from run_batch7_3b_1_fish_control_audit import probe_wav

    workspace = Path(__file__).resolve().parents[3]
    evidence_dir, review_dir = args.output / "evidence", args.output / "review"
    gate = cloud_configuration_gate(workspace, args.config_dir)
    write_json(evidence_dir / "storage-configuration.json", gate)
    if args.live and args.plugin_config is None:
        raise RuntimeError("EXPLICIT_PLUGIN_CONFIG_REQUIRED_FOR_LIVE")
    if args.restore_video and (gate["status"] != "PASS" or not args.confirm_service_restarted):
        raise RuntimeError("STORAGE_MIGRATION_RECONCILIATION_REQUIRED: restore requires cloud gate")
    dpd = DPDSnapshot.model_validate_json(args.dpd.read_text())
    realized = RealizedPerformanceSnapshot.model_validate_json(args.snapshot.read_text())
    async with streamable_http_client(args.mcp_url) as streams, ClientSession(*streams[:2]) as session:
        await session.initialize()

        async def invoke(name, arguments):
            return await call_tool(session, name, arguments)

        work = await invoke("work.get_work", {"work_id": args.work_id})
        shot = await invoke("shot.get_shot", {"shot_id": realized.shot_id})
        scene = await invoke("scene.get_scene", {"scene_id": shot["sceneId"]})
        episode = await invoke("episode.get_episode", {"episode_id": scene["episodeId"]})
        script = await invoke("script.get_script", {"script_id": episode["scriptId"]})
        if script["workId"] != work["id"]:
            raise RuntimeError("WORK_HIERARCHY_MISMATCH")
        voice_id = work_voice_id(work, args.speaker)
        voice = await invoke("voice.get_voice", {"voice_id": voice_id})
        video = await invoke("media.get_media", {"media_id": realized.video_media_id})
        if voice["status"] != "ACTIVE":
            raise RuntimeError("FROZEN_VOICE_NOT_ACTIVE")
        async with httpx.AsyncClient(timeout=120) as client:
            storage = {
                "video": await verified_object(invoke=invoke, client=client, kind="media", metadata=video,
                    service_url=args.service_url, trusted_restore=args.restore_video),
                "voice": await verified_object(invoke=invoke, client=client, kind="voice", metadata=voice,
                    service_url=args.service_url),
            }
        write_json(evidence_dir / "storage-resolve-hash.json", storage)
        spoken = [item for item in scene["content"]["spokenContent"] if item["id"] == dpd.effective.spoken_content_id]
        if len(spoken) != 1:
            raise RuntimeError("CANONICAL_SPOKEN_CONTENT_REQUIRED")
        profiles = json.loads(args.frozen_profiles.read_text())["items"]
        creative = [item["creativeProfile"] for item in profiles if item["speakerKey"] == args.speaker]
        if len(creative) != 1:
            raise RuntimeError("FROZEN_CREATIVE_PROFILE_REQUIRED")
        profile = VoiceProfile(profile_id=args.profile_id, speaker_key=args.speaker, creative_profile=creative[0])
        base = compile_projected_speech_request(work_id=work["id"], dpd_snapshot=dpd, spoken_content=spoken[0],
            voice_profile=profile, voice_identity_ref=voice_id, timing_policy=TargetTimingPolicy(policy="NATURAL"))
        base.material_render_parameters = {"performanceRendering": "BRIEF_CUES_V1"}
        final = condition_audio_on_video(base_request=base, dpd_snapshot=dpd, realized_snapshot=realized,
            video_media=Media.model_validate(video), shot_id=shot["id"], shot_scene_id=scene["id"],
            shot_spoken_content_ids=tuple(item["spokenContentId"] for item in shot["content"]["spokenContentBindings"]),
            canonical_spoken_content=spoken[0], observed_speaker_key=args.speaker, bound_voice_id=voice_id,
            voice_content_hash=voice["contentHash"], accepted_realized_fingerprint=realized.fingerprint)
        mappings = [item for item in voice["content"]["providerMappings"]
            if item["provider"] == "fish" and item["model"] == "s2-pro" and item["status"] == "ACTIVE"]
        if len(mappings) != 1:
            raise RuntimeError("FROZEN_MAPPING_RECONCILIATION_REQUIRED")
        mapping = ProviderVoiceMapping(provider="fish", model="s2-pro", voice_id=mappings[0]["providerVoiceId"], status="APPROVED")
        requests = {}
        source_refs = {}
        provider_fps = {}
        for label, speech in (("B0", base), ("D1", final)):
            requests[label] = RoleDubbingRequest(speech_request=speech)
            resolved = speech.model_copy(update={"provider_mapping": mapping})
            source_refs[label] = "role-dubbing:" + audio_input_fingerprint(resolved)
            performance = map_audio_performance_to_fish(speech.audio_performance_brief)
            payload = compile_fish_tts_payload(exact_text=speech.exact_text, reference_id=mapping.voice_id,
                mode="directed", speed=performance.speed, volume=performance.volume, performance_brief=speech.audio_performance_brief)
            provider_fps[label] = sha256_canonical(payload)
            write_json(evidence_dir / f"{label}-request.json", dump_contract(requests[label]))  # no provider id
        all_audio = await invoke("media.list_media", {"work_id": work["id"], "media_type": "AUDIO"})
        exact_text_matches = [item for item in all_audio if item["content"].get("exactTextHash") == text_hash(base.exact_text)]
        strict = {label: [item for item in all_audio if item["sourceRef"] == ref
            and item.get("purpose") == "ROLE_DUBBING_AUDIO"
            and item["content"].get("voiceMasterContentHash") == voice["contentHash"]
            and item["content"].get("providerRequestFingerprint") == provider_fps[label]]
            for label, ref in source_refs.items()}
        if any(len(items) > 1 for items in strict.values()):
            raise RuntimeError("AMBIGUOUS_MEDIA_RECONCILIATION_REQUIRED")
        summary = {
            "batch": "7.3D", "status": "PREPARED" if gate["status"] == "PASS" else "PARTIAL",
            "cloudMinioMigration": gate["status"], "videoMediaId": video["id"], "videoContentHash": video["contentHash"],
            "realizedPerformanceFingerprint": realized.fingerprint, "dpdFingerprint": dpd.fingerprint,
            "spokenContentFingerprint": sha256_canonical({"id": base.spoken_content_id,
                "speakerKey": base.speaker_key, "text": base.exact_text}),
            "textFingerprint": final.audio_performance_brief.text_fingerprint,
            "canonicalText": base.exact_text, "voiceId": voice_id, "voiceMasterHash": voice["contentHash"],
            "voiceMaterialFingerprint": final.video_conditioned_projection.voice_material_fingerprint,
            "baseAudioProjectionFingerprint": base.audio_performance_brief.fingerprint,
            "finalAudioProjectionFingerprint": final.video_conditioned_projection.fingerprint,
            "providerRequestFingerprints": provider_fps, "sourceRefs": source_refs,
            "mouthActivity": realized.mouth_activity, "speechWindow": "UNKNOWN", "timingPolicy": "NATURAL",
            "exactTextMatchMediaIds": [item["id"] for item in exact_text_matches],
            "strictBaselineMediaId": strict["B0"][0]["id"] if strict["B0"] else None,
            "finalAudioMediaId": strict["D1"][0]["id"] if strict["D1"] else None,
            "generationCounts": {"B0": int((evidence_dir / "B0-submission.json").exists()),
                "D1": int((evidence_dir / "D1-submission.json").exists()),
                "Comfy": 0, "VoiceDesign": 0, "CreateModel": 0},
            "safeRetryCount": 0, "userAudioVisualReview": "NOT_READY", "liveTechnicalQc": "NOT_RUN",
        }
        write_json(review_dir / "final-audio-performance-brief.json", dump_contract(final.video_conditioned_projection))
        write_json(review_dir / "video-conditioning-summary.json", summary)
        write_json(evidence_dir / "run.json", summary)
        if not args.live:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return
        if gate["status"] != "PASS" or not args.confirm_service_restarted:
            raise RuntimeError("STORAGE_MIGRATION_RECONCILIATION_REQUIRED: unique cloud config and service restart confirmation required")
        async with DramaPlugin.load(root=workspace / "drama-plugin/plugin", config_path=args.plugin_config) as plugin:
            provider = plugin.providers.role_dubbing
            if not isinstance(provider, FishRoleDubbingProvider):
                raise RuntimeError("FISH_NOT_CONFIGURED")
            # Zero auto retries for this comparison; uncertain submissions are journaled.
            provider.fish._max_transient_retries = 0
            response = await provider.fish._get("model/" + mapping.voice_id)
            if response.status_code != 200:
                raise RuntimeError("FROZEN_PROVIDER_MAPPING_UNAVAILABLE")
            for label in ("B0", "D1"):
                journal = evidence_dir / f"{label}-submission.json"
                if strict[label]:
                    audio = strict[label][0]
                else:
                    if journal.exists():
                        raise RuntimeError("AMBIGUOUS_SUBMISSION_RECONCILE_REQUIRED: do not resubmit")
                    write_json(journal, {"status": "SUBMITTED_OR_UNKNOWN", "sourceRef": source_refs[label]})
                    summary["generationCounts"][label] += 1
                    write_json(evidence_dir / "run.json", summary)
                    result = await provider.generate_role_dubbing(requests[label])
                    if result.voice_design_calls or result.create_model_calls or result.voice_id != voice_id:
                        raise RuntimeError("FROZEN_VOICE_BOUNDARY_VIOLATION")
                    audio = await invoke("media.get_media", {"media_id": result.audio_media_id})
                    write_json(journal, {"status": "DURABLE", "mediaId": audio["id"], "sourceRef": source_refs[label]})
                name = "B0-baseline.wav" if label == "B0" else "D1-video-conditioned.wav"
                async with httpx.AsyncClient(timeout=120) as client:
                    verified = await verified_object(invoke=invoke, client=client, kind="media", metadata=audio,
                        service_url=args.service_url, destination=review_dir / name)
                qc = {**probe_wav(review_dir / name), **analyze_pcm_wav(review_dir / name),
                    "intelligibilityQc": audio["content"]["intelligibilityQc"], "download": verified}
                if qc["obviousClipping"] or qc["intelligibilityQc"]["status"] != "PASS":
                    raise RuntimeError("TECHNICAL_QC_FAILED")
                write_json(evidence_dir / f"{label}-qc.json", qc)
                summary["strictBaselineMediaId" if label == "B0" else "finalAudioMediaId"] = audio["id"]
            summary.update(status="PASS", userAudioVisualReview="PENDING", liveTechnicalQc="PASS")
            write_json(evidence_dir / "run.json", summary)
            write_json(review_dir / "video-conditioning-summary.json", summary)
            print(json.dumps(summary, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mcp-url", "service-url", "work-id", "speaker", "profile-id"):
        parser.add_argument("--" + name, required=True)
    for name in ("config-dir", "dpd", "snapshot", "frozen-profiles", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--plugin-config", type=Path)
    parser.add_argument("--restore-video", type=Path)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-service-restarted", action="store_true")
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except Exception as exc:
        # Never print provider exceptions with URLs or raw payloads.
        print(f"BATCH_7_3D_STOPPED: {type(exc).__name__}")
        pending = [exc]
        while pending:
            error = pending.pop()
            if isinstance(error, BaseExceptionGroup):
                pending.extend(error.exceptions)
                continue
            trace = error.__traceback__
            while trace and trace.tb_next:
                trace = trace.tb_next
            print(f"SAFE_CAUSE: {type(error).__name__} at "
                  f"{Path(trace.tb_frame.f_code.co_filename).name}:{trace.tb_lineno}" if trace else type(error).__name__)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
