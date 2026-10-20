"""Offline timing transport proofs, not evidence of authored creative quality."""
from copy import deepcopy
import json
import re
import socket

import pytest

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.execution.live_transport import TargetHttpTransport
from drama_plugin.generation.contracts import FinalPromptArtifact, GenerationPreparation
from drama_plugin.generation.seedance import ModelPolicyCatalog, SeedanceTargetAdapter
from test_event_scope_delivery import material, pipeline


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('Timing preamble tests cannot call models or providers')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)


def without_windows(value):
    """Remove this fixture's author text ranges; no production time inference."""
    if isinstance(value, str):
        return re.sub(r'\d+–\d+s: ', '', value)
    if isinstance(value, list):
        return [without_windows(item) for item in value]
    if isinstance(value, dict):
        return {key: without_windows(item) for key, item in value.items()}
    return value


@pytest.mark.parametrize('duration', [8000, None])
@pytest.mark.parametrize('windows', [False, True])
async def test_duration_preamble_does_not_claim_unwritten_windows_and_preserves_authored_ranges(
        tmp_path, monkeypatch, duration, windows):
    req, raw = material(single=True)
    if not windows:
        raw = without_windows(raw)
    before = deepcopy(raw)
    p, compiler, package, rows = await pipeline(tmp_path, monkeypatch, req, raw, duration=duration)
    try:
        row = rows[0]
        text = row['wire']['content'][0]['text']
        preamble = text.split('\n', 1)[0]
        assert '下述时间窗' not in preamble and '预计节拍' not in preamble
        assert '保持下述动作与声音注明的先后、并行与结束条件' not in preamble
        assert '不为凑时长补演或循环' not in preamble
        assert row['wire']['duration'] == (-1 if duration is None else 8)
        assert ('自动时长范围4–15秒，上限不是填满目标' in preamble) == (duration is None)
        assert '本段生成时长8秒' not in preamble
        assert ('0–2s: the keeper supports the packet' in text) == windows
        assert ('2–5s: the courier speaks while the keeper holds it still.' in text) == windows
        assert ('5–8s: the packet is supported by the keeper' in text) == windows
        assert ('0–2s: one cloth contact at the receiving grip' in text) == windows
        assert ('2–5s: speak once over the continuing handoff.' in text) == windows
        assert ('5–8s: listen; do not repeat the line.' in text) == windows
        assert raw == before
        assert json.loads(json.dumps(row['wire']))['content'][0]['text'] == row['final'].prompt_text
    finally:
        await p.aclose()


def test_absent_profile_does_not_fabricate_duration():
    assert SeedanceTargetAdapter.segment_timing(None) == ''


async def test_frozen_v7_prompt_replays_exactly_while_new_compilation_uses_distinct_policy(
        tmp_path, monkeypatch):
    req, raw = material(single=True)
    p, compiler, package, rows = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        row = rows[0]
        ready, current, task = row['ready'], row['final'], row['task']
        # Reconstruct a frozen v7 final from the exact previous preamble. The
        # production read/replay path must never invoke a new text generator.
        catalog = ModelPolicyCatalog()
        previous = catalog._policy(task.target_model, 't5r-seedance-unit-layout-v7')
        current_policy = catalog.policy(task.target_model)
        assert previous.fingerprint != current_policy.fingerprint
        old_preamble = ('本段生成时长8秒；下述时间窗是本段内的预计节拍，不代表切镜。'
                        '保持注明的先后、并行与结束条件，不为凑时长补演或循环。')
        old_text = old_preamble + '\n' + current.prompt_text.split('\n', 1)[1]
        frozen = FinalPromptArtifact.seal(**{**current.model_dump(exclude={'fingerprint'}),
            'generator_policy_fingerprint': previous.fingerprint, 'prompt_text': old_text})
        frozen_ref = compiler.artifacts.put(frozen)
        frozen_ready = GenerationPreparation.seal(**{**ready.model_dump(exclude={'fingerprint'}),
            'final_prompt_ref': frozen_ref})
        frozen_ready_ref = compiler.artifacts.put(frozen_ready)
        old_key = sha256_canonical([package.artifact_reference().model_dump(mode='json'),
            task.model_dump(mode='json'), previous.fingerprint])
        current_key = sha256_canonical([package.artifact_reference().model_dump(mode='json'),
            task.model_dump(mode='json'), current_policy.fingerprint])
        compiler.artifacts.register_final(old_key, frozen_ref)
        assert old_key != current_key
        selected = compiler.reader.operations.selected
        async def offline_selected(package, task, reader, **kwargs):
            return await selected(package, task, reader, admission_required=False)
        monkeypatch.setattr(compiler.reader.operations, 'selected', offline_selected)
        restored_ir = await compiler.prompt_ir(frozen_ready)
        assert restored_ir.fingerprint == frozen.prompt_ir_fingerprint
        assert compiler.stale(frozen_ready_ref, package.artifact_reference(), task)
        def no_regeneration(*args, **kwargs):
            raise AssertionError('Frozen or cached final text must never be regenerated')
        monkeypatch.setattr(compiler.generator, 'generate', no_regeneration)
        restored = compiler.artifacts.get(frozen_ready.final_prompt_ref, FinalPromptArtifact)
        wire = TargetHttpTransport.preview(frozen_ready, restored, ledger=p.ledger)
        assert wire['content'][0]['text'] == old_text
        rebuilt = await compiler.compile(package.artifact_reference(), task)
        assert compiler.artifacts.get(rebuilt.preparation_ref, GenerationPreparation).final_prompt_ref == ready.final_prompt_ref
        assert compiler.artifacts.final_for(old_key) == frozen_ref
        assert compiler.artifacts.final_for(current_key) == ready.final_prompt_ref
        assert compiler.artifacts.get(frozen_ref, FinalPromptArtifact) == frozen
    finally:
        await p.aclose()
