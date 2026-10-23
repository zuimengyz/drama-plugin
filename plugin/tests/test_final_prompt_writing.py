"""One-pass final writing: coverage, exact speech, source pins and wire identity."""
import pytest
from drama_plugin.generation.contracts import (
    FinalPromptWriting, GenerationTask, GenerationPreparation, FinalPromptArtifact, PromptCoverage,
)
from test_prompt_audio_convergence import generation_fixture, fixture, load, prepare, artifacts, offline


async def source_writing(plugin, final, ready):
    ir = await plugin.prompt_compiler.prompt_ir(ready)
    paragraphs = []
    for fact in ir.facts:
        module = ('sound' if fact.domain == 'SOUND' else 'camera' if fact.domain == 'CAMERA'
                  else 'lighting' if fact.domain in ('LIGHTING', 'COLOR') else 'space' if fact.domain == 'WORLD'
                  else 'people' if fact.domain == 'SUBJECTS' else 'ending' if fact.slot == 'video.end_state'
                  else 'action')
        text = ('{{speech:' + fact.fact_id + '}}' if fact.domain == 'SOUND' and fact.subject_id else fact.text)
        paragraphs.append(dict(module=module, text=text, fact_ids=(fact.fact_id,)))
    return FinalPromptWriting.seal(source_package_ref=final.source_package_ref,
        source_ir_fingerprint=ir.fingerprint, paragraphs=paragraphs)


async def test_single_writing_serialization_and_exact_wire(generation_fixture, monkeypatch):
    plugin = load(generation_fixture)
    run = await prepare(plugin)
    old, _, ready = artifacts(plugin, run)
    writing = await source_writing(plugin, old, ready)
    ref = plugin.generation_artifacts.put(writing)
    task = ready.task.model_copy(update={'final_writing_ref':ref})
    calls = []
    original = plugin.prompt_compiler.generator.generate
    def generate(*a, **kw):
        calls.append(kw['writing'])
        return original(*a, **kw)
    monkeypatch.setattr(plugin.prompt_compiler.generator, 'generate', generate)
    result = await plugin.prompt_compiler.compile(old.source_package_ref, task)
    assert result.preparation_ref, plugin.generation_artifacts.diagnostics(result.diagnostics_ref)
    preparation = plugin.generation_artifacts.get(result.preparation_ref, GenerationPreparation)
    final = plugin.generation_artifacts.get(preparation.final_prompt_ref, FinalPromptArtifact)
    assert calls == [writing]
    assert final.prompt_text.count('机制测试的精确正文。') == 1
    assert final.prompt_text.count('【声音】') == 1
    assert final.prompt_text.count('【摄影】') == 1
    assert final.expression_ref is None and final.baseline_final_ref is None
    assert plugin.generation_artifacts.get(old.artifact_reference(), FinalPromptArtifact) == old
    coverage = plugin.generation_artifacts.get(final.coverage_ref, PromptCoverage)
    assert any(e.status == 'HOST_MAPPED' for e in coverage.entries)
    from drama_plugin.execution.contracts import ProviderRequest
    from drama_plugin.execution.live_transport import wire_payload
    wire = wire_payload(ProviderRequest(model=task.target_model, input_mode='text_to_video',
        prompt_text=final.prompt_text, duration_ms=6000, native_audio='OPTIONAL', references=()),
        provider='seedance', resolution='720p', aspect_ratio='16:9')
    assert wire['content'][0]['text'] == final.prompt_text
    assert '{{speech:' not in final.prompt_text


async def test_changed_source_and_missing_speech_not_silently_accepted(generation_fixture):
    plugin = load(generation_fixture)
    run = await prepare(plugin)
    old, _, ready = artifacts(plugin, run)
    writing = await source_writing(plugin, old, ready)
    for changed in (
        writing.model_copy(update={'source_ir_fingerprint':'f'*64}),
        writing.model_copy(update={'paragraphs':tuple(p for p in writing.paragraphs if '{{speech:' not in p.text)}),
    ):
        changed = FinalPromptWriting.seal(**changed.model_dump(exclude={'fingerprint'}))
        task = ready.task.model_copy(update={'final_writing_ref':plugin.generation_artifacts.put(changed)})
        result = await plugin.prompt_compiler.compile(old.source_package_ref, task)
        assert result.preparation_ref is None


def test_context_is_bounded_and_old_tasks_have_no_new_body():
    task = GenerationTask()
    assert 'finalWritingRef' not in task.model_dump(by_alias=True)
    with pytest.raises(ValueError, match='AT_MOST_TWO'):
        FinalPromptWriting.seal(source_package_ref={'owner':'production-package','artifactRef':'p','version':1},
            source_ir_fingerprint='a'*64,
            paragraphs=[dict(module='context',text='来源决定的处境。')]*3)


async def test_retired_compression_does_not_run(generation_fixture):
    from drama_plugin.runtime.contracts import ArtifactReference
    plugin = load(generation_fixture)
    run = await prepare(plugin)
    final, _, ready = artifacts(plugin, run)
    task = ready.task.model_copy(update={'prompt_expression_ref':ArtifactReference(
        owner='prompt-expression',artifact_ref='historical-only',version=1)})
    result = await plugin.prompt_compiler.compile(final.source_package_ref, task)
    assert result.preparation_ref is None


async def test_mixed_source_maps_to_multiple_modules_without_raw_append(generation_fixture):
    plugin = load(generation_fixture)
    run = await prepare(plugin)
    old, _, ready = artifacts(plugin, run)
    writing = await source_writing(plugin, old, ready)
    original = next(p for p in writing.paragraphs if p.module == 'action')
    # A single source can carry meanings expressed in two places. This explicit
    # Host map is retained; the generator must neither append the old leaf nor
    # label a rewritten clause as literal coverage.
    first = original.model_copy(update={'text':'开场已有接触，后续按既定动作接收。'})
    second = original.model_copy(update={'module':'ending', 'text':'已收到回应，接触关系保持。'})
    paragraphs = tuple(first if p == original else p for p in writing.paragraphs) + (second,)
    writing = FinalPromptWriting.seal(**{**writing.model_dump(exclude={'fingerprint'}),'paragraphs':paragraphs})
    task = ready.task.model_copy(update={'final_writing_ref':plugin.generation_artifacts.put(writing)})
    result = await plugin.prompt_compiler.compile(old.source_package_ref, task)
    assert result.preparation_ref
    prepared = plugin.generation_artifacts.get(result.preparation_ref, GenerationPreparation)
    final = plugin.generation_artifacts.get(prepared.final_prompt_ref, FinalPromptArtifact)
    coverage = plugin.generation_artifacts.get(final.coverage_ref, PromptCoverage)
    source = next(e for e in coverage.entries if e.fact_id == original.fact_ids[0])
    assert source.status == 'HOST_MAPPED'
    span = final.prompt_text[slice(*source.span)]
    assert first.text in span and second.text in span
    assert final.prompt_text.count(first.text) == final.prompt_text.count(second.text) == 1
