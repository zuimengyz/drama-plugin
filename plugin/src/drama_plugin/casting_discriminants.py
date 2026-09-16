"""Compile authored discriminants without inventing face features from psychology."""
from typing import Any, Sequence
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.performance_casting import RoleArchetypeProfile, CastingReview
from drama_plugin.contracts.casting_discriminants import VisualCastingPlan, ProofStage
from drama_plugin.contracts.visual_route import RouteCastingContext
from drama_plugin.performance_casting import profile_fingerprint, excavation_gate, user_selection_gate


def _pointer(data: Any, pointer: str) -> Any:
    if not pointer.startswith('/'):
        raise ValueError('Basis must be a JSON pointer into the source profile')
    try:
        for key in pointer[1:].split('/'):
            key = key.replace('~1', '/').replace('~0', '~')
            data = data[int(key)] if isinstance(data, list) else data[key]
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise ValueError('Unresolved casting basis: ' + pointer) from exc
    if data is None or data == '' or data == []:
        raise ValueError('Empty casting basis')
    return data


def validate_visual_plan(profile: RoleArchetypeProfile, plan: VisualCastingPlan) -> dict[str, Any]:
    profile = RoleArchetypeProfile.model_validate(dump_contract(profile))
    plan = VisualCastingPlan.model_validate(dump_contract(plan))
    if plan.profile_fingerprint != profile_fingerprint(profile):
        raise ValueError('STALE_VISUAL_PLAN')
    if excavation_gate(profile)['status'] != 'PASS':
        raise ValueError('CHARACTER_EXCAVATION_BLOCKED')
    source = dump_contract(profile)
    for group, pointers in plan.intent.basis.items():
        for pointer in pointers:
            value = _pointer(source, pointer)
            expected = {'excavation': '/excavation', 'identity_era_social': '/excavation/context',
                        'counter_stereotype': '/excavation/insights', 'role_obligations': '/sceneObligations'}[group]
            if not (pointer == expected or pointer.startswith(expected + '/')):
                raise ValueError('Interpretation basis points to the wrong responsibility')
            if group == 'counter_stereotype' and (not isinstance(value, dict) or value.get('dimension') != 'COUNTER_STEREOTYPE'):
                raise ValueError('Counter-stereotype basis must resolve to that insight')
    if set(plan.proof_set.required_stages) != {s.stage for s in profile.stage_plan}:
        raise ValueError('Proof set cannot silently waive the role stage plan')
    story_keys = {d.key for d in plan.discriminants if d.responsibility in {'STORY_DEPENDENT', 'STORY_ONLY'}}
    if any(story_keys & set(stage.criteria) for stage in profile.stage_plan):
        raise ValueError('Story-dependent judgments cannot be static proof criteria')
    for d in plan.discriminants:
        for pointer in d.basis_pointers:
            _pointer(source, pointer)
    ds = {d.key: d for d in plan.discriminants}
    if (profile.archetype_references or profile.archetypal_exaggeration) and plan.salience_policy is None:
        raise ValueError('ROLE_SALIENCE_POLICY_REQUIRED')
    for ref in profile.archetype_references:
        for principle in ref.transferable_principles:
            if not set(principle.discriminant_ids) <= ds.keys():
                raise ValueError('Reference mechanism must resolve to authored discriminants')
    if profile.archetypal_exaggeration:
        ids = set(profile.archetypal_exaggeration.defining_discriminant_ids)
        if not ids <= ds.keys() or not plan.salience_policy or not ids <= set(plan.salience_policy.defining_discriminant_ids):
            raise ValueError('Exaggeration may not bypass defining salience')
    return {'profile': source, 'planFingerprint': sha256_canonical(plan),
            'boundary': 'Validates authored trace and categorical contrast, not psychological truth or image quality.'}


def compile_visual_discriminants(profile: RoleArchetypeProfile, plan: VisualCastingPlan,
        variant_key: str, stage: ProofStage, *, purpose: str = 'CANDIDATE',
        calibration_conditions: dict[str, str] | None = None,
        route_context: RouteCastingContext | None = None) -> dict[str, Any]:
    meta = validate_visual_plan(profile, plan)
    if purpose not in {'CANDIDATE', 'CALIBRATION'}:
        raise ValueError('Unknown compilation purpose')
    variant = next((v for v in plan.variants if v.key == variant_key), None)
    if variant is None:
        raise ValueError('Unknown variant')
    stage_plan = next((s for s in profile.stage_plan if s.stage == stage), None)
    if stage_plan is None:
        raise ValueError('Stage not in role plan')
    if purpose == 'CALIBRATION' and (stage != 'FACE' or not calibration_conditions):
        raise ValueError('Geometry calibration requires FACE and explicit controls')
    if purpose != 'CALIBRATION' and calibration_conditions is not None:
        raise ValueError('Calibration controls cannot silently replace candidate conditions')
    buckets: dict[str, list[dict[str, Any]]] = {k: [] for k in (
        'DIRECT_FACE_DISCRIMINANTS', 'BODY_SCALE_DISCRIMINANTS',
        'SOCIAL_PRESENCE_DISCRIMINANTS', 'PERFORMANCE_ONLY_NOT_FOR_FACE', 'STORY_NOT_FOR_STATIC_REVIEW')}
    bucket_by_stage = {'FACE': 'DIRECT_FACE_DISCRIMINANTS', 'SCALE': 'BODY_SCALE_DISCRIMINANTS',
        'SOCIAL': 'SOCIAL_PRESENCE_DISCRIMINANTS', 'PERFORMANCE': 'PERFORMANCE_ONLY_NOT_FOR_FACE',
        None: 'STORY_NOT_FOR_STATIC_REVIEW'}
    lines: list[str] = []
    trace = []
    # Only stage-relevant visible choices enter generation. Interpretation stays in trace.
    for d in plan.discriminants:
        option = variant.assignments.get(d.key)
        text = d.choices[option] if option is not None else next(iter(d.choices.values()))
        buckets[bucket_by_stage[d.stage]].append({'key': d.key, 'text': text,
            'observation': d.observation, 'basisPointers': list(d.basis_pointers)})
        if d.stage == stage:
            lines.append(text)
            trace.append({'discriminant': d.key, 'option': option, 'line': text,
                          'basisPointers': list(d.basis_pointers)})
    conditions = calibration_conditions if purpose == 'CALIBRATION' else stage_plan.conditions
    assert conditions is not None
    sections = list(conditions.values()) + lines
    # Calibration changes controls and eligibility, not the authored structure policy.
    if plan.salience_policy:
        sections.append('Preserve the defining structures above; aesthetic refinement must never reduce their salience or pull them toward an average face.')
    if profile.archetypal_exaggeration:
        sections.append(profile.archetypal_exaggeration.anatomical_limit)
    if purpose == 'CANDIDATE' or profile.archetypal_exaggeration:
        for channel in plan.appeal.channels:
            if any(d.key in channel.discriminant_ids and d.stage == stage for d in plan.discriminants):
                sections.append(channel.audience_effect)
    prompt = '\n'.join(sections)
    if any(name.casefold() in prompt.casefold() for ref in profile.archetype_references for name in ref.proper_names):
        raise ValueError('REFERENCE_PROPER_NAME_IN_PROVIDER_PROMPT')
    result = {'phase': 'SEARCH', 'purpose': purpose, 'stage': stage, 'variant': variant_key,
        'profileFingerprint': plan.profile_fingerprint, 'planFingerprint': meta['planFingerprint'],
        'conditionsFingerprint': sha256_canonical(conditions), 'prompt': prompt,
        'promptFingerprint': sha256_canonical(prompt), 'trace': trace, 'responsibilityBuckets': buckets,
        'appeal': dump_contract(plan.appeal), 'intent': dump_contract(plan.intent),
        'FaceDiscriminants': buckets['DIRECT_FACE_DISCRIMINANTS'],
        'BodyDiscriminants': buckets['BODY_SCALE_DISCRIMINANTS'],
        'SocialPresenceRequirements': buckets['SOCIAL_PRESENCE_DISCRIMINANTS'],
        'PerformanceProofRequirements': buckets['PERFORMANCE_ONLY_NOT_FOR_FACE'],
        'ForbiddenDrifts': list(profile.drift_avoidance) + (list(profile.archetypal_exaggeration.forbidden_drifts) if profile.archetypal_exaggeration else []),
        'referenceMechanisms': [{'referenceId': ref.reference_id, 'principles': [
            {'key': pr.key, 'mechanism': pr.mechanism, 'discriminantIds': list(pr.discriminant_ids),
             'projectedChoices': [row for row in trace if row['discriminant'] in pr.discriminant_ids]}
            for pr in ref.transferable_principles]}
            for ref in profile.archetype_references],
        'exaggerationProjection': ({'mode': profile.archetypal_exaggeration.mode,
            'anatomicalLimit': profile.archetypal_exaggeration.anatomical_limit,
            'projectedChoices': [row for row in trace if row['discriminant'] in profile.archetypal_exaggeration.defining_discriminant_ids]}
            if profile.archetypal_exaggeration else None),
        'approvalEligible': False, 'transportRequirement': 'MCP',
        'boundary': 'Compilation is not spend authorization, provider adherence, a stage pass, or user approval.'}
    if route_context is not None:
        from drama_plugin.visual_route import project_casting_route
        result = project_casting_route(result, route_context, character_identity=profile.identity)
        if any(name.casefold() in result['prompt'].casefold() for ref in profile.archetype_references for name in ref.proper_names):
            raise ValueError('REFERENCE_PROPER_NAME_IN_PROVIDER_PROMPT')
    return result


def verify_submitted_projection(compiled: dict[str, Any], submitted_prompt: str) -> dict[str, Any]:
    if sha256_canonical(compiled['prompt']) != compiled['promptFingerprint'] or submitted_prompt != compiled['prompt']:
        raise ValueError('SUBMITTED_PROMPT_DIFFERS_FROM_COMPILED_DISCRIMINANTS')
    if any(row['line'] not in submitted_prompt for row in compiled['trace']):
        raise ValueError('MISSING_COMPILED_CHOICE')
    return {'status': 'PASS', 'promptFingerprint': compiled['promptFingerprint'],
            'boundary': 'Exact pre-provider-node text, not provider internal rewritten text.'}


def visual_selection_gate(profile: RoleArchetypeProfile, plan: VisualCastingPlan,
                          reviews: Sequence[CastingReview], *, purpose: str = 'CANDIDATE') -> dict[str, Any]:
    meta = validate_visual_plan(profile, plan)
    if purpose != 'CANDIDATE':
        return {'status': 'CALIBRATION_ONLY', 'finalists': [], 'userApprovedWinner': None, 'formalPromotionAllowed': False}
    accepted = []
    for r in reviews:
        if plan.salience_policy:
            stage_ids = {d.key for d in plan.discriminants if d.stage == r.stage}
            required = set(plan.salience_policy.defining_discriminant_ids) & stage_ids
            if any('salience:' + key not in r.findings or r.findings['salience:' + key].status != 'PASS' for key in required):
                continue
        appeal = r.audience_appeal
        if appeal is None or appeal.plan_fingerprint != meta['planFingerprint']:
            continue
        if appeal.primary_response != plan.appeal.primary_response:
            continue
        permitted = {'PASS', 'SHORTLIST'} if r.stage == 'FACE' else {'PASS'}
        if appeal.status in permitted:
            accepted.append(r)
    return user_selection_gate(profile, accepted)
