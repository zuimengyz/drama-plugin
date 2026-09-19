"""Explicit review workflow; provider facts remain candidates until user attest."""
from typing import Any
from drama_plugin.providers.base.audio_semantic import AudioSemanticInput, AudioSemanticProvider, AudioSemanticResult
from drama_plugin.contracts.adaptive_direction import ObservedMaterialEvidence
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.source_pin import SourcePin


async def observe_audio(provider: AudioSemanticProvider | None, source: AudioSemanticInput) -> AudioSemanticResult:
    if provider is None:
        return AudioSemanticResult(None, {'semanticProviderCalls':0,'status':'NOT_RUN'}, '', 'AUDIO_SEMANTIC_PROVIDER_DISABLED')
    return await provider.observe_audio(source)


def align_for_user_review(visual: dict[str, Any], result: AudioSemanticResult) -> dict[str, Any]:
    if result.receipt.get('sourceMediaHash') != visual['sourceHash']:
        raise ValueError('Audio/visual source hash mismatch')
    observation=result.observation
    candidates=[{'id':f'A{i+1:03}', 'layer':layer, **dump_contract(event)}
                for i,(layer,event) in enumerate(observation.timed_events())] if observation else []
    for event in candidates:
        if event['end'] > visual['duration']:raise ValueError('Audio exceeds source duration')
    return {'sourceHash':visual['sourceHash'], 'status':'READY_FOR_USER_ATTESTATION' if candidates and result.status=='READY_FOR_USER_ATTESTATION' else 'BLOCKED',
        'audioSemanticUserAttestation':'PENDING','adoptedAudioFacts':[], 'audioCandidates':candidates,
        'events':[{'id':v['id'],'start':v['start'],'end':v['end'],'visual':v['visual'],
                   'audioCandidates':[a for a in candidates if max(v['start'],a['start']) < min(v['end'],a['end'])],
                   'audioEvidenceRefs':[result.receipt['sourceAudioHash']],
                   'fusionMeaning':'Concurrent candidate claims only; no causal or identity inference; user attestation required'} for v in visual['events']],
        'formalMediaAuthorized':False}


def attested_audio_facet(result: AudioSemanticResult, binding: dict[str, Any],
                         evidence_pin: SourcePin, user_review_pin: SourcePin | None) -> ObservedMaterialEvidence:
    """The caller must verify a genuine user receipt before supplying its pin."""
    if user_review_pin is None or result.observation is None:
        raise ValueError('AUDIO_SEMANTIC_USER_ATTESTATION_REQUIRED')
    facts=[f'[{event.start}–{event.end}s] {layer}: {event.description}; speaker={event.speaker_hint}; confidence={event.confidence}; uncertainty={event.uncertainty}'
           for layer,event in result.observation.timed_events()]
    return ObservedMaterialEvidence(**binding, basis='OBSERVED_MEDIA',
        media_hash=result.receipt['sourceMediaHash'], start=result.receipt['sourceStart'],end=result.receipt['sourceEnd'],
        facts={'audio_events':tuple(facts)},uncertain_observations=result.observation.uncertain_observations,
        observation_confidence='MEDIUM',observer_type='VERIFIED_MULTIMODAL_RUNTIME',method='AUDIO',
        evidence_refs=(evidence_pin,),fact_review_ref=user_review_pin)
