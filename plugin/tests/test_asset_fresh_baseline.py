"""Explicit new art within the same Work; offline metadata, never real adoption."""
from copy import deepcopy

import pytest

from drama_plugin.contracts.base import dump_contract
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
from drama_plugin.professional_design.asset_sequence import (
    AssetChoice, AssetPreparationPending, SceneAssetDraft, SpecializedAssetSequence,
)
from drama_plugin.runtime.contracts import ArtifactReference
from test_asset_sequence import Author, accept_pending, film, plugin, request_for, resolve


class FreshAuthor(Author):
    def __init__(self):
        super().__init__()
        self.requests = []

    async def design_assets(self, request):
        self.requests.append(request)
        draft = await super().design_assets(request)
        if request.scope.scene_id != 's-1':
            return draft
        return SceneAssetDraft(assets=(*draft.assets,
            AssetChoice(asset_type='COSTUME', name='A coat', subject_selection=0,
                design={'material': 'The newly selected plain coat'}),
            AssetChoice(asset_type='PROP', name='Plane',
                design={'construction': 'The newly selected working hand plane'}),
            AssetChoice(asset_type='OTHER', name='Workbench fixture',
                design={'construction': 'The newly selected supporting fixture'})),
            rationale='A selected new art baseline, preserving the same dramatic people')


async def resolve_exact(p, request, author, pin):
    for _ in range(8):
        try:
            return await p.asset_sequence.prepare(request, author, narrative_ref=pin)
        except AssetPreparationPending as pending:
            await accept_pending(p, pending)
    raise AssertionError('Exact family preparation did not converge')


@pytest.mark.asyncio
async def test_fresh_same_work_excludes_old_assets_and_reuses_only_its_own_family(tmp_path, monkeypatch):
    old_author = FreshAuthor()
    p = plugin(tmp_path, monkeypatch, old_author)
    try:
        _, second = request_for(p, 's-2')
        await resolve(p, second, old_author)
        _, first = request_for(p, 's-1')
        old_pin = p.asset_sequence.selected(first)
        old_assets = deepcopy([dump_contract(a) for a in p.providers.asset.data.assets])
        old_ids = {a['id'] for a in old_assets}
        old_roots = {a['content']['specializedAsset']['stableIdentity'] for a in old_assets}
        legacy_index = {f.name: f.read_bytes() for f in p.asset_sequence.objects.root.glob('asset-narrative/*')}
        old_preparations = {f.name: f.read_bytes() for f in p.asset_sequence.objects.root.glob('asset-scene-design/*')}
        current = FreshAuthor()
        fresh_pin = p.asset_sequence.bind_film(first.scope.work_id, film(),
            source_ref=ArtifactReference(owner='offline-selected-art', artifact_ref='explicit-new-baseline'),
            fresh_baseline=True)
        assert fresh_pin != old_pin and p.asset_sequence.selected(first) == old_pin
        assert {f.name: f.read_bytes() for f in p.asset_sequence.objects.root.glob('asset-narrative/*')} == legacy_index
        with pytest.raises(AssetPreparationPending) as waiting:
            await p.asset_sequence.prepare(first, current, narrative_ref=fresh_pin)
        context = current.requests[0].professional_context['assetPreparation']
        assert context['assetCandidates'] == []
        assert all(row['inherited'] is None for row in context['subjectCandidates'])
        packet = p.asset_sequence.objects.read_ref(waiting.value.ref)
        assert {r['assetType'] for r in packet['requirements']} == {'CHARACTER', 'COSTUME', 'LOCATION', 'PROP', 'OTHER'}
        assert all(r['inheritedFromAssetId'] is None and r['identityRootAssetId'] is None
            and r['stableIdentity'] not in old_roots and r['revision'] == 1 for r in packet['requirements'])
        assert all(r['narrativeRef'] == dump_contract(fresh_pin) for r in packet['requirements'])
        old_a = next(a for a in p.providers.asset.data.assets if a.asset_type == 'CHARACTER'
            and a.content['specializedAsset']['subjectId'] == 'A')
        with pytest.raises(ValueError, match='ASSET_REUSE_FAMILY_MISMATCH'):
            p.asset_sequence._project(fresh_pin, 's-1', [{'id': 'A'}], {'A': old_a}, [],
                SceneAssetDraft(assets=(AssetChoice(asset_type='CHARACTER', name='A', subject_selection=0,
                    design={'face': 'The approved new face'}),), rationale='Test mixed family rejection'))
        await accept_pending(p, waiting.value)
        first_ready = await p.asset_sequence.prepare(first, current, narrative_ref=fresh_pin)
        fresh_a = next(a for a in first_ready.professional_context['assetSequence']['currentAssets'] if a['assetType'] == 'CHARACTER')
        count = len(p.providers.asset.data.assets)
        await accept_pending(p, waiting.value)  # Exact acceptance replay must not duplicate registration.
        assert len(p.providers.asset.data.assets) == count
        next_ready = await resolve_exact(p, second, current, fresh_pin)
        inherited = current.requests[-1].professional_context['assetPreparation']
        assert inherited['subjectCandidates'][0]['inherited']['id'] == fresh_a['id']
        assert all(row['asset']['id'] not in old_ids for row in inherited['assetCandidates'])
        assert {a['id'] for a in next_ready.professional_context['assetSequence']['currentAssets']}.isdisjoint(old_ids)
        assert [dump_contract(a) for a in p.providers.asset.data.assets[:len(old_assets)]] == old_assets
        assert all((p.asset_sequence.objects.root/'asset-scene-design'/name).read_bytes() == value
            for name, value in old_preparations.items())
        legacy = await p.professional_design.prepare_assets(second)
        assert {a['id'] for a in legacy.professional_context['assetSequence']['currentAssets']} <= old_ids
        assert p.asset_sequence.selected(first) == old_pin
        with p.ledger.transaction() as db:
            assert db.execute('SELECT count(*) FROM production_operation').fetchone()[0] == 0
    finally:
        await p.aclose()


@pytest.mark.asyncio
async def test_exact_fresh_binding_survives_restart_and_service_original_recovery(tmp_path, monkeypatch):
    author = FreshAuthor()
    p = plugin(tmp_path, monkeypatch, author)
    try:
        _, first = request_for(p, 's-1')
        original_pin = p.asset_sequence.selected(first)
        source_ref = ArtifactReference(owner='offline-selected-art', artifact_ref='new-baseline-for-recovery')
        pin = p.asset_sequence.bind_film(first.scope.work_id, film(), source_ref=source_ref, fresh_baseline=True)
        ready = await resolve_exact(p, first, author, pin)
        before = [dump_contract(a) for a in p.providers.asset.data.assets]
        restored = SpecializedAssetSequence(DirectorArtifactStore(tmp_path/'restored-originals'), p.providers.asset, p.providers.media)
        assert restored.bind_film(first.scope.work_id, film(), source_ref=source_ref, fresh_baseline=True) == pin
        restored_request = first.model_copy(update={'professional_context': {
            'currentDesigns': [{'facts': {'assetNarrativeRef': dump_contract(pin)}}]}})
        assert restored.selected(restored_request) == pin
        reread = await restored.prepare(restored_request, author)
        assert reread.professional_context['assetSequence']['currentAssets'] == ready.professional_context['assetSequence']['currentAssets']
        assert [dump_contract(a) for a in p.providers.asset.data.assets] == before
        assert author.scenes == ['s-1']
        assert p.asset_sequence.selected(first) == original_pin
        # A separate legacy reader has no fresh narrative original cached. It
        # still excludes fresh assets before attempting design/adoption recovery.
        cold = SpecializedAssetSequence(DirectorArtifactStore(tmp_path/'cold-legacy-originals'), p.providers.asset, p.providers.media)
        assert await cold._available(first.scope.work_id) == []
        with pytest.raises(ValueError, match='ASSET_NARRATIVE_BINDING_CONFLICT'):
            await restored.prepare(restored_request, author, narrative_ref=original_pin)
        with pytest.raises(ValueError, match='ASSET_NARRATIVE_CANON_MISMATCH'):
            await restored.prepare(first.model_copy(update={'scope': first.scope.model_copy(update={'scene_id': 'missing'})}),
                author, narrative_ref=pin)
    finally:
        await p.aclose()


@pytest.mark.asyncio
async def test_fresh_reference_child_skips_only_accepted_requirements_in_exact_family(tmp_path, monkeypatch):
    from drama_plugin.professional_design.reference_production import TargetReferenceProduction
    author = FreshAuthor()
    p = plugin(tmp_path, monkeypatch, author)
    try:
        _, request = request_for(p, 's-1')
        await resolve(p, request, author)
        pin = p.asset_sequence.bind_film(request.scope.work_id, film(),
            source_ref=ArtifactReference(owner='offline-selected-art', artifact_ref='fresh-child-selection'), fresh_baseline=True)
        with pytest.raises(AssetPreparationPending) as waiting:
            await p.asset_sequence.prepare(request, author, narrative_ref=pin)
        await accept_pending(p, waiting.value)
        # All requirements are registered. The native child must take recovery,
        # not start a duplicate child because its discovery used the legacy family.
        production = TargetReferenceProduction(p)
        outcome = await production.pending(waiting.value.ref, 'offline-film-sequence', request)
        assert outcome.external_ref.owner == 'specialized-asset-preparation'
        assert outcome.external_ref.artifact_ref.endswith(waiting.value.ref.fingerprint)
    finally:
        await p.aclose()


@pytest.mark.asyncio
async def test_exact_pending_requirements_create_separate_unadopted_reference_children(tmp_path, monkeypatch):
    from drama_plugin.professional_design.reference_production import TargetReferenceProduction
    author = FreshAuthor()
    p = plugin(tmp_path, monkeypatch, author)
    try:
        _, request = request_for(p, 's-1')
        pin = p.asset_sequence.bind_film(request.scope.work_id, film(),
            source_ref=ArtifactReference(owner='offline-selected-art', artifact_ref='batch-reference-preparation'), fresh_baseline=True)
        with pytest.raises(AssetPreparationPending) as waiting:
            await p.asset_sequence.prepare(request, author, narrative_ref=pin)
        packet = p.asset_sequence.objects.read_ref(waiting.value.ref)
        production = TargetReferenceProduction(p)
        async def no_execution(run_id):
            # Exercise native creation/retention only; never run even a mock author.
            return p.runtime.store.load(run_id)
        monkeypatch.setattr(production, 'resume', no_execution)
        keys = [row['requirementKey'] for row in packet['requirements'][:2]]
        children = []
        for key in keys:
            result = await production.pending(waiting.value.ref, 'offline-film-sequence', request, requirement_key=key)
            children.append(next(ref.artifact_ref for ref in result.artifact_refs if ref.owner == 'runtime'))
        assert len(set(children)) == 2 and p.providers.asset.data.assets == []
        for run_id, key in zip(children, keys, strict=True):
            record = production.get(run_id)
            assert record.requirement_key == key and record.adoption_ref is None and record.asset_id is None
            assert record.preparation_ref == waiting.value.ref
        replay = await production.pending(waiting.value.ref, 'offline-film-sequence', request, requirement_key=keys[0])
        assert children[0] in {ref.artifact_ref for ref in replay.artifact_refs}
        with pytest.raises(ValueError, match='REFERENCE_REQUIREMENT_NOT_PENDING'):
            await production.pending(waiting.value.ref, 'offline-film-sequence', request, requirement_key='f'*64)
        await accept_pending(p, waiting.value)
        count = len(p.providers.asset.data.assets)
        with pytest.raises(ValueError, match='REFERENCE_REQUIREMENT_ALREADY_ACCEPTED'):
            await production.pending(waiting.value.ref, 'offline-film-sequence', request, requirement_key=keys[0])
        assert len(p.providers.asset.data.assets) == count
        _, second = request_for(p, 's-2')
        with pytest.raises(AssetPreparationPending) as next_scene:
            await p.asset_sequence.prepare(second, author, narrative_ref=pin)
        next_packet = p.asset_sequence.objects.read_ref(next_scene.value.ref)
        reused = next(row for row in next_packet['requirements'] if row.get('reuseAssetId'))
        with pytest.raises(ValueError, match='REFERENCE_REQUIREMENT_NOT_PENDING'):
            await production.pending(next_scene.value.ref, 'offline-film-sequence', second,
                requirement_key=reused['requirementKey'])
        with p.ledger.transaction() as db:
            assert db.execute('SELECT count(*) FROM production_operation').fetchone()[0] == 0
    finally:
        await p.aclose()
