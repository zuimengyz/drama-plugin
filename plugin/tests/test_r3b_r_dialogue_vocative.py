from __future__ import annotations
from copy import deepcopy
from typing import Any
import pytest
from drama_plugin.dpd import compose_dpd
from drama_plugin.screenplay_playability import validate_exact_turn
from r3b_r_helpers import load_case, repin, turn

LID = 'S02-L7-new'


def case(text: str = '先生！', action: str = 'get_attention') -> dict[str, Any]:
    e = load_case(1)
    e['source']['content']['spokenContent'][-1].update(text=text, intent=action)
    repin(e)
    return e


@pytest.mark.parametrize('text', ['先生！', '喂！', '妈妈！', '约翰！'])
@pytest.mark.parametrize('action', ['get_attention', 'call_to_target', '叫住新出现的求助对象'])
def test_explicit_current_call_to_encountered_target(text: str, action: str) -> None:
    e = case(text, action); before = deepcopy(e)
    assert validate_exact_turn(e['source'], LID, turn(e, LID))['text'] == text
    assert e == before


@pytest.mark.parametrize('action', ['ask_for_medical_help', 'persuade target to follow',
                                    'get_attention and ask for medical help', '叫住新出现的求助对象并要求同行'])
def test_vocative_cannot_convey_help_or_follow_request(action: str) -> None:
    e = case(action=action)
    with pytest.raises(ValueError, match='AMBIGUOUS_DIALOGUE'):
        validate_exact_turn(e['source'], LID, turn(e, LID))


@pytest.mark.parametrize('action', ['get_attention', 'ask_for_medical_help'])
def test_old_ambiguous_fragment_is_not_a_contextual_call(action: str) -> None:
    e = case('妈妈……先生，妈妈……', action)
    with pytest.raises(ValueError, match='AMBIGUOUS_DIALOGUE'):
        validate_exact_turn(e['source'], LID, turn(e, LID))


@pytest.mark.parametrize('attack', ['missing', 'absent', 'wrong-dpd', 'wrong-encounter', 'no-encounter', 'no-facet'])
def test_target_and_current_encounter_are_required(attack: str) -> None:
    e = case(); scene = e['source']; facet = scene['content']['dramaturgy']
    if attack == 'missing':
        scene['content']['spokenContent'][-1]['target'] = None
        next(c for c in facet['carriers'] if c['ref'] == 'spoken:' + LID)['target'] = None
        # Keep a valid old DPD to show canonical source cannot omit its target.
        from drama_plugin.contracts.base import sha256_canonical as fp
        from drama_plugin.scene_dramaturgy import scene_body_hash
        facet['sourceBodyHash'] = scene_body_hash(scene)
        d = turn(e, LID)
        assert d.beat.playability
        d = compose_dpd(d.scene.model_copy(update={'source_fingerprint': fp(scene)}),
                        d.beat.model_copy(update={'playability': d.beat.playability.model_copy(update={'source_scene_hash': fp(scene)})}), d.line)
        with pytest.raises(ValueError):
            validate_exact_turn(scene, LID, d)
        return
    if attack == 'absent': scene['content']['characters'].remove('另一行人')
    elif attack == 'wrong-encounter':
        next(c for c in facet['carriers'] if c['ref'] == 'action:368:379')['target'] = '男人'
    elif attack == 'no-encounter':
        next(c for c in facet['carriers'] if c['ref'] == 'spoken:' + LID)['causeRef'] = None
    elif attack == 'no-facet':
        scene['content'].pop('dramaturgy')
        from drama_plugin.contracts.base import sha256_canonical as fp
        d = turn(e, LID); assert d.beat.playability
        d = compose_dpd(d.scene.model_copy(update={'source_fingerprint': fp(scene)}),
                        d.beat.model_copy(update={'playability': d.beat.playability.model_copy(update={'source_scene_hash': fp(scene)})}), d.line)
        with pytest.raises(ValueError, match='AMBIGUOUS_DIALOGUE'):
            validate_exact_turn(scene, LID, d)
        return
    repin(e); d = turn(e, LID)
    if attack == 'wrong-dpd':
        d = compose_dpd(d.scene, d.beat.model_copy(update={'direction': d.beat.direction.model_copy(update={'interaction_target':'男人'})}), d.line)
    with pytest.raises(ValueError):
        validate_exact_turn(scene, LID, d)


def test_same_vocative_cannot_borrow_another_turn_or_target() -> None:
    e = case()
    e['source']['content']['spokenContent'][0].update(text='先生！', intent='get_attention')
    repin(e)
    with pytest.raises(ValueError, match='EXACT_DIALOGUE_TURN_MISMATCH'):
        validate_exact_turn(e['source'], LID, turn(e, 'S02-L1a'))
    with pytest.raises(ValueError, match='EXACT_DIALOGUE_TURN_MISMATCH'):
        validate_exact_turn(e['source'], 'S02-L1a', turn(e, LID))


def test_literal_meaning_cannot_smuggle_a_complete_request_into_call() -> None:
    e = case(); d = turn(e, LID); assert d.line.playability
    ld = d.line.model_copy(update={'playability': d.line.playability.model_copy(update={'literal_meaning':'Mother needs medical help; follow me'})})
    with pytest.raises(ValueError, match='AMBIGUOUS_DIALOGUE'):
        validate_exact_turn(e['source'], LID, compose_dpd(d.scene, d.beat, ld))
