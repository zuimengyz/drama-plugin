from copy import deepcopy
import pytest
from pydantic import ValidationError
from drama_plugin.contracts.base import dump_contract,sha256_canonical
from drama_plugin.contracts.asset import Asset,AssetType
from drama_plugin.contracts.visual_route import ProjectVisualRoutes,SequenceVisualRoute,RouteStyleContract,RouteContext,RouteCastingContext
from drama_plugin.visual_route import resolve_visual_route,resolved_context,bind_route_artifact,verify_route_artifact,check_sequence_routes,discover_route_assets,search_route_assets
from drama_plugin.casting_discriminants import compile_visual_discriminants,verify_submitted_projection
from test_casting_reconciliation import reconciled,reference

CG='stylized_cinematic_cg';REAL='live_action_realist'

def context(route=CG):
 return RouteContext(project=ProjectVisualRoutes(work_id='w',revision='1',visual_route=REAL,enabled_routes=(REAL,CG)),
  sequence=SequenceVisualRoute(work_id='w',sequence_key='excerpt',visual_route=route,override_reason='Separate design study'),
  style=RouteStyleContract(visual_route=route,revision='1',medium='DESIGNED_CG' if route==CG else 'PHOTOGRAPHIC',
   rendering='Designed volumetric surfaces' if route==CG else 'Photographic surfaces',casting_criteria=['Role readable under motion'],
   shape_language='Readable differentiated planes',material_palette='Muted cloth and worn wood',camera_grammar='Information motivates camera',
   performance_grammar='Listen before redirecting body',historical_boundary='Preserve declared period and source',forbidden_drifts=['No arbitrary costume additions']))


def test_default_and_override_are_project_scoped_without_global_mutation():
 a=ProjectVisualRoutes(work_id='a',revision='1',visual_route=REAL,enabled_routes=(REAL,));b=ProjectVisualRoutes(work_id='b',revision='1',visual_route=REAL,enabled_routes=(REAL,))
 assert resolve_visual_route(a,SequenceVisualRoute(work_id='a',sequence_key='s')).visual_route==REAL
 a.enabled_routes=(REAL,CG);a.visual_route=CG
 assert b.visual_route==REAL and b.enabled_routes==(REAL,)
 with pytest.raises(ValueError,match='WORK_MISMATCH'):resolve_visual_route(a,SequenceVisualRoute(work_id='b',sequence_key='s'))
 with pytest.raises(ValueError,match='NOT_ENABLED'):resolve_visual_route(b,SequenceVisualRoute(work_id='b',sequence_key='s',visual_route=CG,override_reason='study'))
 with pytest.raises(ValidationError):SequenceVisualRoute(work_id='a',sequence_key='s',visual_route=CG)


def test_style_cannot_contradict_resolved_route():
 c=context();c.style=context(REAL).style
 with pytest.raises(ValueError,match='STYLE_MISMATCH'):resolved_context(c)
 d=dump_contract(context().style);d['medium']='PHOTOGRAPHIC'
 with pytest.raises(ValidationError):RouteStyleContract.model_validate(d)


@pytest.mark.parametrize('responsibility',['CASTING','ART_DIRECTION','CAMERA','PERFORMANCE','AUTHORIAL_PRESENTATION'])
def test_approved_payload_is_preserved_and_approval_never_transfers(responsibility):
 payload={'status':'APPROVED','canon':['unchanged'],'approvalEvidence':'user original revision'};old=deepcopy(payload);c=context()
 packet=bind_route_artifact(payload,c,responsibility=responsibility)
 assert payload==old and packet['sourceFingerprint']==sha256_canonical(old)
 assert packet['sourcePayload']==old and not packet['approvalTransferAllowed'] and not packet['productionAllowed']
 payload['canon'].append('caller mutation');assert packet['sourcePayload']==old
 verify_route_artifact(packet,c)
 c.project.revision='2'
 with pytest.raises(ValueError,match='STALE'):verify_route_artifact(packet,c)


def test_mixed_routes_or_other_sequence_cannot_form_one_clip():
 c=context();p=bind_route_artifact({'action':'take rope'},c,responsibility='CAMERA')
 check_sequence_routes([p],c)
 with pytest.raises(ValueError):check_sequence_routes([p],context(REAL))
 changed=c.model_copy(deep=True);changed.sequence.sequence_key='other'
 with pytest.raises(ValueError):check_sequence_routes([p],changed)
 altered=deepcopy(p);altered['sourcePayload']['action']='draw sword'
 with pytest.raises(ValueError):verify_route_artifact(altered,c)


def test_compiler_projects_opt_in_style_without_changing_legacy_output():
 p,v=reconciled();old=compile_visual_discriminants(p,v,'n','FACE');c=context()
 rc=RouteCastingContext(**dump_contract(c),characterIdentity=p.identity,profileFingerprint=old['profileFingerprint'],planFingerprint=old['planFingerprint'])
 new=compile_visual_discriminants(p,v,'n','FACE',route_context=rc)
 assert new['visualRoute']==CG and 'Designed volumetric surfaces' in new['prompt']
 assert old['trace']==new['trace']
 assert all(r['line'] in new['prompt'] for r in old['trace'])
 assert old['prompt'].startswith('Live-action human performer.')
 assert new['prompt'].startswith('Feature-film CG character.')
 assert new['promptFingerprint']!=old['promptFingerprint'] and not new['approvalEligible']
 verify_submitted_projection(new,new['prompt'])
 assert compile_visual_discriminants(p,v,'n','FACE')==old and 'visualRoute' not in old
 rc.character_identity='another-role'
 with pytest.raises(ValueError,match='SOURCE_MISMATCH'):compile_visual_discriminants(p,v,'n','FACE',route_context=rc)


def test_stale_plan_context_and_reference_name_in_route_text_block():
 p,v=reconciled();p.archetype_references=(reference(p.identity),);v.profile_fingerprint=sha256_canonical(p)
 old=compile_visual_discriminants(p,v,'n','FACE');rc=RouteCastingContext(**dump_contract(context()),characterIdentity=p.identity,profileFingerprint=old['profileFingerprint'],planFingerprint=old['planFingerprint'])
 rc.plan_fingerprint='a'*64
 with pytest.raises(ValueError,match='SOURCE_MISMATCH'):compile_visual_discriminants(p,v,'n','FACE',route_context=rc)
 rc.plan_fingerprint=old['planFingerprint'];rc.style.rendering='Copy Lu Bu'
 with pytest.raises(ValueError,match='PROPER_NAME'):compile_visual_discriminants(p,v,'n','FACE',route_context=rc)


def asset(key,route=None,work='w'):
 return Asset(id=key,work_id=work,asset_type=AssetType.CHARACTER,name=key,content={'approved':True,**({'visualRoute':route} if route else {})},reference_media_ids=['m-'+key])


def test_asset_discovery_no_cross_work_route_or_implicit_legacy_cg():
 assets=[asset('cg',CG),asset('real',REAL),asset('old'),asset('foreign',CG,'other')];before=[dump_contract(a) for a in assets]
 found=discover_route_assets(assets,work_id='w',visual_route=CG)
 assert [x['assetId'] for x in found['matches']]==['cg']
 assert [x['assetId'] for x in found['legacyForReview']]==['old']
 assert all(not x['approvalInherited'] for x in found['matches'])
 assert [dump_contract(a) for a in assets]==before


@pytest.mark.asyncio
async def test_search_uses_only_existing_read_tool():
 class ReadOnly:
  calls=[]
  async def invoke(self,name,**kwargs):
   assert name=='asset.search_assets';self.calls.append((name,kwargs));return [asset('cg',CG),asset('real',REAL)]
 tools=ReadOnly();out=await search_route_assets(tools,work_id='w',visual_route=CG,query='commander')
 assert len(out['matches'])==1 and len(tools.calls)==1 and out['mutations']==0
