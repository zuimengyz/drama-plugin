"""Portable synthetic characters only. No project assets, prompts or media calls."""
import copy,json,os,subprocess,sys
from pathlib import Path
import pytest,yaml
from drama_plugin.contracts.base import dump_contract,sha256_canonical
from drama_plugin.contracts.character_package import CharacterPackage,CharacterPackageRef,CharacterDesignAuthorization
from drama_plugin.contracts.character_embodiment import CharacterEmbodiment
from drama_plugin.characters.authoring import create_character_version
from drama_plugin.characters.repository import CharacterRepository,manifest_digest,digest
from drama_plugin.characters.embodiment import embodiment_handoff
from character_package_fixture import make_package

DIRECTIVE=b'Create synthetic draft versions.'

def authored(repo,p,auth):
    d=dump_contract(p);m=d['manifest'];m.update(schemaVersion='character-package-v2',version='v2')
    d['provenance']['revision']='v2'
    (repo.root/'test').write_bytes(DIRECTIVE)
    d['provenance']['sourceFiles']['test']=digest(DIRECTIVE)
    source={'pointer':'/core/decisionPattern','valueHash':sha256_canonical(d['core']['decisionPattern'])}
    d['embodiment']={'depth':'LIGHTWEIGHT','rationale':'Small role with one evidenced decision habit.',
      'rules':[{'id':'wait','dimension':'posture','source':[source],
        'interpretation':['Checks carry personal responsibility rather than automatic hesitation.'],
        'observableEvidence':{'posture':['Waits until the partner can answer before committing weight to leaving.']},
        'conditions':'Only where the current screenplay leaves the decision open.'}],
      'visualTheses':[{'id':'T','statement':'Readiness leaves time for an answer.','ruleIds':['wait'],'observationTest':'Check the order of attention and weight transfer.'}],
      'counterfactual':{'substitution':'An impatient witness','nearlyInterchangeable':False,'discriminatingRuleIds':['wait'],'rationale':'The substitute departs before checking, contrary to this core.'},
      'bodyIndependence':{'removed':['armor','weapon','cape','battlefield','costume','camera'],'survivingRuleIds':['wait'],'rationale':'Timing attention and departure needs no equipment.'},
      'provenance':{'sourceCharacterPackage':'characters/synthetic/actor','sourceVersion':'v1','sourceChecksum':p.manifest.checksum,
        'sourceWork':'w','sourceRevision':'r','driverDirectiveHash':auth.directive_hash,'directiveRef':'test','host':'test',
        'createdAt':m['createdAt'],'derivedFrom':['core']}}
    return d

def ready(tmp_path):
    repo,p,ref,auth,_=make_package(tmp_path/'repo')
    d=authored(repo,p,auth)
    result=create_character_version(repo,d,authorization=auth,directive=DIRECTIVE)
    ref2=CharacterPackageRef(character_package_ref=ref['characterPackageRef'],character_package_version='v2',checksum=result.manifest.checksum)
    return repo,p,result,ref2,auth,d

def test_old_payload_and_new_reader(tmp_path):
    repo,old,new,ref,auth,d=ready(tmp_path)
    assert 'embodiment' not in dump_contract(old)
    assert repo.load_character_package(ref.character_package_ref,'v1').manifest.checksum==old.manifest.checksum
    assert new.embodiment and new.manifest.schema_version=='character-package-v2'
    view=embodiment_handoff(repo,ref,consumer='character-art',route='heroic_cinematic_cg')
    assert view['embodiment']['rules'] and 'counterfactual' not in view['embodiment']
    assert not view['artisticApproval']
    with pytest.raises(FileExistsError):create_character_version(repo,d,authorization=auth,directive=DIRECTIVE)

@pytest.mark.parametrize('consumer',['character-art','performance-casting','director','action-choreography','dramatic-performance-direction','expression'])
def test_downstream_has_only_detached_reader(tmp_path,consumer):
    repo,old,new,ref,auth,d=ready(tmp_path)
    before={str(p):p.read_bytes() for p in repo.root.rglob('*') if p.is_file()}
    view=repo.resolve_character_package(ref,consumer=consumer)
    view['embodiment']['rules'][0]['interpretation']=['Reinvented personality']
    with pytest.raises(ValueError,match='REDEFINITION'):repo.verify_downstream_embodiment(ref,view['embodiment'])
    assert before=={str(p):p.read_bytes() for p in repo.root.rglob('*') if p.is_file()}
    with pytest.raises(ValueError):CharacterDesignAuthorization(**{**dump_contract(auth),'capability':consumer})
    assert not hasattr(repo,'save')

@pytest.mark.parametrize('mutation',['hash','pointer','core','route','directive','self_source','work'])
def test_source_checks_before_write(tmp_path,mutation):
    repo,p,ref,auth,_=make_package(tmp_path/'repo');d=authored(repo,p,auth)
    e=d['embodiment']
    if mutation=='hash':e['rules'][0]['source'][0]['valueHash']='a'*64
    if mutation=='pointer':e['rules'][0]['source'][0]['pointer']='/core/missing'
    if mutation=='core':d['core']['desire']='A new desire'
    if mutation=='route':d['visualExpression']['routes']['heroic_cinematic_cg']['cameraPolicy']='Copied camera default'
    if mutation=='directive':e['provenance']['driverDirectiveHash']='a'*64
    if mutation=='self_source':e['provenance']['sourceVersion']='v2'
    if mutation=='work':e['provenance']['sourceWork']='another'
    with pytest.raises(ValueError):create_character_version(repo,d,authorization=auth,directive=DIRECTIVE)
    assert not (repo.root/ref['characterPackageRef']/'v2').exists()

@pytest.mark.parametrize('mutation',['malformed','unlisted','checksum','source_hash','nested_manifest'])
def test_file_contract_rejection(tmp_path,mutation):
    repo,old,new,ref,auth,d=ready(tmp_path);folder=repo.root/ref.character_package_ref/'v2'
    if mutation=='malformed':(folder/'embodiment.yaml').write_text('rules: [')
    if mutation=='unlisted':(folder/'unexpected.yaml').write_text('x: y')
    if mutation=='nested_manifest':
        (folder/'nested').mkdir();(folder/'nested/manifest.yaml').write_text('x: y')
    if mutation=='checksum':
        path=folder/'embodiment.yaml';path.write_text(path.read_text()+'\n# tampered\n')
    if mutation=='source_hash':
        path=folder/'embodiment.yaml';e=yaml.safe_load(path.read_text());e['rules'][0]['source'][0]['valueHash']='f'*64
        path.write_text(yaml.safe_dump(e));mp=folder/'manifest.yaml';m=yaml.safe_load(mp.read_text());m['fileChecksums']['embodiment.yaml']=digest(path.read_bytes());m['checksum']=manifest_digest(m);mp.write_text(yaml.safe_dump(m))
    with pytest.raises(ValueError):repo.load_character_package(ref.character_package_ref,'v2')

@pytest.mark.parametrize('mutation',['empty_evidence','missing_source','thesis_unknown','unknown_field','full_without_review'])
def test_malformed_embodiment(tmp_path,mutation):
    repo,p,_,auth,_=make_package(tmp_path/'repo');e=authored(repo,p,auth)['embodiment']
    if mutation=='empty_evidence':e['rules'][0]['observableEvidence']={}
    if mutation=='missing_source':e['rules'][0]['source']=[]
    if mutation=='thesis_unknown':e['visualTheses'][0]['ruleIds']=['not-authored']
    if mutation=='unknown_field':e['providerPrompt']='generic hero'
    if mutation=='full_without_review':e['depth']='FULL'
    with pytest.raises(ValueError):CharacterEmbodiment.model_validate(e)


def test_generic_counterfactual_and_body_dependent_fail(tmp_path):
    repo,p,_,auth,_=make_package(tmp_path/'repo');d=authored(repo,p,auth);e=d['embodiment']
    e['rules'][0]['interpretation']=['Strong dominant leader']
    e['rules'][0]['observableEvidence']={'posture':['Stands confidently.']}
    e['counterfactual'].update(nearlyInterchangeable=True,rationale='This can transfer unchanged to almost any dominant leader.')
    assert 'DISTINCTIVENESS_INSUFFICIENT' in CharacterEmbodiment.model_validate(e).review_findings()
    with pytest.raises(ValueError,match='DISTINCTIVENESS_INSUFFICIENT'):create_character_version(repo,d,authorization=auth,directive=DIRECTIVE)
    e['counterfactual']['nearlyInterchangeable']=False;e['rules'][0]['equipmentRequired']=True
    assert 'EMBODIMENT_FAILS_BODY_INDEPENDENCE' in CharacterEmbodiment.model_validate(e).review_findings()


def test_same_archetype_different_source_produces_different_allowed_logic(tmp_path):
    observations=[]
    for n,decision,observation in [('a','Checks before committing','Waits for partner before shifting weight.'),('b','Commits then asks others to respond','Shifts weight into the choice before turning to partner.')]:
        repo,p,_,auth,_=make_package(tmp_path/n)
        # Both are witnesses. Create second literary identity as an independent fixture before embodiment.
        if n=='b':
            data=dump_contract(p);data['manifest']['version']='v9';data['provenance']['revision']='v9';data['core']['decisionPattern']=decision
            p=create_character_version(repo,data,authorization=auth,directive=DIRECTIVE)
        d=authored(repo,p,auth);d['embodiment']['provenance']['sourceVersion']=p.manifest.version
        d['embodiment']['rules'][0]['observableEvidence']={'posture':[observation]}
        result=create_character_version(repo,d,authorization=auth,directive=DIRECTIVE)
        assert result.core.dramatic_role=='Witness'
        observations.append(result.embodiment.rules[0].observable_evidence.posture)
    assert observations[0]!=observations[1]

@pytest.mark.parametrize('depth',['NONE','ARCHETYPE'])
def test_explicit_nonfull_depth_does_not_invent(tmp_path,depth):
    repo,p,_,auth,_=make_package(tmp_path/'repo');d=authored(repo,p,auth)
    for k in ('rules','visualTheses'):d['embodiment'][k]=[]
    d['embodiment'].update(depth=depth,counterfactual=None,bodyIndependence=None)
    p=create_character_version(repo,d,authorization=auth,directive=DIRECTIVE)
    assert not p.embodiment.rules


def test_fresh_process_no_chat_or_images(tmp_path):
    repo,old,new,ref,_,_=ready(tmp_path)
    result=subprocess.run([sys.executable,'-m','drama_plugin.characters',ref.character_package_ref,'v2','--root',str(repo.root),'--checksum',ref.checksum],cwd=tmp_path,env={'PATH':os.environ['PATH'],'PYTHONPATH':str(Path(__file__).resolve().parents[1]/'src')},capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)['embodiment']['rules']


def test_generic_assets_and_casting_pointer_boundary():
    root=Path(__file__).resolve().parents[1]
    files=[*list((root/'skills/character-embodiment').rglob('*')),root/'docs/character-embodiment.md',root/'src/drama_plugin/contracts/character_embodiment.py',root/'src/drama_plugin/characters/embodiment.py']
    for p in files:
        if p.is_file():assert not any(x in p.read_text() for x in ['xiang_yu','项羽','gaixia','韩信'])
    from drama_plugin.characters.casting import pointer_value
    for path in ['/embodiment','/embodiment/contrasts/0','/embodiment/counterfactual']:
        with pytest.raises(ValueError,match='MUST_NOT_ENTER_PROMPT'):pointer_value({},path)


def test_casting_requires_embodiment_source_map_without_generating(tmp_path):
    from drama_plugin.characters.casting import PackageCastingProjection,compile_package_casting
    repo,p,_,auth,_=make_package(tmp_path/'repo');d=authored(repo,p,auth)
    d['manifest']['status']='VISUAL_TESTING'
    new=create_character_version(repo,d,authorization=auth,directive=DIRECTIVE)
    sections=['core','dramaticIdentity','visualExpression','actionSignature','antiDrift']
    data={'characterPackage':{'characterPackageRef':'characters/synthetic/actor','characterPackageVersion':'v2','checksum':new.manifest.checksum},'route':'heroic_cinematic_cg','castingMode':'HERO_CASTING','framing':'FULL_BODY','scopeText':'Synthetic offline projection','directiveRef':str(repo.root/'test'),'directiveHash':digest(DIRECTIVE),'paragraphs':[{'key':s,'text':'Synthetic '+s,'packagePointers':['/'+s],'interpretation':'VISUAL_INTERPRETATION_NOT_NEW_CORE'} for s in sections]}
    with pytest.raises(ValueError,match='EMBODIMENT_SOURCE_MAP_REQUIRED'):compile_package_casting(repo,PackageCastingProjection.model_validate(data))
    data['paragraphs'].append({'key':'existence','text':'Synthetic existence logic','packagePointers':['/embodiment/rules/0'],'interpretation':'VISUAL_INTERPRETATION_NOT_NEW_CORE'})
    brief=compile_package_casting(repo,PackageCastingProjection.model_validate(data))
    assert brief['status']=='DESIGN_ONLY'
    assert brief['sourceTrace']['paragraphs'][-1]['sources'][0]['sourceValue']['id']=='wait'
