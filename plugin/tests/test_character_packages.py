import copy,json,subprocess,sys,os
from pathlib import Path
import pytest,yaml
from pydantic import ValidationError
from drama_plugin.characters.repository import CharacterRepository,CharacterPackageError,resolve_root,CONSUMERS
from drama_plugin.characters.authoring import create_character_version
from drama_plugin.characters.screenplay import approved_screenplay
from drama_plugin.contracts.character_package import CharacterPackageRef,VisualExpression,CharacterCore
from drama_plugin.contracts.base import dump_contract
from drama_plugin.characters.consumption import require_character_context
from character_package_fixture import make_package


def test_external_root_and_independent_git(tmp_path):
    source=tmp_path/'plugin';(source/'.git').mkdir(parents=True)
    with pytest.raises(ValueError,match='OUTSIDE_PLUGIN'):resolve_root(source/'assets',plugin_root=source)
    with pytest.raises(ValueError,match='ABSOLUTE'):resolve_root('relative')
    link=tmp_path/'link';link.symlink_to(source,target_is_directory=True)
    with pytest.raises(ValueError,match='OUTSIDE_PLUGIN'):resolve_root(link/'assets',plugin_root=source)
    external=tmp_path/'private';(external/'.git').mkdir(parents=True)
    assert resolve_root(external,plugin_root=source)==external
    assert not resolve_root().is_relative_to(Path(__file__).resolve().parents[2])


def test_versions_checksum_missing_and_immutable(tmp_path):
    repo,p,ref,auth,data=make_package(tmp_path/'repo')
    _,v2,ref2,_,_=make_package(repo.root,version='v2')
    assert repo.load_character_package(ref['characterPackageRef'],'v1').manifest.checksum==ref['checksum']
    assert v2.manifest.version=='v2' and ref2['checksum']!=ref['checksum']
    with pytest.raises(FileExistsError):create_character_version(repo,data,authorization=auth,directive=b'Create synthetic draft versions.')
    with pytest.raises(ValueError,match='MISSING'):repo.load_character_package(ref['characterPackageRef'],'v3')
    with pytest.raises(ValidationError):repo.load_character_package(ref['characterPackageRef'],'latest')
    with pytest.raises(ValueError,match='CHECKSUM'):repo.load_character_package(ref['characterPackageRef'],'v1',checksum='a'*64)
    with pytest.raises(ValueError,match='AUTHORIZATION'):create_character_version(repo,data,authorization=auth,directive=b'not authorized')

@pytest.mark.parametrize('case',['missing','malformed','duplicate','tampered','escape','unmanifested','source','secret','signed'])
def test_corrupt_package_rejected(tmp_path,case):
    repo,p,ref,_,_=make_package(tmp_path/'repo');folder=repo.root/ref['characterPackageRef']/'v1'
    if case=='missing':(folder/'core.yaml').unlink()
    if case=='malformed':(folder/'core.yaml').write_text('identity: [')
    if case=='duplicate':(folder/'core.yaml').write_text('identity: one\nidentity: two\n')
    if case=='tampered':(folder/'core.yaml').write_text((folder/'core.yaml').read_text().replace('Midlife','Youth'))
    if case=='escape':
        outside=tmp_path/'outside';outside.write_text((folder/'core.yaml').read_text());(folder/'core.yaml').unlink();(folder/'core.yaml').symlink_to(outside)
    if case=='unmanifested':(folder/'unlisted.txt').write_text('extra')
    if case=='source':(repo.root/'source.md').write_text('changed script')
    if case in {'secret','signed'}:
        v=json.loads((folder/'provenance.json').read_text());v['userFeedback']=[{'apiKey':'redacted'}] if case=='secret' else [{'url':'https://example.test/a?X-Amz-Signature=redacted'}];(folder/'provenance.json').write_text(json.dumps(v))
    with pytest.raises(ValueError):repo.load_character_package(ref['characterPackageRef'],'v1')

@pytest.mark.parametrize('consumer',sorted(CONSUMERS))
def test_readonly_ownership(tmp_path,consumer):
    repo,p,ref,_,_=make_package(tmp_path/'repo');reference=CharacterPackageRef.model_validate(ref)
    before={str(x):x.read_bytes() for x in repo.root.rglob('*') if x.is_file()}
    view=repo.resolve_character_package(reference,consumer=consumer)
    view['core']['identity']='unauthorized new core'
    with pytest.raises(ValueError,match='REDEFINITION'):repo.verify_downstream_core(reference,view['core'])
    assert repo.load_character_package(ref['characterPackageRef'],'v1').core.identity=='Synthetic actor'
    assert before=={str(x):x.read_bytes() for x in repo.root.rglob('*') if x.is_file()}
    assert not hasattr(repo,'save') and not hasattr(repo,'create_character_version')


def test_route_and_status_gates(tmp_path,monkeypatch):
    repo,p,ref,_,_=make_package(tmp_path/'repo');reference=CharacterPackageRef.model_validate(ref)
    for purpose in ['CASTING','PRODUCTION']:
        with pytest.raises(ValueError,match='NOT_READY'):repo.resolve_character_package(reference,consumer='performance-casting',purpose=purpose)
    with pytest.raises(ValueError,match='NOT_AUTHORED'):repo.resolve_character_package(reference,consumer='expression',route='live_action_realist')
    cg=dump_contract(p.visual_expression)['routes']['heroic_cinematic_cg']
    live={**cg,'visualRoute':'live_action_realist','visualLanguage':'LIVE_ACTION_REALIST','proportionPolicy':'REAL_HUMAN','performancePolicy':'HUMAN_PERFORMABLE','equipmentPolicy':'WEARABLE_EXECUTABLE'}
    both=VisualExpression.model_validate({'routes':{'heroic_cinematic_cg':cg,'live_action_realist':live}})
    both.routes['heroic_cinematic_cg'].camera_policy='CG only change'
    assert both.routes['live_action_realist'].camera_policy=='Scene owned'
    with pytest.raises(ValidationError):VisualExpression.model_validate({'routes':{'live_action_realist':{**live,'proportionPolicy':'HEROIC_GROUNDED'}}})
    monkeypatch.setenv('DRAMA_CHARACTER_REPOSITORY_ROOT',str(repo.root))
    with pytest.raises(ValueError,match='BINDING_REQUIRED'):require_character_context(None,consumer='performance-casting',purpose='CASTING')
    with pytest.raises(ValueError,match='NOT_READY'):require_character_context(ref,consumer='performance-casting',purpose='CASTING')


def test_core_not_visual_and_manifest_validation(tmp_path):
    _,p,_,_,_=make_package(tmp_path/'repo')
    from drama_plugin.contracts.character_package import CharacterPackage
    d=dump_contract(p);d['manifest']['version']='../escape'
    with pytest.raises(ValidationError):CharacterPackage.model_validate(d)
    core=dump_contract(p.core);core['identity']='low angle commander'
    with pytest.raises(ValidationError):CharacterCore.model_validate(core)


def test_current_approval_and_raw_source_parser():
    from drama_plugin.characters.repository import digest
    script='### S01｜Test\n**Location：**room **Character：**Person **Dramatic Purpose：**test\n**Person〔D〕：**hello\n'.encode()
    w={'id':'work','content':{'approval':{'status':'APPROVED'},'revisionId':'r','screenplayAuthority':{'sha256':digest(script)}}}
    raw=approved_screenplay(w,script);assert len(raw['scenes'])==1 and len(raw['scenes'][0]['speakers'])==1
    with pytest.raises(ValueError,match='HASH'):approved_screenplay(w,script+b'x')
    w['content']['approval']['status']='DRAFT'
    with pytest.raises(ValueError,match='APPROVED'):approved_screenplay(w,script)


def test_memory_independence_fresh_process(tmp_path):
    repo,p,ref,_,_=make_package(tmp_path/'repo')
    env={'PATH':os.environ['PATH'],'PYTHONPATH':str(Path(__file__).resolve().parents[1]/'src')}
    result=subprocess.run([sys.executable,'-m','drama_plugin.characters',ref['characterPackageRef'],'v1','--root',str(repo.root),'--checksum',ref['checksum']],env=env,cwd=tmp_path,capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)['core']['identity']=='Synthetic actor'


def test_generic_skill_contamination_and_owners():
    root=Path(__file__).resolve().parents[1]
    files=list((root/'skills/character-external-driver').rglob('*'))+[root/'docs/character-external-driver.md']
    for path in files:
        if path.is_file():
            assert not any(x in path.read_text() for x in ['项羽','刘邦','韩信','xiang_yu','gaixia'])
    for owner in ['character-art','performance-casting','director','action-choreography','dialogue-design','voice-direction','shot-production']:
        text=(root/'skills'/owner/'SKILL.md').read_text()
        assert 'Never create or overwrite Character Core' in text
        assert 'resolve_character_package' in text


def test_repository_env_explicit_and_blank_override(tmp_path):
    from drama_plugin.config import load_config
    assert load_config(environment={'DRAMA_CHARACTER_REPOSITORY_ROOT':str(tmp_path)}).character_repository_root==str(tmp_path)
    config=tmp_path/'config.yaml';config.write_text('character_repository_root: /previous/repository\n')
    assert load_config(config,environment={'DRAMA_CHARACTER_REPOSITORY_ROOT':''}).character_repository_root==''
