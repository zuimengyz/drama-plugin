"""Offline A4 source-to-existing-request proofs; fictional fixtures, no generation."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from test_specialized_asset import fixture as asset_fixture
from test_visual_prompt_ir import visual_ir
from test_route_image_inputs import image_input
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.professional import CreativeBible, CreativeRecord
from drama_plugin.contracts.specialized_asset import AssetDecision, SpecializedAssetBible, GlobalVisualStyle, ImagingCharacterIntent
from drama_plugin.contracts.creation import Work
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.professional import registry, approval_subject
from drama_plugin.visual.frame_request import FrameSpec, compile_frame
from drama_plugin.visual.prompt_ir import compile_ir
from drama_plugin.visual.still_knowledge import *
from drama_plugin.hosts.route_production import (prepare_still_projection, validate_still_professional_sources,
    still_rule_catalog, _still_originals)


def scene(tmp_path, monkeypatch):
    host, assets, asset_pin, current = asset_fixture(tmp_path/'store')
    monkeypatch.setenv('DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT', str(tmp_path/'store'))
    monkeypatch.setenv('DRAMA_PLUGIN_VISUAL_MEDIUM', 'live_action')
    current[assets.runtime_ref.key] = assets.runtime_ref.fingerprint
    raw=dump_contract(assets)
    for key,text in {'age_presentation':'Forty years old as cast.', 'hair':'Short brown hair with a high hairline.',
                     'surface_state':'Even olive complexion.', 'physical_identity':'A small mole on the left cheek.'}.items():
        raw['assets'][0]['decisions'][key]=dump_contract(AssetDecision(text=text,reason='Approved individual identity',source_refs=(assets.assets[0].dramaturgy.bible_ref,)))
    for key,text in {'interior_structure':'A single courtyard.', 'period_visible_details':'A low timber door.'}.items():
        raw['assets'][2]['decisions'][key]=dump_contract(AssetDecision(text=text,reason='Approved set',source_refs=(assets.assets[2].dramaturgy.bible_ref,)))
    assets=SpecializedAssetBible.model_validate(raw)
    review=host.store.put('asset-review:work',{'kind':'SPECIALIZED_ASSET_REVIEW','decision':'APPROVE','workId':'work','reviewer':'offline',
        'checkedBoundaries':['DRAMATURGY','DIRECTOR_INTENT','SOURCE_WORLD','GLOBAL_STYLE'], 'subjectFingerprint':fp(dump_contract(assets,exclude={'approval_ref'}))})
    current[review.key]=review.fingerprint;assets=assets.model_copy(update={'approval_ref':review})
    asset_pin=host.submit(assets,current=current);current[asset_pin.key]=asset_pin.fingerprint
    source=host.store.put('source:still-test',{'synthetic':True});current[source.key]=source.fingerprint
    now=datetime.now(timezone.utc);custom={}
    def original(owner,values):
        deps=[]
        for dep in registry()[owner].depends_on:
            if dep in custom:deps.append(custom[dep]);continue
            key='bible:baseline-'+dep
            deps.append(SourcePin(key=key,kind='DESIGN',fingerprint=current[key]))
        bible=CreativeBible(id='still-'+owner,type=registry()[owner].output_contract,work_ref='work',scene_refs=('s',),shot_refs=('shot',),
            source_refs=(source,),depends_on=tuple(deps),created_by_capability=owner,status='READY_FOR_REVIEW',
            content=(CreativeRecord(id='r',scope_refs=('shot',),values=values,provenance='NEW_PROFESSIONAL_ELABORATION',source_refs=(source,)),),created_at=now,updated_at=now)
        approval=host.store.put('approval:still-'+owner,{'kind':'PROFESSIONAL_CREATIVE_APPROVAL','subjectId':bible.id,'workRef':'work','decision':'APPROVE','subjectFingerprint':approval_subject(bible),'approvedBy':['offline']})
        bible=CreativeBible.model_validate({**dump_contract(bible),'status':'APPROVED','approvedBy':['offline'],'approvalRefs':[dump_contract(approval)]})
        pin=host.store.put('bible:still-'+owner,dump_contract(bible)).model_copy(update={'kind':'DESIGN'});current.update({pin.key:pin.fingerprint,approval.key:approval.fingerprint});custom[owner]=pin;return pin
    def intent(s):return {'intent':s,'reason':'INTERNAL_REASON_NEVER_RENDER','criteria':'OBSERVATION_ONLY'}
    world=original('adaptation-boundary',{'source_basis':intent(['Present day.','Workshop courtyard.','An ordinary workplace.','Only approved workshop objects.'])})
    camera=original('cinematography',{k:intent(v) for k,v in {'shot_scale_philosophy':'Medium shot.', 'spatial_readability':'Face and both hands readable.',
        'camera_point_of_view':'A shared observer.', 'camera_height':'Waist height.', 'camera_distance':'Across the courtyard.', 'perspective':'Level optical axis.',
        'subject_hierarchy':'Person framed left.', 'lens_intention':['Normal spatial relationship.','Face and hands share the focus plane.']}.items()})
    light=original('lighting-design',{k:intent(v) for k,v in {'source':'Window daylight.', 'motivation':'The visible window lights the room.', 'direction':'Soft light from the left.',
        'contrast':'Readable shade.', 'falloff':'Light falls gradually across the face.', 'day_night_continuity':'Daytime.'}.items()})
    blocking=original('blocking',{'scene_ref':'s',**{k:intent(v) for k,v in {'actor_positions':'Person left.', 'actor_movements':'Standing still.', 'eye_lines':'Looking toward the door.', 'physical_relations':'Hands apart.'}.items()}})
    action=original('action-choreography',{'scene_ref':'s','body_mechanics':intent('Standing with hands at rest.')})
    performance=original('dramatic-performance-direction',{'character_ref':'c','emotional_state':intent('A small smile.')})
    look=original('look-continuity',{'character_ref':'c','skin_condition':intent('Dry, uninjured skin.')})
    pins=[assets.runtime_ref,assets.style_ref,asset_pin,assets.assets[0].dramaturgy.bible_ref,world,camera,light,blocking,action,performance,look]
    s,t=image_input(tmp_path);sd=s.model_dump(mode='json');actor=sd['actors'][0];actor.update(entity_key='c',label='person');sd.update(shot_id='shot',actors=[actor]);spec=FrameSpec.model_validate(sd)
    ir=visual_ir();ir['subjects'][0]['id']='c';ir['subjects'][0]['beard']=None
    ir['world']['environment_rules']=[];ir['action']['non_current']=[];ir['negative_constraints']=[];ir['secondary_details']=[]
    ir['camera']['depth_cues']=[];ir['preserve']=[]
    rows=[]
    def add(pin,path,target,cap='C15',owner=None,operation='COPY_LEAF',extra=()):
        if owner is None:owner='specialized-asset-design' if pin==asset_pin else host.store.read_ref(pin)['createdByCapability']
        leaves=(Leaf(pin=pin,pointer=path),*extra)
        rows.append(MappingRow(mapping_id='m'+str(len(rows)),capability_ids=(cap,),owner=owner,inputs=leaves,target=target,operation=operation));return leaves[0]
    for j,key in enumerate(['era','location','historical_context','environment_rules/0']):add(world,f'/content/0/values/source_basis/intent/{j}','/world/'+key)
    add(assets.assets[0].dramaturgy.bible_ref,'/content/0/values/character_ref','/subjects/0/role')
    coverage=[]
    for key,target,cap in [('face','face','F01'),('age_presentation','apparent_age','F20'),('hair','hair','F13'),('body','body_proportions','C15')]:
        extra=tuple(Leaf(pin=asset_pin,pointer='/assets/0/decisions/'+f+'/text') for f in ['surface_state','physical_identity']) if key=='face' else ()
        leaf=add(asset_pin,'/assets/0/decisions/'+key+'/text','/subjects/0/'+target,cap,operation='JOIN_ORDERED_LEAVES' if extra else 'COPY_LEAF',extra=extra)
        if key!='body':
            for l in (leaf,*extra):coverage.append(Coverage(capability_id=cap,canonical_field=l,use_requirement='REQUIRED_FOR_USE',evidence_state='VISIBLE',semantic_class='STABLE_IDENTITY').model_dump(mode='json'))
    add(asset_pin,'/assets/1/decisions/material/text','/subjects/0/costume')
    add(look,'/content/0/values/skin_condition/intent','/subjects/0/visible_condition','F29')
    for key,target in [('actor_positions','positions'),('eye_lines','orientation'),('physical_relations','contact'),('actor_movements','visible_relation')]:add(blocking,'/content/0/values/'+key+'/intent','/blocking/'+target)
    add(action,'/content/0/values/body_mechanics/intent','/action/current_visible_action')
    add(performance,'/content/0/values/emotional_state/intent','/action/expression')
    for key,target in [('architecture','architecture'),('interior_structure','topology'),('period_visible_details','required_period_objects')]:add(asset_pin,'/assets/2/decisions/'+key+'/text','/environment/'+target)
    for key,target,cap in [('shot_scale_philosophy','shot_size','C02'),('spatial_readability','readable_details','C02'),('subject_hierarchy','framing','C05')]:add(camera,'/content/0/values/'+key+'/intent','/camera/'+target,cap)
    add(camera,'/content/0/values/camera_point_of_view/intent','/camera/perspective','C03',operation='JOIN_ORDERED_LEAVES',extra=tuple(Leaf(pin=camera,pointer='/content/0/values/'+k+'/intent') for k in ['camera_height','camera_distance','perspective']))
    for j in range(2):add(camera,f'/content/0/values/lens_intention/intent/{j}',f'/camera/depth_cues/{j}','C06' if j==0 else 'C07')
    add(light,'/content/0/values/source/intent','/lighting/light_sources','C09',operation='JOIN_ORDERED_LEAVES',extra=tuple(Leaf(pin=light,pointer='/content/0/values/'+k+'/intent') for k in ['motivation','direction']))
    for key,target in [('contrast','contrast'),('falloff','realism'),('day_night_continuity','time_of_day')]:add(light,'/content/0/values/'+key+'/intent','/lighting/'+target,'C09')
    refplan=original('reference-strategy',{'shot_ref':'shot','reference_images':[],'reference_roles':[],'requirements':{'face_coverage':coverage}});pins.append(refplan)
    work=Work(id='work',title='OFFLINE SYNTHETIC',content={'movieVisualMediumRef':dump_contract(assets.runtime_ref),'visualSourceCurrent':current})
    scope=Scope(work_id='work',scene_id='s',shot_id='shot',actors={'c':'opening'})
    def prepare():return prepare_still_projection(work,spec,ir,scope=scope,source_pins=tuple(pins),rows=tuple(rows))
    return locals()


def test_complete_source_to_single_serializer_and_host(tmp_path,monkeypatch):
    f=scene(tmp_path,monkeypatch);bound=f['prepare']();compiled=compile_frame(bound,f['t'])
    assert validate_still_professional_sources(f['work'],compiled)
    prompt=compiled['prompt_ir_compilation']['prompt']
    for text in ['Waist height.','Level optical axis.','Across the courtyard.','Face and both hands readable.',
                 'Normal spatial relationship.','Face and hands share the focus plane.','Window daylight.','Forty years old as cast.',
                 'Even olive complexion.','A small mole on the left cheek.','A small smile.']:assert text in prompt
    for text in ['INTERNAL_REASON','OBSERVATION_ONLY','pores','blemishes','rejuvenate','enlarge eyes','rule_id']:assert text not in prompt
    assert f['prepare']().model_dump()==bound.model_dump()
    assert bound.actors[0].identity==bound.prompt_ir['subjects'][0]['face']['text']


@pytest.mark.parametrize('mutation',['stale','forged_owner','wrong_work','wrong_stage','reason','dict','unmapped','identity_expression','reference_light'])
def test_source_and_authority_rejections(tmp_path,monkeypatch,mutation):
    f=scene(tmp_path,monkeypatch)
    if mutation=='stale':f['current'][f['camera'].key]='0'*64
    elif mutation=='forged_owner':f['rows'][0]=f['rows'][0].model_copy(update={'owner':'director'})
    elif mutation=='wrong_work':f['work'].id='other'
    elif mutation=='wrong_stage':f['scope'].actors['c']='older'
    elif mutation in {'reason','dict'}:
        row=next(r for r in f['rows'] if r.target=='/camera/shot_size');i=f['rows'].index(row)
        pointer_value=row.inputs[0].pointer.replace('/intent','/reason' if mutation=='reason' else '')
        f['rows'][i]=row.model_copy(update={'inputs':(Leaf(pin=f['camera'],pointer=pointer_value),)})
    elif mutation=='unmapped':f['rows'].pop()
    elif mutation=='identity_expression':
        i=next(i for i,r in enumerate(f['rows']) if r.target=='/action/expression');f['rows'][i]=f['rows'][i].model_copy(update={'owner':'specialized-asset-design','inputs':(Leaf(pin=f['asset_pin'],pointer='/assets/0/decisions/hair/text'),)})
    elif mutation=='reference_light':
        i=next(i for i,r in enumerate(f['rows']) if r.target=='/lighting/realism');f['rows'][i]=f['rows'][i].model_copy(update={'owner':'reference-strategy','inputs':(Leaf(pin=f['refplan'],pointer='/content/0/values/shot_ref'),)})
    with pytest.raises(ValueError):f['prepare']()


def test_tampered_fact_and_freshness_after_freeze(tmp_path,monkeypatch):
    f=scene(tmp_path,monkeypatch);bound=f['prepare']();compiled=compile_frame(bound,f['t'])
    f['work'].content['visualSourceCurrent'][f['camera'].key]='0'*64
    with pytest.raises(ValueError,match='STALE'):validate_still_professional_sources(f['work'],compiled)
    f['current'][f['camera'].key]=f['camera'].fingerprint;f['work'].content['visualSourceCurrent']=f['current']
    raw=bound.model_dump();raw['prompt_ir']['subjects'][0]['apparent_age']['text']='Eighteen years old.'
    changed=FrameSpec.model_validate(raw);forged=compile_frame(changed,f['t'])
    with pytest.raises(ValueError,match='IR_FACT_CHANGED'):validate_still_professional_sources(f['work'],forged)


def test_legacy_empty_fields_exact_wire(tmp_path,monkeypatch):
    f=scene(tmp_path,monkeypatch)
    legacy=f['spec'].model_dump(mode='json');assert 'professional_sources' not in legacy
    assert FrameSpec.model_validate({**legacy,'professional_sources':[]}).model_dump(mode='json')==legacy
    style=GlobalVisualStyle.model_validate(f['host'].store.read_ref(f['assets'].style_ref));wire=dump_contract(style)
    assert 'imagingCharacter' not in wire
    assert dump_contract(GlobalVisualStyle.model_validate({**wire,'imagingCharacter':None}))==wire


@pytest.mark.parametrize('status,visible,media,severity,remedy,expected',[
    ('PASS',False,None,None,'ACCEPT','PENDING_REVIEW'),('FAIL',True,'a'*64,'MINOR','ACCEPT','PASS_WITH_NOTES'),
    ('FAIL',True,'a'*64,'MAJOR','REGENERATE','FAIL'),('PASS',True,'a'*64,None,'ACCEPT','PASS')])
def test_observation_existing_review(tmp_path,monkeypatch,status,visible,media,severity,remedy,expected):
    f=scene(tmp_path,monkeypatch);originals=_still_originals(f['host'].store,tuple(f['pins']),f['current']);before=deepcopy(originals)
    obs=Observation(criterion_id='QC-AGE-DRIFT',actor='c',arc_stage='opening',requirement=Leaf(pin=f['asset_pin'],pointer='/assets/0/decisions/age_presentation/text'),
        media_hash=media,reference_hash='b'*64,region='whole face',use='identity closeup',visible=visible,comparison='approved age',observation='eye region volume differs',
        status=status,impact='identity use',root_cause_hypothesis='output drift with unchanged approved source',confidence='MEDIUM',repair_owner='shot-production',severity=severity,remedy=remedy,preserve_scope='all other approved facts')
    result=observation_review(attempt_id='c'*64,output_hash='a'*64,reviewer='offline',evidence_ref='evidence:offline',observations=(obs,),originals=originals,current=f['current'])
    assert result['status']==expected and originals==before
    if severity:assert result['qa_values']['owner_routes'][0]['owner']=='shot-production'
    if severity=='MINOR':
        with pytest.raises(ValueError,match='MINOR_FAILURE'):observation_review(attempt_id='c'*64,output_hash='a'*64,reviewer='offline',evidence_ref='evidence:offline',observations=(obs.model_copy(update={'remedy':'REGENERATE'}),),originals=originals,current=f['current'])


def multi_reference(f,tmp_path):
    from test_visual_first_pass import material
    initial,_=material(tmp_path)
    refs=[];lock={};duties=[]
    fields=[('/assets/0/decisions/face/text','face','CHARACTER','c','char'),('/assets/1/decisions/material/text','costume','COSTUME','coat-key','coat'),('/assets/2/decisions/architecture/text','scene','SCENE','room-key','room')]
    for i,(path,carry,kind,key,asset) in enumerate(fields,1):
        r=initial.references[0].model_dump(mode='json');r.update(entity_key=key,kind=kind,asset_id=asset,media_id='media'+str(i),upload_name='image'+str(i)+'.png')
        upload=tmp_path/('upload'+str(i)+'.json');upload.write_text(json.dumps({'name':r['upload_name'],'content_hash':r['content_hash']}));r['upload_receipt']=str(upload)
        refs.append(r);lock[f"{r['asset_id']}/{r['media_id']}/{r['version']}"]=r['content_hash']
        duties.append(ReferenceDuty(entity_key=key,media_id=r['media_id'],version=r['version'],content_hash=r['content_hash'],slot=i,
            actor_ids=('c',) if kind!='SCENE' else (),carries=(carry,),must_not_carry=tuple(sorted(CURRENT)),canonical_fields=(Leaf(pin=f['asset_pin'],pointer=path),),evidence_state='VISIBLE',visibility='visible selected region',use=carry,
            preservation_text=f'Image {i} supplies only approved {carry}; current pose, gaze, expression, lighting and camera remain shot-owned.').model_dump(mode='json'))
    ref=f['original']('reference-strategy',{'shot_ref':'shot','reference_images':[r['media_id'] for r in refs],'reference_roles':duties,'requirements':{'face_coverage':f['coverage']}})
    pins=[p if p.key!=ref.key else ref for p in f['pins']]
    rows=list(f['rows'])
    for i in range(3):rows.append(MappingRow(mapping_id='duty'+str(i),capability_ids=('C15','F23'),owner='reference-strategy',inputs=(Leaf(pin=ref,pointer=f'/content/0/values/reference_roles/{i}/preservation_text'),),target=f'/preserve/{i}'))
    spec=FrameSpec.model_validate({**f['spec'].model_dump(mode='json'),'identity_bootstrap':None,'references':refs,'reference_lock':lock})
    f['work'].content['visualSourceCurrent']=f['current']
    return spec,pins,rows,ref,duties


def test_three_reference_duties_and_leakage(tmp_path,monkeypatch):
    f=scene(tmp_path,monkeypatch);spec,pins,rows,ref,duties=multi_reference(f,tmp_path)
    bound=prepare_still_projection(f['work'],spec,f['ir'],scope=f['scope'],source_pins=tuple(pins),rows=tuple(rows))
    prompt=compile_ir(bound.prompt_ir,provider_family='Flux.2 [pro]')['prompt']
    assert all('Image '+str(i)+' supplies only approved' in prompt for i in [1,2,3])
    assert bound.prompt_ir['action']['expression']['text']=='A small smile.'
    assert bound.prompt_ir['lighting']['light_sources']['text'].startswith('Window daylight.')
    for mutation in ['swap','missing','wrongkind']:
        raw=bound.model_dump(mode='json')
        if mutation=='swap':raw['references'].reverse()
        if mutation=='missing':raw['references'].pop()
        if mutation=='wrongkind':raw['references'][0]['kind']='COSTUME'
        changed=FrameSpec.model_validate(raw);receipt_pin=changed.professional_sources[-1];receipt=f['host'].store.read_ref(receipt_pin)
        originals=_still_originals(f['host'].store,tuple(pins),f['current'])
        with pytest.raises(ValueError):validate_reference_plan(changed,receipt,originals,f['current'])


def test_d1_scope_approval_mapping_and_legacy_consumer(tmp_path,monkeypatch):
    f=scene(tmp_path,monkeypatch)
    base_originals=_still_originals(f['host'].store,tuple(f['pins']),f['current'])
    old=GlobalVisualStyle.model_validate(f['host'].store.read_ref(f['assets'].style_ref))
    imaging=ImagingCharacterIntent(capture_character='Restrained photographic capture.',reason='Approved capture boundary',source_refs=(f['camera'],),optical_texture=())
    style=old.model_copy(update={'imaging_character':imaging})
    pin=f['host'].save_style(style,current=f['current'])
    assert fp(style)!=fp(old) and dump_contract(style)['imagingCharacter']['captureCharacter']==imaging.capture_character
    f['current'][pin.key]=pin.fingerprint
    originals=_still_originals(f['host'].store,(pin,),f['current'])
    row=MappingRow(mapping_id='capture',capability_ids=('C11','C30'),owner='global-visual-style',inputs=(Leaf(pin=pin,pointer='/imagingCharacter/captureCharacter'),),target='/preserve/0')
    receipt=make_receipt(scope=f['scope'],source_pins=(pin,),rows=(row,),originals=originals,current=f['current'],subject_ids=['c'],rule_catalog=still_rule_catalog())
    assert receipt['rows'][0]['text_hash']==fp(imaging.capture_character)
    with pytest.raises(ValueError):f['host'].save_style(style,current={})
    with pytest.raises(ValueError):ImagingCharacterIntent(reason='empty',source_refs=(f['camera'],))
    cg=deepcopy(originals);cg[style.runtime_ref.key]['medium']='CG'
    # Changed medium fails the exact pin before it can be accepted as a capture choice.
    with pytest.raises(ValueError):validate_imaging(style,cg,f['current'])
    from drama_plugin.specialized_asset import compile_asset,provider_projection
    raw=dump_contract(f['assets']);raw['styleRef']=dump_contract(pin);raw['approvalRef']=None
    assets=SpecializedAssetBible.model_validate(raw)
    originals={**base_originals,**originals}
    compiled=compile_asset(assets,'char',originals,f['current'])
    assert any('imagingCharacter' in r.get('fields',[]) for r in compiled['sourceMap'])
    with pytest.raises(ValueError,match='STILL_PROFESSIONAL_CONSUMER'):provider_projection(compiled,originals,f['current'])


@pytest.mark.parametrize('task,medium',[('VIDEO','LIVE_ACTION'),('FIRST_FRAME','CINEMATIC_CG')])
def test_non_still_medium_cannot_opt_in(tmp_path,monkeypatch,task,medium):
    f=scene(tmp_path,monkeypatch);f['ir']['task'].update(task_type=task,visual_medium=medium)
    with pytest.raises(ValueError,match='STILL_LIVE_ACTION_ONLY'):f['prepare']()


def test_edit_required_omission_is_explicit(tmp_path,monkeypatch):
    f=scene(tmp_path,monkeypatch);bound=f['prepare']();ir=deepcopy(bound.prompt_ir)
    # Existing selector omits age; A4 does not modify it. A required row cannot
    # be passed off as consumed merely because it is present in the IR.
    ir['task'].update(task_type='IMAGE_EDIT',input_mode='edit');ir['preserve']=[ir['subjects'][0]['hair']]
    ir['edit_delta']=[{'operation':'correct','region':'face','source_issue':ir['subjects'][0]['face'],'target_correction':ir['subjects'][0]['face']}]
    compiled=compile_ir(ir,provider_family='Flux.2 [pro]')
    assert any(r['path']=='subject.c.apparent_age' for r in compiled['omitted'])
    assert 'Forty years old as cast.' not in compiled['prompt']


def test_catalog_scope_hash_and_exact_a3_allowlist():
    catalog=still_rule_catalog();assert {r['capability_id'] for r in catalog['rules']}==CINE|FACE
    for r in catalog['rules']:
        raw={k:v for k,v in r.items() if k!='rule_hash'}
        assert fp(raw)==r['rule_hash'] and r['validation_status']=='LOCAL_EXPERIMENTAL'


def test_nonempty_d1_is_consumed_and_missing_mapping_blocks(tmp_path,monkeypatch):
    f=scene(tmp_path,monkeypatch)
    style=GlobalVisualStyle.model_validate(f['host'].store.read_ref(f['assets'].style_ref)).model_copy(update={
        'imaging_character':ImagingCharacterIntent(capture_character='Restrained capture character.',reason='Approved still capture',source_refs=(f['camera'],))})
    style_pin=f['host'].save_style(style,current=f['current']);f['current'][style_pin.key]=style_pin.fingerprint
    asset=f['assets'].model_copy(update={'style_ref':style_pin,'approval_ref':None})
    approval=f['host'].store.put('asset-review:work',{'kind':'SPECIALIZED_ASSET_REVIEW','decision':'APPROVE','workId':'work','reviewer':'offline','checkedBoundaries':['DRAMATURGY','DIRECTOR_INTENT','SOURCE_WORLD','GLOBAL_STYLE'],'subjectFingerprint':fp(dump_contract(asset,exclude={'approval_ref'}))})
    f['current'][approval.key]=approval.fingerprint
    asset=asset.model_copy(update={'approval_ref':approval})
    asset_pin=f['host'].submit(asset,current=f['current']);f['current'][asset_pin.key]=asset_pin.fingerprint
    coverage=deepcopy(f['coverage'])
    for c in coverage:c['canonical_field']['pin']=asset_pin.model_dump(mode='json')
    plan=f['original']('reference-strategy',{'shot_ref':'shot','reference_images':[],'reference_roles':[],'requirements':{'face_coverage':coverage}})
    replacements={style_pin.key:style_pin,asset_pin.key:asset_pin,plan.key:plan}
    pins=tuple(replacements.get(p.key,p) for p in f['pins'])
    rows=[r.model_copy(update={'inputs':tuple(l.model_copy(update={'pin':replacements.get(l.pin.key,l.pin)}) for l in r.inputs)}) for r in f['rows']]
    f['work'].content['visualSourceCurrent']=f['current']
    with pytest.raises(ValueError,match='IMAGING_CHARACTER_NOT_CONSUMED'):
        prepare_still_projection(f['work'],f['spec'],f['ir'],scope=f['scope'],source_pins=pins,rows=tuple(rows))
    rows.append(MappingRow(mapping_id='capture',capability_ids=('C11','C30'),owner='global-visual-style',inputs=(Leaf(pin=style_pin,pointer='/imagingCharacter/captureCharacter'),),target='/preserve/0'))
    bound=prepare_still_projection(f['work'],f['spec'],f['ir'],scope=f['scope'],source_pins=pins,rows=tuple(rows))
    compiled=compile_frame(bound,f['t']);assert validate_still_professional_sources(f['work'],compiled)
    assert 'Restrained capture character.' in compiled['prompt_ir_compilation']['prompt']


def test_reference_coverage_cannot_certify_current_state_as_identity(tmp_path,monkeypatch):
    f=scene(tmp_path,monkeypatch);coverage=deepcopy(f['coverage']);coverage[0]['semantic_class']='CURRENT_STATE'
    plan=f['original']('reference-strategy',{'shot_ref':'shot','reference_images':[],'reference_roles':[],'requirements':{'face_coverage':coverage}})
    pins=tuple(plan if p.key==plan.key else p for p in f['pins']);f['work'].content['visualSourceCurrent']=f['current']
    with pytest.raises(ValueError,match='MIXED_IDENTITY'):
        prepare_still_projection(f['work'],f['spec'],f['ir'],scope=f['scope'],source_pins=pins,rows=tuple(f['rows']))


@pytest.mark.asyncio
@pytest.mark.parametrize('command',['reserve','begin-submission'])
async def test_both_formal_spend_gates_reopen_sources(tmp_path,monkeypatch,command):
    from types import SimpleNamespace
    from test_production_route import route
    from drama_plugin.hosts import route_production as hostmodule
    f=scene(tmp_path,monkeypatch);compiled=compile_frame(f['prepare'](),f['t'])
    raw=route(tmp_path).model_dump(mode='json');raw['work_id']='work'
    f['work'].content.update(productionRoute=raw,productionStage={'frames':{'shot':compiled},'attempts':[{'attempt_id':'offline','shot_id':'shot','request':compiled['request']} ]})
    class Memory:
        async def get_work(self,work_id):return deepcopy(f['work'])
        async def save_work(self,*args):raise AssertionError('Stale source must not persist reservation')
    async def jurisdiction(*args):pass
    # Isolate existing jurisdiction/campaign gates, not the new source resolver.
    monkeypatch.setattr(hostmodule,'validate_route_direction_sources',jurisdiction)
    monkeypatch.setattr(hostmodule.production,'check_campaign',lambda state:None)
    monkeypatch.setattr(hostmodule,'attempt_frame',lambda state,attempt:state['frames'][attempt['shot_id']])
    f['work'].content['visualSourceCurrent'][f['camera'].key]='0'*64
    with pytest.raises(ValueError,match='STILL_STALE_PROFESSIONAL_SOURCE'):
        await hostmodule.operate(Memory(),'work',command,{'shot_id':'shot'} if command=='reserve' else {'attempt_id':'offline'})


def test_reference_leakage_without_reference_evidence_is_unknown(tmp_path,monkeypatch):
    f=scene(tmp_path,monkeypatch);originals=_still_originals(f['host'].store,tuple(f['pins']),f['current'])
    obs=Observation(criterion_id='QC-REFERENCE-LEAKAGE',actor='c',arc_stage='opening',requirement=Leaf(pin=f['asset_pin'],pointer='/assets/0/decisions/face/text'),
        media_hash='a'*64,region='face',use='closeup',visible=True,comparison='unavailable portrait',observation='possible reference expression',status='FAIL',impact='expression',root_cause_hypothesis='reference duty',confidence='LOW',repair_owner='reference-strategy',severity='MAJOR',preserve_scope='identity')
    result=observation_review(attempt_id='b'*64,output_hash='a'*64,reviewer='offline',evidence_ref='obs',observations=(obs,),originals=originals,current=f['current'])
    assert result['status']=='PENDING_REVIEW' and not result['review']['findings']


def test_required_identity_cannot_be_marked_optional_to_evade_consumption(tmp_path,monkeypatch):
    f=scene(tmp_path,monkeypatch)
    i=next(i for i,r in enumerate(f['rows']) if r.target=='/subjects/0/apparent_age')
    f['rows'][i]=f['rows'][i].model_copy(update={'required':False})
    with pytest.raises(ValueError,match='REQUIRED_FACE_PRESERVATION_MISSING'):f['prepare']()


def test_qc_sidecar_enters_existing_review_without_creative_write(tmp_path,monkeypatch):
    from drama_plugin.hosts.route_production import still_observation_payload
    f=scene(tmp_path,monkeypatch)
    obs=Observation(criterion_id='QC-FACE-GEOMETRY',actor='c',arc_stage='opening',requirement=Leaf(pin=f['asset_pin'],pointer='/assets/0/decisions/face/text'),
        media_hash='a'*64,reference_hash='b'*64,region='jaw',use='closeup identity',visible=True,comparison='approved jaw',observation='jaw relation changed',status='FAIL',impact='required identity lost',root_cause_hypothesis='provider drift',confidence='MEDIUM',repair_owner='shot-production',severity='MAJOR',remedy='REGENERATE',preserve_scope='all other approved facts')
    ref=f['host'].store.put('observation:offline',{'work_id':'work','attempt_id':'c'*64,'output_hash':'a'*64,'observations':[obs.model_dump(mode='json')]})
    before=deepcopy(f['work'].content)
    review=still_observation_payload(f['work'],{'attempt_id':'c'*64,'output_hash':'a'*64,'reviewer':'offline','still_observation_ref':dump_contract(ref)})
    assert review['checks']['QC-FACE-GEOMETRY:c']=='FAIL' and f['work'].content==before
    assert review['findings'][0]['remedy']=='REGENERATE' # recommendation only, no calls/state changes


def test_legacy_frame_matches_pre_a4_wire_and_compilation(tmp_path):
    # Explicit empty extension must not change any existing byte or fingerprint.
    spec,template=image_input(tmp_path)
    old=spec.model_dump(mode='json')
    assert 'professional_sources' not in old
    with_empty=FrameSpec.model_validate({**old,'professional_sources':[]})
    assert compile_frame(spec,template)==compile_frame(with_empty,template)


def test_rule_catalog_never_introduces_new_authority():
    from drama_plugin.professional import registry
    r=registry();assert 'imaging_character' in r['global-visual-style'].authority_scope
    assert 'face-realism-super-owner' not in r and 'cinematography-super-owner' not in r
    assert r['character-art'].deprecated_forward_to=='specialized-asset-design'


def test_current_default_adapter_consumes_exact_existing_serializer(tmp_path,monkeypatch):
    f=scene(tmp_path,monkeypatch);bound=f['prepare']();compiled=compile_frame(bound)
    assert compiled['template']['model']=='gpt-image-2'
    assert compiled['request']['workflow'][compiled['template']['prompt_node']]['inputs']['prompt']==compiled['prompt_ir_compilation']['prompt']
    assert validate_still_professional_sources(f['work'],compiled)
