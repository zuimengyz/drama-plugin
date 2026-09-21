"""Offline isolation and exact-source projection; no media calls."""
from types import SimpleNamespace
import pytest
from drama_plugin.contracts.base import dump_contract as dump, sha256_canonical as fp
from drama_plugin.contracts.expression import CharacterExpressionProfiles, ActionExpressionBinding
from drama_plugin.contracts.visual_route import RouteStyleContract
from drama_plugin.expression import select_expression, casting_expression, project_action_expression
from drama_plugin.full_body_casting import full_body_design, executable_full_body
from drama_plugin.contracts.cinematic import CinematicShotSpec
from drama_plugin.visual.cinematic import execution_brief, validate_canon, narrative_source, freeze_direction
from test_full_body_casting import fixture
from test_cinematic_direction import example


def bundle(character='A'):
    core=dict(identity=character,revision='1',archetype='tragic_warlord',personalityCore=['decisive'],historicalPosition='commander',storyFacts=['unchanged outcome'],sourcePins={'core':'a'*64})
    common=dict(character=character,coreFingerprint=fp(core),revision='1')
    cg=dict(**common,route='stylized_cinematic_cg',visualLanguage='HEROIC_CINEMATIC_CG',heroicExaggeration='heroic',silhouetteStrength='high',physicalPresence='dominant',facialIntensity='high',costumeIconicity='high',kineticPotential='high',cinematicScale='high',martialAura='dominant',imperialPresence='high',maxActionIntensity='extreme_heroic',design=dict(face='sculpted brow and angular jaw',body='long powerful limbs, heroic proportion',costume='iconic jointed armor',posture='weight-bearing turned stance',camera='mild low-angle heroic composition',actionSignature='POWER MOMENTUM DOMINANCE'))
    live=dict(**common,route='live_action_realist',visualLanguage='LIVE_ACTION_REALIST',proportions='real_human',performanceRange='human_performable',equipmentRange='wearable_executable',cameraRange='restrained_motivated',maxActionIntensity='cinematic',design=dict(face='performable focused gaze',body='real human proportions',costume='wearable period armor',posture='balanced stance',camera='restrained eye-level view',actionSignature='performable footwork'))
    return CharacterExpressionProfiles.model_validate(dict(characterCoreProfile=core,cgExpressionProfile=cg,liveActionExpressionProfile=live))


def binding(b,actions,level='heroic',route='stylized_cinematic_cg',function='action'):
    return ActionExpressionBinding(core=b.character_core_profile,profile=select_expression(b,route),sourceActionFingerprint=fp(actions),director=dict(authority='DIRECTOR',sourceRef='director:1',actionSourceRef='action:1',cameraSourceRef='camera:1',workId='W',sceneId='SC',shotId='SHOT',sceneFunction=function,dramaticReason='reveal force',actionIntensity=level,rhythmIntent='motion then recovery',phases=dict(anticipation='foot support and hip preload',acceleration='hip drives weapon',impact='existing contact only',followThrough='recover balance under inertia',environmentalReaction='cloth follows motion'),cameraLanguage='observe load transfer'))


def test_independent_templates_and_no_fallback():
    b=bundle();before=dump(b)
    cg=casting_expression(b,'stylized_cinematic_cg','HERO_CASTING');live=casting_expression(b,'live_action_realist','DESIGN_NEUTRAL')
    assert all(x in cg for x in ('FULL BODY','authored proportion','character-specific screen presence'))
    assert 'real human proportions' not in cg and 'long powerful limbs' not in live and 'heroicExaggeration' not in live
    assert dump(b)==before
    with pytest.raises(ValueError):casting_expression(b,'live_action_realist','HERO_CASTING')
    b.live_action_expression_profile=None
    with pytest.raises(ValueError,match='NO_FALLBACK'):select_expression(b,'live_action_realist')


@pytest.mark.parametrize('field,value',[('heroicExaggeration','heroic'),('maxActionIntensity','heroic'),('visualLanguage','HEROIC_CINEMATIC_CG')])
def test_live_schema_rejects_cg(field,value):
    raw=dump(bundle());raw['liveActionExpressionProfile'][field]=value
    with pytest.raises(ValueError):CharacterExpressionProfiles.model_validate(raw)


def test_core_revision_and_realistic_cg():
    raw=dump(bundle());raw['cgExpressionProfile']['visualLanguage']='REALISTIC_CG'
    with pytest.raises(ValueError):CharacterExpressionProfiles.model_validate(raw)
    raw=dump(bundle());raw['characterCoreProfile']['revision']='2'
    with pytest.raises(ValueError):CharacterExpressionProfiles.model_validate(raw)


def test_full_body_current_work_binding(tmp_path):
    w,p,v,c,s=fixture(tmp_path);s.expression_profiles=bundle(p.identity);s.casting_mode='HERO_CASTING';c.style.visual_language='HEROIC_CINEMATIC_CG'
    from test_casting_visual_compilation import intents
    s.mode_visual_intents=intents()
    s.lighting_background='LEGACY STUDIO MUST NOT LEAK';s.costume='LEGACY COSTUME MUST NOT LEAK'
    d=full_body_design(p,v,c,s);assert 'LEGACY' not in d['prompt'] and 'HERO_CASTING' in d['prompt']
    w.content['visualRouteBinding']['styleFingerprint']=fp(c.style);w.content['characterCastingAuthorizations']['task']['inputsFingerprint']=d['inputsFingerprint']
    with pytest.raises(ValueError,match='CURRENT_WORK_EXPRESSION'):executable_full_body(w,p,v,c,s,'task')
    w.content['characterExpressionProfiles']={p.identity:dump(s.expression_profiles)}
    assert executable_full_body(w,p,v,c,s,'task')['maxOutputs']==1
    s.expression_profiles.cg_expression_profile.design.body='changed'
    with pytest.raises(ValueError):executable_full_body(w,p,v,c,s,'task')


def test_legacy_replay_and_no_shared_wrapper(tmp_path):
    _,p,v,c,s=fixture(tmp_path)
    assert 'castingMode' not in dump(s) and 'expressionProfiles' not in dump(s) and 'visualLanguage' not in dump(c.style)
    spec,_,_=example();assert 'expressionDirection' not in dump(spec)
    from drama_plugin.casting_discriminants import compile_visual_discriminants
    c.style.visual_language='HEROIC_CINEMATIC_CG'
    with pytest.raises(ValueError,match='ROUTE_OWNED'):compile_visual_discriminants(p,v,'n','FACE',route_context=c)
    raw=dump(c.style);raw['visualRoute']='live_action_realist';raw['medium']='PHOTOGRAPHIC'
    with pytest.raises(ValueError,match='LANGUAGE_ROUTE'):RouteStyleContract.model_validate(raw)


def test_action_same_facts_different_presentation():
    actions=[{'actor':'A','behavior':'one spear strike contacts one shield; defender steps back'}];b=bundle()
    g=project_action_expression(actions,binding(b,actions,'grounded'));h=project_action_expression(actions,binding(b,actions))
    assert g['canonicalActions']==h['canonicalActions']==actions and g['presentation']!=h['presentation']
    assert 'Forbidden: magic' in h['physicalBoundary'] and h['scope']=='ONLY_NAMED_CHARACTER_NOT_OTHER_ACTORS'
    h['canonicalActions'][0]['behavior']='changed';assert actions[0]['behavior'].startswith('one spear')
    with pytest.raises(ValueError,match='SOURCE_EVENTS_CHANGED'):project_action_expression([],binding(b,actions))


@pytest.mark.parametrize('level,function,route',[('heroic','quiet','stylized_cinematic_cg'),('extreme_heroic','action','stylized_cinematic_cg'),('heroic','action','live_action_realist')])
def test_director_caps(level,function,route):
    with pytest.raises(ValueError):binding(bundle(),[],level,route,function)


def test_soldier_has_own_signature_and_cap():
    b=bundle('soldier');b.cg_expression_profile.heroic_exaggeration='restrained';b.cg_expression_profile.max_action_intensity='grounded';b.cg_expression_profile.design.action_signature='keep rank, short defensive steps'
    with pytest.raises(ValueError,match='EXCEEDS'):binding(b,[])
    assert project_action_expression([],binding(b,[],'grounded'))['characterSignature']!=project_action_expression([],binding(bundle(),[]))['characterSignature']


def test_cinematic_canon_and_provider_projection():
    spec,ctx,visual=example();b=bundle();actions=[dump(x) for x in spec.performance.beats]
    spec.expression_direction=binding(b,actions,'grounded',function='quiet');spec=CinematicShotSpec.model_validate(dump(spec))
    ctx['work']['content'].update(visualRoute='stylized_cinematic_cg',characterExpressionProfiles={'A':dump(b)})
    spec.source_fingerprint=fp(narrative_source(ctx));validate_canon(spec,ctx)
    assert 'POWER MOMENTUM DOMINANCE' in execution_brief(spec)
    spec.reference_requirements=();spec.execution_requirements.reference_roles=()
    frozen=freeze_direction(spec,context=ctx,visual_resolution=visual,host_review='offline mechanics checked')
    from drama_plugin.hosts.cinematic_projection import project
    r=SimpleNamespace(frozen_creative={'cinematic_direction':frozen},sound='NATIVE_AV',reference_duties=[])
    result=project(r,SimpleNamespace(parameters={'model.generate_audio':True}),{'class_type':'Seedance2'})
    assert 'ONLY A' in result['prompt'] and 'POWER MOMENTUM DOMINANCE' in result['prompt']
    assert any(x['canonical_field'].startswith('expressionDirection') for x in result['manifest'])
    ctx['work']['content']['visualRoute']='live_action_realist';spec.source_fingerprint=fp(narrative_source(ctx))
    with pytest.raises(ValueError,match='CROSS_ROUTE'):validate_canon(spec,ctx)
    raw=dump(spec);raw['expressionDirection']['director']['shotId']='other'
    with pytest.raises(ValueError,match='SCOPE'):CinematicShotSpec.model_validate(raw)


def test_legacy_heroic_exaggeration_is_forbidden_on_live_route():
    from test_casting_reconciliation import reconciled, cg_context
    from drama_plugin.contracts.casting_discriminants import ControlledArchetypalExaggeration
    from drama_plugin.performance_casting import profile_fingerprint
    from drama_plugin.casting_discriminants import compile_visual_discriminants
    from test_visual_route import context
    p,v=reconciled()
    p.archetypal_exaggeration=ControlledArchetypalExaggeration(mode='HEROIC_STYLIZATION',definingDiscriminantIds=['outline'],anatomicalLimit='grounded articulating body',realismObservations=['support'],forbiddenDrifts=['magic'])
    v.profile_fingerprint=profile_fingerprint(p)
    c=cg_context(p,v);c.sequence.visual_route='live_action_realist';c.style=context('live_action_realist').style
    with pytest.raises(ValueError,match='FORBIDDEN_ON_LIVE'):compile_visual_discriminants(p,v,'n','FACE',route_context=c)
