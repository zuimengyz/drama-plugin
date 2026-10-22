"""Synthetic local expression invariants; no media, network or legacy creative source."""
import hashlib
from types import SimpleNamespace
import pytest
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.generation.contracts import GenerationTask, CoverageEntry, CoverageStatus
from drama_plugin.generation.expression import PromptExpression, ExpressionMapping, validate_expression
from drama_plugin.runtime.contracts import ArtifactReference


def fixture(target='参考@图片1，先收到音乐再停步。'):
    task=GenerationTask()
    ref=ArtifactReference(owner='final-prompt',artifact_ref='final-prompt:test',version=1)
    package=ArtifactReference(owner='production-package',artifact_ref='production-package:test',version=1)
    text='参考@图片1。听见音乐后才停步，不提前停下。'
    base=SimpleNamespace(source_package_ref=package,prompt_text=text,expression_ref=None,artifact_reference=lambda:ref)
    exp=PromptExpression.seal(source_package_ref=package,baseline_final_ref=ref,
        baseline_task_fingerprint=sha256_canonical(task),baseline_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
        prompt_text=target,mappings=({'source_span':(0,len(text)),'target_spans':((0,len(target)),),'judgment':'Host preserves sound before response'},),
        reviewer='Host',review_basis='Synthetic expression review',excluded_local_labels=('K05','V5'))
    return base,task,exp


def test_pinned_mapping_and_reloaded_artifact():
    base,task,exp=fixture()
    validate_expression(PromptExpression.model_validate(exp.model_dump()),base,task)


@pytest.mark.parametrize('change,code',[
    ({'baseline_text_sha256':'0'*64},'BASELINE_MISMATCH'),
    ({'baseline_task_fingerprint':'0'*64},'BASELINE_MISMATCH'),
    ({'mappings':(ExpressionMapping(source_span=(1,999),target_spans=((0,18),),judgment='invalid bounds'),)},'SPAN_INVALID'),
])
def test_bad_pins_and_bounds(change,code):
    base,task,exp=fixture()
    with pytest.raises(ValueError,match=code):validate_expression(exp.model_copy(update=change),base,task)


def test_unmapped_source_and_target():
    base,task,exp=fixture()
    m=exp.mappings[0]
    with pytest.raises(ValueError,match='SOURCE_UNMAPPED'):
        validate_expression(exp.model_copy(update={'mappings':(m.model_copy(update={'source_span':(1,len(base.prompt_text))}),)}),base,task)
    with pytest.raises(ValueError,match='TARGET_UNMAPPED'):
        validate_expression(exp.model_copy(update={'mappings':(m.model_copy(update={'target_spans':((1,len(exp.prompt_text)),)}),)}),base,task)


@pytest.mark.parametrize('target,code',[('按K05参考@图片1。','LOCAL_LABEL'),('参考@图片2。','REFERENCE_TOKENS')])
def test_reference_and_local_label_preservation(target,code):
    base,task,exp=fixture(target)
    with pytest.raises(ValueError,match=code):validate_expression(exp,base,task)


def test_exact_speech_cannot_be_paraphrased():
    base,task,exp=fixture()
    with pytest.raises(ValueError,match='EXACT_SPEECH_CHANGED'):validate_expression(exp,base,task,('精确台词',))


def test_transformed_baseline_cannot_skip_original():
    base,task,exp=fixture();base.expression_ref=exp.artifact_reference()
    with pytest.raises(ValueError,match='FULL_NATIVE_BASELINE'):validate_expression(exp,base,task)


def test_task_extension_absent_preserves_old_envelope():
    task=GenerationTask()
    assert 'promptExpressionRef' not in task.model_dump(mode='json',by_alias=True)
    assert GenerationTask.model_validate(task.model_dump())==task
    with pytest.raises(ValueError,match='REFERENCE_OWNER'):
        GenerationTask(prompt_expression_ref=ArtifactReference(owner='wrong',artifact_ref='wrong',version=1))


@pytest.mark.asyncio
async def test_expression_compilation_retains_baseline_and_uses_distinct_coverage():
    from drama_plugin.generation.compiler import CompilationResult
    from drama_plugin.generation.expression import compile_expression
    from drama_plugin.generation.contracts import FinalPromptArtifact, PromptCoverage, AudioExecutionPlan, GenerationPreparation
    from drama_plugin.generation.store import GenerationArtifactStore
    from drama_plugin.production.contracts import SourceReference
    store=GenerationArtifactStore();base,task,exp=fixture()
    source=SourceReference(owner='professional',artifact_ref='synthetic-action',version=1,fingerprint='3'*64,path=('action',))
    coverage=PromptCoverage.seal(source_package_ref=base.source_package_ref,entries=(CoverageEntry(fact_id='sound-before-response',domain='ACTION',source_ref=source,obligation='EXECUTION_REQUIRED',status='TEXT_COVERED',span=(0,len(base.prompt_text))),))
    final=FinalPromptArtifact.seal(source_package_ref=base.source_package_ref,task=task,model_family='synthetic',generator_policy_fingerprint='1'*64,prompt_text=base.prompt_text,prompt_ir_fingerprint='2'*64,coverage_ref=store.put(coverage))
    audio=AudioExecutionPlan.seal(source_package_ref=base.source_package_ref,duration_ms=6000,speech_events=(),relations=(),scope={'work_id':'synthetic-work','scene_id':'synthetic-scene','shot_id':'synthetic-shot'},native_audio_policy='OPTIONAL',source_roles=())
    prepared=GenerationPreparation.seal(source_package_ref=base.source_package_ref,task=task,final_prompt_ref=store.put(final),audio_plan_ref=store.put(audio))
    prepref=store.put(prepared)
    exp=PromptExpression.seal(**{**exp.model_dump(exclude={'fingerprint'}),'baseline_final_ref':final.artifact_reference()})
    transformed=task.model_copy(update={'prompt_expression_ref':store.put(exp)})
    package=SimpleNamespace(scope=SimpleNamespace(work=SimpleNamespace(artifact_ref='synthetic-work'),scene=SimpleNamespace(artifact_ref='synthetic-scene'),shot=SimpleNamespace(artifact_ref='synthetic-shot')))
    class Compiler:
        artifacts=store
        packages=SimpleNamespace(get=lambda _:package)
        async def compile(self,package_ref,base_task):
            assert base_task==task
            return CompilationResult(prepref,store.retain_diagnostics(()))
    compiler=Compiler()
    result=await compile_expression(compiler,base.source_package_ref,transformed)
    output=store.get(result.preparation_ref,GenerationPreparation)
    new=store.get(output.final_prompt_ref,FinalPromptArtifact)
    assert new.prompt_text==exp.prompt_text and new.matches_task(transformed)
    assert new.baseline_final_ref==final.artifact_reference()
    assert store.get(final.artifact_reference(),FinalPromptArtifact).prompt_text==base.prompt_text
    mapped=store.get(new.coverage_ref,PromptCoverage)
    assert mapped.entries[0].status==CoverageStatus.HOST_MAPPED
    assert store.get(final.coverage_ref,PromptCoverage).entries[0].status==CoverageStatus.TEXT_COVERED
    assert (await compile_expression(compiler,base.source_package_ref,transformed)).preparation_ref==result.preparation_ref
    broken=PromptExpression.seal(**{**exp.model_dump(exclude={'fingerprint'}),'baseline_text_sha256':'f'*64})
    failure=await compile_expression(compiler,base.source_package_ref,task.model_copy(update={'prompt_expression_ref':store.put(broken)}))
    assert failure.preparation_ref is None
