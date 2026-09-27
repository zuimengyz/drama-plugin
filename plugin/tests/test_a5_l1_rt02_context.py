"""Still execution authority comes from the Host caller, never the candidate."""
from copy import deepcopy
from pathlib import Path
from typing import Any, cast
import pytest

# Retained provider contracts; active Ark admission has a separate test suite.
pytestmark = pytest.mark.usefixtures("retained_production_policy")
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.professional import CreativeBible
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.providers.base import MemoryProvider
from drama_plugin.visual import production
from drama_plugin.professional import approval_subject, validate_bible
from drama_plugin.hosts import route_production as host
from drama_plugin.visual.frame_request import compile_frame
from r3d_helpers import case, approval, use
from test_still_knowledge import scene
from test_production_route import route


def opted_scene(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, owner: str = 'cinematography') -> dict[str, Any]:
    f: dict[str, Any] = scene(tmp_path, monkeypatch)  # type: ignore[no-untyped-call]
    c = case(department=owner); trusted = approval(c)
    for key, value in c['artifacts'].items(): f['host'].store.put(key, value)
    f['current'].update(c['current'])
    old = next(p for p in f['pins'] if f['host'].store.read_ref(p).get('createdByCapability') == owner)
    b = CreativeBible.model_validate(f['host'].store.read_ref(old)); r = b.content[0]
    r = r.model_copy(update={'source_refs': (*r.source_refs, c['ref'], trusted), 'interpretation_uses': (use(c, r.values),)})
    b = b.model_copy(update={'content': (r,)})
    review = f['host'].store.put('approval:rt02-'+owner, dict(kind='PROFESSIONAL_CREATIVE_APPROVAL', subjectId=b.id,
        workRef=b.work_ref, decision='APPROVE', subjectFingerprint=approval_subject(b), approvedBy=list(b.approved_by)))
    b = b.model_copy(update={'approval_refs': (review,)})
    new = f['host'].store.put('bible:rt02-'+owner, dump_contract(b)).model_copy(update={'kind': old.kind})
    f['current'].update({new.key:new.fingerprint, review.key:review.fingerprint})
    f['pins'] = [new if p == old else p for p in f['pins']]
    f['rows'] = [r.model_copy(update={'inputs':tuple(l.model_copy(update={'pin':new}) if l.pin == old else l for l in r.inputs)}) for r in f['rows']]
    f['work'].content['visualSourceCurrent'] = f['current']
    f.update(trusted=(trusted,), c=c, opted_bible=b)
    return f


def prepare(f: dict[str, Any], refs: tuple[SourcePin, ...] = ()) -> Any:
    return host.prepare_still_projection(f['work'], f['spec'], f['ir'], scope=f['scope'],
        source_pins=tuple(f['pins']), rows=tuple(f['rows']), approved_interpretation_refs=refs)


@pytest.mark.parametrize('owner', ['cinematography', 'lighting-design'])
def test_projection_replay_and_prompt_isolation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, owner: str) -> None:
    f = opted_scene(tmp_path, monkeypatch, owner)
    originals = host._still_originals(f['host'].store, tuple(f['pins']), f['current'])
    assert validate_bible(f['opted_bible'], originals, f['current'], approved_interpretation_refs=f['trusted'])['validationStatus'] == 'PASS'
    compiled = compile_frame(prepare(f, f['trusted']), f['t'])
    assert host.validate_still_professional_sources(f['work'], compiled, approved_interpretation_refs=f['trusted'])
    for refs in [(), (approval(case(identity='other')), )]:
        with pytest.raises(ValueError, match='USER_INTERPRETATION_APPROVAL_REQUIRED'): prepare(f, refs)
        with pytest.raises(ValueError, match='USER_INTERPRETATION_APPROVAL_REQUIRED'):
            host.validate_still_professional_sources(f['work'], compiled, approved_interpretation_refs=refs)
    prompt = compiled['prompt_ir_compilation']['prompt']
    for token in ['approved_interpretation_refs', f['trusted'][0].key, f['c']['item']['meaning'], 'actorType', 'interpretationUses']:
        assert token not in prompt
    f['work'].content['approved_interpretation_refs'] = [dump_contract(x) for x in f['trusted']]
    with pytest.raises(ValueError, match='USER_INTERPRETATION_APPROVAL_REQUIRED'):
        host.validate_still_professional_sources(f['work'], compiled)


@pytest.mark.parametrize('stale', ['ref', 'approval_ref', 'source_ref'])
def test_stale_pins_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stale: str) -> None:
    f = opted_scene(tmp_path, monkeypatch); compiled = compile_frame(prepare(f, f['trusted']), f['t'])
    f['work'].content['visualSourceCurrent'][f['c'][stale].key] = 'f'*64
    with pytest.raises(ValueError, match='STALE'):
        host.validate_still_professional_sources(f['work'], compiled, approved_interpretation_refs=f['trusted'])


def test_cross_work_and_wrong_receipt_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    f = opted_scene(tmp_path, monkeypatch)
    trusted = f['trusted'][0]; raw = deepcopy(f['c']['artifacts'][trusted.key]); raw['workRef'] = 'other-work'
    forged = f['host'].store.put(trusted.key, raw)
    with pytest.raises(ValueError, match='USER_INTERPRETATION_APPROVAL_REQUIRED'): prepare(f, (forged,))
    f['scope'] = f['scope'].model_copy(update={'work_id':'other-work'})
    with pytest.raises(ValueError, match='STILL_MOVIE_OR_SHOT_SCOPE'): prepare(f, f['trusted'])


@pytest.mark.asyncio
@pytest.mark.parametrize('command', ['reserve', 'begin-submission'])
async def test_formal_entry_propagates_only_external_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str) -> None:
    f = opted_scene(tmp_path, monkeypatch); compiled = compile_frame(prepare(f, f['trusted']), f['t'])
    raw = route(tmp_path).model_dump(mode='json')  # type: ignore[no-untyped-call]
    raw['work_id'] = 'work'
    f['work'].content.update(productionRoute=raw, productionStage={'frames':{'shot':compiled},
        'attempts':[{'attempt_id':'offline','shot_id':'shot','request':compiled['request']}]})
    class Memory:
        async def get_work(self, work_id: str) -> Any: return deepcopy(f['work'])
        async def save_work(self, *args: Any) -> None: raise AssertionError('Must not persist or spend')
    class AdmissionPassed(Exception): pass
    def stop(*args: Any, **kwargs: Any) -> None: raise AdmissionPassed
    async def jurisdiction(*args: Any) -> None: pass
    # Isolate unrelated jurisdiction and ledger mutation, retaining real immutable
    # source replay, prompt binding, projection and all Interpretation validators.
    monkeypatch.setattr(host, 'validate_route_direction_sources', jurisdiction)
    monkeypatch.setattr(production, 'check_campaign', lambda state: None)
    monkeypatch.setattr(host, 'attempt_frame', lambda state, attempt: state['frames'][attempt['shot_id']])
    monkeypatch.setattr(production, 'reserve' if command == 'reserve' else 'begin_submission', stop)
    payload = {'shot_id':'shot'} if command == 'reserve' else {'attempt_id':'offline'}
    with pytest.raises(AdmissionPassed):
        await host.operate(cast(MemoryProvider, Memory()), 'work', command, payload, approved_interpretation_refs=f['trusted'])
    fake_payloads: list[dict[str, Any]] = [payload, {**payload, 'approved_interpretation_refs':[dump_contract(x) for x in f['trusted']]}]
    for fake in fake_payloads:
        with pytest.raises(ValueError, match='USER_INTERPRETATION_APPROVAL_REQUIRED'):
            await host.operate(cast(MemoryProvider, Memory()), 'work', command, fake)


@pytest.mark.parametrize('mutation', ['workRef', 'subjectFingerprint', 'evidenceFingerprint'])
def test_explicitly_trusted_wrong_receipt_still_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    from drama_plugin.interpretation import validate_consumption
    f = opted_scene(tmp_path, monkeypatch); c = f['c']; old = f['trusted'][0]
    raw = deepcopy(c['artifacts'][old.key]); raw[mutation] = 'other-work' if mutation == 'workRef' else 'f'*64
    new = f['host'].store.put(old.key, raw)
    originals = {**c['artifacts'], new.key:raw}; current = {**c['current'], new.key:new.fingerprint}
    record = f['opted_bible'].content[0]
    use_value = record.interpretation_uses[0].model_copy(update={'approval_ref':new})
    with pytest.raises(ValueError, match='SCOPE_OR_VERSION_MISMATCH'):
        validate_consumption(use_value, department='cinematography', work_ref='work', scope_refs=record.scope_refs,
            values=record.values, artifacts=originals, current=current, approved_refs=(new,))
    with pytest.raises(ValueError, match='CONSUMER_SCOPE_MISMATCH'):
        validate_consumption(record.interpretation_uses[0], department='cinematography', work_ref='other-work',
            scope_refs=record.scope_refs, values=record.values, artifacts=c['artifacts'], current=c['current'], approved_refs=(old,))


def test_specialized_asset_leaf_revalidates_upstream_authority(tmp_path: Path) -> None:
    from r3d_r_helpers import blocker_case
    from drama_plugin.contracts.base import sha256_canonical as fp
    from drama_plugin.visual.still_knowledge import Leaf, MappingRow, Scope, _leaf
    f = blocker_case(tmp_path); h = f['host']; b = f['candidate']; current = f['current']
    review = h.store.put('asset-review:rt02', dict(kind='SPECIALIZED_ASSET_REVIEW', decision='APPROVE', workId='work', reviewer='offline',
        checkedBoundaries=['DRAMATURGY','DIRECTOR_INTENT','SOURCE_WORLD','GLOBAL_STYLE'], subjectFingerprint=fp(dump_contract(b,exclude={'approval_ref'}))))
    current[review.key] = review.fingerprint; b = b.model_copy(update={'approval_ref':review})
    refs = (f['trusted'],); pin = h.submit(b, current=current, approved_interpretation_refs=refs); current[pin.key] = pin.fingerprint
    originals, resolved = h._inputs(b, current); originals[pin.key] = dump_contract(b)
    leaf = Leaf(pin=pin, pointer='/assets/0/decisions/face/text')
    row = MappingRow(mapping_id='face', capability_ids=('F01',), owner='specialized-asset-design', inputs=(leaf,), target='/subjects/0/face')
    scope = Scope(work_id='work', scene_id='s', shot_id='shot', actors={'c':'opening'})
    assert _leaf(leaf, row, scope, originals, resolved, ['c'], approved_interpretation_refs=refs) == b.assets[0].decisions['face'].text
    with pytest.raises(ValueError, match='USER_INTERPRETATION_APPROVAL_REQUIRED'):
        _leaf(leaf, row, scope, originals, resolved, ['c'])
