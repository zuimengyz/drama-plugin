"""Diverse synthetic cases: never provider calls or production defaults."""
import json
from pathlib import Path
import pytest
from drama_plugin.contracts.base import dump_contract as dump,sha256_canonical as fp
from drama_plugin.contracts.expression import CastingArchetypeProfile, ApprovedVisualTargetRange
from drama_plugin.casting_visual_compiler import compile_heroic_visual_intent,DIMENSIONS
from drama_plugin.full_body_casting import full_body_design,executable_full_body
from test_expression_routes import bundle
from test_visual_route import context
from test_full_body_casting import fixture
P=Path(__file__).parents[1]

def profile(identity='S',archetype='scholar_official'):
    b=bundle(identity);b.character_core_profile.archetype=archetype
    b.character_core_profile.historical_position='civil office'
    b.character_core_profile.personality_core=('inquisitive',)
    digest=fp(b.character_core_profile)
    b.cg_expression_profile.core_fingerprint=digest;b.live_action_expression_profile.core_fingerprint=digest
    return b

def intent(mode):
    return dict(zip(DIMENSIONS,(
      'Compact elderly frame with designed angular contrast' if mode=='HERO_CASTING' else 'Inspect baseline compact frame',
      'Alert asymmetrical expressive eyes' if mode=='HERO_CASTING' else 'Relaxed evenly lit eyes',
      'Strong bent contour and open sleeve spaces' if mode=='HERO_CASTING' else 'Separated inspection contours',
      'Decisive seated lean' if mode=='HERO_CASTING' else 'Balanced seated posture',
      'Elevated oblique full-figure perspective' if mode=='HERO_CASTING' else 'Eye-level inspection view',
      'Woven robe and soft cap',
      'Window shadows establish charged interior depth' if mode=='HERO_CASTING' else 'Even blank background',
      'Weight supported by the stool; gathered sleeve tension' if mode=='HERO_CASTING' else 'Settled sleeves',
      'No weapon; one closed manuscript')))

def compile(mode='HERO_CASTING', b=None,target=None):
    b=b or profile();style=context().style;style.visual_language='HEROIC_CINEMATIC_CG'
    arch=CastingArchetypeProfile.model_validate(json.loads((P/'config/casting-archetypes.json').read_text())[b.character_core_profile.archetype])
    return compile_heroic_visual_intent(b,'stylized_cinematic_cg',mode,intent(mode),dump(style),archetype=arch,target_range=target)

def target(character='S'):
    return ApprovedVisualTargetRange(range_id='test_range',character=character,visual_route='stylized_cinematic_cg',visual_language='HEROIC_CINEMATIC_CG',reference_media_id='media_reference',reference_content_hash='a'*64,approval_ref='approval',approval_hash='b'*64,positive_traits=['Designed contrast within authored bounds'],negative_traits=['No idol photo or magic'])

def test_generic_capability_does_not_add_a_warlord_to_a_scholar():
    d=compile();text=d['prompt']
    for forbidden in ('broad clavicle','thick neck','deep chest','powerful waist','battlefield','polearm','red cloak','项羽','young commander'):
        assert forbidden not in text
    assert 'Compact elderly frame' in text and 'Elevated oblique' in text
    assert 'copied recognizable game-IP' in text and 'Forbidden: magic' in text

def test_generic_skill_and_archetypes_have_no_specific_instance_literals():
    for root in ('skills','src','config','docs'):
        for path in (P/root).rglob('*'):
            if path.suffix not in ('.py','.md','.json','.yaml','.yml'):continue
            text=path.read_text()
            assert not any(x in text for x in ('项羽','西楚霸王','垓下','乌江','楚军','broad clavicle','thick neck','deep chest','青年成年统帅')),str(path)
    lib=json.loads((P/'config/casting-archetypes.json').read_text())
    assert len(lib)>=4
    assert not any(x in json.dumps(lib).lower() for x in ('red cloak','black armor','spear','jaw','xiang'))

def test_all_paragraphs_trace_layers_and_same_archetype_modes_change():
    h=compile(target=target());n=compile('DESIGN_NEUTRAL',target=target())
    assert h['coreFingerprint']==n['coreFingerprint'] and h['archetypeFingerprint']==n['archetypeFingerprint']
    rows={r['id']:r for r in h['segments']};other={r['id']:r for r in n['segments']}
    for key in ('bodyProportion','silhouette','camera','environmentEnergy','facialIntensity'):
        assert rows['intent.'+key]['text']!=other['intent.'+key]['text']
    for r in rows.values():
        assert h['prompt'][r['start']:r['end']]==r['text'] and r['sources'] and r['sourceLayers']
    assert rows['archetype']['sourceLayer']=='archetype'
    assert rows['target.positive']['sourceLayer']=='approved_target_range'
    assert rows['intent.camera']['sourceLayer']=='instance'
    assert rows['expression.martialAura']['sourceLayers']==['generic_capability','instance']
    assert 'target.positive' not in other

@pytest.mark.parametrize('change',[{'identityAdoption':True},{'referenceUse':'EXACT_COPY'},{'visualRoute':'live_action_realist'},{'visualLanguage':'REALISTIC_CG'}])
def test_range_rejects_adoption_copy_and_other_routes(change):
    with pytest.raises(ValueError):ApprovedVisualTargetRange.model_validate({**dump(target()),**change})

def test_range_cannot_cross_character():
    with pytest.raises(ValueError,match='INSTANCE_OR_ROUTE'):compile(target=target('OTHER'))

def test_exact_work_range_and_archetype_required(tmp_path):
    w,p,v,c,s=fixture(tmp_path);s.expression_profiles=profile(p.identity);s.casting_mode='HERO_CASTING'
    s.mode_visual_intents={m:intent(m) for m in ('HERO_CASTING','DESIGN_NEUTRAL')}
    s.approved_target_range=target(p.identity)
    s.archetype_profile=CastingArchetypeProfile.model_validate(json.loads((P/'config/casting-archetypes.json').read_text())['scholar_official'])
    c.style.visual_language='HEROIC_CINEMATIC_CG';d=full_body_design(p,v,c,s)
    w.content['visualRouteBinding']['styleFingerprint']=fp(c.style)
    w.content['characterExpressionProfiles']={p.identity:dump(s.expression_profiles)}
    w.content['characterCastingAuthorizations']['task']['inputsFingerprint']=d['inputsFingerprint']
    with pytest.raises(ValueError,match='APPROVED_RANGE'):executable_full_body(w,p,v,c,s,'task')
    w.content['approvedVisualTargetRanges']={'test_range':dump(s.approved_target_range)}
    w.content['castingArchetypeProfiles']={'scholar_official':dump(s.archetype_profile)}
    assert executable_full_body(w,p,v,c,s,'task')['referenceMediaIds']==[]
    w.content['approvedVisualTargetRanges']['test_range']['positiveTraits']=['changed']
    with pytest.raises(ValueError,match='APPROVED_RANGE'):executable_full_body(w,p,v,c,s,'task')


def test_live_adapter_respects_an_older_nonmilitary_instance():
    from test_casting_projection import batch
    from drama_plugin.hosts.casting_projection import seedream_casting_projection
    b,_=batch();one=b[0]
    one.reconciliation.apparent_age_min=65;one.reconciliation.apparent_age_max=75
    prompt=seedream_casting_projection(one,seed=1)['input_overrides']['3']['prompt']
    assert '65–75' in prompt and '青年成年统帅' not in prompt and '不是老将' not in prompt
    assert '无甲、无护肩、无兵器' not in prompt

def test_target_is_not_silently_ignored_without_heroic_compiler(tmp_path):
    _,p,v,c,s=fixture(tmp_path);s.approved_target_range=target(p.identity)
    with pytest.raises(ValueError,match='EXPLICIT_HEROIC_COMPILATION'):full_body_design(p,v,c,s)

@pytest.mark.parametrize('archetype',['ordinary_soldier','disciplined_commander','tragic_hero_warlord'])
def test_other_archetypes_do_not_supply_specific_body_equipment(archetype):
    d=compile(b=profile('DifferentPerson',archetype))
    assert 'Compact elderly frame' in d['prompt'] and 'No weapon' in d['prompt']
    assert not any(x in d['prompt'] for x in ('broad clavicle','thick neck','red cloak','long spear','项羽'))
