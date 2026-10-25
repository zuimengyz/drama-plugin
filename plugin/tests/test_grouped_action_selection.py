"""Analysis granularity must not schedule generation or lose source obligations."""
from dataclasses import replace

import pytest

from drama_plugin.config.video_route import VideoRoutePolicy
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.creative_engine.store import CreativeVersionStore
from drama_plugin.generation.operation import OperationResolver, validate_segment_progress
from drama_plugin.persistence.ledger import ProductionLedger
from drama_plugin.production.contracts import ProductionPackage, PackageContent
from test_operation_selection_capacity import package_and_reader


def sources(count=4):
    package, reader = package_and_reader(12)
    records = reader.resolver.records
    records['ACTION']['content']['actionPhases'] = [
        dict(beatId=f'beat-{i}', spokenIds=[], entryState=f'Entry {i}.',
             observable=f'Outcome {i}.', action=f'Work {i} shares the ongoing task.')
        for i in range(count)]
    records['PERFORMANCE']['content']['beats'] = [
        dict(id=f'beat-{i}',physicalExpression=f'Partner receives {i}.') for i in range(count)]
    records['CAMERA'] = {'content': {'movement': {'phaseDirections': [
        dict(phaseIndex=i,trajectory=f'Camera event {i}.') for i in range(count)]}}}
    records['EDITORIAL'] = {'content': {'protectedEvents': [
        dict(phaseIndex=i,design=f'Protect consequence {i}.') for i in range(count)]}}
    from drama_plugin.production.contracts import DomainReference, SourceReference
    refs = tuple(DomainReference(domain=name,reference=SourceReference(owner='professional',artifact_ref=name,
        version=1,fingerprint=sha256_canonical(body),path=('content',)))
        for name,body in sorted(records.items()) if name != 'shot')
    content = PackageContent.model_validate({**package.model_dump(exclude={'package_id','fingerprint'}),'sources':refs})
    return ProductionPackage.freeze(content),reader


@pytest.mark.asyncio
async def test_native_opening_consumes_host_clip_plan_without_inference(tmp_path):
    package,reader=sources()
    original=reader.selections
    async def selected(p):
        items=await original(p)
        return tuple(replace(i,value={**i.value,'generationGroups':[{'phaseIndices':[0,1,2]}]})
            if i.selection.domain=='EDITORIAL' else i for i in items)
    reader.selections=selected
    op=OperationResolver(CreativeVersionStore(tmp_path/'owners'),ProductionLedger(tmp_path/'ledger.sqlite'),VideoRoutePolicy())
    planned=await op.select_unit(package,reader)
    assert len(planned.action_refs)==3
    # Exact legacy/manual selection remains available; never silently regroup it.
    legacy=await op.select_unit(package,reader,phase_index=0)
    assert len(legacy.action_refs)==1


@pytest.mark.asyncio
async def test_group_preserves_exact_facts_and_boundary_without_extra_requests(tmp_path):
    package,reader=sources()
    op=OperationResolver(CreativeVersionStore(tmp_path/'owners'),ProductionLedger(tmp_path/'ledger.sqlite'),VideoRoutePolicy())
    a=await op.select_unit(package,reader,phase_indices=(0,1))
    b=await op.select_unit(package,reader,phase_indices=(2,3))
    assert a.beat_ids == ('beat-0','beat-1')
    assert a.start_ref.path[-2:] == ('0','entryState')
    assert a.end_ref.path[-2:] == ('1','observable')
    assert a.execution_context.boundary == 'START'
    assert b.execution_context.boundary == 'CONTINUE'
    values=[str(await reader.resolver.resolve(f.reference)) for f in a.fact_refs]
    assert 'Partner receives 0.' in values and 'Partner receives 1.' in values
    assert 'Camera event 1.' in values and 'Protect consequence 1.' in values
    assert 'Camera event 2.' not in values and 'Partner receives 2.' not in values
    validate_segment_progress(b,(a,))
    with pytest.raises(ValueError,match='REPEAT_OR_SKIP'):
        validate_segment_progress(a,(b,))
    overlap=await op.select_unit(package,reader,phase_indices=(1,2))
    with pytest.raises(ValueError,match='REPEAT_OR_SKIP'):
        validate_segment_progress(overlap,(a,))
    old=await op.select_unit(package,reader,phase_index=0)
    explicit=await op.select_unit(package,reader,phase_indices=(0,))
    assert old.model_dump_json() == explicit.model_dump_json()
    assert package.generation_intent.duration_ms == 4000  # selection never allocates time


@pytest.mark.asyncio
@pytest.mark.parametrize('indices', [(),(0,2),(1,0),(0,0),(False,1),(0,4)])
async def test_group_is_explicit_consecutive_source_selection(tmp_path,indices):
    package,reader=sources()
    op=OperationResolver(CreativeVersionStore(tmp_path/'owners'),ProductionLedger(tmp_path/'ledger.sqlite'),VideoRoutePolicy())
    with pytest.raises(ValueError,match='UNIT_PHASE_SELECTION_INVALID'):
        await op.select_unit(package,reader,phase_indices=indices)


@pytest.mark.asyncio
async def test_group_does_not_swallow_authored_cut(tmp_path):
    package,reader=sources()
    original=reader.selections
    async def selected(p):
        items=await original(p)
        action=next(i for i in items if i.selection.domain=='ACTION')
        phases=[dict(r) for r in action.value['actionPhases']]
        phases[1]['transition']='cut'
        return tuple(replace(i,value={**action.value,'actionPhases':phases}) if i is action else i for i in items)
    reader.selections=selected
    op=OperationResolver(CreativeVersionStore(tmp_path/'owners'),ProductionLedger(tmp_path/'ledger.sqlite'),VideoRoutePolicy())
    with pytest.raises(ValueError,match='UNIT_GROUP_CROSSES_AUTHORED_CUT'):
        await op.select_unit(package,reader,phase_indices=(0,1))


@pytest.mark.asyncio
async def test_group_keeps_numeric_analysis_order(tmp_path):
    package,reader=sources(12)
    op=OperationResolver(CreativeVersionStore(tmp_path/'owners'),ProductionLedger(tmp_path/'ledger.sqlite'),VideoRoutePolicy())
    unit=await op.select_unit(package,reader,phase_indices=tuple(range(12)))
    actions=[int(f.reference.path[-2]) for f in unit.fact_refs
        if f.domain=='ACTION' and f.reference.path[-1]=='action']
    assert actions == list(range(12))


@pytest.mark.asyncio
async def test_group_reaches_compiled_wire_without_intermediate_stop_states(tmp_path,monkeypatch):
    from test_event_scope_delivery import material,pipeline
    from drama_plugin.generation.contracts import GenerationPreparation,FinalPromptArtifact,PromptCoverage
    from drama_plugin.execution.live_transport import TargetHttpTransport
    import socket
    def deny(*args,**kwargs):
        raise AssertionError('Grouped replay must not call a provider')
    monkeypatch.setattr(socket.socket,'connect',deny)
    monkeypatch.setattr(socket.socket,'connect_ex',deny)
    req,raw=material()
    next(d for d in raw if d['domain']=='EDITORIAL')['facts']['generationGroups']=[
        {'phaseIndices':[0,1],'reason':'The waiting and handoff form one continuous viewing task.'}]
    p,compiler,package,old=await pipeline(tmp_path,monkeypatch,req,raw)
    try:
        op=compiler.reader.operations
        unit=await op.select_unit(package,compiler.reader)
        assert len(unit.action_refs)==2  # author DTO -> professional owner -> default selector
        task=old[0]['task'].model_copy(update={'unit':unit})
        result=await compiler.compile(compiler.packages.put(package),task)
        assert result.preparation_ref,compiler.artifacts.diagnostics(result.diagnostics_ref)
        ready=compiler.artifacts.get(result.preparation_ref,GenerationPreparation)
        final=compiler.artifacts.get(ready.final_prompt_ref,FinalPromptArtifact)
        wire=TargetHttpTransport.preview(ready,final,ledger=p.ledger)
        assert wire['duration']==8 and not ready.provider_submission_allowed
        assert wire['content'][0]['text']==final.prompt_text
        assert 'both wait without touching' in final.prompt_text
        assert 'supports the packet while' in final.prompt_text
        assert final.prompt_text.count('{Помогите.}')==1
        assert 'Small' in final.prompt_text and 'No displacement' in final.prompt_text
        assert 'FUTURE_CAMERA_EVENT' not in final.prompt_text
        coverage=compiler.artifacts.get(final.coverage_ref,PromptCoverage)
        for index,leaf in (('0','observable'),('1','entryState')):
            assert any(e.status=='INTERNAL_ONLY' and e.source_ref.path[-2:]==(index,leaf)
                for e in coverage.entries)
        assert not any(e.status=='UNRESOLVED' for e in coverage.entries)
        forged=unit.model_copy(update={'end_ref':old[0]['task'].unit.end_ref})
        with pytest.raises(ValueError,match='UNIT_SCOPED_PROJECTION_DRIFT'):
            await op.selected(package,task.model_copy(update={'unit':forged}),compiler.reader,admission_required=False)
    finally:
        await p.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize('indices',[(0,),(0,1),(0,1,2,3)])
async def test_progress_counts_grouped_coverage_once_and_keeps_old_records_readable(tmp_path,monkeypatch,indices):
    from types import SimpleNamespace as N
    from drama_plugin.film import media_units as m
    from drama_plugin.creative_engine.contracts import Kind
    from drama_plugin.runtime.contracts import ArtifactReference
    package,reader=sources()
    op=OperationResolver(CreativeVersionStore(tmp_path/'owners'),ProductionLedger(tmp_path/'ledger.sqlite'),VideoRoutePolicy())
    selection=await op.select_unit(package,reader,phase_indices=indices)
    ref=ArtifactReference(owner='test',artifact_ref='retained')
    scope=N(work_id='work')
    unit=N(scene_id='scene',shot_id='shot',refs=('shot','editorial'),package_ref=ref)
    task=N(unit=selection,profile=N(requested_duration_ms=8000),input_mode='text_to_video',
        boundary=None,continuation=None,execution_reference_refs=None)
    child=N(state=N(value='SUCCEEDED'),scope=scope)
    parent=N(state=N(value='WAITING_INPUT'),scope=scope,workflow_id='film')
    canon=N(scenes=[N(scene_id='scene',scene=N(scene_text='Exchange',dialogue=[]))])
    direction=N(shots=[unit])
    cp=N(canon_ref='canon',direction_ref='direction',units=[unit])
    owners={'shot':N(kind=Kind.SHOT,body=N(duration_ms=12000)),
        'editorial':N(kind=Kind.PROFESSIONAL,body=N(domain='EDITORIAL',facts={
            'generationGroups':[{'phaseIndices':[0,1]},{'phaseIndices':[2,3]}]}))}
    p=N(film=N(store=N(checkpoint=lambda _:cp,author=lambda r,_:canon if r=='canon' else direction)),
        runtime=N(store=N(load=lambda r:parent if r=='film' else child)),
        generation_artifacts=N(inputs=lambda _:N(task=task)),creative_versions=N(resolve=owners.__getitem__),
        ledger=N(get_index=lambda *_:None))
    check=N(progress=N(video_ref=ref,current_video_technical_ref=None,video_creative_ref=None))
    media=N(canonical_media_ref=ref,media=N(content_hash='a'*64))
    monkeypatch.setattr(m,'child_ids',lambda *_:['child'])
    monkeypatch.setattr(m,'unit_for_task',lambda *_:unit)
    monkeypatch.setattr(m,'phases_for',lambda *_:(None,reader.resolver.records['ACTION']['content']['actionPhases']))
    monkeypatch.setattr(m,'completion',lambda *_:(None,check,media,task))
    monkeypatch.setattr(m,'adoption_receipts',lambda _:[N(run_id='child',scope=scope,source_ref=ref)])
    monkeypatch.setattr(m,'archive_status',lambda *_:[])
    monkeypatch.setattr(m,'boundary_for',lambda *_:'CONTINUE')
    progress=m.production_progress(p,'film')
    shot=progress['scenes'][0]['shots'][0]
    assert shot['producedPhases']==shot['adoptedPhases']==list(indices)
    assert len(shot['segments'])==1  # one generated file can cover multiple analysis rows
    if len(indices)==4:
        assert progress['nextUnit'] is None and progress['filmContentComplete']
    elif len(indices)==2:
        assert progress['nextUnit']['phaseIndices']==[2,3]
    else:
        assert progress['nextUnit']['phaseIndex']==1
        assert 'phaseIndices' not in progress['mediaIndex'][0]  # legacy serialized shape
