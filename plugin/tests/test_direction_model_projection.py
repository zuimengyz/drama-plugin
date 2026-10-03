"""Direction producer projection must advertise precisely the existing authority."""
import json

import httpx
import pytest
from pydantic import TypeAdapter, ValidationError
from drama_plugin.config.loader import load_config
from drama_plugin.creative_engine.backends import compose_authors, direction_model_schema, professional_model_schema
from drama_plugin.creative_engine.contracts import CanonDraft, DesignBody, ShotBody
from drama_plugin.creative_engine.diagnostics import AuthorResultFailure
from drama_plugin.production.contracts import SourceDomain
from test_formal_author_backends import ENV, SKILLS, model_output, request, response

LEGAL=sorted(d.value for d in SourceDomain if d not in (SourceDomain.CANON,SourceDomain.DIRECTION))


def test_only_direction_projection_narrows_enum_and_explains_array_contract():
    canonical=TypeAdapter(ShotBody).json_schema(by_alias=True)
    schema=direction_model_schema();field=schema['properties']['professionalDomains']
    assert field['items']=={'type':'string','enum':LEGAL}
    assert '"CANON"' not in json.dumps(schema) and '"DIRECTION"' not in json.dumps(schema)
    assert field['uniqueItems'] is True and field['minItems']==1 and field['maxItems']==10
    assert 'lexicographic' in field['description'] and 'ownership' in field['description']
    assert SourceDomain.CANON in SourceDomain and SourceDomain.DIRECTION in SourceDomain
    assert TypeAdapter(ShotBody).json_schema(by_alias=True)==canonical
    assert schema['additionalProperties'] is False


@pytest.mark.asyncio
@pytest.mark.parametrize('domain',LEGAL)
async def test_every_existing_legal_domain_is_expressible_and_validated(domain):
    body={**model_output('direction'),'professionalDomains':[domain]};calls=[]
    def mock(r):
        calls.append(r)
        payload=json.loads(r.content);system=payload['messages'][0]['content']
        prompt,schema=system.rsplit('\nOutput JSON schema:\n',1)
        assert json.loads(schema)==direction_model_schema()
        assert 'CANON and DIRECTION must never appear in professionalDomains' in prompt
        assert 'does not describe Canon or Direction ownership' in prompt
        return response(body)
    _,a,_=compose_authors(load_config(environment=ENV).text_composition,SKILLS,transport=httpx.MockTransport(mock))
    result=await a.author(request('direction'))
    assert result==ShotBody.model_validate(body) and result.professional_domains==(SourceDomain(domain),)
    assert len(calls)==1


@pytest.mark.asyncio
@pytest.mark.parametrize('domains',[['CANON','LIGHTING'],['DIRECTION','LIGHTING'],['LIGHTING','LIGHTING'],['SOUND','CAMERA']])
async def test_unchanged_validator_rejects_without_filter_repair_or_retry(domains):
    body={**model_output('direction'),'professionalDomains':list(domains)};calls=[]
    with pytest.raises(ValidationError):ShotBody.model_validate(body)
    def mock(r):calls.append(r);return response(body)
    _,a,_=compose_authors(load_config(environment=ENV).text_composition,SKILLS,transport=httpx.MockTransport(mock))
    with pytest.raises(AuthorResultFailure) as caught:await a.author(request('direction'))
    assert caught.value.diagnostic.failure_stage=='SHOT_POST_VALIDATION'
    assert caught.value.diagnostic.validator=='ShotBody.domains'
    assert len(calls)==1 and body['professionalDomains']==domains


@pytest.mark.asyncio
@pytest.mark.parametrize('role',['canon','professional'])
async def test_direction_projection_preserves_other_role_contracts(role):
    domain_schema=TypeAdapter(CanonDraft if role=='canon' else tuple[DesignBody,...]).json_schema(by_alias=True)
    captured=[]
    def mock(r):captured.append(json.loads(r.content));return response(model_output(role))
    c,_,p=compose_authors(load_config(environment=ENV).text_composition,SKILLS,transport=httpx.MockTransport(mock))
    if role=='canon':await c.author(request())
    else:await p.design(request('professional'))
    schema=json.loads(captured[0]['messages'][0]['content'].rsplit('\nOutput JSON schema:\n',1)[1])
    expected=domain_schema if role=='canon' else professional_model_schema()
    assert schema==expected
    assert TypeAdapter(CanonDraft if role=='canon' else tuple[DesignBody,...]).json_schema(by_alias=True)==domain_schema
    assert 'CANON and DIRECTION must never appear in professionalDomains' not in captured[0]['messages'][0]['content']
