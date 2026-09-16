from copy import deepcopy
from pathlib import Path
import pytest
from pydantic import ValidationError
from drama_plugin import DramaPlugin
from drama_plugin.contracts.base import dump_contract,sha256_canonical
from drama_plugin.contracts.asset import Asset,AssetType
from drama_plugin.contracts.production_design import (CharacterVisualSpec,CharacterState,ProductionDesignContent,
 CanonBasis,FactionVisualSystem,LocationDesignSpec,VisualMotifSpec,FirstAppearanceContract)
from drama_plugin.contracts.dramatic_editorial import (DramaticPeakMap,SetPiece,HeroMoment,PressureRelease,
 EditorialRhythmPlan,SingleTakeFeasibility,CutMotivation,CoverageShot,PictureEditPlan)
from drama_plugin.production_design import (design_handoff,verify_design_handoff,validate_reference_design,
 picture_edit_handoff,review_design,review_peaks)
from drama_plugin.creative_assets import remember
ROOT=Path(__file__).resolve().parents[1]


def character(core=True):
 first={k:'Story-supported readable distinction' for k in ['silhouette','visual_hierarchy','costume_hierarchy','blocking','camera_privilege','lighting_privilege','surrounding_reaction','first_readable_action','first_readable_attitude']}
 return CharacterVisualSpec(character_identity='captain',revision='v2',dramatic_role='authority',core_character=core,
 visual_objective='A tired station commander identifiable through economical action',silhouette='Long upright line',
 first_appearance=first if core else None,visual_authority=dict(silhouette_authority='Upright stillness',costume_hierarchy='Maintained collar',blocking_hierarchy='Others leave workspace clear',first_glance_importance='Decisions converge here') if core else None)


def content():
 return ProductionDesignContent(creative_kind='CHARACTER_VISUAL_SPEC',semantic_key='production-design/captain/v2',title='Captain visual candidate',spec=character(),provenance={'source_type':'PROJECT','source_note':'Existing script'},validation={'status':'PROJECT_DERIVED'},stable_reuse_reason='Cross-scene casting')


def editorial():
 return dict(scene_ids=['s'],source_fingerprint='a'*64,revision='r1',information_beats=[dict(key='a',information='Signal arrives',focus='Console',change='A choice becomes possible'),dict(key='b',information='Refusal',focus='Captain',change='Opportunity closes')],coverage=[dict(key='x',beat_ids=['a'],duration=2,duration_basis='DRAMATIC_INFORMATION',duration_reason='Read the signal',purpose='DETAIL'),dict(key='y',beat_ids=['b'],duration=3,duration_basis='DRAMATIC_INFORMATION',duration_reason='Complete refusal',purpose='HERO',visual_power_reason='Decision commits the crew')],cuts=[dict(from_beat='a',to_beat='b',reason='Information to choice',new_information_or_relation='The person responsible')],reaction_chain=[dict(actor='Crew',observed_action='Stops working',responds_to='Captain refusal',changes='Attention converges')],establishing_need='Console and door in opening view',visual_contrast_rhythm='Detail to group')


def picture():
 return dict(revision='r1',source_canon_fingerprint='a'*64,sources=[dict(media_id='m',content_hash='b'*64,duration=14,performance_review='Observed gesture and unknown speech')],picture_edit=[dict(source_media='m',source_in=1,source_out=12,cut_reason='Omit repeated wait',audio_carry='Preserve native until hearing review',pace_function='Attention shift')],protected_dialogue_review='Pending real listening')


def test_skill_discovery_and_no_generation_access():
 p=DramaPlugin.load(ROOT);s=p.skills.get('production-design')
 assert s.name=='Production Design & Casting' and len(p.skills.list())==17 and len(p.tools.list())==50
 assert all(n in {t.code for t in p.tools.list()} for n in s.tools.preferred+s.tools.allowed)
 assert not any(n.startswith(('production.','media.import','media.save')) for n in s.tools.preferred+s.tools.allowed)


@pytest.mark.parametrize('field',['model','provider','providerPrompt','input_overrides','state','mud','injury','currentWetness'])
def test_typed_design_forbids_provider_and_transient_fields(field):
 raw=dump_contract(character());raw[field]='unrequested'
 with pytest.raises(ValidationError):CharacterVisualSpec.model_validate(raw)


def test_optional_supporting_character_and_core_authority():
 assert character(False).face.shape is None
 for field in ['firstAppearance','visualAuthority']:
  raw=dump_contract(character());raw[field]=None
  with pytest.raises(ValidationError):CharacterVisualSpec.model_validate(raw)


def test_first_appearance_caption_cannot_replace_distinction():
 raw=dump_contract(character().first_appearance);raw.update(distinctFromExtras=False,nameCaptionRequirement='REQUIRED')
 with pytest.raises(ValidationError):FirstAppearanceContract.model_validate(raw)
 raw['hiddenIdentityReason']='The commander is undercover';assert FirstAppearanceContract.model_validate(raw)


def test_historical_constraints_follow_handoff_and_revision():
 c=content();c.spec.historical_constraints.historical=True
 with pytest.raises(ValidationError):ProductionDesignContent.model_validate(dump_contract(c))
 c.spec.historical_constraints.constraints=('No unsupported uniform insignia',)
 c.spec.historical_constraints.source_canon=(CanonBasis(source_ref='Museum',claim='Garment construction evidence',classification='DOCUMENTED'),)
 c=ProductionDesignContent.model_validate(dump_contract(c));h=design_handoff(c,consumer='asset-resolution')
 assert verify_design_handoff(h)==c
 bad=deepcopy(h);bad['content']['spec']['historicalConstraints']['constraints']=[]
 with pytest.raises(ValueError):verify_design_handoff(bad)
 changed=c.model_copy(deep=True);changed.spec.face.shape='Different cheek proportions'
 assert sha256_canonical(changed)!=sha256_canonical(c)


def test_identity_state_separate_and_candidate_cannot_replace():
 c=content();state=CharacterState(character_identity='captain',scene_or_shot_id='s',changes=['Wet sleeve'])
 a=design_handoff(c,consumer='shot-design',state=state);b=design_handoff(c,consumer='shot-design')
 assert a['contentFingerprint']==b['contentFingerprint'] and 'changes' not in a['content']['spec']
 with pytest.raises(ValueError):design_handoff(c,consumer='asset-resolution',for_production=True)
 with pytest.raises(ValueError):design_handoff(c,consumer='asset-resolution',state=state.model_copy(update={'character_identity':'other'}))
 c.usage_mode='APPROVED_DESIGN';c.approval_evidence='User selected this design revision';h=design_handoff(c,consumer='asset-resolution',for_production=True)
 with pytest.raises(ValueError):validate_reference_design(h,{'productionDesignFingerprint':'0'*64})
 validate_reference_design(h,{'productionDesignFingerprint':h['contentFingerprint']})


def test_director_freeze_preserves_stable_design():
 from test_cinematic_direction import example
 from drama_plugin.visual.cinematic import freeze_direction,verify_frozen
 spec,ctx,visual=example();c=content();c.usage_mode='APPROVED_DESIGN';c.approval_evidence='User selected'
 h=design_handoff(c,consumer='cinematic-direction');ctx['productionDesign']=[h]
 frozen=freeze_direction(spec,context=ctx,visual_resolution=visual,host_review='Reviewed')
 assert frozen['productionDesign'][0]==h and verify_frozen(frozen)
 damaged=deepcopy(frozen);damaged['productionDesign'][0]['content']['spec']['silhouette']='rewritten by director'
 damaged['fingerprint']=sha256_canonical({k:v for k,v in damaged.items() if k!='fingerprint'})
 with pytest.raises(ValueError):verify_frozen(damaged)


@pytest.mark.asyncio
async def test_text_asset_create_get_search_reuse_conflict_no_media():
 p=DramaPlugin.load(ROOT);c=content();w=p.providers.memory.data.work.id
 a,status=await remember(p.tools,w,c);assert status=='CREATED' and a.asset_type==AssetType.OTHER and a.reference_media_ids==[]
 assert (await remember(p.tools,w,c))[1]=='REUSED'
 changed=c.model_copy(deep=True);changed.spec.silhouette='New revision'
 with pytest.raises(ValueError,match='revision conflict'):await remember(p.tools,w,changed)
 for kind,refs in [(AssetType.CHARACTER,[]),(AssetType.OTHER,['m'])]:
  with pytest.raises(ValueError):Asset(id='x',work_id=w,asset_type=kind,name='bad',content=dump_contract(c),reference_media_ids=refs)


def test_faction_differences_not_renamed_faces():
 rank=dict(role='leader',silhouette='same',materials='cloth',wear='used',rank_signals='same')
 with pytest.raises(ValueError):FactionVisualSystem(faction='crew',revision='1',shared_language='Utility',ranks=[rank,{**rank,'role':'worker'}])
 assert FactionVisualSystem(faction='crew',revision='1',shared_language='Utility',ranks=[rank,{**rank,'role':'worker','rank_signals':'No collar strip'}])


def test_location_and_motif_require_story_not_adjectives():
 with pytest.raises(ValueError):LocationDesignSpec(location='station',revision='1',materials='cinematic')
 with pytest.raises(ValueError):VisualMotifSpec(motif='lamp',revision='1',physical_form='blue')
 motif=VisualMotifSpec(motif='lamp',revision='1',physical_form='Used work lamp',serves='PLOT',narrative_function='Marks whether the signal station is occupied',recurrence_change='Occupied to abandoned',avoid_decoration='No extra lamps without workers')
 assert motif.serves=='PLOT'


def test_peaks_earned_release_no_hard_quota():
 raw=dict(scope_id='e',source_fingerprint='a'*64,revision='1',mode='CURRENT',dynamic_range='Held then released',memory_review='No strong excerpt yet',delete_strongest_test='No change')
 assert review_peaks(DramaticPeakMap(**raw))['status']=='WARN'
 with pytest.raises(ValueError):HeroMoment(character='captain',action='Stand',earned_by=[],cost_or_irreversibility='None',changes_space_or_others='Crew looks',canon_refs=['s'])
 with pytest.raises(ValueError):SetPiece(key='p',scene_ids=['s'],memorable_because='Loud',pressure_ladder=['Only release'],first_reveal='None',payoff='Noise',irreversible_action='Nothing',aftermath='Same')
 with pytest.raises(ValueError):PressureRelease(starting_pressure='Danger',pressure_escalation='More',turn='Wait',aftermath='Danger')
 assert PressureRelease(starting_pressure='Danger',pressure_escalation='More',turn='Wait',aftermath='No answer',withheld_release_reason='The next scene must force choice')


@pytest.mark.parametrize('change',['unknown_beat','same_cut','model_length','long_unreviewed','hero_without_reason','incomplete_peak'])
def test_editorial_information_and_duration_guards(change):
 raw=editorial()
 if change=='unknown_beat':raw['coverage'][0]['beat_ids']=['missing']
 if change=='same_cut':raw['cuts'][0]['to_beat']='a'
 if change=='model_length':raw['coverage'][0]['duration_basis']='MODEL_MAXIMUM'
 if change=='long_unreviewed':raw['coverage'][0].update(duration=14,attention_changes=3)
 if change=='hero_without_reason':raw['coverage'][1].pop('visual_power_reason')
 if change=='incomplete_peak':raw['set_piece_coverage']={'hero':['y']}
 with pytest.raises(ValueError):EditorialRhythmPlan.model_validate(raw)


def test_single_take_can_be_long_with_staging_not_forced_four_shots():
 raw=editorial();raw['coverage'][0].update(duration=14,attention_changes=3,single_take=dict(verdict='CONDITIONAL',rationale='Three visible shifts',attention_transitions=['signal','face'],staging_solution='Actor crosses to reveal console',alternative='Separate reaction coverage'))
 assert len(EditorialRhythmPlan.model_validate(raw).coverage)==2
 with pytest.raises(ValueError):SingleTakeFeasibility(verdict='YES',rationale='Model supports it',attention_transitions=[])


@pytest.mark.parametrize('mutation',['negative','reverse','overflow','unknown','audio','canon','hash'])
def test_picture_edit_ranges_dialogue_and_frozen_canon(mutation):
 raw=picture();canon='a'*64;sources={'m':'b'*64}
 if mutation=='negative':raw['picture_edit'][0]['source_in']=-1
 if mutation=='reverse':raw['picture_edit'][0]['source_out']=0
 if mutation=='overflow':raw['picture_edit'][0]['source_out']=15
 if mutation=='unknown':raw['picture_edit'][0]['source_media']='other'
 if mutation=='audio':raw['status']='REVIEWED'
 if mutation=='canon':canon='c'*64
 if mutation=='hash':sources['m']='c'*64
 with pytest.raises(ValueError):picture_edit_handoff(PictureEditPlan.model_validate(raw),current_sources=sources,canon_fingerprint=canon)


def test_picture_edit_can_trim_native_without_render_or_canon_write():
 p=PictureEditPlan.model_validate(picture());h=picture_edit_handoff(p,current_sources={'m':'b'*64},canon_fingerprint='a'*64)
 assert not h['assemblyReady'] and not h['sourceMutationAllowed'] and p.picture_edit[0].source_out<14
 assert review_design({'identity':'PASS'})['status']=='PARTIAL'
 with pytest.raises(ValueError):review_design({'identity':'9.1'})


@pytest.mark.parametrize('kind',['FACTION_VISUAL_SYSTEM','LOCATION_DESIGN','VISUAL_MOTIF'])
@pytest.mark.asyncio
async def test_other_design_modes_use_existing_text_asset_memory(kind):
 if kind=='FACTION_VISUAL_SYSTEM':
  spec=FactionVisualSystem(faction='station crew',revision='1',shared_language='Utility',ranks=[dict(role='technician',silhouette='Loose coverall',materials='Canvas',wear='Repaired',rank_signals='Tools arranged by task')])
 elif kind=='LOCATION_DESIGN':
  spec=LocationDesignSpec(location='station',revision='1',space_purpose='Receive a signal',spatial_hierarchy='Console faces entry',entrance_exit='Single door',major_anchors=['Console'],materials='Painted steel',wear_state='Worn switches',storytelling_state='Abandoned mid-shift',foreground='Empty chair',midground='Console',background='Door')
 else:
  spec=VisualMotifSpec(motif='lamp',revision='1',physical_form='Work lamp',serves='PLOT',narrative_function='Signal occupancy',recurrence_change='Lit to dark',avoid_decoration='Only where someone works')
 c=content().model_copy(update={'creative_kind':kind,'spec':spec,'semantic_key':'production-design/station/'+kind.lower().replace('_','-')})
 c=ProductionDesignContent.model_validate(dump_contract(c));p=DramaPlugin.load(ROOT)
 a,status=await remember(p.tools,p.providers.memory.data.work.id,c)
 assert status=='CREATED' and not a.reference_media_ids and a.asset_type==AssetType.OTHER
 assert ProductionDesignContent.model_validate(a.content)==c


def test_design_core_is_generic_and_helpers_have_no_generation_dependencies():
 import ast
 core=(ROOT/'skills/production-design/SKILL.md').read_text()
 assert all(word not in core for word in ['项羽','唐朝','楚汉战争','古装','Seedance','Comfy Cloud'])
 source=(ROOT/'src/drama_plugin/production_design.py').read_text()
 imports=[n.module for n in ast.walk(ast.parse(source)) if isinstance(n,ast.ImportFrom)]
 assert all(not any(x in (name or '') for x in ['providers','hosts','tools','visual.production','audio']) for name in imports)
 assert 'create_asset' not in source and 'save_script' not in source and 'generate' not in {n.attr for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Attribute)}
