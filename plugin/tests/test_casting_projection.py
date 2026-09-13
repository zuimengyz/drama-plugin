from copy import deepcopy
import pytest
from pydantic import ValidationError
from test_production_design import content
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.production_design import CastingBrief,CastingReconciliation,CastingTestConditions
from drama_plugin.production_design import design_handoff,casting_briefs
from drama_plugin.hosts.casting_projection import seedream_casting_projection,audit_casting_batch,costume_fit_eligible

def batch():
 r=CastingReconciliation(request_ref='User reconciliation',population_direction='Chinese / East Asian male',apparent_age_min=27,apparent_age_max=34,hair='Black long hair in Chinese bun',beard='Minimal stubble',face=['Firm jaw'],body=['Visible neck above collar','Long limbs, broad back, narrow waist'],authority='Quiet focused gaze',avoid=['Western medieval knight','Modern short haircut'])
 c=CastingTestConditions(background='Neutral wall',lighting='Soft even light',camera='Eye level natural perspective',framing='Full body 90 percent frame height',orientation='Front',posture='Arms relaxed',clothing='Same unarmored charcoal robe')
 b=casting_briefs(design_handoff(content(),consumer='asset-resolution'),reconciliation=r,conditions=c,variations={k:'Distinct bone structure '+k for k in 'ABCD'})
 return b,[seedream_casting_projection(x,seed=i+1) for i,x in enumerate(b)]

def test_population_age_hair_body_and_conditions_survive_projection():
 b,p=batch();assert audit_casting_batch(b,p)['status']=='PASS'
 for item in p:
  prompt=item['input_overrides']['3']['prompt']
  for term in ['Chinese / East Asian','27–34','Chinese bun','Visible neck','Long limbs','Same unarmored','Eye level','90 percent','Western medieval','Modern short']:assert term in prompt
  assert not any('image_' in key for key in item['input_overrides']['3'])

@pytest.mark.parametrize('case',['population','age','hair','body','costume','camera','reference','desktop','duplicate','source','count'])
def test_audit_blocks_projection_drift_and_unfair_comparison(case):
 b,p=batch()
 if case in {'population','age','hair','body','costume','camera'}:p[0]['input_overrides']['3']['prompt']='omitted '+case
 if case=='reference':p[0]['input_overrides']['3']['model.images.image_1']='old.png'
 if case=='desktop':p[0]['tool']='desktop'
 if case=='duplicate':b[1].variation=b[0].variation
 if case=='source':b[0].source_content.spec.silhouette='changed'
 if case=='count':p.pop()
 with pytest.raises(ValueError):audit_casting_batch(b,p)

def test_conditions_must_be_equal_even_if_both_projections_valid():
 b,p=batch();b[0].conditions=b[0].conditions.model_copy(update={'camera':'Low angle'})
 p[0]=seedream_casting_projection(b[0],seed=1)
 with pytest.raises(ValueError,match='Unequal'):audit_casting_batch(b,p)

@pytest.mark.parametrize('field,value',[('status','APPROVED'),('formalPromotionAllowed',True)])
def test_casting_brief_cannot_authorize_formal_replacement(field,value):
 b,_=batch();raw=dump_contract(b[0]);raw[field]=value
 with pytest.raises(ValidationError):CastingBrief.model_validate(raw)

@pytest.mark.parametrize('field',['oldFaceAuthority','oldBodyAuthority'])
def test_old_reference_cannot_gain_authority(field):
 b,_=batch();raw=dump_contract(b[0].reconciliation);raw[field]=True
 with pytest.raises(ValidationError):CastingReconciliation.model_validate(raw)

def test_source_handoff_tampering_and_duplicate_directions():
 b,_=batch();h=design_handoff(content(),consumer='asset-resolution');h['content']['spec']['hair']='tampered'
 with pytest.raises(ValueError):casting_briefs(h,reconciliation=b[0].reconciliation,conditions=b[0].conditions,variations={'A':'a','B':'b'})
 h=design_handoff(content(),consumer='asset-resolution')
 with pytest.raises(ValueError):casting_briefs(h,reconciliation=b[0].reconciliation,conditions=b[0].conditions,variations={'A':'same','B':'same'})

@pytest.mark.parametrize('reviews,eligible',[({'A':'PASS','B':'PASS'},True),({'A':'SHORTLIST','B':'SHORTLIST'},True),({'A':'PASS','B':'SHORTLIST'},False),({'A':'SHORTLIST','B':'REJECT'},False),({'A':'REJECT','B':'REJECT'},False)])
def test_costume_gate_does_not_turn_one_marginal_candidate_into_fit(reviews,eligible):
 assert costume_fit_eligible(reviews)==eligible
