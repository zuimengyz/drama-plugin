"""Text-only authority regressions: no provider submission or media creation."""
from pathlib import Path
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from drama_plugin.config import load_config
from drama_plugin.config.video_route import resolve_policy, VideoRoutePolicy
from drama_plugin.exceptions import ConfigurationError, ContractValidationError
from drama_plugin.contracts.audio import CreativeCastingDimension
from drama_plugin.audio.creative_casting import project_creative_voice_casting_profile
from drama_plugin.providers.speech.role_dubbing import _native_performance
from drama_plugin.providers.http.providers import HttpProductionProvider
from drama_plugin.contracts.creation import Episode, Scene
from test_audio_foundation import voice


def test_example_config_is_loadable():
    example = Path(__file__).parents[2] / 'drama-plugin.env.example'
    env = dict(line.split('=', 1) for line in example.read_text().splitlines()
               if line and not line.startswith('#') and '=' in line)
    config = load_config(environment=env)
    assert config.rhythm_speed == 'work_defined'
    assert config.services.role_dubbing.api_key is None


def test_explicit_empty_env_clears_saved_credentials_endpoints_and_fallbacks(tmp_path):
    p = tmp_path / 'config.yaml'
    p.write_text('''services:
  memory: {base_url: 'https://old.invalid', api_token: OLD_TEST_KEY}
  role_dubbing: {api_key: OLD_TEST_KEY, output_directory: /old}
  qwen_omni: {api_key: OLD_TEST_KEY, base_url: 'https://old.invalid'}
video_route_policy:
  mode: PREFER
  preferred_model: seedance-2.5
  fallbacks: [flux-3]
''')
    c = load_config(p, environment={
        'DRAMA_PLUGIN_SERVICE_MEMORY_BASE_URL': '', 'DRAMA_PLUGIN_SERVICE_MEMORY_API_TOKEN': '',
        'FISH_AUDIO_API_KEY': '', 'DRAMA_PLUGIN_ROLE_DUBBING_OUTPUT_DIRECTORY': '',
        'DRAMA_PLUGIN_PROVIDER_QWEN_OMNI_API_KEY': '', 'DRAMA_PLUGIN_PROVIDER_QWEN_OMNI_BASE_URL': '',
        'DRAMA_PLUGIN_VIDEO_MODEL_FALLBACKS': '', 'rhythm_speed': 'fast',
    })
    assert c.services.memory.base_url == '' and c.services.memory.api_token is None
    assert c.services.role_dubbing.api_key is None and c.services.role_dubbing.output_directory == ''
    assert c.services.qwen_omni.base_url == '' and not c.services.qwen_omni.api_key.get_secret_value()
    assert c.video_route_policy.fallbacks == () and c.rhythm_speed == 'fast'


@pytest.mark.parametrize('key', ['DRAMA_PLUGIN_PROVIDER_MEMORY_MODE', 'DRAMA_PLUGIN_SERVICE_MEMORY_TIMEOUT_SECONDS',
    'DRAMA_PLUGIN_PROVIDER_AUDIO_SEMANTIC_MODE', 'FISH_TTS_MODEL', 'rhythm_speed'])
def test_explicit_invalid_env_does_not_fall_back(key):
    with pytest.raises(ConfigurationError):
        load_config(environment={key: ''})


def test_external_route_authority_and_receipt_replay(tmp_path):
    from test_video_route_policy import candidates
    from drama_plugin.visual.video_selection import choose, verify_policy_resolution
    from drama_plugin.contracts.base import sha256_canonical
    p = load_config(environment={'DRAMA_PLUGIN_VIDEO_ROUTE_MODE':'PIN',
        'DRAMA_PLUGIN_VIDEO_MODEL_PREFERRED':'seedance-2.5'}).video_route_policy
    task = VideoRoutePolicy(mode='PIN', preferred_model='flux-3')
    with pytest.raises(ValueError, match='EXTERNAL_ROUTE_POLICY_CONFLICT'):
        resolve_policy(p, task)
    assert resolve_policy(p, p).source == p.source
    r, cs = candidates(tmp_path)
    selection = choose(r, cs, policy=p)
    receipt = selection['route_policy_resolution']
    receipt['effective_policy']['source'] = 'TASK_OVERRIDE'
    receipt['source'] = 'TASK_OVERRIDE'
    receipt['policy_fingerprint'] = sha256_canonical(receipt['effective_policy'])
    with pytest.raises(ValueError, match='POLICY_SOURCE_MISMATCH'):
        verify_policy_resolution(receipt, cs[0], selection['candidates'][0], dry_run=False)


def test_known_voice_identity_cannot_be_overwritten_by_casting_art():
    v = voice(vocal_age='MATURE_ADULT')
    with pytest.raises(ValueError, match='STABLE_VOICE_AUTHORITY_CONFLICT'):
        project_creative_voice_casting_profile(v, artistic_decisions={
            'vocalAge': CreativeCastingDimension(value='LATE_MIDDLE_ADULT', basis_refs=['creative:unapproved'])})
    result = project_creative_voice_casting_profile(v, artistic_decisions={
        'vocalAge': CreativeCastingDimension(value='MATURE_ADULT', basis_refs=['creative:duplicate'])})
    assert result.dimensions['vocalAge'].basis_refs == ['VoiceProfile.creativeProfile.vocal_age']


def test_legacy_voice_projection_has_no_neutral_value_shadow():
    speech = SimpleNamespace(material_render_parameters={}, performance_intent={'sceneDelta':{'paceAdjustment':'SLOWER'}})
    req = SimpleNamespace(speech_request=speech)
    assert _native_performance(req) == (.92, 0.)
    speech.material_render_parameters['speed'] = 1.0
    with pytest.raises(ValueError, match='VOICE_INTENT_RENDER_CONFLICT'):
        _native_performance(req)
    speech.performance_intent = {}
    assert _native_performance(req) == (1., 0.)


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['image', 'video'])
async def test_legacy_http_generation_cannot_bypass_registry_gate(kind):
    class NoTransport:
        async def request(self, *a, **k):
            raise AssertionError('transport must never execute')
    with pytest.raises(ContractValidationError, match='FORMAL_ROUTE_RESERVATION'):
        await getattr(HttpProductionProvider(NoTransport()), 'generate_' + kind)('raw prompt')


def test_negative_structural_numbers_rejected_like_java():
    with pytest.raises(ValidationError):
        Episode(id='e', script_id='s', episode_no=-1, title='fixture')
    with pytest.raises(ValidationError):
        Scene(id='s', episode_id='e', order=-1, title='fixture')


def test_provider_prompt_is_exact_core_compilation():
    from test_official_video_providers import request, config, resolve, MODELS
    from drama_plugin.providers.video.adapters import ADAPTERS
    from drama_plugin.visual.video_prompt import prompt_compilation
    import json
    import httpx
    r = request()
    compiled = prompt_compilation(r)
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: (_ for _ in ()).throw(AssertionError())))
    p = ADAPTERS['seedance'](MODELS['seedance'], config('seedance'), resolve=resolve, client=client)
    texts = [item['text'] for item in p.payload(r, {}, 'offline')['content'] if item['type']=='text']
    assert texts == [compiled['prompt']]
    assert compiled['schema'] == 'visual-prompt-compilation-v1'
    assert compiled['generator']['family'] == 'seedance_2'
    assert compiled['statistics']['uncovered_required'] == 0


@pytest.mark.asyncio
async def test_formal_http_compile_reserve_replays_receipt_without_media_or_auth_claim(tmp_path):
    from drama_plugin import DramaPlugin
    from drama_plugin.providers.mock import MockDramaData
    from drama_plugin.hosts.http_video import verify_execution
    from drama_plugin.contracts.base import sha256_canonical
    from test_official_video_providers import formal_setup
    from copy import deepcopy
    import httpx
    data = MockDramaData()
    plugin = DramaPlugin.load(Path(__file__).parents[1], mock_data=data)
    x = SimpleNamespace(data=data, memory=plugin.providers.memory, store=plugin.providers.media,
                        asset=plugin.providers.asset, tmp=tmp_path)
    def no_call(req):
        raise AssertionError('No Provider request is allowed in this regression')
    async with httpx.AsyncClient(transport=httpx.MockTransport(no_call)) as client:
        host, attempt_id = await formal_setup(x, client)
        a = await host._attempt(data.work.id, attempt_id)
        assert a['execution_binding']['authentication_status'] == 'CONFIGURED_NOT_VERIFIED'
        assert 'authenticated' not in a['execution_binding']
        decision = a['frame_snapshot']
        verify_execution(decision)
        compilation = decision['request']['promptCompilation']
        assert compilation['generator']['family'] == 'seedance_2'
        assert compilation['coverage'] and compilation['statistics']['uncovered_required'] == 0
        forged = deepcopy(decision)
        forged['request']['promptCompilation']['prompt'] = 'Host replacement'
        forged['fingerprint'] = sha256_canonical({k:v for k,v in forged.items() if k!='fingerprint'})
        with pytest.raises(ValueError):
            verify_execution(forged)
        from drama_plugin.visual.execution import validate_http_binding
        false_claim = {**a['execution_binding'], 'authentication_status':'VERIFIED'}
        with pytest.raises(ValueError, match='HTTP_PROVIDER_BINDING_REQUIRED'):
            validate_http_binding(decision, false_claim)
        # A legacy binding is only readable as credential presence, never verified auth.
        legacy_binding = {k:v for k,v in a['execution_binding'].items() if k!='authentication_status'}
        legacy_binding['authenticated'] = True
        validate_http_binding(decision, legacy_binding)
        from drama_plugin.visual.video_selection import Requirements, Candidate
        from drama_plugin.hosts.http_video import seal_execution
        legacy_request = {k:v for k,v in decision['request'].items() if k!='promptCompilation'}
        seal_execution(Requirements.model_validate(decision['requirements']),
                       Candidate.model_validate(decision['candidate']), legacy_request, {})


def test_optional_audio_config_does_not_mislabel_route_errors():
    with pytest.raises(ConfigurationError, match='Invalid video route policy'):
        load_config(environment={'DRAMA_PLUGIN_VIDEO_ROUTE_MODE':'typo',
                                 'DRAMA_PLUGIN_PROVIDER_AUDIO_SEMANTIC_MODE':'off',
                                 'DRAMA_PLUGIN_PROVIDER_QWEN_OMNI_API_KEY':''})
