"""Offline regression for endpoint state scope and frozen recovery."""
import pytest
from test_continuation_endpoints import scenario, finish, following, media_files
from drama_plugin.generation.contracts import GenerationPreparation, AudioExecutionPlan
from drama_plugin.production.references import ReferenceExecutionBinding
from drama_plugin.generation.sources import SelectedValue

@pytest.mark.asyncio
async def test_endpoint_state_and_authored_duty_have_distinct_scopes(tmp_path, monkeypatch, media_files):
    p,r,service,calls,creates,auth,authors = await scenario(tmp_path,monkeypatch,media_files)
    cp=p.film.store.checkpoint(r); first=cp.units[0].generation_run_id; package_ref=cp.units[0].package_ref
    await finish(p,first,package_ref)
    task=await following(p,r,service,first,1)
    compiled=await p.prompt_compiler.compile(package_ref,task)
    assert compiled.preparation_ref, p.generation_artifacts.diagnostics(compiled.diagnostics_ref)
    prepared=p.generation_artifacts.get(compiled.preparation_ref,GenerationPreparation)
    ir=await p.prompt_compiler.prompt_ir(prepared)
    endpoint=[f for f in ir.facts if f.source_ref.path[-1:] == ('endpointState',)]
    assert len(endpoint)==1 and endpoint[0].slot=='video.start_state' and endpoint[0].domain=='ACTION'
    package=p.production_packages.get(package_ref)
    selected=await p.operation_resolver.selected(package,task,p.prompt_compiler.reader)
    amended=[]
    for item in selected:
        if item.selection.reference in task.execution_reference_refs:
            binding=ReferenceExecutionBinding.model_validate(item.value)
            duty=binding.duties[0].model_copy(update={'purpose':'The narrow shape in the case is unresolved; transfer only the object in the right hand.'})
            binding=binding.model_copy(update={'use_ref':binding.authority_refs[0],'duties':(duty,)})
            item=SelectedValue(item.selection,binding.model_dump(mode='json',by_alias=True))
        amended.append(item)
    plan=p.generation_artifacts.get(prepared.audio_plan_ref,AudioExecutionPlan)
    current=await p.prompt_compiler.projection.project(package,task,plan,tuple(amended))
    assert any(duty.purpose==f.text and f.slot=='preserve.reference_use' for f in current.ir.facts)
    frozen=await p.prompt_compiler.projection.project(package,task,plan,tuple(amended),legacy_endpoint_projection=True)
    assert any(f.slot=='video.camera_motion' and f.source_ref.path[-1:] == ('endpointState',) for f in frozen.ir.facts)
    assert not any(f.text==duty.purpose for f in frozen.ir.facts)
    assert len(creates)==1
