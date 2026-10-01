from copy import deepcopy
from types import SimpleNamespace
import pytest
from drama_plugin.contracts.creation import Work
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.hosts.route_production import persist_stage
from drama_plugin.hosts.http_video import VideoProviderHost
from drama_plugin.exceptions import RemoteServiceError


def work():
 stage={'stage':{'id':'S'},'attempts':[],'frames':{},'plan_fingerprint':fp({}),'production_route':{}}
 return Work(id='w',title='w',version=180,content={'productionStage':stage,'productionRoute':{},'history':{'credits':None}})


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['normal','ack','no_commit','partial','later_version','conflict','late_commit','read_error'])
async def test_one_patch_exact_commit_only(mode,monkeypatch):
 w=work();state=deepcopy(w.content['productionStage']);state['pause']='WAIT';calls=[]
 class Memory:
  current=w.model_copy(deep=True);reads=0
  async def patch_work(self,wid,v,changes):
   calls.append(v)
   if mode not in ('no_commit','conflict'):
    self.current=w.model_copy(update={'version':v+1,'content':{**w.content,**changes}})
   if mode=='partial':self.current.content={**self.current.content,'unrelated':'changed'}
   if mode=='later_version':self.current.version+=1
   if mode=='conflict':raise RemoteServiceError('stale',error_code='CONFLICT')
   if mode not in ('normal','read_error'):raise OSError('lost ACK')
  async def get_work(self,wid):
   self.reads+=1
   if mode=='read_error' and self.reads==1:raise OSError('read ACK lost')
   return w if mode=='late_commit' and self.reads==1 else self.current
 async def no_sleep(_):pass
 monkeypatch.setattr('asyncio.sleep',no_sleep)
 mem=Memory()
 if mode in ('normal','ack','late_commit','read_error'):
  result=await persist_stage(mem,w,state)
  assert result['persistenceStatus']==('COMMIT_CONFIRMED' if mode in ('normal','read_error') else 'ACK_LOST_BUT_COMMIT_CONFIRMED')
  assert mem.current.content['history']==w.content['history']
 else:
  with pytest.raises(Exception):await persist_stage(mem,w,state)
 assert calls==[180]


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['normal','job','version','request','receipt','marker'])
@pytest.mark.usefixtures("legacy_contract_admission")
async def test_dispatch_boundary_never_reclaims_or_reposts(tmp_path,mode):
 w=work();request={'exact':'request'}
 a={'attempt_id':'a','status':'UNKNOWN','submission_started':True,'job_id':None,'request':request,'request_fingerprint':fp(request),'reserved_credits':13}
 w.content['productionStage']['attempts']=[a];expected=w.model_copy(deep=True)
 if mode=='job':a['job_id']='existing'
 if mode=='version':w.version+=1
 if mode=='request':a['request']={'changed':True}
 class Memory:
  async def get_work(self,_):return w
  async def patch_work(self,*args):raise AssertionError('Must not claim or reserve again')
 class Provider:
  calls=0
  async def create_task(self,*args,**kwargs):
   self.calls+=1
   return SimpleNamespace(durable=lambda:{'providerTaskId':'job'})
 host=VideoProviderHost(Memory(),None,None,tmp_path,configuration={})
 async def record(*args):pass
 host._record=record
 if mode in ('receipt','marker'):(tmp_path/('a.receipt.json' if mode=='receipt' else 'a.dispatch.json')).write_text('{}')
 p=Provider()
 if mode=='normal':
  await host._dispatch_claimed('w',a,p,None,expected)
  assert p.calls==1 and a['reserved_credits']==13
  with pytest.raises(ValueError):await host._dispatch_claimed('w',a,p,None,expected)
 else:
  with pytest.raises((ValueError,FileExistsError)):await host._dispatch_claimed('w',a,p,None,expected)
  assert p.calls==0


def test_actual_video_probe_retains_dimensions_and_fps(tmp_path):
 import shutil,subprocess
 from drama_plugin.audio.host_media import probe_media
 if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):pytest.skip('ffmpeg required')
 path=tmp_path/'probe.mp4'
 subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=size=128x72:rate=24','-t','0.2','-c:v','mpeg4',str(path)],check=True)
 stream=next(s for s in probe_media(path).streams if s['codec_type']=='video')
 assert (stream['width'],stream['height'],stream['avg_frame_rate'])==(128,72,'24/1')
