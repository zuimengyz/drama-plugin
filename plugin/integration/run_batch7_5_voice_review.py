"""Batch 7.5 Phase A only: two unbound voice auditions, then a human gate.

No production TTS, Voice import/materialization/binding, video or domain writes.
--live consumes one Fish Voice Design request with n=2. A journal forbids replay.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import wave
from pathlib import Path

from drama_plugin.audio.creative_casting import compile_fish_creative_casting_brief
from drama_plugin.audio.intelligibility import analyze_pcm_wav
from drama_plugin.contracts import DPDSnapshot, VoiceProfile
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.dpd import fingerprint_dpd
from drama_plugin.plugin import DramaPlugin
from drama_plugin.providers.speech.fish_audio import compile_fish_voice_design_payload
from drama_plugin.providers.speech.role_dubbing import FishRoleDubbingProvider
from run_fish_role_dubbing_validation import build_creative_casting_profile

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/batch7-5"
EVIDENCE, REVIEW = OUT / "evidence", OUT / "review"
WORK = "work_9cc5d11969a64f93bce4a544f349c793"
SPEAKER = "speaker:wangsili"
VOICE = "voice_06ac45335157432e8322a9b32e8d9804"
AUDIO_A = "media_76a8fb24233246189d030babc7ceffd4"
AUDIO_B = "media_6f4d16d785b84b52b3062e0666a826b5"
VIDEO = "media_ac9d14c5cdc74c43ba44562752cf9489"


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode(path: Path) -> bytes:
    return subprocess.run([
        "ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le",
        "-ac", "1", "-ar", "24000", "pipe:1",
    ], check=True, capture_output=True).stdout


def dialogue_preview(candidate: Path, partner: Path, destination: Path) -> dict:
    a, b = decode(candidate), decode(partner)
    # Audition spacing only. This is neither reconciliation nor accepted timing.
    pre, gap, post = bytes(24000), bytes(38400), bytes(24000)
    with wave.open(str(destination), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(24000)
        output.writeframes(pre + a + gap + b + post)
    return {"path": str(destination), "sha256": digest(destination),
            "turnACount": 1, "turnBCount": 1, "overlap": False,
            "turnADecodedHash": hashlib.sha256(a).hexdigest(),
            "turnBDecodedHash": hashlib.sha256(b).hexdigest(),
            "durationMs": (len(pre + a + gap + b + post) * 1000 / 48000),
            "timingAuthority": "AUDITION_ONLY", "ratePitchTrim": "NONE"}


async def run(live: bool) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    user = json.loads((EVIDENCE / "user-voice-differential.json").read_text())
    if user["voiceMasterNarratorBias"] != "PRESENT" or user["authority"] != "USER_REVIEW":
        raise RuntimeError("VOICE_IDENTITY_FAILURE_NOT_ESTABLISHED")
    dpd = DPDSnapshot.model_validate_json((ROOT / "artifacts/resume-7-4b-turn-a/evidence/turn-a-production-dpd.json").read_text())
    assert dpd.fingerprint == fingerprint_dpd(dpd)
    plugin = DramaPlugin.load(root=ROOT / "drama-plugin/plugin", config_path=ROOT / "drama-plugin/plugin/config/drama-service-http.example.yaml")
    try:
        provider, voices = plugin.providers.role_dubbing, plugin.providers.voice
        if not isinstance(provider, FishRoleDubbingProvider) or voices is None:
            raise RuntimeError("FISH_OR_VOICE_PROVIDER_UNAVAILABLE")
        provider.fish._max_transient_retries = 0
        work = await plugin.providers.memory.get_work(WORK)
        scene = await plugin.providers.memory.get_scene(dpd.effective.scene_id)
        shot = await plugin.providers.memory.get_shot("shot_83db7eb53b2f49d3a58428d4659e584e")
        voice = await voices.get_voice(VOICE)
        media = [await plugin.providers.media.get_media(mid) for mid in (AUDIO_A, AUDIO_B, VIDEO)]
        assert [x["voiceId"] for x in work.content["voiceProfiles"] if x["speakerKey"] == SPEAKER] == [VOICE]
        spoken = next(x for x in scene.content["spokenContent"] if x["id"] == dpd.line.spoken_content_id)
        assert spoken["speakerKey"] == SPEAKER and spoken["kind"] == "DIALOGUE"
        current_source = sha256_canonical({
            "workVersion": work.version,
            "actorHierarchy": [x for x in work.content["historicalActorHierarchy"] if x.get("speakerKey") in {SPEAKER, "speaker:geshuhan"}],
            "historicalBeat": next(x for x in work.content["historicalSpine"] if x["beatId"] == "P2"),
            "scene": dump_contract(scene), "shot": dump_contract(shot), "spokenContent": spoken,
        })
        assert current_source == dpd.scene.source_fingerprint
        await voices.download_voice(VOICE, REVIEW / "voice-master-before.wav")
        paths = [REVIEW / "01-turn-a-before.wav", EVIDENCE / "turn-b-frozen.wav", REVIEW / "03-old-video.mp4"]
        for item, path in zip(media, paths):
            await plugin.providers.media.download_media(item.id, path)
            assert digest(path) == item.content_hash
        assert digest(REVIEW / "voice-master-before.wav") == voice.content_hash
        frozen = {x.id: sha256_canonical(dump_contract(x)) for x in [work, voice, *media]}
        profiles = json.loads((ROOT / "artifacts/batch7-2/evidence/voice-profile-7.2s-r.json").read_text())["items"]
        profile = VoiceProfile.model_validate(next(x for x in profiles if x["speakerKey"] == SPEAKER))
        casting = build_creative_casting_profile(speaker_key=SPEAKER, creative_profile=dump_contract(profile.creative_profile))
        brief = compile_fish_creative_casting_brief(casting)
        instruction = str(brief["instruction"]) + (
            " The voice must sound usable inside a live two-person scene: direct address to a nearby listener,"
            " responsive phrasing, controlled breath, non-broadcast cadence and non-presentational endings."
            " In this audition the officer asks his visible commander for permission and leaves room for his reply."
            " Speak to that person, never to an audience; do not summarize events, declaim, or deliver a speech."
        )
        payload = compile_fish_voice_design_payload(instruction=instruction, reference_text=spoken["text"], candidate_count=2)
        request = {"voiceUseCase": "CHARACTER_DIALOGUE", "castingProfile": dump_contract(casting),
                   "dpdFingerprint": dpd.fingerprint, "payload": payload,
                   "previewContext": {"speaker": SPEAKER, "listener": dpd.effective.interaction_target,
                       "dramaticAction": dpd.effective.dramatic_action, "partnerAudioMediaId": AUDIO_B,
                       "twoPersonPreview": "candidate request followed by frozen partner refusal"}}
        request["fingerprint"] = sha256_canonical(request)
        write(EVIDENCE / "voice-design-request.json", request)
        write(EVIDENCE / "phase-a-preflight.json", {"status": "PASS", "sourceDpdCurrent": True,
            "voiceId": VOICE, "voiceHash": voice.content_hash, "frozenContracts": frozen,
            "downloadHashes": {path.name: digest(path) for path in paths},
            "voiceMasterHash": digest(REVIEW / "voice-master-before.wav"),
            "oldVideoDiagnostic": "STALE_FOR_DIALOGUE_PERFORMANCE", "domainWrites": 0})
        if not live:
            print("PHASE_A_PREFLIGHT=PASS; VOICE_DESIGN_CALLS=0")
            return
        journal = EVIDENCE / "voice-design-submission.json"
        if journal.exists():
            raise RuntimeError("SUBMISSION_EXISTS: recover saved candidates; never resubmit")
        write(journal, {"status": "SUBMITTED_OR_UNKNOWN", "requestFingerprint": request["fingerprint"],
                        "primaryCalls": 1, "safeRetries": 0, "candidateCount": 2})
        result = await provider.fish.design_voice(payload)
        candidates = []
        # Save every returned byte before probing, assembling or reviewing any candidate.
        for index, candidate in enumerate(result.candidates, 1):
            path = REVIEW / f"voice-candidate-{index}.wav"
            path.write_bytes(candidate.audio)
            candidates.append({"label": str(index), "candidateId": candidate.candidate_id,
                "providerIndex": candidate.index, "path": str(path), "sha256": digest(path),
                "text": candidate.text, "instruction": candidate.instruction,
                "sampleRate": candidate.sample_rate, "providerDurationMs": candidate.duration_ms,
                "reviewStatus": "PENDING", "selected": False})
        write(journal, {"status": "COMPLETED", "requestFingerprint": request["fingerprint"],
            "providerRequestId": result.provider_request_id, "primaryCalls": 1, "safeRetries": 0,
            "candidates": candidates, "voiceImport": 0, "createModel": 0, "workRebind": 0})
        for candidate in candidates:
            path = Path(candidate["path"])
            pcm = decode(path)
            candidate["decodedDurationMs"] = len(pcm) * 1000 / 48000
            candidate["signalQc"] = analyze_pcm_wav(path)
            candidate["dialoguePreview"] = dialogue_preview(path, paths[1], REVIEW / f"voice-candidate-{candidate['label']}-dialogue.wav")
        after = [await plugin.providers.memory.get_work(WORK), await voices.get_voice(VOICE)]
        after += [await plugin.providers.media.get_media(mid) for mid in (AUDIO_A, AUDIO_B, VIDEO)]
        assert frozen == {x.id: sha256_canonical(dump_contract(x)) for x in after}
        write(EVIDENCE / "phase-a-result.json", {"phaseA": "REVIEW_REQUIRED", "rootLayer": "VOICE_IDENTITY",
            "narratorBias": "USER_REVIEW_REQUIRED", "candidates": candidates, "frozenState": "PASS",
            "fishCalls": {"voiceDesign": 1, "tts": 0, "asr": 0, "createModel": 0, "safeRetries": 0},
            "comfyCalls": 0, "productionMediaImport": 0, "selectedCandidate": None,
            "phaseB": "NOT_STARTED", "boundary": "STOP_FOR_USER_VOICE_CHOICE"})
        print("PHASE_A=REVIEW_REQUIRED; CANDIDATES=2; FROZEN_STATE=PASS; STOP_FOR_USER_VOICE_CHOICE")
    finally:
        await plugin.aclose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    asyncio.run(run(parser.parse_args().live))
