"""Offline package-to-provider-request regression. Never submits a request.

Run with the development Python runtime; test fixtures live in tests/.
"""
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import socket
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests')]
from character_medium_fixture import medium_case
from drama_plugin.characters.casting import compile_package_casting, executable_package_casting
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.creation import Work
from drama_plugin.contracts.visual_medium import VisualMediumIntent
from drama_plugin.hosts.casting_projection import full_body_seedream_projection
from drama_plugin.visual_medium import medium_consistency_gate, verify_medium_compilation


def no_network(*args, **kwargs):
    raise AssertionError('TEXT_REGRESSION_NETWORK_FORBIDDEN')


def run(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    results = {}
    # No network, workflow client, media tool or generation API can be used here.
    original = socket.socket.connect
    socket.socket.connect = no_network
    try:
        with tempfile.TemporaryDirectory(prefix='character-medium-text-') as tmp:
            compiled = {}
            for key, medium in [('A','CINEMATIC_CG'), ('B','LIVE_ACTION_PHOTOREAL')]:
                repo, package, projection = medium_case(Path(tmp)/key, medium)
                brief = compile_package_casting(repo, projection)
                verify_medium_compilation(brief)
                auth = dict(authorizationId='offline', authority='USER_EXPLICIT_SINGLE_CANDIDATE',
                    directiveRef=projection.directive_ref,directiveHash=projection.directive_hash,
                    workId='w',workRevision='r',character='actor',purpose='CHARACTER_FULL_BODY_CASTING',
                    maxOutputs=1,stopAfterFirstResult=True,inputsFingerprint=brief['inputsFingerprint'],status='AUTHORIZED')
                work = Work(id='w',title='Offline regression only',content=dict(
                    revisionId='r',approval={'status':'APPROVED'},visualRoute=brief['visualRoute'],
                    visualLanguage=brief['visualLanguage'],visualMediumIntent=brief['visualMediumIntent'],
                    characterPackageRoster={'sourceRevision':'r','characters':[{'characterId':'actor',
                        'name':package.core.identity,'package':dump_contract(projection.character_package)}]},
                    characterCastingAuthorizations={'offline':auth}))
                executable = executable_package_casting(work,repo,projection,'offline')
                evidence = {'checkedAt':datetime.now(timezone.utc).isoformat(),'schema':{
                    'id':'api_bytedance_seedream_5_0_pro_t2i','nodes':[
                    {'id':'3','class_type':'ByteDanceSeedreamNodeV3','inputs':{'model.width':1,'model.height':1,'prompt':''}},
                    {'id':'2','class_type':'SaveImageAdvanced','inputs':{}}]}}
                request = full_body_seedream_projection(executable,evidence,seed=1)
                assert request['input_overrides']['3']['prompt'] == brief['prompt']
                assert brief['prompt']+'\n' == (ROOT/'tests/snapshots'/('character-medium-'+medium.lower()+'.txt')).read_text()
                (output/(key+'-prompt.txt')).write_text(brief['prompt']+'\n')
                (output/(key+'-compilation.json')).write_text(json.dumps(brief,ensure_ascii=False,indent=2)+'\n')
                (output/(key+'-request-not-submitted.json')).write_text(json.dumps(request,ensure_ascii=False,indent=2)+'\n')
                results[key] = dict(expected='PASS',actual=brief['mediumGate']['status'],
                    visualMedium=medium,castingMode=brief['castingMode'],snapshot='PASS',providerPromptEquality=True,
                    promptFingerprint=brief['promptFingerprint'])
                compiled[medium] = brief
            failures=[]
            for legacy in (False,True):
                repo,_,projection = medium_case(Path(tmp)/('attack-'+str(legacy)),legacy=legacy)
                projection.paragraphs[0].text='真人演员，摄影棚定妆照片，真实演员试装摄影'
                try:
                    compile_package_casting(repo,projection)
                except ValueError as exc:
                    assert 'MEDIUM_CONSISTENCY_FAIL' in str(exc)
                    failures.append(dict(legacy=legacy,actual='FAIL',reason=str(exc)))
                else:
                    raise AssertionError('CG_ROUTE_REAL_ACTOR_PHOTO_ESCAPED')
            results['C'] = dict(expected='FAIL',actual='FAIL',attacks=failures)
            results['D'] = dict(expected='PASS',actual='PASS',legalCombinations=[
                b['castingMode']+' + '+b['visualMedium'] for b in compiled.values()])
            assert all(b['castingMode']=='HERO_CASTING' for b in compiled.values())
            cg,live=compiled.values()
            assert [r['text'] for r in cg['segments'] if r['id'].startswith('package.')]==[r['text'] for r in live['segments'] if r['id'].startswith('package.')]
            weak=medium_consistency_gate(VisualMediumIntent(visual_medium='CINEMATIC_CG'),'cinematic CG, 3D character, natural stubble, cloth costume')
            assert weak['status']=='WARN'
            results['weakLabelHeuristic']=weak
            assert not any(p.suffix.lower() in {'.png','.jpg','.mp4','.wav','.mp3'} for p in Path(tmp).rglob('*'))
    finally:
        socket.socket.connect = original
    result=dict(status='PASS',cases=results,providerSubmissions=0,mediaGenerated=0,
                phaseIReruns=0,creditsConsumed=0,networkPolicy='BLOCKED',
                sourceScope='New synthetic text fixture only; no old asset inputs')
    (output/'regression-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(run(args.output),ensure_ascii=False,indent=2))
