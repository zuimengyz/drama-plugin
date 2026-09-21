"""Pure authority regression; no persisted Work, media, or provider requests."""
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from drama_plugin.config import load_config
from drama_plugin.config.video_route import VideoRoutePolicy, resolve_policy
from drama_plugin.context.rhythm import RhythmContextProvider
from drama_plugin.contracts.context import ContextBuildRequest, CreativeRhythm
from drama_plugin.contracts.audio import (
    CreativeVoiceProfile, VoiceProfile, SpeechGenerationRequest, TargetTimingPolicy,
    validate_scene_performance_authority,
)
from drama_plugin.exceptions import RhythmAuthorityConflict
from drama_plugin.providers.speech.role_dubbing import _native_performance, _projected_performance


class NoReads:
    async def build_context(self, request):
        raise AssertionError('must reject or create an empty context without reading memory')


PATHS = [('rhythm_speed',), ('rhythmSpeed',)] + [
    (outer, inner) for outer in ('creativeRhythm', 'creative_rhythm')
    for inner in ('rhythm_speed', 'rhythmSpeed')
]


def options(path, value):
    return {'newWork': True, path[0]: value if len(path) == 1 else {path[1]: value}}


@pytest.mark.asyncio
@pytest.mark.parametrize('path', PATHS)
@pytest.mark.parametrize('source', ['environment', 'explicit_config', 'default'])
async def test_all_task_aliases_assert_only_one_rhythm(tmp_path, path, source):
    if source == 'explicit_config':
        p = tmp_path / 'config.yaml'; p.write_text('rhythm_speed: medium\n')
        config = load_config(p, environment={})
    else:
        config = load_config(environment={'rhythm_speed':'medium'} if source == 'environment' else {})
    provider = RhythmContextProvider(NoReads(), config)
    request = ContextBuildRequest(scope='WORK', resource_id='smoke-only', purpose='WORK_CREATION', options=options(path, 'fast'))
    with pytest.raises(RhythmAuthorityConflict, match='RHYTHM_AUTHORITY_CONFLICT'):
        await provider.build_context(request)
    same = request.model_copy(update={'options': options(path, config.rhythm_speed)})
    result = await provider.build_context(same)
    assert result.creative_rhythm == provider.rhythm and result.work is None


@pytest.mark.asyncio
@pytest.mark.parametrize('assertions', [
    {'rhythm_speed':'medium','rhythmSpeed':'fast'},
    {'rhythm_speed':'medium','creativeRhythm':{'rhythmSpeed':'fast'}},
    {'creativeRhythm':{'rhythm_speed':'medium','rhythmSpeed':'fast'}},
    {'creativeRhythm':None}, {'creative_rhythm':{}}, {'rhythm_speed':None},
])
async def test_one_correct_alias_cannot_hide_another_conflict(assertions):
    provider = RhythmContextProvider(NoReads(), load_config(environment={'rhythm_speed':'medium'}))
    request = ContextBuildRequest(scope='WORK', resource_id='smoke-only', purpose='WORK_CREATION', options={'newWork':True,**assertions})
    with pytest.raises(RhythmAuthorityConflict): await provider.build_context(request)


@pytest.mark.asyncio
async def test_refresh_asserts_preserved_rhythm_not_new_config():
    request = ContextBuildRequest(scope='WORK', resource_id='smoke-only', purpose='WORK_CREATION', options={'newWork':True})
    first = RhythmContextProvider(NoReads(), load_config(environment={'rhythm_speed':'medium'}))
    current = await first.build_context(request)
    later = RhythmContextProvider(NoReads(), load_config(environment={'rhythm_speed':'fast'}))
    same = request.model_copy(update={'options':{'newWork':True,'rhythm_speed':'medium'}})
    assert not (await later.refresh_context(same,current)).changes
    conflict = request.model_copy(update={'options':{'newWork':True,'rhythm_speed':'fast'}})
    with pytest.raises(RhythmAuthorityConflict): await later.refresh_context(conflict,current)


def test_rhythm_has_one_canonical_public_key_and_legacy_read():
    for alias in ('rhythm_speed','rhythmSpeed'):
        value = CreativeRhythm.model_validate({alias:'medium','source':'fixture','semantics':'fixture'})
        assert value.model_dump(by_alias=True) == {'rhythm_speed':'medium','source':'fixture','semantics':'fixture'}
    assert 'rhythm_speed' in CreativeRhythm.model_json_schema()['required']
    assert 'rhythmSpeed' not in CreativeRhythm.model_json_schema()['properties']


def test_default_auto_allows_task_constraint_but_explicit_policy_does_not(tmp_path):
    task = VideoRoutePolicy(mode='PIN',preferred_model='flux-3')
    default = load_config(environment={}).video_route_policy
    assert default.source == 'DEFAULT_AUTO'
    assert resolve_policy(default,task).source == 'TASK_OVERRIDE'
    p = tmp_path / 'config.yaml'
    p.write_text('video_route_policy:\n  mode: PIN\n  preferred_model: seedance-2.5\n')
    explicit = load_config(p,environment={}).video_route_policy
    assert explicit.source == 'PLUGIN_CONFIG'
    with pytest.raises(ValueError,match='EXTERNAL_ROUTE_POLICY_CONFLICT'): resolve_policy(explicit,task)
    assert resolve_policy(explicit,explicit) == explicit


def speech(intent):
    profile = VoiceProfile(profile_id='local-test-profile', speaker_key='local-test-role',
        creative_profile=CreativeVoiceProfile(timbre='dark',timbre_brightness='SLIGHTLY_DARK'))
    return SpeechGenerationRequest(work_id='no-persisted-work',scene_id='no-persisted-scene',spoken_content_id='line',
        exact_text='请停步。',speaker_key=profile.speaker_key,voice_profile=profile,performance_intent=intent,
        target_timing_policy=TargetTimingPolicy(policy='NATURAL'))


@pytest.mark.parametrize('field', [
    'timbre','timbreBrightness','timbre_brightness','voiceIdentityRef','voice_identity_ref',
    'voiceProfile','stable_profile','creativeProfile','providerMappings','speaker_key',
    'baselinePace','vocalAge','resonanceDepth','texture','register','roughness','breathiness',
    'brightness','creativeCastingProfile','sourceProfileId','voiceUseCase',
])
@pytest.mark.parametrize('container', ['sceneDelta','scene_delta','direct','nested'])
def test_legacy_identity_rejected_in_contract_and_mutable_adapter(field,container):
    bad = {field:'forbidden'}
    intent = bad if container == 'direct' else {'beats':[{'performance':bad}]} if container == 'nested' else {container:bad}
    with pytest.raises(ValidationError,match='STABLE_VOICE_AUTHORITY_CONFLICT'): speech(intent)
    valid = speech({})
    # Direct model mutation/copy must not bypass the pre-provider gate either.
    valid.performance_intent = intent
    for guard in (_native_performance,_projected_performance):
        with pytest.raises(ValueError,match='STABLE_VOICE_AUTHORITY_CONFLICT'):
            guard(SimpleNamespace(speech_request=valid))


def test_every_non_transient_profile_field_is_protected_in_both_spellings():
    for name,field in CreativeVoiceProfile.model_fields.items():
        if name in {'articulation','restraint','energy','power'}:continue
        for alias in {name,field.alias or name}:
            with pytest.raises(ValueError,match='STABLE_VOICE_AUTHORITY_CONFLICT'):
                validate_scene_performance_authority({'sceneDelta':{alias:'change'}})


def test_legal_scene_delivery_remains_compatible_and_preserves_identity():
    delta = {'paceAdjustment':'SLOWER','volumeAdjustment':'LOWER','pace':'deliberate',
        'pause':'before reply','breath':'strained','volume':'close address',
        'restraint':'high','articulation':'firm','energy':'low','power':'contained',
        'linePerformance':{'emphasis':'last word'},'sceneState':{'urgency':'high'}}
    request = speech({'sceneDelta':delta})
    assert request.performance_intent['sceneDelta'] == delta
    assert _native_performance(SimpleNamespace(speech_request=request))[0] == .92
    assert request.voice_profile.creative_profile.timbre == 'dark'
    assert _projected_performance(SimpleNamespace(speech_request=request)) is None
