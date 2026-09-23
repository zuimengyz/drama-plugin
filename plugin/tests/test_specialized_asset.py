from datetime import datetime, timezone
from copy import deepcopy
import pytest
from pydantic import ValidationError
from drama_plugin.config import load_config
from drama_plugin.exceptions import ConfigurationError
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.specialized_asset import *
from drama_plugin.contracts.professional import CreativeBible, CreativeRecord
from drama_plugin.contracts.creation import Work
from drama_plugin.hosts.specialized_asset import SpecializedAssetHost, require_production_visual_authority
from drama_plugin.specialized_asset import provider_projection, FORWARDED_DEPARTMENTS
from drama_plugin.professional import approval_subject, registry, dependency_order, bible_pin


def fixture(tmp_path, medium='live_action', source='HISTORICAL', work_id='work'):
    config=load_config(environment={'DRAMA_PLUGIN_VISUAL_MEDIUM':medium,'DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT':str(tmp_path)})
    host=SpecializedAssetHost(config); runtime=host.bind_movie(work_id); current={}
    style=GlobalVisualStyle(work_id=work_id,runtime_ref=runtime,realism='NATURALISTIC',render_stylization='VISIBLE_FILMIC_CG' if medium=='cg' else None)
    style_ref=host.save_style(style);current[style_ref.key]=style_ref.fingerprint
    now=datetime.now(timezone.utc)
    bases={}
    base_source=host.store.put('source:baseline', {'synthetic':True})
    current[base_source.key]=base_source.fingerprint
    for owner in dependency_order():
        base=CreativeBible(id='baseline-'+owner,type=registry()[owner].output_contract,work_ref=work_id,
            source_refs=(base_source,),created_by_capability=owner,status='NOT_REQUIRED',
            not_required_reason='Unused offline fixture dependency',
            depends_on=tuple(bible_pin(bases[key]) for key in registry()[owner].depends_on),created_at=now,updated_at=now)
        base_ref=bible_pin(base);host.store.put(base_ref.key,dump_contract(base));bases[owner]=base
        current[base_ref.key]=base_ref.fingerprint
    def original(owner,values):
        source_ref=host.store.put('source:'+source,{'synthetic':True,'sourceType':source})
        bible=CreativeBible(id=owner,type=registry()[owner].output_contract,work_ref=work_id,source_refs=(source_ref,),depends_on=tuple(bible_pin(bases[key]) for key in registry()[owner].depends_on),created_by_capability=owner,status='READY_FOR_REVIEW',
            content=(CreativeRecord(id='r',scope_refs=(work_id,),values=values,provenance='NEW_PROFESSIONAL_ELABORATION',source_refs=(source_ref,)),),created_at=now,updated_at=now)
        approval=host.store.put('approval:'+owner,{'kind':'PROFESSIONAL_CREATIVE_APPROVAL','subjectId':bible.id,'workRef':work_id,'decision':'APPROVE','subjectFingerprint':approval_subject(bible),'approvedBy':['reviewer']})
        bible=CreativeBible.model_validate({**dump_contract(bible),'status':'APPROVED','approvedBy':['reviewer'],'approvalRefs':[dump_contract(approval)]})
        ref=host.store.put('bible:'+owner,dump_contract(bible))
        current.update({ref.key:ref.fingerprint,approval.key:approval.fingerprint,source_ref.key:source_ref.fingerprint})
        return DramaturgyInput(bible_ref=ref,record_id='r',constraint_fields=tuple(values))
    character=original('character-dramaturgy',{'character_ref':'c','arc_stage':'opening','behavior_pattern':'careful movement','social_position':'ordinary worker'})
    scene=original('scene-development',{'scene_ref':'s','scene_purpose':'waiting for a visitor'})
    director=original('director',{'restraint_principles':'do not reveal later anxiety'})
    world=original('adaptation-boundary',{'source_basis':'Synthetic present-day workshop'})
    def decision(text,dramaturgy):return AssetDecision(text=text,reason='Observable reading under approved constraints',source_refs=(dramaturgy.bible_ref,))
    common=dict(director=director,world=world)
    assets=(CharacterAsset(id='char',character_id='c',arc_stage='opening',dramaturgy=character,decisions={'body':decision('Ordinary narrow adult shoulders.',character),'face':decision('A lined asymmetric face.',character)},**common),
        CostumeAsset(id='coat',character_id='c',arc_stage='opening',dramaturgy=character,decisions={'material':decision('Worn plain cotton with repaired cuffs.',character)},**common),
        SceneAsset(id='room',scene_id='s',dramaturgy=scene,decisions={'architecture':decision('A modest stone courtyard with a low timber door.',scene)},**common))
    bible=SpecializedAssetBible(work_id=work_id,runtime_ref=runtime,style_ref=style_ref,assets=assets)
    review=host.store.put('asset-review:'+work_id,{'kind':'SPECIALIZED_ASSET_REVIEW','decision':'APPROVE',
        'workId':work_id,'reviewer':'offline-fixture-review',
        'checkedBoundaries':['DRAMATURGY','DIRECTOR_INTENT','SOURCE_WORLD','GLOBAL_STYLE'],
        'subjectFingerprint':sha256_canonical(dump_contract(bible,exclude={'approval_ref'}))})
    current[review.key]=review.fingerprint
    bible=bible.model_copy(update={'approval_ref':review})
    ref=host.submit(bible,current=current);current[ref.key]=ref.fingerprint
    return host,bible,ref,current


@pytest.mark.parametrize('medium,expected',[('live_action','LIVE_ACTION'),('cg','CG')])
def test_env_pin_and_new_movie(tmp_path,medium,expected):
    host,_,_,_=fixture(tmp_path,medium)
    assert host.store.read_ref(host.movie('work'))['medium']==expected
    other=SpecializedAssetHost(load_config(environment={'DRAMA_PLUGIN_VISUAL_MEDIUM':'cg' if medium=='live_action' else 'live_action','DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT':str(tmp_path)}))
    assert other.bind_movie('work')==host.movie('work')
    assert other.store.read_ref(other.bind_movie('next'))['medium']!=expected


@pytest.mark.parametrize('invalid',['','CG','realistic','cinematic','3d','photo','game','anime'])
def test_invalid_runtime(invalid):
    with pytest.raises(ConfigurationError):load_config(environment={'DRAMA_PLUGIN_VISUAL_MEDIUM':invalid})


def test_env_overrides_config_and_missing_fails(tmp_path):
    path=tmp_path/'config.yaml';path.write_text('visual_medium: cg\n')
    assert load_config(path,environment={'DRAMA_PLUGIN_VISUAL_MEDIUM':'live_action'}).visual_medium=='live_action'
    host=SpecializedAssetHost(load_config(environment={'DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT':str(tmp_path)}))
    with pytest.raises(ValueError,match='CONFIGURATION_REQUIRED'):host.bind_movie('missing')


@pytest.mark.parametrize('source',['HISTORICAL','LITERARY'])
@pytest.mark.parametrize('medium',['live_action','cg'])
def test_actual_compiler_provider_all_combinations(tmp_path,medium,source):
    host,bible,ref,current=fixture(tmp_path,medium,source)
    for asset in bible.assets:
        result=host.compile(ref,asset.id,current=current,casting_mode='HERO_CASTING');receipt=result['compilation'];projection=result['projection']
        assert projection['prompt'] != receipt['prompt'] and projection['promptEnhancement']=='DISABLED'
        assert 'do not reveal later anxiety' not in projection['prompt']
        assert projection['scope_review']['gate'] == 'VISUAL_PROVIDER_SCOPE_REVIEW'
        assert {'DRAMATURGY','GLOBAL_STYLE','ASSET_DESIGN','DIRECTOR_INTENT','RUNTIME_MEDIUM'} <= {r['layer'] for r in receipt['sourceMap']}
        if medium=='live_action':
            for token in ('VISIBLE_FILMIC_CG','LOOKDEV_NEUTRAL','GROUNDED_STYLIZED','digital sculpture','authored digital form','CG groom'):assert token not in projection['prompt']
        elif asset.kind=='CHARACTER':assert receipt['legacyMediumCompilation']['visualMediumIntent']['visualMedium']=='CINEMATIC_CG'
    normal=host.compile(ref,'char',current=current)['compilation'];hero=host.compile(ref,'char',current=current,casting_mode='HERO_CASTING')['compilation']
    assert normal['assetBible']==hero['assetBible']
    assert [r for r in normal['sourceMap'] if r['layer']=='ASSET_DESIGN']==[r for r in hero['sourceMap'] if r['layer']=='ASSET_DESIGN']
    for design in bible.assets[0].decisions.values():assert design.text in hero['prompt']


@pytest.mark.parametrize('index',[0,1,2])
def test_missing_or_stale_dramaturgy_blocked(tmp_path,index):
    host,bible,_,current=fixture(tmp_path);current.pop(bible.assets[index].dramaturgy.bible_ref.key)
    with pytest.raises(ValueError,match='UPSTREAM_INFORMATION_REQUIRED'):host.submit(bible,current=current)


@pytest.mark.parametrize('index',[0,1])
def test_character_arc_and_social_dependency(tmp_path,index):
    host,bible,_,current=fixture(tmp_path);data=dump_contract(bible);data['approvalRef']=None;data['assets'][index]['arcStage']='ending'
    with pytest.raises(ValueError,match='STAGE_MISMATCH'):host.submit(SpecializedAssetBible.model_validate(data),current=current)
    data=dump_contract(bible);data['approvalRef']=None;data['assets'][index]['dramaturgy']['constraintFields']=['social_position']
    with pytest.raises(ValueError,match='UPSTREAM_INFORMATION_REQUIRED'):host.submit(SpecializedAssetBible.model_validate(data),current=current)


@pytest.mark.parametrize('field',['personality','belief','desire','fear','character_arc','relationship_arc','dramatic_purpose'])
def test_asset_cannot_mutate_narrative(tmp_path,field):
    _,bible,_,_=fixture(tmp_path);data=dump_contract(bible);data['approvalRef']=None;data['assets'][0]['decisions'][field]=data['assets'][0]['decisions']['body']
    with pytest.raises(ValidationError):SpecializedAssetBible.model_validate(data)


@pytest.mark.parametrize('field',['face','body','costume','furniture','architecture'])
def test_global_style_no_specific_design(tmp_path,field):
    host,bible,_,_=fixture(tmp_path);style=host.store.read_ref(bible.style_ref);style[field]='invented'
    with pytest.raises(ValidationError):GlobalVisualStyle.model_validate(style)


@pytest.mark.parametrize('index',[0,1,2])
def test_assets_cannot_override_medium(tmp_path,index):
    host,bible,_,current=fixture(tmp_path);data=dump_contract(bible);data['approvalRef']=None;data['assets'][index]['visualMedium']='CG'
    with pytest.raises(ValidationError):SpecializedAssetBible.model_validate(data)
    data=dump_contract(bible);data['approvalRef']=None;next(iter(data['assets'][index]['decisions'].values()))['text']='Use VISIBLE_FILMIC_CG digital form.'
    with pytest.raises(ValueError,match='CANNOT_OVERRIDE'):host.submit(SpecializedAssetBible.model_validate(data),current=current)


def test_provider_tampering_and_work_override(tmp_path,monkeypatch):
    host,bible,ref,current=fixture(tmp_path);result=host.compile(ref,'char',current=current);originals,resolved=host._inputs(bible,current)
    changed=deepcopy(result['compilation']);changed['prompt']+=' a golden crown'
    with pytest.raises(ValueError,match='COMPILATION_CHANGED'):provider_projection(changed,originals,resolved)
    monkeypatch.setenv('DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT',str(tmp_path))
    work=Work(id='work',title='synthetic',content={'movieVisualMediumRef':dump_contract(bible.runtime_ref),'specializedAssetCompilationRefs':[result['compilationRef']],'visualSourceCurrent':current})
    assert require_production_visual_authority(work)[0]['medium']=='LIVE_ACTION'
    work.content['movieVisualMediumRef']=dump_contract(host.bind_movie('another'))
    with pytest.raises(ValueError,match='MISMATCH'):require_production_visual_authority(work)


def test_old_writers_forward_and_reject(tmp_path):
    from drama_plugin.hosts.professional import ProfessionalDepartmentHost
    host,bible,_,_=fixture(tmp_path)
    for department in FORWARDED_DEPARTMENTS:
        definition=registry()[department];assert definition.authority_owner=='specialized-asset-design';assert definition.can_create==definition.can_modify==()
    original=CreativeBible.model_validate(host.store.read_ref(bible.assets[0].dramaturgy.bible_ref));old=original.model_copy(update={'created_by_capability':'character-art'})
    with pytest.raises(ValueError,match='DEPRECATED_DESIGN_WRITER'):ProfessionalDepartmentHost(tmp_path).submit('character-art',old,current={})


def test_department_view_is_real_readonly_consumer(tmp_path):
    from drama_plugin.hosts.professional import ProfessionalDepartmentHost
    host,bible,ref,current=fixture(tmp_path)
    current[bible.runtime_ref.key]=bible.runtime_ref.fingerprint
    professional=ProfessionalDepartmentHost(tmp_path)
    for department,asset_id in [('character-art','char'),('costume-design','coat')]:
        records=host.department_records(ref,(asset_id,),department,current=current)
        base_key='bible:baseline-'+department
        from drama_plugin.contracts.source_pin import SourcePin
        base=CreativeBible.model_validate(host.store.read_ref(SourcePin(key=base_key,kind='DESIGN',fingerprint=current[base_key])))
        view=CreativeBible.model_validate({**dump_contract(base),'id':'projected-'+department,
            'status':'READY_FOR_REVIEW','notRequiredReason':None,'content':[dump_contract(r) for r in records]})
        assert professional.submit(department,view,current=current)['validationStatus']=='PASS'
        changed=dump_contract(view);next(iter(changed['content']))['values']['face_structure']='invented face'
        with pytest.raises(ValueError,match='SPECIALIZED_ASSET_VIEW_CHANGED|AUTHORITY_VIOLATION'):
            professional.submit(department,CreativeBible.model_validate(changed),current=current)


def test_production_gate_binds_actual_prompt_and_medium(tmp_path,monkeypatch):
    from drama_plugin.hosts.specialized_asset import validate_visual_submission, bind_video_request
    from test_official_video_providers import request
    host,bible,ref,current=fixture(tmp_path,'cg');compiled=host.compile(ref,'room',current=current)
    monkeypatch.setenv('DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT',str(tmp_path))
    work=Work(id='work',title='Synthetic',content={'movieVisualMediumRef':dump_contract(bible.runtime_ref),
        'specializedAssetCompilationRefs':[compiled['compilationRef']],'visualSourceCurrent':current})
    r=request();r.continuity.work_id=work.id
    with pytest.raises(ValueError,match='DOES_NOT_CONSUME'):validate_visual_submission(work,dump_contract(r))
    r=bind_video_request(work,r);validate_visual_submission(work,dump_contract(r))
    modified=dump_contract(r);modified['continuity']['style']['visualRoute']='live_action_realist'
    with pytest.raises(ValueError,match='OVERRIDE_FORBIDDEN'):validate_visual_submission(work,modified)
    modified=dump_contract(r);modified['promptEnhancement']='standard'
    with pytest.raises(ValueError,match='ENHANCEMENT_NOT_AUTHORIZED'):validate_visual_submission(work,modified)


def test_approved_bible_cannot_lie_about_owner_fields(tmp_path):
    host,bible,ref,current=fixture(tmp_path)
    # A mutated approval cannot be accepted just because its status says APPROVED.
    link=bible.assets[0].director
    value=host.store.read_ref(link.bible_ref);value['content'][0]['values']['restraint_principles']='different'
    new_ref=host.store.put(link.bible_ref.key,value);current[new_ref.key]=new_ref.fingerprint
    data=dump_contract(bible);data['approvalRef']=None
    for asset in data['assets']:asset['director']['bibleRef']=dump_contract(new_ref)
    with pytest.raises(ValueError,match='APPROVAL_RECEIPT'):
        host.submit(SpecializedAssetBible.model_validate(data),current=current)


def test_asset_review_binds_design_before_production(tmp_path,monkeypatch):
    host,bible,ref,current=fixture(tmp_path)
    changed=dump_contract(bible);changed['assets'][0]['decisions']['body']['text']='Another body'
    with pytest.raises(ValueError,match='APPROVAL_NOT_BOUND'):
        host.submit(SpecializedAssetBible.model_validate(changed),current=current)
    draft=bible.model_copy(update={'approval_ref':None})
    ref=host.submit(draft,current=current);current[ref.key]=ref.fingerprint
    result=host.compile(ref,'char',current=current)
    monkeypatch.setenv('DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT',str(tmp_path))
    work=Work(id='work',title='Synthetic',content={'movieVisualMediumRef':dump_contract(bible.runtime_ref),
        'specializedAssetCompilationRefs':[result['compilationRef']],'visualSourceCurrent':current})
    with pytest.raises(ValueError,match='REVIEW_REQUIRED'):require_production_visual_authority(work)
