"""Read-only current approval replay + original R3CR-RT01 offline consumer fixture.

The calling user explicitly authorized reuse of these exact existing approvals.
This diagnostic does not create approvals or professional designs for the Work.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any, Callable
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
sys.path.insert(0,str(REPO/'plugin/tests'))
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.interpretation import approved_interpretation, department_handoff
from drama_plugin.professional import validate_bible
from r3d_r_helpers import blocker_case


def capture(fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        fn()
        return {'status':'PASS'}
    except (ValueError,TypeError) as exc:
        return {'status':'FAIL','error':str(exc)}


def main() -> None:
    path=Path('/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/creative/screenplay-r3c-r/interpretation-approved.json')
    baseline=json.loads((HERE/'baseline.json').read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest()==baseline['sha256'][str(path)]
    data=json.loads(path.read_text())
    # Explicit Host caller allowlist, pinned in this turn before any runtime edit.
    context=json.loads((HERE/'authorized-context.json').read_text())
    assert context['approvedInputSha256']==baseline['sha256'][str(path)]
    trusted=tuple(SourcePin.model_validate(p) for p in context['approvedRefs'])
    approvals=[]
    for row in data['approvalRows']:
        approved_interpretation(SourcePin.model_validate(row['interpretationRef']),SourcePin.model_validate(row['approvalRef']),data['originals'],data['current'],trusted)
        approvals.append({'id':row['id'],'version':row['version'],'status':'PASS'})
    handoffs=[]
    for old in data['handoffs']:
        fresh=department_handoff(SourcePin.model_validate(old['interpretationRef']),SourcePin.model_validate(old['approvalRef']),old['implicationId'],data['originals'],data['current'],approved_refs=trusted)
        assert fresh==old
        handoffs.append({'department':old['department'],'status':'PASS','unchanged':True})
    with TemporaryDirectory(prefix='r3d-r-preflight-') as tmp:
        x=blocker_case(Path(tmp));host=x['host'];candidate=x['candidate'];current=x['current'];refs=(x['trusted'],)
        originals,resolved=host._inputs(candidate,current)
        checks={'direct':capture(lambda:validate_bible(x['character'],originals,resolved,approved_interpretation_refs=refs)),
                'missingContext':capture(lambda:host.submit(candidate,current=current)),
                'approvedHostSubmit':capture(lambda:host.submit(candidate,current=current,approved_interpretation_refs=refs))}
        ref=host.submit(candidate,current=current,approved_interpretation_refs=refs);current[ref.key]=ref.fingerprint
        for asset,department in [('char','character-art'),('coat','costume-design')]:
            checks[department+'Compile']=capture(lambda:host.compile(ref,asset,current=current,approved_interpretation_refs=refs))
            checks[department+'Records']=capture(lambda:host.department_records(ref,(asset,),department,current=current,approved_interpretation_refs=refs))
        assert checks['missingContext']=={'status':'FAIL','error':'USER_INTERPRETATION_APPROVAL_REQUIRED'}
        assert all(v['status']=='PASS' for k,v in checks.items() if k!='missingContext')
    result={'blocker':'R3CR-RT01','resolved':True,'currentApprovalRecheck':approvals,'unchangedDepartmentHandoffs':handoffs,
            'sameOfflineBlockerFixture':checks,'currentWorkCreativeArtifactsWritten':False,'paidCalls':0,
            'readyToResumeR3CR':True,'creativeRewriteResumed':False}
    (HERE/'preflight-after.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
