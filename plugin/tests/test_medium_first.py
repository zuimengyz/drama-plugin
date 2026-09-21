"""Offline generic structure tests; no image providers or character-specific branches."""
from copy import deepcopy
from pathlib import Path
import pytest
from drama_plugin.contracts.character_prompt import StructuredCharacterFacts
from drama_plugin.contracts.visual_medium import VisualMediumIntent
from drama_plugin.visual_medium import compile_character_art, verify_medium_compilation, medium_consistency_gate, ANCHORS

# Authored fixture differences remain facts in both media. These are synthetic,
# not historical appearance claims or a face template inferred from role names.
CASES = [
    ('heroic_commander', 'adult; long rectangular face; broad lower jaw', 'deep chest; stable hips', 'tied-back hair; short beard', 'dark iron lamellar armor'),
    ('young_officer', 'young adult; oval face; narrow lower jaw', 'lean torso; level shoulders', 'short tied hair; no beard', 'woven tunic; leather belt'),
    ('older_civilian', 'older adult; broad cheeks; rounded chin', 'slight stoop; narrow shoulders', 'thinning hair; sparse beard', 'patched linen'),
    ('female_companion', 'adult woman; long oval face; level brows', 'slender torso; grounded stance', 'coiled hair; no beard', 'dense woven outer cloth'),
    ('ordinary_cavalryman', 'adult; asymmetrical jaw; rounded nose', 'compact torso; sturdy legs', 'short hair; patchy stubble', 'worn leather; small iron plates'),
    ('background_performer', 'middle-aged adult; narrow cheeks; wide nose', 'ordinary proportions; sloping shoulders', 'receding tied hair; short beard', 'coarse cloth; repaired seams'),
]


def facts(case):
    key, face, body, hair, clothes = case
    rows = [('face','form',face), ('body','form',body),
            ('skin','skin','uneven skin tone; natural skin texture'), ('hair','groom',hair),
            ('costume','materials',clothes), ('silhouette','shape','specified shoulder-to-waist contour'),
            ('composition','rendering','one person; three-quarter orientation; simple background; inspect proportions')]
    return StructuredCharacterFacts.model_validate({'facts': [dict(id=k,domain=d,text=t,sources=['fixture:'+key+'/'+k]) for k,d,t in rows]})


@pytest.mark.parametrize('case',CASES,ids=[r[0] for r in CASES])
@pytest.mark.parametrize('mode',['DESIGN_NEUTRAL','HERO_CASTING'])
def test_generic_facts_are_independent_of_medium_and_mode(case,mode):
    original=facts(case); outputs={}
    for medium in ('CINEMATIC_CG','LIVE_ACTION_PHOTOREAL'):
        c=compile_character_art(VisualMediumIntent(visual_medium=medium,casting_mode=mode),original)
        verify_medium_compilation(c); outputs[medium]=c
        assert c['prompt'].startswith(ANCHORS[medium])
        assert c['mediumGate']['status']=='PASS'
        assert c['visualMediumCompilation']['castingMode']==mode
        assert all(r['mediumTransform'].startswith(medium) for r in c['visualMediumCompilation']['translatedFactSections'])
        assert all(atom in c['prompt'] for atom in (case[1]+'; '+case[2]).split('; '))
        for r in c['segments']: assert c['prompt'][r['start']:r['end']]==r['text']
    cg,live=outputs.values()
    assert cg['visualMediumCompilation']['inputSections']==live['visualMediumCompilation']['inputSections']
    for domain in ('skin','groom','materials','rendering'):
        a=next(r['text'] for r in cg['segments'] if r.get('domain')==domain)
        b=next(r['text'] for r in live['segments'] if r.get('domain')==domain)
        assert a!=b and len(set(a.split())^set(b.split()))>10
    assert 'natural skin texture' not in cg['prompt']
    assert 'natural skin texture' in live['prompt']


def test_old_actual_prompt_and_host_prefix_workaround_blocked():
    old=(Path(__file__).parent/'fixtures/medium-first/legacy-photographic-pull-prompt.txt').read_text()
    i=VisualMediumIntent(visual_medium='CINEMATIC_CG')
    for p in (old,ANCHORS['CINEMATIC_CG']+'\n\n'+old,ANCHORS['CINEMATIC_CG']+'\n\n'+'\n\n'.join('CG: '+r for r in old.split('\n\n'))):
        gate=medium_consistency_gate(i,p)
        assert gate['blocking'] and gate['status'] in ('FAIL','WARN')


def test_dedup_preserves_base_authority_and_unique_summary_facts():
    rows=[dict(id='summary',domain='form',derivedSummary=True,text='broad jaw；short nose',sources=['summary']),
          dict(id='face',domain='form',text='broad jaw',sources=['face']),
          dict(id='repeat',domain='form',text=' broad jaw. ',sources=['repeat'])]
    c=compile_character_art(VisualMediumIntent(visual_medium='CINEMATIC_CG'),rows)
    assert c['prompt'].count('broad jaw')==1 and c['prompt'].count('short nose')==1
    assert len(c['visualMediumCompilation']['deduplicatedFacts'])==2
    assert c['visualMediumCompilation']['deduplicatedFacts'][1]['retainedBy']=='face'
    verify_medium_compilation(c)


@pytest.mark.parametrize('field',['mediumTransform','sourceFactText','domain','sourceValueFingerprint'])
def test_fact_transform_source_map_tampering_fails(field):
    c=compile_character_art(VisualMediumIntent(visual_medium='CINEMATIC_CG'),facts(CASES[0]))
    row=next(r for r in c['segments'] if not r['id'].startswith('compiled.'))
    row[field]='forged'
    with pytest.raises(ValueError,match='MEDIUM_'): verify_medium_compilation(c)


def test_new_schema_and_receipt_roundtrip():
    f=facts(CASES[2]);assert StructuredCharacterFacts.model_validate_json(f.model_dump_json())==f
    assert 'facts' in StructuredCharacterFacts.model_json_schema()['properties']
    c=compile_character_art(VisualMediumIntent(visual_medium='CINEMATIC_CG'),f)
    for field in ('mediumAnchor','translatedFactSections','generatedMediumSections','deduplicatedFacts','negativeGuards','mediumBalanceStatus'):
        assert field in c['visualMediumCompilation']
    verify_medium_compilation(deepcopy(c))


def test_source_casting_mode_cannot_silently_override_control():
    with pytest.raises(ValueError,match='CASTING_MODE_AUTHORITY_CONFLICT'):
        compile_character_art(VisualMediumIntent(visual_medium='CINEMATIC_CG',casting_mode='HERO_CASTING'),
                              [dict(id='mode',text='DESIGN_NEUTRAL')],legacy=True)
