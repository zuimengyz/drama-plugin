"""Synthetic local expression invariants; no media, network or legacy creative source."""
import hashlib
from types import SimpleNamespace
import pytest
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.generation.contracts import GenerationTask, CoverageEntry, CoverageStatus
from drama_plugin.generation.expression import PromptExpression, ExpressionMapping
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



def test_history_still_deserializes_without_execution_entry():
    import drama_plugin.generation.expression as retired
    _, _, expression = fixture()
    assert PromptExpression.model_validate_json(expression.model_dump_json()) == expression
    assert not hasattr(retired, 'compile_expression')
    assert not hasattr(retired, 'validate_expression')


def test_old_task_roundtrip_keeps_fingerprint():
    _, task, expression = fixture()
    historical = task.model_copy(update={'prompt_expression_ref':expression.artifact_reference()})
    assert GenerationTask.model_validate_json(historical.model_dump_json()) == historical
    assert 'finalWritingRef' not in historical.model_dump(mode='json', by_alias=True)
