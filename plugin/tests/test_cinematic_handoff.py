"""Traceability, selection and authority safeguards; no literary keyword scoring."""
from copy import deepcopy
import hashlib
import importlib.util

import pytest

from test_meta_dramaturgy import meta_ledger
from test_screenplay_incubation import SKILL, checker

spec = importlib.util.spec_from_file_location('handoff', SKILL / 'scripts/check_handoff.py')
assert spec and spec.loader
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)


def intents():
    return [dict(id=kind, sceneIds=['s1'], kind=kind, priority=priority,
                 meaning='Experience the local action', why='A choice changes', source='frozen scene/anchor')
            for kind, priority in [('opening','MUST'), ('closing','MUST'), ('subjective','MUST'),
                                    ('emphasis','SHOULD'), ('suggestion','FREE')]]


def shots():
    return [dict(id='p1', sceneId='s1', action='act then respond')]


def assessments():
    return [dict(intentId=i['id'], status='PASS', shotIds=['p1'], evidence='The planned action carries the choice') for i in intents()]


def test_cinematic_intent_has_priority():
    items = intents(); assert handoff.check_intents(items) == []
    del items[0]['priority']
    assert handoff.check_intents(items)


def test_must_intent_cannot_be_silently_dropped():
    rows = handoff.review_intents(intents(), shots(), assessments()[1:])
    assert rows[0]['status'] == 'INTENT_LOSS' and rows[0]['blocking']
    a = assessments(); a[0]['status'] = 'N/A'
    assert handoff.review_intents(intents(), shots(), a)[0]['blocking']


@pytest.mark.parametrize('idx', [0, 3])
def test_must_and_should_allow_alternate_interpretation(idx):
    a = assessments(); a[idx].update(status='ACCEPTABLE_INTERPRETATION', evidence='A different visible action retains the same purpose')
    row = handoff.review_intents(intents(), shots(), a)[idx]
    assert row['status'] == 'ACCEPTABLE_INTERPRETATION' and not row['blocking']


def test_free_intent_does_not_block_shot_plan():
    row = handoff.review_intents(intents(), shots(), assessments()[:-1])[-1]
    assert row['status'] == 'N/A' and not row['blocking'] and not row['reviewRequired']


@pytest.mark.parametrize('kind', ['opening','closing','subjective'])
def test_boundary_and_subjective_intent_reaches_shot_context(kind):
    scene = handoff.scene_handoff(checker.project(meta_ledger(), scene_id='s1'), intents())
    context = handoff.shot_context(scene, intent_ids=[kind], character_ids=['speaker:one'],
                                    state_keys=['place'], fact_ids=['event'], action='local action')
    assert context['cinematicIntent'] == [next(i for i in intents() if i['id'] == kind)]
    assert scene['cinematicIntent'] == intents()  # selection cannot erase group obligations


def test_shot_plan_does_not_receive_irrelevant_global_state():
    b = meta_ledger()
    scene = handoff.scene_handoff(checker.project(b, scene_id='s1'), intents())
    scene['unrelatedFuture'] = {'ending': 'global secret'}
    context = handoff.shot_context(scene, intent_ids=['opening'], character_ids=['speaker:one'],
                                   state_keys=['place'], fact_ids=['event'], action='receive evidence')
    assert 'unrelatedFuture' not in context and 'activeSetups' not in context
    assert set(context['characters']) == {'speaker:one'}
    assert context['knowledgeAtEntry'] == {'speaker:one': []}
    assert context['receiptsWithinScene'][0]['beforeBeat'] == 2
    with pytest.raises(ValueError, match='Unknown intent'):
        handoff.shot_context(scene, intent_ids=['remote'], character_ids=[], state_keys=[], fact_ids=[], action='act')


def test_scene_selection_does_not_take_another_episode_boundary():
    scene = checker.project(meta_ledger(), scene_id='s2')
    assert handoff.scene_handoff(scene, intents())['cinematicIntent'] == []


def test_intent_loss_routes_to_shot_revision():
    row = handoff.review_intents(intents(), shots(), [])[0]
    assert row['owner'] == 'SHOT_PLANNING'
    a = assessments(); a[0].update(status='CONFLICT', evidence='Contradicts established historical boundary')
    assert handoff.review_intents(intents(), shots(), a)[0]['blocking']


def test_review_cannot_pass_without_implementation_evidence():
    a = assessments(); a[0]['shotIds'] = []
    assert handoff.review_intents(intents(), shots(), a)[0]['status'] == 'INTENT_LOSS'
    a[0]['shotIds'] = ['unrelated']
    with pytest.raises(ValueError): handoff.review_intents(intents(), shots(), a)


def epilogue_fixture():
    body, closing = 'A complete frozen dramatic body.', 'The final action.'
    epi = dict(placement='AFTER_DRAMA_END', boundary='Separate supplement after end',
               bodySha256=hashlib.sha256(body.encode()).hexdigest(), closingSha256=hashlib.sha256(closing.encode()).hexdigest(),
               items=[dict(claimId='c', text='A concise contextual fact.', certainty='Confirmed', textForm='paraphrase')])
    claims = {'c': dict(certainty='Confirmed', evidence=[dict(source='r', locator='record, entry')])}
    return epi, dict(body=body, closing=closing, claims=claims, sources={'r': {'title':'Historical record'}})


def test_historical_epilogue_is_outside_screenplay_body():
    epi, ctx = epilogue_fixture(); assert handoff.check_epilogue(epi, **ctx) == []
    epi['placement'] = 'CLOSING_DIALOGUE'
    assert handoff.check_epilogue(epi, **ctx)
    epi['placement'] = 'AFTER_DRAMA_END'; ctx['body'] += 'added explanation'
    assert handoff.check_epilogue(epi, **ctx)


def test_historical_epilogue_requires_historical_grounding():
    epi, ctx = epilogue_fixture(); ctx['claims']['c']['evidence'] = []
    assert handoff.check_epilogue(epi, **ctx)


def test_historical_epilogue_does_not_promote_reconstruction_to_fact():
    epi, ctx = epilogue_fixture(); ctx['claims']['c']['certainty'] = 'Dramatic Reconstruction'
    assert handoff.check_epilogue(epi, **ctx)
    epi['items'][0].update(certainty='Dramatic Reconstruction', textForm='reconstruction')
    assert handoff.check_epilogue(epi, **ctx) == []


def test_epilogue_original_requires_exact_excerpt():
    epi, ctx = epilogue_fixture(); epi['items'][0]['textForm'] = 'original'
    assert handoff.check_epilogue(epi, **ctx)
    ctx['claims']['c']['evidence'][0]['excerpt'] = epi['items'][0]['text']
    assert handoff.check_epilogue(epi, **ctx) == []


def test_fixture_not_in_production_rules():
    entities = ('莱特','威尔伯','奥维尔','泰勒','丹尼尔斯','Wilbur','Orville','Kitty Hawk','1901','1902','1903','飞机')
    for name in ('cinematic-screenplay-incubation','scene-development','shot-design'):
        for p in (SKILL.parent / name).rglob('*'):
            if p.is_file() and p.suffix in {'.md','.yaml','.py'}:
                assert not any(e in p.read_text() for e in entities), p


def test_handoff_does_not_mutate_frozen_scene_or_intent():
    scene = checker.project(meta_ledger(), scene_id='s1'); before = deepcopy(scene)
    original = intents(); result = handoff.scene_handoff(scene, original)
    result['cinematicIntent'][0]['meaning'] = 'downstream mutation'
    assert scene == before and original == intents()
