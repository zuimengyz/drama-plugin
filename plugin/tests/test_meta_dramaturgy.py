"""Structural safeguards, not keyword scoring of literary quality."""
from copy import deepcopy
from pathlib import Path

import pytest

from test_screenplay_incubation import SKILL, checker, ledger


def meta_ledger():
    b = ledger()
    b['characters']['speaker:remote'] = {'identity': 'remote observer', 'arc': 'unrelated future'}
    first = b['sequence'][0]
    first.update(episodeId='e1', pov='speaker:one', omniscience=[], goal='test an uncertain claim', turn='evidence arrives',
                 context=dict(factIds=['event'], characterIds=['speaker:one'], relationshipIds=[], stateKeys=['place'], setupIds=[], lensIds=[]))
    second = deepcopy(first)
    second.update(id='s2', episodeId='e2', receipts=[], decisions=[], knowledgeIn={'speaker:one': ['order']})
    b['sequence'].append(second)
    remote = deepcopy(b['historicalGrounding']['claims'][0]); remote['id'] = 'remote'
    b['historicalGrounding']['claims'].append(remote)
    b['relationships'] = []
    profile = dict.fromkeys(('historicalSpan','ensembleSize','politicalComplexity','militaryScale','spatialComplexity',
                            'evidenceUncertainty','informationAsymmetry','emotionalIntensity','continuityHorizon',
                            'spectacleRequirement','dialogueDensity','subjectiveIntensity'), 'MEDIUM')
    profile['militaryScale'] = 'N/A'
    b['direction'] = {'narrativeTexture': 'derived for this case', 'meta': {
        'loadProfile': profile, 'capabilityUse': {'warDramaturgy': {'level': 'N/A', 'reason': 'no armed conflict'}},
        'narrativeAperture': dict(included=['one inquiry'], excluded=['later biography'], startState='unknown', endState='tested', selectionReason='causal completeness'),
        'povContract': dict(primaryPOV=['speaker:one'], secondaryPOV=[], audiencePrivilege='shared evidence', allowedOmniscience=[], forbiddenOmniscience=['remote.privateThought'], POVTransitionRule='return to observable shared action'),
        'subjectiveLens': dict(anchorCharacter='speaker:one', emotionalFilter='uncertainty', audienceDistance='near', allowedOmniscience=[], subjectiveMoments=[], objectiveMoments=['s1-return'])}, 'episodeArchitecture': []}
    for eid in ['e1', 'e2']:
        b['direction']['episodeArchitecture'].append(dict(id=eid, episodeJob='change an option', startState={'place':'gate'}, endState={'place':'gate'},
            tensionShape='build then reorient', majorTurn='new evidence', emotionalPeak='discovery', breathingSpace='shared work', afterEffect='new task', nextEpisodePressure='resolution' if eid=='e2' else 'test result',
            openingShotAnchor=dict(perception='unfinished action', purpose='enter the problem', derivedFrom='episode job and POV'),
            closingShotAnchor=dict(perception='completed action', purpose='show change', derivedFrom='episode outcome')))
    return b


def test_no_historical_fixture_hardcoding():
    # This is a contamination audit explicitly requested by the user, not a prose-quality test.
    entities = ('潼关','高仙芝','封常清','睢阳','张巡','颜真卿','颜季明','香积寺','李嗣业','郭子仪','安史之乱',
                '莱特','Wilbur','Orville','Kitty Hawk','1903')
    for p in SKILL.rglob('*'):
        if p.is_file() and p.suffix in {'.md','.yaml','.py'}:
            assert not any(entity in p.read_text() for entity in entities), p


def test_load_profile_allows_na_capabilities():
    b = meta_ledger()
    assert checker.check(b) == []
    b['direction']['meta']['loadProfile']['militaryScale'] = 99
    assert any('invalid load' in e for e in checker.check(b))


def test_narrative_aperture_has_explicit_exclusions():
    b = meta_ledger(); b['direction']['meta']['narrativeAperture']['excluded'] = []
    assert any('APERTURE missing excluded' in e for e in checker.check(b))


def test_pov_contract_blocks_forbidden_omniscience():
    b = meta_ledger(); b['sequence'][0]['omniscience'] = ['remote.privateThought']
    assert any('forbidden perspective/omniscience' in e for e in checker.check(b))


def test_subjective_lens_cannot_override_confirmed_fact():
    b = meta_ledger()
    moment = dict(id='near', scene='s1', anchorCharacter='speaker:one', purpose='experience uncertainty',
                  expression='attention narrows', returnToObjective='s1-return', altersFacts=[])
    b['direction']['meta']['subjectiveLens']['subjectiveMoments'] = [moment]
    assert checker.check(b) == []
    moment['altersFacts'] = ['event']
    assert any('cannot override historical facts' in e for e in checker.check(b))
    moment['altersFacts'] = []; moment['returnToObjective'] = 'unrecorded'
    assert any('missing objective return' in e for e in checker.check(b))


def test_character_elasticity_requires_pressure_reason():
    b = meta_ledger()
    b['characters']['speaker:one']['elasticity'] = dict(normalBehavior='checks', pressureResponse='rushes', breakCondition='exhaustion', possibleDeviation='interrupts', recoveryPattern='rechecks')
    b['sequence'][1]['deviations'] = [dict(speaker='speaker:one', pressureEvidence=['s1 fatigue'], reason='fatigue changes pace')]
    assert checker.check(b) == []
    b['sequence'][1]['deviations'][0]['pressureEvidence'] = []
    assert any('ELASTICITY' in e for e in checker.check(b))


def test_cross_episode_continuity():
    b = meta_ledger(); b['sequence'][1]['inputState']['place'] = 'elsewhere'
    errors = checker.check(b)
    assert any('CONTINUITY' in e for e in errors)
    assert any('startState contradicts' in e for e in errors)


def test_context_projection_excludes_irrelevant_state():
    b = meta_ledger()
    b['characters']['speaker:one']['arc'] = 'future private revelation'
    scene = checker.project(b, scene_id='s1')
    assert [f['id'] for f in scene['authorConstraints']] == ['event']
    assert set(scene['characters']) == {'speaker:one'}
    assert 'arc' not in scene['characters']['speaker:one']
    assert scene['sceneJobs'][0]['knowledgeAtEntry'] == {'speaker:one': []}
    assert scene['sceneJobs'][0]['receiptsWithinScene'][0]['beforeBeat'] == 2
    episode = checker.project(b, episode_id='e2')
    assert [s['id'] for s in episode['sceneJobs']] == ['s2']
    with pytest.raises(ValueError): checker.project(b, scene_id='s1', episode_id='e1')
    b['sequence'][0]['context']['factIds'].append('absent')
    with pytest.raises(ValueError, match='Unknown factIds'): checker.project(b, scene_id='s1')


def test_dependency_revision_scope():
    b = meta_ledger()
    b['dependencies'] = [dict(source='injury', target='s1', reason='blocking consumes body'), dict(source='s1', target='s2', reason='next movement')]
    assert checker.affected_scopes(b, ['injury']) == ['injury','s1','s2']
    b['review']['findings'] = [dict(id='f', problem='wrong movement', severity='MAJOR', layer='CONTINUITY', evidence='s1', recommendedRevisionScope=['s1'], resolved=True)]
    rev = dict(number=1, findingIds=['f'], changedScopes=['s1'], before={'s1':'a','s2':'c'}, after={'s1':'b','s2':'c'},
               invalidation=dict(changedNodes=['injury'], affectedScopes=['injury','s1','s2'], unaffectedScopes=['remote-politics'], recheckedScopes=['injury','s1','s2']))
    b['review']['rounds'] = [rev]
    assert checker.check(b) == []
    rev['invalidation']['recheckedScopes'].remove('s2')
    assert any('missing recheck' in e for e in checker.check(b))


def test_opening_closing_anchors_exist():
    b = meta_ledger(); del b['direction']['episodeArchitecture'][1]['closingShotAnchor']
    assert any('ANCHOR e2 missing' in e for e in checker.check(b))


def test_opening_closing_not_full_shot_plan():
    b = meta_ledger()
    b['direction']['episodeArchitecture'][0]['openingShotAnchor']['extra'] = {'lens': 'exact equipment'}
    assert any('contains shot execution' in e for e in checker.check(b))


def test_revision_budget_still_enforced():
    b = meta_ledger()
    b['review']['rounds'] = [dict(number=i, findingIds=[], changedScopes=[], before={}, after={}) for i in range(1,4)]
    assert any('two corrective rounds' in e for e in checker.check(b))


def test_v2_01_ledger_remains_valid_without_meta():
    assert checker.check(ledger()) == []


def test_material_change_does_not_invalidate_unchanged_historical_output():
    b = meta_ledger()
    b['dependencies'] = [dict(source='s1:lens', target='s1', reason='attention'),
                         dict(source='fact:date', target='s1', reason='time'),
                         dict(source='fact:date', target='s2', reason='message travel')]
    assert checker.affected_scopes(b, ['s1:lens']) == ['s1','s1:lens']
    assert checker.affected_scopes(b, ['fact:date']) == ['fact:date','s1','s2']
