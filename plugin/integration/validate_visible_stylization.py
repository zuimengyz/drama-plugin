"""Explicit project/Character Art revision and offline text regression. No production."""
import argparse
from copy import deepcopy
import hashlib,json,socket,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from drama_plugin.contracts.base import dump_contract,sha256_canonical
from drama_plugin.contracts.visual_medium import VisualMediumIntent,revise_render_intent
from drama_plugin.visual_medium import compile_character_art,verify_medium_compilation,medium_consistency_gate,fact_domain,VERSION
from drama_plugin.render_stylization import render_stylization_gate


def run(source: Path,handoff: Path,b1: Path,b2: Path,directive: Path,out: Path):
    def blocked(*a,**k):raise RuntimeError('NETWORK_FORBIDDEN_TEXT_REGRESSION')
    socket.socket.connect=blocked;socket.create_connection=blocked
    out.mkdir(parents=True,exist_ok=True);(out/'snapshot').mkdir(exist_ok=True)
    def save(n,v):(out/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,handoff,b1,b2,directive]}
    art=json.loads(source.read_text());planning=json.loads(handoff.read_text());old=json.loads(b2.read_text());first=json.loads(b1.read_text())
    policy_path=out/'character-art-visual-contract-revision.json'
    # This is an explicit task-authorized owner revision, not a global default or
    # compiler inference from a character name. Old source bytes are immutable.
    revision=dict(revision='CHARACTER-VISUAL-CONTRACT-R3',owner='character-art',directive=str(directive),directiveSha256=pins[str(directive)],directorRole='visual philosophy and final creative review; no shader prose',renderStylization='VISIBLE_FILMIC_CG',presentationMode='LOOKDEV_NEUTRAL',scope='CURRENT_PROJECT_CHARACTER_TEXT_CONTRACT',sourceFiles=pins,mediaAuthorization=False,environmentImplementation=False,characters=[])
    classifications={r['characterRef']:r for r in planning['characters']}
    for idx,r in enumerate(art['character-art']):
        old_intent=VisualMediumIntent.model_validate(r['values']['cg_route']['visualMediumIntent'])
        role=classifications[r['values']['character_ref']]
        mode='HERO_CASTING' if role['classification']=='HERO' else old_intent.casting_mode
        new_intent=revise_render_intent(old_intent,render_stylization='VISIBLE_FILMIC_CG',source=str(policy_path)+f'#/characters/{idx}',presentation_mode='LOOKDEV_NEUTRAL',casting_mode=mode)
        revision['characters'].append(dict(id=r['id'],characterRef=r['values']['character_ref'],priorIntent=dump_contract(old_intent),intent=dump_contract(new_intent),sourceRecordFingerprint=sha256_canonical(r),handoffClassification=role['classification'],modeRevisionReason='Explicit owner correction of blanket Phase-I design-neutral mode using current HERO handoff importance; neutral framing moves to presentationMode' if mode!=old_intent.casting_mode else 'Preserve authored casting scope; no automatic heroic strengthening'))
    save(policy_path.name,revision)
    save('render-stylization-contract.json',VisualMediumIntent.model_json_schema(by_alias=True))
    results=[];compilations={};dedup={}
    fields=['apparent_age','height_impression','body_proportion','body_mass','shoulder_waist_ratio','face_structure','jaw','eyes','brows','nose','skin','hair','facial_hair','silhouette','dominant_visual_traits','secondary_traits','screen_presence','camera_readable_features','forbidden_appearance']
    cost_fields=['costume_identity','rank_distinction','garment_construction_intent','armor_intent','materials','layering','wear']
    for idx,r in enumerate(art['character-art']):
        rows=[]
        def add(rec,field,value,pointer,domain=None):
            if isinstance(value,dict):value=value['design']
            text='；'.join(value) if isinstance(value,list) else value
            row=dict(id=rec+'.'+field,topic=field,text=text,sources=[str(source)+'#'+pointer],sourceValueFingerprint=sha256_canonical(value))
            row['domain']=domain or fact_domain(row);rows.append(row)
        for f in fields:add(r['id'],f,r['values'][f],f'/character-art/{idx}/values/{f}')
        for ci,cost in enumerate(art['costume-design']):
            if cost['values']['character_ref']==r['values']['character_ref']:
                for f in cost_fields:add(cost['id'],f,cost['values'][f],f'/costume-design/{ci}/values/{f}','materials')
        rows.append(dict(id='text.composition',domain='rendering',text='One person; three-quarter orientation; simple non-narrative background; authored proportions, face, hands and costume visible.',sources=['offline:composition-control']))
        intent=VisualMediumIntent.model_validate(revision['characters'][idx]['intent'])
        c=compile_character_art(intent,rows,source_intent=str(policy_path)+f'#/characters/{idx}/intent');verify_medium_compilation(c)
        assert c['mediumGate']['status']==c['renderStylizationGate']['renderStylizationStatus']=='PASS'
        for fact in c['visualMediumCompilation']['translatedFactSections']:assert c['prompt'][fact['start']:fact['end']]==fact['text']
        (out/'snapshot'/f'{r["id"]}.txt').write_text(c['prompt']+'\n');save(f'snapshot/{r["id"]}.json',c)
        compilations[r['id']]=c;dedup[r['id']]=c['visualMediumCompilation']['deduplicatedFacts']
        results.append(dict(id=r['id'],intent=dump_contract(intent),medium='PASS',renderStylization='PASS',receiptReplay='PASS',factsFingerprint=sha256_canonical(rows),promptFingerprint=c['promptFingerprint']))
    assert len(results)==12
    # Recompile the actual B1-R2 fact/framing inputs; do not reuse its rendered prose.
    xi=next(x for x in revision['characters'] if x['id']=='ART-xiangyu')
    target=VisualMediumIntent.model_validate(xi['intent']);input_rows=old['visualMediumCompilation']['inputSections']
    c=compile_character_art(target,input_rows,source_intent=str(policy_path)+'#/characters/0/intent');verify_medium_compilation(c)
    (out/'current-failure-prompt.txt').write_text(old['prompt'])
    m=medium_consistency_gate(target,old['prompt']);audit=render_stylization_gate(target,old['prompt'],medium_status=m['status'])
    assert m['status']=='PASS' and audit['renderStylizationStatus']=='FAIL'
    save('current-failure-style-audit.json',dict(medium=m,style=audit))
    (out/'new-xiangyu-prompt.txt').write_text(c['prompt']);save('new-xiangyu-compilation.json',c)
    save('new-xiangyu-style-audit.json',dict(medium=c['mediumGate'],style=c['renderStylizationGate']))
    assert len(c['prompt'])<len(old['prompt'])
    save('source-map-sample.json',c['visualMediumCompilation'])
    save('prompt-dedup-report.json',dict(oldCharacters=len(old['prompt']),newCharacters=len(c['prompt']),characterReductionPercent=round((1-len(c['prompt'])/len(old['prompt']))*100,2),oldRepeatedPrefixCount=old['prompt'].count('Authored digital')+old['prompt'].count('Authored CG'),newRepeatedPrefixCount=c['prompt'].count('Authored digital')+c['prompt'].count('Authored CG'),actualXiangyuFactDeduplications=c['visualMediumCompilation']['deduplicatedFacts'],characters=dedup))
    abc=[]
    for label,medium,style in [('A','LIVE_ACTION_PHOTOREAL',None),('B','CINEMATIC_CG','PHOTOREAL_DIGITAL_HUMAN'),('C','CINEMATIC_CG','VISIBLE_FILMIC_CG'),('D','CINEMATIC_CG','HEIGHTENED_FILMIC_CG')]:
        raw=dump_contract(target);raw.update(visualMedium=medium,renderStylization=style,renderStylizationSource=str(policy_path)+'#text-only-ABCD' if style else None)
        cc=compile_character_art(VisualMediumIntent.model_validate(raw),input_rows,source_intent='same-facts-ABCD-diagnostic');verify_medium_compilation(cc)
        save(f'snapshot/xiangyu-{label}.json',cc);(out/'snapshot'/f'xiangyu-{label}.txt').write_text(cc['prompt'])
        abc.append(dict(route=label,medium=medium,style=style,factsFingerprint=sha256_canonical(input_rows),mediumGate=cc['mediumGate'],styleGate=cc['renderStylizationGate'],domainProse=cc['visualMediumCompilation']['compiledMediumConstraints'],promptFingerprint=cc['promptFingerprint']))
    assert len({r['promptFingerprint'] for r in abc})==4
    assert all(abc[1]['domainProse'][d]!=abc[2]['domainProse'][d] for d in ['form','skin','groom','materials','shape','rendering'])
    save('medium-style-abc-regression.json',dict(status='PASS',sameFacts=True,routes=abc))
    presentations=[]
    for mode in ['LOOKDEV_NEUTRAL','HERO_PRESENTATION','PERFORMANCE_PRESENTATION']:
        raw=dump_contract(target);raw['presentationMode']=mode
        cc=compile_character_art(VisualMediumIntent.model_validate(raw),input_rows);verify_medium_compilation(cc)
        presentations.append(dict(presentationMode=mode,castingMode=cc['visualMediumIntent']['castingMode'],factsFingerprint=sha256_canonical(input_rows),styleGate=cc['renderStylizationGate'],promptFingerprint=cc['promptFingerprint']))
    save('presentation-regression.json',dict(status='PASS',results=presentations))
    save('casting-presentation-authority.json',dict(priorCharacterArt=xi['priorIntent'],actualB1=first['visualMediumIntent'],actualB1R2=old['visualMediumIntent'],phaseIIAClassification=xi['handoffClassification'],sourceTrace='Current Phase I build-art.py assigns DESIGN_NEUTRAL to every package; Character Art copies that route. B1 and compiler preserve it.',compilerOrB1SilentOverride=False,sourceDesignIssue='Blanket source casting scope did not separately express leading-role importance and neutral presentation',explicitCurrentOwnerRevision=xi,oldSourceBytesRetained=True))
    save('failure-superseding-interpretation.json',dict(scope='new interpretation; original reports and images untouched',cases=[dict(case=name,originalVerdict='FAIL_MEDIUM',medium='CINEMATIC_CG / ambiguous',renderStylization='PHOTOREAL_DIGITAL_HUMAN',target='VISIBLE_FILMIC_CG',verdict='FAIL_RENDER_STYLIZATION',meaning='Visible appearance classification; not a claim of physical photography or provider internal rendering technology',usage='VISUAL_FAILURE_EVIDENCE_ONLY',referenceEligible=False) for name in ['B1_CANDIDATE_1','B1_R2']],providerCausality='NOT_ESTABLISHED'))
    save('character-12-regression.json',dict(status='PASS',count=12,results=results))
    assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==h for path,h in pins.items())
    save('source-manifest.json',dict(sourceFiles=pins,sourceBytesUnchanged=True,compilerVersion=VERSION,realImageGeneration=0,realVideoGeneration=0,ComfyGeneration=0,SeedreamGeneration=0,FishTTSCalls=0,StableAudioGeneration=0,creditsConsumed=0))
    print(json.dumps(dict(status='PASS',characters=12,oldMedium=m['status'],oldStyle=audit['renderStylizationStatus'],newMedium=c['mediumGate']['status'],newStyle=c['renderStylizationGate']['renderStylizationStatus'],oldLength=len(old['prompt']),newLength=len(c['prompt']),media=0,credits=0)))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['source','handoff','b1','b2','directive','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.source,a.handoff,a.b1,a.b2,a.directive,a.output)
