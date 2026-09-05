"""Phase A: complete coverage -> budget -> protected minima -> visual review -> proposal.

Pure, single-Shot and deterministic. No media generation, acceptance or assembly.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from drama_plugin.audio.foundation import (
    audio_input_fingerprint, provider_mapping_fingerprint, text_hash, voice_profile_fingerprint,
)
from drama_plugin.contracts.audio import SpeechGenerationRequest
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.creation import Scene, Shot, Work
from drama_plugin.contracts.dialogue_reconciliation import DialogueTimingReconciliation
from drama_plugin.contracts.dialogue_timing import DialogueTimingPlan
from drama_plugin.contracts.dpd import DPDSnapshot
from drama_plugin.contracts.media import Media, MediaType
from drama_plugin.contracts.visual_performance import RealizedPerformanceSnapshot
from drama_plugin.contracts.voice import Voice, VoiceProviderMappingStatus, VoiceStatus
from drama_plugin.dialogue_timing import (
    DialogueTimingPolicy, TransitionIntent, validate_dialogue_timing_plan,
)
from drama_plugin.dpd import compose_dpd
from drama_plugin.visual import fingerprint_realized_performance


_AUDIO_LINEAGE_FIELDS = (
    "workId", "sceneId", "shotId", "spokenContentId", "speakerKey", "voiceId",
    "exactTextHash", "dpdFingerprint", "sourceVideoMediaId", "sourceVideoContentHash",
    "realizedPerformanceFingerprint", "voiceMasterContentHash", "voiceMaterialFingerprint",
    "audioInputFingerprint", "audioProjectionFingerprint", "baseAudioProjectionFingerprint",
    "finalAudioProjectionFingerprint", "performanceInputFingerprint", "performanceAuthority",
    "voiceProviderMappingFingerprint", "providerRequestFingerprint",
    "reviewStatus", "technicalReviewStatus",
)


def _current_voice(work: Work, speaker: str, voices: Mapping[str, Voice]) -> tuple[str | None, Voice | None]:
    profiles = work.content.get("voiceProfiles", [])
    if not isinstance(profiles, list):
        raise ValueError("VOICE_BINDING_INVALID")
    bindings = [item for item in profiles if isinstance(item, dict) and item.get("speakerKey") == speaker]
    if len(bindings) > 1:
        raise ValueError("VOICE_BINDING_AMBIGUOUS")
    voice_id = bindings[0].get("voiceId") if bindings else None
    if voice_id is not None and (not isinstance(voice_id, str) or not voice_id.strip()):
        raise ValueError("VOICE_BINDING_INVALID")
    voice = voices.get(voice_id) if voice_id is not None else None
    if voice is not None and voice.id != voice_id:
        raise ValueError("VOICE_IDENTITY_MISMATCH")
    return voice_id, voice


def _expected_audio_lineage(
    request: SpeechGenerationRequest, *, voice: Voice | None, work: Work, scene: Scene,
    plan: DialogueTimingPlan, video: Media, production_dpd: DPDSnapshot,
    audio_realized: RealizedPerformanceSnapshot,
) -> dict[str, Any]:
    """Recompute current request lineage, not a same-text/speaker cache lookup."""
    request = SpeechGenerationRequest.model_validate(dump_contract(request))
    production_dpd = DPDSnapshot.model_validate(dump_contract(production_dpd))
    if production_dpd != compose_dpd(production_dpd.scene, production_dpd.beat, production_dpd.line):
        raise ValueError("CURRENT_AUDIO_DPD_STALE")
    audio_realized = RealizedPerformanceSnapshot.model_validate(dump_contract(audio_realized))
    if audio_realized.fingerprint != fingerprint_realized_performance(audio_realized):
        raise ValueError("CURRENT_AUDIO_REALIZED_PERFORMANCE_STALE")
    projection = request.video_conditioned_projection
    brief = request.audio_performance_brief
    mapping = request.provider_mapping
    if voice is None or voice.status != VoiceStatus.ACTIVE or mapping is None:
        raise ValueError("CURRENT_AUDIO_REQUEST_STALE: current active Voice/mapping required")
    if not any(m.status == VoiceProviderMappingStatus.ACTIVE
               and (m.provider, m.model, m.provider_voice_id) == (mapping.provider, mapping.model, mapping.voice_id)
               for m in voice.content.provider_mappings):
        raise ValueError("CURRENT_AUDIO_REQUEST_STALE: Voice mapping changed")
    if brief is None:
        raise ValueError("CURRENT_FINAL_AUDIO_REQUEST_REQUIRED")
    matching = [t for t in plan.turns if t.spoken_content_id == request.spoken_content_id]
    canonical = [s for s in scene.content["spokenContent"] if s["id"] == request.spoken_content_id]
    if len(matching) != 1 or len(canonical) != 1:
        raise ValueError("CURRENT_AUDIO_REQUEST_SCOPE_MISMATCH")
    turn = matching[0]
    effective = production_dpd.effective
    if (effective.scene_id != scene.id or effective.spoken_content_id != turn.spoken_content_id
            or effective.actor != turn.speaker_key or effective.speaker != turn.speaker_key):
        raise ValueError("CURRENT_AUDIO_DPD_IDENTITY_MISMATCH")
    if projection is None:
        # Dialogue-led production deliberately precedes the new Video. Validate
        # its actual DPD/Voice provenance; never invent a future RP dependency.
        if (request.work_id != work.id or request.scene_id != scene.id
                or request.speaker_key != turn.speaker_key or request.exact_text != canonical[0]["text"]
                or brief.dpd_fingerprint != production_dpd.fingerprint
                or brief.voice_identity_ref != voice.id
                or request.non_material_metadata.get("shotId") != plan.shot_id):
            raise ValueError("CURRENT_AUDIO_REQUEST_STALE: text/DPD/Voice scope changed")
        return {
            "workId": work.id, "sceneId": scene.id, "shotId": plan.shot_id,
            "spokenContentId": turn.spoken_content_id, "speakerKey": turn.speaker_key,
            "voiceId": voice.id, "exactTextHash": text_hash(request.exact_text),
            "dpdFingerprint": production_dpd.fingerprint, "voiceMasterContentHash": voice.content_hash,
            "audioInputFingerprint": audio_input_fingerprint(request),
            "audioProjectionFingerprint": brief.fingerprint, "performanceInputFingerprint": brief.fingerprint,
            "sourceVideoMediaId": None, "sourceVideoContentHash": None,
            "realizedPerformanceFingerprint": None, "voiceMaterialFingerprint": None,
            "baseAudioProjectionFingerprint": None, "finalAudioProjectionFingerprint": None,
            "performanceAuthority": "DPD_AUDIO_PROJECTION",
            "voiceProviderMappingFingerprint": provider_mapping_fingerprint(mapping),
        }
    if (audio_realized.video_media_id != video.id
            or audio_realized.video_content_hash != video.content_hash
            or audio_realized.video_duration_ms != video.duration_ms
            or audio_realized.shot_id != plan.shot_id):
        raise ValueError("CURRENT_AUDIO_REALIZED_PERFORMANCE_STALE")
    voice_material = sha256_canonical({
        "voiceId": voice.id, "masterHash": voice.content_hash,
        "voiceProfileFingerprint": voice_profile_fingerprint(request.voice_profile),
    })
    if (request.work_id != work.id or request.scene_id != scene.id
            or request.speaker_key != turn.speaker_key or request.exact_text != canonical[0]["text"]
            or brief.dpd_fingerprint != production_dpd.fingerprint
            or projection.shot_id != plan.shot_id or projection.video_media_id != video.id
            or projection.video_content_hash != video.content_hash
            or projection.realized_performance_fingerprint != audio_realized.fingerprint
            or projection.voice_material_fingerprint != voice_material):
        raise ValueError("CURRENT_AUDIO_REQUEST_STALE: text/DPD/Voice/Video/RP changed")
    return {
        "workId": work.id, "sceneId": scene.id, "shotId": plan.shot_id,
        "spokenContentId": turn.spoken_content_id, "speakerKey": turn.speaker_key,
        "voiceId": voice.id, "exactTextHash": text_hash(request.exact_text),
        "dpdFingerprint": production_dpd.fingerprint, "sourceVideoMediaId": video.id,
        "sourceVideoContentHash": video.content_hash,
        "realizedPerformanceFingerprint": audio_realized.fingerprint,
        "voiceMasterContentHash": voice.content_hash, "voiceMaterialFingerprint": voice_material,
        "audioInputFingerprint": audio_input_fingerprint(request),
        "audioProjectionFingerprint": brief.fingerprint,
        "performanceInputFingerprint": brief.fingerprint,
        "baseAudioProjectionFingerprint": projection.base_audio_projection_fingerprint,
        "finalAudioProjectionFingerprint": projection.fingerprint,
        "performanceAuthority": "VIDEO_CONDITIONED_FINAL_AUDIO",
        "voiceProviderMappingFingerprint": provider_mapping_fingerprint(mapping),
    }


def _audit_audio(
    *, plan: DialogueTimingPlan, work: Work, scene: Scene, video: Media,
    realized: RealizedPerformanceSnapshot, voices: Mapping[str, Voice],
    requests: Mapping[str, SpeechGenerationRequest], candidates: Sequence[Media],
    planning_dpd_by_spoken_content: Mapping[str, DPDSnapshot],
    audio_dpd_by_spoken_content: Mapping[str, DPDSnapshot],
    audio_realized_by_spoken_content: Mapping[str, RealizedPerformanceSnapshot],
    audio_source_videos_by_spoken_content: Mapping[str, Media],
    review_decisions: Mapping[str, str],
) -> list[dict[str, Any]]:
    if len({m.id for m in candidates}) != len(candidates):
        raise ValueError("DUPLICATE_AUDIO_MEDIA")
    if set(requests) - {t.spoken_content_id for t in plan.turns}:
        raise ValueError("CURRENT_AUDIO_REQUEST_SCOPE_MISMATCH")
    turn_ids = {t.spoken_content_id for t in plan.turns}
    if (set(audio_dpd_by_spoken_content) - turn_ids or set(audio_realized_by_spoken_content) - turn_ids
            or set(audio_source_videos_by_spoken_content) - turn_ids):
        raise ValueError("CURRENT_AUDIO_PRODUCTION_SCOPE_MISMATCH")
    turns: list[dict[str, Any]] = []
    for turn in plan.turns:
        key = turn.spoken_content_id
        plan_dpd = planning_dpd_by_spoken_content[key]
        voice_id, voice = _current_voice(work, turn.speaker_key, voices)
        request = requests.get(key)
        if request is not None and request.spoken_content_id != key:
            raise ValueError("CURRENT_AUDIO_REQUEST_SCOPE_MISMATCH")
        source_video = audio_source_videos_by_spoken_content.get(key, video)
        if (source_video.media_type != MediaType.VIDEO or source_video.work_id != work.id
                or source_video.shot_id != plan.shot_id):
            raise ValueError("AUDIO_SOURCE_VIDEO_SCOPE_MISMATCH")
        expected = (_expected_audio_lineage(
            request, voice=voice, work=work, scene=scene, plan=plan,
            video=source_video,
            production_dpd=audio_dpd_by_spoken_content.get(key, plan_dpd),
            audio_realized=audio_realized_by_spoken_content.get(key, realized),
        ) if request is not None else None)
        relevant = sorted((m for m in candidates if m.content.get("spokenContentId") == key
                           and (m.content.get("sceneId") == scene.id or m.shot_id == plan.shot_id)),
                          key=lambda m: m.id)
        finals = [m for m in relevant if m.content.get("performanceAuthority") == "VIDEO_CONDITIONED_FINAL_AUDIO"
                  or (expected is not None and expected["performanceAuthority"] == "DPD_AUDIO_PROJECTION"
                      and m.content.get("performanceAuthority") == "DPD_AUDIO_PROJECTION")]
        fresh: list[Media] = []
        failures: set[str] = set()
        for media in finals:
            content = media.content
            if expected is None:
                failures.add("CURRENT_REQUEST_MISSING")
                continue
            if (media.media_type != MediaType.AUDIO or media.purpose != "ROLE_DUBBING_AUDIO"
                    or media.work_id != work.id
                    or (media.shot_id != plan.shot_id and not (expected["performanceAuthority"] == "DPD_AUDIO_PROJECTION" and media.shot_id is None))
                    or media.source_ref != f"role-dubbing:{expected['audioInputFingerprint']}"
                    or not media.content_hash or len(media.content_hash) != 64
                    or type(media.duration_ms) is not int or media.duration_ms <= 0
                    or any(content.get(k) != v for k, v in expected.items())):
                failures.add("AUDIO_LINEAGE_MISMATCH")
                continue
            qc = content.get("intelligibilityQc", {})
            if (content.get("technicalReviewStatus") != "PASS" or not isinstance(qc, dict)
                    or qc.get("status") != "PASS" or any(qc.get(k) for k in ("missing", "extra", "repetition", "properNounFindings"))):
                failures.add("AUDIO_TECHNICAL_REVIEW_FAILED")
                continue
            if content.get("reviewStatus") not in ("PASS", "PENDING") or review_decisions.get(media.content_hash or "") == "FAIL":
                failures.add("AUDIO_REVIEW_INVALID")
                continue
            fresh.append(media)
        selected = fresh[0] if len(fresh) == 1 else None
        if len(fresh) > 1:
            failures.add("AMBIGUOUS_CURRENT_AUDIO")
        state = "PRESENT" if selected else "STALE" if finals else "MISSING"
        if not finals:
            failures.add("NO_CURRENT_FINAL_AUDIO")
        diagnostics = (["AUDIO_REVIEW_PENDING"] if selected and selected.content["reviewStatus"] == "PENDING"
                       else [] if selected else sorted(failures))
        # Only neutral material is serialized/hashed; never open Media/Voice
        # content, provider requests, temporary URLs or timestamps.
        evidence = {
            "voiceId": voice_id,
            "voiceMaterial": None if voice is None else {
                "id": voice.id, "hash": voice.content_hash, "status": voice.status.value,
                "castingFingerprint": sha256_canonical(voice.content.creative_casting_profile),
                "mappingFingerprints": sorted(sha256_canonical({
                    "identity": (m.provider, m.model, m.provider_voice_id),
                    "status": m.status.value, "material": m.material_fingerprint,
                }) for m in voice.content.provider_mappings),
            },
            "expectedLineage": expected,
            "candidates": [{
                "id": m.id, "type": m.media_type.value, "purpose": m.purpose,
                "workId": m.work_id, "shotId": m.shot_id,
                "hash": m.content_hash, "durationMs": m.duration_ms,
                "lineage": {k: m.content.get(k) for k in _AUDIO_LINEAGE_FIELDS},
                "technicalQc": {k: m.content.get("intelligibilityQc", {}).get(k)
                                for k in ("status", "cer", "missing", "extra", "repetition", "properNounFindings")}
                    if isinstance(m.content.get("intelligibilityQc"), dict) else None,
            } for m in relevant],
        }
        duration = selected.duration_ms if selected else None
        turns.append({
            "spokenContentId": key, "speakerKey": turn.speaker_key, "sequence": turn.sequence,
            "audioStatus": state, "audioMediaId": selected.id if selected else None,
            "audioContentHash": selected.content_hash if selected else None,
            "audioReviewStatus": selected.content["reviewStatus"] if selected else None,
            "actualDurationMs": duration, "durationAuthority": "ACTUAL_AUDIO" if selected else "PLANNING_ESTIMATE",
            "durationDeltaMs": duration - turn.planned_duration_ms if duration is not None else None,
            "audioEvidenceFingerprint": sha256_canonical(evidence),
            "rejectedAudioIds": [m.id for m in relevant if selected is None or m.id != selected.id],
            "audioDiagnostics": diagnostics, "proposedStartMs": None, "proposedEndMs": None,
        })
    return turns


def reconcile_dialogue_timing(
    *, plan: DialogueTimingPlan, scene: Scene, shot: Shot, work: Work,
    dpd_by_spoken_content: Mapping[str, DPDSnapshot], intents: Mapping[str, TransitionIntent],
    video: Media, realized: RealizedPerformanceSnapshot, accepted_realized_fingerprint: str,
    observed_speaker_key: str, voices: Mapping[str, Voice],
    current_audio_requests: Mapping[str, SpeechGenerationRequest], audio_candidates: Sequence[Media],
    policy: DialogueTimingPolicy | None = None,
    audio_dpd_by_spoken_content: Mapping[str, DPDSnapshot] | None = None,
    audio_realized_by_spoken_content: Mapping[str, RealizedPerformanceSnapshot] | None = None,
    audio_source_videos_by_spoken_content: Mapping[str, Media] | None = None,
    review_decisions: Mapping[str, str] | None = None,
    target_fit_inputs: Mapping[str, Any] | None = None,
) -> DialogueTimingReconciliation:
    policy = policy or DialogueTimingPolicy()
    validate_dialogue_timing_plan(plan, scene=scene, shot=shot,
                                 dpd_by_spoken_content=dpd_by_spoken_content, intents=intents, policy=policy)
    realized = RealizedPerformanceSnapshot.model_validate(dump_contract(realized))
    if realized.fingerprint != fingerprint_realized_performance(realized) or realized.fingerprint != accepted_realized_fingerprint:
        raise ValueError("REALIZED_PERFORMANCE_STALE_OR_UNACCEPTED")
    if (video.media_type != MediaType.VIDEO or video.id != realized.video_media_id
            or video.content_hash != realized.video_content_hash or video.shot_id != shot.id
            or video.work_id != work.id or realized.shot_id != shot.id):
        raise ValueError("VIDEO_IDENTITY_MISMATCH")
    if type(video.duration_ms) is not int or video.duration_ms <= 0 or video.duration_ms != realized.video_duration_ms:
        raise ValueError("VIDEO_DURATION_INVALID_OR_MISMATCH")
    if observed_speaker_key not in {turn.speaker_key for turn in plan.turns}:
        raise ValueError("OBSERVED_SPEAKER_NOT_BOUND")
    # 1: Full canonical coverage and current production Audio; never only the
    # convenient line with an existing duration.
    turns = _audit_audio(plan=plan, work=work, scene=scene, video=video, realized=realized,
                         voices=voices, requests=current_audio_requests, candidates=audio_candidates,
                         planning_dpd_by_spoken_content=dpd_by_spoken_content,
                         audio_dpd_by_spoken_content=audio_dpd_by_spoken_content or {},
                         audio_realized_by_spoken_content=audio_realized_by_spoken_content or {},
                         audio_source_videos_by_spoken_content=audio_source_videos_by_spoken_content or {},
                         review_decisions=review_decisions or {})
    complete = all(t["audioStatus"] == "PRESENT" for t in turns)
    count = sum(t["audioStatus"] == "PRESENT" for t in turns)
    used = [t["actualDurationMs"] if t["actualDurationMs"] is not None else p.planned_duration_ms
            for t, p in zip(turns, plan.turns)]
    # 2–3: Physical budget with protected dramatic minima, then flexible slack.
    minimum = plan.pre_dialogue_hold_ms + sum(used) + sum(t.transition_hold_ms for t in plan.turns) + plan.minimum_post_dialogue_hold_ms
    fits = minimum <= video.duration_ms
    delta = video.duration_ms - plan.planned_duration_ms
    drift = sum(used) - sum(t.planned_duration_ms for t in plan.turns)
    flexible = plan.post_dialogue_hold_ms - plan.minimum_post_dialogue_hold_ms
    # Counterfactual diagnosis only. Never use this smaller reaction budget.
    compressed = minimum - sum(max(t.transition_hold_ms - policy.minimum_inter_turn_separation_ms, 0)
                               for t in plan.turns[1:])
    compression_risk = not fits and compressed <= video.duration_ms
    # 4: Accepted visual evidence. Head/gaze/pause windows are not speech anchors.
    windows = {"HEAD_MOTION": realized.major_head_motion_windows_ms,
               "GESTURE": realized.major_gesture_windows_ms, "VISIBLE_PAUSE": realized.visible_pause_windows_ms}
    artistic = ("CONFLICTING" if not fits else "UNKNOWN" if realized.mouth_activity == "UNKNOWN"
                else "QUESTIONABLE" if realized.mouth_activity == "ABSENT" else "SUPPORTED")
    # One observed speaker cannot establish full-Shot artistic support, nor can
    # technical PASS promote a still-PENDING Audio review.
    if artistic == "SUPPORTED" and (len({t.speaker_key for t in plan.turns}) > 1 or not complete
                                   or any(t["audioReviewStatus"] == "PENDING" for t in turns)):
        artistic = "UNKNOWN"
    visibility_conflict = False
    earliest = plan.pre_dialogue_hold_ms
    coverage = {b["spokenContentId"]: b["coverageIntent"] for b in shot.content["spokenContentBindings"]}
    for planned_turn, duration in zip(plan.turns, used):
        earliest += planned_turn.transition_hold_ms
        if (planned_turn.speaker_key == observed_speaker_key and coverage[planned_turn.spoken_content_id] == "ON_SCREEN_SPEAKER"
                and realized.speaker_visible_start_ms is not None and earliest < realized.speaker_visible_start_ms):
            visibility_conflict = True
        earliest += duration
    if visibility_conflict:
        # Visibility is a lower-bound constraint, never a speech-onset anchor.
        # Flag the conflict for review instead of inventing an event-to-line mapping.
        artistic = "CONFLICTING"
    fit: dict[str, Any] | None = None
    if target_fit_inputs is not None:
        if not complete:
            raise ValueError("COMPLETE_CURRENT_AUDIO_REQUIRED_FOR_TARGET_FIT")
        selected = {t["spokenContentId"]: next(m for m in audio_candidates if m.id == t["audioMediaId"]) for t in turns}
        fit = evaluate_target_performance_fit(plan=plan, video=video, audio_by_spoken_content=selected,
            realized_by_speaker=target_fit_inputs["realized_by_speaker"],
            execution_timing=target_fit_inputs["execution_timing"],
            phase_observations=target_fit_inputs["phase_observations"], review_decisions=review_decisions or {})
        artistic = fit["visualFit"]
    # 5: Evidence-based candidates, not automatic blame or upstream changes.
    causes: set[str] = set()
    if any(t["audioStatus"] == "MISSING" for t in turns): causes.add("MISSING_REALIZED_TURN_AUDIO")
    if any(t["audioStatus"] == "STALE" for t in turns): causes.add("STALE_REALIZED_TURN_AUDIO")
    if any(t["durationDeltaMs"] not in (None, 0) for t in turns): causes.add("DURATION_ESTIMATE_DRIFT")
    if not fits and complete: causes.add("SHOT_DURATION")
    if compression_risk and complete: causes.add("SHOT_SEGMENTATION_REVIEW")
    if realized.mouth_activity == "UNKNOWN": causes.add("TIMING_OBSERVABILITY")
    diagnostics = ["ARTISTIC_TIMING_REVIEW_REQUIRED"]
    if not fits: diagnostics.append("TIMING_CONFLICT")
    if not complete: diagnostics.append("HYBRID_EVIDENCE_ONLY" if count else "NO_ACTUAL_AUDIO")
    if compression_risk: diagnostics.append("REACTION_COMPRESSION_REQUIRED_TO_FIT")
    if any(windows.values()): diagnostics.append("VISIBLE_ACTION_WINDOW_REVIEW")
    if realized.mouth_activity == "ABSENT": diagnostics.append("ON_SCREEN_MOUTH_ACTIVITY_ABSENT")
    if visibility_conflict: diagnostics.append("VISIBLE_COVERAGE_CONFLICT")
    # 6: Only now propose a linear whole-line schedule. Retain every semantic
    # reaction and consume extra video then the surplus post hold.
    propose = fits and count > 0 and artistic != "CONFLICTING"
    cursor = plan.pre_dialogue_hold_ms
    if propose:
        for turn, planned, duration in zip(turns, plan.turns, used):
            cursor += planned.transition_hold_ms
            turn["proposedStartMs"] = cursor
            turn["proposedEndMs"] = cursor + duration
            cursor += duration
    if fit is not None and propose:
        for turn, placement in zip(turns, fit["placements"]):
            turn["proposedStartMs"], turn["proposedEndMs"] = placement["startMs"], placement["endMs"]
        cursor = turns[-1]["proposedEndMs"]
    inputs = {"plan": plan.fingerprint, "videoId": video.id, "videoHash": video.content_hash,
              "videoDurationMs": video.duration_ms, "rp": realized.fingerprint, "observedSpeaker": observed_speaker_key,
              "audioEvidence": [t["audioEvidenceFingerprint"] for t in turns]}
    if fit is not None:
        inputs["targetFitFingerprint"] = fit["fingerprint"]
    if review_decisions:
        inputs["reviewDecisions"] = dict(review_decisions)
    material = {
        "schemaVersion": "dialogue-timing-reconciliation-v1", "sourcePlan": dump_contract(plan),
        "sourceDialogueTimingPlanFingerprint": plan.fingerprint,
        "sceneId": scene.id, "shotId": shot.id, "videoMediaId": video.id, "videoContentHash": video.content_hash,
        "videoDurationMs": video.duration_ms, "realizedPerformanceFingerprint": realized.fingerprint,
        "observedSpeakerKey": observed_speaker_key, "mouthActivity": realized.mouth_activity,
        "visibleActionWindowsMs": {k: [list(w) for w in v] for k, v in windows.items()},
        "reconciliationPolicy": "PARTICIPATION_CONSTRAINED_V1" if fit is not None else "VIDEO_DELTA_THEN_POST_SURPLUS_V1",
        "currentInputsFingerprint": sha256_canonical(inputs), "turns": turns,
        "fullDialogueCoverage": "COMPLETE" if complete else "INCOMPLETE",
        "evidenceMode": "REALIZED" if complete else "HYBRID" if count else "PLANNING_ONLY",
        "physicalFeasibility": ("FEASIBLE" if fits else "CONFLICT") if complete else "EVIDENCE_LIMITED",
        "hybridFeasibility": "NOT_NEEDED" if complete else "FEASIBLE" if fits else "CONFLICT",
        "artisticCompatibility": artistic,
        "recommendedPlacementStatus": ("PROPOSED" if complete else "CONDITIONAL_HYBRID") if propose else "BLOCKED",
        "actualVideoDeltaMs": delta, "flexiblePostSlackMs": flexible,
        "consumedVideoDeltaMs": min(max(delta, 0), max(drift, 0)),
        "consumedPostSlackMs": min(flexible, max(drift - delta, 0)),
        "requiredMinimumDurationMs": minimum, "fullRealizedRequiredMinimumMs": minimum if complete else None,
        "overflowMs": max(minimum - video.duration_ms, 0), "slackMs": max(video.duration_ms - minimum, 0),
        "proposedPostHoldMs": video.duration_ms - cursor if propose else None,
        "candidateCauses": sorted(causes), "diagnostics": sorted(diagnostics),
        "userTimingReview": "REQUIRED" if propose else "NOT_READY",
    }
    return DialogueTimingReconciliation.model_validate({**material, "fingerprint": sha256_canonical(material)})


def validate_dialogue_reconciliation(result: DialogueTimingReconciliation, **current_inputs: Any) -> None:
    """Explicit reuse validation; no background sweep, repair, or acceptance."""
    checked = DialogueTimingReconciliation.model_validate(dump_contract(result))
    current = reconcile_dialogue_timing(**current_inputs)
    if checked != current:
        raise ValueError("STALE_DIALOGUE_TIMING_RECONCILIATION")


def evaluate_target_performance_fit(
    *, plan: DialogueTimingPlan, video: Media,
    audio_by_spoken_content: Mapping[str, Media],
    realized_by_speaker: Mapping[str, RealizedPerformanceSnapshot],
    execution_timing: Mapping[str, Any],
    phase_observations: Mapping[str, Mapping[str, Any]],
    review_decisions: Mapping[str, str],
) -> dict[str, Any]:
    """Physical budget, then evidence-scoped participation; never mouth-as-onset.

    Optional fitWindowMs is a production interpretation of visible participation,
    not an automatic conversion of RP mouth/head windows. Missing stays UNKNOWN.
    """
    from drama_plugin.dialogue_timing import derive_visual_execution_timing

    checked = derive_visual_execution_timing(plan=plan,
        actual_durations_ms={t["spokenContentId"]: t["durationMs"] for t in execution_timing["turns"]},
        target_video_duration_ms=execution_timing["targetVideoDurationMs"])
    if checked != execution_timing:
        raise ValueError("STALE_EXECUTION_MATERIAL")
    keys = {t.spoken_content_id for t in plan.turns}
    speakers = {t.speaker_key for t in plan.turns}
    if set(audio_by_spoken_content) != keys or set(realized_by_speaker) != speakers or set(phase_observations) != keys:
        raise ValueError("COMPLETE_SPEAKER_SCOPE_REQUIRED")
    if video.duration_ms is None or video.duration_ms <= 0 or not video.content_hash:
        raise ValueError("INVALID_TARGET_VIDEO")
    for speaker, rp in realized_by_speaker.items():
        if (rp.observed_speaker_key != speaker or rp.video_media_id != video.id
                or rp.video_content_hash != video.content_hash or rp.video_duration_ms != video.duration_ms
                or rp.shot_id != plan.shot_id or rp.fingerprint != fingerprint_realized_performance(rp)):
            raise ValueError("STALE_OR_WRONG_SPEAKER_RP")
    durations: list[int] = []
    for turn in plan.turns:
        audio = audio_by_spoken_content[turn.spoken_content_id]
        if (audio.media_type != MediaType.AUDIO or audio.work_id != video.work_id
                or audio.content.get("spokenContentId") != turn.spoken_content_id
                or audio.content.get("speakerKey") != turn.speaker_key
                or not audio.content_hash or audio.duration_ms is None or audio.duration_ms <= 0):
            raise ValueError("AUDIO_SCOPE_MISMATCH")
        if (audio.content.get("reviewStatus") == "FAIL" or review_decisions.get(audio.content_hash) == "FAIL"
                or review_decisions.get(video.content_hash) == "FAIL"):
            raise ValueError("USER_REJECTED_PRODUCTION_INPUT")
        durations.append(audio.duration_ms)
    minimum = plan.pre_dialogue_hold_ms + sum(durations) + sum(t.transition_hold_ms for t in plan.turns) + plan.minimum_post_dialogue_hold_ms
    physical = minimum <= video.duration_ms
    status = "SUPPORTED" if physical else "CONFLICTING"
    cursor = plan.pre_dialogue_hold_ms
    placements: list[dict[str, Any]] = []
    for turn, duration in zip(plan.turns, durations):
        observation = phase_observations[turn.spoken_content_id]
        if observation.get("videoContentHash") != video.content_hash:
            raise ValueError("STALE_PHASE_OBSERVATION")
        observed_status = observation.get("status", "UNKNOWN")
        if observed_status not in {"SUPPORTED", "QUESTIONABLE", "CONFLICTING", "UNKNOWN"}:
            raise ValueError("INVALID_PHASE_DIAGNOSTIC")
        if observed_status == "CONFLICTING" or observation.get("wrongSpeakerMouth") is True:
            status = "CONFLICTING"
        elif status != "CONFLICTING" and observed_status == "UNKNOWN":
            status = "UNKNOWN"
        elif status == "SUPPORTED" and observed_status == "QUESTIONABLE":
            status = "QUESTIONABLE"
        cursor += turn.transition_hold_ms
        window = observation.get("fitWindowMs")
        if window is not None:
            if (not isinstance(window, (tuple, list)) or len(window) != 2
                    or any(type(v) is not int for v in window)
                    or not 0 <= window[0] < window[1] <= video.duration_ms
                    or not observation.get("evidence")):
                raise ValueError("REVIEWED_PARTICIPATION_RANGE_REQUIRED")
            cursor = max(cursor, window[0])
            if cursor + duration > window[1]:
                status = "CONFLICTING"
        elif status == "SUPPORTED":
            status = "UNKNOWN"
        placements.append({"spokenContentId": turn.spoken_content_id, "startMs": cursor, "endMs": cursor + duration})
        cursor += duration
    if cursor + plan.minimum_post_dialogue_hold_ms > video.duration_ms:
        status = "CONFLICTING"
    material = {"physicalFit": "FEASIBLE" if physical else "CONFLICT", "visualFit": status,
                "requiredMinimumMs": minimum, "slackMs": max(video.duration_ms - minimum, 0),
                "placements": placements if status != "CONFLICTING" else [],
                "videoHash": video.content_hash, "executionFingerprint": checked["fingerprint"],
                "audioHashes": {k: a.content_hash for k, a in audio_by_spoken_content.items()},
                "rpFingerprints": {k: r.fingerprint for k, r in realized_by_speaker.items()},
                "phaseObservations": dict(phase_observations), "reviewDecisions": dict(review_decisions)}
    return {**material, "fingerprint": sha256_canonical(material)}
