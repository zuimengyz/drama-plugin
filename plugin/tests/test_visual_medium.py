from pathlib import Path
import pytest
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.visual_medium import VisualMediumIntent, legacy_medium_intent
from drama_plugin.visual_medium import (compile_character_art, medium_consistency_gate,
                                        verify_medium_compilation, generated_sections)
from drama_plugin.characters.casting import compile_package_casting, executable_package_casting
from drama_plugin.contracts.creation import Work
from drama_plugin.hosts.casting_projection import full_body_seedream_projection
from character_medium_fixture import medium_case
from test_full_body_casting import request_for


def intent(medium='CINEMATIC_CG', **kwargs):
    return VisualMediumIntent(visual_medium=medium, **kwargs)


def compile_one(medium='CINEMATIC_CG', **kwargs):
    return compile_character_art(intent(medium, **kwargs), [dict(id='facts',text='An adult with natural stubble, ordinary proportions and cloth clothing.',sources=['test'])])


@pytest.mark.parametrize('medium',['CINEMATIC_CG','LIVE_ACTION_PHOTOREAL'])
@pytest.mark.parametrize('treatment',['NATURAL','HEROIC','MYTHIC'])
@pytest.mark.parametrize('realism',['NATURALISTIC','GROUNDED_STYLIZED','HEIGHTENED'])
@pytest.mark.parametrize('mode',['DESIGN_NEUTRAL','HERO_CASTING','SUPPORTING_CASTING'])
def test_contract_independent_axes_and_serialization(medium,treatment,realism,mode):
    control=intent(medium,character_treatment=treatment,realism_level=realism,casting_mode=mode)
    assert VisualMediumIntent.model_validate_json(control.model_dump_json())==control
    output=compile_one(medium,character_treatment=treatment,realism_level=realism,casting_mode=mode)
    verify_medium_compilation(output)
    assert output['mediumGate']['status']=='PASS'
    assert output['visualMediumIntent']==dump_contract(control)


@pytest.mark.parametrize('value',['ANIMATION','HERO_CASTING','heroic_cinematic_cg',None])
def test_contract_rejects_non_medium_values(value):
    with pytest.raises(ValueError):intent(value)


@pytest.mark.parametrize('text',[
    'real actor', 'live-action actor', 'studio photography', 'costume fitting photo',
    'cosplay photography', 'photographic portrait', 'shot on camera', 'real person casting photo',
    '真人演员','摄影棚定妆照片','真实演员试装摄影','真人演员，摄影棚定妆照片，真实演员试装摄影',
    'Avoid cosplay photography. Use real actor', 'Not only real actor but also studio photography',
    '避免卡通；使用真人演员', 'Do not show cartoons, but show a photographic portrait',
])
def test_cg_conflict_fails_even_in_negative_or_core_section(text):
    for kind in ('visual','negative','core'):
        with pytest.raises(ValueError,match='MEDIUM_CONSISTENCY_FAIL'):
            compile_character_art(intent(),[dict(id='facts',text=text,kind=kind)],legacy=True)


@pytest.mark.parametrize('text',[
    'Avoid the appearance of a cosplay photography.', 'Not a real actor or studio photography.',
    'Never use a photographic portrait.', 'Do not use a real actor.',
    '避免真人演员摄影棚定妆照片。', '禁止真实演员试装摄影。',
    'No real actor, live-action actor, studio photography, costume fitting photo or cosplay photography.',
])
def test_negated_conflicts_are_not_false_positives(text):
    result=compile_character_art(intent(),[dict(id='negative',text=text)],legacy=True)
    assert result['mediumGate']['status']=='PASS'


@pytest.mark.parametrize('text',['digital sculpt','CG skin shader','3D groom','feature-film digital character','数字角色'])
def test_live_reverse_conflicts(text):
    with pytest.raises(ValueError,match='MEDIUM_CONSISTENCY_FAIL'):
        compile_character_art(intent('LIVE_ACTION_PHOTOREAL'),[dict(id='facts',text=text)],legacy=True)
    assert medium_consistency_gate(intent('LIVE_ACTION_PHOTOREAL'),'Avoid '+text)['status']=='PASS'


@pytest.mark.parametrize('text',['cinematic CG, 3D character, ordinary adult, natural stubble.',
    'CG. Avoid sculpted facial planes, controlled subsurface response, controlled strand grouping, sculpted fold hierarchy, silhouette hierarchy and feature-film character presentation.'])
def test_labels_and_negated_evidence_cannot_pass_photo_explainability(text):
    result=medium_consistency_gate(intent(),text)
    assert result['status']=='WARN' and result['actorPhotoExplainability']=='WEAK_MEDIUM'
    assert result['missingEvidence']


def test_removing_one_medium_domain_invalidates_completeness():
    b=compile_one()
    for section in generated_sections(intent())[:6]:
        weak=b['prompt'].replace(section['text'],'cinematic CG')
        assert medium_consistency_gate(intent(),weak)['status']=='WARN'


@pytest.mark.parametrize('medium,text',[('CINEMATIC_CG','cinematic CG'),('LIVE_ACTION_PHOTOREAL','real actor'),('CINEMATIC_CG','3D character')])
def test_new_host_cannot_declare_even_matching_medium(medium,text):
    with pytest.raises(ValueError,match='HOST_MEDIUM_DECLARATION_FORBIDDEN'):
        compile_character_art(intent(medium),[dict(id='facts',text=text)])
    assert next(r for r in compile_character_art(intent(medium),[dict(id='facts',text=text)],legacy=True)['segments'] if r['id']=='facts')['mediumAuthority']=='LEGACY_CONFLICT_INPUT'


@pytest.mark.parametrize('tamper',['missing','source_intent','compiler','version','constraints','generated','prompt','span','intent','gate','label','route','language','fake_fingerprint'])
def test_provider_replays_medium_proof_not_just_prompt_hash(tamper):
    brief=compile_one();brief.update(status='EXECUTABLE_SINGLE_CANDIDATE',purpose='CHARACTER_FULL_BODY_CASTING',maxOutputs=1,stopAfterFirstResult=True)
    evidence=request_for(brief)['capabilityEvidence']
    if tamper=='source_intent':del brief['visualMediumCompilation']['sourceIntent']
    if tamper=='missing':del brief['visualMediumCompilation']
    if tamper=='compiler':brief['visualMediumCompilation']['compiler']='Host written Generic CG Grammar'
    if tamper=='version':brief['visualMediumCompilation']['compilerVersion']='0'
    if tamper=='constraints':brief['visualMediumCompilation']['compiledMediumConstraints']['skin']='CG'
    if tamper=='generated':brief['visualMediumCompilation']['generatedSections']=[]
    if tamper=='span':brief['segments'][0]['start']=3
    if tamper=='intent':brief['visualMediumIntent']['visualMedium']='LIVE_ACTION_PHOTOREAL'
    if tamper=='gate':brief['mediumGate']['status']='PASS_BYPASS'
    if tamper=='route':brief['visualRoute']='live_action_realist'
    if tamper=='language':brief['visualLanguage']='LIVE_ACTION_REALIST'
    if tamper=='label':brief['visualMedium']='LIVE_ACTION_PHOTOREAL'
    if tamper in ('prompt','fake_fingerprint'):
        brief['prompt']='真人演员摄影棚定妆照片'
        brief['promptFingerprint']=sha256_canonical(brief['prompt'])
        if tamper=='fake_fingerprint':brief['visualMediumCompilation']['promptFingerprint']=brief['promptFingerprint']
    with pytest.raises(ValueError,match='MEDIUM_'):
        full_body_seedream_projection(brief,evidence,seed=1)


@pytest.mark.parametrize('medium',['CINEMATIC_CG','LIVE_ACTION_PHOTOREAL'])
def test_package_end_to_end_snapshot_and_provider_projection(tmp_path,medium):
    repo,package,projection=medium_case(tmp_path,medium)
    brief=compile_package_casting(repo,projection)
    verify_medium_compilation(brief)
    snapshot=Path(__file__).parent/'snapshots'/('character-medium-'+medium.lower()+'.txt')
    assert brief['prompt']+'\n'==snapshot.read_text()
    assert brief['sourceTrace']['visualMediumCompilation']==brief['visualMediumCompilation']
    assert brief['sourceTrace']['paragraphs'][0]['sources'][0]['sourceValue']==dump_contract(package.core)
    assert all(brief['prompt'][r['start']:r['end']]==r['text'] for r in brief['segments'])
    assert '\n\n'.join(r['text'] for r in brief['segments'])==brief['prompt']
    auth=dict(authorizationId='text-only',authority='USER_EXPLICIT_SINGLE_CANDIDATE',directiveRef=projection.directive_ref,
        directiveHash=projection.directive_hash,workId='w',workRevision='r',character='actor',purpose='CHARACTER_FULL_BODY_CASTING',
        maxOutputs=1,stopAfterFirstResult=True,inputsFingerprint=brief['inputsFingerprint'],status='AUTHORIZED')
    work=Work(id='w',title='Offline',content=dict(approval={'status':'APPROVED'},revisionId='r',
        visualRoute=brief['visualRoute'],visualLanguage=brief['visualLanguage'],visualMediumIntent=brief['visualMediumIntent'],
        characterPackageRoster={'sourceRevision':'r','characters':[{'characterId':'actor','name':package.core.identity,'package':dump_contract(projection.character_package)}]},
        characterCastingAuthorizations={'text-only':auth}))
    executable=executable_package_casting(work,repo,projection,'text-only')
    req=request_for(executable)
    assert req['providerRequest']['input_overrides']['3']['prompt']==brief['prompt']
    assert req['providerRequest']['input_overrides']['3']['model.prompt_optimization']=='standard'
    assert req['providerRequest']['input_overrides']['3']['model.thinking'] is True
    work.content['visualMediumIntent']['visualMedium']='LIVE_ACTION_PHOTOREAL' if medium=='CINEMATIC_CG' else 'CINEMATIC_CG'
    with pytest.raises(ValueError,match='CURRENT_WORK_MEDIUM_INTENT'):
        executable_package_casting(work,repo,projection,'text-only')


def test_modes_have_materially_different_prompts_with_identical_facts(tmp_path):
    outputs=[]
    for medium in ('CINEMATIC_CG','LIVE_ACTION_PHOTOREAL'):
        repo,_,p=medium_case(tmp_path/medium,medium);outputs.append(compile_package_casting(repo,p))
    cg,live=outputs
    assert cg['visualMediumCompilation']['inputSections']==live['visualMediumCompilation']['inputSections']
    for domain in ('form','skin','groom','materials','shape','rendering'):
        c=cg['visualMediumCompilation']['compiledMediumConstraints'][domain]
        l=live['visualMediumCompilation']['compiledMediumConstraints'][domain]
        assert c!=l and len(set(c.split()) ^ set(l.split()))>15
    assert cg['visualMediumIntent']['castingMode']==live['visualMediumIntent']['castingMode']=='HERO_CASTING'


@pytest.mark.parametrize('legacy',[True,False])
@pytest.mark.parametrize('target',['scope_text','paragraph'])
def test_original_malicious_package_is_blocked(tmp_path,legacy,target):
    repo,_,p=medium_case(tmp_path,legacy=legacy)
    if target=='scope_text':p.scope_text='真人演员 摄影棚定妆照片 真实演员试装摄影'
    else:p.paragraphs[0].text='真人演员 摄影棚定妆照片 真实演员试装摄影'
    with pytest.raises(ValueError,match='MEDIUM_CONSISTENCY_FAIL'):compile_package_casting(repo,p)


def test_legacy_adapter_and_route_mismatch(tmp_path):
    for language,medium,treatment in [('HEROIC_CINEMATIC_CG','CINEMATIC_CG','HEROIC'),('REALISTIC_CG','CINEMATIC_CG','NATURAL'),('LIVE_ACTION_REALIST','LIVE_ACTION_PHOTOREAL','NATURAL')]:
        converted=legacy_medium_intent(language,'HERO_CASTING')
        assert (converted.visual_medium,converted.character_treatment)==(medium,treatment)
    repo,_,p=medium_case(tmp_path,legacy=True)
    b=compile_package_casting(repo,p)
    assert b['visualMediumCompilation']['sourceIntent']=='legacy:projection.route'
    assert b['mediumGate']['status']=='PASS'
    p.visual_medium_intent=intent('LIVE_ACTION_PHOTOREAL',casting_mode='HERO_CASTING')
    with pytest.raises(ValueError,match='PACKAGE_MEDIUM_ROUTE'):compile_package_casting(repo,p)


@pytest.mark.parametrize('medium',['CINEMATIC_CG','LIVE_ACTION_PHOTOREAL'])
def test_production_design_briefs_use_same_control_and_compiler(medium):
    from test_casting_projection import batch
    from drama_plugin.production_design import casting_briefs, design_handoff
    from drama_plugin.character_art import compile_casting_brief
    from drama_plugin.hosts.casting_projection import seedream_casting_projection
    old,_=batch();source=old[0]
    control=intent(medium,character_treatment='HEROIC',casting_mode='HERO_CASTING')
    briefs=casting_briefs(design_handoff(source.source_content,consumer='asset-resolution'),
        reconciliation=source.reconciliation,conditions=source.conditions,variations={'A':'Angular face','B':'Round face'},
        visual_medium_intent=control)
    for brief in briefs:
        compiled=compile_casting_brief(brief)
        assert compiled['visualMediumIntent']==dump_contract(control)
        assert compiled['mediumGate']['status']=='PASS'
        assert seedream_casting_projection(brief,seed=1)['input_overrides']['3']['prompt']==compiled['prompt']


def test_host_source_label_cannot_impersonate_compiler():
    output=compile_character_art(intent(),[dict(id='Generic CG Grammar',text='Adult with natural stubble',
        compiledBy='visual-medium-compiler',compilerVersion='1.0.0',sourceLayer='compiled_control_plane')])
    host=next(r for r in output['segments'] if r['id']=='Generic CG Grammar')
    assert 'compiledBy' not in host and 'compilerVersion' not in host
    assert host['sourceLayer']=='host_authored'
    assert host not in output['visualMediumCompilation']['generatedSections']
    with pytest.raises(ValueError,match='RESERVED_PROMPT_SECTION'):
        compile_character_art(intent(),[dict(id='compiled.medium.form',text='CG')])


@pytest.mark.parametrize('medium,text',[
    ('CINEMATIC_CG','No CG.'),('CINEMATIC_CG','避免数字角色'),('CINEMATIC_CG','Do not use a digital character.'),
    ('LIVE_ACTION_PHOTOREAL','No live-action.'),('LIVE_ACTION_PHOTOREAL','不要真人摄影'),('LIVE_ACTION_PHOTOREAL','Avoid photographed skin.'),
])
def test_negation_cannot_override_selected_medium(medium,text):
    with pytest.raises(ValueError,match='MEDIUM_CONSISTENCY_FAIL'):
        compile_character_art(intent(medium),[dict(id='host',text=text)],legacy=True)
