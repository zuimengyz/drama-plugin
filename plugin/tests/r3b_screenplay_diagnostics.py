"""Non-creative annotations of the unchanged F01-R2 source, never adoption.

Existing DPD tasks are referenced/reused. No replacement dialogue or scene body
is written. S04 examines the explicitly bounded waiting-in-the-grave slice.
"""
from copy import deepcopy
import json
from pathlib import Path
import re

from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.contracts.dpd import BeatDPD
from drama_plugin.contracts.scene_dramaturgy import ResponseInterpretation
from drama_plugin.scene_dramaturgy import scene_body_hash
from r3b_helpers import carrier, authored_review, playability

ROOT = Path(__file__).parent / 'fixtures/screenplay_r2'


def diagnostic(sid):
    pack = json.loads((ROOT / 'performance-sidecar.json').read_text())
    original = next((x for x in pack['scenes'] if x['source']['id'] == sid), None)
    if sid == 'S04':
        text = (ROOT / '04-screenplay-r2.md').read_text()
        body = re.search(r'## S04.*?(?=\n## S05)', text, re.S).group(0)
        excerpt = body[body.index('水滴碰到他闭着的眼皮。'):body.index('他忽然可以看见了。')].strip()
        scene = {'id':'S04-suspension-diagnostic','content':{'revisionId':'F01-R2-S04-excerpt',
            'screenplayAction':excerpt,'spokenContent':[],'characters':['男人']}}
        cs = [carrier(scene, '水滴碰到他闭着的眼皮。', None, None, 'ENVIRONMENT'),
              carrier(scene, '下一滴迟迟不来。', None, None, 'ENVIRONMENT'),
              carrier(scene, '水终于又落下。', None, None, 'ENVIRONMENT')]
        facet = dict(sourceBodyHash=scene_body_hash(scene),carriers=cs,interactions=[],information=[],
            entryState={'subjectiveUnknown':'无法解释地下经验'},exitState={'subjectiveUnknown':'无法解释地下经验'},
            stateEvidence=[c['ref'] for c in cs],suspensionReason='原作主观梦境中的等待片段；不解释现实机制、不新增对手。')
        scene['content']['dramaturgy'] = facet
        return dict(source=scene,dpds={},review=authored_review(scene,{}),diagnosticOnly=True)
    scene = deepcopy(original['source'])
    scene['content']['characters'] = sorted({b['actor'] for b in original['beats']})
    cs=[];dpds={};edges=[]
    beats={b['beatId']:BeatDPD.model_validate(b) for b in original['beats']}
    lines={x['id']:x for x in scene['content']['spokenContent']}

    def action(text, actor, target, role='STIMULUS', cause=None, important=False, silence=None):
        c=carrier(scene,text,actor,target,role,cause=cause,important=important,silence=silence);cs.append(c);return c

    def spoken(number, cause=None):
        line=lines[sid+'-L'+str(number)]
        c=carrier(scene,line['text'],line['speakerKey'],line['target'],'ACTION',line=line['id'],cause=cause)
        cs.append(c);return c

    def task(source_beat, action_c, reaction_c, trace=None):
        base=beats[source_beat]
        key=sid+':carrier:'+action_c['ref']
        dpds[key]=base.model_copy(update={'beat_id':key,'playability':playability(scene,action_c,reaction_c),
                                        'response_interpretations':tuple([trace] if trace else [])})
        return key

    info=[];pending=[]
    if sid=='S01':
        for i in range(1,6):spoken(i)
        wait=action('他停住，回头听。','男人','桌边朋友','SILENCE',important=True,silence='WAITING')
        absence=action('屋里又争起那张纸上的事，没有人叫他。',None,None,'ENVIRONMENT',cause=wait['ref'],silence='ENVIRONMENTAL')
        leave=action('他继续往下走。','男人','桌边朋友','AFTERMATH',cause=absence['ref'])
        pending=[('S01-exit',wait,leave,None)]
        entry={'contact':'停下听房内'};exit_state={'contact':'无人叫他，继续下楼'}
    elif sid=='S03':
        spoken(1)
        sleeve=action('他看见自己衣袖上的褶，用手掌抹平。','男人','自己')
        hand=action('那只手抬到身前，手掌朝下，停住。','男人','自己','REACTION',cause=sleeve['ref'])
        spoken(2)
        cough=action('孩子咳嗽。',None,None,'ENVIRONMENT')
        action('他的目光从桌面移向门。','男人','门外的孩子','REACTION',cause=cough['ref'])
        spoken(3)
        again=action('说完，孩子又咳了一次。',None,None,'ENVIRONMENT')
        door=action('他起身，走到门前。手放上门把，却没开。','男人','门外的孩子','SILENCE',cause=again['ref'],important=True,silence='PROCESSING')
        withdrawal=action('他回到桌前，把椅子拉近。','男人','门外的孩子','AFTERMATH',cause=door['ref'])
        pending=[('S03-respond',door,withdrawal,None)]
        entry={'pressure':'试图结束生命的决定'};exit_state={'pressure':'未开门也未拿枪，仍受门外动静影响'}
    else:
        action('他停下，望着那颗星。','男人','自己')
        touch=action('一只小手拉住他的手肘。','女孩','男人')
        action('他停住脚，身体还朝着原来的方向。','男人','女孩','RESPONSE',cause=touch['ref'])
        l1=spoken(1)
        action('她拉着他的手肘，往另一条街退。','女孩','男人')
        listen=action('男人这才转过脸，听她说。','男人','女孩','RESPONSE',cause=l1['ref'])
        misread=action('她以为他要跟来，先走出一步。','女孩','男人','REACTION',cause=listen['ref'])
        action('他的手抬起一点，停在她肩旁。','男人','女孩')
        l2=spoken(2,cause=listen['ref'])
        withdraw=action('他收回手，身体仍朝着自己要走的方向。','男人','女孩','RESPONSE',cause=l2['ref'])
        l3=spoken(3)
        regrab=action('女孩又抓住他，拉向另一条街。','女孩','男人','RESPONSE',cause=l3['ref'])
        action('男人猛地跺了一下脚。','男人','女孩')
        l4=spoken(4,cause=regrab['ref'])
        recoil=action('女孩松手，往后缩了一步。','女孩','男人','RESPONSE',cause=l4['ref'])
        breath=action('男人喘了一口气。','男人','女孩','AFTERMATH',cause=recoil['ref'])
        see=action('女孩看见街对面的行人','女孩','街对面的行人','TRIGGER')
        action('立刻绕开他跑过去','女孩','街对面的行人','ACTION',cause=see['ref'])
        action('继续叫先生','女孩','街对面的行人','AFTERMATH')
        action('他走进自己的楼门。','男人','自己','AFTERMATH')
        for a,response,nxt,change in [(l1,listen,l2,False),(l2,withdraw,None,False),(l3,regrab,l4,True),(l4,recoil,None,False)]:
            a['important']=True
            edges.append(dict(actionRef=a['ref'],responseRef=response['ref'],nextActionRef=nxt['ref'] if nxt else None,strategyChange=change))
        def interpretation(a,response,expected,meaning,nxt=None,reason=None):
            return ResponseInterpretation(action_ref=a['ref'],response_ref=response['ref'],expected_response=expected,
                interpretation=meaning,next_beat_id=sid+':carrier:'+nxt['ref'] if nxt else None,transition_reason=reason)
        pending=[
            ('S02-appeal',l1,misread,interpretation(l1,listen,'男人跟自己去妈妈那里','她以为转脸表示要跟来')),
            ('S02-deflect',listen,listen,None),
            ('S02-appeal',l2,regrab,interpretation(l2,withdraw,'男人立即跟来','收回手，没有跟随')),
            ('S02-deflect',withdraw,withdraw,None),
            ('S02-deflect',l3,breath,interpretation(l3,regrab,'女孩放开，让他离开','女孩又抓住，推开求助未奏效',l4,'抽袖后又被抓住，源下一行动转为喝斥')),
            ('S02-appeal',regrab,regrab,None),
            ('S02-repel',l4,breath,interpretation(l4,recoil,'女孩松手退开','女孩已经松手后缩')),
            ('S02-appeal',recoil,recoil,None)]
        info=[dict(informationRef='S02-first-request',parts={'mother':'母亲出事','help':'需要帮助','follow':'要求跟随','urgency':'事情急迫'},
            releases=[dict(carrierRef=l1['ref'],parts=['mother','help','follow','urgency'],audience=True,characters=['男人'])],
            notBefore=listen['ref'])]
        entry={'relationship':'尚未进入女孩的求助处境'};exit_state={'relationship':'拒绝后进门，袖上留下接触痕迹'}
    scene['content']['dramaturgy']=dict(sourceBodyHash=scene_body_hash(scene),carriers=cs,interactions=edges,
        information=info,entryState=entry,exitState=exit_state,stateEvidence=[cs[0]['ref'],cs[-1]['ref']])
    for args in pending:task(*args)
    concerns=[]
    if sid=='S02':
        concerns=[dict(axis='INFORMATION_RELEASE',scope='S02-first-request',status='CONCERN',finding='DRAMATICALLY_PREMATURE',
            reason='首次身体停住不等于参与女孩处境；四项核心信息在真正转脸/误判/撤手之前完整释放。R3A Scene 过程审阅，不是禁直接陈述。',
            evidenceRefs=[l1['ref'],listen['ref'],withdraw['ref']],repairOwner='scene-development')]
    review=authored_review(scene,dpds,concerns=concerns)
    review['isolationEvidence']='R3A上下文内来源诊断，非独立冷读；未批准新的创作事实。'
    return dict(source=scene,dpds=dpds,review=review,diagnosticOnly=True)
