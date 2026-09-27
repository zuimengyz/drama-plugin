from copy import deepcopy
import pytest

# Retained provider contracts; active Ark admission has a separate test suite.
pytestmark = pytest.mark.usefixtures("retained_production_policy")
from drama_plugin.visual.video_selection import ProductionRoute,qualify_route
from drama_plugin.contracts.base import sha256_canonical
from test_production_route import route
from test_cinematic_direction import frozen_example
from seedance_helpers import execution_contract


def partial(tmp_path):
    raw=route(tmp_path).model_dump(mode='json')
    raw['video_targets']=['S1','S2']
    raw['inputs'][0]['for_targets']=['S1','S2']
    raw['execution']=execution_contract('flux-3')
    raw['requirements'].update(creative_schema='cinematic-shot-v1',cinematic_directions={'S1':frozen_example()},shots={'S1':'SHOT','S2':'SHOT2'})
    return ProductionRoute.model_validate(raw)


def test_current_target_and_whole_route_are_distinct(tmp_path):
    r=partial(tmp_path)
    assert qualify_route(r,execution_target='S1')['eligible']
    assert set(qualify_route(r,execution_target='S1')['cinematic_directions'])=={'S1'}
    for target in [None,'S2','outside']:
        with pytest.raises(ValueError,match='COMPLETE_FROZEN'):
            qualify_route(r,execution_target=target)


@pytest.mark.parametrize('change',['hash','source','work','shot'])
def test_current_direction_still_strict(tmp_path,change):
    raw=partial(tmp_path).model_dump(mode='json');f=raw['requirements']['cinematic_directions']['S1']
    if change=='hash':f['fingerprint']='0'*64
    if change=='source':f['spec']['sourceFingerprint']='0'*64
    if change=='work':f['spec']['workId']='other'
    if change=='shot':raw['requirements']['shots']['S1']='other'
    with pytest.raises(ValueError):qualify_route(ProductionRoute.model_validate(raw),execution_target='S1')


def test_fully_frozen_and_extra_direction(tmp_path):
    raw=partial(tmp_path).model_dump(mode='json')
    f=deepcopy(raw['requirements']['cinematic_directions']['S1']);f['spec']['shotId']='SHOT2'
    f['fingerprint']=sha256_canonical({k:v for k,v in f.items() if k!='fingerprint'})
    raw['requirements']['cinematic_directions']['S2']=f
    r=ProductionRoute.model_validate(raw)
    assert qualify_route(r)['eligible']
    assert qualify_route(r,execution_target='S2')['eligible']
    raw['requirements']['cinematic_directions']['outside']=f
    with pytest.raises(ValueError,match='COMPLETE_FROZEN'):
        qualify_route(ProductionRoute.model_validate(raw),execution_target='S1')


@pytest.mark.asyncio
async def test_formal_admission_explicit_target_only(tmp_path,monkeypatch):
    from test_production_route import Memory
    from drama_plugin.hosts import route_production
    from drama_plugin.visual.video_selection import choose_routes
    memory=Memory();r=partial(tmp_path);raw=r.model_dump(mode='json')
    async def checked_sources(memory,work,route):
        assert route.requirements['cinematic_directions']['S1']['spec']['workId']==work.id
    monkeypatch.setattr(route_production,'validate_route_direction_sources',checked_sources)
    with pytest.raises(ValueError,match='COMPLETE_FROZEN'):
        await route_production.save_route(memory,'W',raw)
    assert 'productionRoute' not in memory.work.content
    result=await route_production.save_route(memory,'W',raw,execution_target='S1')
    assert result['eligible']
    assert memory.work.content['productionRoute']['video_targets']==['S1','S2']
    with pytest.raises(ValueError,match='COMPLETE_FROZEN'):
        choose_routes([r])
