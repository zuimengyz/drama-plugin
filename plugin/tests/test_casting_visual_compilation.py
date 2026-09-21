import pytest
from drama_plugin.contracts.base import dump_contract as dump
from drama_plugin.casting_visual_compiler import compile_heroic_visual_intent, DIMENSIONS, FIELD_DIMENSIONS, audit_hero_prompt
from drama_plugin.full_body_casting import full_body_design
from test_expression_routes import bundle
from test_visual_route import context
from test_full_body_casting import fixture, request_for


def intents():
    hero=dict(zip(DIMENSIONS,(
        'Tall heroic stature, broad clavicle, thick neck, deep chest, powerful waist and long limbs beneath armor.',
        'Pronounced brow ridge, focused eyes, strong jaw and dangerous commanding neutrality.',
        'Shoulder-to-waist taper and directional cloak form a bold silhouette.',
        'Three-quarter stance, planted feet and loaded torso.',
        'Explicit low-angle view with strong foreground-to-subject hierarchy; head and feet within frame.',
        'Iconic layering rhythm, waist and leg armor structures retain joint clearance.',
        'Controlled battlefield atmosphere with depth and wind-driven dust behind the readable figure.',
        'Opposed torso tension, grip, weight distribution and aligned cloth direction.',
        'Weighty functional polearm gives martial authority through its diagonal relation to the body.')))
    neutral=dict(zip(DIMENSIONS,(
        'Inspect baseline body proportions without perspective amplification.',
        'Relaxed eyes and evenly lit authored face geometry.',
        'Separate contours with cloak falling behind the body.',
        'Front-facing balanced stance with evenly distributed weight.',
        'Normal eye-level full-body inspection view.',
        'Evenly lit functional armor connections without accentuated layer rhythm.',
        'Simple neutral background, still air and visible ground.',
        'Relaxed supported grip and settled cloth without preloaded motion.',
        'Same polearm vertically displayed for proportion inspection.')))
    return {'HERO_CASTING':hero,'DESIGN_NEUTRAL':neutral}


def compile(mode='HERO_CASTING',b=None):
    style=context().style;style.visual_language='HEROIC_CINEMATIC_CG'
    return compile_heroic_visual_intent(b or bundle(),'stylized_cinematic_cg',mode,intents()[mode],dump(style))


def test_eight_visual_contrasts_preserve_exact_core_and_facts():
    h=compile();n=compile('DESIGN_NEUTRAL')
    hs={x['id']:x['text'] for x in h['segments']};ns={x['id']:x['text'] for x in n['segments']}
    assert hs['core']==ns['core'] and h['coreFingerprint']==n['coreFingerprint']
    for key in DIMENSIONS:assert hs['intent.'+key]!=ns['intent.'+key]
    assert 'Explicit low-angle' in h['prompt'] and 'Normal eye-level' not in h['prompt']
    assert 'Normal eye-level' in n['prompt'] and 'loaded torso' not in n['prompt']
    assert 'physically commanding scale' in h['prompt'] and 'CG-only expression envelope:' not in h['prompt']


@pytest.mark.parametrize('field',FIELD_DIMENSIONS)
def test_each_field_changes_actual_visual_prose(field):
    b=bundle();a=compile(b=b)
    snake=next(k for k,v in type(b.cg_expression_profile).model_fields.items() if v.alias==field)
    setattr(b.cg_expression_profile,snake,'legendary' if field=='heroicExaggeration' else 'low')
    z=compile(b=b)
    before=next(x for x in a['segments'] if x['id']=='expression.'+field)
    after=next(x for x in z['segments'] if x['id']=='expression.'+field)
    assert before['text']!=after['text'] and before['text'] in a['prompt'] and after['text'] in z['prompt']


def test_source_map_reconstructs_every_character_of_provider_prompt(tmp_path):
    w,p,v,c,s=fixture(tmp_path);s.expression_profiles=bundle(p.identity);s.casting_mode='HERO_CASTING'
    s.mode_visual_intents=intents();c.style.visual_language='HEROIC_CINEMATIC_CG'
    d=full_body_design(p,v,c,s);rows=d['visualCompilation']['segments']
    assert len({r['id'] for r in rows})==len(rows)
    assert '\n\n'.join(r['text'] for r in rows)==d['prompt']
    for r in rows:assert d['prompt'][r['start']:r['end']]==r['text'] and r['sources']
    executable={**d,'status':'EXECUTABLE_SINGLE_CANDIDATE','stopAfterFirstResult':True}
    request=request_for(executable)
    assert request['providerRequest']['input_overrides']['3']['prompt']==d['prompt']
    assert len(d['visualCompilation']['heroicFieldProjection'])==9
    s.mode_visual_intents=None
    with pytest.raises(ValueError,match='EXPLICIT_MODE'):full_body_design(p,v,c,s)


@pytest.mark.parametrize('text',['realistic actor','neutral studio','studio portrait','真人定妆照','真人演员海报'])
def test_conflicting_hero_prose_is_not_silently_concatenated(text):
    b=bundle();style=context().style;style.visual_language='HEROIC_CINEMATIC_CG';i=intents()['HERO_CASTING'];i['camera']=text
    with pytest.raises(ValueError,match='CONSERVATIVE_HERO_PROMPT_CONFLICT'):
        compile_heroic_visual_intent(b,'stylized_cinematic_cg','HERO_CASTING',i,dump(style))
    assert audit_hero_prompt([{'id':'safe','kind':'visual','text':'intimidating neutral gaze; restrained embers; normal articulating joints'}])==[]


def test_live_and_realistic_cg_cannot_enter_amplification_compiler():
    from drama_plugin.expression import casting_expression
    b=bundle();before=casting_expression(b,'live_action_realist','DESIGN_NEUTRAL')
    with pytest.raises(ValueError,match='ROUTE_FORBIDDEN'):
        compile_heroic_visual_intent(b,'live_action_realist','DESIGN_NEUTRAL',intents()['HERO_CASTING'],dump(context('live_action_realist').style))
    assert before==casting_expression(b,'live_action_realist','DESIGN_NEUTRAL')
    b.cg_expression_profile.visual_language='REALISTIC_CG';b.cg_expression_profile.heroic_exaggeration='restrained';b.cg_expression_profile.max_action_intensity='grounded'
    with pytest.raises(ValueError,match='ROUTE_FORBIDDEN'):compile(b=b)
    assert 'physically commanding scale' not in before and 'pronounced brow' not in before
