"""V2-12B: isolated contract/Tool/IR tests; no paid generation or formal writes."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from drama_plugin import DramaPlugin
from drama_plugin.contracts.asset import Asset, AssetType
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.creative_asset import BgmContent, CinematicLanguageContent
from drama_plugin.contracts.media import Media, MediaType
from drama_plugin.creative_assets import (remember, search_patterns, pattern_ref, search_bgm,
    select_bgm, validate_music_recipe)
from drama_plugin.visual.cinematic import freeze_direction, verify_frozen, execution_brief
from test_cinematic_direction import example
from test_cinematic_finishing import material

ROOT = Path(__file__).resolve().parents[1]


def seeds():
    return [CinematicLanguageContent.model_validate(v) for v in json.loads((ROOT/'examples/cinematic-language-seeds.json').read_text())]


def bgm_fixture(*, known=False, media_id='audio', work_id='w'):
    m = Media(id=media_id, work_id=work_id, media_type=MediaType.AUDIO, source_ref='fixture:audio',
        content_hash='a'*64, duration_ms=4000, mime_type='audio/wav', file_size=100)
    c = BgmContent(title='Isolated contract fixture; not formal music', original_source='isolated fixture',
        mood=['tragic'], narrative_functions=['dread'], rights={'status':'VERIFIED' if known else 'UNKNOWN',
        'source':'isolated fixture' if known else None, 'license':'test-only' if known else None,
        'attribution':'' if known else None, 'commercialUse':True if known else None},
        production_eligible=known, media={'mediaId':m.id,'sourceRef':m.source_ref,'contentHash':m.content_hash})
    a = Asset(id='bgm-fixture',work_id=work_id,asset_type=AssetType.AUDIO_INPUT,name=c.title,
        content=dump_contract(c),reference_media_ids=[m.id])
    return a,m


@pytest.mark.asyncio
async def test_ten_seeds_tool_persistence_rerun_search_and_conflict():
    p=DramaPlugin.load(ROOT); work=p.providers.memory.data.work.id
    ids=[]
    for seed in seeds():
        a,state=await remember(p.tools,work,seed)
        assert state=='CREATED' and a.reference_media_ids==[]
        ids.append(a.id)
        # Explicit save contract verification for isolated newly created assets.
        saved=await p.tools.invoke('asset.save_asset',asset_id=a.id,name=a.name,content=a.content)
        assert (await p.tools.invoke('asset.get_asset',asset_id=a.id)).content==saved.content
        assert (await remember(p.tools,work,seed))[0].id==a.id
        assert (await remember(p.tools,work,seed))[1]=='REUSED'
    assert len(set(ids))==10
    for query in ['reaction','restrained','dialogue']:
        hits=await search_patterns(p.tools,query)
        keys={h['asset']['content']['semanticKey'].split('/')[-1] for h in hits}
        assert {'post-line-hold','eyes-lead-head-follows','locked-camera-performance'}<=keys
        assert all(h['matchReason']['tags'] for h in hits)
    changed=seeds()[0].model_copy(update={'purpose':'changed'})
    with pytest.raises(ValueError,match='conflict'):await remember(p.tools,work,changed)
    assert len(ids)==len(set(ids))


def test_provider_neutral_text_only_and_validation_guards():
    for c in seeds():
        a=Asset(id='a',work_id='w',asset_type=AssetType.OTHER,name=c.title,content=dump_contract(c))
        assert not a.reference_media_ids
        assert c.validation.status=='PROJECT_DERIVED'
        assert not any(x in json.dumps(dump_contract(c.pattern),ensure_ascii=False) for x in ['项羽','哥舒翰','唐朝','战争片','Seedance','H3','Comfy'])
    for invalid in ['Seedance node required','Comfy workflow required','ByteDance API','H3 parameter','FLUX required']:
        raw=dump_contract(seeds()[0]);raw['pattern']['camera']=invalid
        with pytest.raises(ValidationError):CinematicLanguageContent.model_validate(raw)
    raw=dump_contract(seeds()[0]);raw['validation']['status']='VALIDATED'
    with pytest.raises(ValidationError):CinematicLanguageContent.model_validate(raw)


def test_frozen_reference_survives_asset_revision_and_zero_path():
    spec,ctx,visual=example()
    c=seeds()[0];a=Asset(id='pattern-id',work_id='w',asset_type=AssetType.OTHER,name=c.title,content=dump_contract(c))
    ref=pattern_ref(a,'Small motivated approach after realization')
    spec.cinematic_language_refs=(ref,)
    frozen=freeze_direction(spec,context=ctx,visual_resolution=visual,host_review='offline reviewed')
    original=deepcopy(frozen)
    a.content['purpose']='Revision B'
    assert sha256_canonical(a.content)!=ref.content_fingerprint
    assert dump_contract(verify_frozen(frozen))==frozen['spec'] and frozen==original
    assert 'pattern-id' not in execution_brief(spec)
    spec.cinematic_language_refs=()
    assert verify_frozen(freeze_direction(spec,context=ctx,visual_resolution=visual,host_review='zero appropriate')).cinematic_language_refs==()


@pytest.mark.asyncio
async def test_music_unknown_searchable_production_blocked_hash_dedup_and_no_bgm():
    p=DramaPlugin.load(ROOT);a,m=bgm_fixture(work_id=p.providers.memory.data.work.id)
    p.providers.media.data.media.append(m)
    c=BgmContent.model_validate(a.content)
    first,state=await remember(p.tools,m.work_id,c)
    assert state=='CREATED'
    assert (await remember(p.tools,m.work_id,c))[0].id==first.id
    assert len(await search_bgm(p.tools,'SUBTLE',mood='tragic',narrative_function='dread'))==1
    assert await search_bgm(p.tools,'ACTIVE',production_only=True)==[]
    with pytest.raises(ValueError):select_bgm(first,m,decision='SUBTLE',selected_range=(0,3),reason='dread')
    t=AsyncMock()
    assert await search_bgm(t,'NO_BGM')==[]
    t.invoke.assert_not_called()


@pytest.mark.parametrize('mutation',['unknown','missing_media','false_rights','missing_license','missing_attribution','wrong_binding'])
def test_bgm_production_gate(mutation):
    a,m=bgm_fixture(known=True);raw=dump_contract(a)
    if mutation=='unknown':raw['content']['rights']['status']='UNKNOWN'
    if mutation=='missing_media':raw['content']['media']=None
    if mutation=='false_rights':raw['content']['rights']['commercialUse']=False
    if mutation=='missing_license':raw['content']['rights']['license']=None
    if mutation=='missing_attribution':raw['content']['rights']['attribution']=None
    if mutation=='wrong_binding':raw['referenceMediaIds']=[]
    with pytest.raises(ValidationError):Asset.model_validate(raw)


def test_finishing_lineage_ranges_rights_and_no_bgm_guard():
    a,m=bgm_fixture(known=True)
    s=select_bgm(a,m,decision='SUBTLE',selected_range=(0,3),reason='dread')
    recipe={'sources':{m.id:m.content_hash},'soundPlan':{'bgm':{'decision':'SUBTLE'}},'layers':[
        {'role':'BGM','mediaId':m.id,'sourceStart':0,'duration':3,
         'bgmAsset':dump_contract(a),'bgmMedia':dump_contract(m),'bgmSelection':dump_contract(s)}]}
    validate_music_recipe(recipe)
    for change in ['NO_BGM','hash','range','rights','missing']:
        r=deepcopy(recipe)
        if change=='NO_BGM':r['soundPlan']['bgm']['decision']='NO_BGM'
        if change=='hash':r['sources'][m.id]='b'*64
        if change=='range':r['layers'][0]['duration']=5
        if change=='rights':r['layers'][0]['bgmAsset']['content']['rights']['status']='UNKNOWN'
        if change=='missing':del r['layers'][0]['bgmSelection']
        with pytest.raises(ValueError):validate_music_recipe(r)


@pytest.mark.parametrize('kind',[AssetType.CHARACTER,AssetType.LOCATION,AssetType.PROP,AssetType.COSTUME])
def test_existing_asset_no_music_rights_requirement(kind):
    assert Asset(id='a',work_id='w',asset_type=kind,name='unchanged',content={'facts':['old']}).content=={'facts':['old']}


def test_skill_tool_architecture():
    p=DramaPlugin.load(ROOT)
    assert len(p.skills.list())==14 and len(p.tools.list())==50
    for skill in ['cinematic-direction','cinematic-finishing']:
        text=(ROOT/'skills'/skill/'skill.yaml').read_text()
        assert 'asset.search_assets' in text and 'asset.get_asset' in text
    assert '1–3' in (ROOT/'skills/cinematic-direction/SKILL.md').read_text()
    assert 'NO_BGM' in (ROOT/'skills/cinematic-finishing/SKILL.md').read_text()


@pytest.mark.asyncio
async def test_bgm_media_resolve_readback_rename_and_metadata_do_not_reimport(material):
    from test_media_delivery import Store
    from drama_plugin.creative_assets import retain_bgm_media
    from drama_plugin.media_delivery import file_hash
    _, paths, tmp = material  # Existing isolated synthetic renderer fixture, never formal BGM.
    p=DramaPlugin.load(ROOT);store=Store();work=p.providers.memory.data.work.id
    from dataclasses import replace
    from drama_plugin.tools.registry import ToolRegistry
    registry=ToolRegistry()
    for tool in p.tools.list():
        if tool.code in {'media.list_media','media.import_media','media.get_media','media.resolve_media'}:
            tool=replace(tool,handler=getattr(store,tool.name))
        registry.register(tool)
    p.tools=registry
    source=Path(paths['audio']);renamed=tmp/'renamed.wav';renamed.write_bytes(source.read_bytes())
    m=await retain_bgm_media(p.tools,store,work_id=work,source=source,original_source='isolated fixture',cache=tmp/'read1')
    reused=await retain_bgm_media(p.tools,store,work_id=work,source=renamed,original_source='renamed fixture',cache=tmp/'read2')
    assert reused.id==m.id and store.imports==1 and store.reads==2
    assert m.content_hash==file_hash(source)
    c=BgmContent(title='Isolated audio binding fixture',original_source='isolated',rights={'status':'UNKNOWN'},
        duration=m.duration_ms/1000,media={'mediaId':m.id,'sourceRef':m.source_ref,'contentHash':m.content_hash})
    a,_=await remember(p.tools,work,c)
    changed=deepcopy(a.content);changed['mood']=['tragic']
    await p.tools.invoke('asset.save_asset',asset_id=a.id,name=a.name,content=changed,reference_media_ids=[m.id])
    assert store.imports==1 and (await store.get_media(m.id)).content_hash==m.content_hash
    assert len(await search_bgm(p.tools,'SUBTLE',mood='tragic'))==1
    store.objects[m.id]=b'x'*m.file_size
    with pytest.raises(Exception,match='hash|mismatch|SHA|CONTENT'):
        await retain_bgm_media(p.tools,store,work_id=work,source=source,original_source='isolated',cache=tmp/'corrupt')
