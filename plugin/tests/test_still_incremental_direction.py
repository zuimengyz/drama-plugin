from copy import deepcopy
import pytest
from test_incremental_frozen_direction import partial
from drama_plugin.visual.production import _route_frame_gate
from drama_plugin.visual.video_selection import ProductionRoute, qualify_route, route_input_gate


def setup(tmp_path):
    raw=partial(tmp_path).model_dump(mode='json')
    raw['inputs'][0]['for_targets']=['S1']
    for n in range(2,13):
        target=f'S{n}'
        if target not in raw['video_targets']:raw['video_targets'].append(target)
        duty=deepcopy(raw['inputs'][0]);duty.update(target_id=f'I{n}',for_targets=[target],cost_key=f'input_{n}')
        raw['inputs'].append(duty);raw['candidate']['cost']['components'][f'input_{n}']=5
    raw['candidate']['cost']['components']['video']=1200
    frame={'schema':'visual-frame-preflight-v1','spec':{'shot_id':'I','shot_fingerprint':raw['creative_fingerprint']}}
    return {'production_route':raw,'attempts':[]},frame


def test_current_still_with_eleven_pending_targets(tmp_path):
    state,f=setup(tmp_path)
    _route_frame_gate(state,f)
    with pytest.raises(ValueError,match='COMPLETE_FROZEN'):
        qualify_route(ProductionRoute.model_validate(state['production_route']))
    with pytest.raises(ValueError,match='COMPLETE_FROZEN'):
        route_input_gate(ProductionRoute.model_validate(state['production_route']),'I','START')


@pytest.mark.parametrize('mutation',['missing','source','hash','work','binding','outside'])
def test_current_target_remains_strict(tmp_path,mutation):
    state,f=setup(tmp_path);r=state['production_route'];direction=r['requirements']['cinematic_directions']['S1']
    if mutation=='missing':r['requirements']['cinematic_directions']={}
    if mutation=='source':direction['spec']['sourceFingerprint']='0'*64
    if mutation=='hash':direction['fingerprint']='0'*64
    if mutation=='work':direction['spec']['workId']='other'
    if mutation=='binding':f['spec']['shot_fingerprint']='0'*64
    if mutation=='outside':r['inputs'][0]['for_targets']=['outside']
    with pytest.raises(ValueError):_route_frame_gate(state,f)


def test_shared_input_does_not_pick_arbitrary_first_consumer(tmp_path):
    state,f=setup(tmp_path);state['production_route']['inputs'][0]['for_targets']=['S1','S2']
    state['production_route']['inputs']=[d for d in state['production_route']['inputs'] if d['target_id']!='I2']
    with pytest.raises(ValueError,match='COMPLETE_FROZEN'):_route_frame_gate(state,f)
    with pytest.raises(ValueError,match='OUTSIDE_INPUT_DUTY'):
        route_input_gate(ProductionRoute.model_validate(state['production_route']),'I','START',execution_target='S3')


@pytest.mark.parametrize('mutation',[None,'creative','work','journal','frozen','arbitrary'])
def test_still_pin_refresh_requires_exact_creative_and_journal(tmp_path,mutation):
    from drama_plugin.visual.production import _same_still_after_canonical_binding
    state,f=setup(tmp_path);r=state['production_route']
    r['creative_fingerprint']=r['requirements']['cinematic_directions']['S1']['spec']['sourceFingerprint']
    old=deepcopy(f);old['spec']['shot_fingerprint']='4'*64
    f['spec']['shot_fingerprint']=r['creative_fingerprint']
    previous=deepcopy(r);previous['creative_fingerprint']='4'*64
    state['route_revisions']=[{'previous_route':previous}]
    if mutation=='creative':f['spec']['composition']='different'
    if mutation=='work':previous['work_id']='other'
    if mutation=='journal':state['route_revisions']=[]
    if mutation=='frozen':r['requirements']['cinematic_directions']={}
    if mutation=='arbitrary':f['spec']['shot_fingerprint']='5'*64
    assert _same_still_after_canonical_binding(state,old,f) is (mutation is None)
