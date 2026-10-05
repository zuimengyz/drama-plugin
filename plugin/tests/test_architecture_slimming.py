"""M3 admission and immutable workflow compatibility, entirely offline."""
from pathlib import Path
import pytest
from drama_plugin.config import DramaPluginConfig
from drama_plugin.plugin import DramaPlugin
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.runtime.contracts import CapabilityInput, RuntimeScope, ResultStatus
from drama_plugin.creative_engine.sources import NativeCreativeSources
from drama_plugin.generation.policy import MEDIA_WORKFLOW, HISTORICAL_MEDIA_WORKFLOW, media_review_workflow, generation_workflow
from drama_plugin.generation.contracts import GenerationTask, FinalPromptArtifact
from drama_plugin.contracts.base import sha256_canonical

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def plugin(tmp_path, monkeypatch):
    monkeypatch.setattr('drama_plugin.plugin.load_config', lambda _: DramaPluginConfig())
    return DramaPlugin.load(ROOT, mock_data=MockDramaData.empty(), ledger_path=tmp_path/'ledger.sqlite',
                            production_artifact_roots=(tmp_path/'history',))

@pytest.mark.asyncio
async def test_formal_composition_is_native_even_if_historical_paths_are_configured(plugin):
    assert plugin.runtime.executor.legacy is None
    assert plugin.runtime.executor.migration_keys == frozenset()
    assert isinstance(plugin.shot_assembler.sources, NativeCreativeSources)
    assert plugin.professional_design.backend is plugin.shot_assembler.sources
    assert plugin.shot_assembler.sources.references is plugin.execution_references
    assert plugin.prompt_compiler.reader.dependencies is None
    assert plugin.prompt_compiler.references.media_reader is plugin.providers.media
    result=await plugin.runtime.executor.execute('work.get_work',CapabilityInput(run_id='test',operation_id='test:0',scope=RuntimeScope(work_id='absent')))
    assert result.status == ResultStatus.FAILED and result.code == 'LEGACY_GUARD'
    assert len(plugin.runtime.executor.native_keys) == 34
    await plugin.aclose()

@pytest.mark.asyncio
async def test_historical_read_composition_requires_explicit_opt_in(tmp_path,monkeypatch):
    monkeypatch.setattr('drama_plugin.plugin.load_config', lambda _: DramaPluginConfig())
    plugin=DramaPlugin.load(ROOT,mock_data=MockDramaData(),ledger_path=tmp_path/'ledger.sqlite',legacy_reads=True)
    assert plugin.runtime.executor.legacy is not None
    assert plugin.prompt_compiler.reader.dependencies.lifecycle == 'MIGRATION_ONLY'
    assert plugin.shot_assembler.sources.legacy.lifecycle == 'MIGRATION_ONLY'
    await plugin.aclose()


def test_workflow_slimming_preserves_historical_contract():
    old=media_review_workflow(HISTORICAL_MEDIA_WORKFLOW)
    new=media_review_workflow()
    assert old.workflow_id == 'package-to-reviewed-media:v1' and len(old.steps)==12
    assert old.steps[:7] == generation_workflow().steps
    assert new.workflow_id == MEDIA_WORKFLOW and len(new.steps)==10
    assert new.steps == (old.steps[0],*old.steps[3:])
    assert all('audio' not in (s.capability_key or '') and 'finish' not in (s.capability_key or '') for s in new.steps)


def test_final_prompt_historical_task_envelope_remains_exact():
    from drama_plugin.runtime.contracts import ArtifactReference
    package=ArtifactReference(owner='production-package',artifact_ref='production-package:'+'0'*64,version=1)
    coverage=ArtifactReference(owner='prompt-coverage',artifact_ref='prompt-coverage:'+'1'*64,version=1)
    task=GenerationTask()
    final=FinalPromptArtifact.seal(source_package_ref=package,task=task,model_family='seedance',
        generator_policy_fingerprint='2'*64,prompt_text='Exact approved prompt.',prompt_ir_fingerprint='3'*64,coverage_ref=coverage)
    assert final.matches_task(task)
    assert 'taskFingerprint' not in final.model_dump(mode='json',by_alias=True)
    assert final.fingerprint == sha256_canonical(final.model_dump(mode='json',by_alias=True,exclude={'fingerprint'}))
    assert FinalPromptArtifact.model_validate_json(final.model_dump_json()).artifact_reference() == final.artifact_reference()
