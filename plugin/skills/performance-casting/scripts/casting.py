"""Read-only, provider-neutral casting artifact entry point."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'src'))
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.performance_casting import RoleArchetypeProfile,CastingReview,CastingBudget
from drama_plugin.performance_casting import stage_brief,user_selection_gate
from drama_plugin.contracts.casting_discriminants import VisualCastingPlan
from drama_plugin.casting_discriminants import compile_visual_discriminants,visual_selection_gate,verify_submitted_projection
p=argparse.ArgumentParser();p.add_argument('mode',choices=['schema','validate','brief','selection','compile','check-projection']);p.add_argument('--profile',type=Path);p.add_argument('--reviews',type=Path);p.add_argument('--stage',choices=['FACE','SCALE','SOCIAL','PERFORMANCE']);p.add_argument('--candidates',nargs='+');p.add_argument('--budget',type=Path);p.add_argument('--execution',default='DRY_RUN',choices=['DRY_RUN','MCP']);p.add_argument('--output',type=Path);p.add_argument('--visual-plan',type=Path);p.add_argument('--variant');p.add_argument('--purpose',choices=['CANDIDATE','CALIBRATION'],default='CANDIDATE');p.add_argument('--calibration-conditions',type=Path);p.add_argument('--submitted-prompt',type=Path);a=p.parse_args()
if a.mode=='schema':result=RoleArchetypeProfile.model_json_schema(by_alias=True)
else:
 if not a.profile:p.error('--profile required')
 profile=RoleArchetypeProfile.model_validate_json(a.profile.read_text());reviews=[CastingReview.model_validate(r) for r in json.loads(a.reviews.read_text())] if a.reviews else []
 visual=VisualCastingPlan.model_validate_json(a.visual_plan.read_text()) if a.visual_plan else None
 if a.mode in {'compile','check-projection'}:
  if visual is None or not a.variant or not a.stage:p.error('visual-plan, variant and stage required')
  result=compile_visual_discriminants(profile,visual,a.variant,a.stage,purpose=a.purpose,calibration_conditions=json.loads(a.calibration_conditions.read_text()) if a.calibration_conditions else None)
  if a.mode=='check-projection':
   if a.submitted_prompt is None:p.error('submitted-prompt required')
   result=verify_submitted_projection(result,a.submitted_prompt.read_text())
 elif a.mode=='validate':result=dump_contract(profile)
 elif a.mode=='selection':result=visual_selection_gate(profile,visual,reviews,purpose=a.purpose) if visual else user_selection_gate(profile,reviews)
 else:
  if not a.stage or not a.candidates:p.error('--stage and --candidates required')
  result=stage_brief(profile,a.stage,a.candidates,reviews,budget=CastingBudget.model_validate_json(a.budget.read_text()) if a.budget else None,execution=a.execution)
s=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(s)
else:print(s,end='')
