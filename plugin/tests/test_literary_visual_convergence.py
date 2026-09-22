"""Actual P0 source through R1, using only the existing synthetic source fixture."""
from datetime import datetime, timezone
import pytest
from drama_plugin.config import load_config
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.creative_source import LiteraryPackage
from drama_plugin.contracts.professional import CreativeBible, CreativeRecord
from drama_plugin.contracts.specialized_asset import *
from drama_plugin.creative_source import compile_source
from drama_plugin.hosts.professional import ProfessionalDepartmentHost
from drama_plugin.hosts.specialized_asset import SpecializedAssetHost
from drama_plugin.professional import registry, bible_pin, approval_subject
from literary_fixture import fixture

@pytest.mark.parametrize('medium',['live_action','cg'])
def test_p0_root_to_specialized_assets_and_existing_department_consumers(tmp_path,medium):
    package=fixture();compiled=compile_source({'source':package,'jurisdiction':'TEST','intendedUse':'STUDY'})
    source=compiled.package_ref;states=compiled.resolved_input['characterArc']['states']
    host=SpecializedAssetHost(load_config(environment={'DRAMA_PLUGIN_VISUAL_MEDIUM':medium,'DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT':str(tmp_path)}))
    professional=ProfessionalDepartmentHost(tmp_path,source_type='LITERARY')
    host.store.put(source.key,dump_contract(LiteraryPackage.model_validate(package)))
    current={source.key:source.fingerprint};now=datetime.now(timezone.utc);bibles={};links={}
    values={
        'literary-source-input':{'source_package':package,'screenplay_input':dump_contract(compiled)},
        'story-architecture':{'premise':'technical fixture'},
        'character-dramaturgy':{'character_ref':'c','character_arc':states,'arc_stage':states[0]['arcStage'],'behavior_pattern':states[0]['behavioralState'],'social_position':'synthetic neighbor'},
        'scene-development':{'scene_ref':'s','scene_purpose':'structural fixture'},
        'director':{'restraint_principles':'Keep the approved current state.'}}
    for owner,fields in values.items():
        bible=CreativeBible(source_type='LITERARY',id=owner,type=registry('LITERARY')[owner].output_contract,work_ref='literary-work',source_refs=(source,),depends_on=tuple(bible_pin(bibles[d]) for d in registry('LITERARY')[owner].depends_on),content=(CreativeRecord(id='r',scope_refs=('literary-work',),values=fields,provenance='NEW_PROFESSIONAL_ELABORATION',source_refs=(source,)),),created_by_capability=owner,status='READY_FOR_REVIEW',created_at=now,updated_at=now)
        approval=host.store.put('approval:'+owner,{'kind':'PROFESSIONAL_CREATIVE_APPROVAL','decision':'APPROVE','subjectId':bible.id,'workRef':bible.work_ref,'subjectFingerprint':approval_subject(bible),'approvedBy':['offline-fixture']})
        current[approval.key]=approval.fingerprint
        bible=CreativeBible.model_validate({**dump_contract(bible),'status':'APPROVED','approvedBy':['offline-fixture'],'approvalRefs':[dump_contract(approval)]})
        professional.submit(owner,bible,current=current);ref=bible_pin(bible);current[ref.key]=ref.fingerprint;bibles[owner]=bible
        links[owner]=DramaturgyInput(bible_ref=ref,record_id='r',constraint_fields=tuple(fields))
    runtime=host.bind_movie('literary-work');current[runtime.key]=runtime.fingerprint
    style=host.save_style(GlobalVisualStyle(work_id='literary-work',runtime_ref=runtime,realism='NATURALISTIC',render_stylization='VISIBLE_FILMIC_CG' if medium=='cg' else None));current[style.key]=style.fingerprint
    common=dict(director=links['director'],world=links['literary-source-input']);char=links['character-dramaturgy'];scene=links['scene-development']
    def decision(text,link):return AssetDecision(text=text,reason='Synthetic interpretation, never source fact',source_refs=(link.bible_ref,))
    assets=SpecializedAssetBible(work_id='literary-work',runtime_ref=runtime,style_ref=style,assets=(
        CharacterAsset(id='char',character_id='c',arc_stage=states[0]['arcStage'],dramaturgy=char,decisions={'face':decision('An ordinary asymmetric adult face.',char)},**common),
        CostumeAsset(id='coat',character_id='c',arc_stage=states[0]['arcStage'],dramaturgy=char,decisions={'material':decision('Plain worn cotton.',char)},**common),
        SceneAsset(id='room',scene_id='s',dramaturgy=scene,decisions={'architecture':decision('A small room.',scene)},**common)))
    ref=host.submit(assets,current=current);current[ref.key]=ref.fingerprint
    for asset in assets.assets:
        output=host.compile(ref,asset.id,current=current)
        assert output['compilation']['medium']==('CG' if medium=='cg' else 'LIVE_ACTION')
        assert {r['layer'] for r in output['compilation']['sourceMap']} >= {'DRAMATURGY','RUNTIME_MEDIUM','ASSET_DESIGN'}
        assert not output['projection']['productionAuthorized']
    records=host.department_records(ref,('char',),'character-art',current=current)
    view=CreativeBible(source_type='LITERARY',id='art',type=registry('LITERARY')['character-art'].output_contract,work_ref='literary-work',source_refs=(source,),depends_on=tuple(bible_pin(bibles[d]) for d in registry('LITERARY')['character-art'].depends_on),content=records,created_by_capability='character-art',status='READY_FOR_REVIEW',created_at=now,updated_at=now)
    assert professional.submit('character-art',view,current=current)['validationStatus']=='PASS'
    assert records[0].values['arc_continuity_boundaries']==[{'arcStage':s['arcStage'],'visualContinuityBoundary':s['visualContinuityBoundary']} for s in states]
    changed=view.model_copy(deep=True);changed.content[0].values['arc_continuity_boundaries']=[]
    with pytest.raises(ValueError,match='CONSUME_ARC_BOUNDARIES|VIEW_CHANGED'):professional.submit('character-art',changed,current=current)


def test_cross_source_inputs_cannot_hide_behind_same_movie(tmp_path):
    from test_specialized_asset import fixture as historical_fixture
    from drama_plugin.specialized_asset import validate_assets
    from drama_plugin.contracts.base import sha256_canonical
    from drama_plugin.contracts.source_pin import SourcePin
    host,bible,ref,current=historical_fixture(tmp_path)
    originals,resolved=host._inputs(bible,current)
    world=bible.assets[0].world.bible_ref
    changed=dict(originals[world.key]);changed['sourceType']='LITERARY'
    pin=SourcePin(key=world.key,kind=world.kind,fingerprint=sha256_canonical(changed))
    originals[world.key]=changed;resolved[world.key]=pin.fingerprint
    data=dump_contract(bible);data['approvalRef']=None
    for asset in data['assets']:asset['world']['bibleRef']=dump_contract(pin)
    with pytest.raises(ValueError,match='CROSS_SOURCE_SPECIALIZED'):
        validate_assets(SpecializedAssetBible.model_validate(data),originals,resolved)
