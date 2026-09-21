"""Offline reconciliation of immutable current Character Art; never submits media."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from drama_plugin.visual_medium import compile_character_art, verify_medium_compilation, medium_consistency_gate, fact_domain, VERSION
from drama_plugin.contracts.visual_medium import VisualMediumIntent
from drama_plugin.contracts.base import sha256_canonical


def blocked(*args, **kwargs):
    raise RuntimeError('NETWORK_FORBIDDEN_TEXT_REGRESSION')


def run(source, old_path, output):
    socket.socket.connect = blocked
    socket.create_connection = blocked
    output.mkdir(parents=True, exist_ok=True)
    (output/'snapshot').mkdir(exist_ok=True)
    def save(name, value):
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    source_bytes=source.read_bytes(); old_bytes=old_path.read_bytes()
    art=json.loads(source_bytes); old=json.loads(old_bytes)
    old_intent=VisualMediumIntent.model_validate(old['visualMediumIntent'])
    old_audit=medium_consistency_gate(old_intent,old['prompt'])
    (output/'old-xiangyu-prompt.txt').write_text(old['prompt'])
    save('old-xiangyu-medium-audit.json',old_audit)
    assert old_audit['blocking']
    # Actual submitted facts, including costume and B1 framing, are retained.
    old_rows=[deepcopy(r) for r in old['segments'] if not r['id'].startswith('compiled.')]
    for r in old_rows:
        for key in ('start','end','textFingerprint','mediumAuthority'):
            r.pop(key,None)
    new=compile_character_art(old_intent,old_rows,source_intent='retained-B1-source-facts:'+hashlib.sha256(old_bytes).hexdigest())
    verify_medium_compilation(new)
    (output/'new-xiangyu-prompt.txt').write_text(new['prompt'])
    save('new-xiangyu-medium-audit.json',new['mediumGate'])
    save('new-xiangyu-compilation.json',new)
    fields=['apparent_age','height_impression','body_proportion','body_mass','shoulder_waist_ratio','face_structure','jaw','eyes','brows','nose','skin','hair','facial_hair','silhouette','dominant_visual_traits','secondary_traits','screen_presence','camera_readable_features','forbidden_appearance']
    cost_fields=['costume_identity','rank_distinction','garment_construction_intent','armor_intent','materials','layering','wear']
    results=[]; diffs=[]; dedups={}; balances=[]
    for index, record in enumerate(art['character-art']):
        v=record['values']; rows=[]
        def add(record_id, field, value, pointer, domain=None):
            if isinstance(value,dict): value=value['design']
            text='；'.join(value) if isinstance(value,list) else value
            row=dict(id=record_id+'.'+field,topic=field,text=text,sources=[str(source)+'#'+pointer],sourceValueFingerprint=sha256_canonical(value))
            row['domain']=domain or fact_domain(row)
            rows.append(row)
        for field in fields: add(record['id'],field,v[field],f'/character-art/{index}/values/{field}')
        for ci,cost in enumerate(art['costume-design']):
            if cost['values']['character_ref']==v['character_ref']:
                for field in cost_fields: add(cost['id'],field,cost['values'][field],f'/costume-design/{ci}/values/{field}','materials')
        # A neutral diagnostic presentation; no actor-photo or CG wording from Host.
        rows.append(dict(id='diagnostic.composition',domain='rendering',text='One person; three-quarter orientation; simple background; authored proportions and costume visible.',sources=['text-regression:composition-control']))
        intent=VisualMediumIntent.model_validate(v['cg_route']['visualMediumIntent'])
        assert intent.visual_medium=='CINEMATIC_CG'
        cg=compile_character_art(intent,rows,source_intent=str(source)+f'#/character-art/{index}/values/cg_route/visualMediumIntent')
        li=intent.model_copy(update={'visual_medium':'LIVE_ACTION_PHOTOREAL'})
        live=compile_character_art(li,rows,source_intent='text-only-same-facts-live-counterfactual')
        for medium,c in [('cg',cg),('live',live)]:
            verify_medium_compilation(c)
            (output/'snapshot'/f'{record["id"]}-{medium}.txt').write_text(c['prompt']+'\n')
            save(f'snapshot/{record["id"]}-{medium}.json',c)
        assert cg['visualMediumCompilation']['inputSections']==live['visualMediumCompilation']['inputSections']
        differences={}
        for domain in ('form','skin','groom','materials','shape','rendering'):
            a=[r['text'] for r in cg['segments'] if r.get('domain')==domain]
            b=[r['text'] for r in live['segments'] if r.get('domain')==domain]
            differences[domain]={'different':a!=b,'cg':a,'live':b}
        assert all(d['different'] for d in differences.values())
        # Anatomical facts are preserved byte-for-byte except separators/dedup;
        # only skin vocabulary uses the declared lexical medium transform.
        original_facts={r['id']:r['text'] for r in rows}
        for r in cg['visualMediumCompilation']['translatedFactSections']:
            assert all(atom in original_facts[r['id']] for atom in r['sourceFactText'].split('；'))
        dedups[record['id']]=cg['visualMediumCompilation']['deduplicatedFacts']
        diffs.append(dict(id=record['id'],sameInputFacts=True,domains=differences))
        balances.append(dict(id=record['id'],cg=cg['mediumGate'],live=live['mediumGate']))
        results.append(dict(id=record['id'],characterRef=v['character_ref'],cg='PASS',live='PASS',receiptReplay='PASS',factsPreserved=True,visualMediumIntent=cg['visualMediumIntent'],promptFingerprint=cg['promptFingerprint']))
    assert len(results)==12
    save('character-12-regression.json',dict(status='PASS',count=len(results),results=results,executionClass='WORKSPACE_OFFLINE_TEXT_COMPILATION',productionAuthorization=False))
    save('cg-live-action-ab-diff.json',diffs)
    save('prompt-dedup-report.json',dict(algorithm='normalized exact clauses; base facts precede derived summaries; unique derived facts retained',xiangyuActualB1=new['visualMediumCompilation']['deduplicatedFacts'],characters=dedups))
    save('medium-semantic-balance-results.json',dict(old=old_audit,new=new['mediumGate'],characters=balances))
    save('candidate-1-disposition.json',dict(candidate='B1_CANDIDATE_1',MEDIUM='FAIL',usage='VISUAL_FAILURE_EVIDENCE_ONLY',characterPackage=False,referenceImage=False,approvedCasting=False,mediaReadOrUsedAsInput=False))
    assert source.read_bytes()==source_bytes and old_path.read_bytes()==old_bytes
    save('source-manifest.json',dict(compilerVersion=VERSION,sources=[dict(path=str(p),sha256=hashlib.sha256(b).hexdigest()) for p,b in [(source,source_bytes),(old_path,old_bytes)]],sourceBytesUnchanged=True,realMediaProviderCalls=0,creditsConsumed=0,networkCalls=0))
    print(json.dumps(dict(status='PASS',characters=len(results),oldGate='WARN-BLOCKING' if old_audit['status']=='WARN' else old_audit['status'],newGate=new['mediumGate']['status'],realMediaProviderCalls=0,creditsConsumed=0)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--old-compilation',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.source,a.old_compilation,a.output)
