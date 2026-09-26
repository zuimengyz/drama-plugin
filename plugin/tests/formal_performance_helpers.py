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
    base=make_case('intimate');tree={
      'work':[dump_contract(Work(id='war',title='Offline canonical fixture',content={'revisionId':'test-r1'}))],
      'scripts':[dump_contract(Script(id='script',work_id='war',title='fixture',content={'revisionId':'test-r1'}))],
      'episodes':[dump_contract(Episode(id='episode',script_id='script',episode_no=1,title='fixture',content={'revisionId':'test-r1'}))],
      'scenes':[],'shots':[]}
    for i in range(1,4):
        sid='war'+str(i)
        tree['scenes'].append(dump_contract(Scene(id=sid,episode_id='episode',order=i,title='exchange '+str(i),content={'revisionId':'test-r1','characters':['speaker:repairer','partner'],'screenplayAction':'The repairer stops sorting. The partner listens.','spokenContent':[{'id':'L'+str(i),'speakerKey':'speaker:repairer','text':'Finish your account.','target':base['dpd'].effective.interaction_target,'intent':base['dpd'].line.dramatic_action,'performanceIntent':'An invitation to finish, spoken at close range.'}]})))
        for suffix in ('a','b'):tree['shots'].append(dump_contract(Shot(id=sid+'-'+suffix,scene_id=sid,shot_no=str(i)+suffix,content={'revisionId':'test-r1'})))
    path.write_text(json.dumps(tree))
    witness=await read_formal_performance_source(cast(MemoryProvider,PersistedReader(path)),'war')
    inventory={'scope':'FORMAL_PRODUCTION_BOOK','source_hash':witness.fingerprint,**{k:[] for k in CATEGORIES},'not_applicable':{}}
    contexts={};directions={};dpds={};scene_dpds={};intents={};projections={}
    for s in tree['scenes']:
        sid=s['id'];line=s['content']['spokenContent'][0];beat=sid+':spoken:'+line['id']
        sd=base['dpd'].scene.model_copy(update={'scene_id':sid,'source_fingerprint':fp(s)})
        bd=base['dpd'].beat.model_copy(update={'scene_id':sid,'beat_id':beat})
        ld=base['dpd'].line.model_copy(update={'scene_id':sid,'beat_id':beat,'spoken_content_id':line['id']})
        bd = bd.model_copy(update={'direction': bd.direction.model_copy(update={'interaction_target': base['dpd'].effective.interaction_target, 'tactic': base['dpd'].effective.tactic})})
        bd = bd.model_copy(update={'playability': BeatPlayability(source_scene_hash=fp(s),
            source_excerpt='The repairer stops sorting.', playable_actions=({'actor':bd.actor,'behavior':'The repairer stops sorting.','target':bd.direction.interaction_target},),
            performance_state='Stops the hand task to listen without collapsing', reaction={'actor':bd.actor,'behavior':'The repairer stops sorting.','target':bd.direction.interaction_target},
            review_evidence='The visible interruption of sorting gives the partner the floor.')})
        ld = ld.model_copy(update={'playability': LinePlayability(source_text_hash=exact_text_hash(line['text']),
            literal_meaning='Invite the partner to finish speaking', speakability_review='A short direct invitation with an explicit listener; no exposition or ambiguous referent.', fragmentation='CONTINUOUS')})
        dpd=compose_dpd(sd,bd,ld);scene_dpds[sid]=sd;dpds[beat]=dpd
        dpds[sid+':partner']=BeatDPD(scene_id=sid,beat_id=sid,actor='partner',obstacle='The repairer is still sorting',transition_trigger='Sorting stops',direction=DPDLayerState(objective='Finish the account',interaction_target='speaker:repairer',tactic='Wait for attention then finish'),playability=BeatPlayability(source_scene_hash=fp(s),source_excerpt='The partner listens.',playable_actions=({'actor':'partner','behavior':'The partner listens.','target':'speaker:repairer'},),performance_state='Waits for the invitation before replying',reaction={'actor':'partner','behavior':'The partner listens.','target':'speaker:repairer'},review_evidence='The listener remains active in the exchange.'))
        contexts[sid]={'scope':sid,'entities':{'partner':{'scope':sid,'kind':'partner','display':'partner','source_ref':'scenes:'+sid,'evidence':'The partner listens.'}}}
        intent=base['intent'].model_copy(update={'scene_id':sid,'source_fingerprints':{'scenes:'+sid:fp(s)},'dpd_fingerprints':(dpd.fingerprint,), 'beat_ids':(beat,), 'coordination':(), 'review_basis':'SOURCE_BOUND_DESIGN'})
        intents[sid]=intent
        pair={}
        for channel,p in [('VISUAL',base['visual'].director_performance),('VOICE',base['audio'].director_performance)]:
            pair[channel]=p.model_copy(update={'director_intent_fingerprint':fp(intent),'beat_id':beat,'spoken_content_id':line['id'],'coordination':()})
        projections[beat]=pair
    for category,items in witness.obligations().items():
        for ref,truth in items.items():
            sid=truth['scene'];beat=sid+':spoken:'+next(s for s in tree['scenes'] if s['id']==sid)['content']['spokenContent'][0]['id']
            inventory[category].append({'ref':ref,**truth,'performance_bearing':True,'vocal':category=='spoken'})
            directions[ref]={'scene':sid,'source_ref':truth['source_ref'],'status':'COVERED','detail':'STANDARD','core':'Let the partner complete the account','objective_ref':beat,'target_ref':'partner','expression':'LOW','physical':'Stop sorting; keep supporting the tool','partner':'Listen to the partner','continuity_in':'Support the tool','continuity_out':'Resume after listening','do_not':'Do not interrupt','context_refs':['partner'],'context_fingerprint':fp(contexts[sid]),'semantic_review':{'status':'PASS','evidence':'fixture scripted handoff'},'voice':'Address the partner at close range','speech_action':'Invite completion','vocal_mode':'SPOKEN','handoff':'Wait for response','closure':'Short open question'}
    for item in inventory['characters']:
        if item['actor']=='partner':directions[item['ref']]['objective_ref']=item['scene']+':partner'
    for item in inventory['interactions']:
        sid=item['scene'];d=directions[item['ref']]
        d['interaction']={'speaker_ref':'speaker:repairer','listener_ref':'partner','speaker_dpd':d['objective_ref'],'listener_dpd':sid+':partner','speaker_action':'Invite completion','listener_action':'Finish the account','speaker_target':'partner','listener_attention':'The repairer stops sorting','gaze_handoff':'Look up before inviting','voice_handoff':'Wait for the account','physical_handoff':'Keep the tool supported','partner_cue':'Sorting stops','response_timing':'After attention arrives','next_beat_owner':'partner'}
    from drama_plugin.performance_coverage import CONTINUITY_FIELDS
    for item in inventory['continuity']:
        state={k:'LOW' for k in CONTINUITY_FIELDS}
        directions[item['ref']]['edge']={'previous_exit':state,'next_entry':dict(state),'transitions':{}}
    inventory['not_applicable']['ensemble']='Canonical fixture has two individuals and no performanceGroups; their interaction is covered.' 
    return {'formal_source':witness,'inventory':inventory,'directions':directions,'contexts':contexts,'dpds':dpds,'scene_dpds':scene_dpds,'intents':intents,'projections':projections,'source_hash':witness.fingerprint,'current':{**witness.pins,**{k:v for k,v in base['current'].items() if k.startswith('grammar:')}}}
