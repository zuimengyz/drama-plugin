"""Immutable Film lineage validation at the existing Ledger admission boundary."""
from collections.abc import Callable
from drama_plugin.film.contracts import (FilmArtifact,FilmPlan,FinalFilmCandidate,FinalTechnicalQA,FinalCreativeReview,FinalDelivery,FilmRevisionFeedback)
from drama_plugin.execution.contracts import ReviewedAVCandidate,TechnicalMediaReview,CreativeMediaReview
from drama_plugin.persistence.review import UserDecisionRecord
from drama_plugin.runtime.contracts import ArtifactReference,RuntimeContract,DecisionCategory

CORE_QA={'container_readable','video_decode','audio_decode','duration','resolution_profile','hash_consistency'}

def validate_links(item:FilmArtifact,resolve:Callable[[ArtifactReference],RuntimeContract])->None:
    def candidate(ref:ArtifactReference)->FinalFilmCandidate:
        value=resolve(ref)
        if not isinstance(value,FinalFilmCandidate) or value.scope!=item.scope or value.film_version!=item.film_version:
            raise ValueError('Wrong Film candidate scope/version')
        return value
    if isinstance(item,FilmPlan):
        return # Author originals resolve through their independent Canon owner.
    if isinstance(item,FinalFilmCandidate):
        plan=resolve(item.plan_ref)
        if not isinstance(plan,FilmPlan) or plan.scope!=item.scope or plan.film_version!=item.film_version:
            raise ValueError('Wrong Film plan')
        if len(plan.unit_version_refs)!=len(item.shots):
            raise ValueError('Film recipe differs from approved Shot structure')
        if len({s.shot_id for s in item.shots})!=len(item.shots):
            raise ValueError('Duplicate Film Shot binding')
        for slot,shot in enumerate(item.shots):
            if shot.shot_ref not in plan.unit_version_refs[slot]:
                raise ValueError('Film recipe borrows unapproved Shot version/order')
            av=resolve(shot.candidate_ref)
            if not isinstance(av,ReviewedAVCandidate) or av.scope.work_id!=item.scope.work_id or (av.scope.scene_id,av.scope.shot_id)!=(shot.scene_id,shot.shot_id) or av.media!=shot.media or av.source_package_ref!=shot.package_ref:
                raise ValueError('Film assembly borrows wrong reviewed media/Shot/Package')
            technical=resolve(av.av_technical_ref)
            creative=resolve(av.av_creative_ref)
            if not isinstance(technical,TechnicalMediaReview) or technical.outcome!='PASS' or not isinstance(creative,CreativeMediaReview) or creative.outcome!='PASS':
                raise ValueError('Film requires reviewed AV')
        if item.duration_ms!=sum(s.duration_ms for s in item.shots):
            raise ValueError('Film edit recipe duration differs from approved AV')
        if item.profile.subtitle_required and item.subtitle_ref is None:
            raise ValueError('Required subtitle derivative absent')
    elif isinstance(item,(FinalTechnicalQA,FinalCreativeReview)):
        final=candidate(item.candidate_ref)
        if item.media_hash!=final.media.content_hash:
            raise ValueError('Review Media hash differs from exact candidate')
        if isinstance(item,FinalTechnicalQA) and item.outcome=='PASS' and (item.failures or not CORE_QA<=set(item.checks)):
            raise ValueError('Technical pass lacks actual final checks')
        if isinstance(item,FinalCreativeReview):
            if not set(item.affected_shots)<=set(s.shot_id for s in final.shots):
                raise ValueError('Final feedback affects unrelated Shot')
            if item.outcome=='PASS' and any(o.required_revision for o in item.observations):
                raise ValueError('Creative PASS contradicts mandatory revision')
    elif isinstance(item,FinalDelivery):
        final=candidate(item.candidate_ref)
        qa,creative,decision=resolve(item.technical_ref),resolve(item.creative_ref),resolve(item.acceptance_ref)
        if not isinstance(qa,FinalTechnicalQA) or not isinstance(creative,FinalCreativeReview) or qa.outcome!='PASS' or creative.outcome!='PASS' or qa.candidate_ref!=item.candidate_ref or creative.candidate_ref!=item.candidate_ref:
            raise ValueError('Final delivery must bind exact reviewed film')
        if not isinstance(decision,UserDecisionRecord) or not decision.accepted or decision.category!=DecisionCategory.FINAL_ACCEPTANCE or decision.source_ref!=item.candidate_ref or decision.scope!=item.scope:
            raise ValueError('Final acceptance must pin exact reviewed Film/hash')
        if (item.media,item.subtitle_ref,item.profile,item.canonical_media_ref)!=(final.media,final.subtitle_ref,final.profile,final.canonical_media_ref):
            raise ValueError('Delivery cannot replace accepted media/profile/subtitles')
    elif isinstance(item,FilmRevisionFeedback):
        candidate(item.candidate_ref)
