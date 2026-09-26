"""Permanent replay of Pre-R1 F01/F02/F03 adversarial findings."""
from copy import deepcopy
from pathlib import Path
import sys
import pytest
from drama_plugin.contracts.base import dump_contract,sha256_canonical as fp
from drama_plugin.contracts.performance_direction import PerformanceProjection
from drama_plugin.performance_direction import validate_projection
from drama_plugin.performance_coverage import full_performance_coverage_gate
from drama_plugin.preproduction import department_integration,complete_production_book
from preproduction_helpers import make_case
from formal_performance_helpers import formal_case
sys.path.insert(0,str(Path(__file__).parents[1]/'integration/fixtures'))
from r3_fixture_builder import build_fixture

@pytest.fixture(scope='module')
def proposal():return build_fixture((Path(__file__).parents[1]/'integration/fixtures/r3_source_proposal.md').read_text(),'a'*64)

def test_f01_distinct_pressure_control_and_channel_energy(proposal):
    assert proposal['intents']['P03'].external_expression_ceiling=='LOW'
    assert proposal['intents']['P08'].external_expression_ceiling=='HIGH'
    assert len({(d.effective.internal_activation,d.effective.external_control) for d in proposal['dpds'].values() if hasattr(d,'effective')})>3
    p=proposal['projections']['P08:spoken:s7-how']
    assert p['visualProjection']['externalExpression']=='HIGH'
    assert p['audioPerformanceBrief']['directorPerformance']['externalExpression']=='MEDIUM'
    assert 'collapse' not in proposal['intents']['P10'].forbidden_behaviors
    assert 'emotional_collapse' in proposal['intents']['P10'].forbidden_behaviors

@pytest.mark.parametrize('name',['虞美人','军吏','田父','亭长','灌婴','吕马童','楚从骑甲'])
def test_f01_secondary_roles_are_not_protagonist_defaults(proposal,name):
    actors=[d for d in proposal['dpds'].values() if getattr(d,'actor',None)==name]
    assert actors and any((d.direction.internal_activation,d.direction.external_control)!=('HIGH','HIGH') for d in actors)

def test_f02_legacy_packet_cannot_claim_complete_book():
    p,r,c,a=make_case()
    assert department_integration(p,r,c,a)['status']=='DEPARTMENT_REVIEW_READY'
    assert complete_production_book(p,r,c,a)['status']=='DIRECTOR_PRODUCTION_BOOK_NOT_READY'

def gate(f):return full_performance_coverage_gate(f['inventory'],f['directions'],current_source_hash=f['source_hash'],contexts=f['contexts'],dpds=f['dpds'],formal_source=f['formal_source'],scene_dpds=f['scene_dpds'],dramaturgy_reviews=f.get('dramaturgy_reviews'))

@pytest.mark.asyncio
async def test_f03_persisted_formal_fixture_passes(tmp_path):
    f=await formal_case(tmp_path/'canonical.json')
    assert gate(f)['status']=='FULL_PERFORMANCE_COVERAGE_READY'

@pytest.mark.asyncio
@pytest.mark.parametrize('attack',['scenes','spoken','silent','characters','voice','av_plan','interactions','continuity','fake-shot','parent','pin','proposal-dpd','label-only','forged-witness'])
async def test_f03_attacks_fail_closed(tmp_path,attack,proposal):
    f=await formal_case(tmp_path/'canonical.json')
    if attack in ('scenes','spoken','silent','characters','voice','av_plan','interactions','continuity'):f['inventory'][attack].pop()
    elif attack=='fake-shot':f['inventory']['shots'][0]['ref']='not-persisted'
    elif attack=='parent':f['inventory']['shots'][0]['scene']='wrong-scene'
    elif attack=='pin':f['source_hash']='0'*64;f['inventory']['source_hash']='0'*64
    elif attack=='proposal-dpd':
        k=next(iter(f['scene_dpds']));f['scene_dpds'][k]=next(d.scene for d in proposal['dpds'].values() if hasattr(d,'effective')).model_copy(update={'scene_id':k})
    elif attack=='label-only':
        f=deepcopy(proposal);f['inventory']['scope']='FORMAL_PRODUCTION_BOOK';f['formal_source']=None;f['scene_dpds']={}
    elif attack=='forged-witness':
        from drama_plugin.hosts.formal_performance import FormalSourceWitness
        f['formal_source']=FormalSourceWitness(object(),f['formal_source']._tree_json)
    with pytest.raises(ValueError):gate(f)


def test_f01_scripted_death_is_not_emotional_collapse(proposal):
    from drama_plugin.performance_direction import validate_action_performance
    intent=proposal['intents']['P10'];ref='P10:silent:06';source=intent.physical_consequences[ref]
    validate_action_performance(intent,action_ref=ref,source_action=source,behavior='scripted_physical_loss_of_support',action_completed=True)
    for behavior,completed in [('emotional_collapse',True),('scripted_physical_loss_of_support',False)]:
        with pytest.raises(ValueError):validate_action_performance(intent,action_ref=ref,source_action=source,behavior=behavior,action_completed=completed)

@pytest.mark.asyncio
async def test_f02_full_composed_book_passes_and_missing_evidence_blocks(tmp_path):
    f=await formal_case(tmp_path/'canonical.json')
    p,r,c,a=make_case(formal=f);c.update(f['current'])
    from music_fixture_builder import silent_plan
    score=silent_plan(p.scope_id,p.source_pins,p.intent_ref,f['intents'],'FORMAL')
    c.update({d.performance_intent_ref.key:d.performance_intent_ref.fingerprint for d in score.scene_music_decisions})
    reviewed={k:f[k] for k in ('inventory','directions')}
    reviewed.update({k:{ref:dump_contract(v) for ref,v in f[k].items()} for k in ('scene_dpds','dpds','intents')})
    reviewed['score_plan']=dump_contract(score)
    reviewed['dramaturgy_reviews']=f['dramaturgy_reviews']
    reviewed['projections']={k:{ch:dump_contract(v) for ch,v in pair.items()} for k,pair in f['projections'].items()}
    f['self_review']={'verdict':'PASS','reviewedFingerprint':fp(reviewed),'sourcePins':f['formal_source'].pins,'routeRef':dump_contract(p.route_ref)}
    assert complete_production_book(p,r,c,a,performance=f)['status']=='DIRECTOR_PRODUCTION_BOOK_NOT_READY'
    out=complete_production_book(p,r,c,a,performance=f,score_plan=score)
    assert out['status']=='DIRECTOR_PRODUCTION_BOOK_READY_FOR_USER_REVIEW',out
    for field in ('intents','projections','scene_dpds','self_review'):
        attacked={**f,field:{}}
        assert complete_production_book(p,r,c,a,performance=attacked,score_plan=score)['status']=='DIRECTOR_PRODUCTION_BOOK_NOT_READY'
