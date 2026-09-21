from pathlib import Path
import copy
import pytest
from pydantic import ValidationError
from character_package_fixture import make_package
from drama_plugin.characters.casting import PackageCastingProjection, compile_package_casting, executable_package_casting
from drama_plugin.characters.source_guard import package_source_guard
from drama_plugin.characters.repository import digest
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.creation import Work

def case(tmp_path,status='VISUAL_TESTING'):
 repo,p,ref,_,_=make_package(tmp_path/'repo',status=status)
 directive=tmp_path/'directive.txt';directive.write_text('One package-only full-body visual test')
 sections=['core','dramaticIdentity','visualExpression','actionSignature','antiDrift']
 projection=PackageCastingProjection.model_validate({'characterPackage':ref,'route':'heroic_cinematic_cg','castingMode':'HERO_CASTING','framing':'FULL_BODY','scopeText':'One full-body CG character.','directiveRef':str(directive),'directiveHash':digest(directive.read_bytes()),'paragraphs':[{'key':s,'text':'Visual interpretation of '+s,'packagePointers':['/'+s],'interpretation':'VISUAL_INTERPRETATION_NOT_NEW_CORE'} for s in sections]})
 return repo,p,projection

def test_compile_source_values_are_actual_package(tmp_path):
 repo,p,projection=case(tmp_path);brief=compile_package_casting(repo,projection)
 assert brief['sourceTrace']['paragraphs'][0]['sources'][0]['sourceValue']==dump_contract(p.core)
 assert brief['sourceTrace']['legacyProfileInputs']==[] and brief['maxOutputs']==1
 assert brief['status']=='DESIGN_ONLY'

@pytest.mark.parametrize('change',['draft','missing','pointer','incomplete','legacy','directive','route'])
def test_source_fail_closed(tmp_path,change):
 repo,p,projection=case(tmp_path,status='DRAFT' if change=='draft' else 'VISUAL_TESTING')
 data=dump_contract(projection)
 if change=='missing':data['characterPackage']['characterPackageVersion']='v9'
 if change=='pointer':data['paragraphs'][0]['packagePointers']=['/provenance/userFeedback']
 if change=='incomplete':data['paragraphs']=data['paragraphs'][:-1]
 if change=='legacy':data['instanceProfile']={'body':'old'}
 if change=='directive':Path(projection.directive_ref).write_text('different')
 if change=='route':data['route']='live_action_realist'
 with pytest.raises(ValueError):compile_package_casting(repo,PackageCastingProjection.model_validate(data))

def test_execution_pins_and_consumed_authorization(tmp_path):
 repo,p,projection=case(tmp_path);brief=compile_package_casting(repo,projection)
 auth={'authorizationId':'test','authority':'USER_EXPLICIT_SINGLE_CANDIDATE','directiveRef':projection.directive_ref,'directiveHash':projection.directive_hash,'workId':'w','workRevision':'r','character':'actor','purpose':'CHARACTER_FULL_BODY_CASTING','maxOutputs':1,'stopAfterFirstResult':True,'inputsFingerprint':brief['inputsFingerprint'],'status':'AUTHORIZED'}
 w=Work(id='w',title='test',content={'approval':{'status':'APPROVED'},'revisionId':'r','visualRoute':'stylized_cinematic_cg','visualLanguage':'HEROIC_CINEMATIC_CG','characterPackageRoster':{'sourceRevision':'r','characters':[{'characterId':'actor','name':'Synthetic actor','package':dump_contract(projection.character_package)}]},'characterCastingAuthorizations':{'test':auth}})
 assert executable_package_casting(w,repo,projection,'test')['status']=='EXECUTABLE_SINGLE_CANDIDATE'
 w.content['characterCastingAuthorizations']['test']['status']='RESERVED'
 with pytest.raises(ValueError,match='CONSUMED'):executable_package_casting(w,repo,projection,'test')

def test_read_guard_blocks_archive_even_through_symlink(tmp_path):
 legacy=tmp_path/'profiles/instances';legacy.mkdir(parents=True);p=legacy/'old.json';p.write_text('old')
 link=tmp_path/'alias.json';link.symlink_to(p)
 with package_source_guard(denied_roots=[legacy]) as events:
  with pytest.raises(PermissionError,match='FAILED_SOURCE_OF_TRUTH'):link.read_text()
 assert events[-1]['allowed'] is False

def test_guard_blocks_other_task_artifacts(tmp_path):
 artifacts=tmp_path/'artifacts';task=artifacts/'current';task.mkdir(parents=True);old=artifacts/'old.json';old.write_text('old')
 with package_source_guard(denied_roots=[],artifact_root=artifacts,task_root=task):
  with pytest.raises(PermissionError,match='OLD_ARTIFACT'):old.read_text()
