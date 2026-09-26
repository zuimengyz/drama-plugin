"""Read-only same-candidate gate replay; never rebinds Director/projection pins.

Run with --baseline to load the two original modules from the recorded HEAD.
All outputs are derived audit evidence, not creative artifacts or approval.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable

BASELINE = 'df625f9d01cc62c3f1ffed2774e88166ab37bae5'
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'plugin/src'))


def call(fn: Callable[[], Any]) -> dict[str, Any]:
    from drama_plugin.contracts.base import dump_contract
    try:
        value = fn()
        return {'status':'PASS', 'value':dump_contract(value) if hasattr(value, 'model_dump') else value}
    except (ValueError, TypeError, KeyError) as exc:
        return {'status':'FAIL', 'finding':str(exc)}


def recheck(candidate: Path) -> dict[str, Any]:
    from drama_plugin.contracts.base import sha256_canonical as fp
    from drama_plugin.contracts.dpd import SceneDPD, BeatDPD, LineDPD, DPDSnapshot
    from drama_plugin.contracts.performance_direction import DirectorPerformanceIntent
    from drama_plugin.scene_dramaturgy import source_dramaturgy, review_scene_dramaturgy
    from drama_plugin.screenplay_playability import map_screenplay_performance, validate_exact_turn
    from drama_plugin.performance_direction import validate_turn_direction, validate_intent
    pack = json.loads((candidate / 'screenplay-r3-dramaturgy-sidecar.json').read_text())
    directions = json.loads((candidate / 'director-performance-candidate.json').read_text())
    before = fp({'pack': pack, 'directions':directions})
    report: dict[str, Any] = {'scope':'CANDIDATE_ONLY / NOT_ADOPTED', 'scenes':{}}
    for e in pack['scenes']:
        s=e['source']; sid=s['id']
        sd=SceneDPD.model_validate(e['sceneDpd'])
        beats=[BeatDPD.model_validate(b) for b in e['beats']]
        lines=[LineDPD.model_validate(l) for l in e['lines']]
        dpds={k:DPDSnapshot.model_validate(v) if 'effective' in v else BeatDPD.model_validate(v) for k,v in e['dpds'].items()}
        bound: dict[str, DPDSnapshot | BeatDPD] = {b.beat_id:b for b in beats}
        bound.update({d.line.spoken_content_id:d for d in dpds.values() if isinstance(d, DPDSnapshot)})
        r: dict[str, Any] = {'source':call(lambda: source_dramaturgy(s)),
            'dramaturgy':call(lambda: review_scene_dramaturgy(s,bound,e['dramaturgyReview'])), 'turns':{}}
        r['source'].pop('value', None)
        mapped=call(lambda: map_screenplay_performance(s,sd,beats,lines,dramaturgy_review=e['dramaturgyReview']))
        if mapped['status']=='PASS':
            mapped['value']={'readyForDirection':mapped['value']['readyForDirection']}
        r['mapper']=mapped
        intent=DirectorPerformanceIntent.model_validate(directions['intents'][sid])
        current=dict(directions['current'])
        if r['dramaturgy']['status']=='PASS':
            receipt=r['dramaturgy']['value']
            current['dramaturgy:'+sid]=receipt['fingerprint']
            r['listenerSilenceLocal']={axis:[f for f in receipt['findings'] if f['axis']==axis]
                for axis in ('LISTENER_CAUSALITY','SILENCE_FUNCTION')}
            r['receiptBinding']={'originalDirectorPin':intent.dramaturgy_fingerprint,'recomputedReceipt':receipt['fingerprint']}
        for line in s['content']['spokenContent']:
            lid=line['id']; d=dpds[lid]; assert isinstance(d, DPDSnapshot)
            exact=call(lambda:validate_exact_turn(s,lid,d)); exact.pop('value',None)
            r['turns'][lid]={'text':line['text'],'speaker':line['speakerKey'],'target':line['target'],
                'exactTurn':exact,
                'directionOriginalPinsReplay':call(lambda:validate_turn_direction(s,lid,d,intent,directions['projections'][lid],directions['current'])),
                'directionCurrentReceipt':call(lambda:validate_turn_direction(s,lid,d,intent,directions['projections'][lid],current)),
                'directorIntentCurrentReceipt':call(lambda:validate_intent(intent,d,current).schema_version)}
        report['scenes'][sid]=r
    report['inputsUnmodifiedInMemory']=before==fp({'pack':pack,'directions':directions})
    report['productionAuthorized']=False
    return report


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--baseline',action='store_true')
    args=parser.parse_args()
    if args.baseline:
        for name in ('scene_dramaturgy','screenplay_playability'):
            code=subprocess.check_output(['git','show',BASELINE+':plugin/src/drama_plugin/'+name+'.py'],cwd=ROOT,text=True)
            spec=importlib.util.spec_from_loader('drama_plugin.'+name,loader=None)
            assert spec is not None
            module=importlib.util.module_from_spec(spec)
            sys.modules[spec.name]=module
            exec(compile(code, '<baseline:'+name+'>', 'exec'), module.__dict__)
    report=recheck(args.candidate)
    report['boundaryMatrix'] = boundary_matrix()
    report['runtime']='BASELINE '+BASELINE if args.baseline else 'WORKING_TREE'
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for sid,r in report['scenes'].items():
        print(sid,r['dramaturgy'].get('value',{}).get('status'),r['mapper'])
        print('exact',sum(t['exactTurn']['status']=='PASS' for t in r['turns'].values()),'/',len(r['turns']))
        print('current direction',[(lid,t['directionCurrentReceipt'].get('finding','PASS')) for lid,t in r['turns'].items()])


def boundary_matrix() -> dict[str, Any]:
    from test_r3b_r_dialogue_vocative import case as vocative, LID
    from test_r3b_r_self_directed_action import case as self_action
    from r3b_r_helpers import repin, turn, result
    from drama_plugin.dpd import compose_dpd
    from drama_plugin.screenplay_playability import validate_exact_turn
    from drama_plugin.scene_dramaturgy import source_dramaturgy
    matrix: dict[str, Any] = {}
    for name, text, action in [('old ambiguous dialogue','妈妈……先生，妈妈……','get_attention'),
                              ('empty medical request','先生！','ask_for_medical_help'),
                              ('empty follow request','先生！','persuade target to follow')]:
        e=vocative(text,action)
        matrix[name]=call(lambda: validate_exact_turn(e['source'], LID, turn(e,LID)))
    e=vocative(); e['source']['content']['spokenContent'][-1]['target']=None
    # Repin all source-owned identity witnesses; canonical missing target still
    # disagrees with the explicit current DPD, so source validation must reject.
    next(c for c in e['source']['content']['dramaturgy']['carriers'] if c['ref']=='spoken:'+LID)['target']=None
    def missing_target() -> Any:
        repin(e)
        return validate_exact_turn(e['source'],LID,turn(e,LID))
    matrix['missing target']=call(missing_target)
    e=vocative(); d=turn(e,LID)
    d=compose_dpd(d.scene,d.beat.model_copy(update={'direction':d.beat.direction.model_copy(update={'interaction_target':'男人'})}),d.line)
    matrix['wrong target']=call(lambda:validate_exact_turn(e['source'],LID,d))
    matrix['exact-turn binding']=call(lambda:validate_exact_turn(e['source'],'S02-L1a',turn(e,LID)))
    e=self_action('母亲')
    matrix['interpersonal missing response']=call(lambda:result(e))
    e=self_action(); facet=e['source']['content']['dramaturgy']
    env=facet['carriers'][4]; env['causeRef']='spoken:S03-L1'
    facet['interactions']=[{'actionRef':'spoken:S03-L1','responseRef':env['ref']}]
    repin(e)
    matrix['fake environmental response']=call(lambda:source_dramaturgy(e['source']))
    for item in matrix.values():
        if isinstance(item.get('value'),dict) and 'findings' in item['value']:
            item['value']={k:item['value'][k] for k in ('status','findings')}
    return matrix


if __name__=='__main__': main()
