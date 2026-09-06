"""Regression for actual S2 reading long production directions aloud."""
import re
import pytest
from test_coordinated_performance import phrase_request
from drama_plugin.audio.video_conditioning import condition_audio_on_video
from drama_plugin.providers.speech.fish_audio import compile_fish_tts_payload

def test_compact_phrases_preserve_local_actions_without_audit_prose():
    request, _ = phrase_request()
    brief = request.audio_performance_brief
    assert brief is not None
    payload = compile_fish_tts_payload(exact_text=request.exact_text, reference_id='test', mode='directed', speed=1, volume=0, performance_brief=brief, compact_phrases=True)
    assert re.sub(r'\[[^\]]+\]', '', payload['text']) == request.exact_text
    assert re.findall(r'\[([^\]]+)\]', payload['text']) == [x.delivery for x in brief.phrase_delivery_spans]
    assert brief.control not in payload['text']
    assert brief.control and brief.articulation and brief.performance_boundaries
    # Legacy mode remains explicit and unchanged; no silent fingerprint upgrade.
    old = compile_fish_tts_payload(exact_text=request.exact_text, reference_id='test', mode='directed', speed=1, volume=0, performance_brief=brief)
    assert brief.control in old['text']
    assert payload != old

def test_compact_cue_requires_authored_short_scope():
    request, _ = phrase_request()
    brief = request.audio_performance_brief
    assert brief is not None
    span = brief.phrase_delivery_spans[0].model_copy(update={'delivery':'x'*81})
    oversized = brief.model_copy(update={'phrase_delivery_spans':(span,)})
    with pytest.raises(ValueError, match='at most 80'):
        compile_fish_tts_payload(exact_text=request.exact_text, reference_id='test', mode='directed', speed=1, volume=0, performance_brief=oversized, compact_phrases=True)
    with pytest.raises(ValueError, match='requires authored'):
        compile_fish_tts_payload(exact_text=request.exact_text, reference_id='test', mode='directed', speed=1, volume=0, compact_phrases=True)

def test_compact_render_version_survives_video_conditioning():
    request, args = phrase_request()
    request.material_render_parameters={'performanceRendering':'PHRASE_CUES_V2'}
    args['base_request']=request
    final=condition_audio_on_video(**args)
    assert final.material_render_parameters==request.material_render_parameters
    assert final.audio_performance_brief==request.audio_performance_brief
