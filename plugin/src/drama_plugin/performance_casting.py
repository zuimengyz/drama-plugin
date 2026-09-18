"""Pure stage handoff and conservative review gates. No generator or writer."""
from typing import Any, Sequence
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.performance_casting import RoleArchetypeProfile, CastingReview, CastingBudget, Stage


def profile_fingerprint(profile: RoleArchetypeProfile) -> str:
    data = dump_contract(profile)
    # Optional role extensions must not stale preserved, unextended profiles.
    if not profile.archetype_references:
        data.pop('archetypeReferences', None)
    if profile.archetypal_exaggeration is None:
        data.pop('archetypalExaggeration', None)
    if profile.excavation is None and profile.social_presence is None:
        # Previously retained v1 profiles remain readable, never spend-authorizing.
        data.pop('excavation', None)
        data.pop('socialPresence', None)
    return sha256_canonical(data)


def excavation_gate(profile: RoleArchetypeProfile) -> dict[str, Any]:
    excavation = profile.excavation
    if excavation is None:
        return {'status': 'BLOCKED', 'reasons': ['CHARACTER_EXCAVATION_MISSING']}
    data = dump_contract(excavation)
    fingerprint = sha256_canonical({k: data[k] for k in ('context', 'watchability', 'insights')})
    reasons: list[str] = [name for name, check in excavation.checks.items() if check.status != 'PASS']
    if any(check.reviewed_fingerprint != fingerprint for check in excavation.checks.values()):
        reasons.append('EXCAVATION_REVIEW_STALE')
    return {'status': 'BLOCKED' if reasons else 'PASS', 'reasons': reasons,
            'fingerprint': fingerprint, 'boundary': excavation.reviewer_boundary}


def eligible(profile: RoleArchetypeProfile, stage: Stage, reviews: Sequence[CastingReview]) -> list[str]:
    plan = next(s for s in profile.stage_plan if s.stage == stage)
    required = set(plan.criteria)
    if stage == 'SOCIAL':
        required.add('identity_preserved')
    if stage == 'PERFORMANCE':
        required |= {'state:' + s.key for s in profile.performance_states}
        required |= {'identity_preserved'}
    permitted = {'PASS', 'SHORTLIST'} if stage == 'FACE' else {'PASS'}
    seen: set[str] = set()
    result = []
    for review in reviews:
        review = CastingReview.model_validate(dump_contract(review))
        if review.stage != stage:
            continue
        if review.candidate_id in seen:
            raise ValueError('Ambiguous duplicate candidate review; retain versions outside active selection')
        seen.add(review.candidate_id)
        if review.profile_fingerprint != profile_fingerprint(profile) or review.conditions_fingerprint != sha256_canonical(plan.conditions):
            raise ValueError('Stale profile or test conditions')
        conditions = review.findings.get('conditions_preserved')
        if conditions is None or conditions.status != 'PASS':
            continue
        if stage == 'PERFORMANCE':
            states = {s.key for s in profile.performance_states}
            linked = {(m.media_id, m.content_hash) for m in review.media}
            state_refs = {(m.media_id, m.content_hash) for m in review.state_media.values()}
            if not states <= review.state_media.keys() or len(state_refs) < len(states) or not state_refs <= linked:
                continue
        if not required <= review.findings.keys():
            continue
        if all(review.findings[k].status in permitted for k in required):
            result.append(review.candidate_id)
    return result


def stage_brief(profile: RoleArchetypeProfile, stage: Stage, candidate_ids: Sequence[str],
                reviews: Sequence[CastingReview] = (), *, budget: CastingBudget | None = None,
                execution: str = 'DRY_RUN') -> dict[str, Any]:
    # Re-parse mutable contracts at boundary, just as existing freeze does.
    profile = RoleArchetypeProfile.model_validate(dump_contract(profile))
    if budget is not None:
        budget = CastingBudget.model_validate(dump_contract(budget))
    plans = list(profile.stage_plan)
    index = next(i for i, p in enumerate(plans) if p.stage == stage)
    plan = plans[index]
    if len(set(candidate_ids)) != len(candidate_ids) or not plan.minimum_candidates <= len(candidate_ids) <= plan.maximum_candidates:
        raise ValueError('STAGE_CANDIDATE_COUNT')
    # EXECUTE is intent, not a transport. MCP remains a legacy caller alias.
    if execution not in {'DRY_RUN', 'EXECUTE', 'MCP'}:
        raise ValueError('CASTING_EXECUTION_INTENT_REQUIRED')
    if execution != 'DRY_RUN' and (budget is None or budget.requested_reservation <= 0):
        raise ValueError('CURRENT_BUDGET_REQUIRED')
    if budget and budget.recorded_cost + budget.outstanding_reservations + budget.requested_reservation > budget.cap:
        raise ValueError('BUDGET_STOP')
    context_gate = excavation_gate(profile)
    if execution != 'DRY_RUN' and context_gate['status'] != 'PASS':
        raise ValueError('CHARACTER_EXCAVATION_BLOCKED:' + ','.join(context_gate['reasons']))
    refs: dict[str, Any] = {}
    if index:
        # Every earlier selected proof must support this identity; a later pass cannot erase failure.
        for prior in plans[:index]:
            accepted = eligible(profile, prior.stage, reviews)
            if not set(candidate_ids) <= set(accepted):
                raise ValueError('PRIOR_STAGE_NOT_PASSED')
        for cid in candidate_ids:
            previous = [r for r in reviews if r.candidate_id == cid and r.stage in {p.stage for p in plans[:index]}]
            refs[cid] = [dump_contract(m) for r in previous for m in r.media]
    return {'profile': dump_contract(profile), 'profileFingerprint': profile_fingerprint(profile),
            'stage': stage, 'candidateIds': list(candidate_ids), 'conditions': plan.conditions,
            'conditionsFingerprint': sha256_canonical(plan.conditions), 'identityReferences': refs,
            'requiredCriteria': sorted(set(plan.criteria) | {'conditions_preserved'} | ({'identity_preserved'} if stage == 'SOCIAL' else set()) | (
                {'identity_preserved', *('state:' + s.key for s in profile.performance_states)}
                if stage == 'PERFORMANCE' else set())), 'execution': execution,
            'status': 'PENDING_USER_REVIEW', 'formalPromotionAllowed': False,
            'excavationGate': context_gate,
            'castingDecisions': [dump_contract(i) for i in profile.excavation.insights
                if any(d.stage == stage for d in i.casting_implications)] if profile.excavation else [],
            'budget': dump_contract(budget) if budget else None,
            'boundary': 'Host verifies source/media bytes and user spend authorization; this artifact does not authenticate them.'}


def user_selection_gate(profile: RoleArchetypeProfile, reviews: Sequence[CastingReview]) -> dict[str, Any]:
    context_gate = excavation_gate(profile)
    if context_gate['status'] != 'PASS':
        return {'status': 'CASTING_INSUFFICIENT', 'finalists': [], 'userApprovedWinner': None,
                'formalPromotionAllowed': False, 'excavationGate': context_gate}
    accepted = [set(eligible(profile, p.stage, reviews)) for p in profile.stage_plan]
    finalists = sorted(set.intersection(*accepted))
    # Require actual identity lineage across proofs, not a reused candidate label alone.
    valid = []
    for cid in finalists:
        prior_media: set[tuple[str, str]] = set()
        coherent = True
        for plan in profile.stage_plan:
            r = next(r for r in reviews if r.candidate_id == cid and r.stage == plan.stage)
            refs = {(m.media_id, m.content_hash) for m in r.identity_references}
            if prior_media and not (refs & prior_media):
                coherent = False
            prior_media = {(m.media_id, m.content_hash) for m in r.media}
        if coherent:
            valid.append(cid)
    return {'status': 'USER_SELECTION_REQUIRED' if valid else 'CASTING_INSUFFICIENT',
            'finalists': valid, 'userApprovedWinner': None, 'formalPromotionAllowed': False,
            'productionFreezeAuthority': 'Existing ProductionDesignFreeze must still verify explicit user approval and approved Media.'}
