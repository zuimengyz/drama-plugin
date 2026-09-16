"""Opt-in local capability boundaries. No LLM planner, Provider submission or formal write.

Inputs/results remain original specialized contracts. This adapter can establish
CONTRACT_VALID only; creative evidence and adoption still require Director review.
"""
from __future__ import annotations
from typing import Any, Callable, Mapping
from pathlib import Path
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.creation import Scene, Shot
from drama_plugin.contracts.director import CapabilityFeedback, CapabilityRequest
from drama_plugin.contracts.dpd import SceneDPD, BeatDPD, LineDPD
from drama_plugin.contracts.dramatic_editorial import EditorialRhythmPlan, PictureEditPlan
from drama_plugin.contracts.cinematic import CinematicShotSpec
from drama_plugin.contracts.sequence import SourcePin, SequencePackage, FilmReview
from drama_plugin.contracts.visual_route import RouteContext
from drama_plugin.contracts.audio import AvAssemblyManifest
from drama_plugin.director import DirectorError, freshness, request_pin
from drama_plugin.dpd import compose_dpd
from drama_plugin.production_design import picture_edit_handoff
from drama_plugin.sequence import sequence_handoff, film_review_verdict
from drama_plugin.visual.cinematic import freeze_direction
from drama_plugin.visual.video_selection import Requirements, Candidate, qualify
from drama_plugin.visual_route import bind_route_artifact
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore

CAPABILITIES = frozenset({'scene-development', 'dramatic-performance-direction', 'shot-design',
    'cinematic-direction', 'video-model-selection', 'shot-production', 'audio-production', 'cinematic-finishing'})
# Explicit dispatch destinations, not a mandatory chain or autonomous repair loop.
REVISION_TARGETS = {
    'REVISE_EXECUTION': 'shot-production', 'REVISE_PERFORMANCE': 'dramatic-performance-direction',
    'REVISE_BLOCKING': 'shot-design', 'REVISE_COVERAGE': 'shot-design',
    'REVISE_EDIT': 'cinematic-finishing', 'REVISE_SOUND': 'audio-production',
    'REPLAN_SCENE': 'scene-development', 'REQUEST_SCRIPT_REVIEW': 'cinematic-screenplay-incubation',
    'ESCALATE_PRODUCTION_METHOD': 'video-model-selection',
}


def next_responsibility(disposition: str, *, revision_cycles: int = 0) -> dict[str, Any]:
    if revision_cycles < 0:
        raise ValueError('Invalid revision count')
    stop = {'APPROVE': 'APPROVED', 'REQUEST_SCRIPT_REVIEW': 'UPSTREAM_REVIEW_REQUIRED',
            'INSUFFICIENT_EVIDENCE': 'INSUFFICIENT_EVIDENCE',
            'ESCALATE_PRODUCTION_METHOD': 'PRODUCTION_METHOD_ESCALATION'}
    if disposition not in stop and disposition not in REVISION_TARGETS:
        raise ValueError('Unknown Director disposition')
    return {'stop': stop.get(disposition, 'ITERATION_BOUND_REACHED' if revision_cycles >= 1 else 'DIRECTOR_REQUEST_REQUIRED'),
            'capability': REVISION_TARGETS.get(disposition), 'automaticDispatch': False}


class LocalCapabilityBridge:
    """Validate real registry membership and source-bound specialized local contracts.

    Registry lookup does not imply an LLM ran SKILL.md. This is callable contract
    integration; a Host supplies professional decisions as original input artifacts.
    """
    def __init__(self, store: DirectorArtifactStore, skill_lookup: Callable[[str], Any],
                 media_path: Callable[[str], Path] | None = None):
        self.store, self.skill_lookup = store, skill_lookup
        self.media_path = media_path

    def run(self, request: CapabilityRequest, input_ref: SourcePin,
            current: Mapping[str, str]) -> CapabilityFeedback:
        if request.capability not in CAPABILITIES:
            raise DirectorError('CAPABILITY_LIMITATION', 'Capability not wired in the local bridge')
        self.skill_lookup(request.capability)
        if input_ref not in request.requirement_refs:
            raise DirectorError('INVALID_SOURCE', 'Input must be a pinned requirement artifact')
        pins = (*request.source_pins, *request.intent_refs, *request.requirement_refs,
                *((request.route_ref,) if request.route_ref else ()))
        if freshness(pins, current):
            raise DirectorError('STALE_SOURCE', 'Capability input or intent changed')
        if request.result_kind != 'DESIGN_ONLY':
            raise DirectorError('CAPABILITY_LIMITATION', 'This bridge never generates Media')
        inputs = self.store.read_ref(input_ref)
        output, feedback = self._invoke(request, inputs, current)
        result = self.store.put('result:' + request_pin(request).fingerprint, output)
        evidence = self.store.put('boundary:' + request_pin(request).fingerprint, {
            'mode': 'DESIGN_ONLY', 'capability': request.capability, 'inputRef': dump_contract(input_ref),
            'resultRef': dump_contract(result), 'mustPreserve': list(request.must_preserve),
            'prohibitions': list(request.prohibitions), 'checked': ['CONTRACT_VALID'],
            'artisticObservation': 'NOT_OBSERVED', 'providerCalls': 0})
        fulfilled = tuple(x for x in request.required_evidence if x == 'CONTRACT_VALID')
        base = dict(request_ref=request_pin(request), source_pins=request.source_pins,
            result_refs=(result,), evidence_refs=(evidence,), execution='COMPLETED',
            feasibility='SUPPORTED', fulfilled=fulfilled,
            unmet=tuple(x for x in request.required_evidence if x not in fulfilled),
            next_responsibility='Director review')
        return CapabilityFeedback.model_validate({**base, **feedback})

    def _invoke(self, q: CapabilityRequest, data: dict[str, Any], current: Mapping[str, str]
                ) -> tuple[dict[str, Any], dict[str, Any]]:
        name = q.capability
        def scope(value: str) -> None:
            if value != q.scope_id:
                raise DirectorError('INVALID_SOURCE', 'Capability belongs to another scene/scope')
        if name == 'scene-development':
            scene = Scene.model_validate(data['scene']); scope(scene.id)
            if not any(p.fingerprint == sha256_canonical(scene) for p in q.source_pins):
                raise DirectorError('INVALID_SOURCE', 'Canonical Scene is not the pinned source')
            # An interpretation never overwrites canonical content, even on conflict.
            conflict = data.get('proposedContent', scene.content) != scene.content
            return dump_contract(scene), ({'limitations': ('LOCKED_SOURCE_CONFLICT',),
                'next_responsibility': 'REQUEST_SCRIPT_REVIEW', 'feasibility': 'UNSUPPORTED_CURRENTLY'} if conflict else {})
        if name == 'dramatic-performance-direction':
            dpd_scene, beat, line = (SceneDPD.model_validate(data['scene']), BeatDPD.model_validate(data['beat']),
                                 LineDPD.model_validate(data['line']))
            scope(dpd_scene.scene_id); scope(beat.scene_id); scope(line.scene_id)
            if dpd_scene.source_fingerprint not in {p.fingerprint for p in q.source_pins}:
                raise DirectorError('STALE_SOURCE', 'DPD no longer belongs to the pinned Scene')
            return dump_contract(compose_dpd(dpd_scene, beat, line)), {}
        if name == 'shot-design':
            plan = EditorialRhythmPlan.model_validate(data['plan'])
            if q.scope_id not in plan.scene_ids or plan.source_fingerprint not in {p.fingerprint for p in q.source_pins}:
                raise DirectorError('INVALID_SOURCE', 'Coverage must retain source Scene')
            return dump_contract(plan), {}
        if name == 'cinematic-direction':
            spec = CinematicShotSpec.model_validate(data['spec']); scope(spec.scene_id)
            if sha256_canonical(Scene.model_validate(data['context']['scene'])) not in {p.fingerprint for p in q.source_pins}:
                raise DirectorError('STALE_SOURCE', 'Cinematic context Scene changed')
            frozen = freeze_direction(spec, context=data['context'], visual_resolution=data['visual'],
                host_review=data['reviewSummary'])
            if q.route_ref:
                context = RouteContext.model_validate(self.store.read_ref(q.route_ref))
                scope(context.sequence.sequence_key)
                frozen = bind_route_artifact(frozen, context, responsibility='CAMERA')
            return frozen, {}
        if name == 'video-model-selection':
            r = Requirements.model_validate(data['requirements']); scope(r.scene_id)
            c = Candidate.model_validate(data['candidate'])
            result = qualify(r, c)
            failed = result['exclusions']
            # Only observed complex direction failures suggest decomposition; UNKNOWN stays UNKNOWN.
            direction_failed = any(x.startswith('DIRECTOR_REQUIREMENT_FAILED:') for x in failed)
            return result, {'feasibility': 'REQUIRES_DECOMPOSITION' if direction_failed else
                ('UNKNOWN' if failed or result['qualification'] == 'LIMITED_TRIAL' else 'SUPPORTED'),
                'limitations': tuple(failed), 'unknowns': ('Unverified production/artistic capability',) if result['qualification'] == 'LIMITED_TRIAL' else (),
                'next_responsibility': 'shot-design / production method' if direction_failed else 'Director review'}
        if name == 'shot-production':
            from drama_plugin.visual.production import check_campaign
            state = data['campaign']; check_campaign(state)
            shot = Shot.model_validate(data['shot']); scope(shot.scene_id)
            attempt = next((a for a in state['attempts'] if a['attempt_id'] == data['attemptId']), None)
            if attempt is None:
                raise DirectorError('INSUFFICIENT_EVIDENCE', 'Execution owner has no such attempt')
            if attempt['shot_id'] != shot.id:
                raise DirectorError('INVALID_SOURCE', 'Execution result belongs to another Shot')
            frame = state['frames'][shot.id]
            if frame['spec']['shot_fingerprint'] != sha256_canonical(shot):
                raise DirectorError('STALE_SOURCE', 'Production replay Shot fingerprint changed')
            # Read-only replay; only the original execution record knows completion.
            return {'attempt': attempt, 'mode': 'REPLAY_EVIDENCE_ONLY'}, {
                'feasibility': 'UNKNOWN', 'unknowns': ('Production replay is not creative adoption',),
                'limitations': (str(state.get('pause') or 'Actual audiovisual judgment still required'),),
                'next_responsibility': 'Director review' if attempt['status'] == 'COMPLETED' else 'RECONCILIATION_REQUIRED'}
        if name == 'audio-production':
            manifest = AvAssemblyManifest.model_validate(data['manifest'])
            if manifest.audio_mix_media_id or manifest.speech_clip_media_ids or manifest.timeline:
                raise DirectorError('CAPABILITY_LIMITATION', 'Local integration permits native reuse only; NO TTS REPLACEMENT')
            from drama_plugin.audio.host_media import assemble_av
            if self.media_path is None:
                raise DirectorError('INSUFFICIENT_EVIDENCE', 'Host must resolve the stable source Media reference')
            result = assemble_av(self.media_path(manifest.source_video_media_id), manifest=manifest,
                                 source_video_hash=data['sourceHash'], dry_run=True)
            # Execution paths belong to Audio, not the portable Director workspace.
            return {k: v for k, v in result.items() if not k.endswith('Path') and k != 'path'}, {
                'unknowns': ('Listening/artistic approval NOT_OBSERVED',)}
        # Existing Finishing owners and gates, not a parallel Director edit/review object.
        result = {}
        if 'plan' in data:
            if data['canonFingerprint'] not in {p.fingerprint for p in q.source_pins}:
                raise DirectorError('STALE_SOURCE', 'Edit no longer belongs to the pinned Canon')
            result['edit'] = picture_edit_handoff(PictureEditPlan.model_validate(data['plan']),
                current_sources=data['mediaHashes'], canon_fingerprint=data['canonFingerprint'])
        if 'package' in data:
            package = SequencePackage.model_validate(data['package']); scope(package.scope_id)
            result['sequence'] = sequence_handoff(package, dict(current))
        if 'review' in data:
            result['review'] = film_review_verdict(FilmReview.model_validate(data['review']),
                data['mediaHash'], require_director=True)
        if not result:
            raise DirectorError('INSUFFICIENT_EVIDENCE', 'Finishing needs an existing owner contract')
        return result, {}
