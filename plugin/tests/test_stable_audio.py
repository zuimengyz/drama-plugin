from copy import deepcopy
import json
from pathlib import Path
import sys
import wave

import pytest
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.film_score import FilmScorePlan, MusicGenerationRequirements
from drama_plugin.providers.music import stable_audio as sa

sys.path.insert(0, str(Path(__file__).parents[1]/'integration/fixtures'))
from music_fixture_builder import gaixia_score
from r3_fixture_builder import build_fixture

@pytest.fixture
def inputs():
    f=build_fixture((Path(__file__).parents[1]/'integration/fixtures/r3_source_proposal.md').read_text(),'a'*64,
                    music_constraints={'P08':('PRESERVE_REAL_JOY',)})
    score=gaixia_score(f,'b'*64)
    plan=score['plan'];r=plan.music_cues[-1].generation_requirements;b=score['composer_briefs'][-1]
    return plan,r,b,score['current']

@pytest.fixture
def installed(tmp_path):
    root=tmp_path/'mlx';(root/'scripts').mkdir(parents=True);(root/'models/mlx').mkdir(parents=True)
    (root/'scripts/sa3_mlx.py').write_text('# fixture')
    for n in ['t5gemma_f16.npz','dit_medium_f16.npz','same_l_decoder_f32.npz']:
        (root/'models/mlx'/n).write_bytes(b'fixture-not-real-model')
    return sa.LocalConfig(root,Path(sys.executable),'medium')

def translation(b):
    return {'composerBriefFingerprint':fp(b),'protectedPerformanceTexts':['力拔山', '虞兮'],'fields':{k:'Pinned translation of '+k for k in sa.REQUIRED_FIELDS}}

def evidence(i):
    names=['instrumental_control','duration_control','structural_control','continuation','revision','motif_consistency',
           'reference_audio','lossless_export','forced_vocals_risk','commercial_rights','prompt_fidelity','cost_observability',
           'stems','performance_observability']
    return {'binding':i['binding'],'route':'LOCAL','statuses':dict.fromkeys(names,'PASS'),'stemsKind':'B_SYNCHRONIZED_COMPONENTS'}

def wav(path,seconds=1):
    with wave.open(str(path),'wb') as w:
        w.setparams((2,2,44100,0,'NONE','not compressed'))
        w.writeframes(b'\x00\x10\x00\x10'*int(44100*seconds))

def test_configured_discovery_not_model_ready(installed):
    c=sa.LocalConfig.from_env({sa.PREFIX+'ROOT':str(installed.root),sa.PREFIX+'PYTHON':str(installed.python),sa.PREFIX+'MODEL':'medium'})
    i=sa.inspect_installation(c)
    assert i['weightsPresent'] and not i['modelLoaded'] and i['route']=='LOCAL'
    assert i['encoderPresent'] is False
    assert sa.StableAudio3CloudRoute().inspect_capabilities()['qualification']=='NOT_STARTED'

@pytest.mark.parametrize('fault',['config','install','weights','model'])
def test_discovery_fail_closed(installed,fault):
    if fault=='config':
        with pytest.raises(ValueError):sa.LocalConfig.from_env({})
        return
    if fault=='install':(installed.root/'scripts/sa3_mlx.py').unlink()
    if fault=='weights':(installed.root/'models/mlx/t5gemma_f16.npz').unlink()
    if fault=='model':installed=sa.LocalConfig(installed.root,installed.python,'cloud-large')
    with pytest.raises(ValueError):sa.inspect_installation(installed)

@pytest.mark.parametrize('fault',['stale','brief','unreviewed','non-ai','verse','no-score','requirements','vocal'])
def test_semantic_gates(inputs,fault):
    plan,r,b,current=inputs;reviewed=fp(b)
    if fault=='stale':current={}
    if fault=='brief':b=deepcopy(b);b['dramaticFunction']='invented';reviewed=fp(b)
    if fault=='unreviewed':reviewed='0'*64
    if fault=='non-ai':plan=deepcopy(plan);plan.music_cues[-1].source_strategy='ORIGINAL_HUMAN'
    if fault=='verse':b=deepcopy(b);b['dramaticFunction']='力拔山兮氣蓋世';reviewed=fp(b)
    if fault=='no-score':r=r.model_copy(update={'cue_ref':'P03:NO_SCORE'})
    if fault=='requirements':r=r.model_copy(update={'duration_range':(100.,120.)})
    if fault=='vocal':r=r.model_copy(update={'instrumental_policy':'EXPLICIT_VOCAL_APPROVAL','vocal_policy':'DIRECTOR_AND_MUSIC_APPROVED'})
    with pytest.raises(ValueError):sa.validate_inputs(plan,r,b,current,reviewed)

@pytest.mark.parametrize('field',['steps','cfg','seed','duration','device','providerFamily'])
def test_provider_parameters_never_semantic_core(inputs,field):
    raw=dump_contract(inputs[1]);raw[field]=10
    with pytest.raises(ValueError):MusicGenerationRequirements.model_validate(raw)

def test_mapping_binds_inputs_and_no_full_script(inputs):
    p,r,b,c=inputs;sa.validate_inputs(p,r,b,c,fp(b))
    m=sa.map_brief(b,translation(b));assert 'singing, chant, choir, vocal texture' in m['negativeInstructions']
    assert set(m['fieldMapping'])==set(sa.REQUIRED_FIELDS)
    bad=translation(b);bad['composerBriefFingerprint']='0'*64
    with pytest.raises(ValueError):sa.map_brief(b,bad)
    bad=translation(b);bad['fields']['cueArc']='虞兮虞兮'
    with pytest.raises(ValueError):sa.map_brief(b,bad)

@pytest.mark.parametrize('cap',['instrumental_control','duration_control','lossless_export','structural_control',
                                'stems','commercial_rights','forced_vocals_risk','performance_observability'])
@pytest.mark.parametrize('status',['UNKNOWN','FAIL','NOT_SUPPORTED'])
def test_required_capability_blocks(inputs,installed,cap,status):
    p,r,_,_=inputs;i=sa.inspect_installation(installed);e=evidence(i);e['statuses'][cap]=status
    q=sa.qualify(p,r,i,e);assert q['productionQualification']=='BLOCKED' and cap in q['blockers']

def test_stems_a_never_b_and_cloud_independent(inputs,installed):
    p,r,_,_=inputs;i=sa.inspect_installation(installed);e=evidence(i)
    assert sa.qualify(p,r,i,e)['productionQualification']=='PASS'
    e['stemsKind']='A_SEPARATE_INSTRUMENT_GENERATIONS'
    assert sa.qualify(p,r,i,e)['productionQualification']=='BLOCKED'
    cloud=sa.StableAudio3CloudRoute(True,True,True,True,True)
    assert cloud.inspect_capabilities()['qualification']=='NOT_STARTED'
    with pytest.raises(ValueError,match='NO_FALLBACK'):cloud.generate(r)

@pytest.mark.parametrize('fault',['binding','route'])
def test_qualification_bound_to_version_model_route(inputs,installed,fault):
    p,r,_,_=inputs;i=sa.inspect_installation(installed);e=evidence(i);e[fault]='changed'
    with pytest.raises(ValueError):sa.qualify(p,r,i,e)

def test_lossless_and_duration_are_decoded_not_extension(tmp_path):
    p=tmp_path/'test.wav';p.write_bytes(b'not a wav')
    with pytest.raises((ValueError,wave.Error,EOFError)):sa.inspect_wav(p,1)
    wav(p);m=sa.inspect_wav(p,1)
    assert m['codec']=='pcm_s16le' and m['bitDepth']==16 and m['channels']==2
    assert m['durationPass'] and m['delta']==0 and m['sha256']==sa.digest(p)
    assert not sa.inspect_wav(p,2)['durationPass']
    assert m['instrumentalObservation']=='REQUIRES_HUMAN_LISTENING'

def kwargs(inputs,installed,tmp_path):
    p,r,b,c=inputs;i=sa.inspect_installation(installed)
    return dict(current=c,reviewed_brief=fp(b),translation=translation(b),qualification=sa.qualify(p,r,i,evidence(i)),
        poc_evidence={'binding':i['binding'],**dict.fromkeys(['modelLoaded','wavValid','durationValid','offline','instrumentalTargetExecuted'],True)},
        state='LOCAL_ENGINEERING_POC',candidate='A',duration=27,seed=1)

@pytest.mark.parametrize('fault',['route','poc','baseline','budget','duration','qual'])
def test_generation_gates_no_call(inputs,installed,tmp_path,monkeypatch,fault):
    p,r,b,_=inputs;k=kwargs(inputs,installed,tmp_path)
    if fault=='route':k['route']='CLOUD'
    if fault=='poc':k['state']='PRODUCTION'
    if fault=='baseline':k['poc_evidence']['modelLoaded']=False
    if fault=='budget':k['candidate']='C'
    if fault=='duration':k['duration']=120
    if fault=='qual':k['qualification']['route']='CLOUD'
    monkeypatch.setattr(sa,'run_local',lambda *a,**kw:pytest.fail('must not execute'))
    with pytest.raises(ValueError):sa.StableAudio3Provider(installed,tmp_path/'out').generate(p,r,b,**k)

def test_success_two_slots_result_hash_no_adoption_or_formal_provider(inputs,installed,tmp_path,monkeypatch):
    p,r,b,_=inputs;k=kwargs(inputs,installed,tmp_path);count=[]
    def execute(*a,**kw):count.append(kw['seed']);wav(kw['output'],kw['duration']);return {'networkAttempts':0}
    monkeypatch.setattr(sa,'run_local',execute)
    provider=sa.StableAudio3Provider(installed,tmp_path/'out')
    for name in ('A','B'):
        k['candidate']=name;record=provider.generate(p,r,b,**k)
        assert record['composerBriefFingerprint']==fp(b) and record['requirementsFingerprint']==fp(r)
        assert record['formalWrites']==0 and not record['adopted'] and record['eligibility']=='NOT_PRODUCTION_ELIGIBLE'
        assert provider.get_result(name)['sha256']==record['sha256']
    with pytest.raises(ValueError,match='NO_RESUBMIT'):provider.generate(p,r,b,**k)
    assert len(count)==2
    Path(record['outputFile']).write_bytes(b'changed')
    with pytest.raises(ValueError):provider.get_result('B')

def test_failure_no_cloud_fallback_and_ambiguous_no_retry(inputs,installed,tmp_path,monkeypatch):
    p,r,b,_=inputs;k=kwargs(inputs,installed,tmp_path);calls=[]
    def ambiguous(*a,**kw):calls.append(1);wav(kw['output'],27);raise TimeoutError('uncertain')
    monkeypatch.setattr(sa,'run_local',ambiguous)
    provider=sa.StableAudio3Provider(installed,tmp_path/'out')
    with pytest.raises(TimeoutError):provider.generate(p,r,b,**k)
    with pytest.raises(ValueError,match='NO_RESUBMIT'):provider.generate(p,r,b,**k)
    assert len(calls)==1
    assert json.loads((tmp_path/'out/provider-mapping-A.json').read_text())['status']=='AMBIGUOUS_RESULT'

def test_no_network_resolver_or_user_path_in_adapter():
    folder=Path(sa.__file__).parent
    code='\n'.join(p.read_text() for p in folder.glob('*.py'))
    assert '/Users/' not in code
    worker=(folder/'stable_audio_worker.py').read_text()
    assert 'weights.ensure_local = local_only' in worker and 'sys.addaudithook(audit)' in worker
    assert 'hf_hub_download(' not in code and 'httpx' not in code

def test_c03_regression(inputs):
    p,r,b,_=inputs;c=p.music_cues[-1]
    assert c.emotional_direction=='JOY' and c.performance_relation=='SUPPORT_EARNED_RELEASE'
    assert '何如' in b['dialogueWindows'][0] and '如大王言' in b['dialogueWindows'][0]
    assert '真实笑' in b['cueArc'][-1] and '退尽' in b['cueArc'][-1]
    assert r.vocal_policy=='PROHIBITED' and r.stem_requirement=='REQUIRED'
    assert '不提前告诉观众结局' in b['doNot']
    for ref in p.excluded_performance_refs:
        with pytest.raises(ValueError):sa.composer_brief(p,ref,current=inputs[3])

@pytest.mark.parametrize('attack',['network','download'])
def test_real_worker_denies_network_and_missing_weight_download(tmp_path,attack):
    import subprocess
    root=tmp_path/'fake-install';(root/'scripts').mkdir(parents=True)
    (root/'scripts/weights.py').write_text('def ensure_local(rel):\n raise AssertionError("download must never run")\n')
    body='import socket\nsocket.create_connection(("127.0.0.1",1))\n' if attack=='network' else 'import weights\nweights.ensure_local("missing.npz")\n'
    (root/'scripts/sa3_mlx.py').write_text(body)
    request=tmp_path/'request.json';request.write_text(json.dumps({'root':str(root)}))
    worker=Path(sa.__file__).with_name('stable_audio_worker.py')
    result=subprocess.run([sys.executable,str(worker),str(request)],capture_output=True,text=True)
    assert result.returncode != 0
    expected='OFFLINE_EXECUTION_NO_NETWORK_OR_CHILD_PROCESS' if attack=='network' else 'LOCAL_MODEL_INCOMPLETE_NO_DOWNLOAD'
    assert expected in result.stderr and 'download must never run' not in result.stderr


def test_translation_policy_is_explicit_and_work_specific(inputs):
    b=inputs[2];t=translation(b);del t['protectedPerformanceTexts']
    with pytest.raises(ValueError,match='EXPLICIT_PROTECTED'):sa.map_brief(b,t)
    t=translation(b);t['protectedPerformanceTexts']=['A fictional court lament'];t['fields']['cueArc']='A fictional court lament'
    with pytest.raises(ValueError,match='HISTORICAL_VERSE'):sa.map_brief(b,t)
    t['fields']['cueArc']='Tension releases through fewer instruments'
    m=sa.map_brief(b,t);assert m['protectedPerformanceTextsFingerprint']==fp(t['protectedPerformanceTexts'])
    t['protectedPerformanceTexts']=[]
    sa.map_brief(b,t)  # Explicitly no protected source text in this different work.
