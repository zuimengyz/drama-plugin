"""Shared external generation policy; in-process HTTP contract smoke only."""
import json

import httpx
import pytest
from drama_plugin.config.loader import load_config
from drama_plugin.config.text_composition import TextCompositionConfig
from drama_plugin.creative_engine.backends import compose_authors
from drama_plugin.execution.transport import CapabilityAbsent
from drama_plugin.exceptions import ConfigurationError
from test_formal_author_backends import ENV, SKILLS, canon, model_output, request, response

POLICY_ENV = {**ENV, 'DRAMA_PLUGIN_TEXT_COMPOSITION_PROVIDER':'deepseek',
              'DRAMA_PLUGIN_TEXT_COMPOSITION_MAX_TOKENS':'65536',
              'DRAMA_PLUGIN_TEXT_COMPOSITION_REASONING_EFFORT':'high'}


def test_external_shared_policy_overrides_yaml(tmp_path):
    path=tmp_path/'policy.yaml'
    path.write_text('text_composition:\n  max_output_tokens: 4096\n  reasoning_effort: low\n')
    config=load_config(path,environment=POLICY_ENV).text_composition
    assert config.max_output_tokens==65536 and config.reasoning_effort=='high'
    assert all(config.available(r) for r in ('canon','direction','professional'))
    assert ENV['DRAMA_PLUGIN_TEXT_COMPOSITION_API_KEY'] not in repr(config)
    assert ENV['DRAMA_PLUGIN_TEXT_COMPOSITION_API_KEY'] not in config.model_dump_json()


@pytest.mark.parametrize('field,value',[
    ('DRAMA_PLUGIN_TEXT_COMPOSITION_MAX_TOKENS','393217'),
    ('DRAMA_PLUGIN_TEXT_COMPOSITION_MAX_TOKENS','511'),
    ('DRAMA_PLUGIN_TEXT_COMPOSITION_MAX_TOKENS',''),
    ('DRAMA_PLUGIN_TEXT_COMPOSITION_REASONING_EFFORT','unsupported'),
])
def test_policy_bound_and_invalid_values_rejected_without_secret(field,value):
    with pytest.raises(ConfigurationError) as error:
        load_config(environment={**POLICY_ENV,field:value})
    assert ENV['DRAMA_PLUGIN_TEXT_COMPOSITION_API_KEY'] not in str(error.value)


@pytest.mark.asyncio
@pytest.mark.parametrize('role',['canon','direction','professional'])
async def test_each_formal_author_projects_the_same_shared_policy(role):
    calls=[]
    def handler(req):
        body=json.loads(req.content);calls.append(body)
        assert body['max_tokens']==65536 and body['reasoning_effort']=='high'
        assert body.get('thinking',{}).get('type')!='disabled'
        assert body['model']=={'canon':'offline-canon-model','direction':'offline-direction-model','professional':'offline-professional-model'}[role]
        assert 'tools' not in body
        assert ENV['DRAMA_PLUGIN_TEXT_COMPOSITION_API_KEY'] not in json.dumps(body)
        return response(model_output(role))
    c,d,p=compose_authors(load_config(environment=POLICY_ENV).text_composition,SKILLS,transport=httpx.MockTransport(handler))
    if role=='canon':assert (await c.author(request())).work==canon().work
    elif role=='direction':await d.author(request(role))
    else:await p.design(request(role))
    assert len(calls)==1


@pytest.mark.asyncio
async def test_length_is_still_rejected_without_retry():
    calls=[]
    def handler(req):calls.append(req);return response(model_output('canon'),finish='length')
    c,_,_=compose_authors(load_config(environment=POLICY_ENV).text_composition,SKILLS,transport=httpx.MockTransport(handler))
    with pytest.raises(ValueError,match='AUTHOR_RESULT_INCOMPLETE'):await c.author(request())
    assert len(calls)==1


@pytest.mark.asyncio
async def test_unqualified_provider_cannot_silently_drop_reasoning_policy():
    calls=[]
    env={**POLICY_ENV,'DRAMA_PLUGIN_TEXT_COMPOSITION_PROVIDER':'unqualified-text-provider'}
    c,_,_=compose_authors(load_config(environment=env).text_composition,SKILLS,transport=httpx.MockTransport(lambda req:calls.append(req) or response(model_output('canon'))))
    with pytest.raises(CapabilityAbsent,match='REASONING_POLICY_UNSUPPORTED'):await c.author(request())
    assert calls==[]


@pytest.mark.asyncio
async def test_unset_policy_retains_compatible_wire_without_claiming_effort():
    calls=[]
    def handler(req):calls.append(json.loads(req.content));return response(model_output('canon'))
    c,_,_=compose_authors(load_config(environment=ENV).text_composition,SKILLS,transport=httpx.MockTransport(handler))
    await c.author(request())
    assert 'reasoning_effort' not in calls[0]
    assert calls[0]['max_tokens']==TextCompositionConfig().max_output_tokens
