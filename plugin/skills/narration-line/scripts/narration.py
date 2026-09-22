"""Offline candidate CLI. No network, provider, production or approval writes."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src'))
from drama_plugin.contracts.narration import NarrationBible, NarrationCue, NarrationPerformanceIntent, NarrationContext, NarrationPlan, FullDirectorScreenplay
from drama_plugin.narration import compile_narration, compile_director_screenplay
p=argparse.ArgumentParser()
p.add_argument('mode',choices=['schema','narration','director'])
p.add_argument('--input',type=Path)
p.add_argument('--output',type=Path)
a=p.parse_args()
if a.mode=='schema':
    result={c.__name__:c.model_json_schema(by_alias=True) for c in (NarrationBible,NarrationCue,NarrationPerformanceIntent,NarrationPlan,FullDirectorScreenplay)}
else:
    if not a.input:p.error('--input required')
    d=json.loads(a.input.read_text())
    expected={'context','plan'} if a.mode=='narration' else {'context','plan','narration'}
    if set(d)!=expected:p.error('exact input keys required: '+str(sorted(expected)))
    context=NarrationContext.model_validate(d['context'])
    result=compile_narration(NarrationPlan.model_validate(d['plan']),context) if a.mode=='narration' else compile_director_screenplay(FullDirectorScreenplay.model_validate(d['plan']),NarrationPlan.model_validate(d['narration']),context)
text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
if a.output:a.output.write_text(text)
else:print(text,end='')
