from copy import deepcopy
import pytest
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.director import DirectorRuntimeEstimate,DirectorWorkspace
from drama_plugin.contracts.visual_route import ProjectVisualRoutes,SequenceVisualRoute,RouteStyleContract
from drama_plugin.director_runtime import review_runtime
from drama_plugin.visual_route import resolve_visual_route

def budget():
    # Fictional palace clerk protecting a disputed account; no inherited film/CG settings.
    return dict(targetSeconds=310,expectedRangeSeconds=[260,360],uncertainty='Readthrough pending',sceneBudgets=[dict(sceneId=s,sequenceId='account',actId='hearing',sourceRef=dict(key=s,kind='DESIGN',fingerprint='a'*64),purpose='Clerk makes the minister read the original account',dialogueSeconds=65,actionSeconds=20,silentPerformanceSeconds=60,transitionSeconds=10,expectedSeconds=155,expectedRangeSeconds=[130,180],musicBearingSeconds=0,intentionalNoMusicSeconds=155,musicUndecidedSeconds=0,estimateBasis='Exchange, inspection, response and next room') for s in ('palace-room','palace-corridor')])

def test_nonwar_non_cg_story_runtime_is_its_own():
    e=DirectorRuntimeEstimate.model_validate(budget());r=review_runtime(e,scene_ids=['palace-room','palace-corridor'],current={'palace-room':'a'*64,'palace-corridor':'a'*64})
    assert r['targetSeconds']==310 and r['sequenceSeconds']=={'account':310} and not r['artisticApproval'] and r['actualMediaDuration'] is None
    p=ProjectVisualRoutes(work_id='palace-story',revision='draft',visual_route='live_action_realist',enabled_routes=['live_action_realist']);assert p.visual_route=='live_action_realist'
    assert not any(x in str(dump_contract(e)) for x in ['Gaixia','Xiang','项羽','虞','乌江','CG'])

@pytest.mark.parametrize('fault',['negative','nan','range','total','overlap','music','duplicate','act'])
def test_accounting_fail_closed(fault):
    b=budget();r=b['sceneBudgets'][0]
    if fault=='negative':r['dialogueSeconds']=-1
    elif fault=='nan':r['expectedRangeSeconds'][0]=float('nan')
    elif fault=='range':r['expectedRangeSeconds']=[200,300]
    elif fault=='total':b['targetSeconds']=400
    elif fault=='overlap':r['actionSeconds']=85
    elif fault=='music':r['musicBearingSeconds']=30
    elif fault=='duplicate':b['sceneBudgets'][1]['sceneId']=r['sceneId']
    else:b['sceneBudgets'][1]['actId']='other'
    with pytest.raises(ValueError):DirectorRuntimeEstimate.model_validate(b)

@pytest.mark.parametrize('fault',['missing','stale','coverage'])
def test_runtime_review_requires_current_complete_estimate(fault):
    e=DirectorRuntimeEstimate.model_validate(budget());current={'palace-room':'a'*64,'palace-corridor':'a'*64};scenes=list(current)
    if fault=='missing':e=None
    elif fault=='stale':current['palace-room']='b'*64
    else:scenes.pop()
    with pytest.raises(ValueError):review_runtime(e,scene_ids=scenes,current=current)

def test_music_overlay_unknown_does_not_increase_runtime():
    b=budget();r=b['sceneBudgets'][0];r.update(intentionalNoMusicSeconds=100,musicUndecidedSeconds=55)
    e=DirectorRuntimeEstimate.model_validate(b);assert e.target_seconds==310

def test_book_rejects_missing_estimate_without_requiring_production():
    from preproduction_helpers import make_case
    from drama_plugin.preproduction import complete_production_book
    p,r,c,a=make_case();p=p.model_copy(update={'expected_runtime':None})
    out=complete_production_book(p,r,c,a);assert 'DIRECTOR_RUNTIME_ESTIMATE_REQUIRED' in out['missing']

def test_old_workspace_fingerprint_shape_preserved():
    w=DirectorWorkspace(workspace_id='room',scope_id='palace',branch_id='draft',source_pins=[dict(key='source',kind='DESIGN',fingerprint='a'*64)])
    assert 'expectedRuntime' not in dump_contract(w)

@pytest.mark.parametrize('route,medium',[('live_action_realist','PHOTOGRAPHIC'),('stylized_cinematic_cg','DESIGNED_CG'),('stylized_animation','DESIGNED_ANIMATION'),('hybrid','HYBRID'),('provider:future_mode','PROVIDER_DEFINED')])
def test_every_route_explicit_work_scoped_no_global_default(route,medium):
    p=ProjectVisualRoutes(work_id='palace',revision='1',visual_route=route,enabled_routes=[route]);s=SequenceVisualRoute(work_id='palace',sequence_key='hearing')
    assert resolve_visual_route(p,s).visual_route==route
    style=dict(visualRoute=route,revision='1',medium=medium,rendering='declared',castingCriteria=['individual identity'],shapeLanguage='own profile',materialPalette='wood and textile',cameraGrammar='inspect the account',performanceGrammar='listen and choose',historicalBoundary='fictional historical setting',forbiddenDrifts=['unmotivated spectacle'])
    RouteStyleContract.model_validate(style)
    with pytest.raises(ValueError):ProjectVisualRoutes(work_id='another',revision='1')
    with pytest.raises(ValueError):resolve_visual_route(p,s.model_copy(update={'work_id':'other'}))
