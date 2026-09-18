"""Authored score design fixtures; no formal promotion, media or provider calls."""
from __future__ import annotations
from typing import Any
from drama_plugin.contracts.base import sha256_canonical as fp,dump_contract
from drama_plugin.contracts.film_score import FilmScorePlan,MusicCue,SceneMusicDecision,ScorePalette,ScoreMotif,MusicGenerationRequirements
from drama_plugin.contracts.sequence import SourcePin
from drama_plugin.contracts.performance_direction import DirectorPerformanceIntent
from drama_plugin.music_direction import review_score_plan,composer_brief


def silent_plan(scope: str, pins: tuple[SourcePin,...], film_ref: SourcePin,
                intents: dict[str,DirectorPerformanceIntent], source_kind: str='DESIGN_FIXTURE_ONLY') -> FilmScorePlan:
    return FilmScorePlan.model_validate(dict(scope_id=scope,source_kind=source_kind,source_pins=pins,film_intent_ref=film_ref,
        scene_ids=tuple(intents),score_thesis='让角色完成具体任务和选择，由原生行动声保留实际代价；本轮没有另需音乐提供的信息。',
        score_world='可听见人物所在空间的真实工作，不另设情绪旁观者',score_palette=dict(timbre='无新增配乐音色',density='零',rhythm='由动作与原生声音承担',texture='保留环境的空隙',historical_flavor_boundary='不虚构年代音乐证据',modern_cinematic_boundary='有意识留白'),
        silence_policy='所有场次明确 NO_SCORE；不因生成能力存在而补音乐',diegetic_boundary='剧情内声音独立于配乐',score_dynamic_range='零配乐仍有对白与原生声音的动态',
        scene_music_decisions=[dict(scene_id=s,decision='NO_SCORE',rationale=i.performance_core,score_function='由该场人物行动自行完成信息；无额外 score 任务',entry_trigger='不进入',exit_trigger='保持无配乐',performance_alignment=i.continuity_out,
            performance_intent_ref=SourcePin(key='performance:'+s,kind='DIRECTION',fingerprint=fp(i)),dialogue_native_priority='对白、伙伴接收与原生受力声优先',source_strategy='NO_SCORE',do_not=('不以音乐重复人物已给出的情绪',)) for s,i in intents.items()],
        source_strategy_policy='NO_SCORE 不触发检索或生成',rights_policy='有新 cue 才另做作品权及录音权审查',review_status='DESIGN_REVIEWED'))


def cue(key: str, scene: str, function: str, entry: str, exit: str, *, emotion: str='PROPULSION',
        relation: str='SUPPORT_ACTION', motif: str='M1', duration: tuple[float,float]=(12,24)) -> MusicCue:
    arc=('从可见行动获得脉冲','动作兑现时展开一次','让出后果与原生声音')
    return MusicCue.model_validate(dict(cue_id=key,scene_ids=(scene,),narrative_function=function,emotional_direction=emotion,performance_relation=relation,
        audience_effect='观众先理解空间和对象，再获得这次行动真正产生的推动',entry_trigger=entry,exit_trigger=exit,energy_arc=arc,motif_refs=(motif,),
        timbre_palette='低音擦弦与干木质节奏，音头留出对白空隙，无人声',rhythmic_function='连接不同动作的因果推进，不能代替地理解释',
        dialogue_windows=('任何命令、问答与伙伴接收发生时，让出发声及听取的窗口；真实时长待 Picture conform',),
        silence_before='先听清动作空间与具体命令',silence_after='保留接触、气息及行动后果',sync_points=(entry,exit),source_strategy='ORIGINAL_AI',
        rights_requirement='未来必须分别证明 composition 与 master 的商业使用权；本轮无音乐文件',
        do_not=('不持续英雄和声','不增加女声吟唱或合唱','不遮蔽命令与接触声','不提前告诉观众结局'),
        generation_requirements=dict(cue_ref=key,duration_range=duration,dramatic_function=function,energy_arc=arc,motif_refs=(motif,),
            timbre='低音擦弦与干木质节奏，音头留出对白空隙，无人声',rhythm='连接不同动作的因果推进，不能代替地理解释',continuation='保持母题身份，可延展行动段而不循环句尾',
            revision_requirement='能够只改进入、峰值或退出的一段',stem_requirement='REQUIRED',stem_reason='节奏、持续织体、低音分轨，便于保留对白与兵器声',
            editability='保留干净起止、无硬尾混响及可拆段结构')))

GAIXIA_ROWS={
'P01':('SCORE_PRESENT','两翼接触与韩信再进已经能看懂后，短配乐把分离行动接成合力。首次楚军推进主要依原生脚步和碰撞。','当两翼施压开始与汉前列再进形成合力','楚军撤回营垒，原阵线断开后让出退步与命令','命令仍指向近列；音乐不把韩信塑成反派展示','C01'),
'P02':('DIEGETIC_ONLY','空粮器具与不同方向楚歌已改变人物判断；配乐会争夺声音的空间信息。','不进入非剧情配乐','楚歌的声源变化交给 SourceSoundIntent','惊疑通过继续做事与异步辨听发生；不能预告全军精神崩塌',None),
'P03':('NO_SCORE','当前用户已把历史诗句定为非现代歌曲化语言表演；帐内关系由字、呼吸、杯的实际动作与帐外声承担。','不进入，也不为 N04/N05 配伴奏','双方完成有限相处后仍无配乐尾声','泪落肩不垮；给虞回应的时间由表演完成，不用弦乐代替接收',None),
'P04':('TRANSITION_ONLY','同伴归队、骑队脱出眼前阻拦后，用短而有缺口的脉冲承接夜路省略；营口的留营者和等待动作全程保持无配乐。','从骑甲等到同伴越过并重新跟上，骑队确实脱离最后这一处阻拦后','夜路省略完成、天明马迹的实际声音取得注意时','项羽已恢复可执行军令的基线；等待同伴的动作不被配乐催促','C02'),
'P05':('NO_SCORE','前后队距离与马步重新接齐已经表达灌婴的组织能力。','不进入','保持队列接续的实际声音','不给追者增加猎杀者音乐人格；近队收速和后队追上有各自时机',None),
'P06':('NO_SCORE','再等一等是仍在争取具体同伴的请求；留白使来路与未归者保持未知。','不进入','跟上以后以行路声音衔接','短请求与实际等候都不加悲情铺垫；听者拥有作选择的空档',None),
'P07':('NO_SCORE','泥泽、马足失力与互助次序提供压力。配乐的加速会掩盖谁让出路、谁才能退出。','不进入','回到实地仍先保留马与人的负荷','不把田父演成阴谋主题；楚骑不同步惊慌，追骑距离从声源建立',None),
'P08':('SCORE_PRESENT','已建立四队方向后允许动作推进和承诺兑现的快意；认可与真笑有完整的声音空间，之后新压力才接管。','四队的分离方向与会合目标可辨、真正开始突破时','何如与如大王言之间让出对白；真笑完成后，追骑重新进入注意时退尽','HIGH 身体能量与真实喜悦获得一次展开；不以挽歌取消兑现','C03'),
'P09':('NO_SCORE','船是一条真实可行的生路；亭长仍在争取一个活人。对话中的选择不能被音乐提前判死。','主要对白和交缰段不进入','保持船、缰与脚步的具体关系，不加拒渡挽歌','听、靠近、考虑、解释依次发生；亭长的行动不变成遗言伴奏',None),
'P10':('NO_SCORE','接战、伤后换气、身份识认与身体失支撑已足以完成终局。个人停止后军队仍在工作。','死亡前后均不自动进入','最后保留汉军接队与经过的现实声音','不制造第三次音乐高潮；停止发声属于项羽，不属于整个战场',None),
}


def gaixia_score(film: dict[str,Any], policy_fingerprint: str) -> dict[str,Any]:
    pins=(SourcePin(key='r1-proposal',kind='DESIGN',fingerprint=film['source_hash']),SourcePin(key='historical-verse-policy',kind='DESIGN',fingerprint=policy_fingerprint))
    film_ref=SourcePin(key='gaixia-score-director-intent',kind='DIRECTION',fingerprint=fp({'source':film['source_hash'],'thesis':'集体行动如何接续、断裂，个人能力如何只能完成局部兑现','policy':policy_fingerprint}))
    plan=silent_plan('phase-1-r1-proposal',pins,film_ref,film['intents'],'PROPOSAL_ONLY');raw=dump_contract(plan)
    raw.update(scoreThesis='配乐只在军队行动形成合力、骑队脱离与快战兑现时连接观众的期待；其余场面把决定、聆听和后果交还人物及物理世界。一次能战的兑现应被真正感到，影片不靠音乐把局部胜利兑换成战争胜利。',
      scoreWorld='克制数量而保留强度：从接续到缺口，再到一次短暂完整的行动兑现。',
      scorePalette=dict(timbre='低音擦弦、干木质及少量皮膜节奏；不宣称秦汉乐器复原',density='多数场为零；行动 cue 由稀疏到短暂饱满',rhythm='离散脉冲获得接续、被切断、在快战中完成一次',texture='保留粗粒触感和空隙，避免持续光滑抒情铺底',historicalFlavorBoundary='只约束材料与声音气质的可信度，不伪造古曲、古代唱法或考古结论',modernCinematicBoundary='允许现代电影的节奏与织体组织；禁仙侠、古风流行歌、MMO和预告片大落点'),
      motifs=[dict(motifId='M01',dramaticFunction='使分散行动何时接续、何时断开变得可感',identity='短促不等长的脉冲单元；不是项羽个人主题',development='P01属于汉方合力，P04留下缺口，P08在楚方快战中短暂完成',payoffOrWithholding='P08允许完成一次；P09/P10不再用母题替人物总结命运')],
      silencePolicy='P02、P03、P05、P06、P07、P09、P10明确不加非剧情配乐；静默保持对白、空间声与承重。',
      diegeticBoundary='P02楚歌属于剧情声。P03 N04/N05属于历史诗句语言表演；虞回应实现未定，均不得成为 Music Cue。',
      scoreDynamicRange='0→短合力脉冲→长段0→一次高能兑现→0；不全片持续悲壮。',
      excludedPerformanceRefs=['P03:spoken:N04','P03:spoken:N05','P03:nonlexical-vocal'],
      sourceStrategyPolicy='三条候选原创 cue 暂按 ORIGINAL_AI 定义语义需求；无已合格服务，无文件，无调用。其他场 NO_SCORE。',
      unresolvedQuestions=['真实剪辑以后再定 cue 的准确切入与停留','音乐音色和母题是否真能与人物及物理声音共存，须真人听评','未来一个可替换 provider 必须单独资格验证','虞回应声音实现仍未解决，不由 Music 接管'])
    decisions=[];cues=[]
    for sid,(decision,rationale,entry,exit,alignment,cue_id) in GAIXIA_ROWS.items():
        original=next(d for d in plan.scene_music_decisions if d.scene_id==sid)
        d=dump_contract(original);d.update(decision=decision,rationale=rationale,scoreFunction=rationale,entryTrigger=entry,exitTrigger=exit,performanceAlignment=alignment,
            sourceStrategy='ORIGINAL_AI' if cue_id else 'NO_SCORE',cueRefs=[cue_id] if cue_id else [],doNot=[GAIXIA_ROWS[sid][4],'不自动添加人声、悲情底乐或第三高潮'])
        decisions.append(d)
        if cue_id:cues.append(dump_contract(cue(cue_id,sid,rationale,entry,exit,emotion='JOY' if sid=='P08' else 'PROPULSION',relation='SUPPORT_EARNED_RELEASE' if sid=='P08' else 'SUPPORT_ACTION',motif='M01',duration={'P01':(12,22),'P04':(8,16),'P08':(18,35)}[sid])))
    for c in cues:
        if c['cueId']=='C03':
            arc=['方向可辨后才获得推进脉冲','第一次缺口打开允许展开，三路再围时收薄','再次打开空地后向同伴靠近，问答让出对白','真实笑完成一次温暖释放，随后追骑新信息才使音乐退尽']
            c['energyArc']=arc;c['generationRequirements']['energyArc']=arc
            c['dialogueWindows']=['何如？开始前让出发声空间，持续到如大王言的接收结束；真笑由呼吸与同伴关系完成，音乐不抢答']
            c['doNot'].append('不得使用帐中历史诗句的旋律重现；当前没有批准旋律')
    raw.update(sceneMusicDecisions=decisions,musicCues=cues)
    plan=FilmScorePlan.model_validate(raw);current={p.key:p.fingerprint for p in (*pins,film_ref,*(d.performance_intent_ref for d in plan.scene_music_decisions))}
    reviewed=review_score_plan(plan,current=current,expected_scene_ids=list(GAIXIA_ROWS),performance_intents=film['intents'],excluded_performance_refs=plan.excluded_performance_refs)
    return {'plan':plan,'current':current,'review':reviewed,'composer_briefs':[composer_brief(plan,c.cue_id,current=current) for c in plan.music_cues]}


def generic_score(name: str) -> dict[str,Any]:
    from drama_plugin.contracts.dpd import BeatDPD,DPDLayerState
    cases: dict[str,dict[str,Any]]={
        'war':dict(actor='守渡队长',target='抬担架的小队',location='撤离窄桥',prop='担架',action='盾手保持接触，伤者先过，最后一人过桥后仍有人留守。',task='让伤者先过且保持通道',decision='SCORE_PRESENT',why='危险和通道先由动作看清，配乐只把先后通过的人接成一次有效推进，兑现后留住未归者的声音空位。',entry='盾手实际承住压力、担架开始通过窄口后',exit='最后一人落到对岸，队长看见守渡位置空着时',emotion='PROPULSION',constraints=()),
        'intimate':dict(actor='修理工',target='交接工作的搭档',location='工作台旁',prop='工具盒',action='修理工停下收拾，让搭档说完交接条件，之后才合上工具盒。',task='听完搭档对交接的条件',decision='NO_SCORE',why='停手和听完已经改变关系；配乐不会增加信息，只会替观众提前解释情绪。',entry='不进入',exit='交接结束仍保持原生工作声',emotion='NEUTRAL_TEXTURE',constraints=('NO_SCORE',)),
        'political':dict(actor='掌印者',target='记录属吏',location='议事公案',prop='真账',action='掌印者把真账留给记录者，来使收起预写告示离开，记录者继续登记。',task='让真实责任进入公开记录',decision='TRANSITION_ONLY',why='对白段不加压迫底乐；真账已经被登记、权力关系实际改变以后，稀薄织体仅承接程序继续。',entry='属吏已把真账记入公案、来使收起旧告示后',exit='观众注意回到单独持续的书写声时',emotion='NEUTRAL_TEXTURE',constraints=()),
        'silence':dict(actor='夜班工人',target='没有回应的值班室',location='空值班室',prop='交班钥匙',action='工人放下钥匙，停手听室内，远处机器仍在运转；没有人回答。',task='确认交班位置是否有人接收',decision='NO_SCORE',why='无人回应的持续时间就是观众要经历的信息。音乐会把未知改成预设悲情。',entry='不进入',exit='机器声与钥匙落定后的空隙保持',emotion='NEUTRAL_TEXTURE',constraints=('NO_SCORE','NO_FATALISTIC_FORESHADOWING'))}
    x=cases[name];sid='generic-'+name;source={'scope':sid,'label':'DESIGN_FIXTURE_ONLY / NOT HISTORICAL CLAIM',**x};source_hash=fp(source)
    dpd=BeatDPD(scene_id=sid,beat_id=sid+':action',actor=x['actor'],obstacle='任务尚未完成，对方接收与空间条件限制行动',transition_trigger=x['action'],direction=DPDLayerState(objective=x['task'],interaction_target=x['target'],tactic='按源中的具体动作完成交接',internal_activation='HIGH' if name in ('war','political') else 'MEDIUM',external_control='HIGH' if name!='political' else 'MEDIUM'))
    i=DirectorPerformanceIntent(scene_id=sid,source_fingerprints={'source:'+sid:source_hash},dpd_fingerprints=(fp(dpd),),beat_ids=(dpd.beat_id,),performance_core=x['action'],audience_experience=x['why'],primary_focus=x['task'],containment='任务与接收决定幅度，不增加未写的情绪表演',external_expression_ceiling='HIGH' if name=='war' else 'MEDIUM',permitted_release=('one_breath_release',) if name=='war' else (),release_point='任务实际完成后；未完成不补释放',partner_focus=x['target'],performance_rhythm=x['action'],continuity_in='任务正在进行',continuity_out='只继承源中已完成的变化',do_not=('不补剧情与台词',),music_constraints=x['constraints'],review_basis='DESIGN_FIXTURE_ONLY')
    src=SourcePin(key='source:'+sid,kind='DESIGN',fingerprint=source_hash);film=SourcePin(key='film:'+sid,kind='DIRECTION',fingerprint=fp({'task':x['task'],'why':x['why']}))
    plan=silent_plan(sid,(src,),film,{sid:i});raw=dump_contract(plan);raw['scoreThesis']=x['why'];raw['scoreWorld']=x['location']+'中由'+x['action']+'决定音乐有无'
    d=raw['sceneMusicDecisions'][0];d.update(decision=x['decision'],rationale=x['why'],scoreFunction=x['why'],entryTrigger=x['entry'],exitTrigger=x['exit'])
    if x['decision']!='NO_SCORE':
        c=cue('cue-'+name,sid,x['why'],x['entry'],x['exit'],emotion=x['emotion'],motif='motif-'+name)
        if name=='political':
            c=c.model_copy(update={'timbre_palette':'稀薄单层擦奏织体；不设进行曲或权力低音标记','rhythmic_function':'退出台词后以稀疏音头承接书写，不给问答加节拍','silence_before':'全部对白与真正交账动作','silence_after':'单独持续的书写声'})
            assert c.generation_requirements
            c=c.model_copy(update={'generation_requirements':c.generation_requirements.model_copy(update={'timbre':c.timbre_palette,'rhythm':c.rhythmic_function})})
        raw['musicCues']=[dump_contract(c)];raw['motifs']=[dict(motifId='motif-'+name,dramaticFunction=x['why'],identity='断续脉冲' if name=='war' else '稀薄非旋律织体',development='只在本 fixture 任务改变以后进入',payoffOrWithholding=x['exit'])]
        d.update(cueRefs=[c.cue_id],sourceStrategy='ORIGINAL_AI')
        raw['scorePalette']=dict(timbre=c.timbre_palette,density='先无，动作触发后局部进入，后果处退尽',rhythm=c.rhythmic_function,texture='留出原生空间',historicalFlavorBoundary='虚构通用 fixture，不作历史声音声明',modernCinematicBoundary='电影节奏服务事件，不套游戏或预告片模板')
        raw['scoreDynamicRange']='无→有限进入→后果留白';raw['silencePolicy']=c.silence_before+'与'+c.silence_after+'保持无配乐'
    plan=FilmScorePlan.model_validate(raw);current={src.key:src.fingerprint,film.key:film.fingerprint,'performance:'+sid:fp(i)}
    return {'source':source,'dpd':dump_contract(dpd),'intents':{sid:i},'plan':plan,'current':current,'review':review_score_plan(plan,current=current,expected_scene_ids=(sid,),performance_intents={sid:i})}
