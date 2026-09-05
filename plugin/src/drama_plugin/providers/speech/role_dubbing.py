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
    voice_profile_fingerprint,
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
    FISH_VOICE_DESIGN_MODEL,
    FishAudioPerformanceMapping,
    FishAudioHttpClient,
    compile_fish_tts_payload,
    compile_fish_voice_design_payload,
    map_audio_performance_to_fish,
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


def _projected_performance(
    request: RoleDubbingRequest,
) -> FishAudioPerformanceMapping | None:
    brief = request.speech_request.audio_performance_brief
    return map_audio_performance_to_fish(brief) if brief is not None else None


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
        if speech.audio_performance_brief is not None:
            if voice_id is None:
                raise RoleDubbingError(
                    "VOICE_BINDING_REQUIRED",
                    "DPD Audio Projection requires an existing stable Voice binding",
                )
            if voice_id != speech.audio_performance_brief.voice_identity_ref:
                raise RoleDubbingError(
                    "VOICE_BINDING_INVALID",
                    "Audio Projection Voice identity differs from the Work binding",
                )
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
            if speech.video_conditioned_projection is not None:
                await self._validate_video_conditioned_inputs(request, voice)
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

    async def _validate_video_conditioned_inputs(self, request: RoleDubbingRequest, voice: Voice) -> None:
        speech = request.speech_request
        projection = speech.video_conditioned_projection
        if projection is None:
            return
        expected_voice = sha256_canonical({
            "voiceId": voice.id, "masterHash": voice.content_hash,
            "voiceProfileFingerprint": voice_profile_fingerprint(speech.voice_profile),
        })
        if projection.voice_material_fingerprint != expected_voice:
            raise RoleDubbingError("VOICE_BINDING_INVALID", "Frozen Voice material changed")
        video = await self.media.get_media(projection.video_media_id)
        shot = await self.memory.get_shot(projection.shot_id)
        scene = await self.memory.get_scene(speech.scene_id)
        if (video.id != projection.video_media_id or shot.id != projection.shot_id
                or scene.id != speech.scene_id
                or video.media_type is not MediaType.VIDEO or video.work_id != speech.work_id
                or video.shot_id != shot.id or video.content_hash != projection.video_content_hash
                or shot.scene_id != speech.scene_id):
            raise RoleDubbingError("FINAL_AUDIO_INPUT_STALE", "Video or Shot lineage changed")
        bound = {item.get("spokenContentId") for item in shot.content.get("spokenContentBindings", [])}
        spoken = [item for item in scene.content.get("spokenContent", [])
                  if item.get("id", item.get("spokenContentId")) == speech.spoken_content_id]
        if (speech.spoken_content_id not in bound or len(spoken) != 1
                or spoken[0].get("speakerKey") != speech.speaker_key
                or spoken[0].get("text") != speech.exact_text):
            raise RoleDubbingError("SPOKEN_CONTENT_BINDING_REQUIRED", "Canonical speech binding changed")

    async def _create_voice(
        self, request: RoleDubbingRequest
    ) -> tuple[Voice, VoiceProviderMapping, int]:
        speech = request.speech_request
        profile = speech.creative_casting_profile
        if profile is None:
            raise RoleDubbingError("VOICE_CASTING_FAILED", "New Voice requires CreativeVoiceCastingProfile")
        brief = compile_fish_creative_casting_brief(profile)
        payload = compile_fish_voice_design_payload(
            instruction=str(brief["instruction"]), reference_text=speech.exact_text,
            candidate_count=3,
        )
        design_fingerprint = sha256_canonical(
            {
                "schemaVersion": "voice-design-request-v1",
                "speakerKey": speech.speaker_key,
                "castingProfile": dump_contract(profile),
                "provider": "fish",
                "model": FISH_VOICE_DESIGN_MODEL,
                "instruction": payload["instruction"],
                "referenceText": payload["reference_text"],
                "candidateCount": payload["n"],
            }
        )
        review_artifact_id = f"voice-design-review:{design_fingerprint}"
        recovery = self.output_directory / "_casting_recovery" / design_fingerprint
        manifest_path = recovery / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if (
                    manifest["schemaVersion"] != "voice-design-recovery-v1"
                    or manifest["designRequestFingerprint"] != design_fingerprint
                    or manifest["reviewArtifactId"] != review_artifact_id
                    or manifest["referenceText"] != speech.exact_text
                    or manifest["referenceTextHash"] != text_hash(speech.exact_text)
                ):
                    raise ValueError("recovery identity mismatch")
                candidates = manifest["candidates"]
                if not isinstance(candidates, list) or not candidates:
                    raise ValueError("recovery candidates missing")
                for candidate in candidates:
                    candidate_path = recovery / str(candidate["fileName"])
                    if not candidate_path.is_file() or _sha256(candidate_path) != candidate["contentHash"]:
                        raise ValueError("recovery candidate hash mismatch")
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise RoleDubbingError(
                    "VOICE_REFERENCE_UNAVAILABLE",
                    "Known Voice Design recovery artifact is invalid",
                ) from exc
            approval = request.voice_design_approval
            if approval is None:
                raise self._review_required(manifest)
            if (
                approval.design_request_fingerprint != design_fingerprint
                or approval.review_artifact_id != review_artifact_id
            ):
                raise RoleDubbingError(
                    "VOICE_ARTISTIC_APPROVAL_INVALID",
                    "Voice Design approval does not match the recovered review package",
                )
            matches = [
                candidate for candidate in candidates
                if candidate["candidateIndex"] == approval.candidate_index
            ]
            if (
                len(matches) != 1
                or matches[0]["contentHash"] != approval.candidate_hash
            ):
                raise RoleDubbingError(
                    "VOICE_ARTISTIC_APPROVAL_INVALID",
                    "Voice Design approval does not match a hash-verified candidate",
                )
            selected_evidence = matches[0]
            selected = recovery / str(selected_evidence["fileName"])
            master = recovery / "selected-master.wav"
            if master.is_file() and _sha256(master) != approval.candidate_hash:
                raise RoleDubbingError(
                    "VOICE_REFERENCE_UNAVAILABLE",
                    "Frozen approved Voice master hash does not match approval",
                )
            if not master.is_file():
                shutil.copyfile(selected, master)
            content = VoiceContent(
                creative_casting_profile=dump_contract(profile),
                source_provenance={
                    "sourceProfileId": profile.source_profile_id,
                    "voiceUseCase": profile.voice_use_case.value,
                    "designRequestFingerprint": design_fingerprint,
                    "reviewArtifactId": review_artifact_id,
                    "referenceText": manifest["referenceText"],
                    "referenceTextHash": manifest["referenceTextHash"],
                    "masterSelection": {
                        "candidateIndex": selected_evidence["candidateIndex"],
                        "contentHash": selected_evidence["contentHash"],
                        "technicalQc": selected_evidence["technicalQc"],
                        "creativeFit": selected_evidence["creativeFit"],
                        "aiRank": selected_evidence["aiRank"],
                        "artisticApproval": {
                            "status": "USER_APPROVED",
                            "source": approval.approval_source,
                            "reviewArtifactId": review_artifact_id,
                        },
                    },
                    "candidateCount": manifest["candidateCount"],
                },
            )
            voice = await self.voices.import_voice(
                name=f"Role Voice {speech.speaker_key}",
                source_type=VoiceSourceType.DESIGNED,
                source_uri=master.resolve().as_uri(),
                duration_ms=int(selected_evidence["durationMs"]),
                content=content,
            )
            voice, mapping = await self._materialize_mapping(voice)
            return voice, mapping, 0
        if request.voice_design_approval is not None:
            raise RoleDubbingError(
                "VOICE_ARTISTIC_APPROVAL_INVALID",
                "Voice Design approval has no matching recovered review package",
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
        recovery.mkdir(parents=True, exist_ok=True)
        review_candidates: list[dict[str, Any]] = []
        for rank, (_, candidate_path, duration_ms, evidence) in enumerate(eligible, start=1):
            file_name = f"candidate-{evidence['candidateIndex']}.wav"
            shutil.copyfile(candidate_path, recovery / file_name)
            review_candidates.append(
                {
                    "candidateIndex": evidence["candidateIndex"],
                    "contentHash": evidence["sha256"],
                    "durationMs": duration_ms,
                    "technicalQc": evidence["technicalQc"],
                    "creativeFit": evidence["creativeFit"],
                    "aiRank": rank,
                    "fileName": file_name,
                }
            )
        manifest = {
            "schemaVersion": "voice-design-recovery-v1",
            "designRequestFingerprint": design_fingerprint,
            "reviewArtifactId": review_artifact_id,
            "voiceUseCase": profile.voice_use_case.value,
            "referenceText": speech.exact_text,
            "referenceTextHash": text_hash(speech.exact_text),
            "candidateCount": len(candidate_evidence),
            "aiRecommendedCandidateIndex": review_candidates[0]["candidateIndex"],
            "candidates": review_candidates,
        }
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        raise self._review_required(manifest)

    @staticmethod
    def _review_required(manifest: dict[str, Any]) -> RoleDubbingError:
        return RoleDubbingError(
            "VOICE_ARTISTIC_REVIEW_REQUIRED",
            "Voice Design candidates passed technical QC and require user artistic approval",
            details={
                "reviewArtifactId": manifest["reviewArtifactId"],
                "designRequestFingerprint": manifest["designRequestFingerprint"],
                "aiRecommendedCandidateIndex": manifest["aiRecommendedCandidateIndex"],
                "candidates": [
                    {
                        "candidateIndex": item["candidateIndex"],
                        "candidateHash": item["contentHash"],
                        "aiRank": item["aiRank"],
                    }
                    for item in manifest["candidates"]
                ],
            },
        )

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
        reference_text = voice.content.source_provenance.get("referenceText")
        created = await self.fish.create_model(
            reference_audio=master,
            title=title,
            reference_text=reference_text if isinstance(reference_text, str) else None,
        )
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
            rejected = speech.non_material_metadata.get("rejectedAudioHashes", [])
            if any(m.content_hash in rejected or m.content.get("reviewStatus") == "FAIL" for m in existing):
                raise RoleDubbingError("AUDIO_ARTISTIC_REVIEW_FAILED", "Cached Audio was artistically rejected; change the responsible projection before generation")
            qc = IntelligibilityQc.model_validate(existing[0].content["intelligibilityQc"])
            return RoleDubbingResult(audio_media_id=existing[0].id, voice_id=voice.id,
                                     duration_ms=existing[0].duration_ms or 1,
                                     intelligibility_qc=qc, lifecycle_branch=branch,
                                     voice_design_calls=design_calls, create_model_calls=model_calls)
        projected = _projected_performance(request)
        speed, volume = (
            (projected.speed, projected.volume)
            if projected is not None
            else _native_performance(request)
        )
        payload = compile_fish_tts_payload(exact_text=speech.exact_text,
                                          reference_id=mapping.provider_voice_id,
                                          mode="directed", speed=speed, volume=volume,
                                          performance_brief=(speech.audio_performance_brief
                                              if speech.material_render_parameters.get("performanceRendering")
                                              in {"BRIEF_CUES_V1", "PHRASE_CUES_V1"} else None))
        audio, _ = await self.fish.synthesize(payload)
        attempt = self._attempt_directory(speech.spoken_content_id)
        output = attempt / "role-dubbing.wav"
        output.write_bytes(audio)
        physical = self.probe(output)
        if speech.video_conditioned_projection is not None and analyze_pcm_wav(output)["obviousClipping"]:
            raise RoleDubbingError("TECHNICAL_QC_FAILED", "Final Audio contains clipping")
        asr = await self.fish.transcribe(output)
        qc = intelligibility_qc(canonical_text=speech.exact_text, transcript=asr.text,
                                proper_nouns=[item.term for item in speech.pronunciation_guidance],
                                policy=request.qc_policy)
        if qc.status is not IntelligibilityQcStatus.PASS:
            raise RoleDubbingError("INTELLIGIBILITY_QC_FAILED", "Fish TTS output failed intelligibility QC")
        projection = speech.audio_performance_brief
        video_projection = speech.video_conditioned_projection
        content = {
            "schemaVersion": "role-dubbing-audio-v1", "workId": speech.work_id,
            "sceneId": speech.scene_id, "shotId": (video_projection.shot_id if video_projection
                                                     else speech.non_material_metadata.get("shotId")),
            "spokenContentId": speech.spoken_content_id, "speakerKey": speech.speaker_key,
            "voiceId": voice.id, "exactTextHash": text_hash(speech.exact_text),
            "performanceAuthority": (
                "VIDEO_CONDITIONED_FINAL_AUDIO" if video_projection is not None else
                "DPD_AUDIO_PROJECTION" if projection is not None else "LEGACY_PERFORMANCE_INTENT"
            ),
            "performanceInputFingerprint": (
                projection.fingerprint
                if projection is not None
                else sha256_canonical({"sceneState": dump_contract(speech.scene_state) if speech.scene_state else None,
                                       "performanceIntent": speech.performance_intent})
            ),
            "dpdFingerprint": projection.dpd_fingerprint if projection is not None else None,
            "audioProjectionFingerprint": projection.fingerprint if projection is not None else None,
            "baseAudioProjectionFingerprint": video_projection.base_audio_projection_fingerprint if video_projection else None,
            "realizedPerformanceFingerprint": video_projection.realized_performance_fingerprint if video_projection else None,
            "finalAudioProjectionFingerprint": video_projection.fingerprint if video_projection else None,
            "sourceVideoMediaId": video_projection.video_media_id if video_projection else None,
            "sourceVideoContentHash": video_projection.video_content_hash if video_projection else None,
            "voiceMaterialFingerprint": video_projection.voice_material_fingerprint if video_projection else None,
            "voiceMasterContentHash": voice.content_hash,
            "audioInputFingerprint": fingerprint,
            "performanceRendering": speech.material_render_parameters.get("performanceRendering", "NATIVE"),
            "providerRequestFingerprint": sha256_canonical(payload),
            "fishCapabilityMapping": dump_contract(projected) if projected is not None else None,
            "provider": "fish", "model": FISH_TTS_MODEL,
            "voiceProviderMappingFingerprint": provider_mapping_fingerprint(speech_mapping),
            "intelligibilityQc": dump_contract(qc), "technicalReviewStatus": "PASS",
            "reviewStatus": "PENDING", "sameVendorAsTts": True,
        }
        media = await self.media.import_media(work_id=speech.work_id, media_type=MediaType.AUDIO,
                                              source_uri=output.resolve().as_uri(), content=content,
                                              shot_id=video_projection.shot_id if video_projection else None,
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
