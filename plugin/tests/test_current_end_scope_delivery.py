"""Offline formal originals -> native selection -> exact Seedance wire.

These bounded counterexamples verify transport/scope, not author or film quality.
"""
import socket

import pytest

from test_event_scope_delivery import material, pipeline


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('Current-end scope tests cannot call models or providers')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)


def sound(raw):
    return next(row for row in raw if row['domain'] == 'SOUND')['facts']


def test_frozen_scope_read_view_is_exact_and_never_the_new_default():
    from drama_plugin.generation.unit_scope import scoped_spans
    text = '当前炉火从第一声持续到本段最后，刨声停止后才显露，不另起一层火声。'
    args = {'final_phase': False, 'path': ('content', 'ambience')}
    assert scoped_spans(text, set(), set(), **args) == ((0, len(text)),)
    assert scoped_spans(text, set(), set(), explicitly_current=True,
        legacy_scope=True, **args) == ()
    # Unaffected old English fragments preserve their exact stored byte ranges.
    text = 'Room tone persists; a soft hiss, no impact.'
    assert scoped_spans(text, set(), set(), **args) == scoped_spans(
        text, set(), set(), legacy_scope=True, **args)


@pytest.mark.asyncio
@pytest.mark.parametrize('text', [
    '当前炉火从第一声持续到本段最后，刨声停止后才显露，不另起一层火声。',
    '说话者最后一字结束后仍有房间底声，听者不抢答。',
    '细小炉火一直持续到最后；说话声落下后自然可闻。',
    'Current room tone persists through the final line of this segment; no new sound starts at its end',
    '炉火不要等到下一段才响，开画时它已经在房间深处。',
    '不是在最后一个片段才有衣袖摩擦声，从当前第一声起就保持很轻。',
])
async def test_current_end_and_last_word_reach_each_current_wire_complete(tmp_path, monkeypatch, text):
    req, raw = material()
    sound(raw)['ambience'] = [{'design': text}]
    p, compiler, package, rows = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        for row in rows:
            assert text in row['final'].prompt_text
            assert text in row['wire']['content'][0]['text']
            assert not any(ref.reference.path[1:2] == ('ambience',)
                for ref in row['task'].unit.execution_context.background_refs)
    finally:
        await p.aclose()


@pytest.mark.asyncio
async def test_chinese_punctuation_keeps_current_spans_and_suppresses_later_span_with_its_tail(
        tmp_path, monkeypatch):
    req, raw = material()
    current = '当前炉火一直到本段最后，不另起一层火声'
    later = '最后一个片段才有门外钟声，钟声之后留一次远处回响'
    resumed = '当前近处衣袖声保持细小，不夸大为撞击'
    source = f'{current}；{later}。{resumed}。'
    sound(raw)['ambience'] = [{'design': source}]
    p, compiler, package, rows = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        first = rows[0]['wire']['content'][0]['text']
        assert current in first and resumed in first
        assert '门外钟声' not in first and '一次远处回响' not in first
        ref = next(fragment for fragment in rows[0]['task'].unit.execution_context.fact_spans
            if fragment.source_ref.path[1:2] == ('ambience',))
        assert len(ref.spans) == 2
        assert tuple(source[a:b] for a, b in ref.spans) == (current, resumed)
        # "final segment" is applicable only on the actual final Action unit.
        assert source in rows[1]['wire']['content'][0]['text']
    finally:
        await p.aclose()


@pytest.mark.asyncio
async def test_matched_phase_scope_wins_over_last_segment_prose_without_replaying_other_phase(
        tmp_path, monkeypatch):
    req, raw = material()
    current = '最后一段呼吸结束才让接触声消退，不把尾音剪断。'
    other = '另一片段才有的桌面擦声。'
    sound(raw)['contactTiedSound'] = [
        {'phaseIndex': 0, 'design': current},
        {'phaseIndex': 1, 'design': other},
    ]
    p, compiler, package, rows = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        for index, row in enumerate(rows):
            text = row['wire']['content'][0]['text']
            assert (current in text) == (index == 0)
            assert (other in text) == (index == 1)
    finally:
        await p.aclose()


@pytest.mark.asyncio
async def test_explicit_next_segment_stays_background_even_in_last_current_unit(tmp_path, monkeypatch):
    req, raw = material()
    later = '下一段才听见门外钟声，钟声后还有远处回响。'
    final_only = '最后一个片段只留下眼前的衣袖细声'
    current = '当前炉火在本段最后仍持续。'
    sound(raw)['ambience'] = [{'design': f'{later}；{final_only}；{current}'}]
    p, compiler, package, rows = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        for index, row in enumerate(rows):
            text = row['wire']['content'][0]['text']
            assert current.rstrip('。') in text
            assert '门外钟声' not in text and '远处回响' not in text
            assert (final_only in text) == (index == 1)
    finally:
        await p.aclose()


@pytest.mark.asyncio
async def test_other_place_and_whole_shot_clock_are_not_reintroduced(tmp_path, monkeypatch):
    req, raw = material()
    for phase in raw[0]['facts']['actionPhases']:
        phase['entryState'] = 'Room: both remain at the counter.'
    sound(raw)['ambience'] = [{'design': '街道：最后一字后远处车轮声仍在，脚步沿街远去。'}]
    sound(raw)['acousticSpace'] = '当前房间的声音近而短，不添加大厅回响。'
    whole_clock = '0–8秒全镜先等待再交接；8–16秒另段听远处车轮声。'
    next(row for row in raw if row['domain'] == 'EDITORIAL')['facts']['temporalStructure'] = whole_clock
    p, compiler, package, rows = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        for row in rows:
            text = row['wire']['content'][0]['text']
            assert '远处车轮声' not in text and '沿街远去' not in text
            assert whole_clock not in text and '0–8秒全镜' not in text
            excluded = row['task'].unit.execution_context.background_refs
            assert any(ref.reference.path[1:2] == ('ambience',) for ref in excluded)
            assert any(ref.reference.path[1:2] == ('temporalStructure',) for ref in excluded)
    finally:
        await p.aclose()


@pytest.mark.asyncio
async def test_frozen_v8_exact_scope_reads_back_without_weakening_new_scope_or_source_pins(
        tmp_path, monkeypatch):
    from drama_plugin.contracts.base import sha256_canonical
    from drama_plugin.execution.live_transport import TargetHttpTransport
    from drama_plugin.generation.compiler import PromptCompiler
    from drama_plugin.generation.contracts import FinalPromptArtifact, GenerationPreparation
    from drama_plugin.generation.seedance import ModelPolicyCatalog

    req, raw = material()
    text = '当前炉火从第一声持续到本段最后，刨声停止后才显露，不另起一层火声。'
    sound(raw)['ambience'] = [{'design': text}]
    sound(raw)['acousticSpace'] = '当前房间的声音近而短，不添加大厅回响。'
    p, compiler, package, rows = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        current = rows[0]
        operations = compiler.reader.operations
        select = operations.selected
        catalog = ModelPolicyCatalog()
        previous = catalog._policy(current['task'].target_model, 't5r-seedance-unit-layout-v8')
        assert catalog.uses_legacy_unit_scope(current['task'].target_model, previous.fingerprint)
        assert not catalog.uses_legacy_unit_scope(current['task'].target_model, catalog.policy(current['task'].target_model).fingerprint)
        assert not catalog.uses_legacy_unit_scope(current['task'].target_model, 'f' * 64)

        old_unit = await operations.select_unit(package, compiler.reader, phase_index=0,
            legacy_unit_scope=True)
        assert old_unit != current['task'].unit
        assert any(ref.reference.path[1:2] == ('ambience',)
            for ref in old_unit.execution_context.background_refs)
        old_task = current['task'].model_copy(update={'unit': old_unit})

        class FrozenV8Catalog(ModelPolicyCatalog):
            def policy(self, model):
                return self._policy(model, 't5r-seedance-unit-layout-v8')

        # Construct a sealed historical preparation using the actual old scope
        # algorithm and compiler. Only unadmitted fixture-owner checks are skipped.
        async def old_selected(package, task, reader, **kwargs):
            return await select(package, task, reader, admission_required=False,
                legacy_unit_scope=True)
        monkeypatch.setattr(operations, 'selected', old_selected)
        old_compiler = PromptCompiler(compiler.packages, compiler.artifacts, compiler.reader,
            FrozenV8Catalog(), _preview=True)
        result = await old_compiler.compile(package.artifact_reference(), old_task)
        assert result.preparation_ref, compiler.artifacts.diagnostics(result.diagnostics_ref)
        frozen_ready = compiler.artifacts.get(result.preparation_ref, GenerationPreparation)
        frozen = compiler.artifacts.get(frozen_ready.final_prompt_ref, FinalPromptArtifact)
        assert frozen.generator_policy_fingerprint == previous.fingerprint
        assert text not in frozen.prompt_text and text in current['final'].prompt_text

        async def offline_selected(package, task, reader, **kwargs):
            kwargs['admission_required'] = False
            return await select(package, task, reader, **kwargs)
        monkeypatch.setattr(operations, 'selected', offline_selected)
        def no_regeneration(*args, **kwargs):
            raise AssertionError('Frozen/cached requests must not be regenerated')
        monkeypatch.setattr(compiler.generator, 'generate', no_regeneration)
        assert (await compiler.prompt_ir(frozen_ready)).fingerprint == frozen.prompt_ir_fingerprint
        assert await compiler.validate_execution_sources(result.preparation_ref) == ()
        assert TargetHttpTransport.preview(frozen_ready, frozen, ledger=p.ledger)['content'][0]['text'] == frozen.prompt_text
        assert compiler.stale(result.preparation_ref, package.artifact_reference(), current['task'])

        # Both the new policy and its newly selected sources remain separate.
        key = lambda task, policy: sha256_canonical([package.artifact_reference().model_dump(mode='json'),
            task.model_dump(mode='json'), policy.fingerprint])
        assert key(old_task, previous) != key(old_task, catalog.policy(old_task.target_model))
        assert compiler.artifacts.final_for(key(old_task, previous)) == frozen_ready.final_prompt_ref
        assert compiler.artifacts.final_for(key(current['task'], catalog.policy(old_task.target_model))) == current['ready'].final_prompt_ref
        rebuilt = await compiler.compile(package.artifact_reference(), current['task'])
        assert compiler.artifacts.get(rebuilt.preparation_ref, GenerationPreparation).final_prompt_ref == current['ready'].final_prompt_ref

        # An unknown fingerprint cannot unlock the old scope read view.
        bad_final = FinalPromptArtifact.seal(**{**frozen.model_dump(exclude={'fingerprint'}),
            'generator_policy_fingerprint': 'f' * 64})
        bad_ready = GenerationPreparation.seal(**{**frozen_ready.model_dump(exclude={'fingerprint'}),
            'final_prompt_ref': compiler.artifacts.put(bad_final)})
        with pytest.raises(ValueError, match='UNIT_SCOPED_PROJECTION_DRIFT'):
            await compiler.prompt_ir(bad_ready)

        # Even an exact old policy cannot legitimize a changed source pin. Seal
        # the task envelope too, so rejection is by the source/scope comparison.
        pin = old_unit.fact_refs[-1]
        forged_pin = pin.model_copy(update={'reference': pin.reference.model_copy(update={'fingerprint': 'e' * 64})})
        drift_unit = old_unit.model_copy(update={'fact_refs': (*old_unit.fact_refs[:-1], forged_pin)})
        drift_task = old_task.model_copy(update={'unit': drift_unit})
        drift_final = FinalPromptArtifact.seal(**{**frozen.model_dump(exclude={'fingerprint'}),
            'task_fingerprint': sha256_canonical(drift_task)})
        drift_ready = GenerationPreparation.seal(**{**frozen_ready.model_dump(exclude={'fingerprint'}),
            'task': drift_task, 'final_prompt_ref': compiler.artifacts.put(drift_final)})
        with pytest.raises(ValueError, match='UNIT_SCOPED_PROJECTION_DRIFT'):
            await compiler.prompt_ir(drift_ready)
        diagnostics = await compiler.validate_execution_sources(compiler.artifacts.put(drift_ready))
        assert any(row.code == 'SCOPE_MISMATCH' and row.required for row in diagnostics)
    finally:
        await p.aclose()

@pytest.mark.asyncio
async def test_retained_owner_punctuation_is_not_rewritten_as_semicolons(tmp_path, monkeypatch):
    req, raw = material(single=True)
    exact = 'Ответ: «Сейчас.» Then listen; keep the room quiet.'
    sound(raw)['ambience'] = [{'design': exact}]
    p, compiler, package, rows = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        assert exact in rows[0]['wire']['content'][0]['text']
        assert 'Сейчас;' not in rows[0]['wire']['content'][0]['text']
    finally:
        await p.aclose()
