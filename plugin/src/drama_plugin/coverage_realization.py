"""Pure opt-in production bridge; no persistence, provider, media observation or adoption."""
from __future__ import annotations
from typing import Any, Mapping, Sequence
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.coverage_realization import CoverageDependency, CoverageRealizationPlan
from drama_plugin.contracts.editorial_authority import EditorialAuthority
from drama_plugin.contracts.creation import Shot
from drama_plugin.contracts.media import Media


def realization_handoff(authority: EditorialAuthority, plans: Sequence[CoverageRealizationPlan], dependencies: Sequence[CoverageDependency], current_sources: Mapping[str,str]) -> dict[str,Any]:
    units={u.key:u for u in authority.coverage_units};by_id={p.coverage_unit_id:p for p in plans}
    if len(by_id)!=len(plans) or set(by_id)!=set(units):raise ValueError('Exact coverage identity set required')
    edges={d.key:d for d in dependencies}
    if len(edges)!=len(dependencies):raise ValueError('Duplicate dependency ID')
    def fresh(pins: Any) -> None:
        for pin in pins:
            if current_sources.get(pin.key)!=pin.fingerprint:raise ValueError('SOURCE_CONFLICT')
    fresh(authority.source_authority)
    for p in plans:
        u=units[p.coverage_unit_id]
        refs={r.intent.director_intent_id for r in authority.requirements if u.key in (*r.required_coverage,*r.optional_coverage)}
        if p.scene_id!=u.scene_id or set(p.director_intent_refs)!=refs or p.coverage_type!=u.necessity or p.source_fingerprint!=sha256_canonical(u):raise ValueError('Coverage identity/content mismatch')
        allowed_events={event for r in authority.requirements if u.key in (*r.required_coverage,*r.optional_coverage) for event in r.cut.hold.event_sequence}
        if not set(p.policy.required_temporal_order)<=allowed_events:raise ValueError('Unapproved production event')
        fresh(p.source_authority);fresh(u.source_authority);fresh(p.optional_activation_evidence)
        if set(p.dependency_refs)!={d.key for d in dependencies if d.coverage_unit_id==u.key}:raise ValueError('Incomplete dependency refs')
    ordering: dict[str,set[str]]={key:set() for key in units}
    sharing:set[frozenset[str]]=set();forbidden:set[frozenset[str]]=set()
    for d in dependencies:
        fresh(d.source_authority)
        a,b=d.coverage_unit_id,d.target_coverage_unit_id
        if a not in units or b not in units:raise ValueError('Dangling dependency')
        if d.relation in ('depends_on','must_follow'):ordering[b].add(a)
        if d.relation=='must_precede':ordering[a].add(b)
        if d.relation=='may_share_material_with':sharing.add(frozenset((a,b)))
        if d.relation=='must_not_share_material_with':forbidden.add(frozenset((a,b)))
    if sharing&forbidden:raise ValueError('Conflicting sharing relationship')
    visiting:set[str]=set();done:set[str]=set()
    def visit(key: str) -> None:
        if key in visiting:raise ValueError('Causal dependency cycle')
        if key in done:return
        visiting.add(key)
        for target in ordering[key]:visit(target)
        visiting.remove(key);done.add(key)
    for key in units:visit(key)
    return {'state':'REALIZATION_PLAN_VALID','planFingerprint':sha256_canonical([dump_contract(p) for p in plans]),'editorialFingerprint':sha256_canonical(authority),'required':sum(u.necessity=='REQUIRED' for u in units.values()),'optional':sum(u.necessity=='OPTIONAL' for u in units.values()),'formalShotsCreated':0}


def generation_handoff(authority: EditorialAuthority, plans: Sequence[CoverageRealizationPlan], dependencies: Sequence[CoverageDependency], shots: Sequence[Shot], *, scene_id: str, current_sources: Mapping[str,str], approval_fingerprint: str | None, group_members: Mapping[str,Sequence[str]] | None = None) -> dict[str,Any]:
    receipt=realization_handoff(authority,plans,dependencies,current_sources)
    if approval_fingerprint!=receipt['planFingerprint']:raise ValueError('CLOSEOUT_APPROVAL_REQUIRED')
    scoped=[p for p in plans if p.scene_id==scene_id]
    if not scoped:raise ValueError('Unknown scene')
    active=[p for p in scoped if p.coverage_type=='REQUIRED' or p.optional_activation_evidence]
    if any(p.formalization_state!='FORMALIZED' for p in active):raise ValueError('SCENE_REQUIRED_COVERAGE_NOT_FORMALIZED')
    index={s.id:s for s in shots}
    if len(index)!=len(shots):raise ValueError('Duplicate canonical Shot')
    expected={s for p in active for s in p.planned_shot_refs}
    if set(index)!=expected:raise ValueError('Missing or extra Shot / duplicate production expansion')
    group_members=group_members or {}
    manifests=[]
    for p in active:
        for group in p.planned_shot_group_refs:
            if not group_members.get(group) or not set(group_members[group])<=set(p.planned_shot_refs):raise ValueError('Unresolved formal Shot group')
    for p in active:
        segments=[]
        for ref in p.planned_shot_refs:
            shot=index[ref]
            segment=shot.content.get('coverageRealization',{}).get('coverageSegments',{}).get(p.coverage_unit_id)
            if not isinstance(segment,dict) or not segment.get('evidenceLocator'):raise ValueError('Missing independently locatable coverage segment')
            if segment.get('continuityKeys')!=p.policy.continuity_keys:raise ValueError('Continuity obligations lost')
            if segment.get('sharedState')!=p.policy.required_shared_state:raise ValueError('Shared state obligations lost')
            if p.policy.split_policy=='PROTECTED_SEQUENCE' and segment.get('attentionBreak') is not False:raise ValueError('Protected perceptual chain interrupted')
            segments.append(segment)
        if p.policy.split_policy=='NO_INTERNAL_SPLIT' and len(segments)!=1:raise ValueError('Indivisible evidence split')
        if p.policy.realization_mode=='MULTI_MATERIAL_REQUIRED' and len(segments)<2:raise ValueError('Hidden compound material')
        events=[event for segment in segments for event in segment.get('eventRefs',[])]
        if events!=list(p.policy.required_temporal_order):raise ValueError('Approved temporal chain omitted or reordered')
    for shot in shots:
        bound=[p for p in active if shot.id in p.planned_shot_refs]
        required_ids={p.coverage_unit_id for p in bound}
        facet=shot.content.get('coverageRealization',{})
        if shot.scene_id!=scene_id or not required_ids or set(facet.get('satisfiesCoverageIds',[]))!=required_ids:raise ValueError('Invalid satisfiesCoverageIds')
        if facet.get('planFingerprint')!=receipt['planFingerprint']:raise ValueError('Stale Shot realization')
        intents=sorted({i for p in bound for i in p.director_intent_refs})
        if sorted(facet.get('directorIntentRefs',[]))!=intents:raise ValueError('Shot intent mismatch')
        for name in ('mustPreserve','acceptableVariation','forbiddenDrift','continuityKeys','referencePriority','providerModeRequirement'):
            if not facet.get(name):raise ValueError('Missing generation intention: '+name)
        for d in dependencies:
            if d.relation=='must_not_share_material_with' and {d.coverage_unit_id,d.target_coverage_unit_id}<=required_ids:raise ValueError('Forbidden shared material')
        if facet.get('coverageSourceFingerprints')!={p.coverage_unit_id:p.source_fingerprint for p in bound}:raise ValueError('Shot coverage source mismatch')
        manifests.append({'shotRef':shot.id,'shotFingerprint':sha256_canonical(shot),'coverageRefs':sorted(required_ids),'directorIntentRefs':intents,'sourceFingerprint':receipt['planFingerprint'],'sceneId':scene_id,'generationIntent':facet})
    return {**receipt,'state':'READY_FOR_EXISTING_GENERATION_PLANNING','sceneId':scene_id,'shots':manifests,'providerCalls':0}


def media_handoff(media: Media, shot: Shot, generation: Mapping[str,Any], *, work_id: str, current_plan_fingerprint: str, current_source_verified: bool, phase_approved: bool) -> dict[str,Any]:
    # This validates intended lineage only. It never evaluates the footage.
    denied='R5C_OBSERVATION_NOT_AUTHORIZED'
    if not phase_approved or not current_source_verified or generation.get('state')!='READY_FOR_EXISTING_GENERATION_PLANNING' or generation.get('planFingerprint')!=current_plan_fingerprint:raise ValueError(denied)
    matches=[x for x in generation['shots'] if x['shotRef']==shot.id]
    if len(matches)!=1:raise ValueError(denied)
    expected=matches[0]
    if expected['shotFingerprint']!=sha256_canonical(shot) or media.shot_id!=shot.id or media.work_id!=work_id or not media.content_hash:raise ValueError(denied)
    lineage=media.content.get('coverageRealization',{})
    for key in ('shotRef','coverageRefs','directorIntentRefs','sourceFingerprint','sceneId','shotFingerprint'):
        if lineage.get(key)!=expected[key]:raise ValueError(denied)
    return {'state':'INTENDED_LINEAGE_READY_FOR_EXISTING_DAILIES','mediaRef':media.id,'mediaHash':media.content_hash,'shotRef':shot.id,'sceneId':shot.scene_id,'coverageRefs':expected['coverageRefs'],'directorIntentRefs':expected['directorIntentRefs'],'observationPerformed':False,'adopted':False}
