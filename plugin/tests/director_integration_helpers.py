"""Design-only professional inputs, bound to retained S2/S8/S7. No formal mutation."""
from copy import deepcopy
import json
from pathlib import Path
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.creation import Scene
from drama_plugin.contracts.dpd import DPDSnapshot
from drama_plugin.contracts.cinematic import CinematicShotSpec
from drama_plugin.contracts.visual_route import RouteContext
from drama_plugin.contracts.director import CapabilityRequest, DirectorWorkspace
from drama_plugin.director import pin, request_pin
from drama_plugin.skills.registry import SkillRegistry
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
from drama_plugin.hosts.director_capabilities import LocalCapabilityBridge
from drama_plugin.visual.cinematic import narrative_source
from test_cinematic_direction import example
from test_director import design_review

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = json.loads((ROOT/'tests/fixtures/director-three-scenes.json').read_text())['samples']
SOURCES = json.loads((ROOT/'tests/fixtures/director-integration-sources.json').read_text())
MEANING = {2:'楚歌引起求证而非证明楚地已失；选择收缩',8:'看懂帮助、拒绝与交缰之间的距离',7:'局部能战与东侧会合、再围并存；不变成全局胜利'}


def route(scene_id, cg=False):
    name = 'stylized_cinematic_cg' if cg else 'live_action_realist'
    return RouteContext.model_validate({'project':{'workId':SOURCES['work']['id'],'revision':'retained-r1',
        'enabledRoutes':['live_action_realist','stylized_cinematic_cg']},
        'sequence':{'workId':SOURCES['work']['id'],'sequenceKey':scene_id,'visualRoute':name,'overrideReason':'isolated offline comparison'},
        'style':{'visualRoute':name,'revision':'design-only', 'medium':'DESIGNED_CG' if cg else 'PHOTOGRAPHIC',
          'rendering':'DESIGN_ONLY, NOT LOOKDEV','castingCriteria':['identity only; user approval missing'],
          'shapeLanguage':'readable silhouette' if cg else 'natural weight','materialPalette':'earth',
          'cameraGrammar':'maintain geography','performanceGrammar':'controlled pose' if cg else 'restrained attention',
          'historicalBoundary':'preserve uncertainty','forbiddenDrifts':['no canon invention']}})


class Session:
    def __init__(self, path, number, cg=False):
        self.sample=deepcopy(next(s for s in SAMPLES if s['sceneNo']==number))
        self.store=DirectorArtifactStore(path)
        self.source=pin(self.sample['sceneId'],dump_contract(Scene.model_validate(self.sample['canonicalScene'])))
        self.source.kind='CANON'
        assert self.source.fingerprint==self.sample['sourceHash']
        self.intent=self.store.put('intent',{'sourceRef':dump_contract(self.source),'meaning':MEANING[number]})
        self.route_ref=self.store.put('route:'+('cg' if cg else 'live'),dump_contract(route(self.sample['sceneId'],cg)))
        self.current={p.key:p.fingerprint for p in (self.source,self.intent,self.route_ref)}
        self.w=self.store.create(DirectorWorkspace(workspace_id='gaixia',scope_id=self.sample['sceneId'],branch_id='cg' if cg else 'live',
            source_pins=(self.source,),intent_refs=(self.intent,),route_ref=self.route_ref))
        skills=SkillRegistry();skills.load_directory(ROOT/'skills')
        self.bridge=LocalCapabilityBridge(self.store,skills.get)
    def request(self, capability, inputs, revision=0, approvals=(), evidence=('CONTRACT_VALID',)):
        inp=self.store.put('input:'+capability+':'+fp(inputs),inputs);self.current[inp.key]=inp.fingerprint
        q=CapabilityRequest(request_id=capability,revision=revision,workspace_id=self.w.workspace_id,scope_id=self.w.scope_id,
            branch_id=self.w.branch_id,source_pins=self.w.source_pins,intent_refs=self.w.intent_refs,route_ref=self.route_ref,
            capability=capability,task=MEANING[self.sample['sceneNo']],result_kind='DESIGN_ONLY',
            must_preserve=('canonical source and historical uncertainty',),prohibitions=('NO TTS REPLACEMENT','NO CANON CHANGE'),
            priority='CRITICAL',required_evidence=evidence,requirement_refs=(inp,),approval_refs=approvals,supersedes=self.w.request_ref)
        for p in approvals:self.current[p.key]=p.fingerprint
        self.w=self.store.transition(self.w,'REQUEST',self.store.put(request_pin(q).key,dump_contract(q)),self.current)
        return q,inp
    def run(self,q,inp):
        self.w=self.store.transition(self.w,'DISPATCH',None,self.current)
        f=self.bridge.run(q,inp,self.current)
        self.record_current(f)
        self.w=self.store.transition(self.w,'FEEDBACK',self.store.retain_feedback(q,f),self.current)
        return f
    def record_current(self,f):
        self.current.update({p.key:p.fingerprint for p in (*f.result_refs,*f.evidence_refs)})
    def review(self,q,f,disposition='APPROVE',receipt=False):
        delta=self.store.put('presentation-receipt-input',{'domain':'audience_knowledge','summary':'DESIGN_ONLY: '+MEANING[self.sample['sceneNo']], 'presentationOnly':True}) if receipt else None
        if delta:self.current[delta.key]=delta.fingerprint
        review=design_review(self.w,q,f,delta,disposition)
        ref=self.store.put('design-review',review)
        self.w=self.store.transition(self.w,'REVIEW',ref,self.current)
        return self.w


def dpd_input(s):
    d=DPDSnapshot.model_validate(s.sample['dpdSnapshot'])
    return {k:dump_contract(getattr(d,k)) for k in ('scene','beat','line')}


def coverage(s, decomposition=False):
    info = ['geography','decision','contact','consequence'] if decomposition else ['experience']
    text = {'geography':'看清坡地与东侧会点','decision':'项羽分队突击并要求会合','contact':'局部突破仍保留对手方向与接触因果',
        'consequence':'从骑确认局部能战，汉军仍可重围','experience':MEANING[s.sample['sceneNo']]}
    return {'plan':{'sceneIds':[s.w.scope_id], 'sourceFingerprint':s.source.fingerprint,'revision':'decomposed' if decomposition else 'initial',
        'informationBeats':[{'key':k,'information':text[k],'focus':'人物与空间关系','change':text[k]} for k in info],
        'coverage':[{'key':'coverage-'+k,'beatIds':[k],'duration':6,'durationBasis':'DRAMATIC_INFORMATION','durationReason':text[k],
                    'purpose':'DIALOGUE' if k=='experience' else 'SETUP'} for k in info],
        'establishingNeed':'保留空间和距离，不增加正式Shot','visualContrastRhythm':'压制、选择、后果；DESIGN_ONLY'}}


def cinematic(s):
    spec,_,visual=example();raw=dump_contract(spec)
    shot=deepcopy(next(x for x in SOURCES['shots'] if x['scene_id']==s.w.scope_id))
    scene=deepcopy(s.sample['canonicalScene']);dur=shot['content']['plannedDurationMs']/1000
    ctx={k:deepcopy(SOURCES[k]) for k in ('work','script','episode')}
    ctx.update(scene=scene,shot=shot,dpdSnapshot=s.sample['dpdSnapshot'])
    actor=s.sample['dpdSnapshot']['line']['speaker']
    state='项羽仍面对场内回应对象'
    raw.update(workId=ctx['work']['id'],sceneId=s.w.scope_id,shotId=shot['id'],sourceFingerprint=fp(narrative_source(ctx)),
        durationSeconds=dur,narrativeIntent=MEANING[s.sample['sceneNo']], openingState=state,endingState=state,
        anchorOmissionReason='沿用已存在Shot的场内位置',stabilityContract=[{'dimension':'identity','allowed':'视线变化','forbidden':'身份改变','reason':'人物连续'}],
        secondaryMotion=[],secondaryMotionOmissionReason='本离线设计只验证合同，未观测动作',
        referenceRequirements=[{'role':'CHARACTER','necessity':'REQUIRED','subject':actor,'purpose':'身份连续'}])
    raw['performance']={'objective':s.sample['dpdSnapshot']['scene']['direction']['objective'],'interactionTarget':s.sample['dpdSnapshot']['scene']['direction']['interactionTarget'],
        'emotionalArc':['倾听','回应'], 'beats':[{'start':0,'end':dur,'kind':'CONTINUOUS','startState':state,'endState':state,
        'actions':[{'actor':actor,'behavior':'视线留在场内对方，说完后保持等待回应'}]}]}
    spoken={x['id']:x for x in scene['content']['spokenContent']};start=1.;lines=[]
    for b in shot['content']['spokenContentBindings']:
        l=spoken[b['spokenContentId']];end=start+l['estimatedDurationMs']/1000
        lines.append({'spokenContentId':l['id'],'speakerKey':l['speakerKey'],'text':l['text'],'start':start,'end':end,
          'target':'场内对方','delivery':'正常语速，保留疑问或回应','afterLine':'等待回应','coverageIntent':b['coverageIntent']});start=end+.2
    raw['dialogue']=lines;raw['sourceSoundIntent']={'nativeAudioPolicy':'REQUIRED','canonicalDialogueBindings':[l['spokenContentId'] for l in lines]}
    raw['executionRequirements'].update(durationSeconds=dur,referenceRoles=['CHARACTER'])
    raw['cinematography'].update(composition='保留对话距离与空间方向',openingComposition='场内双方位置',endingComposition='场内双方位置')
    if s.sample['sceneNo']==7:
        raw['cinematography'].update(movementClass='DYNAMIC',movement='跟随会合方向缓移',trigger='队伍回到会点',motivation='在同一轴线内交代会合与再围关系')
        raw['executionRequirements'].update(performance={'temporal_adherence':'HIGH'}, motion={'horse_contact':'HIGH','camera_complexity':'HIGH'},continuity={'identity':'HIGH','spatial':'HIGH'})
    return {'spec':dump_contract(CinematicShotSpec.model_validate(raw)), 'context':ctx,'visual':visual,
            'reviewSummary':'DESIGN_ONLY source-bound contract exercise, not actual performance review'}
