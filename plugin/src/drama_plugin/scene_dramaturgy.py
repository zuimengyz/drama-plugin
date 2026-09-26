"""Deterministic Scene → DPD handoff and source-bound professional review.

Presence, order and identity are machine checks. Artistic findings remain named
reviewer attestations. This module has no IO, inference, repair or model calls.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.dpd import BeatDPD, DPDSnapshot
from drama_plugin.contracts.scene_dramaturgy import SceneDramaturgy, DramaturgyReview
from drama_plugin.dpd import compose_dpd

AXES = frozenset({'ACTION_RESPONSE_CHAIN', 'STRATEGY_CHANGE', 'INFORMATION_RELEASE',
                  'LISTENER_CAUSALITY', 'SILENCE_FUNCTION', 'ENTRY_EXIT_DELTA'})
GENERIC = frozenset({'respond', 'react', 'response', 'do something', '回应', '反应', '改变', '做出反应'})


def scene_body_hash(scene: Mapping[str, Any]) -> str:
    body = deepcopy(dict(scene))
    body['content'].pop('dramaturgy', None)
    return sha256_canonical(body)


def carrier_text(scene: Mapping[str, Any], ref: str) -> str:
    if ref.startswith('spoken:'):
        lines = [x for x in scene['content'].get('spokenContent', []) if x['id'] == ref[7:]]
        if len(lines) != 1:
            raise ValueError('UNRESOLVED:scene-development:DIALOGUE_CARRIER_ID')
        return str(lines[0]['text'])
    try:
        kind, start, end = ref.split(':')
        lo, hi = int(start), int(end)
        text = scene['content']['screenplayAction']
        if kind != 'action' or not 0 <= lo < hi <= len(text):
            raise ValueError()
        return str(text[lo:hi])
    except (KeyError, TypeError, ValueError):
        raise ValueError('UNRESOLVED:scene-development:SOURCE_CARRIER_LOCATOR') from None


def source_dramaturgy(scene: Mapping[str, Any]) -> SceneDramaturgy:
    raw = scene['content'].get('dramaturgy')
    if raw is None:
        raise ValueError('UNRESOLVED:scene-development:SCENE_DRAMATURGY_REQUIRED')
    facet = SceneDramaturgy.model_validate(raw)
    if facet.source_body_hash != scene_body_hash(scene):
        raise ValueError('STALE_SCENE_DRAMATURGY')
    refs = [c.ref for c in facet.carriers]
    if len(set(refs)) != len(refs):
        raise ValueError('DUPLICATE_SOURCE_CARRIER')
    order = {ref: i for i, ref in enumerate(refs)}
    carriers = {c.ref: c for c in facet.carriers}
    lines = scene['content'].get('spokenContent', [])
    if len({x['id'] for x in lines}) != len(lines):
        raise ValueError('DUPLICATE_DIALOGUE_TURN')
    # All turns are in the source-owned sequence; action selection is explicit.
    if [c.ref[7:] for c in facet.carriers if c.ref.startswith('spoken:')] != [x['id'] for x in lines]:
        raise ValueError('DIALOGUE_SEQUENCE_MISMATCH')
    actors = set(scene['content'].get('characters', []))
    last_end = -1
    for c in facet.carriers:
        text = carrier_text(scene, c.ref)
        if sha256(text.encode()).hexdigest() != c.text_hash:
            raise ValueError('SOURCE_CARRIER_TEXT_MISMATCH')
        if c.ref.startswith('action:'):
            _, start, end = c.ref.split(':')
            if int(start) < last_end:
                raise ValueError('SOURCE_TEMPORAL_ORDER_MISMATCH')
            last_end = int(end)
        else:
            line = next(x for x in lines if x['id'] == c.ref[7:])
            if (c.actor, c.target) != (line['speakerKey'], line.get('target')):
                raise ValueError('DIALOGUE_CARRIER_ACTOR_TARGET_MISMATCH')
        if c.actor is not None and c.actor not in actors:
            raise ValueError('UNBOUND_CARRIER_ACTOR')
        if c.role == 'ENVIRONMENT' or c.silence_function == 'ENVIRONMENTAL':
            if c.actor is not None or c.target is not None:
                raise ValueError('ENVIRONMENT_CANNOT_HAVE_ACTOR_PSYCHOLOGY')
        elif c.actor is None:
            raise ValueError('SOURCE_CARRIER_ACTOR_REQUIRED')
        if c.role == 'SILENCE' and c.silence_function is None:
            raise ValueError('SILENCE_FUNCTION_REQUIRED')
        if c.role in ('RESPONSE', 'REACTION') and c.cause_ref is None:
            raise ValueError('UNRESOLVED:scene-development:RESPONSE_CAUSE_REQUIRED')
        if c.cause_ref is not None and (c.cause_ref not in order or order[c.cause_ref] >= order[c.ref]):
            raise ValueError('TRIGGER_REACTION_ORDER_MISMATCH')
    edges: set[tuple[str, str]] = set()
    for edge in facet.interactions:
        pair = (edge.action_ref, edge.response_ref)
        if pair in edges or any(ref not in order for ref in pair):
            raise ValueError('DUPLICATE_OR_UNBOUND_INTERACTION')
        edges.add(pair)
        action, response = (carriers[ref] for ref in pair)
        if order[action.ref] >= order[response.ref] or response.cause_ref != action.ref:
            raise ValueError('ACTION_RESPONSE_ORDER_MISMATCH')
        if response.role not in ('RESPONSE', 'REACTION', 'SILENCE'):
            raise ValueError('STIMULUS_IS_NOT_ACTUAL_RESPONSE')
        if action.actor == response.actor or action.target != response.actor:
            raise ValueError('INTERACTION_LISTENER_MISMATCH')
        if edge.next_action_ref is not None:
            nxt = carriers.get(edge.next_action_ref)
            if (nxt is None or order[nxt.ref] <= order[response.ref]
                    or nxt.cause_ref != response.ref or nxt.actor != action.actor):
                raise ValueError('NEXT_ACTION_CAUSAL_BINDING_REQUIRED')
        elif edge.strategy_change:
            raise ValueError('STRATEGY_CHANGE_REQUIRES_NEXT_ACTION')
    if not set(facet.state_evidence) <= set(refs):
        raise ValueError('ENTRY_EXIT_EVIDENCE_UNBOUND')
    info_ids = [i.information_ref for i in facet.information]
    if len(set(info_ids)) != len(info_ids):
        raise ValueError('DUPLICATE_INFORMATION_REF')
    for info in facet.information:
        if any(ref is not None and ref not in order for ref in (info.not_before, info.needed_by)):
            raise ValueError('INFORMATION_WINDOW_UNBOUND')
        if info.needed_by and not info.needed_by_subjects:
            raise ValueError('INFORMATION_KNOWLEDGE_SUBJECT_REQUIRED')
        if not set(info.needed_by_subjects) <= actors | {'AUDIENCE'}:
            raise ValueError('INFORMATION_KNOWLEDGE_SUBJECT_UNKNOWN')
        for who, parts in info.prior_knowledge.items():
            if who not in actors | {'AUDIENCE'} or not set(parts) <= set(info.parts):
                raise ValueError('PRIOR_KNOWLEDGE_UNBOUND')
        for release in info.releases:
            if release.carrier_ref not in order or not set(release.parts) <= set(info.parts):
                raise ValueError('INFORMATION_RELEASE_UNBOUND')
            if not set(release.characters) <= actors:
                raise ValueError('INFORMATION_KNOWLEDGE_SUBJECT_UNKNOWN')
            if not release.audience and not release.characters:
                raise ValueError('INFORMATION_RELEASE_HAS_NO_RECIPIENT')
            if release.after_response_ref is not None:
                prior_response = carriers.get(release.after_response_ref)
                if prior_response is None or prior_response.role not in ('RESPONSE', 'REACTION', 'SILENCE'):
                    raise ValueError('INFORMATION_PRIOR_RESPONSE_UNBOUND')
                if order[prior_response.ref] >= order[release.carrier_ref]:
                    raise ValueError('INFORMATION_RESPONSE_ORDER_MISMATCH')
    return facet


def validate_carrier_order(scene: Mapping[str, Any], beat: BeatDPD) -> None:
    beat = BeatDPD.model_validate(dump_contract(beat))
    facet = source_dramaturgy(scene)
    witness = beat.playability
    if witness is None or not witness.action_carrier_refs or not witness.reaction_carrier_ref:
        raise ValueError('UNRESOLVED:dramatic-performance-direction:ORDERED_PLAYABILITY_REQUIRED')
    if witness.source_scene_hash != sha256_canonical(scene) or beat.scene_id != scene['id']:
        raise ValueError('STALE_SCREENPLAY_PLAYABILITY')
    carriers = {c.ref: c for c in facet.carriers}
    order = {c.ref: i for i, c in enumerate(facet.carriers)}
    refs = witness.action_carrier_refs
    if len(refs) != len(witness.playable_actions) or len(set(refs)) != len(refs):
        raise ValueError('PLAYABILITY_CARRIER_COUNT_MISMATCH')
    if any(ref not in carriers for ref in (*refs, witness.reaction_carrier_ref)):
        raise ValueError('PLAYABILITY_CARRIER_UNBOUND')
    if list(refs) != sorted(refs, key=order.__getitem__):
        raise ValueError('PLAYABILITY_TEMPORAL_ORDER_MISMATCH')
    for ref, action in zip((*refs, witness.reaction_carrier_ref), (*witness.playable_actions, witness.reaction)):
        c = carriers[ref]
        if (c.actor, c.target, carrier_text(scene, ref)) != (action.actor, action.target, action.behavior):
            raise ValueError('PLAYABILITY_SOURCE_IDENTITY_MISMATCH')
    reaction = carriers[witness.reaction_carrier_ref]
    # The source can identify one action as its own sustained aftermath; a trigger
    # may never be smuggled into the reaction slot.
    if reaction.role not in ('REACTION', 'RESPONSE', 'AFTERMATH', 'SILENCE'):
        raise ValueError('TRIGGER_IS_NOT_REACTION')
    if order[reaction.ref] < max(order[x] for x in refs):
        raise ValueError('REACTION_PRECEDES_ACTION')


def dramaturgy_subject(scene: Mapping[str, Any], dpds: Mapping[str, DPDSnapshot | BeatDPD]) -> str:
    return sha256_canonical({'scene': dict(scene), 'dpds': {k: sha256_canonical(v) for k, v in sorted(dpds.items())}})


def review_scene_dramaturgy(scene: Mapping[str, Any], dpds: Mapping[str, DPDSnapshot | BeatDPD],
                           review: DramaturgyReview | Mapping[str, Any]) -> dict[str, Any]:
    facet = source_dramaturgy(scene)
    review = DramaturgyReview.model_validate(dump_contract(review) if isinstance(review, DramaturgyReview) else review)
    subject = dramaturgy_subject(scene, dpds)
    if review.subject_hash != subject:
        raise ValueError('STALE_DRAMATURGY_REVIEW')
    carriers = {c.ref: c for c in facet.carriers}
    order = {c.ref: i for i, c in enumerate(facet.carriers)}
    findings = [dump_contract(f) for f in review.findings]

    def flag(axis: str, scope: str, code: str, evidence: tuple[str, ...], owner: str = 'scene-development') -> None:
        findings.append({'axis': axis, 'scope': scope, 'status': 'CONCERN', 'finding': code,
                         'reason': code, 'evidenceRefs': list(evidence), 'repairOwner': owner})

    if {f.axis for f in review.findings} != AXES:
        raise ValueError('DRAMATURGY_REVIEW_AXES_REQUIRED')
    scopes = {'SCENE', *carriers, *(i.information_ref for i in facet.information)}
    for finding in review.findings:
        if finding.scope not in scopes or not set(finding.evidence_refs) <= set(carriers):
            raise ValueError('DRAMATURGY_REVIEW_EVIDENCE_UNBOUND')
        if finding.reason.strip().lower().strip('.。') in {'pass', 'ok', 'reviewed', '通过', '已审阅', 'n/a'}:
            raise ValueError('SUBSTANTIVE_DRAMATURGY_REVIEW_REQUIRED')
        if finding.axis in ('INFORMATION_RELEASE', 'ENTRY_EXIT_DELTA') and finding.repair_owner != 'scene-development':
            raise ValueError('SCENE_DRAMATURGY_REPAIR_OWNER_REQUIRED')
    beats: dict[str, BeatDPD] = {}
    for dpd in dpds.values():
        if isinstance(dpd, DPDSnapshot):
            if compose_dpd(dpd.scene, dpd.beat, dpd.line) != dpd or dpd.scene.source_fingerprint != sha256_canonical(scene):
                raise ValueError('STALE_DRAMATURGY_DPD')
            beat = dpd.beat
        else:
            beat = dpd
        if beat.scene_id != scene['id']:
            raise ValueError('DRAMATURGY_DPD_SCENE_MISMATCH')
        if beat.beat_id in beats and beats[beat.beat_id] != beat:
            raise ValueError('CONFLICTING_BEAT_DPD')
        validate_carrier_order(scene, beat)
        beats[beat.beat_id] = beat
    edge_pairs = {(e.action_ref, e.response_ref) for e in facet.interactions}
    for beat in beats.values():
        for interpretation in beat.response_interpretations:
            if (interpretation.action_ref, interpretation.response_ref) not in edge_pairs:
                raise ValueError('DPD_INTERPRETATION_NOT_SOURCE_INTERACTION')
            if carriers[interpretation.action_ref].actor != beat.actor:
                raise ValueError('DPD_INTERPRETATION_ACTOR_MISMATCH')
    causal_coverage = []
    for edge in facet.interactions:
        action, response = carriers[edge.action_ref], carriers[edge.response_ref]
        speakers = [b for b in beats.values() if b.actor == action.actor and b.playability
                    and action.ref in b.playability.action_carrier_refs]
        listeners = [b for b in beats.values() if b.actor == response.actor and b.playability
                     and response.ref in (*b.playability.action_carrier_refs, b.playability.reaction_carrier_ref)]
        if not listeners:
            flag('LISTENER_CAUSALITY', response.ref, 'LISTENER_RESPONSE_DPD_REQUIRED', (action.ref, response.ref), 'dramatic-performance-direction')
        for listener in listeners:
            if not listener.direction.objective or not listener.direction.tactic:
                flag('LISTENER_CAUSALITY', response.ref, 'LISTENER_TASK_REQUIRED', (response.ref,), 'dramatic-performance-direction')
        interpretations = [(b, x) for b in speakers for x in b.response_interpretations
                           if (x.action_ref, x.response_ref) == (action.ref, response.ref)]
        if len(interpretations) != 1:
            flag('ACTION_RESPONSE_CHAIN', action.ref, 'EXPECTED_ACTUAL_RESPONSE_TRACE_REQUIRED', (action.ref, response.ref), 'dramatic-performance-direction')
            continue
        beat, intent = interpretations[0]
        nxt = beats.get(intent.next_beat_id or '')
        causal_coverage.append({'actionRef': action.ref, 'actualResponseRef': response.ref,
            'expectedResponse': intent.expected_response, 'interpretation': intent.interpretation,
            'previousTactic': beat.direction.tactic, 'transitionReason': intent.transition_reason,
            'nextActionRef': edge.next_action_ref, 'nextTactic': nxt.direction.tactic if nxt else None,
            'dpdRef': beat.beat_id, 'listenerDpdRefs': [b.beat_id for b in listeners]})
        if not beat.direction.objective or not beat.direction.tactic:
            flag('ACTION_RESPONSE_CHAIN', action.ref, 'ACTOR_TASK_REQUIRED', (action.ref,), 'dramatic-performance-direction')
        if intent.expected_response.strip().lower().strip('.。') in GENERIC:
            flag('ACTION_RESPONSE_CHAIN', action.ref, 'GENERIC_EXPECTED_RESPONSE', (action.ref,), 'dramatic-performance-direction')
        if edge.strategy_change:
            if (nxt is None or nxt.actor != beat.actor or not nxt.playability
                    or not nxt.direction.tactic or edge.next_action_ref not in nxt.playability.action_carrier_refs
                    or not intent.transition_reason or intent.transition_reason.strip().lower() in {'next', 'because', '下一步', '升级'}):
                flag('STRATEGY_CHANGE', action.ref, 'RESPONSE_TO_NEXT_TACTIC_REQUIRED', (action.ref, response.ref), 'dramatic-performance-direction')
    for c in facet.carriers:
        if c.important and c.role == 'ACTION' and c.target and not any(e.action_ref == c.ref for e in facet.interactions):
            # Existing reflexive target labels are identities, not inferred from
            # speech. A real character using such a key takes precedence.
            self_targets = {c.actor, *({'自己', 'SELF'} - set(scene['content'].get('characters', [])))}
            if c.actor is not None and c.target in self_targets:
                continuations = []
                for beat in beats.values():
                    witness = beat.playability
                    if (beat.actor != c.actor or not witness or c.ref not in witness.action_carrier_refs
                            or beat.direction.interaction_target != c.target
                            or not beat.direction.objective or not beat.direction.tactic):
                        continue
                    continuation = carriers[witness.reaction_carrier_ref or '']
                    if (order[continuation.ref] > order[c.ref] and continuation.actor == c.actor
                            and witness.reaction.actor == c.actor and continuation.target in self_targets
                            and continuation.cause_ref in (None, c.ref)
                            and continuation.role in ('AFTERMATH', 'REACTION', 'SILENCE')
                            and continuation.silence_function != 'ENVIRONMENTAL'
                            and any(f.axis == 'ACTION_RESPONSE_CHAIN' and f.status == 'PASS'
                                    and f.scope in ('SCENE', c.ref)
                                    and {c.ref, continuation.ref} <= set(f.evidence_refs) for f in review.findings)):
                        continuations.append(continuation.ref)
                if not continuations:
                    flag('ACTION_RESPONSE_CHAIN', c.ref, 'SELF_DIRECTED_CONTINUATION_REQUIRED', (c.ref,), 'dramatic-performance-direction')
            else:
                flag('ACTION_RESPONSE_CHAIN', c.ref, 'IMPORTANT_ACTION_RESPONSE_MISSING', (c.ref,))
        if c.important and c.role == 'SILENCE' and c.silence_function != 'ENVIRONMENTAL':
            if not any(e.response_ref == c.ref for e in facet.interactions) and not any(x.cause_ref == c.ref for x in facet.carriers):
                flag('SILENCE_FUNCTION', c.ref, 'SILENCE_CAUSAL_LINK_REQUIRED', (c.ref,))
            if not any(b.actor == c.actor and b.playability and c.ref in (*b.playability.action_carrier_refs, b.playability.reaction_carrier_ref) for b in beats.values()):
                flag('SILENCE_FUNCTION', c.ref, 'SILENCE_DPD_REQUIRED', (c.ref,), 'dramatic-performance-direction')
    information = []
    for info in facet.information:
        releases = sorted(info.releases, key=lambda x: order[x.carrier_ref])
        if not any(f.axis == 'INFORMATION_RELEASE' and f.scope == info.information_ref for f in review.findings):
            flag('INFORMATION_RELEASE', info.information_ref, 'IMPORTANT_INFORMATION_REVIEW_REQUIRED', facet.state_evidence)
        if releases and info.not_before and order[releases[0].carrier_ref] < order[info.not_before]:
            flag('INFORMATION_RELEASE', info.information_ref, 'DRAMATICALLY_PREMATURE', (releases[0].carrier_ref, info.not_before))
        if info.needed_by:
            for who in info.needed_by_subjects:
                known = set(info.prior_knowledge.get(who, ()))
                for release in releases:
                    if order[release.carrier_ref] < order[info.needed_by] and (who in release.characters or who == 'AUDIENCE' and release.audience):
                        known.update(release.parts)
                if known != set(info.parts):
                    flag('INFORMATION_RELEASE', info.information_ref, 'DRAMATICALLY_LATE', (info.needed_by,))
        information.append({'informationRef': info.information_ref, 'firstRelease': releases[0].carrier_ref if releases else None,
                            'firstReleasePosition': order[releases[0].carrier_ref] if releases else None,
                            'firstReleaseParts': list(releases[0].parts) if releases else [],
                            'totalParts': len(info.parts), 'releases': [dump_contract(x) for x in releases],
                            'directStatementReason': info.direct_statement_reason})
    if facet.entry_state == facet.exit_state and not facet.suspension_reason:
        flag('ENTRY_EXIT_DELTA', 'SCENE', 'ENTRY_EXIT_CHANGE_OR_SUSPENSION_REQUIRED', facet.state_evidence)
    status = 'UNRESOLVED' if any(f['status'] == 'UNRESOLVED' for f in findings) else 'CONCERN' if any(f['status'] == 'CONCERN' for f in findings) else 'PASS'
    receipt = {'sourceHash': sha256_canonical(scene), 'subjectHash': subject,
               'reviewHash': sha256_canonical(review), 'status': status,
               'findings': findings, 'informationCoverage': information, 'causalCoverage': causal_coverage,
               'productionAuthorized': False}
    return {**receipt, 'fingerprint': sha256_canonical(receipt)}
