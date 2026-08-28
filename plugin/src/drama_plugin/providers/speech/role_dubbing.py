from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Literal
from uuid import uuid4


from drama_plugin.audio.creative_casting import compile_fish_creative_casting_brief
from drama_plugin.audio.foundation import (
    audio_input_fingerprint,
    provider_mapping_fingerprint,
    sha256_canonical,
    text_hash,
)
from drama_plugin.audio.host_media import MediaProbe, probe_media
from drama_plugin.audio.intelligibility import (
    analyze_pcm_wav,
    creative_fit_score,
    intelligibility_qc,
)
from drama_plugin.contracts.audio import (
    IntelligibilityQc,
    IntelligibilityQcStatus,
    ProviderMappingStatus,
    ProviderVoiceMapping,
    RoleDubbingRequest,
    RoleDubbingResult,
)
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.media import MediaType
from drama_plugin.contracts.voice import (
    Voice,
    VoiceContent,
    VoiceProviderMapping,
    VoiceProviderMappingStatus,
    VoiceSourceType,
    VoiceStatus,
)
from drama_plugin.exceptions import ProviderError, RemoteServiceError, RoleDubbingError
from drama_plugin.providers.base import MediaProvider, MemoryProvider, VoiceProvider
from drama_plugin.providers.speech.fish_audio import (
    FISH_TTS_MODEL,
    FishAudioHttpClient,
    compile_fish_tts_payload,
    compile_fish_voice_design_payload,
)

LifecycleBranch = Literal["EXISTING_MAPPING", "MATERIALIZED_MAPPING", "NEW_VOICE"]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _work_voice_id(content: dict[str, Any], speaker_key: str) -> str | None:
    profiles = content.get("voiceProfiles", [])
    if not isinstance(profiles, list):
        raise RoleDubbingError("VOICE_BINDING_INVALID", "Work voiceProfiles is not an array")
    matches = [item for item in profiles if isinstance(item, dict) and item.get("speakerKey") == speaker_key]
    if len(matches) > 1:
        raise RoleDubbingError("VOICE_BINDING_INVALID", "Work has duplicate speaker voice bindings")
    return str(matches[0].get("voiceId")) if matches and matches[0].get("voiceId") else None


def _fish_mapping(voice: Voice) -> VoiceProviderMapping | None:
    matches = [mapping for mapping in voice.content.provider_mappings
               if mapping.provider == "fish" and mapping.model == FISH_TTS_MODEL
               and mapping.status is VoiceProviderMappingStatus.ACTIVE]
    if len(matches) > 1:
        raise RoleDubbingError("VOICE_MAPPING_AMBIGUOUS", "Voice has multiple active Fish mappings")
    return matches[0] if matches else None


def _native_performance(request: RoleDubbingRequest) -> tuple[float, float]:
    speech = request.speech_request
    parameters = speech.material_render_parameters
    speed = parameters.get("speed", 1.0)
    volume = parameters.get("volume", 0.0)
    delta = speech.performance_intent.get("sceneDelta", speech.performance_intent)
    if isinstance(delta, dict):
        pace = str(delta.get("paceAdjustment", "")).upper()
        level = str(delta.get("volumeAdjustment", "")).upper()
        if speed == 1.0:
            speed = {"SLOWER": 0.92, "SLIGHTLY_SLOWER": 0.96, "FASTER": 1.08,
                     "SLIGHTLY_FASTER": 1.04}.get(pace, 1.0)
        if volume == 0.0:
            volume = {"LOWER": -2.0, "SLIGHTLY_LOWER": -1.0, "HIGHER": 2.0,
                      "SLIGHTLY_HIGHER": 1.0}.get(level, 0.0)
    return float(speed), float(volume)


class FishRoleDubbingProvider:
    """One bounded Fish implementation for Voice resolution, synthesis, QC and Media."""

    def __init__(self, *, memory: MemoryProvider, voices: VoiceProvider, media: MediaProvider,
                 fish: FishAudioHttpClient, output_directory: Path,
                 probe: Callable[[Path | str], MediaProbe] = probe_media) -> None:
        self.memory = memory
        self.voices = voices
        self.media = media
        self.fish = fish
        self.output_directory = output_directory
        self.probe = probe

    async def generate_role_dubbing(self, request: RoleDubbingRequest) -> RoleDubbingResult:
        speech = request.speech_request
        work = await self.memory.get_work(speech.work_id)
        voice_id = _work_voice_id(work.content, speech.speaker_key)
        design_calls = 0
        model_calls = 0
        branch: LifecycleBranch
        if voice_id is None:
            voice, mapping, design_calls = await self._create_voice(request)
            model_calls = 1
            branch = "NEW_VOICE"
            work = await self.memory.bind_work_voice(work.id, speech.speaker_key, voice.id, work.version)
        else:
            try:
                voice = await self.voices.get_voice(voice_id)
            except ProviderError as exc:
                raise RoleDubbingError("VOICE_NOT_FOUND", "Bound Voice does not exist") from exc
            if voice.status is not VoiceStatus.ACTIVE:
                raise RoleDubbingError("VOICE_NOT_FOUND", "Bound Voice is not active")
            existing_mapping = _fish_mapping(voice)
            if existing_mapping is None:
                voice, mapping = await self._materialize_mapping(voice)
                model_calls = 1
                branch = "MATERIALIZED_MAPPING"
            else:
                mapping = existing_mapping
                branch = "EXISTING_MAPPING"
        return await self._synthesize_and_persist(
            request=request, voice=voice, mapping=mapping, branch=branch,
            design_calls=design_calls, model_calls=model_calls,
        )

    async def _create_voice(
        self, request: RoleDubbingRequest
    ) -> tuple[Voice, VoiceProviderMapping, int]:
        speech = request.speech_request
        profile = speech.creative_casting_profile
        if profile is None:
            raise RoleDubbingError("VOICE_CASTING_FAILED", "New Voice requires CreativeVoiceCastingProfile")
        recovery_key = sha256_canonical(
            {
                "speakerKey": speech.speaker_key,
                "exactText": speech.exact_text,
                "castingProfile": dump_contract(profile),
                "candidateCount": 3,
            }
        )
        recovery = self.output_directory / "_casting_recovery" / recovery_key
        manifest_path = recovery / "manifest.json"
        recovered_master = recovery / "selected-master.wav"
        if manifest_path.is_file() and recovered_master.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if _sha256(recovered_master) != manifest["contentHash"]:
                    raise ValueError("recovery hash mismatch")
                content = VoiceContent.model_validate(manifest["voiceContent"])
                duration_ms = int(manifest["durationMs"])
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise RoleDubbingError(
                    "VOICE_REFERENCE_UNAVAILABLE",
                    "Known Voice Design recovery artifact is invalid",
                ) from exc
            voice = await self.voices.import_voice(
                name=f"Role Voice {speech.speaker_key}",
                source_type=VoiceSourceType.DESIGNED,
                source_uri=recovered_master.resolve().as_uri(),
                duration_ms=duration_ms,
                content=content,
            )
            voice, mapping = await self._materialize_mapping(voice)
            return voice, mapping, 0
        brief = compile_fish_creative_casting_brief(profile)
        payload = compile_fish_voice_design_payload(
            instruction=str(brief["instruction"]), reference_text=speech.exact_text,
            candidate_count=3,
        )
        attempt = self._attempt_directory(speech.speaker_key)
        designed = await self.fish.design_voice(payload)
        proper_nouns = [item.term for item in speech.pronunciation_guidance]
        eligible: list[tuple[float, Path, int, dict[str, Any]]] = []
        candidate_evidence: list[dict[str, Any]] = []
        for candidate in designed.candidates:
            path = attempt / f"voice-design-candidate-{candidate.index}.wav"
            path.write_bytes(candidate.audio)
            try:
                physical = self.probe(path)
                signal = analyze_pcm_wav(path)
                asr = await self.fish.transcribe(path)
                qc = intelligibility_qc(canonical_text=speech.exact_text, transcript=asr.text,
                                        proper_nouns=proper_nouns, policy=request.qc_policy)
            except (ValueError, OSError) as exc:
                candidate_evidence.append({"candidateIndex": candidate.index, "technicalQc": "FAIL_INVALID_AUDIO"})
                continue
            evidence: dict[str, Any] = {
                "candidateIndex": candidate.index,
                "durationMs": physical.duration_ms,
                "sha256": _sha256(path),
                "technicalQc": dump_contract(qc),
                "signal": signal,
            }
            if qc.status is IntelligibilityQcStatus.PASS and not signal["obviousClipping"]:
                score, dimensions = creative_fit_score(evidence=signal, profile=profile,
                                                        duration_ms=physical.duration_ms,
                                                        reference_text=speech.exact_text)
                evidence["creativeFit"] = {"score": score, "dimensions": dimensions,
                                           "confidence": "LOW_ACOUSTIC_PROXY"}
                eligible.append((score, path, physical.duration_ms, evidence))
            candidate_evidence.append(evidence)
        if not eligible:
            raise RoleDubbingError("VOICE_CASTING_FAILED", "All Voice Design candidates failed technical QC")
        eligible.sort(key=lambda item: (-item[0], str(item[1])))
        _, selected, duration_ms, selected_evidence = eligible[0]
        master = attempt / "selected-master.wav"
        shutil.copyfile(selected, master)
        content = VoiceContent(
            creative_casting_profile=dump_contract(profile),
            source_provenance={
                "sourceProfileId": profile.source_profile_id,
                "masterSelection": {"candidateIndex": selected_evidence["candidateIndex"],
                                    "contentHash": selected_evidence["sha256"],
                                    "technicalQc": selected_evidence["technicalQc"],
                                    "creativeFit": selected_evidence["creativeFit"]},
                "candidateCount": len(candidate_evidence),
            },
        )
        recovery.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(master, recovered_master)
        manifest_path.write_text(
            json.dumps(
                {
                    "schemaVersion": "voice-design-recovery-v1",
                    "contentHash": _sha256(recovered_master),
                    "durationMs": duration_ms,
                    "voiceContent": dump_contract(content),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        voice = await self.voices.import_voice(
            name=f"Role Voice {speech.speaker_key}", source_type=VoiceSourceType.DESIGNED,
            source_uri=recovered_master.resolve().as_uri(), duration_ms=duration_ms, content=content,
        )
        voice, mapping = await self._materialize_mapping(voice)
        return voice, mapping, 1

    async def _materialize_mapping(self, voice: Voice) -> tuple[Voice, VoiceProviderMapping]:
        attempt = self._attempt_directory(voice.id)
        master = attempt / "resolved-master.wav"
        try:
            resolved = await self.voices.download_voice(voice.id, master)
        except RemoteServiceError as exc:
            raise RoleDubbingError(
                "VOICE_REFERENCE_UNAVAILABLE",
                "Drama Service could not deliver the Voice master",
            ) from exc
        if _sha256(master) != voice.content_hash or _sha256(master) != resolved.content_hash:
            raise RoleDubbingError("VOICE_REFERENCE_UNAVAILABLE", "Resolved Voice master hash mismatch")
        title = f"drama-{voice.id}-{voice.content_hash[:12]}"
        created = await self.fish.create_model(reference_audio=master, title=title)
        mapping = VoiceProviderMapping(
            provider="fish", model=FISH_TTS_MODEL, provider_voice_id=created.reference_id,
            material_fingerprint=sha256_canonical({"voiceId": voice.id,
                                                   "masterHash": voice.content_hash,
                                                   "provider": "fish", "model": FISH_TTS_MODEL}),
            status=VoiceProviderMappingStatus.ACTIVE, created_at=datetime.now(UTC),
        )
        content = voice.content.model_copy(deep=True)
        content.provider_mappings = [item for item in content.provider_mappings
                                     if not (item.provider == "fish" and item.model == FISH_TTS_MODEL
                                             and item.status is VoiceProviderMappingStatus.ACTIVE)]
        content.provider_mappings.append(mapping)
        updated = await self.voices.update_voice(voice.id, content, voice.version)
        return updated, mapping

    async def _synthesize_and_persist(self, *, request: RoleDubbingRequest, voice: Voice,
                                      mapping: VoiceProviderMapping, branch: LifecycleBranch,
                                      design_calls: int, model_calls: int) -> RoleDubbingResult:
        speech = request.speech_request
        speech_mapping = ProviderVoiceMapping(provider="fish", model=FISH_TTS_MODEL,
                                              voice_id=mapping.provider_voice_id,
                                              status=ProviderMappingStatus.APPROVED)
        profile = speech.voice_profile.model_copy(deep=True)
        profile.provider_mappings = [speech_mapping]
        resolved_request = speech.model_copy(update={"voice_profile": profile,
                                                     "provider_mapping": speech_mapping}, deep=True)
        fingerprint = audio_input_fingerprint(resolved_request)
        source_ref = f"role-dubbing:{fingerprint}"
        existing = await self.media.list_media(media_type=MediaType.AUDIO, work_id=speech.work_id,
                                               purpose="ROLE_DUBBING_AUDIO", source_ref=source_ref)
        if existing:
            qc = IntelligibilityQc.model_validate(existing[0].content["intelligibilityQc"])
            return RoleDubbingResult(audio_media_id=existing[0].id, voice_id=voice.id,
                                     duration_ms=existing[0].duration_ms or 1,
                                     intelligibility_qc=qc, lifecycle_branch=branch,
                                     voice_design_calls=design_calls, create_model_calls=model_calls)
        speed, volume = _native_performance(request)
        payload = compile_fish_tts_payload(exact_text=speech.exact_text,
                                          reference_id=mapping.provider_voice_id,
                                          mode="directed", speed=speed, volume=volume)
        audio, _ = await self.fish.synthesize(payload)
        attempt = self._attempt_directory(speech.spoken_content_id)
        output = attempt / "role-dubbing.wav"
        output.write_bytes(audio)
        physical = self.probe(output)
        asr = await self.fish.transcribe(output)
        qc = intelligibility_qc(canonical_text=speech.exact_text, transcript=asr.text,
                                proper_nouns=[item.term for item in speech.pronunciation_guidance],
                                policy=request.qc_policy)
        if qc.status is not IntelligibilityQcStatus.PASS:
            raise RoleDubbingError("INTELLIGIBILITY_QC_FAILED", "Fish TTS output failed intelligibility QC")
        content = {
            "schemaVersion": "role-dubbing-audio-v1", "workId": speech.work_id,
            "sceneId": speech.scene_id, "shotId": speech.non_material_metadata.get("shotId"),
            "spokenContentId": speech.spoken_content_id, "speakerKey": speech.speaker_key,
            "voiceId": voice.id, "exactTextHash": text_hash(speech.exact_text),
            "performanceInputFingerprint": sha256_canonical({"sceneState": dump_contract(speech.scene_state) if speech.scene_state else None,
                                                               "performanceIntent": speech.performance_intent}),
            "provider": "fish", "model": FISH_TTS_MODEL,
            "voiceProviderMappingFingerprint": provider_mapping_fingerprint(speech_mapping),
            "intelligibilityQc": dump_contract(qc), "technicalReviewStatus": "PASS",
            "reviewStatus": "PENDING", "sameVendorAsTts": True,
        }
        media = await self.media.import_media(work_id=speech.work_id, media_type=MediaType.AUDIO,
                                              source_uri=output.resolve().as_uri(), content=content,
                                              purpose="ROLE_DUBBING_AUDIO", source_ref=source_ref,
                                              duration_ms=physical.duration_ms)
        return RoleDubbingResult(audio_media_id=media.id, voice_id=voice.id,
                                 duration_ms=physical.duration_ms, intelligibility_qc=qc,
                                 lifecycle_branch=branch, voice_design_calls=design_calls,
                                 create_model_calls=model_calls)

    def _attempt_directory(self, scope: str) -> Path:
        safe = "".join(character if character.isalnum() or character in "-_" else "_" for character in scope)
        path = self.output_directory / f"{safe}-{uuid4().hex}"
        path.mkdir(parents=True, exist_ok=False)
        return path


class UnavailableRoleDubbingProvider:
    async def generate_role_dubbing(self, request: RoleDubbingRequest) -> RoleDubbingResult:
        raise RoleDubbingError("ROLE_DUBBING_CAPABILITY_MISSING", "Fish Role Dubbing is not configured")
