"""No provider/LLM calls: style axes, compact source mapping and request replay."""
from copy import deepcopy
from pathlib import Path
import pytest
from drama_plugin.contracts.base import dump_contract,sha256_canonical
from drama_plugin.contracts.visual_medium import VisualMediumIntent,legacy_medium_intent,revise_render_intent
from drama_plugin.visual_medium import compile_character_art,verify_medium_compilation,medium_consistency_gate
from drama_plugin.render_stylization import render_stylization_gate,compile_render_stylization,compile_presentation
from test_medium_first import CASES,facts

STYLES=['PHOTOREAL_DIGITAL_HUMAN','VISIBLE_FILMIC_CG','HEIGHTENED_FILMIC_CG']
PRESENTATIONS=['LOOKDEV_NEUTRAL','HERO_PRESENTATION','PERFORMANCE_PRESENTATION']

def control(style='VISIBLE_FILMIC_CG',presentation='LOOKDEV_NEUTRAL',mode='DESIGN_NEUTRAL',**kw):
    return VisualMediumIntent(visual_medium='CINEMATIC_CG',render_stylization=style,render_stylization_source='fixture:CharacterArt/rev2',presentation_mode=presentation,casting_mode=mode,**kw)

@pytest.mark.parametrize('style',STYLES)
@pytest.mark.parametrize('presentation',PRESENTATIONS)
@pytest.mark.parametrize('mode',['HERO_CASTING','SUPPORTING_CASTING','DESIGN_NEUTRAL'])
@pytest.mark.parametrize('treatment',['NATURAL','HEROIC','MYTHIC'])
def test_independent_axes_and_roundtrip(style,presentation,mode,treatment):
    i=control(style,presentation,mode,character_treatment=treatment)
    assert VisualMediumIntent.model_validate_json(i.model_dump_json())==i
    c=compile_character_art(i,facts(CASES[0]));verify_medium_compilation(c)
    assert c['mediumGate']['status']=='PASS'
    assert c['renderStylizationGate']['renderStylizationStatus']=='PASS'
    assert c['visualMediumIntent']==dump_contract(i)

@pytest.mark.parametrize('case',CASES,ids=[c[0] for c in CASES])
def test_same_facts_four_routes_preserve_individuality(case):
    output=[]
    for i in [VisualMediumIntent(visual_medium='LIVE_ACTION_PHOTOREAL',presentation_mode='LOOKDEV_NEUTRAL'),*[control(s) for s in STYLES]]:
        c=compile_character_art(i,facts(case));verify_medium_compilation(c);output.append(c)
        assert all(atom in c['prompt'] for atom in (case[1]+'; '+case[2]).split('; '))
        assert 'Authored digital sculptural anatomy:' not in c['prompt']
        for row in c['visualMediumCompilation']['translatedFactSections']:
            assert c['prompt'][row['start']:row['end']]==row['text']
    assert len({c['prompt'] for c in output})==4
    assert all(c['visualMediumCompilation']['inputSections']==output[0]['visualMediumCompilation']['inputSections'] for c in output)
    b,c=output[1:3]
    for domain in ['form','skin','groom','materials','shape','rendering']:
        assert b['visualMediumCompilation']['compiledMediumConstraints'][domain]!=c['visualMediumCompilation']['compiledMediumConstraints'][domain]


def test_legacy_is_not_silently_visible_and_owner_revision_is_explicit():
    old=legacy_medium_intent('HEROIC_CINEMATIC_CG','HERO_CASTING')
    c=compile_character_art(old,facts(CASES[0]))
    assert old.render_stylization is None
    assert c['renderStylizationGate']['renderStylizationStatus']=='LEGACY_UNSPECIFIED'
    assert c['visualMediumCompilation']['migrationStatus']=='LEGACY_GENERIC_CG_UNSPECIFIED'
    with pytest.raises(ValueError,match='EXPLICIT_RENDER'):compile_render_stylization(old)
    new=revise_render_intent(old,render_stylization='VISIBLE_FILMIC_CG',source='current-project:CharacterArt/rev2',presentation_mode='LOOKDEV_NEUTRAL')
    assert new.casting_mode=='HERO_CASTING' and old.render_stylization is None
    assert new.render_stylization_source=='current-project:CharacterArt/rev2'

@pytest.mark.parametrize('patch',[{'visualMedium':'LIVE_ACTION_PHOTOREAL'},{'renderStylizationSource':None},{'presentationMode':None},{'renderStylization':'ANIME'},{'renderStylization':None}])
def test_invalid_contract_combinations(patch):
    raw=dump_contract(control());raw.update(patch)
    with pytest.raises(ValueError):VisualMediumIntent.model_validate(raw)


def test_real_second_failure_is_cg_but_not_visible_style():
    p=(Path(__file__).parent/'fixtures/medium-first/photoreal-digital-human-pull-fixture.txt').read_text()
    i=control();m=medium_consistency_gate(i,p)
    assert m['status']=='PASS'
    for text in [p,'VISIBLE_FILMIC_CG\n'+p]:
        g=render_stylization_gate(i,text,medium_status=m['status'])
        assert g['renderStylizationStatus']=='FAIL'
        assert g['detectedPull']=='PHOTOREAL_DIGITAL_HUMAN' and g['missingDomains']

@pytest.mark.parametrize('domain',['form','skin','groom','materials','shape','rendering'])
def test_removing_domain_evidence_blocks_style(domain):
    i=control();c=compile_character_art(i,facts(CASES[0]))
    row=next(r for r in c['segments'] if r['id']=='compiled.medium.'+domain)
    weak=c['prompt'].replace(row['text'],'VISIBLE_FILMIC_CG')
    assert render_stylization_gate(i,weak)['blocking']

@pytest.mark.parametrize('pull',['fine pores','every individual hair strand rendered as photographic capture','wardrobe-test presentation','incidental physical noise priority','hyperreal skin capture','photographic material noise'])
def test_photoreal_pull_negation_and_reassertion(pull):
    i=control();c=compile_character_art(i,facts(CASES[0]))
    assert render_stylization_gate(i,c['prompt']+'\n'+pull)['blocking']
    assert not render_stylization_gate(i,c['prompt']+'\nAvoid '+pull)['blocking']
    assert render_stylization_gate(i,c['prompt']+'\nAvoid cartoons. Use '+pull)['blocking']


def test_photo_target_rejects_visible_recipe_and_negated_evidence():
    c=compile_character_art(control(),facts(CASES[0]))
    assert render_stylization_gate(control('PHOTOREAL_DIGITAL_HUMAN'),c['prompt'])['blocking']
    assert render_stylization_gate(control(),'VISIBLE_FILMIC_CG. Avoid '+'; '.join(compile_render_stylization(control()).values()))['blocking']

@pytest.mark.parametrize('field',['renderStylization','renderStylizationSource','renderStylizationVersion','renderStylizationEvidence','presentationMode'])
def test_receipt_tamper_cannot_reach_provider(field):
    from test_full_body_casting import request_for
    from drama_plugin.hosts.casting_projection import full_body_seedream_projection
    c=compile_character_art(control(),facts(CASES[0]));c.update(status='EXECUTABLE_SINGLE_CANDIDATE',purpose='CHARACTER_FULL_BODY_CASTING',maxOutputs=1,stopAfterFirstResult=True)
    evidence=request_for(c)['capabilityEvidence']
    c['visualMediumCompilation'][field]='forged'
    with pytest.raises(ValueError,match='MEDIUM_'):full_body_seedream_projection(c,evidence,seed=1)


def test_package_casting_and_host_provider_projection(tmp_path):
    from character_medium_fixture import medium_case
    from drama_plugin.characters.casting import compile_package_casting
    from test_full_body_casting import request_for
    repo,_,p=medium_case(tmp_path);p.visual_medium_intent=control(mode='HERO_CASTING')
    c=compile_package_casting(repo,p);verify_medium_compilation(c)
    c.update(status='EXECUTABLE_SINGLE_CANDIDATE',maxOutputs=1,stopAfterFirstResult=True)
    req=request_for(c)
    assert req['providerRequest']['input_overrides']['3']['prompt']==c['prompt']
    assert req['providerRequest']['input_overrides']['3']['model.prompt_optimization']=='standard'
    assert req['providerRequest']['input_overrides']['3']['model.thinking'] is True


def test_presentation_changes_no_facts_casting_or_other_domains():
    cs=[compile_character_art(control(presentation=p,mode='HERO_CASTING'),facts(CASES[0])) for p in PRESENTATIONS]
    assert len({c['prompt'] for c in cs})==3
    assert all(c['visualMediumIntent']['castingMode']=='HERO_CASTING' for c in cs)
    assert cs[0]['visualMediumCompilation']['inputSections']==cs[1]['visualMediumCompilation']['inputSections']==cs[2]['visualMediumCompilation']['inputSections']
    for key in ['form','body','skin','groom','materials','shape']:
        assert len({next(r['text'] for r in c['segments'] if r['id']=='compiled.medium.'+key) for c in cs})==1


def test_realism_does_not_select_visibility():
    for realism in ['NATURALISTIC','GROUNDED_STYLIZED','HEIGHTENED']:
        for style in STYLES:
            c=compile_character_art(control(style,realism_level=realism),facts(CASES[0]))
            assert c['renderStylizationGate']['target']==style
            assert c['renderStylizationGate']['renderStylizationStatus']=='PASS'


@pytest.mark.parametrize('style',STYLES)
def test_deterministic_style_snapshot(style):
    c=compile_character_art(control(style),facts(CASES[0]))
    assert c['prompt']+'\n'==(Path(__file__).parent/'snapshots'/('character-style-'+style.lower()+'.txt')).read_text()
    assert render_stylization_gate(control(style),c['prompt']+'\nNo '+style)['blocking']


@pytest.mark.parametrize('style',STYLES)
def test_production_design_brief_uses_same_style_compiler(style):
    from test_casting_projection import batch
    from drama_plugin.production_design import casting_briefs,design_handoff
    from drama_plugin.character_art import compile_casting_brief
    from drama_plugin.hosts.casting_projection import seedream_casting_projection
    old,_=batch();source=old[0]
    for brief in casting_briefs(design_handoff(source.source_content,consumer='asset-resolution'),
            reconciliation=source.reconciliation,conditions=source.conditions,
            variations={'A':'Angular face','B':'Round face'},visual_medium_intent=control(style)):
        c=compile_casting_brief(brief);verify_medium_compilation(c)
        assert c['renderStylizationGate']['renderStylizationStatus']=='PASS'
        assert seedream_casting_projection(brief,seed=1)['input_overrides']['3']['prompt']==c['prompt']
