"""Compile authored video facts and constraints without inventing creative decisions."""
from typing import Any
from drama_plugin.contracts.base import canonical_json, sha256_canonical
from drama_plugin.contracts.video import VideoRequest

def compile_video_prompt(r: VideoRequest) -> str:
    """Lossless structural projection. No LLM rewrite, vendor-owned characters or style."""
    if r.prompt_ir is not None:
        return compile_request_ir(r)['prompt']
    p = r.continuity
    facts = {k: v for k, v in p.model_dump(mode='json', by_alias=True).items() if k in {
        'characters', 'locationIdentity', 'timeOfDay', 'weather', 'lighting', 'style', 'colorLanguage', 'lensLanguage'}}
    facts['style'] = {k: v for k, v in facts['style'].items() if k not in {'revision', 'castingCriteria'}}
    labels = [{'slot': slot, 'semantics': list(x.semantics)} for slot, x in
              [('first_frame', r.first_frame), ('last_frame', r.last_frame)] if x]
    for kind, refs in [('image', r.reference_images), ('video', r.reference_videos), ('audio', r.reference_audios)]:
        labels.extend({'slot': f'reference_{kind}_{i + 1}', 'semantics': list(x.semantics)} for i, x in enumerate(refs))
    from drama_plugin.visual.payload_scope import review_compiled
    prompt = review_compiled((r.prompt + ('\nNegative constraints: ' + r.negative_prompt if r.negative_prompt else '')
            + '\nCanonical continuity (preserve exactly): ' + canonical_json(facts)
            + ('\nReference roles: ' + canonical_json(labels) if labels else '')), 'VIDEO', audio=r.native_audio)
    from drama_plugin.visual.positive_projection import normalize
    return normalize(prompt, 'VIDEO', r.prompt_normalization, audio=r.native_audio)[0]



def ir_source_fingerprint(r: VideoRequest) -> str:
    # Authority binding appends source receipts and executable asset text; these
    # remain checked by the existing authority gate, not a second intent contract.
    from copy import deepcopy
    source = deepcopy(r.authority_context['creativeIntent'] if r.authority_context else
                      r.model_dump(mode='json', by_alias=True))
    source.pop('prompt_ir', None)
    source.pop('authority_context', None)
    source['continuity'].pop('sources', None)
    return sha256_canonical(source)


def compile_request_ir(r: VideoRequest) -> dict[str, Any]:
    from drama_plugin.visual.prompt_ir import compile_ir
    from copy import deepcopy
    if not r.prompt_ir:
        raise ValueError('VISUAL_PROMPT_IR_REQUIRED_BEFORE_SUBMISSION')
    if r.prompt_normalization:
        raise ValueError('VISUAL_PROMPT_IR_POST_REWRITE_FORBIDDEN')
    raw = deepcopy(r.prompt_ir)
    if r.authority_context:
        for row in r.authority_context['assets']:
            raw.setdefault('continuity', []).append(dict(text=row['executableSemantic'], priority='CRITICAL',
                source='asset:' + row['assetId'], scope='CURRENT'))
    from drama_plugin.providers.video.registry import registry
    model = r.continuity.primary_model
    limit = registry()['models'][model]['prompt_limit']
    result = compile_ir(raw, provider_family=r.continuity.primary_provider, audio_supported=r.native_audio,
                        hard_limit=limit, model=model, limit_source='provider adapter capability')
    ir = result['ir']
    modes = {'text_to_video': 'text', 'image_to_video': 'single_image', 'first_last_frame': 'first_last'}
    if ir['task']['task_type'] != 'VIDEO' or ir['task']['input_mode'] != modes.get(r.input_mode, 'reference'):
        raise ValueError('VISUAL_PROMPT_IR_TASK_SOURCE_MISMATCH')
    if ir['source_fingerprint'] != ir_source_fingerprint(r):
        raise ValueError('VISUAL_PROMPT_IR_SOURCE_CHANGED')
    return result


def prompt_compilation(request: VideoRequest) -> dict[str, Any]:
    if request.prompt_ir is not None:
        return compile_request_ir(request)
    prompt = compile_video_prompt(request)
    return {"compiledBy": "video-prompt-compiler", "compilerVersion": "1",
            "sourceIntent": sha256_canonical(request.model_dump(mode='json', by_alias=True)),
            "prompt": prompt, "promptFingerprint": sha256_canonical(prompt)}
