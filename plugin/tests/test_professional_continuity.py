"""Real author/scene entries with offline transports; no media or paid services."""
import json
from copy import deepcopy
import httpx
import pytest

from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.film_grammar import WorkDirectingAuthority
from drama_plugin.creative_engine.contracts import Authority, CreativeCheckpoint, Kind
from drama_plugin.creative_engine.screenplay import ContextOriginal
from drama_plugin.creative_engine.screenplay_author import native_scene_screenplay
from drama_plugin.runtime.contracts import CapabilityInput, RunMode
from test_host_first_screenplay import plugin
from test_formal_author_backends import configured, canon, source, shot, response
from test_design_reconciliation import location


def look(work):
    # Deliberately warm: continuity is work-specific, never a universal cold rule.
    return WorkDirectingAuthority(work_scope=work, source_pins=[dict(key='current-film', kind='MEDIA', fingerprint='1'*64)],
        grammar_rules=[dict(rule_id='warm-world', domain='COLOR', narrative_reason='Chosen film grammar',
            applies_when='This film', execution='Warm dominant space, neutral skin', exception='Conscious scene variation', exit_condition='New phase')],
        evolution=[dict(scope_id='current', perceptual_owner='Director', narrative_change='Ordinary interior',
            rule_ids=['warm-world'], realization='Local interpretation')],
        aesthetic_rules=[dict(rule_id='depth', stance='PREFER', criterion='Natural optical depth', reason='Lived space',
            succeeds_when='Material and faces have layers', fails_when='Flat stage')])


async def selected(p, work='offline-r3-capability', sid='scene'):
    w=p.screenplays
    src=w.retain_context(ContextOriginal(work_id=work,label='source',status='DESIGNATED_SOURCE',text=source().text))
    film=w.retain_context(ContextOriginal(work_id=work,label='film',status='ADOPTED_FACT',text=canon().script.screenplay,authority_ref='current-script'))
    w.begin(session_id='selected',work_id=work,scope='SCENE',scene_id=sid,goal='Create freely',source_refs=(src,film),full_film_ref=film)
    w.retain_v1('selected',canon().scene.scene_text)
    w.decide('selected',choice='KEEP_ALL',reason='Selected complete scene',expected_revision=1)
    return w.bind_selection('selected',work_id=work,scene_id=sid)


@pytest.mark.asyncio
async def test_real_professional_entry_consumes_look_and_binds_exact_place(monkeypatch,tmp_path):
    p=configured(monkeypatch,tmp_path)
    work='offline-r3-capability'; sid='scene'
    h=await selected(p,work,sid)
    film=p.screenplays.objects.put('look',dump_contract(look(work)))
    place=location(scenes=(sid,),identity='engineer-home')
    loc=p.screenplays.objects.put('place',dump_contract(place))
    bound=await p.tools.invoke('screenplay.bind_professional_context',handoff_ref=h,
        work_id=work,scene_id=sid,design_refs=(film,loc))
    before=p.screenplays.objects.read_ref(h)
    run=p.create_film_run(work_id=work,scene_id=sid,shot_id='shot',mode=RunMode.EXPERIMENT,source=source(),screenplay_ref=bound)
    refs=[p.creative.state.input(run.run_id).source_ref]
    from drama_plugin.production.contracts import SourceDomain
    s=shot().model_copy(update={'professional_domains':tuple(SourceDomain(d) for d in ('COLOR','LIGHTING','WORLD'))})
    for owner,kind,body in [(Authority.CANON,Kind.WORK,canon().work),(Authority.CANON,Kind.SCRIPT,canon().script),
                           (Authority.CANON,Kind.SCENE,canon().scene),(Authority.DIRECTION,Kind.SHOT,s)]:
        refs.append(p.creative_versions.write(writer=owner,kind=kind,scope=run.scope,body=body,
            sources=tuple(refs),operation='fixture:'+kind.value))
    from drama_plugin.creative_engine.contracts import DesignBody
    refs.append(p.creative_versions.write(writer=Authority.PROFESSIONAL,kind=Kind.PROFESSIONAL,scope=run.scope,
        body=DesignBody(domain='COLOR',facts={'scenePalette':'Prior approved room palette'}),
        sources=tuple(refs),operation='fixture:previous-color'))
    p.creative.state.save(run.run_id,run.scope,CreativeCheckpoint(refs=tuple(refs)))
    inp=CapabilityInput(run_id=run.run_id,scope=run.scope,operation_id='offline-professional')
    req=p.creative._request(inp,Authority.PROFESSIONAL)
    assert req.professional_context['filmLook'][0]['ref']==dump_contract(film)
    assert req.professional_context['locationCandidates'][0]['ref']==dump_contract(loc)
    assert p.creative._request(inp,Authority.CANON).professional_context is None
    from drama_plugin.creative_engine.author_projection import author_payload
    assert 'professionalDesignRefs' not in author_payload(p.creative._request(inp,Authority.CANON))['hostScreenplay']
    directed=await native_scene_screenplay(p.screenplays,object(),p.creative._request(inp,Authority.DIRECTION),
        operation='existing-direction-handoff',scene_id=sid)
    carried=p.screenplays.objects.put('carried-direction-handoff',directed)
    p.creative.state.save(run.run_id,run.scope,CreativeCheckpoint(refs=tuple(refs),screenplay_ref=carried))
    assert p.creative._request(inp,Authority.PROFESSIONAL).professional_context==req.professional_context
    calls=[]
    def receive(wire):
        data=json.loads(wire.content);payload=json.loads(data['messages'][1]['content']);calls.append(payload)
        assert payload['visualContinuity']['filmLook'][0]['grammarRules'][0]['execution']=='Warm dominant space, neutral skin'
        assert payload['visualContinuity']['locationCandidates'][0]['design']['zoneLayout']==dict(place.zone_layout)
        assert payload['visualContinuity']['currentDesigns']==[{'domain':'COLOR','facts':{'scenePalette':'Prior approved room palette'}}]
        assert 'sourcePins' not in payload['visualContinuity']['filmLook'][0]
        assert 'locationSelection' in data['messages'][0]['content']
        return response([{'domain':'COLOR','facts':{'scenePalette':'Warm space, neutral skin','continuityInterpretation':'Inherit film, interior variation'}},
            {'domain':'LIGHTING','facts':{'sources':'Window and practical','directionAndQuality':'Soft transition'}},
            {'domain':'WORLD','facts':{'setting':'Separate workroom; common wood is allowed','locationSelection':0}}])
    p.professional_design.author.client.transport=httpx.MockTransport(receive)
    designs=await p.professional_design.design(req)
    world=next(d for d in designs if d.domain=='WORLD')
    assert world.facts['locationBinding']=={'locationRef':{'locationId':place.id,'artifactRef':dump_contract(loc)}}
    persisted=p.professional_design.persist(p.creative_versions,req,world,operation='persist-professional')
    assert p.creative_versions.resolve(persisted).body.facts['continuityDesignRefs']==[dump_contract(film),dump_contract(loc)]
    assert len(calls)==1 and p.screenplays.objects.read_ref(h)==before
    from drama_plugin.creative_engine.author_projection import professional_projection
    bad=deepcopy(req.professional_context);bad['locationCandidates']=[]
    with pytest.raises(Exception,match='AUTHOR_SELECTION_NOT_IN_AUTHORITY'):
        professional_projection([{'domain':'COLOR','facts':{'scenePalette':'Warm'}},
            {'domain':'LIGHTING','facts':{'sources':'Window','directionAndQuality':'Soft'}},
            {'domain':'WORLD','facts':{'setting':'Separate room','locationSelection':0}}],
            req.model_copy(update={'professional_context':bad}))
    from drama_plugin.runtime.contracts import ResultStatus
    result=await p.runtime.executor.execute('creative.professional:v1',inp.model_copy(update={'operation_id':'registered-professional-entry'}))
    assert result.status==ResultStatus.SUCCEEDED
    outputs=[p.creative_versions.resolve(r).body for r in p.creative.state.checkpoint(run.run_id).refs
        if p.creative_versions.resolve(r).kind==Kind.PROFESSIONAL]
    assert {d.domain.value for d in outputs}=={'COLOR','LIGHTING','WORLD'}
    assert next(d for d in outputs if d.domain=='WORLD').facts['locationBinding']==world.facts['locationBinding']
    assert len(calls)==2
    await p.aclose()


@pytest.mark.asyncio
async def test_post_selection_binding_rejects_other_work_or_room(plugin):
    h=await selected(plugin,'work','room')
    bad=plugin.screenplays.objects.put('wrong-film',dump_contract(look('another-work')))
    with pytest.raises(ValueError,match='work mismatch'):
        plugin.screenplays.bind_professional_context(h,work_id='work',scene_id='room',design_refs=(bad,))
    bad=plugin.screenplays.objects.put('other-room',dump_contract(location(scenes=('other',))))
    with pytest.raises(ValueError,match='location scope mismatch'):
        plugin.screenplays.bind_professional_context(h,work_id='work',scene_id='room',design_refs=(bad,))


def test_explicit_memory_original_survives_missing_discovery_index(plugin):
    from drama_plugin.creative_engine.screenplay import NarrativeThread
    w=plugin.screenplays
    src=w.retain_context(ContextOriginal(work_id='work',label='pinned',status='ADOPTED_FACT',text='Fact',authority_ref='canon'))
    ref=w.retain_thread(NarrativeThread(work_id='work',key='continuity',status='ADOPTED_FACT',
        account='Exact existing meaning',scene_ids=('room',),source_refs=(src,)))
    w.objects._path('narrative-index','work').unlink()
    assert w.relevant_memory('work','room')==[]
    rows=w.relevant_memory('work','room',include_refs=(ref,),only_refs=True)
    assert rows[0]['account']=='Exact existing meaning' and rows[0]['ref']==dump_contract(ref)
    assert not rows[0]['current']


@pytest.mark.asyncio
async def test_default_scene_preserves_exact_scoped_evidence_and_explicit_handoff(plugin):
    from types import SimpleNamespace
    from test_formal_author_backends import request
    w=plugin.screenplays;req=request('direction');work=req.scope.work_id
    originals=[ContextOriginal(work_id=work,label='source',status='DESIGNATED_SOURCE',text=req.source.text),
        *[ContextOriginal(work_id=work,label='fact'+str(i),status='ADOPTED_FACT',text='Pinned fact '+str(i),authority_ref='canon:'+str(i)) for i in range(3)],
        ContextOriginal(work_id=work,label='actual-observation',status='OBSERVED_RESULT',text='Observed low saturation and neutral skin',observation_ref='retained-footage-observation'),
        ContextOriginal(work_id=work,label='selected-film',status='AUTHOR_CONCEPT',text=req.canon.script.screenplay)]
    refs=tuple(w.retain_context(o) for o in originals)
    w.begin(session_id='film',work_id=work,scope='FILM',goal='Whole film',source_refs=refs[:-1])
    w.retain_v1('film',req.canon.script.screenplay);w.decide('film',choice='KEEP_ALL',reason='Selected',expected_revision=1)
    incoming=w.selected_packet('film')
    incoming['context']['sources'].append({'ref':dump_contract(refs[-1]),**w.objects.read_ref(refs[-1])})
    class ReplayHost:
        async def scene_original(self,request,packet):
            assert packet['professionalGuidance']==[]
            assert [r['ref'] for r in packet['sources']]==[dump_contract(r) for r in refs]
            return SimpleNamespace(text=req.canon.scene.scene_text)
        async def scene_decision(self,request,packet):
            return SimpleNamespace(choice='KEEP_ALL',reason='Retain existing fixture',text=None)
    result=await native_scene_screenplay(w,ReplayHost(),req.model_copy(update={'screenplay_context':incoming}),operation='default',scene_id=req.scope.scene_id)
    assert result['context']['sources']==incoming['context']['sources']
    assert result['context']['sources'][4]['observationRef']=='retained-footage-observation'
    assert result['context']['sources'][4]['status']=='OBSERVED_RESULT'
    assert await native_scene_screenplay(w,object(),req.model_copy(update={'screenplay_context':result}),operation='explicit',scene_id=req.scope.scene_id)==result
    changed=deepcopy(incoming);changed['context']['sources'][4]['text']='Changed observation'
    with pytest.raises(ValueError,match='identity or work mismatch'):
        await native_scene_screenplay(w,ReplayHost(),req.model_copy(update={'screenplay_context':changed}),operation='tampered',scene_id=req.scope.scene_id)
