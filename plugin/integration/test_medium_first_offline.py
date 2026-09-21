"""Run all related existing regressions plus medium-first tests with outbound I/O blocked."""
import argparse
import json
from pathlib import Path
import socket
import sys
import pytest


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root/'src'));sys.path.insert(0,str(root/'tests'))
    def blocked(*a,**k): raise RuntimeError('NETWORK_FORBIDDEN_TEXT_REGRESSION')
    socket.socket.connect=blocked;socket.create_connection=blocked
    paths=sorted(str(p) for p in (root/'tests').glob('test_*.py') if any(x in p.name for x in ('character','casting','visual','expression','production','prompt','provider','medium')))
    reports=[];collection_errors=[]
    class Report:
        def pytest_runtest_logreport(self,report):
            if report.when=='call' or report.failed: reports.append(dict(test=report.nodeid,phase=report.when,outcome=report.outcome))
        def pytest_collectreport(self,report):
            if report.failed: collection_errors.append(str(report.longrepr))
    code=pytest.main(paths+['-q','--tb=short'],plugins=[Report()])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(dict(exitCode=int(code),status='PASS' if code==0 else 'FAIL',testFiles=paths,passed=sum(r['outcome']=='passed' for r in reports),failed=sum(r['outcome']=='failed' for r in reports),collectionErrors=collection_errors,results=reports,networkGuard='socket.connect/create_connection forbidden',realMediaProviderCalls=0,creditsConsumed=0),ensure_ascii=False,indent=2)+'\n')
    return code
if __name__=='__main__':sys.exit(main())
