from copy import deepcopy
import pytest
from test_specialized_asset import fixture
from test_official_video_providers import request
from drama_plugin.contracts.creation import Work
from drama_plugin.contracts.base import dump_contract
from drama_plugin.hosts.specialized_asset import bind_video_request, authority_semantics, compile_authority_context, validate_visual_submission

def setup(tmp_path, monkeypatch):
    host,bible,ref,current=fixture(tmp_path,'cg')
    compiled=host.compile(ref,'room',current=current)
    monkeypatch.setenv('DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT',str(tmp_path))
    w=Work(id='work',title='Synthetic',content={'movieVisualMediumRef':dump_contract(bible.runtime_ref),'specializedAssetCompilationRefs':[compiled['compilationRef']],'visualSourceCurrent':current})
    r=request();r.continuity.work_id=w.id
    return w,r

def test_rebinding_is_idempotent_and_repairs_historical_exact_suffix(tmp_path,monkeypatch):
    w,r=setup(tmp_path,monkeypatch)
    bound=bind_video_request(w,r)
    assert bind_video_request(w,bound)==bound
    # Reproduce the old binder, including the nested authority evidence.
    values=dump_contract(bound);values.pop('authority_context')
    context=compile_authority_context(w,values)
    values['prompt']+='\n'+authority_semantics(context);values['authority_context']=context
    old=type(r).model_validate(values)
    with pytest.raises(ValueError,match='DUPLICATED_BLOCK'):validate_visual_submission(w,dump_contract(old))
    repaired=bind_video_request(w,old)
    assert repaired==bound
    validate_visual_submission(w,dump_contract(repaired))
    assert repaired.first_frame==r.first_frame

def test_distinct_prose_preserved_and_forged_authority_rejected(tmp_path,monkeypatch):
    w,r=setup(tmp_path,monkeypatch)
    r.prompt+='\nKeep the room readable while the camera holds.'
    bound=bind_video_request(w,r)
    assert bind_video_request(w,bound).prompt.startswith(r.prompt+'\n')
    bad=deepcopy(bound);bad.authority_context['assets'][0]['executableSemantic']='forged'
    with pytest.raises(ValueError,match='ASSET_AUTHORITY_CONTEXT_CHANGED'):bind_video_request(w,bad)
