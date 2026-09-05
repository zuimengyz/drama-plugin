from __future__ import annotations

from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest
from pydantic import ValidationError

from drama_plugin.audio.foundation import audio_input_fingerprint, provider_mapping_fingerprint, text_hash, is_audio_fresh
from drama_plugin.audio.projection import compile_projected_speech_request
from drama_plugin.audio.video_conditioning import condition_audio_on_video
from drama_plugin.contracts import Media, ProviderVoiceMapping, TargetTimingPolicy, VoiceProfile, CreativeVoiceProfile
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.dialogue_reconciliation import DialogueTimingReconciliation, ReconciledDialogueTurn
from drama_plugin.dialogue_reconciliation import reconcile_dialogue_timing, validate_dialogue_reconciliation
from drama_plugin.dialogue_timing import dialogue_timing_context, plan_dialogue_timing
from drama_plugin.dpd import compose_dpd
from drama_plugin.visual import build_realized_performance_snapshot


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/dialogue-reconciliation-72.json"
RUNNER = ROOT / "integration/evaluate_dialogue_reconciliation.py"
spec = spec_from_file_location("reconciliation_runner", RUNNER)
runner = module_from_spec(spec)
spec.loader.exec_module(runner)


def real_inputs():
    return runner.load_inputs(FIXTURE)


def complete_inputs(a=5000, b=3200, video_duration=11042, visible_start=0, mouth="UNKNOWN"):
    """Offline hypothetical complete realization; no real Audio is generated."""
    args = real_inputs()
    args.pop("audio_dpd_by_spoken_content", None)
    args.pop("audio_realized_by_spoken_content", None)
    # A–C/E are hypothetical fixtures with their own simple direction. Keep the
    # actual 72/73 DPD untouched; the frozen Audio projection has a narrower
    # authority vocabulary than free-text DPD ("commander" also matches dominant).
    key_a = args["plan"].turns[0].spoken_content_id
    direction = args["dpd_by_spoken_content"][key_a]
    direction.beat.direction.tactic = "request authorization"
    direction.beat.direction.relationship_stance = "deferential counsel"
    args["dpd_by_spoken_content"][key_a] = compose_dpd(direction.scene, direction.beat, direction.line)
    planning_inputs = {key: args[key] for key in ("scene", "shot", "dpd_by_spoken_content")}
    context = sha256_canonical(dialogue_timing_context(**planning_inputs))
    args["intents"] = {key: value.model_copy(update={"context_fingerprint": context}) for key, value in args["intents"].items()}
    args["plan"] = plan_dialogue_timing(**planning_inputs, intents=args["intents"])
    args["video"].duration_ms = video_duration
    observed = dump_contract(args["realized"], exclude={"fingerprint"})
    observed.update(videoDurationMs=video_duration, majorHeadMotionWindowsMs=[],
                    speakerVisibleStartMs=visible_start, mouthActivity=mouth)
    args["realized"] = build_realized_performance_snapshot(observed)
    args["accepted_realized_fingerprint"] = args["realized"].fingerprint
    requests, media = {}, []
    for turn, duration in zip(args["plan"].turns, (a, b)):
        spoken = next(s for s in args["scene"].content["spokenContent"] if s["id"] == turn.spoken_content_id)
        voice_id = next(v["voiceId"] for v in args["work"].content["voiceProfiles"] if v["speakerKey"] == turn.speaker_key)
        voice = args["voices"][voice_id]
        profile = VoiceProfile(profile_id=f"test-profile:{turn.speaker_key}", speaker_key=turn.speaker_key,
                               creative_profile=CreativeVoiceProfile(baseline_pace="MODERATE"))
        base = compile_projected_speech_request(
            work_id=args["work"].id, dpd_snapshot=args["dpd_by_spoken_content"][turn.spoken_content_id],
            spoken_content=spoken, voice_profile=profile, voice_identity_ref=voice_id,
            timing_policy=TargetTimingPolicy(policy="NATURAL"),
        )
        speech = condition_audio_on_video(
            base_request=base, dpd_snapshot=args["dpd_by_spoken_content"][turn.spoken_content_id],
            realized_snapshot=args["realized"], video_media=args["video"], shot_id=args["shot"].id,
            shot_scene_id=args["scene"].id, shot_spoken_content_ids=tuple(t.spoken_content_id for t in args["plan"].turns),
            canonical_spoken_content=spoken, observed_speaker_key=turn.speaker_key,
            bound_voice_id=voice_id, voice_content_hash=voice.content_hash,
            accepted_realized_fingerprint=args["accepted_realized_fingerprint"],
        )
        active = next(m for m in voice.content.provider_mappings if m.status == "ACTIVE")
        mapping = ProviderVoiceMapping(provider=active.provider, model=active.model, voice_id=active.provider_voice_id)
        speech = speech.model_copy(update={"provider_mapping": mapping,
                                          "voice_profile": speech.voice_profile.model_copy(update={"provider_mappings": [mapping]})})
        requests[turn.spoken_content_id] = speech
        projection = speech.video_conditioned_projection
        brief = speech.audio_performance_brief
        fp = audio_input_fingerprint(speech)
        # Same established Role Dubbing producer fields, independently of the new selector.
        content = {
            "workId": args["work"].id, "sceneId": args["scene"].id, "shotId": args["shot"].id,
            "spokenContentId": turn.spoken_content_id, "speakerKey": turn.speaker_key,
            "voiceId": voice_id, "exactTextHash": text_hash(spoken["text"]),
            "voiceMasterContentHash": voice.content_hash, "voiceMaterialFingerprint": projection.voice_material_fingerprint,
            "sourceVideoMediaId": args["video"].id, "sourceVideoContentHash": args["video"].content_hash,
            "realizedPerformanceFingerprint": args["realized"].fingerprint,
            "dpdFingerprint": turn.dpd_fingerprint, "audioInputFingerprint": fp,
            "audioProjectionFingerprint": brief.fingerprint, "performanceInputFingerprint": brief.fingerprint,
            "baseAudioProjectionFingerprint": projection.base_audio_projection_fingerprint,
            "finalAudioProjectionFingerprint": projection.fingerprint,
            "voiceProviderMappingFingerprint": provider_mapping_fingerprint(mapping),
            "performanceAuthority": "VIDEO_CONDITIONED_FINAL_AUDIO", "technicalReviewStatus": "PASS",
            "reviewStatus": "PASS", "intelligibilityQc": {"status": "PASS", "cer": 0, "missing": [], "extra": [], "repetition": []},
        }
        media.append(Media(id=f"test-audio-{turn.sequence}", work_id=args["work"].id, shot_id=args["shot"].id,
                           media_type="AUDIO", purpose="ROLE_DUBBING_AUDIO", source_ref=f"role-dubbing:{fp}",
                           duration_ms=duration, content_hash=sha256_canonical({"testSequence": turn.sequence, "duration": duration}), content=content))
    args.update(current_audio_requests=requests, audio_candidates=media)
    return args


def hybrid_inputs():
    """Current fixture with the Turn-A final removed to preserve missing-audio coverage."""
    args = real_inputs()
    key = args["plan"].turns[0].spoken_content_id
    args["audio_candidates"] = [
        media for media in args["audio_candidates"]
        if not (media.content.get("spokenContentId") == key
                and media.content.get("performanceAuthority") == "VIDEO_CONDITIONED_FINAL_AUDIO")
    ]
    return args


def resign(payload):
    payload["fingerprint"] = sha256_canonical({k: v for k, v in payload.items() if k != "fingerprint"})
    return payload


def dialogue_led_inputs():
    """New DPD-led A + frozen video-conditioned B against a different target video."""
    args = complete_inputs()
    a, b = args['plan'].turns
    original_video = args['video'].model_copy(deep=True)
    original_rp = args['realized'].model_copy(deep=True)
    speech = args['current_audio_requests'][a.spoken_content_id]
    spoken = next(s for s in args['scene'].content['spokenContent'] if s['id'] == a.spoken_content_id)
    base = compile_projected_speech_request(work_id=args['work'].id,
        dpd_snapshot=args['dpd_by_spoken_content'][a.spoken_content_id],spoken_content=spoken,
        voice_profile=speech.voice_profile,voice_identity_ref=speech.audio_performance_brief.voice_identity_ref,
        timing_policy=TargetTimingPolicy(policy='NATURAL'),non_material_metadata={'shotId':args['shot'].id})
    base.provider_mapping = speech.provider_mapping
    args['current_audio_requests'][a.spoken_content_id] = base
    media = args['audio_candidates'][0]
    media.shot_id = None
    media.content.update(performanceAuthority='DPD_AUDIO_PROJECTION',
        audioInputFingerprint=audio_input_fingerprint(base),audioProjectionFingerprint=base.audio_performance_brief.fingerprint,
        performanceInputFingerprint=base.audio_performance_brief.fingerprint,
        sourceVideoMediaId=None,sourceVideoContentHash=None,realizedPerformanceFingerprint=None,
        voiceMaterialFingerprint=None,baseAudioProjectionFingerprint=None,finalAudioProjectionFingerprint=None)
    media.source_ref='role-dubbing:'+audio_input_fingerprint(base)
    args['video']=original_video.model_copy(update={'id':'new-dialogue-video','content_hash':'c'*64})
    args['realized']=build_realized_performance_snapshot({**dump_contract(original_rp),
        'videoMediaId':'new-dialogue-video','videoContentHash':'c'*64})
    args['accepted_realized_fingerprint']=args['realized'].fingerprint
    args['audio_source_videos_by_spoken_content']={b.spoken_content_id:original_video}
    args['audio_realized_by_spoken_content']={b.spoken_content_id:original_rp}
    return args


def test_dialogue_led_audio_and_explicit_frozen_b_preserve_actual_provenance():
    args=dialogue_led_inputs(); before=deepcopy(args)
    result=reconcile_dialogue_timing(**args)
    assert result.full_dialogue_coverage=='COMPLETE' and result.physical_feasibility=='FEASIBLE'
    assert args==before
    assert args['audio_candidates'][1].content['sourceVideoMediaId'] != result.video_media_id
    without=deepcopy(args);without.pop('audio_source_videos_by_spoken_content')
    with pytest.raises(ValueError,match='STALE'): reconcile_dialogue_timing(**without)


@pytest.mark.parametrize('changed',['audio','video','rp','source_scope','source_hash'])
def test_dialogue_led_reconciliation_stales_on_material_change(changed):
    args=dialogue_led_inputs(); result=reconcile_dialogue_timing(**args)
    b=args['plan'].turns[1].spoken_content_id
    if changed=='audio': args['audio_candidates'][0].content_hash='d'*64
    if changed=='video': args['video'].content_hash='d'*64
    if changed=='rp':
        args['realized']=build_realized_performance_snapshot({**dump_contract(args['realized']),'headMotion':'different observed motion'})
        args['accepted_realized_fingerprint']=args['realized'].fingerprint
    if changed=='source_scope': args['audio_source_videos_by_spoken_content'][b].shot_id='wrong-shot'
    if changed=='source_hash': args['audio_source_videos_by_spoken_content'][b].content_hash='d'*64
    with pytest.raises(ValueError): validate_dialogue_reconciliation(result,**args)


def test_fixture_a_full_realized_feasible_immutable_and_replayable():
    args = complete_inputs()
    before = deepcopy(args)
    result = reconcile_dialogue_timing(**args)
    assert result.physical_feasibility == "FEASIBLE"
    assert result.full_dialogue_coverage == "COMPLETE"
    assert result.evidence_mode == "REALIZED" and result.hybrid_feasibility == "NOT_NEEDED"
    assert result.required_minimum_duration_ms == result.full_realized_required_minimum_ms == 10000
    assert result.slack_ms == 1042 and result.proposed_post_hold_ms == 1542
    assert result.turns[1].proposed_start_ms == 6300
    assert args == before
    validate_dialogue_reconciliation(result, **args)


def test_fixture_b_drift_feasible_consumes_video_then_flexible_post():
    result = reconcile_dialogue_timing(**complete_inputs(b=4000))
    assert result.physical_feasibility == "FEASIBLE"
    assert result.turns[1].duration_delta_ms == 800
    assert result.consumed_video_delta_ms == 542
    assert result.flexible_post_slack_ms == 500 and result.consumed_post_slack_ms == 258
    assert result.required_minimum_duration_ms == 10800 and result.slack_ms == 242
    assert result.proposed_post_hold_ms == 742
    assert "DURATION_ESTIMATE_DRIFT" in result.candidate_causes
    assert "SHOT_DURATION" not in result.candidate_causes


def test_fixture_c_conflict_stops_before_placement_without_blame_or_repair():
    args = complete_inputs(a=6200, b=4107)
    result = reconcile_dialogue_timing(**args)
    assert result.physical_feasibility == "CONFLICT"
    assert result.required_minimum_duration_ms == 12107 and result.overflow_ms == 1065
    assert result.recommended_placement_status == "BLOCKED"
    assert all(t.proposed_start_ms is None and t.proposed_end_ms is None for t in result.turns)
    assert result.proposed_post_hold_ms is None and result.user_timing_review == "NOT_READY"
    assert "SHOT_DURATION" in result.candidate_causes
    assert "DIALOGUE_LENGTH" not in result.candidate_causes and "AUDIO_REALIZATION" not in result.candidate_causes
    assert [t.actual_duration_ms for t in result.turns] == [6200, 4107]


def test_current_real_fixture_is_full_realized_feasible_with_distinct_audio_production_lineage():
    args = real_inputs()
    result = reconcile_dialogue_timing(**args)
    assert [t.audio_status for t in result.turns] == ["PRESENT", "PRESENT"]
    assert result.turns[0].audio_media_id == "media_76a8fb24233246189d030babc7ceffd4"
    assert result.turns[1].audio_media_id == "media_6f4d16d785b84b52b3062e0666a826b5"
    assert [t.actual_duration_ms for t in result.turns] == [4571, 4107]
    assert [t.duration_delta_ms for t in result.turns] == [-429, 907]
    assert result.full_dialogue_coverage == "COMPLETE" and result.physical_feasibility == "FEASIBLE"
    assert result.evidence_mode == "REALIZED" and result.hybrid_feasibility == "NOT_NEEDED"
    assert result.required_minimum_duration_ms == result.full_realized_required_minimum_ms == 10478
    assert result.slack_ms == 564 and result.overflow_ms == 0
    assert [(t.proposed_start_ms, t.proposed_end_ms) for t in result.turns] == [
        (500, 5071), (5871, 9978),
    ]
    assert result.proposed_post_hold_ms == 1064
    assert result.recommended_placement_status == "PROPOSED" and result.user_timing_review == "REQUIRED"
    assert result.artistic_compatibility == "UNKNOWN"
    assert result.candidate_causes == ("DURATION_ESTIMATE_DRIFT", "TIMING_OBSERVABILITY")
    key = args["plan"].turns[0].spoken_content_id
    assert args["audio_dpd_by_spoken_content"][key].fingerprint != args["plan"].turns[0].dpd_fingerprint
    assert args["audio_realized_by_spoken_content"][key].fingerprint != args["realized"].fingerprint
    validate_dialogue_reconciliation(result, **args)


def test_fixture_d_missing_first_audio_is_only_conditional_hybrid():
    args = hybrid_inputs()
    result = reconcile_dialogue_timing(**args)
    assert [t.audio_status for t in result.turns] == ["MISSING", "PRESENT"]
    assert len(result.turns[0].rejected_audio_ids) == 7
    assert result.turns[1].audio_media_id == "media_6f4d16d785b84b52b3062e0666a826b5"
    assert result.full_dialogue_coverage == "INCOMPLETE" and result.physical_feasibility == "EVIDENCE_LIMITED"
    assert result.evidence_mode == "HYBRID" and result.hybrid_feasibility == "FEASIBLE"
    assert result.full_realized_required_minimum_ms is None
    assert result.required_minimum_duration_ms == 10907 and result.slack_ms == 135
    assert result.turns[0].actual_duration_ms is None and result.turns[0].duration_authority == "PLANNING_ESTIMATE"
    assert result.turns[1].actual_duration_ms == 4107 and result.turns[1].duration_delta_ms == 907
    assert result.consumed_video_delta_ms == 542 and result.consumed_post_slack_ms == 365
    assert [(t.proposed_start_ms, t.proposed_end_ms) for t in result.turns] == [(500, 5500), (6300, 10407)]
    assert result.proposed_post_hold_ms == 635
    assert result.recommended_placement_status == "CONDITIONAL_HYBRID" and result.user_timing_review == "REQUIRED"
    assert result.artistic_compatibility == "UNKNOWN"
    assert "MISSING_REALIZED_TURN_AUDIO" in result.candidate_causes


def test_current_audio_production_dpd_and_speaker_rp_are_required_for_freshness():
    args = real_inputs()
    args.pop("audio_dpd_by_spoken_content")
    args.pop("audio_realized_by_spoken_content")
    with pytest.raises(ValueError, match="CURRENT_AUDIO_REQUEST_STALE"):
        reconcile_dialogue_timing(**args)


@pytest.mark.parametrize("source,error", [
    ("dpd", "CURRENT_AUDIO_DPD_STALE"),
    ("rp", "CURRENT_AUDIO_REALIZED_PERFORMANCE_STALE"),
])
def test_stale_audio_production_inputs_fail_before_coverage(source, error):
    args = real_inputs()
    key = args["plan"].turns[0].spoken_content_id
    if source == "dpd":
        args["audio_dpd_by_spoken_content"][key].line.dramatic_action = "changed"
    else:
        args["audio_realized_by_spoken_content"][key].head_motion = "changed"
    with pytest.raises(ValueError, match=error):
        reconcile_dialogue_timing(**args)


def test_fixture_e_only_reaction_compression_would_fit_is_artistic_conflict():
    result = reconcile_dialogue_timing(**complete_inputs(b=4107, video_duration=10500))
    assert result.physical_feasibility == "CONFLICT" and result.artistic_compatibility == "CONFLICTING"
    assert result.required_minimum_duration_ms == 10907
    assert "REACTION_COMPRESSION_REQUIRED_TO_FIT" in result.diagnostics
    assert "SHOT_SEGMENTATION_REVIEW" in result.candidate_causes
    assert result.source_plan.turns[1].transition_hold_ms == 800
    assert result.turns[1].proposed_start_ms is None


@pytest.mark.parametrize("a, feasible", [(5135, True), (5136, False)])
def test_minimum_post_hold_exact_boundary_has_no_hidden_tolerance(a, feasible):
    result = reconcile_dialogue_timing(**complete_inputs(a=a, b=4107))
    assert (result.physical_feasibility == "FEASIBLE") is feasible
    assert result.proposed_post_hold_ms == (500 if feasible else None)
    assert result.overflow_ms == (0 if feasible else 1)


def test_new_actual_first_duration_moves_second_on_evidence():
    result = reconcile_dialogue_timing(**complete_inputs(a=5100, b=4107))
    assert result.turns[1].proposed_start_ms == 6400
    assert result.turns[0].proposed_end_ms == 5600
    assert result.proposed_post_hold_ms == 535


def test_pending_audio_is_measured_evidence_not_frozen_audio_acceptance():
    args = real_inputs()
    result = reconcile_dialogue_timing(**args)
    media = next(m for m in args["audio_candidates"] if m.id == result.turns[1].audio_media_id)
    speech = args["current_audio_requests"][result.turns[1].spoken_content_id]
    assert not is_audio_fresh(media.content, speech)  # existing accepted-use gate stays frozen
    assert result.turns[1].audio_review_status == "PENDING"
    assert "AUDIO_REVIEW_PENDING" in result.turns[1].audio_diagnostics
    assert result.user_timing_review == "REQUIRED"


@pytest.mark.parametrize("key, value", [
    ("exactTextHash", "0" * 64), ("speakerKey", "other"), ("voiceId", "old"),
    ("voiceMasterContentHash", "0" * 64), ("dpdFingerprint", "0" * 64),
    ("sourceVideoContentHash", "0" * 64), ("sourceVideoMediaId", "old"),
    ("realizedPerformanceFingerprint", "0" * 64), ("audioInputFingerprint", "0" * 64),
    ("finalAudioProjectionFingerprint", "0" * 64), ("voiceProviderMappingFingerprint", "0" * 64),
    ("technicalReviewStatus", "FAIL"), ("reviewStatus", "FAILED"), ("reviewStatus", "DEBUG"),
])
def test_stale_or_rejected_audio_durations_are_never_used(key, value):
    args = complete_inputs()
    args["audio_candidates"][0].content[key] = value
    result = reconcile_dialogue_timing(**args)
    assert result.turns[0].audio_status == "STALE"
    assert result.turns[0].actual_duration_ms is None
    assert result.physical_feasibility == "EVIDENCE_LIMITED"


def test_absent_and_ambiguous_audio_are_not_silently_selected():
    args = complete_inputs()
    args["audio_candidates"] = []
    none = reconcile_dialogue_timing(**args)
    assert none.evidence_mode == "PLANNING_ONLY" and none.recommended_placement_status == "BLOCKED"
    args = complete_inputs()
    args["audio_candidates"].append(args["audio_candidates"][0].model_copy(update={"id": "another-current-candidate"}, deep=True))
    ambiguous = reconcile_dialogue_timing(**args)
    assert ambiguous.turns[0].audio_status == "STALE"
    assert "AMBIGUOUS_CURRENT_AUDIO" in ambiguous.turns[0].audio_diagnostics


@pytest.mark.parametrize("change", ["hash", "duration", "review", "voiceCasting", "candidateSet"])
def test_current_material_changes_invalidate_prior_reconciliation(change):
    args = complete_inputs()
    old = reconcile_dialogue_timing(**args)
    if change == "hash": args["audio_candidates"][0].content_hash = "f" * 64
    elif change == "duration": args["audio_candidates"][0].duration_ms += 1
    elif change == "review": args["audio_candidates"][0].content["reviewStatus"] = "PENDING"
    elif change == "voiceCasting": next(iter(args["voices"].values())).content.creative_casting_profile["reviewNote"] = "changed"
    elif change == "candidateSet": args["audio_candidates"].pop(0)
    new = reconcile_dialogue_timing(**args)
    assert new.fingerprint != old.fingerprint
    with pytest.raises(ValueError, match="STALE_DIALOGUE_TIMING_RECONCILIATION"):
        validate_dialogue_reconciliation(old, **args)


@pytest.mark.parametrize("change, error", [
    ("text", "STALE_TIMING_INTENT"), ("speaker", "DPD_IDENTITY_MISMATCH"),
    ("plan", "FINGERPRINT_INVALID"), ("videoHash", "VIDEO_IDENTITY_MISMATCH"),
    ("videoDuration", "VIDEO_DURATION_INVALID"), ("rpHash", "REALIZED_PERFORMANCE_STALE"),
    ("acceptedRp", "REALIZED_PERFORMANCE_STALE"), ("voiceMaster", "CURRENT_AUDIO_REQUEST_STALE"),
    ("voiceBinding", "CURRENT_AUDIO_REQUEST_STALE"), ("audioRequest", "CURRENT_AUDIO_REQUEST_STALE"),
    ("missingTurn", "DPD_SCOPE_MISMATCH"), ("duplicateAudio", "DUPLICATE_AUDIO_MEDIA"),
])
def test_stale_source_inputs_fail_before_proposal(change, error):
    args = complete_inputs()
    if change == "text": args["scene"].content["spokenContent"][0]["text"] += "请注意。"
    elif change == "speaker": args["scene"].content["spokenContent"][0]["speakerKey"] = "other"
    elif change == "plan": args["plan"].fingerprint = "0" * 64
    elif change == "videoHash": args["video"].content_hash = "0" * 64
    elif change == "videoDuration": args["video"].duration_ms = 0
    elif change == "rpHash": args["realized"].head_motion = "different"
    elif change == "acceptedRp": args["accepted_realized_fingerprint"] = "0" * 64
    elif change == "voiceMaster": next(iter(args["voices"].values())).content_hash = "0" * 64
    elif change == "voiceBinding": args["work"].content["voiceProfiles"][0]["voiceId"] = "missing"
    elif change == "audioRequest": next(iter(args["current_audio_requests"].values())).work_id = "wrong"
    elif change == "missingTurn": args["shot"].content["spokenContentBindings"].pop()
    elif change == "duplicateAudio": args["audio_candidates"].append(args["audio_candidates"][0])
    with pytest.raises(ValueError, match=error): reconcile_dialogue_timing(**args)


def test_updated_video_and_rp_reject_old_audio_request_lineage():
    args = complete_inputs()
    args["video"].content_hash = "a" * 64
    raw = dump_contract(args["realized"], exclude={"fingerprint"})
    raw["videoContentHash"] = args["video"].content_hash
    args["realized"] = build_realized_performance_snapshot(raw)
    args["accepted_realized_fingerprint"] = args["realized"].fingerprint
    with pytest.raises(ValueError, match="CURRENT_AUDIO_REQUEST_STALE"):
        reconcile_dialogue_timing(**args)


@pytest.mark.parametrize("case, error", [
    ("version", "schemaVersion"), ("sourceFp", "SOURCE_PLAN_FINGERPRINT_MISMATCH"),
    ("video", "videoDurationMs"), ("missing", "FULL_SHOT_TURN_COVERAGE_REQUIRED"),
    ("duplicate", "TURN_IDENTITY_OR_ORDER_MISMATCH"), ("duration", "actualDurationMs"),
    ("negative", "proposedStartMs"), ("overlap", "PROTECTED_REACTION"),
    ("reaction", "PROTECTED_REACTION"), ("post", "MINIMUM_POST_HOLD"),
    ("budget", "PHYSICAL_BUDGET_MISMATCH"), ("authority", "DURATION_AUTHORITY_MISMATCH"),
    ("acceptance", "userTimingReview"), ("slack", "SLACK_REALLOCATION_MISMATCH"),
])
def test_contract_rejects_invalid_rehashed_artifacts(case, error):
    payload = dump_contract(reconcile_dialogue_timing(**complete_inputs()))
    if case == "version": payload["schemaVersion"] = "v2"
    elif case == "sourceFp": payload["sourceDialogueTimingPlanFingerprint"] = "0" * 64
    elif case == "video": payload["videoDurationMs"] = -1
    elif case == "missing": payload["turns"].pop()
    elif case == "duplicate": payload["turns"][1] = deepcopy(payload["turns"][0])
    elif case == "duration": payload["turns"][0]["actualDurationMs"] = 0
    elif case == "negative": payload["turns"][0]["proposedStartMs"] = -1
    elif case == "overlap": payload["turns"][1].update(proposedStartMs=5400, proposedEndMs=8600)
    elif case == "reaction": payload["turns"][1].update(proposedStartMs=5600, proposedEndMs=8800)
    elif case == "post": payload["proposedPostHoldMs"] = 499
    elif case == "budget": payload["requiredMinimumDurationMs"] += 1
    elif case == "authority": payload["turns"][0]["durationAuthority"] = "PLANNING_ESTIMATE"
    elif case == "acceptance": payload["userTimingReview"] = "ACCEPTED"
    elif case == "slack": payload["consumedPostSlackMs"] += 1
    with pytest.raises(ValidationError, match=error): DialogueTimingReconciliation.model_validate(resign(payload))


def test_contract_cannot_promote_hybrid_to_full_pass_or_conflict_to_proposal():
    hybrid = dump_contract(reconcile_dialogue_timing(**hybrid_inputs()))
    hybrid["physicalFeasibility"] = "FEASIBLE"
    with pytest.raises(ValidationError, match="COMPLETE_EVIDENCE"):
        DialogueTimingReconciliation.model_validate(resign(hybrid))
    conflict = dump_contract(reconcile_dialogue_timing(**complete_inputs(a=7000, b=5000)))
    conflict["turns"][0].update(proposedStartMs=500, proposedEndMs=7500)
    with pytest.raises(ValidationError, match="BLOCKED_PLACEMENT"):
        DialogueTimingReconciliation.model_validate(resign(conflict))


@pytest.mark.parametrize("field", ["Fish", "Comfy", "provider", "temporaryUrl", "exactText", "dialogueStartMs", "acceptedTiming"])
def test_unknown_fields_are_rejected_at_core_and_turn_boundary(field):
    payload = dump_contract(reconcile_dialogue_timing(**real_inputs()))
    with pytest.raises(ValidationError, match="extra_forbidden"):
        DialogueTimingReconciliation.model_validate({**payload, field: "injected"})
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ReconciledDialogueTurn.model_validate({**payload["turns"][0], field: "injected"})


def test_same_inputs_reordered_maps_and_candidate_set_have_same_result(monkeypatch):
    args = real_inputs()
    first = reconcile_dialogue_timing(**args)
    args["audio_candidates"].reverse()
    args["voices"] = dict(reversed(list(args["voices"].items())))
    for media in args["audio_candidates"]:
        media.content = dict(reversed(list(media.content.items())))
        media.content.update(timestamp="later", host="another", temporaryUrl="ignored", Fish={"request": "ignored"})
    def no_network(*a, **kw): raise AssertionError("unexpected network access")
    monkeypatch.setattr(socket, "socket", no_network)
    assert reconcile_dialogue_timing(**args) == first
    assert DialogueTimingReconciliation.model_validate_json(first.model_dump_json()) == first


def test_visible_head_window_remains_evidence_and_not_speech_anchor():
    result = reconcile_dialogue_timing(**real_inputs())
    assert result.visible_action_windows_ms["HEAD_MOTION"] == ((7500, 10500),)
    assert result.mouth_activity == "UNKNOWN" and result.artistic_compatibility == "UNKNOWN"
    assert result.turns[1].proposed_start_ms != 7500
    assert result.turns[1].proposed_end_ms != 10500


def test_known_visibility_constraint_blocks_incompatible_on_screen_proposal():
    result = reconcile_dialogue_timing(**complete_inputs(visible_start=8000))
    assert result.physical_feasibility == "FEASIBLE"
    assert result.artistic_compatibility == "CONFLICTING"
    assert "VISIBLE_COVERAGE_CONFLICT" in result.diagnostics
    assert result.recommended_placement_status == "BLOCKED"
    assert result.turns[1].proposed_start_ms is None


def test_observed_absent_mouth_activity_requires_artistic_review():
    result = reconcile_dialogue_timing(**complete_inputs(mouth="ABSENT"))
    assert result.artistic_compatibility == "QUESTIONABLE"
    assert "ON_SCREEN_MOUTH_ACTIVITY_ABSENT" in result.diagnostics
    assert result.user_timing_review == "REQUIRED"


def test_old_anchor_comparison_does_not_affect_reconciliation_bytes(tmp_path):
    base = [sys.executable, str(RUNNER), "--fixture", str(FIXTURE), "--output", str(tmp_path)]
    subprocess.run(base, check=True, capture_output=True)
    initial = (tmp_path / "dialogue-timing-reconciliation.json").read_bytes()
    old = json.loads((ROOT / "tests/fixtures/dialogue-timing-72-evaluation.json").read_text())
    for anchor in (5200, 9000):
        old["previousUserStartMs"] = anchor
        comparison = tmp_path / "comparison.json"
        comparison.write_text(json.dumps(old))
        subprocess.run([*base, "--historical-comparison", str(comparison)], check=True, capture_output=True)
        assert (tmp_path / "dialogue-timing-reconciliation.json").read_bytes() == initial
