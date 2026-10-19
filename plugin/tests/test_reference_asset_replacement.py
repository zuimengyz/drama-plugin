"""Existing owner contracts, synthetic metadata only; no model, media, or network."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.film_storage.projection import select_reference_asset
from drama_plugin.professional_design.reference_production import ReferenceProductionRecord
from drama_plugin.runtime.contracts import CapabilityInput, RuntimeState
from test_reference_candidate_handoff import (
    assets, author_counts, candidate_source, quote, reuse, selected_source,
)
from test_target_reference_production import fake_persistence, fake_submission, pass_review


class CurrentAssetIndex:
    """Fictional Film index mirrors Asset registration and existing row updates."""
    def __init__(self, p):
        self.plugin, self.client = p, self
        self.tables = {'drama_asset': {}, 'drama_character': {}}
        self.events = []
        for asset in p.providers.asset.data.assets:
            self.asset_event(asset)
    def asset_event(self, asset):
        s=asset.content['specializedAsset']
        self.tables['drama_asset'][asset.id] = dict(id=asset.id, work_id=asset.work_id,
            identity_key=s['stableIdentity'], character_id=s.get('subjectId'),
            asset_type=asset.asset_type.value,
            version=s['revision'], state='ADOPTED', media_id=asset.reference_media_ids[0])
        if s.get('subjectId'):
            self.tables['drama_character'].setdefault(s['subjectId'],
                dict(id=s['subjectId'], adopted_asset_id=asset.id))
    def scene_asset_event(self, *args): pass
    async def query(self, table, filters, limit=100):
        return [dict(row) for row in self.tables[table].values()
            if all(row.get(k)==v for k,v in filters.items())][:limit]
    def row(self, table, event, order, **fields):
        return dict(table=table,fields=fields,event=event,order=order)
    async def rows(self, rows):
        for row in rows:
            value=row['fields']; self.tables[row['table']][value['id']].update(value)
        self.events.extend(deepcopy(rows))


async def awaiting_adoption(p, old, run_id, monkeypatch):
    value=await reuse(p,old,run_id)
    posts=[];fake_submission(monkeypatch,posts);fake_persistence(monkeypatch,p)
    await quote(p,run_id)
    assert (await p.reference_production.resume(run_id)).state==RuntimeState.WAITING_USER
    value=p.reference_production.get(run_id)
    await p.decide_target_run(run_id,decision_id=p.runtime.decision_id(run_id),accepted=True,
        source_ref=value.artifact_reference())
    run=await p.reference_production.resume(run_id)
    assert run.cursor==4 and len(posts)==1
    value=await pass_review(p,run_id)
    return value,posts


@pytest.mark.asyncio
async def test_exact_native_new_image_replaces_current_index_without_rewriting_design(tmp_path,monkeypatch):
    p,_,_,old,author=await selected_source(tmp_path,monkeypatch)
    before=assets(p);calls=author_counts(author)
    store=CurrentAssetIndex(p);p.asset_sequence.film_storage=store
    value,posts=await awaiting_adoption(p,old,'offline-explicit-reference-replacement',monkeypatch)
    assert assets(p)==before  # Review is not adoption.
    await p.decide_target_run(value.run_id,decision_id=p.runtime.decision_id(value.run_id),
        accepted=True,source_ref=value.artifact_reference())
    run=await p.reference_production.resume(value.run_id)
    assert run.state==RuntimeState.SUCCEEDED
    final=p.reference_production.get(value.run_id)
    new=await p.providers.asset.get_asset(final.asset_id)
    assert new.reference_media_ids==[final.delivery['mediaId']]
    assert new.content['specializedAsset']['designRef']==before[0]['content']['specializedAsset']['designRef']
    assert new.content['specializedAsset']['revision']==before[0]['content']['specializedAsset']['revision']
    assert assets(p)[:len(before)]==before  # Original Assets and adoption originals remain unchanged.
    await select_reference_asset(store,new,'offline-exact-asset-event',100)
    old_id=before[0]['id'];subject=new.content['specializedAsset']['subjectId']
    assert store.tables['drama_asset'][old_id]['state']=='SUPERSEDED'
    assert store.tables['drama_character'][subject]['adopted_asset_id']==new.id
    selected=await p.asset_sequence._available(new.work_id)
    assert p.asset_sequence._latest(selected,new.content['specializedAsset']['stableIdentity']).id==new.id
    assert (await p.reference_production.resume(value.run_id)).state==RuntimeState.SUCCEEDED
    await select_reference_asset(store,new,'offline-exact-asset-event',100)
    assert len(assets(p))==len(before)+1 and len(posts)==1 and author_counts(author)==calls
    assert final.frame==old.frame


@pytest.mark.asyncio
async def test_candidate_item_selection_merges_without_selecting_its_unapproved_sibling(tmp_path,monkeypatch):
    p,request,_,old,author=await candidate_source(tmp_path,monkeypatch)
    store=CurrentAssetIndex(p);p.asset_sequence.film_storage=store
    packet=p.asset_sequence.objects.read_ref(old.preparation_ref)
    parent=p.asset_sequence.candidate_parent(old.preparation_ref)
    parent_packet=p.asset_sequence.objects.read_ref(parent)
    before=deepcopy(parent_packet['requirements']);calls=author_counts(author)
    value,posts=await awaiting_adoption(p,old,'offline-explicit-candidate-adoption',monkeypatch)
    await p.decide_target_run(value.run_id,decision_id=p.runtime.decision_id(value.run_id),
        accepted=True,source_ref=value.artifact_reference())
    assert (await p.reference_production.resume(value.run_id)).state==RuntimeState.SUCCEEDED
    final=p.reference_production.get(value.run_id)
    new=await p.providers.asset.get_asset(final.asset_id)
    await select_reference_asset(store,new,'offline-first-candidate',100)
    path=p.asset_sequence.objects._path('asset-scene-design',[packet['narrativeRef']['fingerprint'],packet['sceneId']])
    selected=SourcePin.model_validate(p.asset_sequence.objects._read(path))
    current=p.asset_sequence.objects.read_ref(selected)
    own=next(r for r in packet['requirements'] if r['requirementKey']==old.requirement_key)
    assert next(r for r in current['requirements'] if r['stableIdentity']==own['stableIdentity'])==own
    assert [r for r in current['requirements'] if r['stableIdentity']!=own['stableIdentity']]==[
        r for r in before if r['stableIdentity']!=own['stableIdentity']]
    # The same frozen parent/candidate is still readable after an exact partial adoption.
    assert p.asset_sequence.candidate_parent(parent)==selected
    assert p.asset_sequence.candidate_parent(old.preparation_ref)==selected
    assert p.asset_sequence.objects.read_ref(old.preparation_ref)==packet
    assert len(posts)==1 and author_counts(author)==calls


@pytest.mark.asyncio
@pytest.mark.parametrize('tamper',['no-decision','wrong-hash','wrong-parent','wrong-approval'])
async def test_reference_replacement_cannot_bypass_existing_exact_approval(tmp_path,monkeypatch,tamper):
    p,_,_,old,_=await selected_source(tmp_path,monkeypatch)
    store=CurrentAssetIndex(p);p.asset_sequence.film_storage=store
    value,_=await awaiting_adoption(p,old,'offline-replacement-negative-'+tamper,monkeypatch)
    before=assets(p)
    if tamper!='no-decision':
        await p.decide_target_run(value.run_id,decision_id=p.runtime.decision_id(value.run_id),
            accepted=True,source_ref=value.artifact_reference())
        inp=CapabilityInput(run_id=value.run_id,operation_id='offline-adopt-only',scope=value.scope)
        await p.reference_production.adopt(inp)
        value=p.reference_production.get(value.run_id)
    original={'decision':'ADOPT','workId':value.scope.work_id,'subjectFingerprint':value.requirement_key,
        'referenceMediaIds':[value.delivery['mediaId']],'referenceContentHash':value.delivery['contentHash'],
        'reviewOriginal':value.stage['attempts'][0]['review'],
        'referenceProductionRef':dump_contract(value.artifact_reference()),
        'userDecisionRef':dump_contract(value.adoption_ref) if value.adoption_ref else None}
    if tamper=='wrong-hash':original['referenceContentHash']='0'*64
    if tamper=='wrong-approval':original['userDecisionRef']=dump_contract(value.cost_ref)
    review=p.asset_sequence.objects.put('offline-negative-adoption-'+tamper,original)
    prep=value.preparation_ref
    if tamper=='wrong-parent':
        packet=p.asset_sequence.objects.read_ref(prep);packet['professionalBasisRefs']=[]
        packet['requirements']=deepcopy(packet['requirements']);packet['requirements'][0]['stableIdentity']='foreign'
        prep=p.asset_sequence.objects.put('offline-foreign-preparation',packet)
    with pytest.raises(ValueError):
        await p.asset_sequence.accept(prep,value.requirement_key,adoption_ref=review,
            reference_media_ids=(value.delivery['mediaId'],),reference_record=value)
    assert assets(p)==before


@pytest.mark.asyncio
async def test_sequential_candidate_adoptions_merge_only_their_exact_requirements(tmp_path,monkeypatch):
    p,request,_,old,author=await candidate_source(tmp_path,monkeypatch)
    packet=p.asset_sequence.objects.read_ref(old.preparation_ref)
    other=next(row for row in packet['requirements'] if row['requirementKey']!=old.requirement_key)
    child_result=await p.reference_production.pending(old.preparation_ref,'offline-old-candidate-parent',
        request,requirement_key=other['requirementKey'])
    second_id=next(ref.artifact_ref for ref in child_result.artifact_refs if ref.owner=='runtime')
    second=p.reference_production.get(second_id)
    calls=author_counts(author);store=CurrentAssetIndex(p);p.asset_sequence.film_storage=store
    for i,source in enumerate((old,second)):
        value,posts=await awaiting_adoption(p,source,'offline-two-selected-'+str(i),monkeypatch)
        await p.decide_target_run(value.run_id,decision_id=p.runtime.decision_id(value.run_id),
            accepted=True,source_ref=value.artifact_reference())
        assert (await p.reference_production.resume(value.run_id)).state==RuntimeState.SUCCEEDED
        final=p.reference_production.get(value.run_id)
        await select_reference_asset(store,await p.providers.asset.get_asset(final.asset_id),
            'offline-two-asset-events-'+str(i),100+i*2)
        assert final.frame==source.frame and len(posts)==1
    path=p.asset_sequence.objects._path('asset-scene-design',[packet['narrativeRef']['fingerprint'],packet['sceneId']])
    selected=SourcePin.model_validate(p.asset_sequence.objects._read(path))
    current=p.asset_sequence.objects.read_ref(selected)
    assert current['requirements']==packet['requirements']
    assert author_counts(author)==calls


@pytest.mark.asyncio
async def test_independent_change_to_same_identity_is_not_overwritten_by_larger_candidate_revision(tmp_path,monkeypatch):
    p,_,_,old,_=await candidate_source(tmp_path,monkeypatch)
    store=CurrentAssetIndex(p);p.asset_sequence.film_storage=store
    value,_=await awaiting_adoption(p,old,'offline-conflicting-candidate-adoption',monkeypatch)
    packet=p.asset_sequence.objects.read_ref(old.preparation_ref)
    parent=p.asset_sequence.candidate_parent(old.preparation_ref)
    current=p.asset_sequence.objects.read_ref(parent)
    target=next(row for row in current['requirements']
        if row['stableIdentity']==next(r for r in packet['requirements']
            if r['requirementKey']==old.requirement_key)['stableIdentity'])
    independent=deepcopy(target)
    independent['design']={**independent['design'],'proof':'Independently selected other proof'}
    original={k:v for k,v in independent.items() if k not in {'designRef','requirementKey'}}
    design=p.asset_sequence.objects.put('offline-independent-asset-design',original)
    independent.update(designRef=dump_contract(design),requirementKey=design.fingerprint)
    assert independent['revision']<next(r for r in packet['requirements'] if r['requirementKey']==old.requirement_key)['revision']
    revised={**current,'requirements':[independent if r==target else r for r in current['requirements']],
        'professionalBasisRefs':[dump_contract(parent),*current.get('professionalBasisRefs',[])]}
    branch=p.asset_sequence.objects.put('specialized-asset-preparation:offline-independent-branch',revised)
    path=p.asset_sequence.objects._path('asset-scene-design',[packet['narrativeRef']['fingerprint'],packet['sceneId']])
    p.asset_sequence.objects._write(path,dump_contract(branch))
    before=assets(p)
    await p.decide_target_run(value.run_id,decision_id=p.runtime.decision_id(value.run_id),
        accepted=True,source_ref=value.artifact_reference())
    run=await p.reference_production.resume(value.run_id)
    assert run.state==RuntimeState.FAILED and run.cursor==6
    assert assets(p)==before and SourcePin.model_validate(p.asset_sequence.objects._read(path))==branch
