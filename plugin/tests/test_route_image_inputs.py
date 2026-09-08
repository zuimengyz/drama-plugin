"""OFFLINE image graph and identity contract checks; no provider call."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from test_visual_first_pass import material
from drama_plugin.visual.frame_request import FrameSpec,Template,compile_frame,verify_compiled
from drama_plugin.contracts.base import sha256_canonical as fp

def image_input(tmp_path, shared=False):
 s,_=material(tmp_path);data=s.model_dump();data.update(props=[],references=[],reference_lock={},identity_bootstrap='OFFLINE initial identities')
 api={'1':{'class_type':'Flux2ImageNode','inputs':{'prompt':'OFFLINE','model':'Flux.2 [pro]','model.width':1536,'model.height':1024,'seed':1}},
      'output':{'class_type':'SaveImage','inputs':{'images':['1',0],'filename_prefix':'OFFLINE'}}}
 graph={'nodes':[{'id':'1','type':'Flux2ImageNode','inputs':[],'widgets_values_named':dict(api['1']['inputs'])}],'links':[]}
 slots=[]
 if shared:
  ref=s.references[0].model_dump();ref.update(kind='SCENE',entity_key='ensemble')
  data.update(references=[ref],reference_lock=s.reference_lock,identity_bootstrap=None,reference_members={'ensemble':['w','o']})
  slots=['ref1'];api['ref1']={'class_type':'LoadImage','inputs':{'image':'placeholder'}};api['1']['inputs']['model.images.image_1']=['ref1',0]
  graph['nodes'][0]['inputs']=[{'name':'model.images.image_1','link':1}]
  graph['nodes'].append({'id':'ref1','type':'LoadImage'});graph['links']=[[1,'ref1',0,'1',0,'IMAGE']]
 path=tmp_path/'api-proof.json';path.write_text(json.dumps(graph))
 t=Template(name='OFFLINE',model='Flux.2 [pro]',evidence='OFFLINE',graph_hash=fp(graph),graph_path=str(path),image_slots=slots,prompt_node='1',output_size=[1536,1024],supported_types=['PERSON_PROP'],api_workflow=api)
 return FrameSpec.model_validate(data),t

def test_explicit_identity_bootstrap_compiles_one_paid_node(tmp_path):
 s,t=image_input(tmp_path);d=compile_frame(s,t);verify_compiled(d)
 assert d['request']['tool']=='submit_workflow' and len(d['request']['workflow'])==2
 assert 'INITIAL IDENTITY CREATION' in d['request']['workflow']['1']['inputs']['prompt']
 with pytest.raises(ValueError,match='MISSING_STABLE_REFERENCE'):compile_frame(s.model_copy(update={'identity_bootstrap':None}),t)

def test_shared_reference_keeps_two_named_actor_bindings(tmp_path):
 s,t=image_input(tmp_path,True);d=compile_frame(s,t);verify_compiled(d)
 assert len(d['spec']['references'])==1 and 'w, o' in d['request']['workflow']['1']['inputs']['prompt']
 with pytest.raises(ValueError,match='MISSING_STABLE_REFERENCE'):compile_frame(s.model_copy(update={'reference_members':{}}),t)

@pytest.mark.parametrize('mutation',['extra_paid','dimensions','wiring'])
def test_api_graph_cannot_hide_extra_work_or_replace_refs(tmp_path,mutation):
 s,t=image_input(tmp_path,True);api=deepcopy(t.api_workflow)
 if mutation=='extra_paid':api['extra']={'class_type':'Flux2ImageNode','inputs':{}}
 if mutation=='dimensions':api['1']['inputs']['model.width']=1024
 if mutation=='wiring':api['1']['inputs']['model.images.image_1']=['other',0]
 with pytest.raises(ValueError):compile_frame(s,t.model_copy(update={'api_workflow':api}))
