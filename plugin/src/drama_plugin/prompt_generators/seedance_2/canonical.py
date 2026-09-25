"""HTTP cinematic source gate. Checks source facts; never writes a prompt."""
from typing import Any
from drama_plugin.contracts.base import dump_contract
from drama_plugin.visual.cinematic import verify_frozen
from drama_plugin.hosts.cinematic_projection import executable, prose, source_audio


def verify_cinematic(r: Any, compilation: dict[str, Any]) -> None:
    spec = verify_frozen(r.frozen_creative['cinematic_direction'])
    v = r.video_request
    if source_audio(spec, r.sound) != v.native_audio:
        raise ValueError('DIRECTOR_AUDIO_INTENT_CHANGED')
    ir = compilation['ir']
    if ir['task']['clip_id'] != r.target_id:
        raise ValueError('VISUAL_PROMPT_IR_CLIP_CHANGED')
    temporal = ir['video_temporal']
    if temporal['start_state']['text'] != spec.opening_state or temporal['end_state']['text'] != spec.ending_state:
        raise ValueError('VISUAL_PROMPT_IR_ENDPOINT_CHANGED')
    # Inspect complete source atoms before syntax substitution (actor tags), and
    # require a receipt for every such atom. This is not a second final serializer.
    covered = {c['obligation_id'] for c in compilation['coverage']}
    facts = [a['text'] for a in compilation['atoms'] if a['obligation_id'] in covered]
    if r.authority_context is not None:
        from drama_plugin.hosts.specialized_asset import validate_authority_context
        validate_authority_context(r.authority_context, r.frozen_creative['cinematic_direction'])
        if r.authority_context['workId'] != spec.work_id:
            raise ValueError('MOVIE_VISUAL_AUTHORITY_MISMATCH')
        if any(row['executableSemantic'] not in '\n'.join(facts) for row in r.authority_context['assets']):
            raise ValueError('ASSET_EXECUTABLE_SEMANTICS_MISSING')
    raw = dump_contract(spec)
    for beat in raw['performance']['beats']:
        text = prose(executable({k: value for k, value in beat.items() if k not in ('start', 'end', 'kind')}))
        timing = f"{beat['start']:g}–{beat['end']:g}s"
        if not any(text in fact and timing in fact for fact in facts):
            raise ValueError('UNRESOLVED:clip-decomposition:CANONICAL_TIMED_ACTION_MISSING')
    # Sections must already be projected by their owners. No fallback uses the
    # generic canonical serializer as a production prompt.
    for key in ('visualBible', 'cinematography', 'lighting', 'stabilityContract', 'behaviorAnchor', 'secondaryMotion', 'environmentInteraction'):
        value = executable(raw.get(key))
        if value and prose(value) not in '\n'.join(facts):
            raise ValueError('UNRESOLVED:professional-owner:CANONICAL_SECTION_MISSING:' + key)
    bindings = v.prompt_projection.audio if v.prompt_projection else ()
    audio_facts = temporal['audio_requirements']
    if sum(binding.kind == 'DIALOGUE' for binding in bindings) != len(spec.dialogue):
        raise ValueError('UNRESOLVED:dialogue-design:UNAPPROVED_DIALOGUE')
    for dialogue in spec.dialogue:
        exact = dialogue.text if dialogue.text_range is None else dialogue.text[dialogue.text_range[0]:dialogue.text_range[1]]
        matches = [binding for binding in bindings if binding.kind == 'DIALOGUE'
                   and binding.speaker == dialogue.speaker_key
                   and binding.timing == f'{dialogue.start:g}–{dialogue.end:g}s'
                   and any(binding.path == f'video.audio_requirements[{i}]' and fact['text'] == exact
                           for i, fact in enumerate(audio_facts))]
        if len(matches) != 1:
            raise ValueError('UNRESOLVED:dialogue-design:CANONICAL_DIALOGUE_BINDING_MISSING')
    for reference in spec.reference_requirements:
        duty = next((d for d in r.reference_duties if (d.role, d.subject) == (reference.role, reference.subject)), None)
        if reference.necessity == 'REQUIRED' and duty is None:
            raise ValueError('REQUIRED_REFERENCE_UNFULFILLED')
        if duty is not None:
            if duty.status == 'EQUIVALENT':
                if duty.equivalent_text not in '\n'.join(facts):
                    raise ValueError('REFERENCE_SUBSTITUTE_NOT_COVERED')
            elif not any(s['media_id'] == duty.media_id for s in compilation['input_slots']):
                raise ValueError('REFERENCE_DUTY_INPUT_MISSING')
