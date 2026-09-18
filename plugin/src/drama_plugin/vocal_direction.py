"""Provider-neutral vocal requirement. No melody invention or audio generation."""
from __future__ import annotations
from typing import Any, AbstractSet
from drama_plugin.contracts.performance_direction import VocalDelivery
from drama_plugin.contracts.sequence import FilmReview


def require_vocal_capability(delivery: VocalDelivery, *, supported_modes: AbstractSet[str], lyrics: str | None = None) -> dict[str, Any]:
    if delivery.realization_status!='RESOLVED':
        raise ValueError('VOCAL_REALIZATION_UNRESOLVED_OR_WITHHELD')
    if delivery.lyric_status == 'NO_APPROVED_LYRICS' and lyrics:
        raise ValueError('NEW_LYRICS_FORBIDDEN')
    if delivery.mode not in supported_modes:
        raise ValueError('VOCAL_MODE_CAPABILITY_REQUIRED: '+delivery.mode)
    if delivery.melody_status == 'UNRESOLVED':
        raise ValueError('MELODY_UNRESOLVED: production qualification blocked; choose/approve composition without historical authenticity claim')
    return {'status':'SEMANTIC_REQUIREMENT_SATISFIED','mode':delivery.mode,'productionAuthorized':False}


def native_vocal_disposition(review: FilmReview, delivery: VocalDelivery, *, observed_mode: str) -> dict[str, Any]:
    from drama_plugin.performance_direction import native_audio_disposition
    if observed_mode != delivery.mode:
        return {'disposition':'REVIEW_REQUIRED','reason':'VOCAL_MODE_MISMATCH','providerCalls':0}
    # Preserving acceptable existing audio requires no new singing qualification.
    return native_audio_disposition(review)


def historical_verse_realization(delivery: VocalDelivery, *, policy_ref: str,
                                 policy_fingerprint: str, current: dict[str,str],
                                 shared_response: bool = False) -> VocalDelivery:
    """Explicit current user amendment; source fact is not rewritten as a score."""
    if current.get(policy_ref)!=policy_fingerprint:raise ValueError('STALE_HISTORICAL_VERSE_POLICY')
    if shared_response:
        return VocalDelivery(mode='SHARED_RESPONSE',source_ref=delivery.source_ref,
            lyric_status='NO_APPROVED_LYRICS',melody_status='NOT_APPLICABLE',realization_status='UNRESOLVED')
    return VocalDelivery(mode='DECLAMED_VERSE',source_ref=delivery.source_ref,
        lyric_status='EXACT_SOURCE',melody_status='NOT_APPLICABLE')
