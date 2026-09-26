from __future__ import annotations
from copy import deepcopy
from typing import Any
import pytest
from drama_plugin.scene_dramaturgy import source_dramaturgy
from r3b_r_helpers import load_case, repin, result, codes

LID = 'S03-L1'


def case(target: str = '自己', text: str = '就是今天。') -> dict[str, Any]:
    e = load_case(2)
    scene = e['source']; scene['content']['spokenContent'][0].update(target=target, text=text)
    cs = scene['content']['dramaturgy']['carriers']
    cs[0]['target'] = target
    cs[3]['target'] = target
    e['dpds'][LID]['beat']['direction']['interactionTarget'] = target
    repin(e)
    return e


@pytest.mark.parametrize('target', ['自己', 'SELF', '男人'])
@pytest.mark.parametrize('text', ['就是今天。', '走。', '别回头。'])
def test_self_directed_action_with_reviewed_own_continuation(target: str, text: str) -> None:
    e = case(target, text); before = deepcopy(e)
    receipt = result(e)
    assert receipt['status'] == 'PASS'
    assert receipt['causalCoverage'] == []  # No interpersonal listener invented.
    assert e == before


@pytest.mark.parametrize('target', ['母亲', 'AUDIENCE', 'VOICE_OVER', 'DIRECT_ADDRESS'])
def test_same_words_addressed_elsewhere_do_not_inherit_self_exception(target: str) -> None:
    assert 'IMPORTANT_ACTION_RESPONSE_MISSING' in codes(case(target))


@pytest.mark.parametrize('attack', ['no-dpd', 'same-carrier', 'review-does-not-cover', 'review-concern', 'wrong-target', 'no-task', 'unrelated-cause'])
def test_self_is_not_an_unconditional_causal_exemption(attack: str) -> None:
    e = case()
    if attack == 'no-dpd': del e['dpds'][LID]
    elif attack == 'same-carrier':
        # Reusing the utterance itself is not a subsequent continuation.
        e['source']['content']['dramaturgy']['carriers'][0]['role'] = 'AFTERMATH'
        e['dpds'][LID]['beat']['playability']['reactionCarrierRef'] = 'spoken:' + LID
        repin(e)
        e['source']['content']['dramaturgy']['carriers'][0]['role'] = 'ACTION'
        repin(e)
        with pytest.raises(ValueError, match='TRIGGER_IS_NOT_REACTION'): result(e)
        return
    elif attack == 'wrong-target': e['dpds'][LID]['beat']['direction']['interactionTarget'] = '母亲'
    elif attack == 'no-task':
        e['dpds'][LID]['beat']['direction']['objective'] = None
        with pytest.raises(ValueError, match='required effective fields missing'):
            repin(e)
        return
    elif attack == 'unrelated-cause':
        e['source']['content']['dramaturgy']['carriers'][3]['causeRef'] = 'action:180:191'
    repin(e)
    if attack == 'review-does-not-cover':
        for f in e['dramaturgyReview']['findings']:
            if f['axis'] == 'ACTION_RESPONSE_CHAIN': f['evidenceRefs'] = ['spoken:' + LID]
    elif attack == 'review-concern':
        for f in e['dramaturgyReview']['findings']:
            if f['axis'] == 'ACTION_RESPONSE_CHAIN': f['status'] = 'CONCERN'
    assert 'SELF_DIRECTED_CONTINUATION_REQUIRED' in codes(e)


def test_environment_cannot_be_response_or_self_continuation() -> None:
    e = case(); facet = e['source']['content']['dramaturgy']
    environment = facet['carriers'][4]
    environment['causeRef'] = 'spoken:' + LID
    facet['interactions'] = [{'actionRef':'spoken:' + LID, 'responseRef':environment['ref']}]
    repin(e)
    with pytest.raises(ValueError, match='STIMULUS_IS_NOT_ACTUAL_RESPONSE'):
        source_dramaturgy(e['source'])
    facet['interactions'] = []
    e['dpds'][LID]['beat']['playability']['reactionCarrierRef'] = environment['ref']
    # Cannot forge an actor for an explicitly environmental source carrier.
    with pytest.raises(ValueError):
        repin(e)
        result(e)


def test_source_environment_sound_does_not_supply_a_missing_self_dpd() -> None:
    e = case(); del e['dpds'][LID]; repin(e)
    assert 'SELF_DIRECTED_CONTINUATION_REQUIRED' in codes(e)
    assert result(e)['causalCoverage'] == []


def test_self_to_other_mutation_invalidates_old_witness_and_review() -> None:
    e = case(); old = deepcopy(e['dramaturgyReview'])
    e['source']['content']['spokenContent'][0]['target'] = '母亲'
    e['source']['content']['dramaturgy']['carriers'][0]['target'] = '母亲'
    repin(e)
    assert 'IMPORTANT_ACTION_RESPONSE_MISSING' in codes(e)
    e['dramaturgyReview'] = old
    with pytest.raises(ValueError, match='STALE_DRAMATURGY_REVIEW'): result(e)


def test_real_character_named_self_is_not_a_reflexive_alias() -> None:
    e = case('SELF'); e['source']['content']['characters'].append('SELF'); repin(e)
    assert 'IMPORTANT_ACTION_RESPONSE_MISSING' in codes(e)


@pytest.mark.parametrize(('text', 'behavior'), [('走。', 'A rises and leaves.'), ('别回头。', 'A keeps walking forward.')])
def test_self_command_can_continue_as_own_action(text: str, behavior: str) -> None:
    e = case(text=text); s=e['source']; facet=s['content']['dramaturgy']
    s['content']['spokenContent']=s['content']['spokenContent'][:1]
    s['content']['screenplayAction']=behavior
    continuation=deepcopy(facet['carriers'][3]); continuation['ref']=f'action:0:{len(behavior)}'
    continuation['causeRef']='spoken:'+LID
    facet['carriers']=[facet['carriers'][0],continuation]
    facet['information']=[]; facet['stateEvidence']=['spoken:'+LID,continuation['ref']]
    e['dpds']={LID:e['dpds'][LID]}
    e['dpds'][LID]['beat']['playability']['reactionCarrierRef']=continuation['ref']
    e['dramaturgyReview']['findings']=[f for f in e['dramaturgyReview']['findings'] if f['scope']=='SCENE']
    for f in e['dramaturgyReview']['findings']: f['evidenceRefs']=facet['stateEvidence']
    repin(e)
    assert result(e)['status']=='PASS'
    assert result(e)['causalCoverage']==[]
