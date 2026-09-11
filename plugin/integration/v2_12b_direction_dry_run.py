#!/usr/bin/env python3
"""Host-authored A-D using fresh formal snapshots and retrieved assets; writes IR only."""
import json
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from drama_plugin.contracts.asset import Asset
from drama_plugin.contracts.base import dump_contract,sha256_canonical as fp
from drama_plugin.contracts.cinematic import CinematicShotSpec
from drama_plugin.creative_assets import pattern_ref
from drama_plugin.visual.cinematic import narrative_source,resolve_visual_bible,freeze_direction,verify_frozen,selection_handoff

out=Path(sys.argv[1]);source=json.loads((out/'gaixia-context.json').read_text())
assets={r['key'].split('/')[-1]:Asset.model_validate(r['asset']) for r in json.loads((out/'seed-assets-persistence-result.json').read_text()) if 'asset' in r}
search=json.loads((out/'cinematic-language-search-result.json').read_text())
results={}

def save(name,data): (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def snake(e):
    v=deepcopy(e)
    for c,s in [('workId','work_id'),('scriptId','script_id'),('episodeId','episode_id'),('sceneId','scene_id')]:
        if c in v:v[s]=v.pop(c)
    return v

for code,no,keys in [('A','G06',['restrained-motivated-push-in']),('B','G23',['post-line-hold','multi-beat-micro-expression']),('C','G01',[])]:
    sh=next(x for x in source['shot'] if x['shotNo']==no)
    sc=next(x for x in source['scene'] if x['id']==sh['sceneId'])
    ep=next(x for x in source['episode'] if x['id']==sc['episodeId'])
    script=next(x for x in source['script'] if x['id']==ep['scriptId'])
    ctx={k:snake(v) for k,v in dict(work=source['work'],script=script,episode=ep,scene=sc,shot=sh).items()}
    c=sh['content'];duration=c['plannedDurationMs']/1000
    night=no=='G06'
    light='营火从场内侧面照来，火外保留暗部' if night else '日间天光保持同一方向，面部亮度服从朝向'
    base={'realism':'保留汗尘、布甲与器物使用痕迹，不美容抹平',
        'palette':{'dominant':['布土本色'],'accent':['局部火暖'] if night else []},
        'lighting':{'philosophy':light,'fill':'仅场景已有反射','faceShadowAllowed':True},
        'imageCharacter':{'saturation':'服从材质本色','contrast':'动作和眼神可读','highlight':'保留高光纹理','blackLevel':'阴影不自动抬灰'},
        'materials':{'skin':'汗尘延续前镜','costume':'布甲磨损连续','metal':'反射有来源','environment':'场地随行动受力'},
        'atmosphere':'不另造天气、烟雾或新剧情','cameraPhilosophy':'随信息与人物行动观察，不以镜头替观众预判结局','forbidden':[]}
    visual=resolve_visual_bible(base,{'episode':{},'scene':{},'shot':{}})
    opening=c['opening'];ending=c['endingAndTransition']
    if code=='A':
        rows=[(0,3,'ACTION','项羽停在领粮处','楚卒放低碗，项羽经过后停住；军吏把空粮器放正。'),
          (3,5.5,'DIALOGUE','问话落下','项羽看着粮器，向军吏发问；没有朝观众转正。'),
          (5.5,8,'DIALOGUE','确认粮尽','军吏仍持空粮器回答，不拿第二份物件解释。'),
          (8,11,'REACTION','项羽听到外围声音','项羽看空粮器的视线停住，呼吸短收，再看营垒边的伤兵；摄影机在视线停住之后轻微靠近，确认信息后停住。'),
          (11,14,'HOLD',ending,'近处碗碰声停止，项羽侧脸听外围楚调；军吏留在原处收回空粮器。')]
        slots=[(3,5.5),(5.5,8)]
        camera=dict(movementClass='RESTRAINED',movement='经过时略移，回报后轻微靠近，人物意识到粮尽后停住；收尾保留转向营垒的空间',amplitude='幅度很小，不环绕或加速',trigger='军吏回答后项羽的视线在空粮器上停住',motivation='把注意力收拢到粮尽被理解的瞬间，不提前宣判败局')
        purpose='在原领粮镜头的略移内吸收CL-01的先反应后靠近和停住，不添加新剧情。'
    elif code=='B':
        rows=[(0,2,'ACTION','项羽望向江对岸','项羽看江面，呼吸未恢复平稳；亭长的手仍在前景等待。'),
          (2,15,'DIALOGUE','项羽说完对父兄的问句','前段视线留对岸，随后转回仅余骑者；提到父兄时看亭长，句间压住呼吸，嘴角收紧后松开以继续说话，不用同一悲愤表情贯穿。'),
          (15,17,'REACTION','船边那只脚收回','问句落下，项羽仍看着亭长；下颌压住一次呼吸，收回船边的脚。'),
          (17,19,'HOLD','亭长还在等','镜头继续停留；亭长未立刻收手，项羽看到那只手却没有向船走去。'),
          (19,21,'REACTION',ending,'项羽目光从等候的手移开，转向坐骑，结束在下一镜双人关系可衔接的位置。')]
        slots=[(2,15)]
        camera=dict(movementClass='LOCKED',movement='保持中近景，让说完后的无言反应继续',amplitude='无')
        purpose='CL-10拆解江面、骑者、亭长之间的注意力变化；CL-02用于台词后仍不登船的可见选择。'
    else:
        rows=[(0,4,'ACTION','汉卒被同伴接住','盾被顶退，同伴接住踉跄汉卒，楚军自左向右推进。'),
          (4,10,'ACTION','楚卒继续跟上','项羽逼退近前持兵者后回望自己队伍；近卒跟上，远处汉军仍退，不停下接受欢呼。'),
          (10,14,'ACTION',ending,'楚方队列继续推进，一名后撤汉卒沿既定方向退到右沿，保留接入汉军阵后的方位。')]
        slots=[];camera=dict(movementClass='MOTIVATED',movement='随队列横移',amplitude='服从原队列速度',trigger='楚军战线推进',motivation='保持双方相对方向与项羽所处队列可读')
        purpose='动作与战线方位已承担叙事；反应/克制/台词模式不适用，选择零引用。'
    beats=[];entry=opening
    for start,end,kind,state,behavior in rows:
        beats.append(dict(start=start,end=end,kind=kind,startState=entry,actions=[{'actor':'场内人物','behavior':behavior}],endState=state));entry=state
    spoken={s['id']:s for s in sc['content']['spokenContent']}
    dialogue=[]
    for binding,(a,b) in zip(c['spokenContentBindings'],slots):
        line=spoken[binding['spokenContentId']]
        dialogue.append(dict(spokenContentId=line['id'],speakerKey=line['speakerKey'],text=line['text'],start=a,end=b,
            target='当前叙事对象',delivery=line['performanceIntent'],afterLine='按后续反应beat保持场内关系，不立即切镜',coverageIntent=binding['coverageIntent']))
    refs=[dump_contract(pattern_ref(assets[k],purpose)) for k in keys]
    spec=CinematicShotSpec.model_validate(dict(workId=source['work']['id'],sceneId=sc['id'],shotId=sh['id'],creativeRevision='v2-12b-dry-'+code,
        sourceFingerprint=fp(narrative_source(ctx)),visualBibleFingerprint=visual['fingerprint'],narrativeIntent=c['narrativePurpose'],visualBible=visual['effective'],durationSeconds=duration,
        openingState=opening,anchorOmissionReason='原镜头已明确正在发生的行动；保留既有开场，不加准备程序',
        performance={'objective':c['actionAndPerformance'],'interactionTarget':'当前场内人物','beats':beats},dialogue=dialogue,
        cinematography={**camera,'shotSize':c['cameraLanguage'],'composition':'保留原镜头的前后景及人物关系','placement':'原叙事观察侧','height':'服从人物与道具可读关系','subjectOrientation':'保持既定相对方向','lensIntent':'自然透视，无无因焦距变化','focusTarget':'当前说话或行动者及其相关物件','focusTransition':'随叙事注意力，不添加炫技拉焦','openingComposition':opening,'endingComposition':ending},
        lighting=light,secondaryMotionOmissionReason='本轮验证知识引用，不额外增设持续环境运动',
        stabilityContract=[{'dimension':'canon','allowed':'对既有行为与摄影时序作细化','forbidden':'新增对白、人物、事件或改变空间方向','reason':'保护正式文本事实'}],
        executionRequirements={'durationSeconds':duration,'performance':{'temporal_adherence':'HIGH'},'motion':{'camera_complexity':'LOW'},'continuity':{'identity':'HIGH'},'referenceRoles':[],'timingIntent':'遵守正式总长和对白估时，停留来自剧情'},
        endingState=ending,cinematicLanguageRefs=refs,sourceSoundIntent={'nativeAudioPolicy':'REQUIRED','canonicalDialogueBindings':[d['spokenContentId'] for d in dialogue],'generatedMusic':'FORBIDDEN'}))
    frozen=freeze_direction(spec,context=ctx,visual_resolution=visual,host_review='V2-12B text-only：核对正式父链、对白全文与估时；仅在artifact中细化执行，不修改正式Shot或生成视频。')
    handoff=selection_handoff(frozen)
    assert all(a.id not in handoff['motion_prompt'] for a in assets.values())
    save('dry-run-'+code+'-context.json',ctx);save('dry-run-'+code+'-spec.json',dump_contract(spec));save('dry-run-'+code+'-frozen.json',frozen)
    (out/('dry-run-'+code+'-execution.md')).write_text(handoff['motion_prompt']+'\n')
    results[code]={'shotId':sh['id'],'shotNo':no,'status':'VERIFIED_TEXT_ONLY','selected':refs,'reason':purpose,
        'searchEvidence':'cinematic-language-search-result.json','sourceFingerprint':spec.source_fingerprint,'frozenFingerprint':frozen['fingerprint'],'formalShotWrites':0}
    if code=='A':
        before=deepcopy(frozen);asset=assets[keys[0]].model_copy(deep=True);old=fp(asset.content);asset.content['purpose']='isolated simulated revision B'
        assert fp(asset.content)!=old and verify_frozen(frozen).cinematic_language_refs[0].content_fingerprint==old and frozen==before
        results['D']={'status':'VERIFIED_OFFLINE','revisionA':old,'revisionB':fp(asset.content),'historicalReference':old,'formalAssetUpdates':0}
save('cinematic-direction-retrieval-dry-run.json',results)
print(json.dumps({k:{'status':v['status'],'refs':len(v.get('selected',[]))} for k,v in results.items()}))
