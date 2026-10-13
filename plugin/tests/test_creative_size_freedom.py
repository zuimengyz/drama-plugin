"""Creative manifests follow authored structure; execution budgets remain explicit."""
import pytest
from pydantic import ValidationError
from drama_plugin.creative_engine.author_projection import canon_schema,direction_schema,check,select
from drama_plugin.creative_engine.contracts import WorkBody,ScriptBody,SceneBody,DependencyTask,RoutePlan
from drama_plugin.film.contracts import FilmCanon,CanonScene,FilmDirection,DirectedShot,FilmCheckpoint,ShotUnit
from test_film_engine import Authors,video,load,create


@pytest.mark.parametrize('count',[13,100,150])
def test_more_than_twelve_scenes_and_shots_survive_contract_and_schema(count):
    canon=FilmCanon(work=WorkBody(interpretation='Source interpretation',dramatic_intent='Follow consequence',character_meaning='Independent people'),
        script=ScriptBody(screenplay='Complete authored film'),scenes=tuple(CanonScene(scene_id=f'scene-{i}',scene=SceneBody(scene_text=f'Action {i}')) for i in range(count)))
    direction=FilmDirection(shots=tuple(DirectedShot(scene_id=s.scene_id,shot_id=f'shot-{i}',shot=Authors().body()) for i,s in enumerate(canon.scenes)))
    cp=FilmCheckpoint(units=tuple(ShotUnit(scene_id=s.scene_id,shot_id=s.shot_id,creative_run_id=f'creative-{i}') for i,s in enumerate(direction.shots)))
    assert len(FilmCanon.model_validate(canon.model_dump()).scenes)==count
    assert len(FilmDirection.model_validate(direction.model_dump()).shots)==count and len(cp.units)==count
    assert 'maxItems' not in canon_schema(film=True)['properties']['scenes']
    assert 'maxItems' not in direction_schema(film=True)['properties']['shots']
    value={'work':canon.work.model_dump(by_alias=True),'script':canon.script.model_dump(by_alias=True),
        'scenes':[{'scene':{'sceneText':'Source-bound action','subjects':[{'name':'Person','meaning':'Independent need'}],'dialogue':[]}} for _ in range(count)]}
    check(value,canon_schema(film=True),'canon')
    assert select(count-1,list(range(count)),('sceneSelection',),'direction')==count-1


def test_long_spoken_candidate_inventory_is_not_an_artistic_limit():
    body=Authors().body().model_copy(update={'spoken_ids':tuple(f'line-{i}' for i in range(150))})
    assert len(type(body).model_validate(body.model_dump()).spoken_ids)==150
    assert 'maxItems' not in direction_schema(film=False)['properties']['spokenSelections']


def test_duplicate_identity_and_explicit_execution_resource_budget_still_apply():
    task=DependencyTask(task_id='one',output='video',estimated_cost=1)
    with pytest.raises(ValidationError,match='child count'):
        RoutePlan(route='offline',tasks=(task,task.model_copy(update={'task_id':'two'})),max_tasks=1,
            max_depth=3,capability_available=True,authorization_required=True,cost_limit=5)
    with pytest.raises(ValidationError,match='estimated cost'):
        RoutePlan(route='offline',tasks=(task,),max_tasks=1,max_depth=3,
            capability_available=True,authorization_required=True,cost_limit=0)
    direction=DirectedShot(scene_id='scene',shot_id='shot',shot=Authors().body())
    with pytest.raises(ValidationError,match='Duplicate Shot'):FilmDirection(shots=(direction,direction))


@pytest.mark.asyncio
async def test_real_film_preparation_keeps_thirteen_scenes_twenty_six_shots(tmp_path,monkeypatch,video):
    p,authors=load(tmp_path,monkeypatch,video,Authors(scenes=13,shots=2))
    try:
        run=create(p,'large-film')
        run=await p.runtime.run(run.run_id)
        from drama_plugin.runtime.contracts import RuntimeState
        assert run.state==RuntimeState.WAITING_USER
        cp=p.film.store.checkpoint(run.run_id)
        assert len(cp.units)==26 and len({u.scene_id for u in cp.units})==13
        assert len(cp.graph.tasks)>32 and all(len(t.requires)<=4 for t in cp.graph.tasks)
        assert authors.calls.count('film-canon')==authors.calls.count('film-direction')==1
        assert not (tmp_path/'remote'/'submissions.jsonl').exists()
    finally:await p.aclose()
