"""Source-bound, artifact-only R1 full-film performance design fixture builder."""
from __future__ import annotations
import hashlib
from typing import Any, Literal
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.dpd import SceneDPD, BeatDPD, LineDPD, DPDLayerState, DPDSnapshot, PerformanceLevel
from drama_plugin.dpd import compose_dpd
from drama_plugin.contracts.performance_direction import DirectorPerformanceIntent, PerformanceProjection, VocalDelivery
from drama_plugin.contracts.audio import VoiceProfile, CreativeVoiceProfile, TargetTimingPolicy
from drama_plugin.audio.projection import compile_projected_speech_request
from drama_plugin.performance_direction import validate_projection
from drama_plugin.performance_coverage import parse_proposal, CATEGORIES, render_bound_direction, full_performance_coverage_gate
from r3_direction_data import SCENES, LINES, SILENT_OWNERS


def build_fixture(text: str, grammar_hash: str, route: Literal['stylized_cinematic_cg','live_action']='stylized_cinematic_cg') -> dict[str, Any]:
    source=hashlib.sha256(text.encode()).hexdigest();scenes=parse_proposal(text)
    assert {s['ref'] for s in scenes}==set(SCENES)
    actual={line['ref'] for s in scenes for line in s['spoken']}
    assert actual==set(LINES), ('source lexical inventory changed', actual.symmetric_difference(LINES))
    inventory: dict[str, Any]={'scope':'PROPOSAL_ONLY','source_hash':source,'not_applicable':{'shots':'R1 screenplay is not approved; no proposal Shots are fabricated. Formal Production Book must supply real Shot inventory.'},**{k:[] for k in CATEGORIES}}
    contexts: dict[str, Any]={};directions: dict[str, Any]={};dpds: dict[str, Any]={};intents={};projections={};scene_rows: list[dict[str,Any]]=[];continuity_maps: dict[str,list[Any]]={}
    def actor_ref(scene: str,name: str) -> str:return scene+':actor:'+name
    def add_entity(ctx: dict[str,Any],name: str,kind: str,evidence: str) -> str:
        ref=kind+':'+name
        ctx['entities'][ref]={'scope':ctx['scope'],'kind':kind,'display':name,'source_ref':ctx['scope']+':R1-proposal','evidence':evidence,'aliases':[]}
        return ref
    def direction(ref: str,s: dict[str,Any],task_ref: str,core: str,physical: str,target: str,detail: str='STANDARD',vocal: bool=False) -> dict[str,Any]:
        data=SCENES[s['ref']];ctx=contexts[s['ref']]
        target_ref=next((k for k,e in ctx['entities'].items() if e['display']==target),None)
        if target_ref is None:target_ref=add_entity(ctx,target,'partner',s['body'])
        d={'ref':ref,'scene':s['ref'],'source_ref':s['ref']+':R1-proposal','status':'COVERED','detail':detail,'core':core,'objective_ref':task_ref,'target_ref':target_ref,'expression':'LOW→MEDIUM，受控；仅具体动作触发释放','physical':physical,'partner':'把注意交给'+target+'的当前任务，不预演回应','continuity_in':data['entry'],'continuity_out':data['exit'],'do_not':data['do_not'],'context_refs':[target_ref],'context_fingerprint':'pending','semantic_review':{'status':'PASS','evidence':'作者逐场对照R1动作／对象／交接顺序；具体执行：'+physical,'source_context':s['ref']}}
        if vocal:d.update(voice=physical,speech_action=core,vocal_mode='SPOKEN',handoff='等绑定对象完成回应再进入下一动作',closure='按该句实际行动收口')
        directions[ref]=d;return d
    def item(category: str,ref: str,s: dict[str,Any],**kwargs: Any) -> None:
        inventory[category].append({'ref':ref,'scene':s['ref'],'source_ref':s['ref']+':R1-proposal','performance_bearing':True,**kwargs})
    for s in scenes:
        key=s['ref'];data=SCENES[key];assert len(data['silent'])==len(s['action_paragraphs']),(key,len(data['silent']),len(s['action_paragraphs']))
        ctx={'scope':key,'source_fingerprint':source,'entities':{}}
        contexts[key]=ctx
        add_entity(ctx,data['location'],'location',s['body'].splitlines()[1] if len(s['body'].splitlines())>1 else s['body'])
        for prop in {p for other in SCENES.values() for p in other['props'] if p in s['body']} | set(data['props']):add_entity(ctx,prop,'prop',s['body'])
        # A prior-state reference can be mentioned in continuity, not introduced as an on-screen prop.
        if key=='P04':add_entity(ctx,'杯','continuity-reference','P03相处已完成；P04不把私人状态带入军令')
        for name in data['characters']:add_entity(ctx,name,'character',s['body'])
        for name in {n for other in SCENES.values() for n in other['characters'] if n in s['body']} - set(data['characters']):add_entity(ctx,name,'source-reference',s['body'])
        if key=='P08':add_entity(ctx,'追骑','group-alias','汉骑／追军为本场同一追击群体的职能称呼')
        for g in data['groups']:add_entity(ctx,g[0],'group',s['body'])
        for line in s['spoken']:
            target=LINES[line['ref']][0];add_entity(ctx,target,'partner',s['body'])
        char_rows=[]
        for name,(objective,obstacle,tactic,target,body,voice) in data['characters'].items():
            ref=actor_ref(key,name)
            dpds[ref]=BeatDPD(scene_id=key,beat_id=ref,actor=name,obstacle=obstacle,transition_trigger=data['exit'],direction=DPDLayerState(objective=objective,interaction_target=target,tactic=tactic,external_control=PerformanceLevel.HIGH,internal_activation=PerformanceLevel.HIGH,relationship_stance=('她获得共同相处何时完成的决定权' if name=='虞美人' else '保留源中的当下关系，不补新的阵营或私人历史')))
            d=direction(ref,s,ref,'当前行动：'+objective,body,target,'EXPANDED' if key in ('P03','P08','P09','P10') else 'STANDARD')
            d['voice_baseline']=voice;item('characters',ref,s)
            char_rows.append({'name':name,'dpd_ref':ref,'direction_ref':ref,'objective':objective,'obstacle':obstacle,'tactic':tactic,'target':target,'body':body,'voice':voice})
            load='HIGH' if key in ('P06','P07','P08','P09','P10') and name in ('项羽','楚从骑甲','从骑','剩余楚方') else 'MEDIUM' if key in ('P01','P04','P05') or name=='项羽' else 'LOW'
            state={'physical_load':load,'fatigue':'已有作战／行路负荷保留，未见充分恢复事件，不因外放降低清零' if name in ('项羽','楚从骑甲','从骑','剩余楚方') else '只按源中当前任务受力，不补额外损伤','injury':'多处受伤影响承重' if key=='P10' and name=='项羽' else '未新增明确伤势','breath_load':load,'voice_load':load,'expression_baseline':'能接收、能执行，保持外部控制','release_residue':'TEMPORARY:私人泪落，出场恢复行动' if key=='P03' and name=='项羽' else 'TEMPORARY:真实笑已完成，新追兵信息进入' if key=='P08' and name=='项羽' else '没有永久情绪模板','attention':data['exit'],'interaction_residue':'本场已完成的对象交接，不重置人物身份','return_condition':data['exit']}
            continuity_maps.setdefault(name,[]).append({'scene':key,'dpd_ref':ref,'entry_text':data['entry'],'entry_state':{**state,'attention':data['entry'],'release_residue':'尚未发生本场释放'},'change':body,'exit':state,'exit_text':data['exit'],'post_exit':'NO_INVENTED_POST_EXIT_STATE' if name in ('虞美人','亭长','韩信','灌婴','吕马童','王翳','田父') else '仅下一次有源出场时衔接'})
        first=actor_ref(key,next(iter(data['characters'])))
        direction(key,s,first,data['core'],data['silent'][0],next(iter(data['characters'])))
        item('scenes',key,s)
        group_rows=[]
        for name,task,trigger,response,latency in data['groups']:
            ref=actor_ref(key,name)
            if ref not in dpds:dpds[ref]=BeatDPD(scene_id=key,beat_id=ref,actor=name,obstacle='空间与信息未同时抵达所有人',transition_trigger=trigger,direction=DPDLayerState(objective=task,interaction_target=name,tactic=response))
            group_rows.append({'group_ref':name,'dpd_ref':ref,'attention':task,'trigger':trigger,'response':response,'latency_order':latency,'task_persistence':'未收到该线索者继续：'+task,'variation':'按视野、受力和前人让出的空间各自完成，不统一相位'})
        ens_ref=key+':ensemble';d=direction(ens_ref,s,first,'把注意沿实际视野和行动传递',data['silent'][0],data['groups'][0][0]);d['ensemble']={'groups':group_rows,'added_spoken_content':False};item('ensemble',ens_ref,s)
        silent_rows=[]
        if key=='P02':
            dpds[actor_ref(key,'营外楚歌声源')]=BeatDPD(scene_id=key,beat_id=key+':source-song',actor='营外楚歌声源',obstacle='歌词未指定，声音由远处抵达',transition_trigger='歌声进入营中听觉',direction=DPDLayerState(objective='执行源中远处唱楚歌的声音行为，不补心理动机',interaction_target='营中听者',tactic='保持远处来源'))
        for index,(source_action,body) in enumerate(zip(s['action_paragraphs'],data['silent']),1):
            ref=key+':silent:'+str(index).zfill(2);action_ref=add_entity(ctx,'动作'+str(index)+':'+source_action,'action',source_action)
            owner=SILENT_OWNERS[key][index-1]
            owner_dpd=dpds[actor_ref(key,owner)]
            d=direction(ref,s,actor_ref(key,owner),'使这一动作的接收、受力与后果可见',body,str(owner_dpd.direction.interaction_target or owner))
            d['performer']=owner
            d['context_refs'].append(action_ref);d['source_excerpt']=source_action
            item('silent',ref,s,source_excerpt=source_action)
            silent_rows.append({'ref':ref,'source':source_action,'direction':body})
        # The DPD owner builds each partner's task before Director composes a handoff.
        interactions=[data['interaction']]
        additions={'P01':[('项羽','楚军近阵','转马与口令让近阵先护侧，远阵的信息延迟不能抹掉','近阵能让身后才进入撤回')],'P02':[('楚从骑甲','缠布帮手','甲已听见歌，帮手未听清仍绷布，手的接触才传递停止','帮手止住用力后再辨听')],'P04':[('项羽','军吏','核数者需要真实能力，回报者只报现有骑数','回报落定后项羽上马')],'P07':[('项羽','田父','真正求路与明确指向，不给田父补误导心理','指向可辨认后项羽左行')],'P10':[('项羽','吕马童','项羽识旧人，吕马童仍属于汉军并转向王翳','吕马童识认完成，项羽听见后才给功劳之语')]}
        interactions+=additions.get(key,[])
        interaction_rows=[]
        for n,(speaker,listener,exchange,next_action) in enumerate(interactions,1):
            ir=key+':interaction:'+str(n);d=direction(ir,s,actor_ref(key,speaker),exchange,next_action,listener,'EXPANDED')
            d['interaction']={'speaker_ref':speaker,'listener_ref':listener,'speaker_dpd':actor_ref(key,speaker),'listener_dpd':actor_ref(key,listener),'speaker_action':exchange,'listener_action':dpds[actor_ref(key,listener)].direction.objective,'speaker_target':listener,'listener_attention':'继续自己的任务，并接收对方当前能看见／听见的行动','gaze_handoff':'先确认对方收到，再转向下一实际动作：'+next_action,'voice_handoff':'有台词时不覆盖对方句尾；无词交接不补口号','physical_handoff':next_action,'partner_cue':exchange,'response_timing':next_action,'next_beat_owner':listener}
            item('interactions',ir,s);interaction_rows.append({'ref':ir,**d['interaction']})
        spoken_rows=[];line_snapshots=[]
        for line in s['spoken']:
            target,action,delivery,pause,handoff,closure=LINES[line['ref']]
            speaker='楚从骑甲' if line['speaker']=='楚从骑' else line['speaker']
            base=dpds[actor_ref(key,speaker)];assert isinstance(base,BeatDPD)
            beat=key+':line:'+line['ref']
            line_state=DPDLayerState(objective=action,interaction_target=target,tactic=base.direction.tactic,authority_position='按源中当前职役与相对位置',relationship_stance=base.direction.relationship_stance,internal_activation=PerformanceLevel.HIGH,external_control=PerformanceLevel.HIGH,public_private_context=data['location'])
            snapshot=compose_dpd(SceneDPD(scene_id=key,source_fingerprint=source,dramatic_purpose=s['purpose'],conflict_condition=base.obstacle,power_structure='源中角色关系，非新增心理',information_asymmetry='只使用当场可见可听信息；不补未来结局知识',direction=line_state),BeatDPD(scene_id=key,beat_id=beat,actor=speaker,obstacle=base.obstacle,transition_trigger=handoff,direction=line_state),LineDPD(scene_id=key,beat_id=beat,spoken_content_id=line['ref'],speaker=speaker,dramatic_action=action,observable_intent=action,continuity=data['entry'],change_from_previous=delivery))
            dpds[beat]=snapshot;line_snapshots.append(snapshot)
            ref=key+':spoken:'+line['ref'];d=direction(ref,s,beat,action,SCENES[key]['characters'][speaker][4],target,'EXPANDED' if key in ('P03','P08','P09','P10') else 'STANDARD',True)
            mode='SUNG' if line['ref'] in ('N04','N05') else 'SPOKEN'
            d.update(voice=delivery,speech_action=action,vocal_mode=mode,handoff=handoff,closure=closure,pause=pause,breath=('战后／长途负荷下按语意短换气，不一口满气宣讲' if key in ('P06','P07','P08','P09','P10') and speaker=='项羽' else '依当前身体任务支撑，不用哭腔替代气息'),pace='按该句行动推进：'+delivery,speaker=speaker,text=line['text'])
            item('spoken',ref,s,vocal=True);item('voice',ref,s,vocal=True)
            spoken_rows.append({**line,'ref':ref,'local_ref':line['ref'],'dpd_ref':beat,'speaker':speaker,'target':target,**{k:d[k] for k in ('speech_action','voice','vocal_mode','handoff','closure','pause','breath','pace','do_not')}})
        nonlex=[]
        if key in ('P02','P03','P08'):
            mode,actor,action=('SUNG','营外楚歌声源','原稿允许远处楚歌，不提供歌词') if key=='P02' else ('SHARED_RESPONSE','虞美人','等项羽声尾完成后和应，不添加未批准和辞') if key=='P03' else ('NONVERBAL','从骑群体','突破后原稿允许的不成句声息，不加欢呼口号')
            vocal_event=VocalDelivery.model_validate(dict(mode=mode,source_ref=key+':nonlexical-vocal',lyric_status='NO_APPROVED_LYRICS',melody_status='NOT_APPLICABLE' if mode=='NONVERBAL' else 'UNRESOLVED'))
            if actor_ref(key,actor) not in dpds:
                dpds[actor_ref(key,actor)]=BeatDPD(scene_id=key,beat_id=key+':vocal-behavior',actor=actor,obstacle='源未给歌词，不得补词或心理',transition_trigger=action,direction=DPDLayerState(objective=action,interaction_target=actor,tactic='仅执行源中允许的声音行为'))
            ref=key+':nonlexical-vocal';d=direction(ref,s,actor_ref(key,actor),action,action,actor,'EXPANDED',True);d.update(voice=action,speech_action=action,vocal_mode=mode,handoff='依据本场源中的声尾与接收动作，不叠压伙伴',closure='行为结束即收，不补未批准的词',vocal_delivery=dump_contract(vocal_event))
            item('voice',ref,s,vocal=True);nonlex=[{'ref':ref,'actor':actor,'action':action,'delivery':dump_contract(vocal_event)}]
        intent=DirectorPerformanceIntent(scene_id=key,source_fingerprints={'r1-proposal':source},dpd_fingerprints=tuple(x.fingerprint for x in line_snapshots),beat_ids=tuple(x.effective.beat_id for x in line_snapshots),performance_core=data['core'],audience_experience=s['purpose'],primary_focus=data['core'],containment=data['do_not'],external_expression_ceiling='MEDIUM',permitted_release=('controlled_tear','hand_pause') if key=='P03' else ('real_smile','one_breath_release') if key=='P08' else (),release_point=data['exit'],partner_focus='服从每条DPD的当场对象',performance_rhythm=data['core'],continuity_in=data['entry'],continuity_out=data['exit'],do_not=(data['do_not'],),forbidden_behaviors=('sobbing','collapse','continuous_shaking','heroic_declamation'),review_basis='DESIGN_FIXTURE_ONLY')
        intents[key]=intent
        scene_rows.append({'scene':s,'data':data,'characters':char_rows,'silent':silent_rows,'interactions':interaction_rows,'ensemble':group_rows,'spoken':spoken_rows,'nonlexical':nonlex})
    edges=[]
    for name,states in continuity_maps.items():
        for prev,nxt in zip(states,states[1:]):
            # Entry equals prior visible exit unless a concrete source event changes it.
            entry=dict(prev['exit']);desired=nxt['exit']
            transitions={}
            for field in ('physical_load','fatigue','injury','breath_load','voice_load'):
                if entry[field]!=desired[field]:
                    entry[field]=desired[field];transitions[field]={'reason':nxt['change'],'source_ref':nxt['scene']+':R1-proposal'}
            if prev['exit']['release_residue'].startswith('TEMPORARY:'):
                entry['release_residue']='释放已经完成，依新行动恢复基线';transitions['release_residue']={'reason':nxt['entry_text'],'source_ref':nxt['scene']+':R1-proposal'}
            nxt['entry_state']=entry
            edge={'character':name,'from':prev['scene'],'to':nxt['scene'],'previous_exit':prev['exit'],'next_entry':entry,'transitions':transitions,'dpd_refs':[prev['dpd_ref'],nxt['dpd_ref']]}
            ref='continuity:'+name+':'+prev['scene']+'>'+nxt['scene'];s=next(x for x in scenes if x['ref']==nxt['scene']);d=direction(ref,s,nxt['dpd_ref'],'将已有身体与声音负荷带入下一次有源出场',nxt['change'],name);d['edge']=edge;item('continuity',ref,s);edges.append(edge)
    # All relevant source fragments get AV observation obligations, not just highlights.
    for category in ('spoken','silent','interactions','ensemble'):
        for original in inventory[category]:
            ref='av:'+original['ref'];s=next(x for x in scenes if x['ref']==original['scene']);d=dict(directions[original['ref']]);d['ref']=ref;directions[ref]=d
            item('av_plan',ref,s,review_key=original['ref']+'#'+('spoken' if category=='spoken' else 'action-ref'),channels=['VISUAL','VOICE'] if original.get('vocal') else ['VISUAL'])
    for original in inventory['voice']:
        if ':nonlexical-vocal' in original['ref']:
            ref='av:'+original['ref'];d=dict(directions[original['ref']]);d['ref']=ref;directions[ref]=d;s=next(x for x in scenes if x['ref']==original['scene']);item('av_plan',ref,s,review_key=original['ref']+'#nonlexical-ref',channels=['VISUAL','VOICE'])
    # Freeze the completed bound contexts only after all legitimately referenced roles resolve.
    for d in directions.values():
        ctx=contexts[d['scene']];d['context_fingerprint']=fp(ctx)
        prose=' '.join(str(v) for v in d.values())
        d['context_refs']=list(dict.fromkeys([*d['context_refs'],*(r for r,e in ctx['entities'].items() if e['display'] in prose)]))
    for row in scene_rows:
        key=row['scene']['ref'];intent=intents[key]
        for line in row['spoken']:
            d=directions[line['ref']];dpd=dpds[line['dpd_ref']];current={'r1-proposal':source,'grammar:'+route:grammar_hash,'performance-context':fp(contexts[key])}
            current.update({'context-ref:'+r:fp(contexts[key]) for r in contexts[key]['entities']})
            actor_body=d['physical'];voice=d['voice'];common=dict(director_intent_fingerprint=fp(intent),beat_id=dpd.effective.beat_id,spoken_content_id=dpd.effective.spoken_content_id,interaction_target=dpd.effective.interaction_target,spatial_projection=SCENES[key]['location']+'中声音抵达'+line['target'],external_expression='LOW' if key in ('P02','P03','P06','P09','P10') else 'MEDIUM',external_control='HIGH',body_load='HIGH' if key in ('P06','P07','P08','P09','P10') and line['speaker']=='项羽' else 'MEDIUM',breath=d['breath'],release=(),continuity_in=intent.continuity_in,continuity_out=intent.continuity_out,context_fingerprint=current['performance-context'],context_refs=tuple(d['context_refs']))
            vi={'body_state':actor_body,'posture':actor_body,'weight':'按当前动作保留真实承重，不用情绪代替受力','movement':actor_body+('；CG姿态轴线与轮廓服务动作可读' if route=='stylized_cinematic_cg' else '；真人保留受力中的自然微调'),'eyes':'目光服务当前对象：'+line['target'],'head':'跟随必要的注意变化，不固定点头','hands':actor_body,'visible_breath':d['breath'],'prop':'只允许绑定场景中已给出的物件与动作','partner':line['target'],'distance':common['spatial_projection'],'timing':d['handoff'],'release':'只允许本场意图指定的动作触发释放','continuity':intent.continuity_out,'do_not':d['do_not']}
            ai={'voice_core':voice,'interaction':line['target'],'spatial_projection':common['spatial_projection'],'pace':d['pace'],'rhythm':voice,'intensity':'按对象距离投射；内压不自动变音量','breath_support':d['breath'],'phrase_attack':voice,'articulation':'保留原文与字头，状态不改变声音身份','emphasis':d['speech_action'],'pause_function':d['pause'],'sentence_closure':d['closure'],'coloration':'身体负荷作用于气息与收句，不换身份','release':'不抢伙伴的声尾；释放由场内事件触发','continuity':intent.continuity_out,'do_not':d['do_not']}
            vocal=VocalDelivery(mode=d['vocal_mode'],source_ref=line['ref'],lyric_status='EXACT_SOURCE',melody_status='UNRESOLVED' if d['vocal_mode']=='SUNG' else 'NOT_APPLICABLE')
            vp=PerformanceProjection(**common,channel='VISUAL',instructions=vi,route=route,grammar_fingerprint=grammar_hash)
            ap=PerformanceProjection(**common,channel='VOICE',instructions=ai,vocal_delivery=vocal)
            validate_projection(intent,dpd,vp,current,'VISUAL')
            request=compile_projected_speech_request(work_id='R1-PROPOSAL-ONLY',dpd_snapshot=dpd,spoken_content={'id':dpd.effective.spoken_content_id,'speakerKey':line['speaker'],'text':line['text']},voice_profile=VoiceProfile(profile_id='DESIGN_ONLY:'+line['speaker'],speaker_key=line['speaker'],creative_profile=CreativeVoiceProfile(vocal_age='ADULT',vocal_weight='MEDIUM',baseline_pace='MODERATE')),voice_identity_ref='UNAPPROVED_DESIGN_VOICE:'+line['speaker'],timing_policy=TargetTimingPolicy(policy='NATURAL'),director_intent=intent,performance_projection=ap,current_fingerprints=current)
            assert request.audio_performance_brief is not None
            projections[line['ref']]={'visualProjection':dump_contract(vp),'audioPerformanceBrief':dump_contract(request.audio_performance_brief),'shotBinding':'NOT_CREATED; bind the visual projection to actual Shot after R1 approval'}
    gate=full_performance_coverage_gate(inventory,directions,current_source_hash=source,contexts=contexts,dpds=dpds,source_text=text)
    return {'source_hash':source,'scenes':scene_rows,'inventory':inventory,'directions':directions,'contexts':contexts,'dpds':dpds,'intents':intents,'projections':projections,'continuity':continuity_maps,'edges':edges,'gate':gate,'route':route}
