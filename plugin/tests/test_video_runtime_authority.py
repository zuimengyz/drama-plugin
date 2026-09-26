"""Runtime authority regressions. Synthetic approvals, mock transport, no paid calls."""
from copy import deepcopy
from types import SimpleNamespace
import json

import httpx
import pytest

from drama_plugin.config import load_config, VideoRoutePolicy
from drama_plugin.config.video_route import require_runtime_route
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.production_language import SpeechLanguageAuthorization
from drama_plugin.production_language import (
    dialogue_review_subject, resolve_profile, prepare_native_video_language,
    require_native_video_submission, require_video_request_language,
)
from drama_plugin.providers.video.registry import registry, model_availability
from drama_plugin.providers.video.adapters import SeedanceProvider
from drama_plugin.hosts.http_video import candidate, compile_request
from drama_plugin.visual.video_selection import choose, Cost, Quality, Evidence, Requirements
from test_video_selection import fixture as legacy_fixture, evidence
from test_official_video_providers import request, config, resolve, with_ir


def official_requirements(model='seedance-2-mini'):
    v = request()
    v.continuity.primary_model = model
    v = with_ir(v)
    r = Requirements(work_id='W', scene_id='SC', shot_id='SHOT', target_id='clip', shot_type='ENVIRONMENT',
        source_fingerprint='a'*64, mode='TEXT_TO_VIDEO', controls=['TEXT'], duration_seconds=5,
        aspect_ratio='16:9', sound='NATIVE', frozen_creative={'motion_prompt':v.prompt},
        inputs=[], video_request=v, required=['courtyard'], forbidden=['modern objects'])
    return r, official_candidate(r, model)


def official_candidate(r, model='seedance-2-mini'):
    return candidate(r, model, cost=Cost(components={'video':20,'audio':0,'references':0,'addons':0,'correction':0},
        evidence=evidence()), evidence=Evidence.model_validate(evidence()), quality=Quality())


def configured(monkeypatch, provider):
    monkeypatch.setenv('DRAMA_PLUGIN_VIDEO_PROVIDER', provider)
    monkeypatch.setenv('DRAMA_VIDEO_SEEDANCE_API_KEY', 'OFFLINE_ONLY')


def test_official_policy_cannot_be_trimmed_or_pinned_to_comfy(tmp_path, monkeypatch):
    r, official = official_requirements()
    _, comfy, *_ = legacy_fixture(tmp_path)
    configured(monkeypatch, 'official')
    assert choose(r, [comfy, official])['selected'] == official.candidate_id
    assert choose(r, [comfy])['selected'] is None
    with pytest.raises(ValueError, match='EXTERNAL_ROUTE_POLICY_CONFLICT'):
        choose(r, [comfy], task_policy=VideoRoutePolicy(mode='PIN', preferred_model='flux-3'))
    with pytest.raises(ValueError, match='EXTERNAL_ROUTE_POLICY_CONFLICT'):
        choose(r, [comfy], policy=VideoRoutePolicy())
    with pytest.raises(ValueError, match='PROVIDER_POLICY_CONFLICT'):
        require_runtime_route('comfy_cloud', 'flux-3')


def test_explicit_comfy_preserves_legacy_route(tmp_path, monkeypatch):
    r, comfy, *_ = legacy_fixture(tmp_path)
    _, official = official_requirements()
    configured(monkeypatch, 'comfy_cloud')
    assert choose(r, [official, comfy])['selected'] == comfy.candidate_id
    require_runtime_route('comfy_cloud', comfy.model)
    with pytest.raises(ValueError, match='PROVIDER_POLICY_CONFLICT'):
        require_runtime_route('seedance', 'seedance-2-mini')


def test_unavailable_official_blocks_without_comfy_fallback(tmp_path, monkeypatch):
    r, official = official_requirements()
    _, comfy, *_ = legacy_fixture(tmp_path)
    configured(monkeypatch, 'official')
    monkeypatch.setenv('DRAMA_VIDEO_SEEDANCE_API_KEY', '')
    assert choose(r, [official, comfy])['selected'] is None


def test_auto_and_specific_official_provider(tmp_path, monkeypatch):
    r, c, *_ = legacy_fixture(tmp_path)
    configured(monkeypatch, 'auto')
    assert choose(r, [c])['selected'] == c.candidate_id
    configured(monkeypatch, 'seedance')
    require_runtime_route('seedance', 'seedance-2-standard')
    with pytest.raises(ValueError, match='PROVIDER_POLICY_CONFLICT'):
        require_runtime_route('vidu', 'vidu-q3-turbo')


def test_config_file_is_reloaded_at_submission(tmp_path, monkeypatch):
    path = tmp_path/'runtime.yaml'
    path.write_text('video_route_policy:\n  provider: official\n')
    monkeypatch.setenv('DRAMA_PLUGIN_CONFIG_FILE', str(path))
    with pytest.raises(ValueError, match='PROVIDER_POLICY_CONFLICT'):
        require_runtime_route('comfy_cloud', 'flux-3')
    path.write_text('video_route_policy:\n  provider: comfy_cloud\n')
    require_runtime_route('comfy_cloud', 'flux-3')


def test_legacy_policy_snapshot_remains_readable(tmp_path):
    from test_mcp_execution import decision
    from drama_plugin.visual.video_selection import verify_decision
    d=decision(tmp_path)
    for name in ('configured_policy','effective_policy'):
        d['route_policy_resolution'][name].pop('provider')
    d['route_policy_resolution']['policy_fingerprint']=fp(d['route_policy_resolution']['effective_policy'])
    d['fingerprint']=fp({k:v for k,v in d.items() if k!='fingerprint'})
    verify_decision(d)


def test_unified_compile_cli_dispatches_official_without_comfy_graph(tmp_path,monkeypatch):
    import os
    import subprocess
    import sys
    from pathlib import Path
    from drama_plugin.visual.video_selection import ProductionRoute
    from drama_plugin.visual.execution import ExecutionRoute
    r,c=official_requirements()
    route=ProductionRoute(route_id='mock-http',work_id='W',stage_id='offline',creative_fingerprint=r.source_fingerprint,
        video_targets=[r.target_id],candidate=c,
        execution=ExecutionRoute(transport='HTTP',backend={'provider':'seedance','backend_key':'official'},
            capability={'kind':'video_generation','model_key':c.model}),
        requirements=dict(controls=r.controls,duration_seconds=r.duration_seconds,aspect_ratio=r.aspect_ratio,
            sound=r.sound,shot_type=r.shot_type,video_requests={r.target_id:dump_contract(r.video_request)}),
        quality_thresholds={'continuity':'source preserved'},stops=['mock only'],fallback='stop',
        generations_per_video_request=1,generation_count_evidence=evidence(),video_request_credits=20)
    data=dict(requirements=r.model_dump(mode='json'),candidate=c.model_dump(mode='json'),host_adapter={},
        production_route=route.model_dump(mode='json'),stage_id='offline',rationale='offline',fallback='stop')
    source=tmp_path/'input.json';source.write_text(json.dumps(data));output=tmp_path/'compiled'
    configured(monkeypatch,'official')
    script=Path(__file__).parents[1]/'skills/shot-production/scripts/compile_video.py'
    result=subprocess.run([sys.executable,str(script),'--input',str(source),'--output',str(output)],
                          env=os.environ.copy(),capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    sealed=json.loads((output/'sealed-request.json').read_text())
    assert sealed['execution']['transport']=='HTTP'
    assert sealed['request']['tool']=='video.create_task' and sealed['dry_run_only']


async def test_mcp_submission_rechecks_runtime_even_for_old_seal(tmp_path, monkeypatch):
    from test_mcp_execution import decision, reserved, Registry, binding, invoke_reserved
    from drama_plugin.hosts.comfy_video import verify_execution
    d = decision(tmp_path)
    reg = Registry([binding(d)])
    configured(monkeypatch, 'official')
    with pytest.raises(ValueError, match='PROVIDER_POLICY_CONFLICT'):
        await invoke_reserved(reserved(d), reg, verify_request=verify_execution)
    assert reg.calls == [] and reg.claims == set()


async def test_http_submission_rechecks_runtime_before_network(monkeypatch):
    configured(monkeypatch, 'comfy_cloud')
    calls = []
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: calls.append(r))) as client:
        p = SeedanceProvider('seedance-2-mini', config('seedance'), resolve=resolve, client=client)
        with pytest.raises(ValueError, match='PROVIDER_POLICY_CONFLICT'):
            await p.create_task(request(), client_request_id='offline')
    assert calls == []


def dream_fixture(tmp_path):
    """F01 language scenario; synthetic short line, not approval of the actual screenplay."""
    from test_production_language import fixture as language_fixture
    from test_seedance_prompt_generator import cinematic_sample, rebound
    from test_cinematic_direction import example
    from drama_plugin.visual.cinematic import freeze_direction, narrative_source, selection_handoff
    from drama_plugin.prompt_generators.contracts import ProjectionAnnotations
    c, metadata, _, intent, line = language_fixture()
    profile = resolve_profile('W', load_config(environment={
        'DRAMA_PLUGIN_SPOKEN_LANGUAGE_POLICY':'source_original',
        'DRAMA_PLUGIN_CREATIVE_REVIEW_LANGUAGE':'zh',
    }), c.package.artifacts, [metadata], c.package.source_artifact_id)
    intent.line_id='L'; intent.scene_id='SC'; intent.character_id='A'
    intent.review_status='APPROVED'; intent.approval_ref='mock-semantic-review'
    line.line_id='L'; line.scene_id='SC'; line.character_id='A'
    line.purpose='PRODUCTION'; line.semantic_intent_hash=fp(intent); line.language_profile_hash=fp(profile)
    line.review_status='APPROVED'; line.reviewer='mock-reviewer'; line.approval_ref='mock-russian-review'
    line.review_subject_hash=dialogue_review_subject(line)
    auth = SpeechLanguageAuthorization(profile=profile, intent=intent, line=line)
    work = SimpleNamespace(id='W', title='一个荒唐人的梦', content={
        'creativeSourceType':'LITERARY', 'literaryPackage':dump_contract(c.package),
        'productionLanguageProfile':dump_contract(profile), 'productionDialogueApprovals':{'L':fp(line)}})
    r = cinematic_sample(tmp_path)
    spec, context, visual = example()
    context['scene']['content']['spokenContent'][0]['text']=line.review_text
    spec.dialogue[0].text=line.review_text
    spec.reference_requirements=(); spec.execution_requirements.reference_roles=()
    spec.source_fingerprint=fp(narrative_source(context))
    frozen=freeze_direction(spec, context=context, visual_resolution=visual, host_review='MOCK ONLY')
    r=r.model_copy(update={'frozen_creative':selection_handoff(frozen), 'language':'zh'})
    before=deepcopy(r.frozen_creative)
    r=prepare_native_video_language(work,r,[auth])
    assert r.frozen_creative == before
    # Owner supplies exact approved production text into the existing IR audio slot.
    v=r.video_request
    ir=deepcopy(v.prompt_ir); ir['video_temporal']['audio_requirements'][0]['text']=line.production_text
    audio=v.prompt_projection.audio[0].model_copy(update={'text_hash':fp(line.production_text),'language':'ru'})
    v=rebound(v,prompt_ir=ir,prompt_projection=ProjectionAnnotations(audio=(audio,)))
    return work,r.model_copy(update={'video_request':v}),auth


async def test_source_original_russian_native_dialogue_in_mock_provider_projection(tmp_path):
    work,r,auth=dream_fixture(tmp_path)
    assert r.language == auth.profile.resolved_production_language == 'ru'
    assert auth.profile.creative_review_language == 'zh'
    c=official_candidate(r)
    projection=compile_request(r,c)
    decision={'requirements':r.model_dump(mode='json'), 'request':projection}
    require_native_video_submission(work,decision)
    assert auth.line.production_text in projection['promptCompilation']['prompt']
    assert auth.line.review_text not in projection['promptCompilation']['prompt']
    calls=[]
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda q: (calls.append(q) or httpx.Response(200,json={'id':'mock-job'})))) as client:
        p=SeedanceProvider(c.model,config('seedance'),resolve=resolve,client=client)
        await p.create_task(r.video_request,client_request_id='mock-dream')
    body=json.loads(calls[0].content)
    assert auth.line.production_text in body['content'][0]['text']
    assert auth.line.review_text not in body['content'][0]['text']


def test_comfy_projection_uses_same_approved_russian_dialogue(tmp_path):
    from drama_plugin.hosts.cinematic_projection import project
    from drama_plugin.hosts.comfy_video import inspect_graph
    from seedance_helpers import seed_fixture
    work,r,auth=dream_fixture(tmp_path)
    _,c,g,s,_=seed_fixture(tmp_path,'t2v')
    projected=project(r.model_copy(update={'video_request':None}),c,inspect_graph(g,s))
    assert projected['resolvedSpokenLanguage']=='ru'
    assert auth.line.production_text in projected['prompt']
    assert auth.line.review_text not in projected['prompt']
    require_native_video_submission(work,{'requirements':r.model_copy(update={'video_request':None}).model_dump(mode='json')})


def test_changed_runtime_language_blocks_without_rewriting_work(tmp_path,monkeypatch):
    work,r,_=dream_fixture(tmp_path)
    before=deepcopy(work.content)
    monkeypatch.setenv('DRAMA_PLUGIN_SPOKEN_LANGUAGE_POLICY','explicit')
    monkeypatch.setenv('DRAMA_PLUGIN_SPOKEN_LANGUAGE','zh')
    with pytest.raises(ValueError,match='RUNTIME_SPOKEN_LANGUAGE_CONFLICT'):
        require_native_video_submission(work,{'requirements':r.model_dump(mode='json')})
    assert work.content==before


def test_missing_original_language_cannot_resolve_as_review_language():
    from test_production_language import fixture as language_fixture
    c,metadata,*_=language_fixture()
    metadata.original_work_languages=()
    with pytest.raises(ValueError,match='SOURCE_ORIGINAL_LANGUAGE_REQUIRED'):
        resolve_profile('dream',load_config(environment={}),c.package.artifacts,[metadata],c.package.source_artifact_id)


async def test_direct_http_dialogue_cannot_omit_authorization(tmp_path):
    work,r,_=dream_fixture(tmp_path)
    v=r.video_request.model_copy(update={'production_dialogue':()})
    calls=[]
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda q: calls.append(q))) as client:
        p=SeedanceProvider('seedance-2-mini',config('seedance'),resolve=resolve,client=client)
        with pytest.raises(ValueError,match='APPROVED_PRODUCTION_DIALOGUE_REQUIRED'):
            await p.create_task(v,client_request_id='must-not-send')
    assert calls==[]


async def test_formal_begin_submission_blocks_unbound_comfy_dialogue_before_write(tmp_path,monkeypatch):
    from drama_plugin.hosts.route_production import operate
    from test_production_route import route
    work,r,_=dream_fixture(tmp_path)
    r=r.model_copy(update={'production_dialogue':(), 'video_request':None})
    snapshot=dict(schema='video-decision-v1',requirements=r.model_dump(mode='json'),
        execution=dict(transport='MCP',capability={'model_key':'flux-3'}))
    work.content.update(productionRoute=route(tmp_path).model_dump(mode='json'),
        productionStage={'attempts':[{'attempt_id':'offline','frame_snapshot':snapshot}]})
    writes=[]
    class Memory:
        async def get_work(self,_):return work
        async def save_work(self,*args,**kwargs):writes.append(args)
    async def checked_sources(*_):pass
    # Source/rights validation is covered independently; exercise the actual live
    # language gate in operate, with no provider or stage mutation permitted.
    monkeypatch.setattr('drama_plugin.hosts.route_production.validate_route_direction_sources',checked_sources)
    with pytest.raises(ValueError,match='APPROVED_PRODUCTION_DIALOGUE_REQUIRED'):
        await operate(Memory(),'W','begin-submission',{'attempt_id':'offline'})
    assert writes==[]


@pytest.mark.parametrize('fault', ['missing_profile','missing_authorization','unapproved_line','wrong_language','wrong_production_text','missing_audio_binding'])
def test_native_dialogue_blocks_missing_or_changed_authority(tmp_path,fault):
    work,r,auth=dream_fixture(tmp_path)
    if fault=='missing_profile': work.content.pop('productionLanguageProfile')
    elif fault=='missing_authorization': r=r.model_copy(update={'production_dialogue':()})
    elif fault=='unapproved_line': work.content['productionDialogueApprovals']={}
    elif fault=='wrong_language': r=r.model_copy(update={'language':'zh'})
    elif fault=='wrong_production_text':
        ir=deepcopy(r.video_request.prompt_ir);ir['video_temporal']['audio_requirements'][0]['text']=auth.line.review_text
        r=r.model_copy(update={'video_request':r.video_request.model_copy(update={'prompt_ir':ir})})
    else: r=r.model_copy(update={'video_request':r.video_request.model_copy(update={'prompt_projection':None})})
    with pytest.raises(ValueError,match='LANGUAGE|PRODUCTION|DIALOGUE|CLASSIFICATION'):
        require_native_video_submission(work,{'requirements':r.model_dump(mode='json')})


def test_seedance_standard_fast_mini_registry_config_and_payload():
    names=['Seedance 2.0','Seedance 2.0 Fast','Seedance 2.0 Mini']
    keys=['seedance-2-standard','seedance-2-fast','seedance-2-mini']
    enum=model_availability({})
    assert [enum[k]['display_name'] for k in keys] == names
    assert len({enum[k]['vendor_model'] for k in keys}) == 3
    # IDs retained from the pre-existing project official registry, not invented here.
    assert registry()['models'][keys[0]]['vendor_model'] == 'doubao-seedance-2-0-260128'
    for key in keys:
        cfg=load_config(environment={'DRAMA_PLUGIN_VIDEO_ROUTE_MODE':'PIN','DRAMA_PLUGIN_VIDEO_MODEL_PREFERRED':key})
        assert cfg.video_route_policy.preferred_model == key
        r,c=official_requirements(key)
        assert choose(r,[c],policy=cfg.video_route_policy)['selected'] == c.candidate_id
        assert compile_request(r,c)['promptCompilation']['generator']['family']=='seedance_2'
