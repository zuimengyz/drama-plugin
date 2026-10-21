"""Real native entry/AssetProvider regressions; text and metadata only, no media IO."""
from copy import deepcopy
import json
import httpx
import pytest
from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.media import Media
from drama_plugin.creative_engine.contracts import (AuthorRequest, Authority, CanonDraft,
    CanonSubject, CreativeCheckpoint, DesignBody, Kind, SceneBody, ScriptBody, WorkBody)
from drama_plugin.film.contracts import FilmCanon, CanonScene, FilmDirection, DirectedShot, LanguageMetadata, DeliveryProfile
from drama_plugin.professional_design.asset_sequence import (AssetChoice, SceneAssetDraft,
    AssetPreparationPending, SpecializedAssetSequence)
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.runtime.contracts import ArtifactReference, CapabilityInput, RunMode, ResultStatus, RuntimeState
from drama_plugin.production.contracts import SourceDomain
from test_formal_author_backends import source, shot, configured, response


def film():
    appearances = [('A',), ('A', 'B'), ('A', 'B'), ('A', 'B', 'C'), ('C',)]
    return FilmCanon(work=WorkBody(interpretation='Offline film', dramatic_intent='Test inheritance', character_meaning='Stable people'),
        script=ScriptBody(screenplay='Five ordered scenes; C first appears in the fourth.'),
        scenes=tuple(CanonScene(scene_id=f's-{i + 1}', scene=SceneBody(scene_text=f'Complete selected scene {i + 1}',
            subjects=tuple(CanonSubject(id=s, name=s, meaning='A recurring person') for s in ids))) for i, ids in enumerate(appearances)))


class Author:
    def __init__(self, variant=False):
        self.scenes, self.shots, self.variant = [], [], variant
    async def design_assets(self, request):
        context = request.professional_context['assetPreparation']
        self.scenes.append(request.scope.scene_id)
        rows = context['subjectCandidates']
        choices = [AssetChoice(asset_type='CHARACTER', name=row['name'], subject_selection=row['selection'],
            design={'face': 'Distinct approved ' + row['name']}) for row in rows if row['inherited'] is None]
        if request.scope.scene_id == 's-1':
            choices.append(AssetChoice(asset_type='LOCATION', name='Room', design={'architecture': 'An independent room'}))
        if request.scope.scene_id == 's-2':
            choices.append(AssetChoice(asset_type='PROP', name='Letter', design={'material': 'Used paper'}))
            room=next(row['selection'] for row in context['assetCandidates'] if row['asset']['assetType']=='LOCATION')
            choices.append(AssetChoice(asset_type='LOCATION',name='Same room',reuse_selection=room,
                design={'architecture':'Reuse the same space; scene state changes'}))
        if request.scope.scene_id == 's-3':
            choices.append(AssetChoice(asset_type='LOCATION', name='Different room', design={'architecture': 'Another physical place; shared wood allowed'}))
            if self.variant:
                choices.append(AssetChoice(asset_type='CHARACTER', name='A tired', subject_selection=0,
                    variant_reason='The selected story advances A through fatigue', design={'face': 'Approved A with fatigue'}))
        return SceneAssetDraft(assets=tuple(choices), rationale='Scene increment under the selected screenplay')
    async def design(self, request):
        self.shots.append(request)
        return (DesignBody(domain='SUBJECTS', facts={'presentSubjects':[
            {'id':s.id,'role':s.name,'inSceneBehaviour':'Current action'} for s in request.canon.scene.subjects]}),
            DesignBody(domain='WORLD', facts={'setting':'This scene physical space'}))


def test_nonhuman_canon_subjects_keep_independently_authored_asset_types(tmp_path, monkeypatch):
    p = plugin(tmp_path, monkeypatch, Author())
    canon = film()
    ref = p.asset_sequence.bind_film('offline-sequence', canon,
        source_ref=ArtifactReference(owner='source-owner', artifact_ref='offline-source', version=1))
    roster = [{'id': key, 'name': key, 'meaning': 'A canonical subject'}
        for key in ('person', 'room', 'instruments')]
    choices = (
        AssetChoice(asset_type='CHARACTER', name='Person', subject_selection=0, design={'face':'Distinct face'}),
        AssetChoice(asset_type='LOCATION', name='Room', subject_selection=1, design={'architecture':'One room'}),
        AssetChoice(asset_type='PROP', name='First instrument', subject_selection=2, design={'construction':'First object'}),
        AssetChoice(asset_type='PROP', name='Second instrument', subject_selection=2, design={'construction':'Second object'}),
    )
    draft = SceneAssetDraft(assets=choices, rationale='Independent types for people, places and objects')
    result = p.asset_sequence._project(ref, 's-1', roster, {r['id']:None for r in roster}, [], draft)
    assert [row['assetType'] for row in result['requirements']] == ['CHARACTER', 'LOCATION', 'PROP', 'PROP']
    assert len({row['stableIdentity'] for row in result['requirements']}) == 4
    with pytest.raises(ValueError, match='FIRST_APPEARANCE_CHARACTER_DESIGN_REQUIRED'):
        p.asset_sequence._project(ref, 's-1', roster, {r['id']:None for r in roster}, [],
            SceneAssetDraft(assets=choices[1:], rationale='Missing the actual person'))


def plugin(tmp_path, monkeypatch, author):
    import drama_plugin.plugin as module
    monkeypatch.setattr(module, 'load_config', lambda _: DramaPluginConfig())
    data=MockDramaData();data.assets=[]
    return DramaPlugin.load(mock_data=data, ledger_path=tmp_path/'offline.sqlite',
        creative_root=tmp_path/'originals', professional_author=author)


def request_for(p, target, *, operation=None, scene_packets=None):
    canon = film()
    parent_id='offline-film-sequence'
    try:
        parent=p.runtime.store.load(parent_id)
    except KeyError:
        ref=ArtifactReference(owner='source-owner',artifact_ref='offline-explicit-language-and-rights',version=1)
        parent=p.create_source_film_run(work_id='offline-sequence',run_id=parent_id,source=source(),
            languages=LanguageMetadata(source_document_language='en',original_work_language='ru',spoken_language='ru',authority_ref=ref),
            profile=DeliveryProfile(width=1280,height=720),rights_refs=(ref,),route='offline',model='seedance-2-standard')
        p.film.store.put_author(parent_id,canon)
        direction=FilmDirection(shots=tuple(DirectedShot(scene_id=s.scene_id,shot_id=s.scene_id+'-shot',
            shot=shot().model_copy(update={'professional_domains':(SourceDomain.SUBJECTS,SourceDomain.WORLD), 'spoken_ids':()})) for s in canon.scenes))
        p.film.store.put_author(parent_id,direction)
        if scene_packets:
            cp=p.film.store.checkpoint(parent_id)
            ref=p.screenplays.objects.put('offline-selected-scene-handoffs', {'selectedSceneScreenplays':scene_packets})
            p.film.store.save(parent_id,parent.scope,cp.model_copy(update={'screenplay_ref':ref}))
    slot=next(i for i,s in enumerate(canon.scenes) if s.scene_id==target)
    unit=p.film.create_unit(CapabilityInput(run_id=parent_id,scope=parent.scope,operation_id='offline-unit'),slot)
    run=p.runtime.store.load(unit.creative_run_id)
    # The real source action seeds Canon/Shot refs, without any production action.
    p.creative.state.save(run.run_id,run.scope,CreativeCheckpoint(refs=unit.refs))
    inp = CapabilityInput(run_id=run.run_id, scope=run.scope, operation_id=run.run_id+':professional')
    return inp, p.creative._request(inp, Authority.PROFESSIONAL)


async def accept_pending(p, pending):
    packet = p.asset_sequence.objects.read_ref(pending.ref)
    for row in packet['requirements']:
        if row.get('reuseAssetId'):
            continue
        # Existing metadata-only reference fixture. No generation, files or paid models.
        mid = 'offline-reference-' + row['requirementKey'][:16]
        if not any(m.id == mid for m in p.providers.media.data.media):
            p.providers.media.data.media.append(Media(id=mid, work_id=packet['workId'], media_type='IMAGE',
                source_ref='OFFLINE_METADATA_FIXTURE', content_hash=sha256_canonical(mid),
                content={'width':1024,'height':1024,'qualification':'OFFLINE_FIXTURE'}))
        review = p.asset_sequence.objects.put('offline-artistic-adoption:' + row['requirementKey'],
            {'decision':'ADOPT','workId':packet['workId'], 'subjectFingerprint':row['designRef']['fingerprint'],
             'referenceMediaIds':[mid], 'qualification':'OFFLINE_FIXTURE'})
        await p.tools.invoke('specialized_assets.accept', preparation_ref=pending.ref,
            requirement_key=row['requirementKey'], adoption_ref=review, reference_media_ids=(mid,))
    return packet


async def resolve(p, request, author):
    pending_scenes = []
    for _ in range(12):
        try:
            result = await p.professional_design.prepare_assets(request)
            return result, pending_scenes
        except AssetPreparationPending as pending:
            packet = await accept_pending(p, pending)
            pending_scenes.append(packet['sceneId'])
    raise AssertionError('Preparation did not converge')


@pytest.mark.asyncio
async def test_a_normal_sequence_exact_identity_references_and_versions(tmp_path, monkeypatch):
    a=Author(); p=plugin(tmp_path,monkeypatch,a)
    identities={}
    for sid in ('s-1','s-2','s-3'):
        _,req=request_for(p,sid)
        ready,pending=await resolve(p,req,a)
        assert pending == [sid]
        for asset in ready.professional_context['assetSequence']['currentAssets']:
            value=asset['content']['specializedAsset']
            if asset['assetType']=='CHARACTER':
                if value['subjectId'] in identities:
                    assert identities[value['subjectId']]==asset['id']
                identities[value['subjectId']]=asset['id']
                assert value['revision']==1 and asset['referenceMediaIds']
    assert a.scenes==['s-1','s-2','s-3'] and set(identities)=={'A','B'}
    assert len(p.providers.asset.data.assets)==5
    assert not a.shots


@pytest.mark.asyncio
async def test_b_jump_scene_four_prepares_only_predecessor_assets_and_resumes_native_entry(tmp_path,monkeypatch):
    a=Author(); p=plugin(tmp_path,monkeypatch,a); inp,req=request_for(p,'s-4')
    pending=[]
    run=await p.runtime.run(inp.run_id)
    for _ in range(8):
        if run.state==RuntimeState.SUCCEEDED:
            break
        assert run.state==RuntimeState.WAITING_EXTERNAL, run
        result=run.last_result
        assert result.status==ResultStatus.WAITING_EXTERNAL and result.code is None
        original=await p.tools.invoke('specialized_assets.read_preparation', reference=result.external_ref)
        from drama_plugin.contracts.source_pin import SourcePin
        item=AssetPreparationPending(SourcePin.model_validate(original['preparationRef']))
        pending.append((await accept_pending(p,item))['sceneId'])
        run=await p.resume_film_run(inp.run_id)
    assert run.state==RuntimeState.SUCCEEDED, run
    assert pending==a.scenes==['s-1','s-2','s-3','s-4']
    assert len(a.shots)==1 and a.shots[0].scope.scene_id=='s-4'
    cp=p.creative.state.checkpoint(inp.run_id)
    design=next(p.creative_versions.resolve(r).body for r in cp.refs if p.creative_versions.resolve(r).kind==Kind.PROFESSIONAL)
    assert {r['content']['specializedAsset']['subjectId'] for r in design.facts['assetBindings']}=={'A','B','C'}
    assert design.facts['assetNarrativeRef']
    with p.ledger.transaction() as db:
        assert db.execute('SELECT count(*) FROM production_operation WHERE operation_ref_json IS NOT NULL').fetchone()[0]==0
    assert not p.creative.state.checkpoint(inp.run_id).child_runs
    assert cp.package_ref and p.production_packages.get(cp.package_ref)
    from types import SimpleNamespace
    from drama_plugin.creative_engine.sources import NativeCreativeSources
    from drama_plugin.film.media_references import asset_reference_candidates
    unit=SimpleNamespace(refs=cp.refs, scene_id='s-4', shot_id='s-4-shot')
    native=NativeCreativeSources(p.creative_versions,cp.refs,p.execution_references)
    subject_version=next(p.creative_versions.resolve(r) for r in cp.refs if p.creative_versions.resolve(r).kind==Kind.PROFESSIONAL
        and p.creative_versions.resolve(r).body.domain=='SUBJECTS')
    projected=native.project(subject_version)
    selection=SimpleNamespace(start_ref=projected.reference('content','presentSubjects','0','inSceneBehaviour'),
        fact_refs=tuple(SimpleNamespace(domain='SUBJECTS',reference=projected.reference('content','presentSubjects',str(i))) for i in range(3)))
    references=asset_reference_candidates(p,unit,selection)
    assert {r.subject_ids[0] for r in references}=={'A','B','C'}
    assert all(r.media.kind=='image' and r.media.version=='1' and len(r.media.content_hash)==64 for r in references)
    assert all([d.role for d in r.duties]==['CHARACTER'] for r in references)
    for binding in references:
        assert p.execution_references.resolve(p.execution_references.register(binding))['media']['mediaId']==binding.media.media_id


@pytest.mark.asyncio
async def test_c_adopted_assets_and_restore_do_not_regenerate_or_overwrite(tmp_path,monkeypatch):
    a=Author();p=plugin(tmp_path,monkeypatch,a)
    for sid in ('s-1','s-2'):
        _,req=request_for(p,sid)
        await resolve(p,req,a)
    before=[dump_contract(x) for x in p.providers.asset.data.assets]
    # Lose no source semantics when a new owner instance resumes.
    p.asset_sequence=SpecializedAssetSequence(p.creative_versions.objects,p.providers.asset,p.providers.media)
    p.professional_design.asset_sequence=p.asset_sequence
    _,req=request_for(p,'s-3');ready,pending=await resolve(p,req,a)
    assert pending==['s-3'] and a.scenes==['s-1','s-2','s-3']
    assert [dump_contract(x) for x in p.providers.asset.data.assets[:len(before)]]==before
    assert (await resolve(p,req,a))[1]==[]
    assert a.scenes==['s-1','s-2','s-3']


@pytest.mark.asyncio
async def test_service_held_originals_restore_without_local_design_cache(tmp_path,monkeypatch):
    from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
    a=Author();p=plugin(tmp_path,monkeypatch,a)
    _,req=request_for(p,'s-2');await resolve(p,req,a)
    source_plan=p.asset_sequence.objects.read_ref(p.asset_sequence.selected(req))
    before=[dump_contract(x) for x in p.providers.asset.data.assets]
    restored=SpecializedAssetSequence(DirectorArtifactStore(tmp_path/'fresh-owner'),p.providers.asset,p.providers.media)
    restored.bind_film(req.scope.work_id,film(),source_ref=ArtifactReference.model_validate(source_plan['sourceRef']))
    p.professional_design.asset_sequence=restored
    ready=await p.professional_design.prepare_assets(req)
    assert len(ready.professional_context['assetSequence']['preparedScenes'])==2
    assert a.scenes==['s-1','s-2']
    assert [dump_contract(x) for x in p.providers.asset.data.assets]==before


@pytest.mark.asyncio
async def test_bounded_global_asset_list_does_not_hide_existing_work_versions(tmp_path,monkeypatch):
    a=Author();p=plugin(tmp_path,monkeypatch,a)
    _,req=request_for(p,'s-2');await resolve(p,req,a)
    before=[dump_contract(x) for x in p.providers.asset.data.assets]
    async def bounded_list(*args,**kwargs):
        return []  # The service's first page is occupied by other Works.
    async def exact_search(query,*args,**kwargs):
        return [x for x in p.providers.asset.data.assets if query in json.dumps(dump_contract(x))]
    monkeypatch.setattr(p.providers.asset,'list_assets',bounded_list)
    monkeypatch.setattr(p.providers.asset,'search_assets',exact_search)
    ready=await p.professional_design.prepare_assets(req)
    assert ready.professional_context['assetSequence']['currentAssets']
    assert a.scenes==['s-1','s-2'] and [dump_contract(x) for x in p.providers.asset.data.assets]==before


@pytest.mark.asyncio
async def test_proven_legacy_asset_shape_is_read_without_mutation(tmp_path,monkeypatch):
    a=Author();p=plugin(tmp_path,monkeypatch,a)
    _,req=request_for(p,'s-2');await resolve(p,req,a)
    character=next(x for x in p.providers.asset.data.assets if x.asset_type=='CHARACTER')
    # Existing explicit design/adoption proof, outside the new envelope.
    character.content=deepcopy(character.content['specializedAsset'])
    original=dump_contract(character)
    ready=await p.professional_design.prepare_assets(req)
    inherited=next(x for x in ready.professional_context['assetSequence']['currentAssets'] if x['id']==character.id)
    assert inherited['content']['specializedAsset']['lineageStatus']=='PROVEN_EXISTING_ASSET'
    assert dump_contract(character)==original and a.scenes==['s-1','s-2']


@pytest.mark.asyncio
async def test_same_space_reuses_and_different_space_shares_material_without_identity_copy(tmp_path,monkeypatch):
    a=Author();p=plugin(tmp_path,monkeypatch,a)
    _,one=request_for(p,'s-1');r1,_=await resolve(p,one,a)
    _,two=request_for(p,'s-2');r2,_=await resolve(p,two,a)
    _,three=request_for(p,'s-3');r3,_=await resolve(p,three,a)
    def room(result):return next(x for x in result.professional_context['assetSequence']['currentAssets'] if x['assetType']=='LOCATION')
    assert room(r1)['id']==room(r2)['id'] and room(r3)['id']!=room(r1)['id']
    assert room(r3)['content']['specializedAsset']['inheritedFromAssetId'] is None


@pytest.mark.asyncio
async def test_candidate_template_and_failed_adoption_do_not_become_identity(tmp_path,monkeypatch):
    from drama_plugin.contracts.asset import Asset
    a=Author();p=plugin(tmp_path,monkeypatch,a)
    _,req=request_for(p,'s-1')
    p.providers.asset.data.assets.append(Asset(id='template',work_id=req.scope.work_id,
        asset_type='MASTER_CHARACTER_CARD',name='A board',content={'state':'CANDIDATE','subjectId':'A'}))
    with pytest.raises(AssetPreparationPending) as pending:
        await p.professional_design.prepare_assets(req)
    row=p.asset_sequence.objects.read_ref(pending.value.ref)['requirements'][0]
    bad=p.asset_sequence.objects.put('rejected',{'decision':'REJECT','workId':req.scope.work_id,
        'subjectFingerprint':row['requirementKey']})
    with pytest.raises(ValueError,match='ADOPTION_MISMATCH'):
        await p.asset_sequence.accept(pending.value.ref,row['requirementKey'],adoption_ref=bad)
    assert len(p.providers.asset.data.assets)==1


@pytest.mark.asyncio
async def test_existing_shot_prose_cannot_skip_narrative_asset_preparation(tmp_path,monkeypatch):
    a=Author();p=plugin(tmp_path,monkeypatch,a)
    inp,req=request_for(p,'s-4')
    cp=p.creative.state.checkpoint(inp.run_id)
    refs=list(cp.refs)
    for design in await a.design(req):
        refs.append(p.creative_versions.write(writer=Authority.PROFESSIONAL,kind=Kind.PROFESSIONAL,
            scope=inp.scope,body=design,sources=cp.refs,operation='offline-existing-'+design.domain.value))
    p.creative.state.save(inp.run_id,inp.scope,cp.model_copy(update={'refs':tuple(refs)}))
    run=await p.runtime.run(inp.run_id)
    assert run.state==RuntimeState.WAITING_EXTERNAL
    packet=await p.tools.invoke('specialized_assets.read_preparation',reference=run.last_result.external_ref)
    assert packet['sceneId']=='s-1' and a.scenes==['s-1']
    assert not p.providers.asset.data.assets
    # A committed old text response must not win over the new adopted assets.
    current=p.creative.state.checkpoint(inp.run_id)
    core=tuple(ref for ref in current.refs if p.creative_versions.resolve(ref).kind!=Kind.PROFESSIONAL)
    old=tuple(p.creative_versions.resolve(ref).body for ref in current.refs
        if p.creative_versions.resolve(ref).kind==Kind.PROFESSIONAL)
    p.creative_versions.retain_author_output(f'{run.run_id}:{run.cursor}','professional',core,old)
    for _ in range(6):
        if run.state==RuntimeState.SUCCEEDED:
            break
        from drama_plugin.contracts.source_pin import SourcePin
        packet=await p.tools.invoke('specialized_assets.read_preparation',reference=run.last_result.external_ref)
        await accept_pending(p,AssetPreparationPending(SourcePin.model_validate(packet['preparationRef'])))
        run=await p.resume_film_run(inp.run_id)
    assert run.state==RuntimeState.SUCCEEDED
    selected=[p.creative_versions.resolve(r).body for r in p.creative.state.checkpoint(inp.run_id).refs
        if p.creative_versions.resolve(r).kind==Kind.PROFESSIONAL]
    assert all(body.facts['assetBindings'] for body in selected)
    assert len(a.shots)==2 and a.shots[-1].professional_context['assetSequence']['currentAssets']


@pytest.mark.asyncio
async def test_predecessor_designs_receive_their_own_complete_selected_scene(tmp_path,monkeypatch):
    from drama_plugin.creative_engine.screenplay import ContextOriginal
    class SelectedAuthor(Author):
        async def design_assets(self, request):
            selected=request.screenplay_context['screenplay']
            assert selected['sceneId']==request.scope.scene_id
            assert selected['text']=='Complete independently chosen scene '+request.scope.scene_id
            return await super().design_assets(request)
    a=SelectedAuthor();p=plugin(tmp_path,monkeypatch,a);w=p.screenplays
    src=w.retain_context(ContextOriginal(work_id='offline-sequence',label='source',status='DESIGNATED_SOURCE',text=source().text))
    framework=w.retain_context(ContextOriginal(work_id='offline-sequence',label='selected-film',status='ADOPTED_FACT',
        text=film().script.screenplay,authority_ref='offline-selected-film'))
    packets=[]
    for scene in film().scenes:
        w.begin(session_id=scene.scene_id,work_id='offline-sequence',scope='SCENE',scene_id=scene.scene_id,
            goal='Write the complete scene freely',source_refs=(src,framework),full_film_ref=framework)
        w.retain_v1(scene.scene_id,'Complete independently chosen scene '+scene.scene_id)
        w.decide(scene.scene_id,choice='KEEP_ALL',reason='Selected original',expected_revision=1)
        packets.append(w.selected_packet(scene.scene_id))
    _,req=request_for(p,'s-4',scene_packets=packets)
    await resolve(p,req,a)
    assert a.scenes==['s-1','s-2','s-3','s-4']


@pytest.mark.asyncio
async def test_d_first_appearance_is_not_forced_into_first_scene(tmp_path,monkeypatch):
    a=Author();p=plugin(tmp_path,monkeypatch,a)
    _,req=request_for(p,'s-3');await resolve(p,req,a)
    assert not any(x.content['specializedAsset']['subjectId']=='C' for x in p.providers.asset.data.assets)
    _,req=request_for(p,'s-4');await resolve(p,req,a)
    c=next(x for x in p.providers.asset.data.assets if x.content['specializedAsset']['subjectId']=='C')
    assert c.scene_id is None and c.content['specializedAsset']['establishedSceneId']=='s-4'
    assert a.scenes==['s-1','s-2','s-3','s-4']


@pytest.mark.asyncio
async def test_variant_preserves_root_and_old_accepted_versions(tmp_path,monkeypatch):
    a=Author(variant=True);p=plugin(tmp_path,monkeypatch,a)
    _,req=request_for(p,'s-2');await resolve(p,req,a)
    first=next(x for x in p.providers.asset.data.assets if x.content['specializedAsset']['subjectId']=='A')
    before=dump_contract(first)
    _,req=request_for(p,'s-3');await resolve(p,req,a)
    variants=[x for x in p.providers.asset.data.assets if x.asset_type=='CHARACTER' and x.content['specializedAsset']['subjectId']=='A']
    assert len(variants)==2
    latest=variants[-1].content['specializedAsset']
    assert latest['revision']==2 and latest['stableIdentity']==first.content['specializedAsset']['stableIdentity']
    assert latest['inheritedFromAssetId']==latest['identityRootAssetId']==first.id
    assert dump_contract(first)==before


@pytest.mark.asyncio
async def test_http_asset_contract_persists_work_owned_versions_without_invented_service_scene(tmp_path,monkeypatch):
    from drama_plugin.config import ServiceConfig
    from drama_plugin.providers.http.client import HttpProviderClient
    from drama_plugin.providers.http.providers import HttpAssetProvider
    a=Author();p=plugin(tmp_path,monkeypatch,a);_,req=request_for(p,'s-1')
    rows={}
    def server(wire):
        if wire.method=='POST':
            body=json.loads(wire.content)
            assert body['work_id']=='offline-sequence' and body['scene_id'] is None
            assert body['content']['specializedAsset']['establishedSceneId']=='s-1'
            result={'id':'registered-'+str(len(rows)),**body};rows[result['id']]=result
            return httpx.Response(200,json=result)
        if wire.url.path=='/get':
            return httpx.Response(200,json=rows[wire.url.params['asset_id']])
        matches=list(rows.values())
        if wire.url.path=='/search':
            matches=[row for row in matches if wire.url.params['query'] in json.dumps(row)]
        return httpx.Response(200,json=matches)
    async with httpx.AsyncClient(base_url='https://offline-service.invalid',transport=httpx.MockTransport(server)) as client:
        provider=HttpAssetProvider(HttpProviderClient(ServiceConfig(base_url='https://offline-service.invalid',
            operations={'create_asset':'/create','get_asset':'/get','list_assets':'/list','search_assets':'/search'}),client))
        p.asset_sequence.assets=provider
        with pytest.raises(AssetPreparationPending) as pending:
            await p.professional_design.prepare_assets(req)
        await accept_pending(p,pending.value)
        ready=await p.professional_design.prepare_assets(req)
        assert len(rows)==2 and all(row['sceneId'] is None for row in ready.professional_context['assetSequence']['currentAssets'])
        assert len(a.scenes)==1


@pytest.mark.asyncio
async def test_default_formal_specialist_receives_inheritance_without_machine_identity_on_wire(tmp_path,monkeypatch):
    p=configured(monkeypatch,tmp_path);_,req=request_for(p,'s-1')
    wires=[]
    def receive(wire):
        data=json.loads(wire.content); payload=json.loads(data['messages'][1]['content']);wires.append(payload)
        subjects=payload['assetPreparation']['subjectCandidates']
        if len(wires)==1:
            assert subjects==[{'selection':0,'name':'A','meaning':'A recurring person','inherited':None}]
        else:
            assert subjects[0]['inherited']=={'face':'An authored adult face A'}
            assert subjects[1]=={'selection':1,'name':'B','meaning':'A recurring person','inherited':None}
        assert 'specialized-character:' not in json.dumps(payload)
        # Return raw semantic DTO, not old professional fixture's identity conversion.
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':json.dumps({
            'assets':[{'assetType':'CHARACTER','name':row['name'],'subjectSelection':row['selection'],
                'design':{'face':'An authored adult face '+row['name']}} for row in subjects if row['inherited'] is None],
            'rationale':'First-appearance baseline'})}}]})
    p.professional_design.author.client.transport=httpx.MockTransport(receive)
    with pytest.raises(AssetPreparationPending) as pending:
        await p.professional_design.prepare_assets(req)
    packet=await accept_pending(p,pending.value)
    ready=await p.professional_design.prepare_assets(req)
    assert len(wires)==1 and ready.professional_context['assetSequence']['currentAssets'][0]['referenceMediaIds']
    original=p.creative_versions.objects.read_ref(p.asset_sequence.selected(req))
    assert original['canon']==dump_contract(film())
    _,second=request_for(p,'s-2')
    with pytest.raises(AssetPreparationPending) as pending:
        await p.professional_design.prepare_assets(second)
    await accept_pending(p,pending.value)
    inherited=await p.professional_design.prepare_assets(second)
    assert len(wires)==2
    assert inherited.professional_context['assetSequence']['currentAssets'][-1]['id']==ready.professional_context['assetSequence']['currentAssets'][0]['id']
