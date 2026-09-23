"""Compile authored video facts and constraints without inventing creative decisions."""
from drama_plugin.contracts.base import canonical_json, sha256_canonical
from drama_plugin.contracts.video import VideoRequest

def compile_video_prompt(r: VideoRequest) -> str:
    """Lossless structural projection. No LLM rewrite, vendor-owned characters or style."""
    p = r.continuity
    facts = {k: v for k, v in p.model_dump(mode='json', by_alias=True).items() if k in {
        'characters', 'locationIdentity', 'timeOfDay', 'weather', 'lighting', 'style', 'colorLanguage', 'lensLanguage'}}
    facts['style'] = {k: v for k, v in facts['style'].items() if k not in {'revision', 'castingCriteria'}}
    labels = [{'slot': slot, 'semantics': list(x.semantics)} for slot, x in
              [('first_frame', r.first_frame), ('last_frame', r.last_frame)] if x]
    for kind, refs in [('image', r.reference_images), ('video', r.reference_videos), ('audio', r.reference_audios)]:
        labels.extend({'slot': f'reference_{kind}_{i + 1}', 'semantics': list(x.semantics)} for i, x in enumerate(refs))
    from drama_plugin.visual.payload_scope import review_compiled
    return review_compiled((r.prompt + ('\nNegative constraints: ' + r.negative_prompt if r.negative_prompt else '')
            + '\nCanonical continuity (preserve exactly): ' + canonical_json(facts)
            + ('\nReference roles: ' + canonical_json(labels) if labels else '')), 'VIDEO', audio=r.native_audio)



def prompt_compilation(request: VideoRequest) -> dict[str, str]:
    prompt = compile_video_prompt(request)
    return {"compiledBy": "video-prompt-compiler", "compilerVersion": "1",
            "sourceIntent": sha256_canonical(request.model_dump(mode='json', by_alias=True)),
            "prompt": prompt, "promptFingerprint": sha256_canonical(prompt)}
