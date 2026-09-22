from copy import deepcopy
from pathlib import Path
import pytest
from pydantic import ValidationError
from drama_plugin import DramaPlugin
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.creative_source import CompileSourceRequest, LiteraryPackage
from drama_plugin.creative_source import compile_source, production_gate, validate_work_content, verify_screenplay_input
from literary_fixture import fixture, reviewed
ROOT = Path(__file__).resolve().parents[1]


def compiled(data=None, use='STUDY', jurisdiction='TEST'):
    return compile_source(dict(source=data or fixture(), jurisdiction=jurisdiction, intendedUse=use))


def content(data=None):
    data = data or fixture()
    return dict(creativeSourceType='LITERARY', literaryPackage=data, screenplayInput=dump_contract(compiled(data)))


def test_synthetic_complete_chain_and_real_source_map():
    p=fixture();result=compiled(p)
    assert result.pipeline == ('literary-source-analysis','philosophical-core','literary-adaptation','dramatic-compression','literature-to-cinema')
    assert not result.rights_gate.authorized
    assert {r.origin for r in result.source_map} == {'SOURCE_FACT','INTERPRETATION','ADAPTATION_INVENTION'}
    assert {'ADAPTATION_CONTRACT','DRAMATIC_COMPRESSION','LITERATURE_TO_CINEMA','CHARACTER_ARC'} <= {r.layer for r in result.source_map}
    assert result.package_ref.fingerprint == sha256_canonical(LiteraryPackage.model_validate(p))
    source=dump_contract(LiteraryPackage.model_validate(p))
    for row in result.source_map:
        value=source
        for key in row.source_path.strip('/').split('/'):
            value=value[int(key)] if isinstance(value,list) else value[key]
        assert value and row.anchor_ids==('a',)
    assert len(result.resolved_input['characterArc']['states'])==2


@pytest.mark.parametrize('status,allowed',[('UNKNOWN',False),('RESTRICTED',False),('PUBLIC_DOMAIN',True),('LICENSED',False),('USER_OWNED',True)])
def test_rights_status(status,allowed):
    p=fixture();p['artifacts'][0]['rights']['status']=status;reviewed(p)
    if allowed:assert compiled(p,'COMMERCIAL_PRODUCTION').rights_gate.authorized
    else:
        with pytest.raises(ValueError,match='RIGHTS_GATE_BLOCKED'):compiled(p,'COMMERCIAL_PRODUCTION')


def test_license_scope_jurisdiction_evidence():
    p=fixture();p['artifacts'][0]['rights'].update(status='LICENSED',licenseScope='TEST; adaptation and commercial distribution');reviewed(p)
    assert compiled(p,'COMMERCIAL_PRODUCTION').rights_gate.authorized
    for key,value in [('jurisdictions',['OTHER']),('evidence',[]),('permittedUses',['ADAPTATION']),('assertedBy',None),('basis',None)]:
        other=deepcopy(p);other['artifacts'][0]['rights'][key]=value;reviewed(other)
        with pytest.raises(ValueError,match='RIGHTS_GATE_BLOCKED'):compiled(other,'COMMERCIAL_PRODUCTION')


def test_original_public_domain_never_authorizes_translation():
    p=fixture();original=p['artifacts'][0];original['rights']['status']='PUBLIC_DOMAIN';original['role']='NON_COPYING_REFERENCE'
    t=deepcopy(original);t.update(id='modern-translation',kind='TRANSLATION',role='SOURCE_OF_TRUTH',derivedFrom='original');t['rights']={'status':'UNKNOWN'}
    p['artifacts'].append(t);p['sourceArtifactId']='modern-translation';p['anchors'][0]['artifactId']='modern-translation';reviewed(p)
    with pytest.raises(ValueError,match='modern-translation:UNKNOWN'):compiled(p,'COMMERCIAL_PRODUCTION')
    assert compiled(p).source_type=='LITERARY'


@pytest.mark.parametrize('change,error',[
 (lambda p:p['anchors'][0].update(quote='not the text'),'QUOTE_MISMATCH'),
 (lambda p:p['artifacts'][0].update(kind='FILM_REFERENCE'),'MODERN_ADAPTATION'),
 (lambda p:p['analysis']['units'][0].update(supports=['interpretation']),'CANNOT_UPGRADE'),
 (lambda p:p['adaptation']['decisions'][0].update(sourceUnitIds=['e1']),'UNACCOUNTED_SOURCE'),
 (lambda p:p['compression']['mappings'][0].update(decisionId='missing'),'COMPRESSION_MUST_MAP'),
 (lambda p:p['cinema']['expressions'][0].update(destinationId='undeclared'),'DANGLING_CINEMA_DESTINATION'),
 (lambda p:p['cinema']['expressions'][0].update(channels=['VOICE_OVER']),'REQUIRES_DIRECTOR_CHOICE'),
 (lambda p:p['cinema']['expressions'][0].update(channels=['EXPLICIT_EXPLANATION']),'REQUIRES_DIRECTOR_CHOICE'),
 (lambda p:p['characterArc']['states'][0].update(characterId='new'),'DANGLING_ARC_CHARACTER')])
def test_negative_contract_cases(change,error):
    p=fixture();change(p);reviewed(p)
    with pytest.raises(ValueError,match=error):compiled(p)


def test_deletion_preservation_and_stale_review():
    p=fixture();p['adaptation']['permittedChanges'].append('REMOVE');p['adaptation']['decisions'][0]['operation']='REMOVE';reviewed(p)
    with pytest.raises(ValueError,match='CANNOT_REMOVE'):compiled(p)
    p=fixture();p['philosophicalCore']['question']='changed interpretation'
    with pytest.raises(ValueError,match='STALE_SPECIALIST'):compiled(p)


def test_justified_voice_over_and_no_keyword_ban():
    p=fixture();p['cinema']['expressions'][0].update(channels=['VOICE_OVER'],explicitnessException=dict(basis='DRAMATIC_STRUCTURE_REQUIRES',reason='specific contrast',sourceUnitIds=['e1'],directorDecision='recorded director choice'))
    p['philosophicalCore']['question']='人生、命运、死亡、意义、自由、灵魂？';reviewed(p)
    assert 'DIRECTOR_DECISION' in {r.layer for r in compiled(p).source_map}


def test_provider_controls_forbidden():
    p=fixture();p['cinema']['provider']='not-an-owner'
    with pytest.raises(ValidationError):compiled(p)


def test_forged_compilation_and_routing_downgrade():
    p=fixture();r=dump_contract(compiled(p));r['resolvedInput']['adaptation']['decisions'][0]['expression']='silent rewrite'
    with pytest.raises(ValueError,match='STALE_OR_TAMPERED'):verify_screenplay_input(p,r)
    with pytest.raises(ValueError,match='IMMUTABLE'):validate_work_content({},content())
    with pytest.raises(ValueError,match='BYPASS'):validate_work_content({'literaryPackage':p})


@pytest.mark.asyncio
async def test_actual_registry_write_director_handoff(tmp_path):
    plugin=DramaPlugin.load(ROOT);request=CompileSourceRequest(source=fixture(),jurisdiction='TEST')
    out=await plugin.tools.invoke('source.prepare_screenplay',request=request)
    work=await plugin.tools.invoke('work.create_work',title='TECHNICAL_FIXTURE',content=content())
    with pytest.raises(ValueError,match='CURRENT_SCREENPLAY_INPUT'):
        await plugin.tools.invoke('script.create_script',work_id=work.id,title='technical',content={})
    script=await plugin.tools.invoke('script.create_script',work_id=work.id,title='technical',content={'screenplayInput':dump_contract(out),'fixtureOnly':True})
    host=plugin.creative_source_host(tmp_path);host.prepare(request)
    workspace=host.director_handoff(work_id=work.id,work_content=work.content,script_content=script.content,workspace_id='test',branch_id='novel')
    intent=host.store.read_ref(workspace.intent_refs[0]);assert intent['role']=='CREATIVE_ORCHESTRATOR'
    assert 'analysis' not in intent['constraints']
    assert intent['constraints']['philosophicalCore']==out.resolved_input['philosophicalCore']
    current={r.key:r.fingerprint for r in workspace.source_pins+workspace.intent_refs}
    assert host.store.resume('test','novel',current)
    assert host.store.read_ref(workspace.source_pins[0])['sourceType']=='LITERARY'
    with pytest.raises(ValueError,match='IMMUTABLE'):
        await plugin.tools.invoke('work.save_work',work_id=work.id,title='downgrade',content={})
    await plugin.aclose()


def test_production_rechecks_rights():
    p=fixture();p['artifacts'][0]['rights']={'status':'UNKNOWN'};reviewed(p)
    with pytest.raises(ValueError,match='RIGHTS_GATE_BLOCKED'):production_gate(content(p),'TEST')
    production_gate(content(),'TEST')
    with pytest.raises(ValueError,match='JURISDICTION'):production_gate(content(),None)
    with pytest.raises(ValueError,match='RIGHTS_GATE_BLOCKED'):production_gate(content(),'OTHER')


def test_historical_routing_executes_existing_checker():
    from test_screenplay_incubation import ledger
    work={key:['existing historical governed content'] for key in ('historicalScope','historicalSpine','historicalActorHierarchy','narrativeAuthority','protagonist','storyArchitecture')}
    p=dict(sourceType='HISTORICAL',id='historic-test',workContent=work,incubationBible=ledger());out=compiled(p)
    assert out.pipeline==('historical-research','historical-scope','historical-spine','historical-actor-hierarchy','narrative-authority','protagonist','story-architecture')
    assert out.resolved_input['workContent']==work
    p['incubationBible']['historicalGrounding']['claims'][0]['causeIds']=['event']
    with pytest.raises(ValueError,match='HISTORICAL_REVIEW_FAILED'):compiled(p)


def test_literary_incubation_shared_continuity():
    from test_screenplay_incubation import ledger,checker
    b=ledger();del b['historicalGrounding'];b.update(content());assert checker.check(b)==[]
    b['sequence'][0]['inputState']={'place':'unexplained'}
    assert any('CONTINUITY' in error for error in checker.check(b))


def test_literary_professional_graph_consumes_same_root_without_historical_requirements(tmp_path):
    from datetime import datetime,timezone
    from drama_plugin.professional import registry,dependency_order,bible_pin
    from drama_plugin.contracts.professional import CreativeBible,CreativeRecord
    plugin=DramaPlugin.load(ROOT)
    host=plugin.professional_host(tmp_path,source_type='LITERARY')
    definitions=registry('LITERARY');ordered=dependency_order('LITERARY')
    assert 'historical-research' not in definitions and 'historical-qa' not in definitions
    assert 'literary-source-input' in ordered
    assert registry()['character-dramaturgy'].depends_on==('story-architecture','historical-entity-registry')
    result=compiled();source=result.package_ref;now=datetime.now(timezone.utc)
    current={source.key:source.fingerprint};bibles={}
    values={
        'literary-source-input':{'source_package':fixture(),'screenplay_input':dump_contract(result)},
        'story-architecture':{'premise':'technical'},
        'character-dramaturgy':{'character_ref':'c','character_arc':result.resolved_input['characterArc']['states']},
        'scene-development':{'scene_ref':'technical'},
        'director':{'cinematic_interpretation':'technical orchestration only'},
        'character-art':{'character_ref':'c','source_identity':{'sourceUnitId':'c','origin':'SOURCE_FACT'},'arc_continuity_boundaries':[{'arcStage':s['arcStage'],'visualContinuityBoundary':s['visualContinuityBoundary']} for s in result.resolved_input['characterArc']['states']]},
    }
    for dept,v in values.items():
        bible=CreativeBible(source_type='LITERARY',id=dept,type=definitions[dept].output_contract,work_ref='test',source_refs=(source,),depends_on=tuple(bible_pin(bibles[d]) for d in definitions[dept].depends_on),content=(CreativeRecord(id=dept,scope_refs=('test',),values=v,provenance='NEW_PROFESSIONAL_ELABORATION',source_refs=(source,)),),created_by_capability=dept,status='READY_FOR_REVIEW',created_at=now,updated_at=now)
        response=host.submit(dept,bible,current=current)
        assert response['validationStatus']=='PASS' and response['creativeApproval']=='NOT_GRANTED_BY_HOST_VALIDATOR'
        bibles[dept]=bible;ref=bible_pin(bible);current[ref.key]=ref.fingerprint
    task=host.task('director',task='test handoff',available={d:bible_pin(b) for d,b in bibles.items()},current=current)
    assert task['directorMayFillMissingContent'] is False
    bad=bibles['character-dramaturgy'].model_copy(deep=True);bad.content[0].values['character_arc']='art redefines narrative arc'
    with pytest.raises(ValueError,match='UPSTREAM_REVISION'):host.submit('character-dramaturgy',bad,current=current)
    bad=bibles['character-art'].model_copy(deep=True);bad.content[0].values['arc_continuity_boundaries']=[]
    with pytest.raises(ValueError,match='CONSUME_ARC_BOUNDARIES'):host.submit('character-art',bad,current=current)
    bad=bibles['director'].model_copy(deep=True);bad.content[0].values['cinematic_interpretation']={'literary_analysis':'reinterpret'}
    with pytest.raises(ValueError,match='AUTHORITY_VIOLATION'):host.submit('director',bad,current=current)


@pytest.mark.asyncio
async def test_unknown_rights_block_actual_route_before_any_provider_call():
    from drama_plugin.hosts.route_production import validate_route_direction_sources
    from drama_plugin.contracts.creation import Work
    p=fixture();p['artifacts'][0]['rights']={'status':'UNKNOWN'};reviewed(p)
    c=content(p);c['productionJurisdiction']='TEST'
    # The rights check must execute before reading the route or touching a provider.
    with pytest.raises(ValueError,match='RIGHTS_GATE_BLOCKED'):
        await validate_route_direction_sources(None,Work(id='test',title='test',content=c),None)


def test_historical_envelope_cannot_hide_literary_bible():
    from test_screenplay_incubation import ledger
    work={key:['preserved'] for key in ('historicalScope','historicalSpine','historicalActorHierarchy','narrativeAuthority','protagonist','storyArchitecture')}
    bible=ledger();bible.update(content())
    with pytest.raises(ValueError,match='CANNOT_ROUTE'):
        compiled(dict(sourceType='HISTORICAL',id='wrong',workContent=work,incubationBible=bible))


def test_remote_context_cannot_hide_stale_script_input():
    from drama_plugin.contracts.context import DramaRunContext
    from drama_plugin.contracts.creation import Work,Script
    w=Work(id='w',title='test',content=content())
    with pytest.raises(ValueError,match='CURRENT_SCREENPLAY_INPUT'):
        DramaRunContext(context_id='ctx',version=1,scope='SCRIPT',purpose='test',work=w,script=Script(id='s',work_id='w',title='test',content={}))


def test_invented_character_arc_requires_recorded_adaptation_decision():
    p=fixture();state=p['characterArc']['states'][0];state['origin']='ADAPTATION_INVENTION';reviewed(p)
    with pytest.raises(ValueError,match='INVENTED_ARC_REQUIRES'):compiled(p)
    state['adaptationDecisionId']='d';reviewed(p)
    rows=[r for r in compiled(p).source_map if r.target=='arc:c:early']
    assert rows[0].decision_id=='d' and rows[0].origin=='ADAPTATION_INVENTION'
