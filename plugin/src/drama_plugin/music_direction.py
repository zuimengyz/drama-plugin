"""Pure score planning, alignment and execution requirements. Never generates audio."""
from __future__ import annotations
from typing import Any, Mapping, Sequence
from drama_plugin.contracts.base import dump_contract,sha256_canonical
from drama_plugin.contracts.film_score import FilmScorePlan,MusicCue
from drama_plugin.contracts.performance_direction import DirectorPerformanceIntent
from drama_plugin.contracts.preproduction import DepartmentConflict
from drama_plugin.contracts.sequence import SourcePin,FilmFinding


def review_score_plan(plan: FilmScorePlan, *, current: Mapping[str,str],
                      expected_scene_ids: Sequence[str],
                      performance_intents: Mapping[str,DirectorPerformanceIntent],
                      excluded_performance_refs: Sequence[str] = ()) -> dict[str,Any]:
    plan=FilmScorePlan.model_validate(dump_contract(plan))
    pins=(*plan.source_pins,plan.film_intent_ref,*(d.performance_intent_ref for d in plan.scene_music_decisions),
          *(p for c in plan.music_cues for p in (*c.binding_refs,*c.vocal_approval_refs.values())),
          *(p for c in plan.music_cues if c.yield_policy for p in (*c.yield_policy.protected_no_score_refs,*(e.source_ref for e in c.yield_policy.events))))
    if any(current.get(p.key)!=p.fingerprint for p in pins):raise ValueError('STALE_FILM_SCORE_SOURCE')
    if set(plan.scene_ids)!=set(expected_scene_ids):raise ValueError('ALL_SCENES_REQUIRE_MUSIC_REVIEW')
    if not set(excluded_performance_refs)<=set(plan.excluded_performance_refs):raise ValueError('HISTORICAL_VERSE_EXCLUSION_REQUIRED')
    conflicts=[]
    cues={c.cue_id:c for c in plan.music_cues}
    for d in plan.scene_music_decisions:
        intent=performance_intents.get(d.scene_id)
        if intent is None or d.performance_intent_ref.fingerprint!=sha256_canonical(intent):raise ValueError('MUSIC_PERFORMANCE_INTENT_BINDING_REQUIRED')
        if any(current.get(k)!=v for k,v in intent.source_fingerprints.items()):raise ValueError('STALE_DIRECTOR_PERFORMANCE_INTENT')
        constraints=set(intent.music_constraints)
        for cue_ref in d.cue_refs:
            c=cues[cue_ref];violations=[]
            if 'NO_SCORE' in constraints:violations.append('DIRECTOR_REQUIRES_NO_SCORE')
            if 'PRESERVE_REAL_JOY' in constraints and c.emotional_direction=='MOURNING':violations.append('REAL_JOY_PREMATURELY_TRAGIC')
            if 'NO_FATALISTIC_FORESHADOWING' in constraints and c.emotional_direction=='MOURNING':violations.append('PREMATURE_FATALISTIC_SCORE')
            if c.performance_relation in ('DUPLICATE_EMOTION','PREMATURE_FORESHADOWING'):violations.append(c.performance_relation)
            for code in violations:
                conflicts.append(dump_contract(DepartmentConflict(code=code,
                    subject_refs=(SourcePin(key='score:'+plan.scope_id,kind='DESIGN',fingerprint=sha256_canonical(plan)),d.performance_intent_ref),
                    evidence=d.performance_alignment+'; cue='+c.cue_id,repair_owner='music-direction')))
    return {'status':'DEPARTMENT_CONFLICT' if conflicts else 'SCORE_DESIGN_REVIEW_READY','conflicts':conflicts,
            'sceneCoverage':len(plan.scene_music_decisions),'scoreScenes':sum(bool(d.cue_refs) for d in plan.scene_music_decisions),
            'allScenesHaveMusic':all(bool(d.cue_refs) for d in plan.scene_music_decisions),
            'artisticObservation':'NOT_OBSERVED','providerCalls':0,'productionAuthorized':False}


def composer_brief(plan: FilmScorePlan, cue_ref: str, *, current: Mapping[str,str]) -> dict[str,Any]:
    plan=FilmScorePlan.model_validate(dump_contract(plan))
    if cue_ref in plan.excluded_performance_refs:raise ValueError('HISTORICAL_VERSE_NOT_APPLICABLE_TO_COMPOSER')
    cue=next((c for c in plan.music_cues if c.cue_id==cue_ref),None)
    if cue is None:raise ValueError('NOT_A_MUSIC_CUE')
    if any(current.get(p.key)!=p.fingerprint for p in (*plan.source_pins,plan.film_intent_ref)):raise ValueError('STALE_FILM_SCORE_SOURCE')
    if cue.yield_policy and any(current.get(p.key)!=p.fingerprint for p in (*cue.yield_policy.protected_no_score_refs,*(e.source_ref for e in cue.yield_policy.events))):raise ValueError('STALE_MUSIC_PLACEMENT_SOURCE')
    r=cue.generation_requirements
    if cue.source_strategy=='ORIGINAL_AI' and r is None:raise ValueError('MUSIC_GENERATION_REQUIREMENTS_REQUIRED')
    return {'cueRef':cue.cue_id,'dramaticFunction':cue.narrative_function,'cueArc':list(cue.energy_arc),
            'motifReferences':list(cue.motif_refs),'timbrePalette':cue.timbre_palette,'rhythmicFunction':cue.rhythmic_function,
            'instrumentationPolicy':plan.score_palette.timbre,'instrumentalVocalPolicy':r.vocal_policy if r else 'PROHIBITED',
            'dialogueWindows':list(cue.dialogue_windows),
            'nativeSfxPriority':{'native':cue.native_audio_priority,'sfx':cue.sfx_priority},
            'entryTrigger':cue.entry_trigger,'exitTrigger':cue.exit_trigger,
            'generationRequirements':dump_contract(r) if r else None,
            'referenceAudioPolicy':'Rights-cleared references only; TEMP is not releasable or automatic training authorization',
            'deliveryRequirements':'Lossless master; separable stems as required; cue revision and source lineage',
            'rightsRequirements':cue.rights_requirement,'doNot':list(cue.do_not),'providerImplemented':False,
            **({'yieldPolicy':dump_contract(cue.yield_policy)} if cue.yield_policy else {})}


def cue_production_eligible(cue: MusicCue) -> bool:
    if cue.source_strategy=='TEMP_REFERENCE':return False
    rights=cue.rights
    return (rights.allows_production() and rights.composition_rights in ('CLEARED','PUBLIC_DOMAIN')
            and rights.recording_rights=='CLEARED')


def qualify_music_requirements(cue: MusicCue, capability_evidence: Mapping[str,str]) -> dict[str,Any]:
    """Semantic future qualification only; UNKNOWN fails and no provider is called."""
    required={'instrumental_control','duration_control','structural_control','continuation','revision','motif_consistency',
              'reference_audio','lossless_export','forced_vocals_risk','commercial_rights','prompt_fidelity','cost_observability'}
    if cue.generation_requirements and cue.generation_requirements.stem_requirement=='REQUIRED':required.add('stems')
    unknown=sorted(k for k in required if capability_evidence.get(k)!='PASS')
    return {'status':'PRODUCTION_QUALIFICATION_BLOCKED' if unknown else 'CAPABILITY_EVIDENCE_COMPLETE',
            'missingOrFailed':unknown,'providerImplemented':False,'providerCalls':0,'productionAuthorized':False}


def observed_music_finding(*, key: str, start: float, end: float, observation: str,
                           consequence: str, evidence_ref: str) -> FilmFinding:
    """Finishing supplies real-media observation; use the existing FilmReview finding."""
    if not evidence_ref.strip():raise ValueError('MUSIC_OBSERVATION_EVIDENCE_REQUIRED')
    return FilmFinding(key=key,start=start,end=end,domain='SOUND',severity='MAJOR',
        observation=observation+' | evidence='+evidence_ref,consequence=consequence,
        repair_owner='music-direction',proposed_repair='Return music/performance conflict to Director; do not change Script or acting to fit score')


def validate_score_context(plan: FilmScorePlan, context: Mapping[str,Any], *,
                           foreign_contexts: Sequence[Mapping[str,Any]] = ()) -> dict[str,Any]:
    from drama_plugin.performance_coverage import validate_performance_context_isolation
    refs=[r for m in plan.motifs for r in m.context_refs]+[r for c in plan.music_cues for r in c.context_refs]+[r for d in plan.scene_music_decisions for r in d.context_refs]
    return validate_performance_context_isolation(context=context,refs=refs,
        text=str(dump_contract(plan)),foreign_contexts=foreign_contexts)
