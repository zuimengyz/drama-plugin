"""Pure preproduction gates. Professional judgments are supplied with evidence.

These checks prove completeness/consistency, not aesthetic or historical truth.
No IO, provider dispatch, formal writes, automatic repairs or approval promotion.
"""
from __future__ import annotations
from typing import Any, Mapping
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.preproduction import (
    ScreenplayReadinessReview, CostumeState, DirectorDepartmentPacket,
    FilmProductionDesign, SceneProductionDesignPacket, LightingScript,
    CostumeBible, PropDesign, StylizationReview, DepartmentConflict)
from drama_plugin.contracts.dramatic_editorial import EditorialRhythmPlan
from drama_plugin.contracts.sequence import SourcePin

GATE_REGISTRY = (
    ('G0', 'formal source', 'source owners'),
    ('G1', 'screenplay readiness', 'cinematic-screenplay-incubation'),
    ('G2', 'director preliminary intent', 'director'),
    ('G3', 'route design', 'production-design'),
    ('G4', 'film production design', 'production-design'),
    ('G5', 'scene visual development', 'production-design'),
    ('G6', 'cinematography lighting', 'cinematic-direction'),
    ('G7', 'shot transition', 'shot-design'),
    ('G8', 'production book self review', 'director'),
    ('G9', 'user directorial review', 'user'),
    ('G10', 'route-specific character/casting', 'performance-casting'),
    ('G11', 'route-specific visual development', 'production-design'),
    ('G12', 'route-specific identity/art approval', 'user'),
    ('G13', 'production design freeze', 'production-design'),
    ('G14', 'current model qualification', 'video-model-selection'),
    ('G15', 'production preflight', 'shot-production'),
    ('G16', 'user production authorization', 'user'))


def readiness(review: ScreenplayReadinessReview, current: Mapping[str, str]) -> dict[str, Any]:
    review = ScreenplayReadinessReview.model_validate(dump_contract(review))
    stale = [p.key for p in review.source_pins if current.get(p.key) != p.fingerprint]
    if stale:
        return {'status': 'STALE_SOURCE', 'stale': stale, 'directionAllowed': False}
    blockers = [f.dimension for f in review.findings if f.verdict in {'MAJOR', 'UNKNOWN'}]
    # A human carrier need not be romance, speech or a second protagonist.
    if not review.human_stakes_carrier:
        blockers.append('human_stakes_carrier')
    if not review.emotional_counterline:
        blockers.append('emotional_counterline')
    if review.repeated_scene_pattern and not review.pattern_dramatic_progression:
        blockers.append('repeated_scene_pattern')
    blockers.extend('affordance:' + a.opportunity for a in review.affordances
                    if a.significant and a.decision == 'UNRESOLVED')
    blockers.extend(f.dimension for f in review.findings if f.verdict == 'NA' and f.dimension in
                    {'historical_causality', 'narrative_spine', 'protagonist_decision_arc', 'human_stakes', 'audience_knowledge'})
    notes = [f.dimension for f in review.findings if f.verdict == 'NOTE']
    status = ('DIRECTOR_REQUESTS_SCRIPT_REVIEW' if blockers else
              'READY_WITH_NOTES' if notes else 'READY_FOR_DIRECTION')
    return {'status': status, 'blockers': blockers, 'notes': notes,
            'directionAllowed': not blockers,
            'repairOwner': 'cinematic-screenplay-incubation' if blockers else None,
            'formalWriteAuthorized': False, 'productionAuthorized': False}


def stylization(review: StylizationReview) -> dict[str, Any]:
    review = StylizationReview.model_validate(dump_contract(review))
    return {'status': 'REVISE' if review.violations else 'DESIGN_POLICY_CONSISTENT',
            'violations': list(review.violations), 'artisticApproval': 'NOT_APPROVED',
            'lookdev': 'NOT_EXECUTED', 'route': review.route}


def costume_continuity(previous: CostumeState, current: CostumeState,
                       previous_ref: SourcePin) -> tuple[str, ...]:
    errors: list[str] = []
    if previous_ref.fingerprint != sha256_canonical(previous) or current.previous_state_ref != previous_ref:
        errors.append('STALE_COSTUME_STATE')
    if previous.character_identity != current.character_identity or previous.bible_ref != current.bible_ref:
        errors.append('COSTUME_IDENTITY_DRIFT')
    fields = ('costume', 'armor', 'equipment', 'dirt', 'dust', 'water', 'sweat', 'damage', 'missing_equipment', 'blood')
    errors.extend('UNEXPLAINED_COSTUME_CHANGE:' + f for f in fields
                  if getattr(previous, f) != getattr(current, f) and not current.change_causes.get(f))
    if previous.continuity_out != current.continuity_in:
        errors.append('COSTUME_HANDOFF_MISMATCH')
    return tuple(errors)


def transition_completeness(plan: EditorialRhythmPlan) -> tuple[str, ...]:
    if len(plan.coverage) == 1:
        return () if plan.transition_omission_reason else ('SINGLE_VIEW_NEEDS_TRANSITION_REASON',)
    required = set(zip([s.key for s in plan.coverage], [s.key for s in plan.coverage][1:]))
    present = {(t.from_shot, t.to_shot) for t in plan.transitions}
    return tuple('MISSING_TRANSITION:' + a + '->' + b for a,b in sorted(required-present))


def gate_progress(records: Mapping[str, str], target: str) -> dict[str, Any]:
    """Read explicit host-authenticated statuses; never manufacture a passed gate."""
    names = [g[0] for g in GATE_REGISTRY]
    if target not in names:
        raise ValueError('Unknown preproduction gate')
    preceding = names[:names.index(target)]
    missing = [g for g in preceding if records.get(g) not in {'PASS', 'PASS_WITH_NOTES'}]
    return {'target': target, 'allowed': not missing, 'missing': missing,
            'automaticPromotion': False, 'productionAuthorized': False}


def department_integration(packet: DirectorDepartmentPacket, review: ScreenplayReadinessReview,
                           current: Mapping[str, str], artifacts: Mapping[str, dict[str, Any]]) -> dict[str, Any]:
    """Resolve hash-addressed originals; packet summaries cannot satisfy completeness."""
    packet = DirectorDepartmentPacket.model_validate(dump_contract(packet))
    refs = (*packet.source_pins, packet.route_ref, packet.intent_ref, packet.readiness_ref,
            *(e.artifact_ref for e in packet.entries))
    stale = [p.key for p in refs if current.get(p.key) != p.fingerprint]
    if stale:
        return {'status': 'STALE_SOURCE', 'missing': stale, 'productionAuthorized': False}
    if (packet.readiness_ref.fingerprint != sha256_canonical(review) or
        review.scope_id != packet.scope_id or review.source_pins != packet.source_pins):
        raise ValueError('Readiness does not bind this exact Director scope')
    upstream = readiness(review, current)
    if not upstream['directionAllowed']:
        return upstream
    missing: list[str] = []
    conflicts = [dump_contract(c) for c in packet.conflicts if c.severity == 'MAJOR' and not c.resolved_by]

    def resolve(ref: SourcePin) -> dict[str, Any]:
        value = artifacts.get(ref.key)
        if value is None or sha256_canonical(value) != ref.fingerprint or current.get(ref.key) != ref.fingerprint:
            raise ValueError('Missing or stale department original: ' + ref.key)
        return value

    def conflict(code: str, a: SourcePin, b: SourcePin, evidence: str, owner: str) -> None:
        conflicts.append(dump_contract(DepartmentConflict.model_validate(dict(code=code,
            subject_refs=(a,b), evidence=evidence, repair_owner=owner))))

    entries = {(e.department,e.scope_id):e for e in packet.entries}
    required = {('film_design',packet.scope_id)} | {(d,s) for s in packet.scene_ids for d in
        ('scene_design','costume','lighting','performance','coverage','sound')}
    missing.extend(d + ':' + s for d,s in sorted(required-set(entries)))
    film_entry = entries.get(('film_design',packet.scope_id))
    film = FilmProductionDesign.model_validate(resolve(film_entry.artifact_ref)) if film_entry else None
    if film:
        if film.scope_id != packet.scope_id or film.source_pins != packet.source_pins or film.intent_ref != packet.intent_ref:
            raise ValueError('Film design source/intent mismatch')
        from drama_plugin.contracts.visual_route import RouteContext
        from drama_plugin.contracts.cinematic import VisualBible
        from drama_plugin.contracts.production_design import CharacterVisualSpec
        route_data = RouteContext.model_validate(resolve(packet.route_ref))
        if (route_data.sequence.visual_route or route_data.project.visual_route) != film.route or route_data.style.visual_route != film.route:
            raise ValueError('Film design route mismatch')
        VisualBible.model_validate(resolve(film.visual_bible_ref))
        if film.stylization.violations:
            missing.append('STYLIZATION_REVIEW_FAILED')
        if {c.scene_id for c in film.color_script} != set(packet.scene_ids):
            missing.append('COLOR_SCRIPT_INCOMPLETE')
        for ref in film.costume_bible_refs:
            cb = CostumeBible.model_validate(resolve(ref))
            CharacterVisualSpec.model_validate(resolve(cb.visual_spec_ref))
        for ref in film.prop_design_refs:
            PropDesign.model_validate(resolve(ref))
    # Optional design facets preserve the old pipeline; once opted in, every
    # scene resolves the same film-owned place original instead of a local copy.
    location_by_id = {}
    location_uses: dict[str, set[str]] = {}
    design_notes: list[dict[str, Any]] = []
    characters_by_id = {}
    if film and film.location_design_refs is not None:
        from drama_plugin.contracts.location_design import LocationDesign
        for location_ref in film.location_design_refs:
            location = LocationDesign.model_validate(resolve(location_ref.artifact_ref))
            if location.id != location_ref.location_id or not set(location.scene_refs) <= set(packet.scene_ids):
                raise ValueError('Film location identity/scene scope mismatch')
            location_by_id[location.id] = location
            location_uses[location.id] = set()
        for location in location_by_id.values():
            parent = location.parent_location_id
            seen = {location.id}
            while parent is not None:
                if parent not in location_by_id or parent in seen:
                    raise ValueError('Missing or cyclic parent location')
                seen.add(parent)
                parent = location_by_id[parent].parent_location_id
    if film and film.character_visual_refs is not None:
        from drama_plugin.contracts.character_evidence import CharacterCoverageReview
        from drama_plugin.production_design import review_character_coverage
        characters = tuple(CharacterVisualSpec.model_validate(resolve(ref)) for ref in film.character_visual_refs)
        if film.character_coverage_ref is None:
            raise ValueError('Character evidence inventory requires a coverage review reference')
        character_review = CharacterCoverageReview.model_validate(resolve(film.character_coverage_ref))
        if set(character_review.scene_refs) != set(packet.scene_ids):
            raise ValueError('Character coverage review scene scope mismatch')
        character_result = review_character_coverage(character_review, characters)
        missing.extend(character_result['missing'])
        design_notes.extend(character_result['notes'])
        characters_by_id = {c.character_identity: c for c in characters}
    coverage_by_scene: dict[str, EditorialRhythmPlan] = {}
    for sid in packet.scene_ids:
        design_entry = entries.get(('scene_design',sid)); light_entry = entries.get(('lighting',sid))
        scene = SceneProductionDesignPacket.model_validate(resolve(design_entry.artifact_ref)) if design_entry else None
        light = LightingScript.model_validate(resolve(light_entry.artifact_ref)) if light_entry else None
        if scene and film and film_entry:
            if scene.scene_id != sid or scene.film_design_ref != film_entry.artifact_ref:
                raise ValueError('Scene design film binding mismatch')
            if not all(p in packet.source_pins for p in scene.source_pins):
                raise ValueError('Scene design source mismatch')
            if film.location_design_refs is not None:
                from drama_plugin.production_design import resolve_location_design
                if scene.environment_refs is None:
                    missing.append('SCENE_ENVIRONMENT_REFERENCE_REQUIRED:' + sid)
                else:
                    allowed = {r.location_id: r for r in film.location_design_refs}
                    for binding in scene.environment_refs:
                        environment_ref = binding.location_ref
                        if allowed.get(environment_ref.location_id) != environment_ref:
                            raise ValueError('Scene environment differs from film location reference')
                        resolve_location_design(binding, scene_id=sid, current=current, artifacts=artifacts)
                        location_uses[environment_ref.location_id].add(sid)
            elif scene.environment_refs is not None:
                raise ValueError('Scene environment requires film-owned location references')
            if film.character_visual_refs is not None:
                for identity in scene.character_start_end:
                    character = characters_by_id.get(identity)
                    if character is None or character.evidence is None or sid not in character.evidence.scene_refs:
                        missing.append('CHARACTER_SCENE_EVIDENCE_REQUIRED:' + identity + ':' + sid)
            color = next((c for c in film.color_script if c.scene_id == sid), None)
            if color != scene.color_key:
                conflict('COLOR_INTENT_CONFLICT',film_entry.artifact_ref,design_entry.artifact_ref, # type: ignore[union-attr]
                         'Scene color departs from film color script','production-design')
        if light and scene and design_entry and light_entry:
            if light.scene_id != sid or light.scene_design_ref != design_entry.artifact_ref or light.source_pins != scene.source_pins:
                raise ValueError('Lighting scene binding mismatch')
            if not set(light.motivated_sources) <= set(scene.practical_sources):
                conflict('UNMOTIVATED_LIGHT',design_entry.artifact_ref,light_entry.artifact_ref,
                         'Lighting names a source absent from scene design','cinematic-direction')
        costume_entry = entries.get(('costume',sid))
        if costume_entry:
            state_data = resolve(costume_entry.artifact_ref)
            states = [CostumeState.model_validate(x) for x in state_data['states']]
            if not states or len({x.character_identity for x in states}) != len(states):
                raise ValueError('Empty/duplicate costume state group')
            for state in states:
                if state.scene_or_shot_id != sid:
                    raise ValueError('Costume scene mismatch')
                CostumeBible.model_validate(resolve(state.bible_ref))
                if state.previous_state_ref:
                    previous = CostumeState.model_validate(resolve(state.previous_state_ref))
                    for err in costume_continuity(previous,state,state.previous_state_ref):
                        conflict(err,state.previous_state_ref,costume_entry.artifact_ref,
                                 'Costume state loses its source handoff or change cause','production-design')
            if scene:
                for ref in scene.costume_state_refs:
                    if CostumeState.model_validate(resolve(ref)) not in states:
                        raise ValueError('Scene costume ref outside current states')
        coverage_entry = entries.get(('coverage',sid))
        if coverage_entry:
            plan = EditorialRhythmPlan.model_validate(resolve(coverage_entry.artifact_ref))
            if sid not in plan.scene_ids or plan.source_fingerprint not in {p.fingerprint for p in packet.source_pins}:
                raise ValueError('Coverage source mismatch')
            missing.extend(transition_completeness(plan))
            coverage_by_scene[sid] = plan
        # Existing DPD and source sound owners are referenced, not copied as Director psychology.
        performance_entry = entries.get(('performance',sid))
        if performance_entry:
            from drama_plugin.contracts.dpd import SceneDPD
            dpd = SceneDPD.model_validate(resolve(performance_entry.artifact_ref))
            if dpd.scene_id != sid or dpd.source_fingerprint not in {p.fingerprint for p in packet.source_pins}:
                raise ValueError('DPD source mismatch')
        sound_entry = entries.get(('sound',sid))
        if sound_entry:
            from drama_plugin.contracts.cinematic import SourceSoundIntent
            SourceSoundIntent.model_validate(resolve(sound_entry.artifact_ref))
    for identity, location in location_by_id.items():
        if location_uses[identity] != set(location.scene_refs):
            missing.append('LOCATION_SCENE_USAGE_MISMATCH:' + identity)
    sequence_edges: set[tuple[str, str]] = set()
    for ref in packet.sequence_transition_refs:
        sequence_plan = EditorialRhythmPlan.model_validate(resolve(ref))
        if not set(sequence_plan.scene_ids) <= set(packet.scene_ids) or sequence_plan.source_fingerprint not in {p.fingerprint for p in packet.source_pins}:
            raise ValueError('Sequence transition source mismatch')
        sequence_edges.update((t.from_shot,t.to_shot) for t in sequence_plan.transitions)
    for left,right in zip(packet.scene_ids,packet.scene_ids[1:]):
        if left in coverage_by_scene and right in coverage_by_scene:
            edge = (coverage_by_scene[left].coverage[-1].key,coverage_by_scene[right].coverage[0].key)
            if edge not in sequence_edges:
                missing.append('MISSING_SCENE_TRANSITION:' + left + '->' + right)
    # Resolved conflicts need fresh replacement evidence, not a boolean erasure.
    for c in packet.conflicts:
        if c.resolved_by:
            resolution = resolve(c.resolved_by)
            if resolution.get('verdict') != 'RESOLVED' or resolution.get('subjectRefs') != [dump_contract(p) for p in c.subject_refs]:
                missing.append('CONFLICT_RESOLUTION_NOT_BOUND:' + c.code)
    if not packet.self_review_ref:
        missing.append('DIRECTOR_SELF_REVIEW')
    else:
        evidence = resolve(packet.self_review_ref)
        expected = [(e.artifact_ref.key,e.artifact_ref.fingerprint) for e in packet.entries]
        expected.extend((p.key,p.fingerprint) for p in packet.sequence_transition_refs)
        if (evidence.get('subjectKind') != 'DESIGN_ONLY' or evidence.get('verdict') != 'PASS'
            or evidence.get('reviewedArtifacts') != [list(x) for x in expected]
            or not all(evidence.get('interfaceReviews', {}).get(k) for k in
                       ('costume_light', 'layout_blocking', 'direction_axis', 'color_hierarchy'))):
            missing.append('DIRECTOR_SELF_REVIEW_INCOMPLETE')
    return {'status': 'DEPARTMENT_CONFLICT' if conflicts else
            'DIRECTOR_PRODUCTION_BOOK_NOT_READY' if missing else 'DEPARTMENT_REVIEW_READY',
            'missing': missing, 'conflicts': conflicts, 'userApproved': False,
            'productionAuthorized': False, 'productionDesignFreeze': 'NOT_REACHED',
            **({'notes': design_notes} if design_notes else {})}


def complete_production_book(packet: DirectorDepartmentPacket, review: ScreenplayReadinessReview,
                             current: Mapping[str,str], artifacts: Mapping[str,dict[str,Any]], *,
                             performance: Mapping[str,Any] | None = None,
                             score_plan: Any = None) -> dict[str,Any]:
    """Unique full-book completion entry; R0 department readiness is insufficient.

    Performance evidence is recomputed from an ephemeral Host canonical witness.
    A JSON status, label or proposal manifest cannot replace formal evidence.
    """
    departments=department_integration(packet,review,current,artifacts)
    missing: list[str]=[]
    from drama_plugin.director_runtime import review_runtime
    try:
        review_runtime(packet.expected_runtime, scene_ids=packet.scene_ids, current=current)
    except ValueError as exc:
        missing.append(str(exc))
    if departments['status']!='DEPARTMENT_REVIEW_READY':missing.append('R0_DEPARTMENT_INTEGRATION')
    if performance is None:
        return {'status':'DIRECTOR_PRODUCTION_BOOK_NOT_READY','missing':missing+['FULL_FORMAL_PERFORMANCE_REQUIRED'],'productionAuthorized':False}
    try:
        from drama_plugin.hosts.formal_performance import FormalSourceWitness
        from drama_plugin.performance_coverage import full_performance_coverage_gate
        from drama_plugin.performance_direction import validate_projection
        from drama_plugin.contracts.performance_direction import DirectorPerformanceIntent, PerformanceProjection
        from drama_plugin.contracts.dpd import DPDSnapshot
        from drama_plugin.contracts.visual_route import RouteContext
        witness=performance.get('formal_source')
        if not isinstance(witness,FormalSourceWitness):raise ValueError('TRUSTED_FORMAL_READER_REQUIRED')
        if packet.scope_id != witness.tree['work'][0]['id']:raise ValueError('FULL_BOOK_WORK_SCOPE_MISMATCH')
        if {p.key:p.fingerprint for p in packet.source_pins}!=witness.pins:
            raise ValueError('FULL_BOOK_FORMAL_SOURCE_MISMATCH')
        if set(packet.scene_ids)!={s['id'] for s in witness.tree['scenes']}:
            raise ValueError('FULL_BOOK_SCENE_INVENTORY_MISMATCH')
        coverage=full_performance_coverage_gate(performance['inventory'],performance['directions'],
            current_source_hash=witness.fingerprint,contexts=performance['contexts'],dpds=performance['dpds'],
            formal_source=witness,scene_dpds=performance['scene_dpds'])
        if coverage['status']!='FULL_PERFORMANCE_COVERAGE_READY':raise ValueError('FULL_PERFORMANCE_COVERAGE_INCOMPLETE')
        intents={k:DirectorPerformanceIntent.model_validate(v) for k,v in performance['intents'].items()}
        if set(intents)!=set(packet.scene_ids):raise ValueError('DIRECTOR_PERFORMANCE_INTENT_INCOMPLETE')
        route=RouteContext.model_validate(artifacts[packet.route_ref.key])
        route_name=route.sequence.visual_route or route.project.visual_route
        expected=witness.obligations()['spoken']
        if set(performance['projections'])!=set(expected):raise ValueError('FULL_VISUAL_VOICE_PROJECTION_REQUIRED')
        for ref,item in expected.items():
            d=performance['directions'][ref];dpd=performance['dpds'][d['objective_ref']]
            if not isinstance(dpd,DPDSnapshot):raise ValueError('FORMAL_LINE_DPD_REQUIRED')
            intent=intents[item['scene']]
            if intent.review_basis!='SOURCE_BOUND_DESIGN':raise ValueError('PROPOSAL_DPD_NOT_FORMAL')
            if any(current.get(k)!=v for k,v in intent.source_fingerprints.items()):raise ValueError('STALE_PERFORMANCE_INTENT')
            for channel in ('VISUAL','VOICE'):
                projection=PerformanceProjection.model_validate(performance['projections'][ref][channel])
                validate_projection(intent,dpd,projection,current,channel)
                if channel=='VISUAL' and projection.route!=route_name:raise ValueError('FULL_BOOK_ROUTE_MISMATCH')
        # Every action and Shot is already covered by source enumeration. Expanded
        # dual-channel briefs do not exempt ordinary silent/interaction fragments.
        from drama_plugin.contracts.film_score import FilmScorePlan
        from drama_plugin.music_direction import review_score_plan
        if score_plan is None:raise ValueError('EXPLICIT_REVIEWED_FILM_SCORE_PLAN_REQUIRED')
        score=FilmScorePlan.model_validate(score_plan)
        if (score.source_kind!='FORMAL' or score.scope_id!=packet.scope_id or score.source_pins!=packet.source_pins
                or score.film_intent_ref!=packet.intent_ref or score.review_status!='DESIGN_REVIEWED'):
            raise ValueError('FULL_BOOK_MUSIC_SOURCE_REVIEW_MISMATCH')
        excluded=[s['id']+':spoken:'+line['id'] for s in witness.tree['scenes'] for line in s['content'].get('spokenContent',[])
                  if line.get('vocalDelivery',{}).get('mode')=='DECLAMED_VERSE']
        music=review_score_plan(score,current=current,expected_scene_ids=packet.scene_ids,performance_intents=intents,
                               excluded_performance_refs=excluded)
        if music['status']!='SCORE_DESIGN_REVIEW_READY':raise ValueError('MUSIC_PERFORMANCE_CONFLICT')
        reviewed={'score_plan':dump_contract(score),'inventory':performance['inventory'],'directions':performance['directions'],
                  'scene_dpds':{k:dump_contract(v) for k,v in performance['scene_dpds'].items()},'dpds':{k:dump_contract(v) for k,v in performance['dpds'].items()},
                  'intents':{k:dump_contract(v) for k,v in intents.items()},'projections':{k:{channel:dump_contract(PerformanceProjection.model_validate(v)) for channel,v in pair.items()} for k,pair in performance['projections'].items()}}
        self_review=performance.get('self_review',{})
        if (self_review.get('verdict')!='PASS' or self_review.get('reviewedFingerprint')!=sha256_canonical(reviewed)
                or self_review.get('sourcePins')!=witness.pins or self_review.get('routeRef')!=dump_contract(packet.route_ref)):
            raise ValueError('FULL_BOOK_SELF_REVIEW_REQUIRED')
    except (ValueError,KeyError,TypeError) as exc:
        missing.append(str(exc))
    return {'status':'DIRECTOR_PRODUCTION_BOOK_NOT_READY' if missing else 'DIRECTOR_PRODUCTION_BOOK_READY_FOR_USER_REVIEW',
            'missing':missing,'userApproved':False,'productionAuthorized':False,'productionDesignFreeze':'NOT_REACHED',
            **({'notes': departments['notes']} if departments.get('notes') else {})}
