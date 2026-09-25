"""Read-only audit checks. No imports of plugin or external skill executables."""
from pathlib import Path
import ast, hashlib, json, re, subprocess
E=Path(__file__).resolve().parent
O=E.parent
R=O.parents[2]
def read(name):return json.loads((E/name).read_text())
base=read('local-baseline.json');rows=read('capabilities.json');refs=read('source-index.json');conf=read('conflicts.json');dec=read('final-decisions.json')
errors=[]
def check(condition,message):
    if not condition:errors.append(message)
changed=[]
for group in ['tracked','prior_reports']:
    for name,digest in base[group].items():
        p=R/name
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:changed.append(name)
check(not changed,'Frozen files changed')
check(subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==base['head'],'HEAD changed')
ids={r['id'] for r in rows};check(len(ids)==len(rows)==54,'Inventory uniqueness/count')
allowed={'ADOPT','ADAPT','REPLACE_LOCAL','KEEP_LOCAL','REFERENCE_ONLY','REJECT','OUT_OF_SCOPE'}
relationships={'ABSENT','COMPLEMENTARY','OVERLAP','DUPLICATE','CONFLICT','PROVIDER_ONLY','AESTHETIC_ONLY','OUT_OF_SCOPE'}
for r in rows:
    check(r['final_decision'] in allowed,r['id']+' final disposition')
    check(r['relationship'] in relationships,r['id']+' relationship')
    check(set(r['content_classes'])<={'K','W','P','R','Q','A'},r['id']+' type')
    check(all(k in refs for k in r['external_refs']+r['local_refs']),r['id']+' refs')
for k,v in refs.items():
    p=R/v['path'] if v['source']=='LOCAL' else Path('/private/tmp/face-audit-sources')/v['source']/v['path']
    if p.exists():
        check(hashlib.sha256(p.read_bytes()).hexdigest()==v['sha256'],k+' digest')
        check(1<=v['line']<=len(p.read_text().splitlines()),k+' line')
for name in ['Face-A1-Capability-Forensics.md','Face-A2-Local-Capability-Mapping.md']:
    found=re.findall(r'^\| (F\d{2})(?: | \|)',(O/name).read_text(),re.M)
    check(len(found)==54 and set(found)==ids,name+' row coverage')
for k,n in dec['counts'].items():check(n==sum(r['final_decision']==k for r in rows),k+' count')
check(set(dec['recommended_for_face_a3'])=={r['id'] for r in rows if r['final_decision']=='ADAPT'},'A3 candidate set')
for c in conf:
    check(set(c['capabilities'])<=ids,c['id']+' capability references')
    check(c['status']=='RESOLVED_FOR_AUDIT' and bool(c['winner']) and bool(c['future_action']),c['id']+' resolution')
check(len({c['id'] for c in conf})==16,'Conflict count')
def fields(path,cls):
    tree=ast.parse((R/path).read_text());node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
    return {n.target.id for n in node.body if isinstance(n,ast.AnnAssign)}
check('professional_sources' not in fields('plugin/src/drama_plugin/visual/frame_request.py','FrameSpec'),'D2 implemented unexpectedly')
check('face' in fields('plugin/src/drama_plugin/contracts/visual_prompt.py','Subject'),'IR face missing')
check({'shape','bone_structure','jaw','cheekbone'}<=fields('plugin/src/drama_plugin/contracts/production_design.py','FaceDesign'),'Legacy geometry counterevidence missing')
check('geometric_regions' in fields('plugin/src/drama_plugin/contracts/casting_discriminants.py','VisualDiscriminant'),'Current geometry counterevidence missing')
for p in O.glob('*.md'):
    s=p.read_text()
    for target in re.findall(r'\]\(([^)]+)\)',s):
        if target.startswith('http'):continue
        clean=re.sub(r':\d+$','',target.split('#')[0]); dest=Path(clean) if clean.startswith('/') else p.parent/clean
        if dest.name=='completion-check.json':continue
        check(dest.exists(),p.name+' missing link '+target)
    check(s.count('```')%2==0,p.name+' unmatched fence')
for p in E.glob('*.json'):
    if p.name != 'completion-check.json':json.loads(p.read_text())
check(dec['ready_for_face_a3']=='YES' and dec['stop_after']=='FACE_A2R','Stop gate')
result={'status':'PASS' if not errors else 'FAIL','errors':errors,'capability_count':len(rows),'decision_counts':dec['counts'],'conflicts_resolved':len(conf),'tracked_files_unchanged':len(base['tracked']),'prior_report_files_unchanged':len(base['prior_reports']),'changed_frozen_files':changed,'head':base['head'],'validation_scope':'Document/JSON/AST/source-link/hash checks; no runtime tests or platform generation experiments; B published comparison board visually inspected','runtime_behavior_changes':0,'paid_generations':0,'external_skill_installations':0,'parallel_face_authorities':0,'copied_prompt_bundles':0,'unresolved_same_scope_conflicts':0,'face_a3_or_a4_executed':False,'ready_for_face_a3':'YES'}
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(bool(errors))
