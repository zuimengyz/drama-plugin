"""Deterministic synthetic evidence. No network, URLs resolved, or model calls."""
import json
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(root/'plugin/src'), str(root/'plugin/tests')]
from test_seedance_prompt_generator import sample
from drama_plugin.visual.video_prompt import compile_request_ir
from drama_plugin.visual.prompt_ir import compile_ir
from drama_plugin.prompt_generators.seedance_2.policy import policy

rows=[]
for mode in ('text_to_video','image_to_video','first_last_frame','reference'):
    request=sample(mode)
    old=compile_ir(request.prompt_ir,provider_family='seedance',audio_supported=request.native_audio,
                   hard_limit=5000,model=request.continuity.primary_model,legacy_replay=True)
    new=compile_request_ir(request)
    rows.append(dict(mode=mode,fixture='SYNTHETIC_OFFLINE_NOT_APPROVED_PRODUCTION',
        chars_before=len(old['prompt']),**new['statistics'],
        old_prompt=old['prompt'],new_prompt=new['prompt'],coverage=new['coverage'],input_slots=new['input_slots']))
result=dict(schema='seedance-offline-comparison-v1',paid_generation=0,media_generation=0,policy=policy(),cases=rows)
Path(__file__).with_name('offline-comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
for case in rows:
    print(case['mode'],case['chars_before'],case['chars_after'],case['obligations_total'],case['text_covered'],case['reference_covered'],case['omitted_optional'],case['uncovered_required'],case['semantic_duplicates'])
