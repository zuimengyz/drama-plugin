"""Offline native adoption of a real Scene -> Shot department graph.

All authors/decisions are explicit temporary test fixtures. No live source,
movie store, model, credentials or external IO are read or changed.
"""
from copy import deepcopy
from types import SimpleNamespace
import socket
import pytest
from pydantic import ValidationError

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.creative_engine.contracts import (
    Authority, AuthorRequest, CanonDraft, CreativeCheckpoint, CreativeIntegrityReconciliation,
    DesignBody, FilmInput, Kind, SourceBody,
)
from drama_plugin.creative_engine.sources import NativeCreativeSources
from drama_plugin.film.contracts import ShotUnit
from drama_plugin.film.media_references import professional
from drama_plugin.film.media_units import phases_for
from drama_plugin.generation.sources import PackageReader
from drama_plugin.professional_design.contracts import ProfessionalDesignRequest
from drama_plugin.production.contracts import PackageScope, SourceDomain
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.runtime.contracts import ArtifactReference, CapabilityInput, RuntimeScope, RuntimeState
from test_unified_planning_recovery import DOMAINS, StructuredAuthors

DECLARED = tuple(SourceDomain(d) for d in DOMAINS if d not in {'COLOR','LIGHTING','REFERENCE'})


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*a, **k):
        raise AssertionError('Scoped adoption fixture forbids network and real authors')
    monkeypatch.setattr(socket.socket,'connect',blocked)
    monkeypatch.setattr(socket.socket,'connect_ex',blocked)
    monkeypatch.setattr('drama_plugin.plugin.load_config',lambda _:DramaPluginConfig())
    monkeypatch.setattr('drama_plugin.creative_engine.backends.TextCompositionBackend.complete',blocked)


class FixedAuthors:
    async def author(self, request):
        raise AssertionError('Already retained Canon and Shot must not be reauthored')

    async def design(self, request):
        raise AssertionError('Already retained Shot departments must not be reauthored')


def load(path):
    fixed=FixedAuthors()
    return DramaPlugin.load(mock_data=MockDramaData.empty(),ledger_path=path/'ledger.sqlite',
        creative_root=path/'owners',target_media_root=path/'cache',
        canon_author=fixed,direction_author=fixed,professional_author=fixed)


async def retained_graph(p, *, families=False):
    """25 topological refs: core4, Scene10, unchanged thin Shot, Shot10."""
    store=p.creative_versions
    w=RuntimeScope(work_id='scoped-film')
    s=RuntimeScope(work_id=w.work_id,scene_id='specific-scene')
    scope=RuntimeScope(work_id=w.work_id,scene_id=s.scene_id,shot_id='specific-shot')
    fixture=StructuredAuthors()
    canon=await fixture.author_film(None)
    directed=await fixture.direct_film(None)
    shot=directed.shots[0].shot.model_copy(update={'professional_domains':DECLARED,'duration_ms':18000})
    designs=await fixture.design(None)
    refs=[store.write(writer=Authority.SOURCE,kind=Kind.SOURCE,scope=w,
        body=SourceBody(goal='OFFLINE scoped graph fixture',text='An approved silent gesture.',spoken_language='ru'),
        sources=(),operation='fixture-source')]
    for kind,body,target in ((Kind.WORK,canon.work,w),(Kind.SCRIPT,canon.script,w),(Kind.SCENE,canon.scenes[0].scene,s)):
        refs.append(store.write(writer=Authority.CANON,kind=kind,scope=target,body=body,
            sources=tuple(refs),operation='fixture-'+kind.value))
    core=tuple(refs)
    for body in designs:
        facts=deepcopy(body.facts)
        if families and body.domain=='SUBJECTS':
            facts['assetNarrativeRef']={'key':'offline-scene-family','kind':'DIRECTION','fingerprint':'a'*64}
        if body.domain=='ACTION':
            facts['actionPhases']=[{**facts['actionPhases'][0],'action':'Scene event extends beyond this Shot.',
                'observable':'Scene later state, not the Shot ending.'}]
        if body.domain=='WORLD':facts['setting']='Whole Scene setting, not the Shot current view.'
        refs.append(store.write(writer=Authority.PROFESSIONAL,kind=Kind.PROFESSIONAL,scope=s,
            body=DesignBody(domain=body.domain,facts=facts),sources=core,operation='scene-'+body.domain.value))
    shot_ref=store.write(writer=Authority.DIRECTION,kind=Kind.SHOT,scope=scope,body=shot,
        sources=tuple(refs),operation='fixture-shot')
    parents=(*core,shot_ref,*refs[4:])
    refs.append(shot_ref)
    for body in designs:
        if families and body.domain=='SUBJECTS':
            body=body.model_copy(update={'facts':{**body.facts,'assetNarrativeRef':{
                'key':'offline-fresh-shot-family','kind':'DIRECTION','fingerprint':'b'*64}}})
        refs.append(store.write(writer=Authority.PROFESSIONAL,kind=Kind.PROFESSIONAL,scope=scope,
            body=body,sources=parents,operation='shot-'+body.domain.value))
    assert len(refs)==25
    return tuple(refs),scope,designs


async def start(p, refs, scope, *, mode='PRODUCTION', run_id='scoped-adoption'):
    run=p.create_film_run(work_id=scope.work_id,scene_id=scope.scene_id,shot_id=scope.shot_id,
        source_ref=refs[0],base_refs=refs,mode=mode,run_id=run_id)
    return await p.runtime.run(run.run_id)


async def approve_fixture(p,run):
    """Explicit offline fixture decision; never a real movie/user receipt."""
    cp=p.creative.state.checkpoint(run.run_id)
    await p.decide_target_run(run.run_id,decision_id=p.runtime.decision_id(run.run_id),
        accepted=True,source_ref=cp.candidate_ref)
    result=await p.runtime.run(run.run_id)
    assert result.state==RuntimeState.SUCCEEDED,result.model_dump()
    return p.creative.state.checkpoint(run.run_id)


@pytest.mark.asyncio
async def test_25_ref_graph_reaches_exact_adoption_then_default_ten_domain_package_and_silent_dpd(tmp_path):
    p=load(tmp_path);refs,scope,designs=await retained_graph(p)
    originals={r:p.creative_versions.resolve(r) for r in refs}
    pending=await start(p,refs,scope)
    assert pending.state==RuntimeState.WAITING_USER and pending.cursor==6,pending.model_dump()
    cp=p.creative.state.checkpoint(pending.run_id)
    assert cp.refs==refs and cp.package_ref is None
    assert all(p.creative_versions.resolve(r).state=='REVIEWED' for r in refs[1:])
    adopted=await approve_fixture(p,pending)
    assert len(adopted.refs)==25
    assert all(p.creative_versions.resolve(r).state=='ADOPTED' for r in adopted.refs[1:])
    package=p.production_packages.get(adopted.package_ref)
    assert package.generation_intent.duration_ms==18000
    professional_sources=[r for r in package.sources if r.reference.owner=='professional']
    assert {r.domain.value for r in professional_sources}==set(DOMAINS)
    assert len(professional_sources)==10
    for row in professional_sources:
        assert p.creative_versions.projection(row.reference.fingerprint).scope==scope
    dpd,projection,snapshots=p.operation_resolver.compose_performance(adopted.refs)
    body=p.creative_versions.objects.read_ref(dpd)
    assert body['fullShotDPDCoverage']['status']=='PASS' and snapshots==()
    assert p.creative_versions.resolve(__import__('drama_plugin.creative_engine.contracts',fromlist=['VersionRef']).VersionRef.model_validate(body['performanceRef'])).scope==scope
    operation=await p.operation_resolver.select_unit(package,p.prompt_compiler.reader)
    assert operation.spoken_ids==() and {'COLOR','LIGHTING'} <= {r.domain for r in operation.fact_refs}
    unit=ShotUnit(scene_id=scope.scene_id,shot_id=scope.shot_id,creative_run_id=pending.run_id,refs=adopted.refs)
    assert professional(p,unit,'WORLD').scope==scope
    assert phases_for(p,unit)[1][0]['observable']=='The gesture has completed.'
    assert all(p.creative_versions.resolve(r)==v for r,v in originals.items())
    restored=load(tmp_path)
    assert restored.production_packages.get(adopted.package_ref)==package
    assert restored.creative.state.checkpoint(pending.run_id)==adopted
    assert restored.operation_resolver.compose_performance(adopted.refs)==(dpd,projection,snapshots)
    # Lost derived selections recover only current exact Shot originals, including
    # the three already bound extra departments, never the Scene counterparts.
    shot=next(restored.creative_versions.resolve(r) for r in adopted.refs if restored.creative_versions.resolve(r).kind==Kind.SHOT)
    restored.creative_versions._path('selection',shot.ref()).unlink()
    recovered=restored.creative_versions.selected_refs(shot.ref())
    assert len(recovered)==25
    native=NativeCreativeSources(restored.creative_versions,recovered)
    result=await native.select(ProfessionalDesignRequest(scope=package.scope))
    assert not result.issues and len(result.sources)==11


@pytest.mark.asyncio
async def test_explicit_domain_query_does_not_expand_to_bound_ten_or_scene_registry(tmp_path):
    p=load(tmp_path);refs,scope,_=await retained_graph(p)
    native=NativeCreativeSources(p.creative_versions,refs)
    work,scene,shot=await native.scope_sources(scope)
    result=await native.select(ProfessionalDesignRequest(scope=PackageScope(work=work.reference(),
        scene=scene.reference(),shot=shot.reference()),domains=('CAMERA',)))
    assert {r.domain for r in result.sources}=={'DIRECTION','CAMERA'}
    assert all(p.creative_versions.projection(r.reference.fingerprint).scope==scope for r in result.sources)


@pytest.mark.asyncio
async def test_capacity_remains_bounded_and_missing_parent_cannot_be_omitted(tmp_path):
    p=load(tmp_path);refs,scope,_=await retained_graph(p)
    assert len(FilmInput(source_ref=refs[0],base_refs=refs).base_refs)==25
    assert len(CreativeCheckpoint(refs=refs,candidate_version_refs=refs).refs)==25
    parent=ArtifactReference(owner='creative-candidate',artifact_ref='offline-parent',version=1)
    assert len(CreativeIntegrityReconciliation(parent=parent,original_refs=refs).original_refs)==25
    for cls,fields in ((FilmInput,dict(source_ref=refs[0],base_refs=refs+(refs[0],)*8)),
                       (CreativeCheckpoint,dict(refs=refs+(refs[0],)*8))):
        with pytest.raises(ValidationError):cls(**fields)
    missing=refs[:4]+refs[5:]
    failed=await start(p,missing,scope)
    assert failed.state==RuntimeState.FAILED and failed.cursor==0
    assert p.creative.state.checkpoint(failed.run_id).package_ref is None
    unordered=(*refs[:4],refs[14],*refs[4:14],*refs[15:])
    failed=await start(p,unordered,scope,run_id='unordered')
    assert failed.state==RuntimeState.FAILED and failed.cursor==0


@pytest.mark.asyncio
async def test_unrelated_ancestor_scope_original_cannot_enter_adoption(tmp_path):
    p=load(tmp_path);refs,scope,_=await retained_graph(p)
    unrelated=p.creative_versions.write(writer=Authority.PROFESSIONAL,kind=Kind.PROFESSIONAL,
        scope=RuntimeScope(work_id=scope.work_id),body=DesignBody(domain='COLOR',facts={'scenePalette':['Unrelated.']}),
        sources=refs[:3],operation='unrelated-world-color')
    failed=await start(p,(*refs,unrelated),scope)
    assert failed.state==RuntimeState.FAILED and failed.cursor==5
    assert p.creative.state.checkpoint(failed.run_id).package_ref is None


@pytest.mark.asyncio
async def test_asset_refresh_preserves_scene_parents_and_all_ten_selected_domains(tmp_path,monkeypatch):
    p=load(tmp_path);refs,scope,designs=await retained_graph(p)
    calls=[]
    class HostProfessional:
        async def design(self,request):
            calls.append(request)
            assert tuple(d.value for d in request.shot.professional_domains)==DOMAINS
            assert len(request.source_refs)==15
            assert sum(p.creative_versions.resolve(r).scope.shot_id is None and
                p.creative_versions.resolve(r).kind==Kind.PROFESSIONAL for r in request.source_refs)==10
            return designs
    p.professional_design.author=HostProfessional()
    monkeypatch.setattr(p.professional_design,'asset_inheritance_current',lambda *a:False)
    pending=await start(p,refs,scope)
    assert pending.state==RuntimeState.WAITING_USER,pending.model_dump()
    current=p.creative.state.checkpoint(pending.run_id)
    assert len(current.refs)==25 and len(calls)==1
    assert current.refs[:15]==refs[:15]
    assert p.creative_versions.resolve(current.refs[14]).body.professional_domains==DECLARED
    assert len({p.creative_versions.resolve(r).body.domain for r in current.refs[15:]})==10


@pytest.mark.asyncio
async def test_adoption_run_preserves_named_scene_and_shot_scope(tmp_path):
    p=load(tmp_path);refs,scope,_=await retained_graph(p)
    done=await start(p,refs,scope,mode='EXPERIMENT',run_id='experiment')
    assert done.state==RuntimeState.SUCCEEDED,done.model_dump()
    adopted=p.create_adoption_run(done.run_id,run_id='specific-adoption')
    assert adopted.scope==scope
    pending=await p.runtime.run(adopted.run_id)
    assert pending.state==RuntimeState.WAITING_USER and pending.cursor==6


@pytest.mark.asyncio
async def test_professional_context_keeps_shot_family_without_relabeling_scene_ancestors(tmp_path):
    from drama_plugin.professional_design.asset_sequence import SpecializedAssetSequence
    p=load(tmp_path);refs,scope,_=await retained_graph(p,families=True)
    run=p.create_film_run(work_id=scope.work_id,scene_id=scope.scene_id,shot_id=scope.shot_id,
        source_ref=refs[0],base_refs=refs,mode='EXPERIMENT',run_id='context-only')
    p.creative.state.save(run.run_id,scope,CreativeCheckpoint(refs=refs))
    before={r:p.creative_versions.resolve(r) for r in refs}
    request=p.creative._request(CapabilityInput(run_id=run.run_id,operation_id='context-only',scope=scope),Authority.PROFESSIONAL)
    current=request.professional_context['currentDesigns']
    assert len(current)==10 and len(request.source_refs)==25
    assert all(row['facts']['scope']['shotId']==scope.shot_id for row in current)
    family=SpecializedAssetSequence._fixed_narrative(request)
    assert family.key=='offline-fresh-shot-family' and family.fingerprint=='b'*64
    assert sum(p.creative_versions.resolve(r).scope.shot_id is None and
        p.creative_versions.resolve(r).kind==Kind.PROFESSIONAL for r in request.source_refs)==10
    assert all(p.creative_versions.resolve(r)==value for r,value in before.items())
