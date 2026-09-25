"""NON_RUNTIME audit only. Existing compiler, synthetic fixtures, no provider IO."""
from pathlib import Path
import sys, json, socket
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / 'plugin/src'), str(ROOT / 'plugin/tests')]
def blocked(*args, **kwargs):
    raise AssertionError('AUDIT_NETWORK_FORBIDDEN')
socket.socket.connect = blocked
socket.create_connection = blocked
from test_visual_prompt_ir import visual_ir, fact
from drama_plugin.visual.prompt_ir import compile_ir

records = []
def capture(label, ir, **kwargs):
    try:
        result = compile_ir(ir, provider_family=ir['task']['provider_family'], **kwargs)
        records.append({'case': label, 'synthetic': True, 'characters': len(result['prompt']), **result})
        return result
    except ValueError as exc:
        records.append({'case': label, 'synthetic': True, 'error': str(exc)})
        return None

for task in ('FIRST_FRAME', 'IMAGE_EDIT'):
    capture(task, visual_ir(task, 'gpt-image-2'))
for family in ('vidu', 'seedance'):
    for mode in ('text', 'single_image', 'first_last', 'reference'):
        ir = visual_ir('VIDEO', family)
        ir['task']['input_mode'] = mode
        capture(f'{family}:{mode}', ir)
ir = visual_ir('FIRST_FRAME', 'gpt-image-2')
ir['secondary_details'] = []
required = capture('required-only', ir)
ir['secondary_details'] = [fact('Optional paving detail. ' * 30, 'SECONDARY')]
capture('optional-budget-drop', ir, hard_limit=len(required['prompt']))
capture('required-overflow', ir, hard_limit=100)
ir = visual_ir('FIRST_FRAME', 'gpt-image-2')
ir['preserve'] = [fact('Preserve the approved face.'), fact('Maintain the same facial identity.')]
capture('semantic-duplicate', ir)
ir = visual_ir('FIRST_FRAME', 'gpt-image-2')
ir['action']['expression']['text'] = 'alienated and lonely'
capture('abstract-only-expression', ir)
ir = visual_ir('IMAGE_EDIT', 'gpt-image-2')
ir['continuity'] = [fact('Meaning-critical ring remains visible on left hand.')]
capture('edit-critical-continuity-selection', ir)
summary = {'classification': 'NON_RUNTIME_SYNTHETIC_COMPILER_OBSERVATION', 'provider_calls': 0,
           'network_guard': 'socket connect blocked', 'records': records}
Path(__file__).with_name('offline-probes.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
for row in records:
    print(row['case'], row.get('characters', row.get('error')), 'omitted=', len(row.get('omitted', [])))
