"""Bounded adaptive judgments over attested evidence; never senses or generates media."""
from __future__ import annotations
from typing import Any, Mapping, Sequence
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.contracts.adaptive_direction import ObservedMaterialEvidence, AdaptiveDecision
from drama_plugin.contracts.creation import Shot
from drama_plugin.contracts.media import Media
from drama_plugin.contracts.editorial_authority import EditorialUsability
from drama_plugin.coverage_realization import media_handoff

AUTHORITY_ROLES={'priority','cut_conditions','continuity','performance','film_grammar','aesthetic_constitution','music_boundary','historical_provenance','director_intent','runtime'}

def _fresh(pins: Sequence[SourcePin], current: Mapping[str,str]) -> None:
    if any(current.get(p.key)!=p.fingerprint for p in pins):raise ValueError('ADAPTIVE_SOURCE_CONFLICT')


def authorize_observation(media: Media, shot: Shot, generation: Mapping[str,Any], *, work_id: str, plan_fingerprint: str, authorities: Mapping[str,Sequence[SourcePin]], current_sources: Mapping[str,str], phase_approved: bool, runtime_capabilities: Sequence[str], runtime_evidence: SourcePin | None, approved_priorities: Mapping[str,str]) -> dict[str,Any]:
    if set(authorities)!=AUTHORITY_ROLES or any(not v for v in authorities.values()):raise ValueError('R5C_OBSERVATION_NOT_AUTHORIZED')
    for pins in authorities.values():_fresh(pins,current_sources)
    if not runtime_evidence or not {'SEMANTIC_VIDEO','SEMANTIC_AUDIO'}<=set(runtime_capabilities):raise ValueError('MEDIA_SEMANTIC_OBSERVATION_GAP')
    _fresh([runtime_evidence],current_sources)
    receipt=media_handoff(media,shot,generation,work_id=work_id,current_plan_fingerprint=plan_fingerprint,current_source_verified=True,phase_approved=phase_approved)
    receipt.update(basis='OBSERVED_MEDIA',workId=work_id,priorityLevels=dict(approved_priorities),authorityRefs={k:[dump_contract(p) for p in v] for k,v in authorities.items()},runtimeEvidence=dump_contract(runtime_evidence),observationPerformed=False)
    receipt['receiptFingerprint']=sha256_canonical(receipt)
    return receipt


def fixture_receipt(evidence: ObservedMaterialEvidence, *, work_id: str, approved_priorities: Mapping[str,str]) -> dict[str,Any]:
    if evidence.basis!='STRUCTURED_FIXTURE':raise ValueError('Fixtures cannot authorize real media')
    return {'basis':'STRUCTURED_FIXTURE','workId':work_id,'priorityLevels':dict(approved_priorities),'mediaRef':evidence.media_ref,'mediaHash':evidence.media_hash,'shotRef':evidence.shot_ref,'sceneId':evidence.scene_id,'coverageRefs':list(evidence.coverage_refs),'directorIntentRefs':list(evidence.director_intent_refs),'formalMediaAuthorized':False}


def adaptive_review(decision: AdaptiveDecision, observations: Sequence[ObservedMaterialEvidence], usability: EditorialUsability, receipt: Mapping[str,Any], current_sources: Mapping[str,str], *, prior_surprise: AdaptiveDecision | None = None) -> dict[str,Any]:
    d=AdaptiveDecision.model_validate(dump_contract(decision));obs=[ObservedMaterialEvidence.model_validate(dump_contract(o)) for o in observations];u=EditorialUsability.model_validate(dump_contract(usability))
    index={o.key:o for o in obs}
    if len(index)!=len(obs) or not set(d.evidence_refs)<=set(index):raise ValueError('Missing/duplicate observed evidence')
    if d.media_ref!=receipt['mediaRef'] or u.asset_ref!=d.media_ref or u.media_hash!=receipt['mediaHash'] or u.scene_id!=receipt['sceneId']:raise ValueError('R5C_OBSERVATION_NOT_AUTHORIZED')
    if not set(u.director_intent_ids)<=set(receipt['directorIntentRefs']):raise ValueError('Unbound dailies intent')
    if d.editorial_usability_ref!=sha256_canonical(u):raise ValueError('Stale dailies assessment')
    for o in obs:
        if (o.basis!=receipt['basis'] or o.media_ref!=d.media_ref or o.media_hash!=receipt['mediaHash'] or o.shot_ref!=receipt['shotRef'] or o.scene_id!=receipt['sceneId'] or set(o.coverage_refs)!=set(receipt['coverageRefs']) or set(o.director_intent_refs)!=set(receipt['directorIntentRefs'])):raise ValueError('R5C_OBSERVATION_NOT_AUTHORIZED')
        _fresh(o.evidence_refs,current_sources)
        if o.fact_review_ref:_fresh([o.fact_review_ref],current_sources)
    fixture=receipt['basis']=='STRUCTURED_FIXTURE'
    if fixture and u.basis!='SYNTHETIC_FIXTURE':raise ValueError('Fixture cannot claim observed dailies')
    if not fixture:
        raw=dict(receipt);fingerprint=raw.pop('receiptFingerprint',None)
        if fingerprint!=sha256_canonical(raw) or not receipt.get('runtimeEvidence'):raise ValueError('Invalid observation receipt')
        roles=receipt.get('authorityRefs',{})
        if set(roles)!=AUTHORITY_ROLES:raise ValueError('Incomplete intended authority')
        for pins in roles.values():_fresh([SourcePin.model_validate(p) for p in pins],current_sources)
        _fresh([SourcePin.model_validate(receipt['runtimeEvidence'])],current_sources)
        if u.basis!='OBSERVED_MEDIA':raise ValueError('Live judgment requires live dailies basis')
    _fresh(d.authority_refs,current_sources)
    for dev in d.deviations:
        _fresh(dev.intended_refs,current_sources)
        if not set(dev.observed_evidence_refs)<=set(index):raise ValueError('Deviation cites absent facts')
        levels=receipt.get('priorityLevels',{})
        if not set(dev.affected_priority_ids)<=set(levels) or any(levels[k] not in ('P0','P1','P2','P3') for k in dev.affected_priority_ids):raise ValueError('Missing approved priority identity')
        if dev.priority_impact!='NONE' and dev.priority_impact!=min(levels[k] for k in dev.affected_priority_ids):raise ValueError('Cannot downgrade approved intent priority')
        if dev.classification=='MATERIAL_DEVIATION' and dev.priority_impact=='NONE':raise ValueError('Material deviation must disclose priority impact')
    if d.performance_redirection:
        r=d.performance_redirection;_fresh(r.authority_refs,current_sources)
        if not set(r.observed_evidence_refs)<=set(index) or r.performance_deviation_ref not in {v.key for v in d.deviations if v.domain=='PERFORMANCE'}:raise ValueError('Redirection not bound to performance facts')
    if d.surprise and not set(d.surprise.unexpected_evidence_refs)<=set(index):raise ValueError('Surprise cites absent evidence')
    if d.downstream_impact:
        _fresh(d.downstream_impact.base_authority,current_sources);_fresh([d.downstream_impact.parent_revision_ref],current_sources)
    if d.human_review_ref:_fresh([d.human_review_ref],current_sources)
    if d.model_selection_ref:_fresh([d.model_selection_ref],current_sources)
    if d.retained_surprise_ref:_fresh([d.retained_surprise_ref],current_sources)
    issues=[];impacts={v.priority_impact for v in d.deviations}
    if any(v.classification=='OBSERVATION_UNCERTAIN' for v in d.deviations) or any(o.uncertain_observations or o.observation_confidence=='LOW' for o in obs):issues.append('OBSERVATION_REQUIRED')
    if any(v.domain!='PROVIDER_TECHNICAL' for v in d.deviations) and any(o.method=='TECHNICAL' for o in obs):issues.append('MEDIA_SEMANTIC_OBSERVATION_GAP')
    if 'P0' in impacts:issues.append('BLOCK_HUMAN_REVIEW_REQUIRED')
    if 'P1' in impacts and not d.human_review_ref:issues.append('P1_EXPLICIT_REVIEW_REQUIRED')
    if 'P2' in impacts and not d.grammar_equivalence_reason:issues.append('FILM_GRAMMAR_EQUIVALENCE_REQUIRED')
    if d.decision in ('KEEP','KEEP_SURPRISE') and (u.editorial_usability!='USABLE_FULL' or any(v.classification=='MATERIAL_DEVIATION' for v in d.deviations)):issues.append('KEEP_CONFLICTS_WITH_REQUIRED_INTENT')
    if d.decision in ('KEEP_SURPRISE','ADAPT_DOWNSTREAM'):
        assert d.surprise and d.downstream_impact
        if any(v!='PASS' for v in d.surprise.checks.values()):issues.append('SURPRISE_GATE_NOT_PASSED')
        if impacts&{'P0','P1'}:issues.append('SURPRISE_CANNOT_HIDE_PROTECTED_LOSS')
        if d.downstream_impact.affected['historical_claims']:issues.append('HISTORICAL_AUTHORITY_REQUIRED')
        if not d.downstream_impact.future_only:issues.append('PAST_REVISION_EXPLICIT_REVIEW_REQUIRED')
    if d.decision=='KEEP' and any(v.classification=='POSITIVE_SURPRISE_CANDIDATE' for v in d.deviations):issues.append('SURPRISE_REVIEW_REQUIRED_BEFORE_KEEP')
    if d.decision=='ADAPT_DOWNSTREAM':
        if not d.retained_surprise_ref or not prior_surprise or d.retained_surprise_ref.key!=prior_surprise.key or d.retained_surprise_ref.fingerprint!=sha256_canonical(prior_surprise) or prior_surprise.decision!='KEEP_SURPRISE' or prior_surprise.media_ref!=d.media_ref or not prior_surprise.surprise or any(v!='PASS' for v in prior_surprise.surprise.checks.values()) or any(v.priority_impact in ('P0','P1') for v in prior_surprise.deviations):issues.append('RETAINED_SURPRISE_RECEIPT_REQUIRED')
    if d.decision=='REJECT' and (u.editorial_usability!='UNUSABLE' or u.usable_ranges or u.covered_requirements):issues.append('REJECT_CONFLICTS_WITH_USABLE_FRAGMENT')
    if d.decision=='ROUTE_CHANGE' and not d.model_selection_ref:issues.append('MODEL_SELECTION_AUTHORITY_REQUIRED')
    if d.decision=='UPSTREAM_REWRITE':issues.append('HUMAN_UPSTREAM_REVIEW_REQUIRED')
    return {'status':('DRY_RUN_' if fixture else '')+('BLOCKED' if issues else 'DECISION_PROPOSAL_READY'),'decision':d.decision,'issues':issues,'whatIsPreserved':list(d.what_is_preserved),'nextAction':d.next_action,'decisionFingerprint':sha256_canonical(d),'editorialUsability':u.editorial_usability,'artisticJudgment':d.artistic_judgment,'formalMediaAuthorized':not fixture,'executionAuthorized':False,'observedByThisFunction':False,'authorityChanged':False}


def downstream_overlay_handoff(decision: AdaptiveDecision, verdict: Mapping[str,Any], *, current_sources: Mapping[str,str], reviewed_decision_fingerprint: str | None) -> dict[str,Any]:
    d=AdaptiveDecision.model_validate(dump_contract(decision));impact=d.downstream_impact
    if d.decision not in ('KEEP_SURPRISE','ADAPT_DOWNSTREAM') or not impact or verdict.get('decisionFingerprint')!=sha256_canonical(d) or verdict.get('issues'):raise ValueError('DOWNSTREAM_IMPACT_NOT_APPROVED')
    _fresh(impact.base_authority,current_sources);_fresh([impact.parent_revision_ref],current_sources)
    if not impact.future_only or impact.affected['historical_claims']:raise ValueError('UPSTREAM_AUTHORITY_REQUIRED')
    if reviewed_decision_fingerprint!=sha256_canonical(d):raise ValueError('EXPLICIT_OVERLAY_REVIEW_REQUIRED')
    return {'status':'ADAPTIVE_OVERLAY_CANDIDATE','overlay':dump_contract(impact),'basePreserved':True,'writes':0,'productionAuthorized':False,'fixtureOnly':str(verdict.get('status','')).startswith('DRY_RUN_')}


def pairwise_handoff(review: Any, evidence_a: ObservedMaterialEvidence, evidence_b: ObservedMaterialEvidence, current_sources: Mapping[str,str], *, receipt_a: Mapping[str,Any] | None = None, receipt_b: Mapping[str,Any] | None = None) -> dict[str,Any]:
    from drama_plugin.contracts.film_grammar import AestheticPairwiseReviewContract
    r=AestheticPairwiseReviewContract.model_validate(dump_contract(review))
    evidence_a=ObservedMaterialEvidence.model_validate(dump_contract(evidence_a));evidence_b=ObservedMaterialEvidence.model_validate(dump_contract(evidence_b))
    for o,receipt in ((evidence_a,receipt_a),(evidence_b,receipt_b)):
        _fresh(o.evidence_refs,current_sources)
        if o.fact_review_ref:_fresh([o.fact_review_ref],current_sources)
        if o.basis=='OBSERVED_MEDIA':
            if not receipt:raise ValueError('R5C_OBSERVATION_NOT_AUTHORIZED')
            raw=dict(receipt);fingerprint=raw.pop('receiptFingerprint',None)
            if fingerprint!=sha256_canonical(raw) or receipt.get('basis')!='OBSERVED_MEDIA' or receipt.get('workId')!=r.work_id or receipt.get('mediaRef')!=o.media_ref or receipt.get('mediaHash')!=o.media_hash or receipt.get('shotRef')!=o.shot_ref or receipt.get('sceneId')!=o.scene_id or set(receipt.get('coverageRefs',[]))!=set(o.coverage_refs) or set(receipt.get('directorIntentRefs',[]))!=set(o.director_intent_refs):raise ValueError('R5C_OBSERVATION_NOT_AUTHORIZED')
            roles=receipt.get('authorityRefs',{})
            if set(roles)!=AUTHORITY_ROLES or not receipt.get('runtimeEvidence'):raise ValueError('Incomplete intended authority')
            for pins in roles.values():
                if not pins:raise ValueError('Incomplete intended authority')
                _fresh([SourcePin.model_validate(pin) for pin in pins],current_sources)
            _fresh([SourcePin.model_validate(receipt['runtimeEvidence'])],current_sources)
    if not r.work_id or set(r.coverage_refs)!=set(evidence_a.coverage_refs) or set(r.coverage_refs)!=set(evidence_b.coverage_refs) or set(r.director_intent_refs)!=set(evidence_a.director_intent_refs) or set(r.director_intent_refs)!=set(evidence_b.director_intent_refs):raise ValueError('Pairwise needs same Coverage and Intent')
    if evidence_a.scene_id!=evidence_b.scene_id or evidence_a.basis!=evidence_b.basis:raise ValueError('Incomparable pairwise scope')
    if (r.candidate_a.key,r.candidate_a.fingerprint)!=(evidence_a.media_ref,evidence_a.media_hash) or (r.candidate_b.key,r.candidate_b.fingerprint)!=(evidence_b.media_ref,evidence_b.media_hash):raise ValueError('Pairwise media mismatch')
    _fresh((*r.source_pins,r.constitution_ref,*r.evidence_refs),current_sources)
    if r.user_feedback_ref:_fresh([r.user_feedback_ref],current_sources)
    if r.preferred_candidate!='UNDETERMINED' and (any(o.uncertain_observations or o.observation_confidence=='LOW' or o.method in ('TECHNICAL','FRAMES') for o in (evidence_a,evidence_b))):raise ValueError('Insufficient semantic observation for taste choice')
    return {'status':'DRY_RUN_PAIRWISE_REVIEW' if evidence_a.basis=='STRUCTURED_FIXTURE' else 'PAIRWISE_PROPOSAL','preferredCandidate':r.preferred_candidate,'reason':r.reason,'userPreference':r.user_preference,'workScope':r.work_id,'modelLearningClaimed':False,'adopted':False}
