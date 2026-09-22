"""Pure P1R validators/consumers. Structural acceptance is never artistic approval.

Source-narrator and character-thought provenance are separate. Existing literary
explicitness grants stay authoritative; missing grants return an upstream request.
"""
from typing import Any, Iterable
from drama_plugin.contracts.creative_source import ScreenplayInput
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.narration import NarrationContext, NarrationPlan, FullDirectorScreenplay
from drama_plugin.creative_source import verify_screenplay_input


def _unique(items: Iterable[str], label: str) -> None:
    items = list(items)
    if len(items) != len(set(items)):
        raise ValueError('DUPLICATE_' + label)


def validate_context(context: NarrationContext) -> tuple[NarrationContext, ScreenplayInput]:
    c = NarrationContext.model_validate(dump_contract(context))
    compiled = verify_screenplay_input(dump_contract(c.package), c.screenplay['screenplayInput'])
    if c.character_dramaturgy.get('characterArc', {}).get('states') != dump_contract(c.package.character_arc)['states']:
        # P1 sidecars omit contract defaults; compare typed states below.
        from drama_plugin.contracts.creative_source import CharacterArc
        if CharacterArc.model_validate(c.character_dramaturgy.get('characterArc')) != c.package.character_arc:
            raise ValueError('CHARACTER_DRAMATURGY_UPSTREAM_MISMATCH')
    import hashlib
    text = c.screenplay['text']
    if hashlib.sha256(text.encode()).hexdigest() != c.screenplay['textSha256']:
        raise ValueError('SCREENPLAY_TEXT_HASH_MISMATCH')
    beats = c.screenplay['beats']
    _unique((b['id'] for b in beats), 'BEAT')
    expressions = {e.id: e for e in c.package.cinema.expressions}
    if {b['id'] for b in beats} != {e.destination_id for e in expressions.values()}:
        raise ValueError('SCREENPLAY_BEAT_COVERAGE_MISMATCH')
    states = {s.character_id + ':' + s.arc_stage for s in c.package.character_arc.states}
    for b in beats:
        e = expressions.get(b['cinemaExpressionId'])
        if not e or (e.destination_id, e.decision_id) != (b['id'], b['adaptationDecisionId']):
            raise ValueError('SCREENPLAY_BEAT_BINDING_MISMATCH')
        if text[b['textStart']:b['textEnd']] != b['text'] or hashlib.sha256(b['text'].encode()).hexdigest() != b['textSha256']:
            raise ValueError('SCREENPLAY_BEAT_TEXT_MISMATCH')
        if not b['characterStates'] or not set(b['characterStates']) <= states:
            raise ValueError('SCREENPLAY_CHARACTER_STATE_MISMATCH')
    return c, compiled


def narration_review_subject(plan: NarrationPlan, context: NarrationContext) -> str:
    return sha256_canonical({'plan': dump_contract(plan, exclude={'review'}), 'context': dump_contract(context)})


def compile_narration(plan: NarrationPlan, context: NarrationContext) -> dict[str, Any]:
    plan = NarrationPlan.model_validate(dump_contract(plan))
    c, compiled = validate_context(context)
    if plan.review.subject_hash != narration_review_subject(plan, c):
        raise ValueError('STALE_NARRATION_REVIEW')
    _unique((s.scene_id for s in plan.scenes), 'SCENE')
    _unique((q.cue_id for q in plan.cues), 'CUE')
    _unique((r.id for r in plan.upstream_change_requests), 'UPSTREAM_REQUEST')
    all_beats = [b for s in plan.scenes for b in s.beat_ids]
    _unique(all_beats, 'SCENE_BEAT')
    if all_beats != [b['id'] for b in c.screenplay['beats']]:
        raise ValueError('SCENE_BEAT_ORDER_OR_COVERAGE_MISMATCH')
    if (plan.bible.narration_mode == 'NONE') != (not plan.cues):
        raise ValueError('NONE_HAS_NO_CUES_OTHER_MODES_REQUIRE_CUES')
    units = {u.id: u for u in c.package.analysis.units}
    anchors = {a.id: a for a in c.package.anchors}
    decisions = {d.id: d for d in c.package.adaptation.decisions}
    expressions = c.package.cinema.expressions
    scenes = {s.scene_id: s for s in plan.scenes}
    requests = {r.id: r for r in plan.upstream_change_requests}
    rows, conflicts, used_requests = [], [], set()
    for q in plan.cues:
        if q.narration_type != plan.bible.narration_mode:
            raise ValueError('CUE_BIBLE_MODE_MISMATCH')
        if q.scene_id not in scenes or q.beat_id not in scenes[q.scene_id].beat_ids:
            raise ValueError('CUE_SCENE_BEAT_MISMATCH')
        if not set(q.source_unit_ids) <= units.keys() or not set(q.source_anchor_ids) <= anchors.keys():
            raise ValueError('UNKNOWN_NARRATION_SOURCE')
        source_units = [units[u] for u in q.source_unit_ids]
        supported_anchors = {a for u in source_units for a in u.anchor_ids}
        if not set(q.source_anchor_ids) <= supported_anchors:
            raise ValueError('CUE_ANCHOR_NOT_SUPPORTED_BY_UNIT')
        expected_refs = {'analysis:' + u for u in q.source_unit_ids}
        if set(q.source_map_refs) != expected_refs or not expected_refs <= {r.target for r in compiled.source_map}:
            raise ValueError('CUE_SOURCE_MAP_MISMATCH')
        if q.source_layer in {'SOURCE_NARRATOR_FUNCTION', 'ADAPTED_SOURCE_NARRATOR'}:
            if q.narration_type != 'AUTHORIAL_NARRATION' or any(u.kind != 'NARRATOR' or u.origin != 'SOURCE_FACT' for u in source_units):
                raise ValueError('SOURCE_NARRATOR_IS_NOT_CHARACTER_THOUGHT')
            if q.source_layer == 'SOURCE_NARRATOR_FUNCTION' and not any(q.text in anchors[a].quote for a in q.source_anchor_ids):
                raise ValueError('SOURCE_QUOTATION_MUST_MATCH_ANCHOR')
        elif q.source_layer == 'CHARACTER_THOUGHT_SOURCE':
            if q.narration_type not in {'CHARACTER_VOICE_OVER', 'INTERNAL_MONOLOGUE'} or any(u.kind != 'INTERNAL_STATE' or u.origin != 'SOURCE_FACT' for u in source_units):
                raise ValueError('CHARACTER_THOUGHT_IS_NOT_SOURCE_NARRATOR')
        else:
            # New authorial claims always need human conflict resolution, even if
            # a caller self-labels a philosophical slogan FUNCTION_ONLY.
            conflicts.append('INVENTED_NARRATION_REQUIRES_HUMAN_REVIEW:' + q.cue_id)
        if q.theme_explicitness_review.disposition == 'HUMAN_CONFLICT':
            conflicts.append('THEME_EXPLICITNESS_CONFLICT:' + q.cue_id)
        if q.theme_explicitness_review.disposition == 'SOURCE_SUPPORTED_EXCEPTION':
            support = q.theme_explicitness_review.source_explicit_support
            if not support or not set(support) <= set(q.source_anchor_ids):
                raise ValueError('EXPLICIT_THEME_SOURCE_SUPPORT_REQUIRED')
        d = decisions.get(q.adaptation_decision_id)
        if not d or not set(q.source_unit_ids) <= set(d.source_unit_ids):
            raise ValueError('NARRATION_ADAPTATION_SCOPE_MISMATCH')
        matching = [e for e in expressions if e.decision_id == d.id and e.destination_id == q.beat_id]
        if not matching:
            raise ValueError('NARRATION_ADAPTATION_DESTINATION_MISMATCH')
        grant = any('VOICE_OVER' in e.channels and e.explicitness_exception and
                    set(q.source_unit_ids) <= set(e.explicitness_exception.source_unit_ids) for e in matching)
        if not grant:
            request = requests.get(q.upstream_change_request_id) if q.upstream_change_request_id else None
            if not request or request.target_authority not in {'literary-adaptation', 'literature-to-cinema'}:
                raise ValueError('NARRATION_REQUIRES_UPSTREAM_CHANGE_REQUEST')
            if not set(request.source_evidence) <= anchors.keys():
                raise ValueError('UPSTREAM_REQUEST_SOURCE_MISMATCH')
            used_requests.add(request.id)
            conflicts.append('UPSTREAM_CHANGE_REQUIRED:' + request.id)
        elif q.upstream_change_request_id:
            raise ValueError('UNNEEDED_OR_UNRESOLVED_CHANGE_REQUEST')
        rows.append({'cueId': q.cue_id, 'sourceLayer': q.source_layer,
            'literaryFunction': q.literary_function, 'adaptationDecisionId': d.id,
            'sourceUnitIds': list(q.source_unit_ids), 'sourceAnchorIds': list(q.source_anchor_ids),
            'sourceMapRefs': list(q.source_map_refs), 'sourceRef': dump_contract(compiled.package_ref),
            'sceneId': q.scene_id, 'beatId': q.beat_id, 'origin': 'ADAPTATION_INVENTION'})
    if set(requests) != used_requests:
        raise ValueError('UNBOUND_UPSTREAM_CHANGE_REQUEST')
    for scene in plan.scenes:
        actual = [q.cue_id for q in plan.cues if q.scene_id == scene.scene_id]
        if list(scene.cue_ids) != actual or (scene.policy == 'SILENCE') != (not actual):
            raise ValueError('SCENE_NARRATION_POLICY_MISMATCH')
    if plan.review.status == 'HUMAN_CONFLICT':
        conflicts.append('SPECIALIST_REVIEW_CONFLICT')
    return {'status': 'HUMAN_CONFLICT' if any('CONFLICT' in x or 'HUMAN_REVIEW' in x for x in conflicts)
            else 'UPSTREAM_CHANGE_REQUIRED' if conflicts else 'CANDIDATE_READY',
        'reasons': list(dict.fromkeys(conflicts)), 'narrationPlanHash': sha256_canonical(plan),
        'sourceMap': rows, 'audioFutureHandoff': [{'cueId': q.cue_id, 'intent': dump_contract(q.performance_intent)} for q in plan.cues],
        'humanApproval': None, 'p2Authorized': False, 'artisticQualityJudged': False}


def director_review_subject(plan: FullDirectorScreenplay) -> str:
    return sha256_canonical(dump_contract(plan, exclude={'review'}))


def compile_director_screenplay(plan: FullDirectorScreenplay, narration: NarrationPlan, context: NarrationContext) -> dict[str, Any]:
    plan = FullDirectorScreenplay.model_validate(dump_contract(plan))
    result = compile_narration(narration, context)
    if result['status'] != 'CANDIDATE_READY':
        raise ValueError('DIRECTOR_UPSTREAM_NARRATION_UNRESOLVED')
    if (plan.narration_plan_hash != sha256_canonical(narration) or
        plan.screenplay_hash != sha256_canonical(context.screenplay) or
        plan.character_dramaturgy_hash != sha256_canonical(context.character_dramaturgy) or
        plan.review.subject_hash != director_review_subject(plan)):
        raise ValueError('STALE_DIRECTOR_BINDING_OR_REVIEW')
    if plan.review.status != 'REVIEWED_CANDIDATE':
        raise ValueError('DIRECTOR_REVIEW_CONFLICT')
    if [s.scene_id for s in plan.scenes] != [s.scene_id for s in narration.scenes]:
        raise ValueError('DIRECTOR_SCENE_COVERAGE_MISMATCH')
    states = {(s.character_id, s.arc_stage): s for s in context.package.character_arc.states}
    beats = {b['id']: b for b in context.screenplay['beats']}
    rows = []
    for s, policy in zip(plan.scenes, narration.scenes):
        if (s.beat_ids, s.narration_policy, s.narration_cue_ids) != (policy.beat_ids, policy.policy, policy.cue_ids):
            raise ValueError('DIRECTOR_NARRATION_BINDING_MISMATCH')
        wanted = {state for b in s.beat_ids for state in beats[b]['characterStates']}
        if {r.character_id+':'+r.arc_stage for r in s.character_states} != wanted:
            raise ValueError('DIRECTOR_CHARACTER_STATE_SCOPE_MISMATCH')
        if set(s.source_map_refs) != {b+':'+beats[b]['cinemaExpressionId'] for b in s.beat_ids}:
            raise ValueError('DIRECTOR_SOURCE_MAP_MISMATCH')
        for ref in s.character_states:
            if (ref.character_id, ref.arc_stage) not in states:
                raise ValueError('DIRECTOR_CANNOT_REWRITE_CHARACTER')
        for b in s.beat_ids:
            e = next(e for e in context.package.cinema.expressions if e.id == beats[b]['cinemaExpressionId'])
            d = next(d for d in context.package.adaptation.decisions if d.id == e.decision_id)
            rows.append({'sceneId': s.scene_id, 'beatId': b, 'cinemaExpressionId': e.id,
                'adaptationDecisionId': d.id, 'sourceUnitIds': list(d.source_unit_ids),
                'sourceAnchorIds': list(dict.fromkeys(a for u in context.package.analysis.units if u.id in d.source_unit_ids for a in u.anchor_ids))})
    return {'status': 'CANDIDATE_READY', 'plan': dump_contract(plan), 'sourceMap': rows,
        'narration': result, 'humanApproval': None, 'p2Authorized': False, 'artisticQualityJudged': False}
