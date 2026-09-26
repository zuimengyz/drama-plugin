"""File-persisted canonical fixture. Never Gaixia or a proposal relabel."""
from pathlib import Path
from typing import Any, cast
import json
from drama_plugin.contracts.creation import Work,Script,Episode,Scene,Shot
from drama_plugin.contracts.base import dump_contract,sha256_canonical as fp
from drama_plugin.contracts.dpd import SceneDPD,BeatDPD,LineDPD,DPDLayerState
from drama_plugin.contracts.performance_direction import DirectorPerformanceIntent,PerformanceProjection
from drama_plugin.providers.base import MemoryProvider
from drama_plugin.dpd import compose_dpd
from drama_plugin.contracts.screenplay_playability import BeatPlayability, LinePlayability
from drama_plugin.screenplay_playability import exact_text_hash
from drama_plugin.hosts.formal_performance import read_formal_performance_source
from drama_plugin.performance_coverage import CATEGORIES
from performance_direction_helpers import make_case

class PersistedReader:
    def __init__(self,path:Path):self.path=path
    def tree(self):return json.loads(self.path.read_text())
    async def get_work(self,work_id):return Work.model_validate(self.tree()['work'][0])
    async def list_scripts(self,work_id):return [Script.model_validate(x) for x in self.tree()['scripts']]
    async def list_episodes(self,script_id):return [Episode.model_validate(x) for x in self.tree()['episodes']]
    async def list_scenes(self,episode_id):return [Scene.model_validate(x) for x in self.tree()['scenes']]
    async def list_shots(self,scene_id):return [Shot.model_validate(x) for x in self.tree()['shots'] if x['sceneId']==scene_id]

async def formal_case(path:Path):
    from r3b_helpers import synthetic_case
    from drama_plugin.scene_dramaturgy import review_scene_dramaturgy
    from drama_plugin.screenplay_playability import dialogue_turn_fingerprint
    cases = [synthetic_case('war' + str(i)) for i in range(1, 4)]
    tree = {'work':[dump_contract(Work(id='war', title='Offline canonical fixture', content={'revisionId':'test-r3b'}))],
        'scripts':[dump_contract(Script(id='script', work_id='war', title='fixture'))],
        'episodes':[dump_contract(Episode(id='episode', script_id='script', episode_no=1, title='fixture'))],
        'scenes':[c['source'] for c in cases], 'shots':[]}
    for i, case in enumerate(cases, 1):
        sid=case['source']['id']
        for suffix in ('a','b'):
            tree['shots'].append(dump_contract(Shot(id=sid+'-'+suffix, scene_id=sid, shot_no=str(i)+suffix, content={'revisionId':'test-r3b'})))
    path.write_text(json.dumps(tree))
    witness=await read_formal_performance_source(cast(MemoryProvider,PersistedReader(path)),'war')
    inventory={'scope':'FORMAL_PRODUCTION_BOOK','source_hash':witness.fingerprint,**{k:[] for k in CATEGORIES},'not_applicable':{}}
    contexts={};directions={};dpds={};scene_dpds={};intents={};projections={};reviews={};current=dict(witness.pins)
    for case in cases:
        s=case['source'];sid=s['id'];base=case['base']
        scene_dpds[sid]=case['scene_dpd'];dpds.update(case['dpds']);reviews[sid]=case['review']
        receipt=review_scene_dramaturgy(s,case['dpds'],case['review'])
        assert receipt['status']=='PASS',receipt
        current['dramaturgy:'+sid]=receipt['fingerprint']
        current.update({k:v for k,v in base['current'].items() if k.startswith('grammar:')})
        snapshots=[d for d in case['dpds'].values() if hasattr(d,'effective')]
        turn_hashes={d.line.spoken_content_id:dialogue_turn_fingerprint(s,d.line.spoken_content_id,d) for d in snapshots}
        intent=base['intent'].model_copy(update={'scene_id':sid,'source_fingerprints':{'scenes:'+sid:fp(s)},
            'dpd_fingerprints':tuple(d.fingerprint if hasattr(d,'effective') else fp(d) for d in case['dpds'].values()),
            'beat_ids':tuple(d.beat.beat_id if hasattr(d,'effective') else d.beat_id for d in case['dpds'].values()),
            'coordination':(), 'review_basis':'SOURCE_BOUND_DESIGN','dramaturgy_fingerprint':receipt['fingerprint'],'turn_fingerprints':turn_hashes})
        intents[sid]=intent
        contexts[sid]={'scope':sid,'entities':{actor:{'scope':sid,'kind':'partner','display':actor,'source_ref':'scenes:'+sid,'evidence':'Explicit synthetic exchange participant.'} for actor in s['content']['characters']}}
        for d in snapshots:
            projections[d.beat.beat_id]={ch:p.model_copy(update={'director_intent_fingerprint':fp(intent),
                'beat_id':d.beat.beat_id,'spoken_content_id':d.line.spoken_content_id,'coordination':(),
                'interaction_target':'partner','turn_fingerprint':turn_hashes[d.line.spoken_content_id]})
                for ch,p in [('VISUAL',base['visual'].director_performance),('VOICE',base['audio'].director_performance)]}
    for category,items in witness.obligations().items():
        for ref,truth in items.items():
            sid=truth['scene'];key=sid+':spoken:L1'
            if 'line' in truth:key=sid+':spoken:'+truth['line']['id']
            if category=='characters' and truth['actor']=='partner':
                key=next(k for k,d in dpds.items() if not hasattr(d,'effective') and d.scene_id==sid)
            inventory[category].append({'ref':ref,**truth,'performance_bearing':True,'vocal':category=='spoken'})
            directions[ref]={'scene':sid,'source_ref':truth['source_ref'],'status':'COVERED','detail':'EXPANDED',
                'density':{'dramaticSalience':True,'ambiguity':False,'relationshipTurn':False,'performanceRisk':False,'misreadingRisk':False,
                    'reason':'The refusal changes the next request in this synthetic exchange.','sourceRefs':['scenes:'+sid]},
                'core':'Keep the exchange addressed to the present partner','objective_ref':key,'target_ref':'partner',
                'expression':'LOW','physical':'Maintain the source position','partner':'Follow the source response',
                'continuity_in':'At the door','continuity_out':'Still at the door','do_not':'Do not invent agreement',
                'context_refs':['partner'],'context_fingerprint':fp(contexts[sid]),
                'semantic_review':{'status':'PASS','evidence':'Authored offline source-bound fixture; no artistic outcome claim.'},
                'voice':'Address the source listener','speech_action':'The exact source request','vocal_mode':'SPOKEN',
                'handoff':'Wait for the source response','closure':'Leave space for the partner'}
            if category=='interactions':
                action=truth['action_ref'];response=truth['response_ref']
                directions[ref]['objective_ref']=sid+':spoken:'+action[7:]
                directions[ref]['interaction']={'action_ref':action,'response_ref':response,'speaker_ref':'speaker:repairer',
                    'listener_ref':'partner','speaker_dpd':sid+':spoken:'+action[7:],'listener_dpd':sid+':carrier:'+response,
                    'speaker_action':'Make the source request','listener_action':'Give the source response','speaker_target':'partner',
                    'listener_attention':'Stay in the current exchange','gaze_handoff':'Use source orientation','voice_handoff':'Do not interrupt',
                    'physical_handoff':'Keep the source positions','partner_cue':'Exact source request','response_timing':'After the source action',
                    'next_beat_owner':'speaker:repairer'}
    from drama_plugin.performance_coverage import CONTINUITY_FIELDS
    for item in inventory['continuity']:
        state={k:'LOW' for k in CONTINUITY_FIELDS}
        directions[item['ref']]['edge']={'previous_exit':state,'next_entry':dict(state),'transitions':{}}
    inventory['not_applicable']['ensemble']='Two individually covered participants; no ensemble group.'
    return {'formal_source':witness,'inventory':inventory,'directions':directions,'contexts':contexts,'dpds':dpds,
        'scene_dpds':scene_dpds,'intents':intents,'projections':projections,'source_hash':witness.fingerprint,
        'current':current,'dramaturgy_reviews':reviews}
