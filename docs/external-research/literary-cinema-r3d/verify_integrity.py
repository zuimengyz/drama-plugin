"""Compare frozen inputs to the pre-edit working tree, not merely Git HEAD."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def main() -> None:
    baseline=json.loads((HERE/'baseline-integrity.json').read_text())
    rows=[]
    for name,before in baseline['hashes'].items():
        path=ROOT/name
        after=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        rows.append(dict(path=name,before=before,after=after,unchanged=before==after))
    changed=[r['path'] for r in rows if not r['unchanged']]
    allowed={'drama-plugin/plugin/src/drama_plugin/'+name for name in (
        'contracts/professional.py','professional.py','hosts/creative_source.py','hosts/director_artifacts.py',
        'hosts/professional.py','preproduction.py')}
    unexpected=sorted(set(changed)-allowed)
    before_lines=(HERE/'mypy-before.txt').read_text().splitlines()
    after_lines=(HERE/'mypy-after.txt').read_text().splitlines()
    old={line for line in before_lines if ': error:' in line};new={line for line in after_lines if ': error:' in line}
    result={'head':baseline['head'],'frozenExistingFiles':len(rows),'changedExistingFiles':changed,
            'unexpectedChanges':unexpected,'unchangedCount':sum(r['unchanged'] for r in rows),
            'mypyBaselineErrors':len(old),'mypyAfterErrors':len(new),'mypyNewErrors':sorted(new-old),
            'rows':rows}
    (HERE/'source-integrity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False,indent=2))
    assert not unexpected and not new-old

if __name__=='__main__':main()
