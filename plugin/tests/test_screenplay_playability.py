from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re

import pytest
from pydantic import ValidationError

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.dpd import BeatDPD, LineDPD, SceneDPD
from drama_plugin.contracts.screenplay_playability import BeatPlayability
from drama_plugin.dpd import compose_dpd
from drama_plugin.screenplay_playability import (
    exact_text_hash, map_screenplay_performance, validate_line_playability,
)

FIXTURE = Path(__file__).parent / 'fixtures/screenplay_r2'


def source(index=1):
    return json.loads((FIXTURE / 'performance-sidecar.json').read_text())['scenes'][index]


def mapped(case):
    return map_screenplay_performance(case['source'], SceneDPD.model_validate(case['sceneDpd']),
                                     [BeatDPD.model_validate(b) for b in case['beats']],
                                     [LineDPD.model_validate(l) for l in case['lines']])


def repin(case):
    fp = sha256_canonical(case['source'])
    case['sceneDpd']['sourceFingerprint'] = fp
    for beat in case['beats']:
        beat['playability']['sourceSceneHash'] = fp


@pytest.mark.parametrize('index', [0, 1, 2])
def test_rewritten_scenes_are_source_bound_playable_and_do_not_mutate(index):
    case = source(index)
    before = deepcopy(case)
    result = mapped(case)
    assert case == before
    assert result['spokenContent'] == case['source']['content']['spokenContent']
    result['spokenContent'][0]['text'] = 'attempted downstream rewrite'
    assert case == before
    assert all(b.playability.state_scope == 'CURRENT_BEAT' for b in result['beats'])


def test_old_fragment_is_an_ambiguous_dialogue_regression_even_with_intent_metadata():
    case = source()
    case['source']['content']['spokenContent'][0]['text'] = '妈妈……先生，妈妈……'
    case['lines'][0]['playability']['sourceTextHash'] = exact_text_hash('妈妈……先生，妈妈……')
    repin(case)
    with pytest.raises(ValueError, match='AMBIGUOUS_DIALOGUE'):
        mapped(case)


def test_explicit_unintelligibility_requires_its_own_dramatic_purpose():
    case = source()
    line = case['source']['content']['spokenContent'][0]
    line['text'] = '妈妈……先生，妈妈……'
    witness = case['lines'][0]['playability']
    witness.update(sourceTextHash=exact_text_hash(line['text']), fragmentation='INTENTIONALLY_UNINTELLIGIBLE', dramaticPurpose='让观众听见请求无法成句；不适用于须传达求助内容的 S02 候选。')
    repin(case)
    assert mapped(case)
    witness['dramaticPurpose'] = None
    with pytest.raises(ValueError, match='fragmentation requires'):
        mapped(case)


@pytest.mark.parametrize(('field', 'value', 'error'), [
    ('text', '先生，请您跟我去。', 'EXACT_DIALOGUE_TEXT_MISMATCH'),
    ('speakerKey', '男人', 'DIALOGUE_SPEAKER_MISMATCH'),
    ('target', '另一个行人', 'DIALOGUE_TARGET_MISMATCH'),
    ('intent', '向观众介绍故事', 'DIALOGUE_INTENT_MISMATCH'),
    ('performanceIntent', '', 'source dialogue delivery'),
])
def test_source_change_cannot_be_silently_projected(field, value, error):
    case = source()
    case['source']['content']['spokenContent'][0][field] = value
    repin(case)  # Even a refreshed Scene pin cannot conceal a stale line witness.
    with pytest.raises(ValueError, match=error):
        mapped(case)


@pytest.mark.parametrize('missing', ['objective', 'interactionTarget', 'tactic'])
def test_important_actor_task_cannot_inherit_a_missing_local_decision(missing):
    case = source()
    case['beats'][0]['direction'].pop(missing)
    with pytest.raises(ValueError, match='UNRESOLVED'):
        mapped(case)


@pytest.mark.parametrize('emotion', ['sad', 'alienated', '悲伤', '绝望'])
def test_abstract_emotion_is_not_objective(emotion):
    case = source()
    case['beats'][0]['direction']['objective'] = emotion
    with pytest.raises(ValueError, match='character objective'):
        mapped(case)


def test_missing_action_or_invented_action_returns_to_author_not_generator():
    case = source()
    case['beats'][0]['playability']['playableActions'] = []
    with pytest.raises(ValidationError):
        mapped(case)
    case = source()
    case['beats'][0]['playability']['playableActions'][0]['behavior'] = '攥拳，低头，眼眶泛红'
    with pytest.raises(ValueError, match='return to author'):
        mapped(case)


def test_emotion_alone_is_not_action_even_if_the_source_contains_it():
    case = source()
    case['source']['content']['screenplayAction'] += '\n悲伤'
    case['beats'][0]['playability']['playableActions'][0]['behavior'] = '悲伤'
    repin(case)
    with pytest.raises(ValueError, match='playable action'):
        mapped(case)


@pytest.mark.parametrize('key', ['identity', 'camera', 'lighting', 'dialogue', 'voiceIdentity'])
def test_playability_cannot_add_other_owners_structured_authority(key):
    witness = source()['beats'][0]['playability']
    witness[key] = {'replacement': 'not permitted'}
    with pytest.raises(ValidationError, match='Extra inputs'):
        BeatPlayability.model_validate(witness)


def test_performance_state_is_local_not_character_identity():
    case = source()
    case['beats'][0]['playability']['stateScope'] = 'CHARACTER_IDENTITY'
    with pytest.raises(ValidationError):
        mapped(case)


def test_no_line_concatenation_or_missing_line_coverage():
    case = source()
    case['lines'].pop()
    with pytest.raises(ValueError, match='one exact line binding'):
        mapped(case)
    case = source()
    case['lines'].append(deepcopy(case['lines'][0]))
    with pytest.raises(ValueError, match='one exact line binding'):
        mapped(case)


def test_performance_cannot_edit_dialogue_after_projection():
    case = source()
    dpd = mapped(case)['dpds'][0]
    mutated = deepcopy(case['source'])
    mutated['content']['spokenContent'][0]['text'] += '我给你解释一下。'
    with pytest.raises(ValueError, match='STALE_SCREENPLAY'):
        validate_line_playability(mutated, dpd)


def test_legacy_snapshot_is_readable_but_not_eligible_for_new_production():
    case = source()
    for b in case['beats']:
        b.pop('playability')
    for line in case['lines']:
        line.pop('playability')
    beat = BeatDPD.model_validate(case['beats'][0])
    assert 'playability' not in dump_contract(beat)
    assert compose_dpd(SceneDPD.model_validate(case['sceneDpd']), beat, LineDPD.model_validate(case['lines'][0]))
    with pytest.raises(ValueError, match='UNRESOLVED'):
        mapped(case)


def test_screenplay_source_and_sidecar_match_and_protected_scenes_are_byte_identical():
    old = (FIXTURE / '04-screenplay-r1.md').read_bytes()
    new = (FIXTURE / '04-screenplay-r2.md').read_bytes()
    pack = json.loads((FIXTURE / 'performance-sidecar.json').read_text())
    assert sha256(old).hexdigest() == '11d0f82f18f7defa31a9a4abe0de12e061cdc62183e3744c2b607dc1c19428e1'
    suffix = b'## S04'
    assert old[old.index(suffix):] == new[new.index(suffix):]
    assert sha256(new).hexdigest() == pack['screenplaySha256']
    assert sha256(old[old.index(suffix):]).hexdigest() == pack['protectedS04S16Sha256']
    for case in pack['scenes']:
        sid = case['source']['id']
        section = re.search(r'## ' + sid + r'.*?(?=\n## S|\Z)', new.decode(), re.S).group(0)
        spoken = re.findall(r'^(工程师|朋友|男人|女孩)：(.+)$', section, re.M)
        assert spoken == [(l['speakerKey'], l['text']) for l in case['source']['content']['spokenContent']]
    assert '妈妈……先生，妈妈……' not in new[:new.index(suffix)].decode()
    assert '这是刚才没有放到女孩肩上的手' not in new[:new.index(suffix)].decode()


async def test_formal_book_entry_rejects_missing_playability_without_legacy_fallback(tmp_path):
    from formal_performance_helpers import formal_case
    case = await formal_case(tmp_path / 'formal.json')
    witness = case['formal_source']
    witness.validate(case['inventory'], case['directions'], case['dpds'], case['scene_dpds'], case['source_hash'], dramaturgy_reviews=case['dramaturgy_reviews'])
    key, snapshot = next((k, d) for k, d in case['dpds'].items() if hasattr(d, 'effective'))
    case['dpds'][key] = compose_dpd(snapshot.scene, snapshot.beat.model_copy(update={'playability': None}), snapshot.line)
    with pytest.raises(ValueError, match='UNRESOLVED'):
        witness.validate(case['inventory'], case['directions'], case['dpds'], case['scene_dpds'], case['source_hash'], dramaturgy_reviews=case['dramaturgy_reviews'])


def test_line_override_cannot_replace_actor_objective_with_emotion():
    case = source()
    case['lines'][0]['direction']['objective'] = 'sad'
    with pytest.raises(ValueError, match='effective character objective'):
        mapped(case)


def test_revalidation_rejects_a_forged_fragment_witness():
    case = source()
    dpd = mapped(case)['dpds'][0]
    bad_line = dpd.line.model_copy(update={'playability': dpd.line.playability.model_copy(update={'dramatic_purpose': None})})
    forged = compose_dpd(dpd.scene, dpd.beat, bad_line)
    with pytest.raises(ValueError, match='fragmentation requires'):
        validate_line_playability(case['source'], forged)


@pytest.mark.parametrize('mutation', [None, 'target', 'text'])
def test_cinematic_handoff_pins_original_dialogue_even_if_audio_and_spec_agree(mutation):
    from performance_direction_helpers import make_case
    from test_cinematic_direction import example
    from drama_plugin.contracts.cinematic import CinematicShotSpec
    from drama_plugin.contracts.screenplay_playability import LinePlayability
    from drama_plugin.performance_direction import attach_cinematic_performance
    from drama_plugin.visual.performance import fingerprint_visual_projection
    from drama_plugin.audio.projection import fingerprint_audio_projection
    c = make_case('decision', 'live_action')
    line = c['dpd'].line.model_copy(update={'playability': LinePlayability(
        source_text_hash=exact_text_hash(c['spoken']['text']), literal_meaning='Review the evacuation route again',
        speakability_review='Direct request to the current partner, short enough for the current state.', fragmentation='CONTINUOUS')})
    c['dpd'] = compose_dpd(c['dpd'].scene, c['dpd'].beat, line)
    c['intent'] = c['intent'].model_copy(update={'dpd_fingerprints': (c['dpd'].fingerprint,)})
    for channel, fingerprint in [('visual', fingerprint_visual_projection), ('audio', fingerprint_audio_projection)]:
        brief = c[channel]
        projection = brief.director_performance.model_copy(update={'director_intent_fingerprint': sha256_canonical(c['intent'])})
        brief = brief.model_copy(update={'dpd_fingerprint': c['dpd'].fingerprint, 'director_performance': projection})
        c[channel] = brief.model_copy(update={'fingerprint': fingerprint(brief)})
    spec, _, _ = example()
    payload = dump_contract(spec)
    payload.update(sceneId=c['dpd'].effective.scene_id, shotId=c['visual'].shot_id)
    payload['performance'].update(objective=c['dpd'].effective.objective, interactionTarget=c['dpd'].effective.interaction_target)
    payload['dialogue'][0].update(spokenContentId=c['audio'].spoken_content_id,
        speakerKey=c['audio'].speaker_key, text=c['spoken']['text'], target=c['dpd'].effective.interaction_target)
    if mutation == 'target':
        payload['dialogue'][0]['target'] = 'a different listener'
    if mutation == 'text':
        payload['dialogue'][0]['text'] += '这是新增解释。'
        c['audio'] = c['audio'].model_copy(update={'text_fingerprint': exact_text_hash(payload['dialogue'][0]['text'])})
        c['audio'] = c['audio'].model_copy(update={'fingerprint': fingerprint_audio_projection(c['audio'])})
    args = dict(dpd=c['dpd'], intent=c['intent'], visual=c['visual'], audio=c['audio'], current=c['current'])
    if mutation:
        with pytest.raises(ValueError, match='SCREENPLAY_DIALOGUE_AUTHORITY_MISMATCH'):
            attach_cinematic_performance(CinematicShotSpec.model_validate(payload), **args)
    else:
        assert attach_cinematic_performance(CinematicShotSpec.model_validate(payload), **args).dialogue[0].text == c['spoken']['text']
