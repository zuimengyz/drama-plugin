"""Owner/contract regressions only; synthetic metadata, no author-quality claim."""
from copy import deepcopy
import socket
import pytest

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.creative_engine.contracts import Authority, RevisionRequest
from drama_plugin.professional_design.asset_sequence import AssetChoice, SceneAssetDraft, AssetPreparationPending
from drama_plugin.runtime.contracts import ArtifactReference, RunMode, RuntimeState
from drama_plugin.professional_design.reference_production import ReferenceProductionRecord, WORKFLOW
from drama_plugin.visual.frame_request import FrameSpec, compile_frame
from test_asset_sequence import plugin, request_for, resolve
from test_target_reference_production import ReferenceAuthor, reference_frame


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('This contract test must not use network or paid models')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket.socket, 'connect_ex', denied)


class CandidateAuthor(ReferenceAuthor):
    def __init__(self, *, same=False, fail=False):
        super().__init__()
        self.candidates = []
        self.same, self.fail = same, fail

    async def design_assets(self, request):
        if request.revision is None:
            return await super().design_assets(request)
        self.candidates.append(request)
        if self.fail:
            raise ValueError('OFFLINE_AUTHOR_FAILURE_NO_RETRY')
        rows = request.professional_context['assetPreparation']['assetCandidates']
        choices = []
        for row in rows:
            parent = row['asset']
            design = deepcopy(parent['content']['specializedAsset']['design'])
            if not self.same:
                design['proof'] = 'A source-justified alternative proof, offline fixture only'
            choices.append(AssetChoice(asset_type=parent['assetType'], name=parent['name'],
                design=design, reuse_selection=row['selection'],
                subject_selection=0 if parent['assetType'] == 'CHARACTER' else None))
        return SceneAssetDraft(assets=tuple(choices), rationale='Actual fixture author reassessed both prior choices; no required visual difference')


async def candidate_setup(tmp_path, monkeypatch, *, same=False, fail=False):
    monkeypatch.setenv('DRAMA_VIDEO_SEEDANCE_API_KEY', 'OFFLINE_TEST_SECRET')
    author = CandidateAuthor(same=same, fail=fail)
    p = plugin(tmp_path, monkeypatch, author)
    _, request = request_for(p, 's-1')
    ready, _ = await resolve(p, request, author)
    sequence = ready.professional_context['assetSequence']
    from drama_plugin.contracts.source_pin import SourcePin
    preparation = SourcePin.model_validate(sequence['preparedScenes'][-1]['preparationRef'])
    ids = tuple(a['id'] for a in sequence['currentAssets'])
    request = request.model_copy(update={'revision': RevisionRequest(owner=Authority.PROFESSIONAL,
        target_ref=request.source_refs[0], finding_ref=ArtifactReference(owner='offline-review',
            artifact_ref='offline-explicit-candidate-review'), instruction='Reassess these two selected asset proofs without changing stable identity or space')})
    return p, author, request, preparation, ids


@pytest.mark.asyncio
@pytest.mark.parametrize('same', [False, True])
async def test_formal_candidate_author_then_fresh_reference_authors_without_selection(tmp_path, monkeypatch, same):
    p, author, request, preparation, ids = await candidate_setup(tmp_path, monkeypatch, same=same)
    old_packet = p.asset_sequence.objects.read_ref(preparation)
    active = p.asset_sequence.objects._path('asset-scene-design',
        [old_packet['narrativeRef']['fingerprint'], old_packet['sceneId']])
    active_bytes = active.read_bytes()
    assets_before = sha256_canonical([dump_contract(a) for a in p.providers.asset.data.assets])
    revised = await p.tools.invoke('specialized_assets.revise_assets', request=request,
        preparation_ref=preparation, asset_ids=ids)
    assert revised != preparation
    assert len(author.candidates) == 1
    candidate_request = author.candidates[0]
    assert candidate_request.shot is None and candidate_request.scope.shot_id is None
    assert candidate_request.revision == request.revision
    assert [a['asset']['id'] for a in candidate_request.professional_context['assetPreparation']['assetCandidates']] == list(ids)
    packet = p.asset_sequence.objects.read_ref(revised)
    assert len(packet['requirements']) == 2
    assert not any(r.get('reuseAssetId') for r in packet['requirements'])
    assert {r['inheritedFromAssetId'] for r in packet['requirements']} == set(ids)
    assert p.asset_sequence.candidate_parent(revised) == preparation
    for row in packet['requirements']:
        parent = await p.providers.asset.get_asset(row['inheritedFromAssetId'])
        stable = {k:v for k,v in parent.content['specializedAsset']['design'].items() if k not in {'proof', 'referenceLighting'}}
        assert all(row['design'][k] == v for k,v in stable.items())
        assert row['narrativeRef'] == old_packet['narrativeRef']
    parent = p.runtime.create_run(work_id=request.scope.work_id, scene_id=request.scope.scene_id,
        mode=RunMode.EXPERIMENT, run_id='offline-candidate-parent')
    for row in packet['requirements']:
        result = await p.reference_production.pending(revised, parent.run_id, request,
            requirement_key=row['requirementKey'])
        child = next(r.artifact_ref for r in result.artifact_refs if r.owner == 'runtime')
        value = p.reference_production.get(child)
        assert p.runtime.store.load(child).state == RuntimeState.WAITING_EXTERNAL
        assert value.frame is not None and value.stage is None and value.quote is None
        assert value.required_action == 'REFERENCE_PREPARATION_NOT_SELECTED'
        prompt = value.frame['request']['body']['prompt']
        assert all(text in prompt for text in row['design'].values() if isinstance(text, str))
        if not same:
            # New selected proof is inherited, but must not replace the fresh
            # reference author's compatible viewing composition.
            assert value.frame['spec']['composition'] == reference_frame(row).composition
            from drama_plugin.professional_design.reference_design import verify_design_delivery
            verify_design_delivery(value.frame, row)
        with pytest.raises(ValueError, match='REFERENCE_PREPARATION_AUTHORITY_MISMATCH'):
            await p.reference_production.quote_reference(child, quote={}, balance={}, budget=1, execution_binding={})
    assert len(author.reference_requests) == 2
    assert active.read_bytes() == active_bytes
    assert sha256_canonical([dump_contract(a) for a in p.providers.asset.data.assets]) == assets_before
    row = packet['requirements'][0]
    with pytest.raises(ValueError, match='ASSET_PREPARATION_NOT_SELECTED'):
        await p.asset_sequence.accept(revised, row['requirementKey'], adoption_ref=preparation)
    read = await p.tools.invoke('specialized_assets.read_preparation', reference=AssetPreparationPending(revised).runtime_ref())
    assert read['preparationRef'] == dump_contract(revised)


@pytest.mark.asyncio
async def test_candidate_requires_exact_scope_and_is_not_a_production_preparation(tmp_path, monkeypatch):
    p, author, request, preparation, ids = await candidate_setup(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='EXPLICIT_ASSET_REVISION_REQUIRED'):
        await p.professional_design.revise_assets(request, preparation_ref=preparation, asset_ids=(*ids, ids[0]))
    revised = await p.professional_design.revise_assets(request, preparation_ref=preparation, asset_ids=ids)
    packet = p.asset_sequence.objects.read_ref(revised)
    production = p.runtime.create_run(work_id=request.scope.work_id, scene_id=request.scope.scene_id,
        mode=RunMode.PRODUCTION, run_id='offline-production-parent')
    with pytest.raises(ValueError, match='REFERENCE_PREPARATION_AUTHORITY_MISMATCH'):
        await p.reference_production.pending(revised, production.run_id, request,
            requirement_key=packet['requirements'][0]['requirementKey'])
    forged = deepcopy(packet)
    forged['professionalBasisRefs'] = []
    forged_ref = p.asset_sequence.objects.put('offline-unbound-candidate', forged)
    with pytest.raises(ValueError, match='ASSET_PREPARATION_NOT_SELECTED'):
        p.asset_sequence.candidate_parent(forged_ref)
    assert len(author.candidates) == 1 and not author.reference_requests


@pytest.mark.asyncio
async def test_candidate_author_failure_is_not_retried_or_selected(tmp_path, monkeypatch):
    p, author, request, preparation, ids = await candidate_setup(tmp_path, monkeypatch, fail=True)
    with pytest.raises(ValueError, match='OFFLINE_AUTHOR_FAILURE_NO_RETRY'):
        await p.tools.invoke('specialized_assets.revise_assets', request=request,
            preparation_ref=preparation, asset_ids=ids)
    assert len(author.candidates) == 1
    assert p.asset_sequence.candidate_parent(preparation) is None
    assert not author.reference_requests


def retained_fixture(p, request, preparation, requirement, asset_id, suffix):
    """Synthetic retained record plus genuinely accepted metadata-fixture parent."""
    run = p.runtime.create_run(work_id=request.scope.work_id, scene_id=request.scope.scene_id,
        mode=RunMode.EXPERIMENT, run_id='offline-old-reference-' + suffix, workflow_id=WORKFLOW)
    context = p.asset_sequence.objects.put('offline-old-reference-context-' + suffix, dump_contract(request))
    frame = reference_frame(requirement)
    value = ReferenceProductionRecord.seal(run_id=run.run_id, scope=run.scope,
        preparation_ref=preparation, requirement_key=requirement['requirementKey'],
        author_context_ref=context, frame=compile_frame(frame), asset_id=asset_id)
    p.reference_production.save(value)
    return frame


@pytest.mark.asyncio
async def test_actual_retained_frame_is_only_a_candidate_and_ambiguous_evidence_is_rejected(tmp_path, monkeypatch):
    p, author, request, preparation, ids = await candidate_setup(tmp_path, monkeypatch)
    rows = p.asset_sequence.objects.read_ref(preparation)['requirements']
    by_key = {a.content['specializedAsset']['requirementKey']: a.id for a in p.providers.asset.data.assets}
    old_frames = {}
    for i, row in enumerate(rows):
        identity = by_key[row['requirementKey']]
        old_frames[identity] = retained_fixture(p, request, preparation, row, identity, str(i))
    revised = await p.tools.invoke('specialized_assets.revise_assets', request=request,
        preparation_ref=preparation, asset_ids=ids)
    evidence = [r for r in author.candidates[0].professional_context['currentDesigns'] if r['domain'] == 'REFERENCE']
    assert {r['facts']['assetId'] for r in evidence} == set(ids)
    for row in evidence:
        assert FrameSpec.model_validate(row['facts']['frame']) == old_frames[row['facts']['assetId']]
    candidate = p.asset_sequence.objects.read_ref(revised)
    assert all(r['design']['proof'] != old_frames[r['inheritedFromAssetId']].composition for r in candidate['requirements'])
    # A second exact parent match has no trustworthy implicit "latest" authority.
    retained_fixture(p, request, preparation, rows[0], by_key[rows[0]['requirementKey']], 'ambiguous')
    with pytest.raises(ValueError, match='ASSET_REFERENCE_CANDIDATE_AMBIGUOUS'):
        await p.tools.invoke('specialized_assets.revise_assets', request=request,
            preparation_ref=preparation, asset_ids=ids)
    assert len(author.candidates) == 1


@pytest.mark.asyncio
async def test_invalid_revision_owner_source_and_stable_changes_do_not_enter_reference_author(tmp_path, monkeypatch):
    p, author, request, preparation, ids = await candidate_setup(tmp_path, monkeypatch)
    wrong_owner = request.model_copy(update={'revision': request.revision.model_copy(update={'owner': Authority.DIRECTION})})
    with pytest.raises(ValueError, match='EXPLICIT_ASSET_REVISION_REQUIRED'):
        await p.professional_design.revise_assets(wrong_owner, preparation_ref=preparation, asset_ids=ids)
    wrong_scene = request.model_copy(update={'canon': request.canon.model_copy(update={
        'scene': request.canon.scene.model_copy(update={'scene_text': 'Unselected replacement scene'})})})
    with pytest.raises(ValueError, match='ASSET_NARRATIVE_CANON_MISMATCH'):
        await p.professional_design.revise_assets(wrong_scene, preparation_ref=preparation, asset_ids=ids)
    with pytest.raises(ValueError, match='ASSET_REVISION_SCREENPLAY_BINDING_MISMATCH'):
        await p.professional_design.revise_assets(request.model_copy(update={'screenplay_context': {'unselected': 'screenplay'}}),
            preparation_ref=preparation, asset_ids=ids)
    assert not author.candidates
    original = author.design_assets
    async def changes_identity(value):
        draft = await original(value)
        first = draft.assets[0]
        changed = first.model_copy(update={'design': {**first.design, 'face': 'An unrelated newly invented identity'}})
        return draft.model_copy(update={'assets': (changed, *draft.assets[1:])})
    author.design_assets = changes_identity
    with pytest.raises(ValueError, match='ASSET_REVISION_STABLE_DESIGN_CHANGE'):
        await p.professional_design.revise_assets(request, preparation_ref=preparation, asset_ids=ids)
    assert len(author.candidates) == 1 and not author.reference_requests


@pytest.mark.asyncio
async def test_exact_adoption_record_has_authority_over_ambiguous_current_records(tmp_path, monkeypatch):
    p, author, request, preparation, ids = await candidate_setup(tmp_path, monkeypatch)
    row = p.asset_sequence.objects.read_ref(preparation)['requirements'][0]
    asset = next(a for a in p.providers.asset.data.assets if a.content['specializedAsset']['requirementKey'] == row['requirementKey'])
    retained_fixture(p, request, preparation, row, asset.id, 'selected-by-adoption')
    selected = p.reference_production.get('offline-old-reference-selected-by-adoption')
    retained_fixture(p, request, preparation, row, asset.id, 'another-current-record')
    basis = asset.content['specializedAsset']
    adoption = p.asset_sequence._original(basis, 'adoption')
    adoption = {**adoption, 'referenceProductionRef': dump_contract(selected.artifact_reference())}
    pin = p.asset_sequence.objects.put('offline-exact-adoption-reference', adoption)
    basis['adoptionRef'] = dump_contract(pin)
    basis['adoptionOriginal'] = adoption
    assert p.asset_sequence._proof(asset)
    await p.tools.invoke('specialized_assets.revise_assets', request=request,
        preparation_ref=preparation, asset_ids=ids)
    candidates = [r for r in author.candidates[0].professional_context['currentDesigns'] if r['domain'] == 'REFERENCE']
    assert len(candidates) == 1 and candidates[0]['facts']['assetId'] == asset.id
    assert FrameSpec.model_validate(candidates[0]['facts']['frame']) == FrameSpec.model_validate(selected.frame['spec'])
