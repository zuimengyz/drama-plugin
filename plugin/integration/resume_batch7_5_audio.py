"""Materialize only user-selected candidate 1, bind it, and make one DPD-led take.

The source video is stale for dialogue performance; it must not condition this take.
Journals preserve known/uncertain paid submissions. No Voice Design or Turn B TTS.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
from pathlib import Path

from drama_plugin.audio.foundation import audio_input_fingerprint, text_hash
from drama_plugin.audio.projection import compile_projected_speech_request, fingerprint_audio_projection
from drama_plugin.audio.intelligibility import analyze_pcm_wav
from drama_plugin.contracts import DPDSnapshot, RoleDubbingRequest, VoiceProfile, TargetTimingPolicy, ProviderVoiceMapping
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.voice import VoiceContent, VoiceSourceType
from drama_plugin.plugin import DramaPlugin
from drama_plugin.providers.speech.fish_audio import compile_fish_tts_payload, map_audio_performance_to_fish
from drama_plugin.providers.speech.role_dubbing import FishRoleDubbingProvider
from drama_plugin.providers.http.media_source import allowed_media_roots
from run_batch7_5_voice_review import ROOT, EVIDENCE, REVIEW, WORK, SPEAKER, VOICE, AUDIO_A, AUDIO_B, VIDEO, digest, write


async def run(tts: bool) -> None:
    approval = json.loads((EVIDENCE / "user-voice-choice.json").read_text())
    design = json.loads((EVIDENCE / "voice-design-request.json").read_text())
    result = json.loads((EVIDENCE / "phase-a-result.json").read_text())
    candidate = next(c for c in result["candidates"] if c["label"] == "1")
    path = Path(candidate["path"])
    assert approval["candidateHash"] == candidate["sha256"] == digest(path)
    assert approval["source"] == "USER" and approval["designRequestFingerprint"] == design["fingerprint"]
    plugin = DramaPlugin.load(root=ROOT / "drama-plugin/plugin", config_path=ROOT / "drama-plugin/plugin/config/drama-service-http.example.yaml")
    try:
        provider, voices = plugin.providers.role_dubbing, plugin.providers.voice
        assert isinstance(provider, FishRoleDubbingProvider) and voices is not None
        provider.fish._max_transient_retries = 0
        before = [await plugin.providers.media.get_media(x) for x in (AUDIO_A, AUDIO_B, VIDEO)]
        old_voice = await voices.get_voice(VOICE)
        work = await plugin.providers.memory.get_work(WORK)
        existing = [v for v in await voices.search_voices() if v.content.source_provenance.get("designRequestFingerprint") == design["fingerprint"]]
        assert len(existing) <= 1
        current_binding = next(v["voiceId"] for v in work.content["voiceProfiles"] if v["speakerKey"] == SPEAKER)
        assert current_binding in {VOICE, *(v.id for v in existing)}
        journal = EVIDENCE / "voice-materialization.json"
        if existing:
            voice = existing[0]
        else:
            if journal.exists() and json.loads(journal.read_text())["status"] != "NOT_SUBMITTED_LOCAL_ROOT_REJECTED":
                raise RuntimeError("VOICE_IMPORT_OUTCOME_UNKNOWN")
            # Stage identical approved bytes inside the existing configured import root.
            staging_root = next(r for r in allowed_media_roots() if r.is_dir() and str(r).startswith(str(ROOT)))
            staging = staging_root / "batch7-5-selected-candidate-1.wav"
            if staging.exists():
                assert digest(staging) == digest(path)
            else:
                shutil.copyfile(path, staging)
            write(journal, {"status": "IMPORT_SUBMITTED_OR_UNKNOWN", "candidateHash": digest(path)})
            voice = await voices.import_voice(
                name="王思礼 Character Dialogue — Batch 7.5 用户候选1",
                source_type=VoiceSourceType.DESIGNED, source_uri=staging.resolve().as_uri(),
                duration_ms=round(candidate["decodedDurationMs"]),
                content=VoiceContent(creative_casting_profile=design["castingProfile"], source_provenance={
                    "voiceUseCase": "CHARACTER_DIALOGUE", "designRequestFingerprint": design["fingerprint"],
                    "referenceText": candidate["text"], "referenceTextHash": text_hash(candidate["text"]),
                    "candidateCount": 2, "masterSelection": {"candidateIndex": candidate["providerIndex"],
                        "candidateId": candidate["candidateId"], "contentHash": digest(path),
                        "artisticApproval": {"status": "USER_APPROVED", "source": "USER", "userText": approval["userText"]}},
                }))
            write(journal, {"status": "IMPORTED", "voiceId": voice.id, "candidateHash": digest(path)})
        assert voice.content_hash == digest(path)
        mappings = [m for m in voice.content.provider_mappings if m.provider == "fish" and m.model == "s2-pro" and m.status == "ACTIVE"]
        assert len(mappings) <= 1
        if not mappings:
            if json.loads(journal.read_text())["status"] == "MATERIALIZATION_SUBMITTED_OR_UNKNOWN":
                raise RuntimeError("MATERIALIZATION_OUTCOME_UNKNOWN")
            write(journal, {"status": "MATERIALIZATION_SUBMITTED_OR_UNKNOWN", "voiceId": voice.id})
            voice, mapping = await provider._materialize_mapping(voice)
            write(journal, {"status": "MATERIALIZED", "voiceId": voice.id, "createModelCalls": 1})
        else:
            mapping = mappings[0]
        await voices.download_voice(voice.id, REVIEW / "new-voice-master.wav")
        assert digest(REVIEW / "new-voice-master.wav") == candidate["sha256"]
        current = await plugin.providers.memory.get_work(WORK)
        binding = next(v["voiceId"] for v in current.content["voiceProfiles"] if v["speakerKey"] == SPEAKER)
        if binding == VOICE:
            current = await plugin.providers.memory.bind_work_voice(WORK, SPEAKER, voice.id, current.version)
        else:
            assert binding == voice.id
        write(EVIDENCE / "voice-binding-transition.json", {"status": "PASS", "newVoiceId": voice.id,
            "newMasterHash": voice.content_hash, "oldVoiceId": VOICE, "workVersion": current.version,
            "candidate": 1, "voiceDesignCalls": 0, "createModelCalls": 1, "masterCloudHash": "PASS"})
        assert dump_contract(await voices.get_voice(VOICE)) == dump_contract(old_voice)
        dpd = DPDSnapshot.model_validate_json((ROOT / "artifacts/resume-7-4b-turn-a/evidence/turn-a-production-dpd.json").read_text())
        scene = await plugin.providers.memory.get_scene(dpd.effective.scene_id)
        shot = await plugin.providers.memory.get_shot("shot_83db7eb53b2f49d3a58428d4659e584e")
        spoken = next(s for s in scene.content["spokenContent"] if s["id"] == dpd.line.spoken_content_id)
        profiles = json.loads((ROOT / "artifacts/batch7-2/evidence/voice-profile-7.2s-r.json").read_text())["items"]
        profile = VoiceProfile.model_validate(next(p for p in profiles if p["speakerKey"] == SPEAKER))
        speech = compile_projected_speech_request(work_id=WORK, dpd_snapshot=dpd, spoken_content=spoken,
            voice_profile=profile, voice_identity_ref=voice.id, timing_policy=TargetTimingPolicy(policy="NATURAL"),
            non_material_metadata={"shotId": shot.id})
        # A production take of the current DPD, authored in the existing neutral brief.
        # It does not borrow the old video's RP or its finality-conditioned delivery.
        brief = speech.audio_performance_brief.model_copy(update={
            "control": "Interactive character dialogue to a nearby listener; controlled breath, non-broadcast cadence",
            "intensity": "contained private urgency without raised volume",
            "rhythm": "direct request with responsive phrasing",
            "pause_strategy": "brief natural clause turns; keep addressing the listener",
            "sentence_ending": "leave the decision open to the listener after the request",
            "pace_tendency": "NEUTRAL",
            "pace": "Natural conversational pace; do not stretch to a planned duration",
        })
        brief = brief.model_copy(update={"fingerprint": fingerprint_audio_projection(brief)})
        speech.audio_performance_brief = type(brief).model_validate(dump_contract(brief))
        speech.material_render_parameters = {"performanceRendering": "BRIEF_CUES_V1"}
        request = RoleDubbingRequest(speech_request=speech)
        resolved_mapping = ProviderVoiceMapping(provider="fish", model="s2-pro", voice_id=mapping.provider_voice_id)
        resolved = speech.model_copy(update={"provider_mapping": resolved_mapping,
            "voice_profile": profile.model_copy(update={"provider_mappings": [resolved_mapping]})})
        performance = map_audio_performance_to_fish(speech.audio_performance_brief)
        payload = compile_fish_tts_payload(exact_text=speech.exact_text, reference_id=mapping.provider_voice_id,
            mode="directed", speed=performance.speed, volume=performance.volume, performance_brief=speech.audio_performance_brief)
        fp = audio_input_fingerprint(resolved)
        write(EVIDENCE / "turn-a-request.json", dump_contract(request))
        write(EVIDENCE / "turn-a-resolved-request.json", dump_contract(resolved))
        write(EVIDENCE / "current-context.json", {"work": dump_contract(current), "scene": dump_contract(scene),
            "shot": dump_contract(shot), "voice": dump_contract(voice), "oldMedia": [dump_contract(m) for m in before]})
        write(EVIDENCE / "turn-a-projection.json", {"dpdFingerprint": dpd.fingerprint,
            "inputFingerprint": fp, "providerRequestFingerprint": sha256_canonical(payload),
            "brief": dump_contract(brief), "renderedText": payload["text"], "speed": performance.speed,
            "volume": performance.volume, "performanceAuthority": "DPD_AUDIO_PROJECTION", "oldRpReused": False})
        if not tts:
            print("VOICE_BOUND=PASS; TURN_A_PROJECTION=READY; TTS=0")
            return
        existing_audio = await plugin.providers.media.list_media(work_id=WORK, media_type="AUDIO",
            purpose="ROLE_DUBBING_AUDIO", source_ref=f"role-dubbing:{fp}")
        assert len(existing_audio) <= 1
        tts_journal = EVIDENCE / "turn-a-submission.json"
        if existing_audio:
            media = existing_audio[0]
        else:
            if tts_journal.exists():
                raise RuntimeError("TTS_OUTCOME_UNKNOWN_DO_NOT_RESUBMIT")
            write(tts_journal, {"status": "SUBMITTED_OR_UNKNOWN", "primaryTts": 1, "inputFingerprint": fp})
            response = await provider.generate_role_dubbing(request)
            media = await plugin.providers.media.get_media(response.audio_media_id)
            write(tts_journal, {"status": "DURABLE", "primaryTts": 1, "asrQc": 1, "mediaId": media.id})
        await plugin.providers.media.download_media(media.id, REVIEW / "02-turn-a-after.wav")
        assert digest(REVIEW / "02-turn-a-after.wav") == media.content_hash
        qc = analyze_pcm_wav(REVIEW / "02-turn-a-after.wav")
        assert not qc["obviousClipping"] and media.content["intelligibilityQc"]["status"] == "PASS"
        after = [await plugin.providers.media.get_media(x) for x in (AUDIO_A, AUDIO_B, VIDEO)]
        assert [dump_contract(m) for m in before] == [dump_contract(m) for m in after]
        write(EVIDENCE / "turn-a-result.json", {"technicalStatus": "PASS", "artisticStatus": "USER_REVIEW_PENDING",
            "media": dump_contract(media), "voiceId": voice.id, "voiceHash": voice.content_hash,
            "cloudHash": "PASS", "signalQc": qc, "turnBFrozen": "PASS", "primaryTts": 1, "asrQc": 1,
            "safeRetries": 0, "rootCause": "VOICE_IDENTITY", "selectedVoiceArtisticAuthority": "USER"})
        print(f"TURN_A_AUDIO={media.id}; DURATION={media.duration_ms}; CLOUD_HASH=PASS; TURN_B_UNCHANGED=PASS")
    finally:
        await plugin.aclose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tts", action="store_true")
    asyncio.run(run(parser.parse_args().tts))
