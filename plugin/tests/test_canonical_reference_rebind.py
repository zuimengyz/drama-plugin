from copy import deepcopy
from pathlib import Path
import json
import pytest
from drama_plugin.contracts.creation import Work
from drama_plugin.work_patch import validate_reference_rebinding

def fixture():
 raw=json.loads((Path(__file__).parent/'fixtures/canonical-reference-rebind.json').read_text())
 w=Work(id=raw['workId'],title='fixture',content={'continuityPacks':{'A5-L1-S01':raw['oldPack']},'productionStage':raw['stage']})
 return w,{'A5-L1-S01':raw['newPack']}

def test_reference_only_rebind_preserves_old():
 w,p=fixture();before=deepcopy(w.content)
 validate_reference_rebinding(w,p)
 assert w.content==before

@pytest.mark.parametrize('case',['creative','work','hash','review','failed','count','duties'])
def test_rebinding_negative(case):
 w,p=fixture();pack=p['A5-L1-S01'];ref=pack['references'][0]
 if case=='creative':pack['lighting']='different creative intent'
 if case=='work':pack['workId']='other'
 if case=='hash':ref['contentHash']='a'*64
 if case=='review':ref['reviewRef']='forged'
 if case=='failed':w.content['productionStage']['attempts'][0]['review_status']='FAIL'
 if case=='count':pack['references']=[];pack['requiredReferenceIds']=[]
 if case=='duties':ref['semantics']=['motion']
 with pytest.raises(ValueError):validate_reference_rebinding(w,p)

@pytest.mark.asyncio
async def test_formal_canon_old_pack_rejects_new_reference_then_rebound_passes():
 from types import SimpleNamespace
 from drama_plugin.contracts.video import ContinuityPack
 from drama_plugin.hosts.http_video import VideoProviderHost
 w,p=fixture()
 class Memory:
  async def get_work(self,work_id):return w
 host=object.__new__(VideoProviderHost);host.memory=Memory()
 req=SimpleNamespace(continuity=ContinuityPack.model_validate(p['A5-L1-S01']))
 with pytest.raises(ValueError,match='CANONICAL_CONTINUITY_PACK_MISSING_OR_CHANGED'):
  await host._validate_canon(w.id,req)
 w.content['continuityPacks']=p
 await host._validate_canon(w.id,req)
