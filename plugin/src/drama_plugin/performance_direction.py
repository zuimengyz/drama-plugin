"""Pure R2 coordination: authored direction, evidence comparison, never generation.

Natural-language quality and observation labels require a responsible reviewer.
Rules do not claim to perceive tears, hear speech or infer internal psychology.
"""
from __future__ import annotations
from typing import Any, Mapping
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.dpd import DPDSnapshot
from drama_plugin.dpd import compose_dpd
from drama_plugin.contracts.performance_direction import (
    DirectorPerformanceIntent, PerformanceProjection, PerformanceObservation,
)
from drama_plugin.contracts.visual_performance import VisualPerformanceBrief, RealizedPerformanceSnapshot
from drama_plugin.contracts.audio_projection import AudioPerformanceBrief
from drama_plugin.contracts.sequence import FilmReview, FilmFinding, SourcePin

LEVEL = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
ALIGNMENT_DIMENSIONS = frozenset({
    'emotional_amplitude', 'external_control', 'interaction_target', 'body_voice_effort',
    'breath', 'timing', 'pause', 'spatial_projection', 'partner_cue', 'release_point',
    'continuity', 'native_audio_suitability', 'story_meaning',
})
NATIVE_DIMENSIONS = frozenset({'dialogue', 'breath', 'effort', 'interaction_timing',
                             'voice_identity', 'performance', 'intelligibility'})


def validate_intent(intent: DirectorPerformanceIntent, dpd: DPDSnapshot,
                    current: Mapping[str, str]) -> DirectorPerformanceIntent:
    intent = DirectorPerformanceIntent.model_validate(dump_contract(intent))
    if compose_dpd(dpd.scene, dpd.beat, dpd.line) != dpd:
        raise ValueError('DPD_REVIEW_REQUIRED: source/effective fingerprint mismatch')
    if any(current.get(k) != h for k, h in intent.source_fingerprints.items()):
        raise ValueError('STALE_SOURCE: Director performance intent')
    if intent.dramaturgy_fingerprint is not None and current.get('dramaturgy:' + intent.scene_id) != intent.dramaturgy_fingerprint:
        raise ValueError('STALE_DIRECTOR_DRAMATURGY')
    if dpd.scene.source_fingerprint not in intent.source_fingerprints.values():
        raise ValueError('DPD source is not pinned by Director intent')
    if (dpd.fingerprint not in intent.dpd_fingerprints or dpd.effective.scene_id != intent.scene_id
            or dpd.effective.beat_id not in intent.beat_ids):
        raise ValueError('DPD_AUTHORITY_MISMATCH')
    return intent


def validate_projection(intent: DirectorPerformanceIntent, dpd: DPDSnapshot,
                        projection: PerformanceProjection, current: Mapping[str, str],
                        channel: str) -> PerformanceProjection:
    intent = validate_intent(intent, dpd, current)
    p = PerformanceProjection.model_validate(dump_contract(projection))
    e = dpd.effective
    if (p.channel != channel or p.director_intent_fingerprint != sha256_canonical(intent)
            or p.beat_id != e.beat_id or p.spoken_content_id != e.spoken_content_id):
        raise ValueError('DIRECTOR_INTENT_PROJECTION_MISMATCH')
    if p.interaction_target != e.interaction_target:
        raise ValueError('DPD_AUTHORITY_MISMATCH: interaction target')
    if intent.turn_fingerprints and p.turn_fingerprint != intent.turn_fingerprints.get(e.spoken_content_id):
        raise ValueError('EXACT_TURN_PROJECTION_MISMATCH')
    if p.external_control != e.external_control.value:
        raise ValueError('DPD_AUTHORITY_MISMATCH: external control')
    if LEVEL[p.external_expression] > LEVEL[intent.external_expression_ceiling]:
        raise ValueError('ANTI_OVERACTING: expression exceeds Director envelope')
    forbidden = set(intent.forbidden_behaviors)
    if e.external_control.value == 'HIGH':
        forbidden |= {'sobbing', 'collapse', 'emotional_collapse', 'continuous_shaking', 'theatrical_trembling'}
    if 'scripted_physical_loss_of_support' in p.behaviors and ('scripted_physical_loss_of_support' not in p.release or channel != 'VISUAL'):
        raise ValueError('SOURCE_BOUND_PHYSICAL_CONSEQUENCE_REQUIRED')
    if forbidden & set(p.behaviors):
        raise ValueError('ANTI_OVERACTING: forbidden observable behavior')
    if not set(p.release) <= set(intent.permitted_release):
        raise ValueError('DIRECTOR_INTENT_REVIEW_REQUIRED: release not permitted')
    expected = tuple(c for c in intent.coordination if c.beat_id == p.beat_id and c.spoken_content_id == p.spoken_content_id)
    if p.coordination != expected:
        raise ValueError('BEAT_COORDINATION_MISMATCH')
    if (p.continuity_in, p.continuity_out) != (intent.continuity_in, intent.continuity_out):
        raise ValueError('PERFORMANCE_CONTINUITY_MISMATCH')
    if p.context_fingerprint and (current.get('performance-context') != p.context_fingerprint or any(current.get('context-ref:'+r) != p.context_fingerprint for r in p.context_refs)):
        raise ValueError('STALE_PERFORMANCE_CONTEXT')
    if p.channel == 'VISUAL' and current.get('grammar:' + str(p.route)) != p.grammar_fingerprint:
        raise ValueError('STALE_VISUAL_PERFORMANCE_GRAMMAR')
    return p


def validate_turn_direction(scene: Mapping[str, Any], turn_id: str, dpd: DPDSnapshot,
                            intent: DirectorPerformanceIntent, projections: Mapping[str, Any],
                            current: Mapping[str, str]) -> None:
    """New formal direction requires the complete source → exact turn → intent chain."""
    from drama_plugin.screenplay_playability import dialogue_turn_fingerprint
    turn_hash = dialogue_turn_fingerprint(scene, turn_id, dpd)
    if intent.source_fingerprints.get('scenes:' + str(scene['id'])) != sha256_canonical(scene):
        raise ValueError('STALE_DIRECTOR_SCENE_BINDING')
    if not intent.dramaturgy_fingerprint or intent.turn_fingerprints.get(turn_id) != turn_hash:
        raise ValueError('STALE_DIRECTOR_TURN_BINDING')
    if set(projections) != {'VISUAL', 'VOICE'}:
        raise ValueError('EXACT_TURN_BOTH_PROJECTIONS_REQUIRED')
    for channel, value in projections.items():
        projection = PerformanceProjection.model_validate(dump_contract(value) if isinstance(value, PerformanceProjection) else value)
        if projection.turn_fingerprint != turn_hash:
            raise ValueError('EXACT_TURN_PROJECTION_MISMATCH')
        validate_projection(intent, dpd, projection, current, channel)


def visual_language(p: PerformanceProjection) -> dict[str, Any]:
    i = p.instructions
    return dict(body_activity='；'.join(i[k] for k in ('body_state', 'posture', 'weight', 'movement', 'visible_breath')),
                head_behavior=i['head'], gaze_behavior=i['eyes'], facial_tension=i['release'],
                gesture_policy=i['hands'] + '；' + i['prop'],
                interaction_orientation=i['partner'] + '；' + i['distance'],
                pre_speech_behavior=i['timing'], visible_control=i['continuity'],
                director_performance=dump_contract(p))


def voice_language(p: PerformanceProjection) -> dict[str, Any]:
    i = p.instructions
    return dict(pace=i['pace'], pace_tendency='NEUTRAL', rhythm=i['rhythm'],
                intensity=i['intensity'], volume_tendency='NEUTRAL',
                pause_strategy=i['pause_function'], articulation=i['articulation'],
                sentence_ending=i['sentence_closure'],
                control=i['voice_core'] + '；' + i['interaction'],
                director_performance=dump_contract(p))


def performance_envelope(dpd: DPDSnapshot, intent: DirectorPerformanceIntent,
                         current: Mapping[str, str]) -> dict[str, str]:
    validate_intent(intent, dpd, current)
    return {'Internal Pressure': dpd.effective.internal_activation.value,
            'External Expression Ceiling': intent.external_expression_ceiling,
            'Self Control': dpd.effective.external_control.value,
            'Director Language': intent.performance_core,
            'Release': intent.release_point, 'Continuity Out': intent.continuity_out}


def _verify_briefs(dpd: DPDSnapshot, intent: DirectorPerformanceIntent,
                   visual: VisualPerformanceBrief, audio: AudioPerformanceBrief,
                   current: Mapping[str, str]) -> tuple[PerformanceProjection, PerformanceProjection]:
    from drama_plugin.visual.performance import fingerprint_visual_projection
    from drama_plugin.audio.projection import fingerprint_audio_projection
    if visual.fingerprint != fingerprint_visual_projection(visual) or audio.fingerprint != fingerprint_audio_projection(audio):
        raise ValueError('STALE_PERFORMANCE_BRIEF')
    if (visual.dpd_fingerprint != dpd.fingerprint or audio.dpd_fingerprint != dpd.fingerprint
            or visual.scene_id != intent.scene_id or audio.scene_id != intent.scene_id
            or visual.primary_character_key != dpd.effective.actor or audio.speaker_key != dpd.effective.speaker
            or audio.spoken_content_id != dpd.effective.spoken_content_id):
        raise ValueError('ONE_DPD_REQUIRED')
    if not visual.director_performance or not audio.director_performance:
        raise ValueError('DIRECTOR_PERFORMANCE_PROJECTIONS_REQUIRED')
    return (validate_projection(intent, dpd, visual.director_performance, current, 'VISUAL'),
            validate_projection(intent, dpd, audio.director_performance, current, 'VOICE'))


def render_performance_pair(dpd: DPDSnapshot, intent: DirectorPerformanceIntent,
                            visual: VisualPerformanceBrief, audio: AudioPerformanceBrief,
                            current: Mapping[str, str]) -> str:
    """Critical Beat insert for the existing Production Book, not another book contract."""
    v, a = _verify_briefs(dpd, intent, visual, audio, current)
    pairs = [('整体控制', v.instructions['body_state'], a.instructions['voice_core']),
             ('对象', v.instructions['eyes'], a.instructions['interaction']),
             ('幅度／投射', v.instructions['movement'], a.instructions['spatial_projection']),
             ('释放', v.instructions['release'], a.instructions['release']),
             ('气息', v.instructions['visible_breath'], a.instructions['breath_support']),
             ('Partner cue', v.instructions['timing'], a.instructions['pause_function']),
             ('DO NOT', v.instructions['do_not'], a.instructions['do_not'])]
    def clean(x: str) -> str:
        return x.replace('|', '\\|').replace('\n', ' ')
    return (intent.performance_core + '\n\n| 维度 | Actor / Visual | Voice |\n|---|---|---|\n'
            + ''.join('| ' + ' | '.join(clean(x) for x in row) + ' |\n' for row in pairs))


def attach_cinematic_performance(spec: Any, *, dpd: DPDSnapshot, intent: DirectorPerformanceIntent,
                                 visual: VisualPerformanceBrief, audio: AudioPerformanceBrief,
                                 current: Mapping[str, str]) -> Any:
    """Transfer the reviewed projections into the one existing CinematicShotSpec."""
    from drama_plugin.contracts.cinematic import CinematicShotSpec
    from drama_plugin.audio.foundation import text_hash
    spec = CinematicShotSpec.model_validate(dump_contract(spec))
    v, a = _verify_briefs(dpd, intent, visual, audio, current)
    if spec.shot_id != visual.shot_id or spec.scene_id != intent.scene_id:
        raise ValueError('CINEMATIC_PERFORMANCE_SCOPE_MISMATCH')
    if (spec.performance.objective, spec.performance.interaction_target) != (dpd.effective.objective, dpd.effective.interaction_target):
        raise ValueError('DPD_AUTHORITY_MISMATCH')
    lines = [d for d in spec.dialogue if d.spoken_content_id == audio.spoken_content_id]
    if len(lines) != 1 or lines[0].speaker_key != audio.speaker_key or text_hash(lines[0].text) != audio.text_fingerprint:
        raise ValueError('CANONICAL_VOICE_BINDING_MISMATCH')
    if dpd.line.playability:
        from drama_plugin.screenplay_playability import exact_text_hash
        if (exact_text_hash(lines[0].text) != dpd.line.playability.source_text_hash
                or lines[0].target != dpd.effective.interaction_target):
            raise ValueError('SCREENPLAY_DIALOGUE_AUTHORITY_MISMATCH')
    payload = dump_contract(spec)
    payload['performance']['directorPerformance'] = dump_contract(v)
    for d in payload['dialogue']:
        if d['spokenContentId'] == audio.spoken_content_id:
            d['voicePerformance'] = dump_contract(a)
    return CinematicShotSpec.model_validate(payload)


def reconcile_realized_performance(dpd: DPDSnapshot, intent: DirectorPerformanceIntent,
                                   visual: VisualPerformanceBrief, realized: RealizedPerformanceSnapshot,
                                   current: Mapping[str, str]) -> dict[str, Any]:
    """Observed facts may require a timing repair; never rewrite story or source words."""
    from drama_plugin.visual.performance import fingerprint_realized_performance, fingerprint_visual_projection
    validate_intent(intent, dpd, current)
    if visual.fingerprint != fingerprint_visual_projection(visual) or not visual.director_performance:
        raise ValueError('STALE_OR_MISSING_VISUAL_PROJECTION')
    validate_projection(intent, dpd, visual.director_performance, current, 'VISUAL')
    realized = RealizedPerformanceSnapshot.model_validate(dump_contract(realized))
    if realized.fingerprint != fingerprint_realized_performance(realized) or realized.shot_id != visual.shot_id:
        raise ValueError('STALE_REALIZED_PERFORMANCE')
    observations = [o for o in realized.performance_observations if o.beat_id == dpd.effective.beat_id
                    and o.spoken_content_id == dpd.effective.spoken_content_id]
    if len(observations) != 1 or observations[0].speaker_key != dpd.effective.speaker:
        return {'status': 'INSUFFICIENT_EVIDENCE', 'owner': 'shot-production', 'reason': 'Observe the actual bound speaker/Beat; no guessed action windows.'}
    o = observations[0]
    if o.meaning_preserved == 'FAIL':
        return {'status': 'VISUAL_REVISION_REQUIRED', 'owner': 'shot-production', 'reason': 'Observed action changes story meaning; dubbing cannot repair it.'}
    if o.meaning_preserved == 'UNKNOWN':
        return {'status': 'INSUFFICIENT_EVIDENCE', 'owner': 'cinematic-finishing', 'reason': 'Review observed meaning before conditioning speech.'}
    forbidden = set(intent.forbidden_behaviors)
    if dpd.effective.external_control.value == 'HIGH':
        forbidden |= {'sobbing', 'collapse', 'emotional_collapse', 'continuous_shaking', 'theatrical_trembling'}
    if forbidden & set(o.behaviors):
        return {'status': 'VISUAL_REVISION_REQUIRED', 'owner': 'shot-production', 'reason': 'Observed body violates the performance envelope.'}
    # Do not infer mouth onset or invent a replacement speech duration.
    return {'status': 'REALIZED_TIMING_AVAILABLE', 'owner': 'audio-production',
            'realizedFingerprint': realized.fingerprint, 'observedEventsMs': dict(o.event_times_ms),
            'bodyLoad': o.body_load, 'breath': o.breath, 'evidenceRef': o.evidence_ref,
            'instruction': 'Reconcile phrase/pause execution with these observed actions; keep exact text, DPD and Voice identity. AV review remains required.',
            'adopted': False}


def review_av_performance(*, dpd: DPDSnapshot, intent: DirectorPerformanceIntent,
                          visual: VisualPerformanceBrief, audio: AudioPerformanceBrief,
                          realized: RealizedPerformanceSnapshot, review: FilmReview,
                          current: Mapping[str, str]) -> FilmReview:
    v, a = _verify_briefs(dpd, intent, visual, audio, current)
    from drama_plugin.visual.performance import fingerprint_realized_performance
    realized = RealizedPerformanceSnapshot.model_validate(dump_contract(realized))
    review = FilmReview.model_validate(dump_contract(review))
    if (realized.fingerprint != fingerprint_realized_performance(realized)
            or realized.video_content_hash != review.media_hash or realized.shot_id != visual.shot_id
            or realized.video_duration_ms != round(review.duration * 1000)):
        raise ValueError('AV_REVIEW_SOURCE_MISMATCH')
    if not review.performance_review_basis:
        raise ValueError('Explicit DESIGN_ONLY or OBSERVED_MEDIA basis required')
    evidence = tuple(realized.performance_observations) + tuple(o for o in review.performance_observations if o.channel == 'VOICE')
    evidence = tuple(o for o in evidence if o.beat_id == dpd.effective.beat_id and o.spoken_content_id == dpd.effective.spoken_content_id)
    if any(o.speaker_key != dpd.effective.speaker for o in evidence):
        raise ValueError('OBSERVED_SPEAKER_MISMATCH')
    if review.performance_review_basis == 'OBSERVED_MEDIA' and any(o.method == 'DESIGN_FIXTURE' for o in evidence):
        raise ValueError('DESIGN_FIXTURE_CANNOT_PROVE_MEDIA')
    beat_key = dpd.effective.beat_id + '#' + dpd.effective.spoken_content_id
    if beat_key not in review.performance_required_beats:
        raise ValueError('PERFORMANCE_BEAT_COVERAGE_REQUIRED')
    finding_prefix = 'AV:' + beat_key + ':'
    checks: dict[str, Any] = {k: 'UNKNOWN' for k in ALIGNMENT_DIMENSIONS}
    findings = [f for f in review.findings if not f.key.startswith(finding_prefix)]
    vos = [o for o in evidence if o.channel == 'VISUAL']; aos = [o for o in evidence if o.channel == 'VOICE']
    if len(vos) > 1 or len(aos) > 1:
        raise ValueError('Ambiguous performance observation; choose the actual evidence revision')
    if len(vos) == 1 and len(aos) == 1:
        vo, ao = vos[0], aos[0]
        def check(key: str, state: str, owner: str, code: str, observation: str) -> None:
            checks[key] = state
            if state == 'FAIL':
                findings.append(FilmFinding(key=finding_prefix + key, start=min(vo.start_ms, ao.start_ms) / 1000,
                    end=max(vo.end_ms, ao.end_ms) / 1000, domain='PERFORMANCE', severity='MAJOR',
                    observation=observation + f' Evidence: {vo.evidence_ref}; {ao.evidence_ref}',
                    consequence='Body and voice no longer enact the same bound performance.',
                    repair_owner=owner, proposed_repair=code + '; preserve Script text and DPD authority.'))
        def known_equal(x: Any, y: Any, expected: Any) -> str:
            return 'UNKNOWN' if x is None or y is None or x == 'UNKNOWN' or y == 'UNKNOWN' else ('PASS' if x == y == expected else 'FAIL')
        amp = 'UNKNOWN' if 'UNKNOWN' in (vo.external_expression, ao.external_expression) else ('PASS' if max(LEVEL[vo.external_expression], LEVEL[ao.external_expression]) <= LEVEL[intent.external_expression_ceiling] else 'FAIL')
        forbidden = set(intent.forbidden_behaviors)
        if dpd.effective.external_control.value == 'HIGH':
            forbidden |= {'sobbing', 'collapse', 'emotional_collapse', 'continuous_shaking', 'theatrical_trembling'}
        bad_v = bool(forbidden & set(vo.behaviors)); bad_a = bool(forbidden & set(ao.behaviors))
        if bad_v or bad_a: amp = 'FAIL'
        owner = 'shot-production' if bad_v or (vo.external_expression != 'UNKNOWN' and LEVEL[vo.external_expression] > LEVEL[intent.external_expression_ceiling]) else 'audio-production'
        check('emotional_amplitude', amp, owner, 'VISUAL_REVISION_REQUIRED' if owner == 'shot-production' else 'VOICE_REVISION_REQUIRED', 'External expression / forbidden release exceeds intent.')
        check('external_control', known_equal(vo.external_control, ao.external_control, dpd.effective.external_control.value), 'shot-production' if vo.external_control not in ('UNKNOWN', dpd.effective.external_control.value) else 'audio-production', 'PERFORMANCE_REVISION_REQUIRED', 'Observed control conflicts with DPD externalControl.')
        check('interaction_target', known_equal(vo.interaction_target, ao.interaction_target, dpd.effective.interaction_target), 'shot-production' if vo.interaction_target not in (None, dpd.effective.interaction_target) else 'audio-production', 'PERFORMANCE_REVISION_REQUIRED', 'Interaction targets differ.')
        spatial = 'UNKNOWN' if not vo.spatial_projection or not ao.spatial_projection else ('PASS' if vo.spatial_projection == v.spatial_projection and ao.spatial_projection == a.spatial_projection else 'FAIL')
        check('spatial_projection', spatial, 'audio-production', 'VOICE_REVISION_REQUIRED', 'Voice projection does not reach the intended spatial recipient.')
        load = 'UNKNOWN' if 'UNKNOWN' in (vo.body_load, ao.body_load) else ('FAIL' if vo.body_load != ao.body_load or (vo.body_load == 'HIGH' and 'unbroken_ceremonial_breath' in ao.behaviors) else 'PASS')
        check('body_voice_effort', load, 'audio-production', 'VOICE_REVISION_REQUIRED', 'Observed body load and vocal support/effort conflict.')
        breath = 'UNKNOWN' if not vo.breath or not ao.breath else ('PASS' if vo.breath == ao.breath else 'FAIL')
        check('breath', breath, 'audio-production', 'VOICE_REVISION_REQUIRED', 'Visible and audible breathing belong to different effort states.')
        release = 'PASS' if set(vo.release) <= set(intent.permitted_release) and set(ao.release) <= set(intent.permitted_release) else 'FAIL'
        check('release_point', release, 'shot-production' if not set(vo.release) <= set(intent.permitted_release) else 'audio-production', 'PERFORMANCE_REVISION_REQUIRED', 'Observed release is not permitted at this Beat.')
        continuity = 'UNKNOWN' if any(x is None for x in (vo.continuity_in, vo.continuity_out, ao.continuity_in, ao.continuity_out)) else ('PASS' if (vo.continuity_in, ao.continuity_in) == (intent.continuity_in,) * 2 and (vo.continuity_out, ao.continuity_out) == (intent.continuity_out,) * 2 else 'FAIL')
        check('continuity', continuity, 'director', 'DIRECTOR_INTENT_REVIEW_REQUIRED', 'Release was carried beyond its intended continuity boundary.')
        events = dict(vo.event_times_ms)
        if any(k in events and events[k] != val for k, val in ao.event_times_ms.items()):
            raise ValueError('Conflicting event observations require reconciliation')
        events.update(ao.event_times_ms)
        timing = 'PASS'; reasons = []; timing_owners: set[str] = set()
        for c in v.coordination:
            required = [c.event, c.anchor] + ([c.end_anchor] if c.end_anchor else [])
            if any(k not in events for k in required):
                if timing != 'FAIL': timing = 'UNKNOWN'
                continue
            event, anchor = events[c.event], events[c.anchor]
            okay = (event + c.tolerance_ms >= anchor if c.relation == 'NOT_BEFORE' else event <= anchor + c.tolerance_ms if c.relation == 'NOT_AFTER' else anchor - c.tolerance_ms <= event <= events[str(c.end_anchor)] + c.tolerance_ms)
            if not okay:
                timing = 'FAIL'; reasons.append(c.reason)
                timing_owners.add('shot-production' if c.event in vo.event_times_ms else 'audio-production')
        timing_owner = next(iter(timing_owners)) if len(timing_owners) == 1 else 'director'
        check('timing', timing, timing_owner, 'TIMING_RECONCILIATION_REQUIRED', '; '.join(reasons) or 'Missing or inconsistent observed event timing.')
        check('pause', timing, 'audio-production', 'TIMING_RECONCILIATION_REQUIRED', 'Phrase pause must retain the partner/action event relationship.')
        check('partner_cue', timing, 'shot-production', 'TIMING_RECONCILIATION_REQUIRED', 'Partner response must complete before the dependent action.')
        meaning = 'FAIL' if 'FAIL' in (vo.meaning_preserved, ao.meaning_preserved) else 'UNKNOWN' if 'UNKNOWN' in (vo.meaning_preserved, ao.meaning_preserved) else 'PASS'
        check('story_meaning', meaning, 'shot-production' if vo.meaning_preserved == 'FAIL' else 'audio-production', 'VISUAL_REVISION_REQUIRED' if vo.meaning_preserved == 'FAIL' else 'VOICE_REVISION_REQUIRED', 'Actual performance changes source meaning; do not add corrective dialogue.')
    native = review.native_audio_suitability
    checks['native_audio_suitability'] = ('UNKNOWN' if set(native) != NATIVE_DIMENSIONS or 'UNKNOWN' in native.values() else 'FAIL' if 'FAIL' in native.values() else 'PASS')
    refs = tuple(SourcePin(key=beat_key + ':' + k, kind='DIRECTION', fingerprint=h) for k, h in (
        ('dpd', dpd.fingerprint), ('director-performance', sha256_canonical(intent)),
        ('visual-performance', visual.fingerprint), ('voice-performance', audio.fingerprint), ('realized-performance', realized.fingerprint)))
    beat_checks = {**review.performance_beats, beat_key: checks}
    aggregate = {k: ('FAIL' if any(row.get(k) == 'FAIL' for row in beat_checks.values()) else 'UNKNOWN' if set(beat_checks) != set(review.performance_required_beats) or any(row.get(k, 'UNKNOWN') == 'UNKNOWN' for row in beat_checks.values()) else 'PASS') for k in ALIGNMENT_DIMENSIONS}
    retained_evidence = tuple(o for o in review.performance_observations if o.beat_id + '#' + o.spoken_content_id != beat_key)
    retained_refs = tuple(p for p in review.performance_refs if not p.key.startswith(beat_key + ':'))
    material = dump_contract(review)
    material.update(performanceAlignment=aggregate, performanceBeats=beat_checks, performanceRefs=[dump_contract(p) for p in (*retained_refs, *refs)],
                    performanceObservations=[dump_contract(o) for o in (*retained_evidence, *evidence)], findings=[dump_contract(f) for f in findings])
    if review.director:
        material['director'] = {**dump_contract(review.director), 'disposition': 'INSUFFICIENT_EVIDENCE' if 'UNKNOWN' in aggregate.values() else 'REVISE_PERFORMANCE' if 'FAIL' in aggregate.values() else review.director.disposition,
                                'findingKeys': [f.key for f in findings]}
    return FilmReview.model_validate(material)


def native_audio_disposition(review: FilmReview, *, local_finding_keys: tuple[str, ...] = (),
                             replacement_reason: str | None = None) -> dict[str, Any]:
    """Review-first semantic decision; no Tool/Media/Voice request is created."""
    review = FilmReview.model_validate(dump_contract(review))
    base: dict[str, Any] = {'providerCalls': 0, 'generationAuthorized': False, 'adopted': False,
                           'reviewBasis': review.performance_review_basis, 'mediaHash': review.media_hash}
    if review.performance_review_basis != 'DESIGN_ONLY':
        from drama_plugin.sequence import _coverage
        if _coverage(review, {'AUDIO', 'NORMAL_AV'}):
            return {**base, 'disposition': 'REVIEW_REQUIRED', 'reason': 'Complete listening evidence missing.'}
    native = review.native_audio_suitability
    if set(native) != NATIVE_DIMENSIONS or 'UNKNOWN' in native.values():
        return {**base, 'disposition': 'REVIEW_REQUIRED', 'reason': 'Native speech/performance remains unknown.'}
    findings = {f.key: f for f in review.findings if not f.resolved}
    bounded_audio = tuple(f.key for f in findings.values() if f.domain == 'SOUND' and f.end > f.start and (f.start > 0 or f.end < review.duration))
    global_audio = any(f.domain == 'SOUND' and f.start == 0 and f.end == review.duration for f in findings.values())
    if bounded_audio and not global_audio:
        if replacement_reason:
            raise ValueError('Local audio evidence cannot authorize full dialogue replacement')
        if not local_finding_keys:
            local_finding_keys = bounded_audio
    if local_finding_keys:
        if replacement_reason or any(k not in findings for k in local_finding_keys):
            raise ValueError('Local repair cannot be silently escalated to full dubbing')
        chosen = [findings[k] for k in local_finding_keys]
        if any(f.domain not in ('SOUND', 'PERFORMANCE') or f.end <= f.start or (f.start == 0 and f.end == review.duration) for f in chosen):
            raise ValueError('LOCAL_REPAIR requires bounded reviewed audio findings')
        return {**base, 'disposition': 'LOCAL_REPAIR', 'existingStrategy': 'LOCAL_REPLACE',
                'replaceWindows': [{'startMs': round(f.start * 1000), 'endMs': round(f.end * 1000), 'finding': f.key} for f in chosen],
                'fullReplacementAllowed': False}
    if any(f.severity == 'MAJOR' and f.repair_owner == 'audio-production' for f in findings.values()) and not replacement_reason:
        return {**base, 'disposition': 'REVIEW_REQUIRED', 'reason': 'AV voice conflict must be reviewed/localized before native reuse or replacement.'}
    if all(value == 'PASS' for value in native.values()):
        if replacement_reason: raise ValueError('Good native performance cannot require TTS merely because direction exists')
        return {**base, 'disposition': 'KEEP_NATIVE', 'existingStrategy': 'PRESERVE',
                'externalAudio': [], 'timeline': [], 'newMedia': False}
    allowed = {'dialogue_missing', 'unusable_speech', 'wrong_voice_identity', 'severe_intelligibility', 'fundamental_performance_violation'}
    if replacement_reason not in allowed:
        return {**base, 'disposition': 'REVIEW_REQUIRED', 'reason': 'Localize the actual defect before choosing replacement.'}
    required_failure = {'dialogue_missing':'dialogue', 'unusable_speech':'dialogue', 'wrong_voice_identity':'voice_identity', 'severe_intelligibility':'intelligibility', 'fundamental_performance_violation':'performance'}
    if native.get(required_failure[str(replacement_reason)]) != 'FAIL':
        raise ValueError('Dubbing reason has no corresponding reviewed failure')
    return {**base, 'disposition': 'DUBBING_REQUIRED', 'existingStrategy': 'explicit reviewed speech + AvAssemblyManifest',
            'reason': replacement_reason, 'owner': 'audio-production', 'needsRealizedPerformance': True}


def validate_action_performance(intent: DirectorPerformanceIntent, *, action_ref: str,
                                source_action: str, behavior: str, action_completed: bool) -> None:
    """Silent/action projection uses a source-exact anchor, not a vocal emotion cap."""
    if behavior in intent.forbidden_behaviors or behavior in {'collapse','emotional_collapse'}:
        raise ValueError('ANTI_OVERACTING: emotional or ambiguous collapse')
    if behavior == 'scripted_physical_loss_of_support':
        if intent.physical_consequences.get(action_ref)!=source_action or not action_completed:
            raise ValueError('SCRIPTED_PHYSICAL_CONSEQUENCE_ORDER_REQUIRED')
