"""Read-only literary sidecar CLI; no generators or business writes."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src'))
from drama_plugin.contracts.authorial_voice import AuthorialInterventionGate, LiteraryCandidate, AuthorialVoiceBudget
from drama_plugin.authorial_voice import evaluate_intervention

p = argparse.ArgumentParser()
p.add_argument('mode', choices=['schema', 'evaluate'])
p.add_argument('--input', type=Path)
p.add_argument('--output', type=Path)
a = p.parse_args()
if a.mode == 'schema':
    result = {c.__name__: c.model_json_schema(by_alias=True) for c in (AuthorialInterventionGate, LiteraryCandidate, AuthorialVoiceBudget)}
else:
    if a.input is None:
        p.error('--input required')
    data = json.loads(a.input.read_text())
    if set(data) - {'gate', 'candidate', 'budget'}:
        p.error('unknown input fields')
    result = evaluate_intervention(AuthorialInterventionGate.model_validate(data['gate']),
        LiteraryCandidate.model_validate(data['candidate']) if data.get('candidate') else None,
        AuthorialVoiceBudget.model_validate(data['budget']) if data.get('budget') else None)
text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
if a.output:
    a.output.write_text(text)
else:
    print(text, end='')
