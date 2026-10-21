"""Target projection regression: review Canon and approved speech stay distinct."""
from copy import deepcopy

import pytest

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.production_language import SpeechLanguageAuthorization
from drama_plugin.creative_engine.contracts import Authority, Dialogue, Kind, SceneBody, SourceBody
from drama_plugin.creative_engine.contracts import DesignBody
from drama_plugin.creative_engine.sources import NativeCreativeSources
from drama_plugin.creative_engine.store import CreativeVersionStore
from drama_plugin.hosts.production_language import ProductionLanguageHost
from drama_plugin.production_language import dialogue_review_subject, native_scene_speech
from drama_plugin.runtime.contracts import RuntimeScope
from test_production_language import fixture


def approved():
    _, _, profile, intent, line = fixture()
    intent.review_status = 'APPROVED'
    intent.approval_ref = 'technical-test-user-decision'
    line.purpose = 'PRODUCTION'
    line.semantic_intent_hash = sha256_canonical(intent)
    line.review_subject_hash = dialogue_review_subject(line)
    line.review_status = 'APPROVED'
    line.reviewer = 'technical-test-user'
    line.approval_ref = intent.approval_ref
    return SpeechLanguageAuthorization(profile=profile, intent=intent, line=line)


def project(a, rows=None):
    return native_scene_speech(rows or [dict(id=a.line.line_id, speakerKey='c', text='对不起。')],
        [a], a.profile, work_id='work-test', scene_id='s', spoken_language='ru')


@pytest.mark.parametrize('mutation,error', [
    ('review', 'APPROVED_PRODUCTION_DIALOGUE_REQUIRED'),
    ('stale', 'STALE_LOCALIZATION_BINDING'),
    ('speaker', 'CANON_LOCALIZATION_BINDING_MISMATCH'),
    ('scene', 'CANON_LOCALIZATION_BINDING_MISMATCH'),
    ('canon', 'CANON_LOCALIZATION_BINDING_MISMATCH'),
])
def test_native_speech_rejects_stale_unapproved_or_wrong_owner(mutation, error):
    a = approved()
    rows = [dict(id=a.line.line_id, speakerKey='c', text='对不起。')]
    if mutation == 'review': a.line.review_status = 'CANDIDATE'
    elif mutation == 'stale': a.line.language_profile_hash = '0' * 64
    elif mutation == 'speaker': rows[0]['speakerKey'] = 'other'
    elif mutation == 'scene':
        a.line.scene_id = a.intent.scene_id = 'other'
        a.line.semantic_intent_hash = sha256_canonical(a.intent)
        a.line.review_subject_hash = dialogue_review_subject(a.line)
    else: rows[0]['text'] = '新词'
    with pytest.raises(ValueError, match=error): project(a, rows)


def test_unbound_lines_cannot_inherit_production_language():
    a = approved()
    rows = [dict(id=a.line.line_id, speakerKey='c', text='对不起。'),
            dict(id='future', speakerKey='c', text='尚未批准翻译')]
    out = project(a, rows)
    assert out[0]['text'] == 'Простите.' and out[0]['language'] == 'ru'
    assert out[1]['text'] == rows[1]['text'] and out[1]['language'] is None
    with pytest.raises(ValueError, match='DUPLICATE_LOCALIZATION_BINDING'):
        native_scene_speech(rows, [a, a], a.profile, work_id='work-test', scene_id='s', spoken_language='ru')


def test_native_unit_rejects_unbound_spoken_language():
    from types import SimpleNamespace
    from drama_plugin.generation.audio import AudioPerformanceAssembler
    from drama_plugin.generation.sources import SelectedValue
    from drama_plugin.production.contracts import DomainReference
    from drama_plugin.production.sources import OwnedSource
    value = dict(id='unbound', speakerKey='c', text='尚未批准翻译', language=None)
    source = OwnedSource('scene', 's', 1, dict(spokenContent=[value]))
    selection = DomainReference(domain='SOUND', reference=source.reference('spokenContent', '0'))
    task = SimpleNamespace(unit=SimpleNamespace(spoken_ids=('unbound',), execution_context=None),
                           profile=object(), native_audio='REQUIRED')
    result = AudioPerformanceAssembler().assemble(None, task, (SelectedValue(selection, value),))
    assert result.plan is None and result.diagnostics[0].owner == 'production-language'


def test_actual_target_projection_and_recovery_preserve_canon(tmp_path):
    a = approved()
    versions = CreativeVersionStore(tmp_path)
    host = ProductionLanguageHost(tmp_path)
    host.store._write(host.store._path('work-language', 'work-test'), dump_contract(a.profile))
    pin = versions.objects.put('approved-test-rendition', dump_contract(a))
    source = versions.write(writer=Authority.SOURCE, kind=Kind.SOURCE,
        scope=RuntimeScope(work_id='work-test'), body=SourceBody(goal='technical test', text='original', spoken_language='ru'),
        sources=(), operation='source')
    old = SceneBody(scene_text='对不起。', dialogue=(Dialogue(id=a.line.line_id, speaker='c', text='对不起。'),))
    # Preserve historical empty-field serialization, hence frozen K01 seals.
    assert set(old.model_dump(by_alias=True)) == {'sceneText', 'dialogue'}
    body = old.model_copy(update={'production_dialogue_refs': (pin,)})
    scene = versions.write(writer=Authority.CANON, kind=Kind.SCENE,
        scope=RuntimeScope(work_id='work-test', scene_id='s'), body=body, sources=(source,), operation='scene')
    sources = NativeCreativeSources(versions, (source, scene))
    result = sources.project(versions.resolve(scene))
    assert result.body['content']['spokenContent'][0]['text'] == 'Простите.'
    assert versions.resolve(scene).body.dialogue[0].text == '对不起。'
    # Recover without a cached projection or a current Shot.
    for path in versions.index.glob('projection-*'): path.unlink()
    assert NativeCreativeSources(versions).exact_projection(result.reference()).ref() == scene


def test_received_response_judgment_keeps_its_dpd_owner():
    response = dict(actionRef='spoken:a', responseRef='spoken:b', expectedResponse='accept',
                    interpretation='received refusal', transitionReason='change tactic', nextBeatId='next')
    assert DesignBody(domain='PERFORMANCE', facts={'beats': [{'responseInterpretations': [response]}]})
    with pytest.raises(ValueError, match='authority violation'):
        DesignBody(domain='PERFORMANCE', facts={'interpretation': 'Work interpretation'})
    with pytest.raises(ValueError, match='authority violation'):
        DesignBody(domain='WORLD', facts={'beats': [{'responseInterpretations': [response]}]})
    with pytest.raises(ValueError):
        DesignBody(domain='PERFORMANCE', facts={'beats': [{'responseInterpretations': [{'interpretation': 'untyped'}]}]})


def test_language_pointer_does_not_replace_asset_identity(tmp_path):
    from types import SimpleNamespace
    from drama_plugin.creative_engine.contracts import WorkBody, ScriptBody, CanonDraft
    from drama_plugin.film.contracts import FilmCanon, CanonScene
    from drama_plugin.professional_design.asset_sequence import SpecializedAssetSequence
    versions = CreativeVersionStore(tmp_path)
    a = approved()
    pin = versions.objects.put('test-language', dump_contract(a))
    scene = SceneBody(scene_text='对不起。', dialogue=(Dialogue(id='line-test', speaker='c', text='对不起。'),))
    work = WorkBody(interpretation='test apology', dramatic_intent='test reply', character_meaning='test neighbors')
    script = ScriptBody(screenplay='test apology and reply')
    canon = FilmCanon(work=work, script=script, scenes=(CanonScene(scene_id='s', scene=scene),))
    ref = versions.objects.put('test-narrative', dict(schemaVersion='specialized-asset-narrative-v1',
        workId='work-test', canon=dump_contract(canon)))
    sequence = SpecializedAssetSequence(versions.objects, None, None)
    current = scene.model_copy(update={'production_dialogue_refs': (pin,)})
    request = SimpleNamespace(scope=RuntimeScope(work_id='work-test', scene_id='s'),
        canon=CanonDraft(work=work, script=script, scene=current))
    assert sequence._narrative(ref, request) == canon
    request.canon = request.canon.model_copy(update={'scene': current.model_copy(update={'scene_text': 'changed action'})})
    with pytest.raises(ValueError, match='ASSET_NARRATIVE_CANON_MISMATCH'):
        sequence._narrative(ref, request)
