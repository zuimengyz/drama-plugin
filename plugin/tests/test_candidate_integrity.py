"""No network: deterministic provenance, metadata-only versioning and stale approvals."""
import json
from pathlib import Path

import httpx
import pytest
from pydantic import JsonValue, TypeAdapter

from drama_plugin.config import DramaPluginConfig
from drama_plugin.creative_engine.contracts import (Authority, CreativeCheckpoint, DesignBody, Kind, VersionRef)
from drama_plugin.professional_design import provenance
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeState
from test_creative_engine import Authors, SOURCE, plugin
from test_formal_author_backends import ENV, SKILLS, model_output, request, response

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr('drama_plugin.plugin.load_config',lambda _:DramaPluginConfig())

async def candidate(tmp_path):
    authors=Authors();p=plugin(tmp_path,authors)
    run=p.create_film_run(work_id='integrity',mode='PRODUCTION',source=SOURCE)
    run=await p.runtime.run(run.run_id)
    assert run.state==RuntimeState.WAITING_USER and run.cursor==6
    return p,authors,run,p.creative.state.checkpoint(run.run_id)

@pytest.mark.asyncio
async def test_system_projects_exact_authority_not_model_identity(tmp_path):
    p,a,run,cp=await candidate(tmp_path)
    for r in cp.refs:
        v=p.creative_versions.resolve(r)
        if isinstance(v.body,DesignBody):
            provenance.validate_metadata(v.body,p.creative_versions,v.scope,v.source_refs)
            assert set(TypeAdapter(tuple[VersionRef,...]).validate_python(v.body.facts['sourcePins']))==set(v.source_refs)
            assert v.body.facts['scope']==run.scope.model_dump(mode='json',by_alias=True)
    assert a.calls==['canon','direction','professional']

@pytest.mark.asyncio
@pytest.mark.parametrize('fault',['identity','version','fingerprint','duplicate','missing','scope','nested','flat'])
async def test_bad_pin_cannot_be_persisted_or_pass_review(tmp_path,fault):
    p,a,run,cp=await candidate(tmp_path)
    ref=next(r for r in cp.refs if p.creative_versions.resolve(r).kind==Kind.PROFESSIONAL)
    v=p.creative_versions.resolve(ref);facts=json.loads(json.dumps(v.body.facts))
    if fault=='identity':facts['sourcePins'][0]['identity']='creative-work:malformed'
    elif fault=='version':facts['sourcePins'][0]['version']+=1
    elif fault=='fingerprint':facts['sourcePins'][0]['fingerprint']='a'*64
    elif fault=='duplicate':facts['sourcePins'][0]=facts['sourcePins'][1]
    elif fault=='missing':facts['sourcePins'].pop()
    elif fault=='scope':facts['scope']['workId']='wrong-work'
    elif fault=='nested':facts['nested']={'sceneRef':{'identity':'bad','version':2,'fingerprint':'b'*64}}
    elif fault=='flat':facts['shotVersion']=999
    wrong=DesignBody(domain=v.body.domain,facts=facts)
    with pytest.raises(ValueError,match='AUTHORITY_MISMATCH'):
        p.creative_versions.write(writer=Authority.PROFESSIONAL,kind=Kind.PROFESSIONAL,scope=run.scope,
            body=wrong,sources=v.source_refs,operation='invalid-'+fault)
    assert p.creative_versions.head(v.identity)==ref

@pytest.mark.asyncio
async def test_stale_authoritative_parent_rejected(tmp_path):
    p,a,run,cp=await candidate(tmp_path)
    ref=next(r for r in cp.refs if p.creative_versions.resolve(r).kind==Kind.PROFESSIONAL)
    v=p.creative_versions.resolve(ref)
    p.creative_versions.invalidate(v.source_refs[0])
    with pytest.raises(ValueError,match='AUTHORITY_MISMATCH'):
        provenance.validate_metadata(v.body,p.creative_versions,run.scope,v.source_refs)

@pytest.mark.asyncio
@pytest.mark.parametrize('field',['sourcePins','scope','sourceRef','workRef','scriptRef','sceneRef','shotRef','workIdentity','sceneVersion','sourceFingerprint'])
async def test_model_cannot_author_system_metadata(field):
    from drama_plugin.creative_engine.backends import compose_authors,professional_model_schema
    from drama_plugin.config.loader import load_config
    output=model_output('professional');output[0]['facts']['constraints']={'nested':{field:[]}};calls=[]
    def mock(r):calls.append(r);return response(output)
    _,_,author=compose_authors(load_config(environment=ENV).text_composition,SKILLS,transport=httpx.MockTransport(mock))
    from drama_plugin.creative_engine.diagnostics import AuthorResultFailure
    with pytest.raises(AuthorResultFailure,match='AUTHOR_SYSTEM_FIELD_FORBIDDEN') as caught:
        await author.design(request('professional'))
    assert any(issue.field_path[-1:]==(field,) for issue in caught.value.diagnostic.issues)
    assert len(calls)==1 # No repair/model retry.
    schema=professional_model_schema()
    assert field in schema['$defs']['DesignBody']['properties']['facts']['propertyNames']['not']['enum']
    assert field in schema['$defs']['JsonValue']['anyOf'][-1]['propertyNames']['not']['enum']

@pytest.mark.asyncio
async def test_integrity_revision_keeps_content_history_and_same_user_wait(tmp_path,monkeypatch):
    p,a,run,cp=await candidate(tmp_path)
    original=next(r for r in cp.refs if p.creative_versions.resolve(r).kind==Kind.PROFESSIONAL)
    v=p.creative_versions.resolve(original);facts=json.loads(json.dumps(v.body.facts));facts['sourcePins'][0]['identity']='bad-historical-pin'
    # Import a PRE-FIX historical fixture through the old owner contract only.
    with monkeypatch.context() as old:
        old.setattr(provenance,'validate_metadata',lambda *args,**kwargs:None)
        old.setattr(provenance,'project_metadata',lambda design,*args:design)
        bad=p.creative_versions.write(writer=Authority.PROFESSIONAL,kind=Kind.PROFESSIONAL,
            scope=run.scope,body=DesignBody(domain=v.body.domain,facts=facts),sources=v.source_refs,operation='historical-fixture')
    refs=tuple(bad if r==original else r for r in cp.refs)
    historic=CreativeCheckpoint.model_validate({**cp.model_dump(),'refs':refs,'candidate_version_refs':refs})
    old_candidate=ArtifactReference(owner='creative-candidate',artifact_ref='creative-candidate:'+historic.candidate_fingerprint(),version=1)
    historic=historic.model_copy(update={'candidate_ref':old_candidate})
    p.creative.state.save(run.run_id,run.scope,historic)
    with pytest.raises(ValueError,match='AUTHORITY_MISMATCH'):p.creative.validate_candidate_integrity(historic,run.scope)
    calls=a.calls[:];operations=p.ledger.counts()['production_operation']
    refreshed=await p.reconcile_creative_candidate(run.run_id,candidate_ref=old_candidate)
    assert refreshed.state==RuntimeState.WAITING_USER and refreshed.cursor==6 and a.calls==calls
    new=p.creative.state.checkpoint(run.run_id);p.creative.validate_candidate_integrity(new,run.scope)
    assert new.candidate_ref!=old_candidate and new.decision_ref is None and new.package_ref is None
    fixed=next(r for r in new.refs if p.creative_versions.resolve(r).kind==Kind.PROFESSIONAL and p.creative_versions.resolve(r).body.domain==v.body.domain)
    corrected=p.creative_versions.resolve(fixed)
    assert fixed.version==bad.version+1 and p.creative_versions.resolve(bad).body.facts==facts
    assert provenance.creative_facts(corrected.body.facts)==provenance.creative_facts(v.body.facts)
    assert tuple(r for r in new.refs if p.creative_versions.resolve(r).kind!=Kind.PROFESSIONAL)==tuple(r for r in cp.refs if p.creative_versions.resolve(r).kind!=Kind.PROFESSIONAL)
    assert p.ledger.counts()['production_operation']==operations
    # A stale candidate cannot acquire an adoption receipt after replacement.
    with pytest.raises(ValueError,match='exact candidate'):
        await p.decide_target_run(run.run_id,decision_id=p.runtime.decision_id(run.run_id),accepted=True,source_ref=old_candidate)
    await p.reconcile_creative_candidate(run.run_id,candidate_ref=old_candidate)
    assert p.creative.state.checkpoint(run.run_id)==new and a.calls==calls
    fresh=plugin(tmp_path,Authors())
    restored=await fresh.runtime.recover_run(run.run_id)
    assert restored.state==RuntimeState.WAITING_USER and fresh.creative.state.checkpoint(run.run_id)==new

@pytest.mark.asyncio
async def test_reconciliation_cannot_accept_or_alter_fixed_core(tmp_path):
    p,a,run,cp=await candidate(tmp_path)
    with pytest.raises(ValueError,match='candidate changed'):
        await p.reconcile_creative_candidate(run.run_id,candidate_ref=ArtifactReference(owner='creative-candidate',artifact_ref='wrong',version=1))
    assert p.runtime.store.load(run.run_id).state==RuntimeState.WAITING_USER
