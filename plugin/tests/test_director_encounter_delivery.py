"""S01 artistic-choice delivery, with authored responses and network denied.

This verifies the real owners/serializers, not a model's creativity or film quality.
The three selections are a new OFFLINE proposal, never historical S01 adoptions.
"""
from copy import deepcopy
import json
import socket

import httpx
import pytest

from drama_plugin.contracts.base import dump_contract
from drama_plugin.creative_engine.author_projection import author_payload
from drama_plugin.creative_engine.contracts import (AuthorRequest, Authority, CanonSubject,
    CreativeCheckpoint, Dialogue, SceneBody)
from drama_plugin.creative_engine.screenplay import ContextOriginal
from drama_plugin.film.contracts import (CanonScene, DeliveryProfile, DirectedShot,
    FilmCanon, FilmDirection, LanguageMetadata)
from drama_plugin.professional_design.asset_sequence import AssetPreparationPending
from drama_plugin.production.contracts import SourceDomain
from drama_plugin.runtime.contracts import CapabilityInput
from test_asset_sequence import (accept_pending, Author, plugin as sequence_plugin,
    request_for, resolve)
from test_event_scope_delivery import material, pipeline
from test_formal_author_backends import configured, canon, source, shot, REF
from test_work_aesthetic_delivery import evidence, semantic_art, wire_response, work_look


ENCOUNTERS = [
    dict(key='ensemble', purpose='合奏中体验手艺带来的暂时自在，也保留别人不由他支配的生活。',
        body='雅科夫肩颈随运弓承重，目光落在琴弓接触处，指尖接续当前乐句。',
        partner='罗斯柴尔德持长笛听取同伴节拍，准备接自己的乐句。',
        manager='沙希克斯仍留意桌边客人的需要。',
        camera='从乐手侧前方看肩颈与运弓；边缘客人的身体遮住局部，后席仍有独立活动。',
        light='桌侧暖实用光照到运弓的手与侧脸，背墙更暗，窗光只在远侧留下弱冷层。',
        color='暖肤色、旧木与灰褐衣料有区别，后席低亮度中保留冷暖层次。',
        action='雅科夫接续一个正在进行的乐句，罗斯柴尔德听着等待进入。',
        end='乐句交接已可被听见，身体仍处于合奏之中。',
        editorial='在乐句完成交接后允许切出，不额外停留展示乐手。'),
    dict(key='conflict', purpose='技术自信变成对同伴的压迫；婚宴的欢乐没有为冲突停下来。',
        body='雅科夫停止运弓但手仍握弓，身体朝向罗斯柴尔德，等待对方回答。',
        partner='罗斯柴尔德把长笛留在胸前，迎着雅科夫的视线，不继续吹奏。',
        manager='沙希克斯注意到两人之间的停顿，暂未介入。',
        camera='固定在两人侧面保持对视距离；客席从两人之间的后景可见，脸不同时正对镜头。',
        light='保留同一桌侧暖实用光，转身后的面部落入侧影，客席灯火仍在。',
        color='后景仍暖，人物衣料本色留在阴影中，冲突没有把房间整体变蓝。',
        action='两人停止合奏后相互面对，琴与长笛保持各自手中当前状态。',
        end='罗斯柴尔德没有回避目光，雅科夫的等待尚未得到服从。',
        editorial='让未获得回应的等待成立后切出，不靠额外怒容重复说明。'),
    dict(key='wages', purpose='工钱把逞强后的雅科夫放回雇佣关系；他听下一次是否还会被需要。',
        body='雅科夫手停在已装钱的衣袋口，抬眼等待沙希克斯回答。',
        partner='罗斯柴尔德在后侧擦拭自己的长笛，不为雅科夫的询问停下。',
        manager='沙希克斯在雅科夫面前停留，目光仍会掠向待照看的客席。',
        camera='在原乐手墙席一侧看两人的偏侧面与视线间隔；暖客席留在远景，桌沿占据下缘。',
        light='墙席处弱冷窗光成为面部主要来光，近处没有新增暖补光；远处实用灯仍暖，暗面保持低亮度。',
        color='近处肤色与灰褐衣料在弱冷光下仍有区别，远处婚宴暖色没有消失。',
        action='钱已入袋，雅科夫问出下次工作的事；沙希克斯听着，罗斯柴尔德继续擦笛。',
        end='问句结束，雅科夫仍在等答复，钱留在衣袋内。',
        editorial='保留问句后等答的关系，再交给回答镜头；不把收钱动作重演。'),
]
DOMAINS = tuple(sorted(SourceDomain(d) for d in
    ('ACTION', 'CAMERA', 'COLOR', 'EDITORIAL', 'LIGHTING', 'PERFORMANCE', 'SOUND', 'SUBJECTS', 'WORLD')))
WORK = 'offline-s01-encounter'
SCENE_TEXT = ('离线场景摘编，非正式剧本修订：婚宴上雅科夫、罗斯柴尔德与沙希克斯合奏；'
    '合奏中的支配转为冲突。冲突停止后，沙希克斯结工钱，雅科夫收钱并询问下次工作。'
    '罗斯柴尔德继续照料自己的长笛。人物一直在乐手墙席附近，房间光源未变。')


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('Offline encounter trace cannot contact any service')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)


def direction():
    return FilmDirection(shots=tuple(DirectedShot(scene_id='S01', shot_id=e['key'],
        shot=shot().model_copy(update=dict(purpose=e['purpose'], required_transition=e['end'],
            duration_ms=8000, subject_action=e['action'], entry_state=e['action'], exit_state=e['end'],
            coverage=e['camera'], blocking_intent='沿用乐手墙席及客席的关系，不新造房间。',
            camera_intent=e['camera'], editing_relation=e['editorial'], performance_direction=e['body'],
            spoken_ids=('next-work',) if e['key']=='wages' else (), professional_domains=DOMAINS)))
        for e in ENCOUNTERS))


async def selected_film(p):
    """Actual Host selection/binding and native film-direction author entry."""
    w = p.screenplays
    src = w.retain_context(ContextOriginal(work_id=WORK, label='offline-scene',
        status='DESIGNATED_SOURCE', text=SCENE_TEXT))
    w.begin(session_id='offline-film', work_id=WORK, scope='FILM',
        goal='Offline selected encounter', source_refs=(src,))
    w.retain_v1('offline-film', SCENE_TEXT)
    supports = {
        'Performance / Character Embodiment':'OFFLINE提案：由投入演奏、被打断、等答三种任务理解同一人的身体范围；'
            '不把愤怒刻进脸。依据本场动作作有限推论，不补人物生平。',
        'Cinematography / Production Design':'OFFLINE提案：观看正在做事的人，保留客席独立生活及局部遮挡；'
            '衣服允许劳动，空间不为展示人物而清空。代价是不能同时看清所有面部细节。',
        'Lighting / Color':'OFFLINE提案：婚宴暖色在冲突中继续，工钱处弱冷窗光占主；'
            '维持光源、服装本色和房间，冷峻来自位置与观看关系。备选为三个阶段始终暖光，'
            '它保留环境冷漠，但弱化受雇关系的视觉转折。'}
    for specialty,text in supports.items():
        w.support_packet('offline-film',specialty=specialty,question='如何实现这场关系，所得与所失是什么？')
        w.retain_support('offline-film',specialty=specialty,text=text,
            expected_revision=w.load('offline-film').revision)
    w.decide('offline-film', choice='KEEP_ALL',
        reason='OFFLINE Host 保留独立剧本。选择劳动身体、侧面观看与暖宴/冷墙席反差；'
               '保留冲突时暖色反衬，接受部分脸部不可见；不采用孤立人物展示。',
        expected_revision=w.load('offline-film').revision)
    h = w.bind_selection('offline-film', work_id=WORK, scene_id=None)
    look = work_look(WORK, '从共同劳动的投入，到对同伴的压迫，再到等待雇主答复；摄影随关系改变观看立场。')
    look['sourcePins'] = [dump_contract(src), dump_contract(w.load('offline-film').decision_refs[-1])]
    look['grammarRules'][0].update(domain='DIRECTOR', narrativeReason='手艺的自足与雇佣的依赖并存。',
        appliesWhen='这份离线 S01 提案', exception='温暖可以继续存在而人物已被排除。', exitCondition='进入其他生活关系后重新判断。')
    look['evolution'] = [dict(scopeId='S01:'+e['key'], perceptualOwner='场景关系中的观众',
        narrativeChange=e['purpose'], ruleIds=[look['grammarRules'][0]['ruleId']], realization=e['camera']) for e in ENCOUNTERS]
    pin = w.objects.put('offline-selected-directing-choice', look)
    # An available but unselected alternative must not enter any author request.
    w.objects.put('offline-unselected', {**look, 'grammarRules':[{**look['grammarRules'][0],
        'execution':'UNSELECTED: all three moments become isolated heroic portraits'}]})
    bound = await p.tools.invoke('screenplay.bind_professional_context', handoff_ref=h,
        work_id=WORK, scene_id=None, design_refs=(pin,))
    scene = SceneBody(scene_text=SCENE_TEXT, subjects=tuple(CanonSubject(id=i, name=n, meaning=m) for i,n,m in
        [('yakov','雅科夫','手艺自信并依赖受雇'), ('rothschild','罗斯柴尔德','有自己的音乐劳动与尊严'),
         ('schild','沙希克斯','照看生意并管理乐手')]),
        dialogue=(Dialogue(id='next-work', speaker='yakov', text='В следующий раз?'),))
    film = FilmCanon(work=canon().work.model_copy(update={'interpretation':'婚宴里的手艺、冲突与雇佣关系',
        'dramatic_intent':'劳动能力与受雇处境并存','character_meaning':'三人有各自的劳动与注意对象'}),
        script=canon().script.model_copy(update={'screenplay':SCENE_TEXT}), scenes=(CanonScene(scene_id='S01', scene=scene),))
    run = p.create_source_film_run(work_id=WORK, run_id=WORK,
        source=source().model_copy(update={'text':SCENE_TEXT}), screenplay_ref=bound,
        languages=LanguageMetadata(source_document_language='zh', original_work_language='ru', spoken_language='ru', authority_ref=REF),
        profile=DeliveryProfile(width=1280,height=720), rights_refs=(REF,), route='offline', model='seedance-2-standard')
    p.film.store.put_author(run.run_id, film)
    inp = CapabilityInput(run_id=run.run_id, scope=run.scope, operation_id='offline-direct')
    calls = []
    def receive(wire):
        data=json.loads(wire.content); payload=json.loads(data['messages'][1]['content'])
        calls.append({'system':data['messages'][0]['content'], 'payload':payload})
        if data['model']=='offline-canon-model':
            assert 'filmLook' not in json.dumps(payload)
            return wire_response({'choice':'KEEP_ALL','reason':'OFFLINE preserve scene','text':None}
                if 'preservedV1' in payload else {'text':SCENE_TEXT})
        assert payload['filmLook'][0]['evolution'] == look['evolution']
        assert 'UNSELECTED' not in json.dumps(payload)
        return wire_response({'shots':[{'sceneSelection':0, 'transition':'cut', 'requiresSelections':[],
            'shot':{**s.shot.model_dump(mode='json',by_alias=True,exclude={'spoken_ids'}),
                'spokenSelections':[0] if s.shot.spoken_ids else []}} for s in direction().shots]})
    p.film.direction_author.client.transport=httpx.MockTransport(receive)
    result=await p.film.direction(inp)
    assert result.status.value=='SUCCEEDED'
    evidence('s01-01-selected-direction', {'qualification':'OFFLINE_AUTHORED_FIXTURE',
        'supportOriginals':[w.objects.read_ref(r) for r in w.load('offline-film').support_refs],
        'hostDecision':w.objects.read_ref(w.load('offline-film').decision_refs[-1]),
        'choice':look, 'calls':calls, 'direction':dump_contract(p.film.store.author(p.film.store.checkpoint(run.run_id).direction_ref, FilmDirection))})
    return inp


def professional_result(e):
    _, rows = material(single=True)
    by = {r['domain']:r['facts'] for r in rows}
    spoken = [0] if e['key']=='wages' else []
    entry={'ensemble':'三名乐手已在演奏，客席仍在交谈。',
        'conflict':'合奏已停，两位乐手相互面对。',
        'wages':'钱已入袋，雅科夫与沙希克斯相对，罗斯柴尔德在后侧。'}[e['key']]
    by['ACTION']={'actionPhases':[dict(beatSelection=0, spokenSelections=spoken,
        entryState=entry, action=e['action'], observable=e['end'])],
        'physicalStateConstraints':'小提琴、琴弓与长笛保持各自构造及持有者。'}
    perf=by['PERFORMANCE']
    perf['sceneDPD'].update(dramaticPurpose=e['purpose'], conflictCondition='他人有自己的任务。',
        powerStructure='手艺能力不等于对同伴和雇主的支配。')
    perf['sceneDPD']['direction'].update(objective=e['purpose'], interactionTargetSelection=1,
        tactic='完成当前任务并注意对方', authorityPosition='受雇乐手', relationshipStance='依当前关系行动',
        publicPrivateContext='婚宴公众空间')
    perf['beats']=[dict(actorSelection=i, targetSelection=1 if i==0 else 0,
        objective=e['purpose'] if i==0 else '继续自己的劳动', obstacle='他人的任务未与自己同步',
        tactic='在当前任务中留意对方', note='OFFLINE_BODY_REASON', transitionTrigger='对方当前行动',
        direction={'tactic':'留意对方'}, physicalExpression=body)
        for i,body in enumerate((e['body'],e['partner'],e['manager']))]
    perf['projectionSubjects']=[dict(subjectSelection=i, role='INTERACTIVE_PARTNER', beatSelections=[i]) for i in range(3)]
    perf['lines']=[dict(spokenSelection=0, beatSelection=0, dramaticAction='询问下次工作',
        observableIntent='等候回答', continuity='钱已经入袋', changeFromPrevious='冲突后仍需要工作')] if spoken else []
    by['CAMERA']={'cameraPosition':e['camera'], 'movement':{'policy':'当前观察位置保持固定。'},
        'continuityInterpretation':e['purpose']}
    by['WORLD']={'setting':'同一婚宴房间，乐手墙席、客席、窗与实用灯的位置保持原有关系。'}
    by['SUBJECTS']={'presentSubjects':[dict(subjectSelection=i, role=name, inSceneBehaviour=body)
        for i,(name,body) in enumerate(zip(('雅科夫','罗斯柴尔德','沙希克斯'),
            ('雅科夫仍持有自己的小提琴与琴弓。',e['partner'],e['manager'])))]}
    by['SOUND']={'ambience':[{'design':'客席谈话和餐具声仍来自婚宴空间。'}], 'orderingRules':[],
        'audio_events':[dict(spokenSelection=0, delivery_mode='ON_SCREEN', performance='自然问出一次，听对方回答。',
            continuity='问后留在等待中。')] if spoken else []}
    by['EDITORIAL']={'temporalStructure':'当前动作与听者持续任务共同推进。',
        'protectedEvents':[dict(phaseIndex=0, design=e['editorial'])]}
    by['LIGHTING']={'sources':e['light'], 'directionAndQuality':'面部与背景保留所选方向及亮暗差，物件材质不变。',
        'continuityInterpretation':'OFFLINE_LIGHT_REASON: 同一光源体系下改变可见关系，不能由调色替代。'}
    by['COLOR']={'scenePalette':e['color'], 'continuityInterpretation':'OFFLINE_COLOR_REASON: 当前阶段，不向邻镜复制。'}
    return [{'domain':domain,'facts':facts} for domain,facts in by.items()]


@pytest.mark.asyncio
async def test_selected_encounter_reaches_assets_professionals_and_final_video(monkeypatch,tmp_path):
    p=configured(monkeypatch,tmp_path/'film')
    inp=await selected_film(p)
    requests=[]
    for slot in range(3):
        unit=p.film.create_unit(inp,slot)
        run=p.runtime.store.load(unit.creative_run_id)
        p.creative.state.save(run.run_id,run.scope,CreativeCheckpoint(refs=unit.refs))
        requests.append(p.creative._request(CapabilityInput(run_id=run.run_id, scope=run.scope,
            operation_id='offline-professional'), Authority.PROFESSIONAL))
    calls=[]; stage={'reference':None,'professional':None}
    def receive(wire):
        data=json.loads(wire.content); payload=json.loads(data['messages'][1]['content'])
        calls.append({'system':data['messages'][0]['content'], 'payload':payload})
        assert 'sceneDirectionRefs' not in json.dumps(payload) and 'UNSELECTED' not in json.dumps(payload)
        shared=payload['hostScreenplay']['sceneDirection']
        assert len(shared['shots'])==3 and 'sourceRefs' not in shared
        if stage['professional']:
            assert 'currentShotSelection' in shared
            return wire_response(professional_result(stage['professional']))
        assert 'currentShotSelection' not in shared and 'shot' not in payload
        if stage['reference']:
            return wire_response(semantic_art(stage['reference'], stage['reference']['design']['material']))
        assert all(e['purpose']==row['shot']['purpose'] for e,row in zip(ENCOUNTERS,shared['shots']))
        return wire_response({'assets':[
            {'assetType':'CHARACTER','name':name,'subjectSelection':i,'design':{
                'face':'离线占位身份，非参考图人物：'+name,
                'material':'旧灰褐外衣与米白内衫保持哑光层次。',
                'costume':'肩肘与领口留有劳动活动余量，不以固定耸肩或僵硬正面姿态建立身份。',
                'proof':'选定人物的头颈肩与衣服连接可辨，表情不固定为愤怒、疲倦或含笑。'}}
            for i,name in enumerate(('雅科夫','罗斯柴尔德','沙希克斯'))],
            'rationale':'OFFLINE fixture: preserve body range across selected ensemble/conflict/wages, no new cast.'})
    author=p.professional_design.author
    author.client.transport=httpx.MockTransport(receive)
    # Start at wages. Asset preparation must still receive the WHOLE encounter.
    with pytest.raises(AssetPreparationPending) as pending:
        await p.professional_design.prepare_assets(requests[2])
    packet=p.asset_sequence.objects.read_ref(pending.value.ref)
    scoped=AuthorRequest.model_validate(packet['referenceAuthorContext'])
    assert scoped.shot is None and scoped.scope.shot_id is None
    for item in packet['requirements']:
        stage['reference']=item
        await author.design_asset_reference(scoped,item)  # text-only MockTransport; no image request submission
    stage['reference']=None
    await accept_pending(p,pending.value)  # isolated metadata fixtures, not formal production adoptions
    ready=[]
    for req in requests:
        ready.append(await p.professional_design.prepare_assets(req))
    assets=[r.professional_context['assetSequence']['currentAssets'] for r in ready]
    assert [a['id'] for a in assets[0]]==[a['id'] for a in assets[2]]
    evidence('s01-02-asset-authors', {'qualification':'OFFLINE_AUTHORED_FIXTURE',
        'calls':calls[:], 'referenceAuthorContext':packet['referenceAuthorContext'],
        'selectedAssetDesigns':[r['design'] for r in packet['requirements']]})
    for e,req in zip(ENCOUNTERS,ready):
        stage['professional']=e
        before=deepcopy(req.model_dump())
        designs=await p.professional_design.design(req)
        assert req.model_dump()==before
        monkeypatch.setattr('test_event_scope_delivery.professional_projection',
            lambda _raw,_req: [dump_contract(d) for d in designs])
        _,_,_,outputs=await pipeline(tmp_path/e['key'],monkeypatch,req,professional_result(e),plugin=p)
        wire=outputs[0]['wire']; text=wire['content'][0]['text']
        for selected in ('body','partner','camera','light','color','editorial'):
            assert e[selected] in text
        assert text.count(e['body'])==1 and text.count(e['camera'])==1
        for other in ENCOUNTERS:
            if other is not e:
                assert other['camera'] not in text and other['light'] not in text
        assert all(label not in text for label in ('OFFLINE_BODY_REASON','OFFLINE_LIGHT_REASON',
            'OFFLINE_COLOR_REASON','sceneDirection','UNSELECTED'))
        assert e['purpose'] not in text
        assert not outputs[0]['ready'].provider_submission_allowed
        evidence('s01-03-video-'+e['key'], {'qualification':'OFFLINE_AUTHORED_FIXTURE',
            'authorInput':calls[-1], 'professionalOriginals':[dump_contract(d) for d in designs],
            'finalRequest':wire, 'submissionAllowed':False})
    await p.aclose()


@pytest.mark.asyncio
async def test_earlier_scene_assets_use_pinned_direction_and_recovery_keeps_prepared_original(monkeypatch,tmp_path):
    class Capture(Author):
        def __init__(self):
            super().__init__(); self.inputs=[]
        async def design_assets(self,request):
            self.inputs.append(request)
            return await super().design_assets(request)
    author=Capture(); p=sequence_plugin(tmp_path,monkeypatch,author)
    # A separately selected screenplay used to displace the director context.
    w=p.screenplays; work='offline-sequence'
    src=w.retain_context(ContextOriginal(work_id=work,label='offline-source',status='DESIGNATED_SOURCE',text='Offline source'))
    film=w.retain_context(ContextOriginal(work_id=work,label='offline-film',status='ADOPTED_FACT',
        text='Five ordered scenes',authority_ref='offline-film-fixture'))
    packets=[]
    for i in range(1,6):
        session=f'selected-scene-{i}'; sid=f's-{i}'
        w.begin(session_id=session,work_id=work,scope='SCENE',scene_id=sid,goal='Offline scene',
            source_refs=(src,film),full_film_ref=film)
        w.retain_v1(session,f'Complete scene {i}')
        w.decide(session,choice='KEEP_ALL',reason='Offline selection',expected_revision=1)
        packets.append(w.objects.read_ref(w.bind_selection(session,work_id=work,scene_id=sid)))
    child_input,old=request_for(p,'s-3',scene_packets=packets)
    old_context=deepcopy(old.screenplay_context)
    parent=p.runtime.store.load('offline-film-sequence')
    cp=p.film.store.checkpoint(parent.run_id)
    old_direction=p.film.store.author(cp.direction_ref,FilmDirection)
    p.film.store.put_author(parent.run_id,old_direction.model_copy(update={'shots':tuple(s.model_copy(
        update={'shot':s.shot.model_copy(update={'purpose':'NEW_DIRECTION_'+s.scene_id})}) for s in old_direction.shots)}))
    _,pending=await resolve(p,old,author)
    assert pending==['s-1','s-2','s-3']
    for i,request in enumerate(author.inputs,1):
        assert request.scope.scene_id==f's-{i}'
        assert request.screenplay_context['screenplay']['text']==f'Complete scene {i}'
        raw=request.screenplay_context['sceneDirection']
        assert raw['sourceRefs'][1]==dump_contract(cp.direction_ref)
        assert 'currentShotSelection' not in raw
        payload=author_payload(request)
        assert 'sceneDirectionRefs' not in json.dumps(payload)
        assert 'NEW_DIRECTION' not in json.dumps(payload)
    replay=p.creative._request(child_input,Authority.PROFESSIONAL)
    assert replay.screenplay_context==old_context
    count=len(author.inputs)
    await p.professional_design.prepare_assets(replay)
    assert len(author.inputs)==count
    _,new=request_for(p,'s-4')
    with pytest.raises(AssetPreparationPending):
        await p.professional_design.prepare_assets(new)
    assert len(author.inputs)==count+1  # prior prepared/adopted assets are not rewritten
    assert author.inputs[-1].screenplay_context['sceneDirection']['shots'][0]['shot']['purpose']=='NEW_DIRECTION_s-4'
    evidence('s01-04-recovery-and-cross-scene', {'qualification':'OFFLINE_GENERIC_REGRESSION',
        'earlierScenesUsedPinnedDirection':True, 'retainedChildUnchanged':True,
        'oldPreparedAssetsNotReauthored':True,
        'authorContexts':[author_payload(r) for r in author.inputs]})
    await p.aclose()
