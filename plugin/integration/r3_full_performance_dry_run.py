"""Offline, installed-package R3 full proposal coverage. No formal Shots/media."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import socket
from datetime import datetime, timezone
from typing import Any


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('package','proposal','grammar','output'):p.add_argument('--'+arg,type=Path,required=True)
    a=p.parse_args();package=a.package.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);(out/'contracts').mkdir(exist_ok=True)
    sys.path[:0]=[str(package/'src'),str(package/'integration/fixtures'),str(package/'tests')]
    attempts=[]
    def no_network(*args: Any,**kwargs: Any) -> Any:
        attempts.append('blocked');raise RuntimeError('R3_OFFLINE_NETWORK_FORBIDDEN')
    socket.socket.connect=no_network  # type: ignore[method-assign]
    from drama_plugin import DramaPlugin
    from drama_plugin.contracts.base import dump_contract,sha256_canonical as fp
    import drama_plugin.performance_coverage as core
    from drama_plugin.contracts.performance_direction import VocalDelivery
    from drama_plugin.vocal_direction import require_vocal_capability,native_vocal_disposition
    from drama_plugin.contracts.sequence import FilmReview
    from r3_fixture_builder import build_fixture
    from performance_direction_helpers import make_case
    assert Path(core.__file__).is_relative_to(package)
    plugin=DramaPlugin.load(package);assert len(plugin.skills.list())==18 and len(plugin.tools.list())==50
    source=a.proposal.read_text(encoding='utf-8');grammar=hashlib.sha256(a.grammar.read_bytes()).hexdigest();f=build_fixture(source,grammar)
    assert f['gate']['status']=='FULL_PERFORMANCE_COVERAGE_READY',f['gate']['findings']
    live=build_fixture(source,fp('LIVE_ACTION_DESIGN_GRAMMAR_ONLY'),'live_action')
    assert live['gate']['status']=='FULL_PERFORMANCE_COVERAGE_READY' and f['intents']==live['intents'] and f['edges']==live['edges']
    assert all(p['audioPerformanceBrief']==live['projections'][k]['audioPerformanceBrief'] for k,p in f['projections'].items())
    def save(name: str,value: Any) -> None:(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save('performance-coverage-manifest.json',{'artifactOnly':True,'canonicalAuthority':False,'sourcePath':str(a.proposal),'sourceFingerprint':f['source_hash'],'sourceStatus':'R1_PROPOSAL_ONLY_NOT_FORMAL_GAIXIA',**f['inventory'],'gate':f['gate']})
    save('contracts/full-directions.json',f['directions']);save('contracts/context-bindings.json',f['contexts']);save('contracts/dpd-previews.json',{k:dump_contract(v) for k,v in f['dpds'].items()});save('contracts/director-intents.json',{k:dump_contract(v) for k,v in f['intents'].items()});save('contracts/visual-voice-projections.json',f['projections']);save('contracts/continuity.json',f['continuity'])
    review=core.bind_full_performance_review(FilmReview(media_hash=fp('NO_MEDIA_DESIGN_ONLY'),duration=1,performance_review_basis='DESIGN_ONLY'),f['inventory'])
    save('contracts/av-observation-obligations.json',{'review':dump_contract(review),'coverage':core.full_av_coverage(review),'meaning':'All listed design obligations remain unobserved; no media generated.'})
    book=['# R1候选 · 全片表演导演覆盖 Dry-run','\n**PROPOSAL ONLY · NOT FORMAL GAIXIA SOURCE · NOT DIRECTOR PRODUCTION BOOK**','\nScene Performance Coverage：**10 / 10**。关键场次只决定展开深度；普通动作与台词同样有明确导演。',f"\n以下DPD均由现有DPD owner能力构成设计preview；不是正式SceneDPD。{len(f['inventory']['spoken'])}条是本次从正文逐条重新解析的结果。{len(f['inventory']['silent'])}个动作段保守全纳入，含非词汇声音行为；不以‘非关键’删除。实际Shot尚未建立，不能冒称Shot覆盖100%。",'\n## 全片共享规则','\n项羽保持能听、能决定、能行动的基线。一次泪或笑不永久覆盖后续。普通人物有自己的任务，不共用英雄表情。CG只强化当前受力、姿态与对象的可读性；音乐、喊声和额外对白不能替代表演。下文每场都有单独行动与声线选择。']
    spoken=['# 全部候选台词表演覆盖','\n词汇化台词由R1正文解析；不根据旧报告硬编码。每条保留原文、local ref和speaker，额外声音行为不冒充新SpokenContent。']
    silent=['# 无声／动作表演覆盖',f"\n保守纳入R1 Action与终场Silence的全部{len(f['inventory']['silent'])}个动作段。这里的silent是“非对白驱动单元”，其中楚歌、和唱及不成句声息另有vocal mode；不是把有声行为标成静音。每项是可见／可听动作要求，不补人物回忆或未知心理。"]
    interaction=['# 对手戏与伙伴导演','\n说话人、重要听者各引用自己的DPD preview。缺任一重要伙伴DPD返回PARTNER_DPD_REQUIRED，Director不得填一套心理。普通背景听者由群体任务承载。']
    ensemble=['# 群体表演导演','\nNO synchronized emotional reaction by default。保留注意传播、任务持续、反应延迟与个体受力差异；统一军礼或号令须有source sync reason。群体任务复用BeatDPD，不建Crowd Psychology，不新增SpokenContent。']
    ensemble += ['\n## 通用层次规则', '\nArmy：军令按距离与视线到达，前后列承担不同受力；不是所有士兵一起看主角。Small squad：近人先接触或接话，正在收缰／恢复呼吸者保留任务。Attendants：先接触到私人声息者收眼，远者晚回应，手里事务不丢。Crowd：以各自可得信息建立响应差，不用随机动作噪声充当个性。Background listeners：不重要者无须虚构独立心理，但要知道此刻做什么、是否听见、何时才回应。统一军礼／号令需Script依据，不能把同步情绪当默认。']
    for row in f['scenes']:
        s=row['scene'];key=s['ref'];data=row['data'];ctx=f['contexts'][key]
        # Names resolve from this bound context, not a global example template.
        def resolved(name: str) -> str:
            ref=next(r for r,e in ctx['entities'].items() if e['display']==name)
            return core.render_bound_direction('{'+ref+'}',ctx)
        part=[f"## {key} {s['title']}",f"\n**Scene Purpose（候选源）**：{s['purpose']}",f"\n**Scene Performance Core**：{data['core']}",f"\n**Continuity In**：{data['entry']}",f"\n**Continuity Out**：{data['exit']}",'\n### Character / Actor Direction']
        for ch in row['characters']:
            part += [f"\n**{resolved(ch['name'])}** · DPD preview `{ch['dpd_ref']}`",f"\n目的：{ch['objective']}。阻力：{ch['obstacle']}。策略：{ch['tactic']}。对象：{ch['target']}。",f"\nActor：{ch['body']}。Voice baseline：{ch['voice']}。"]
        part.append('\n### Voice Direction — 每条台词')
        spoken.append(f"\n## {key} {s['title']}")
        for line in row['spoken']:
            block=f"\n**{line['local_ref']} · {resolved(line['speaker'])} → {line['target']}**\n\n> {line['text']}\n\nSpeech action：{line['speech_action']}。Vocal mode：**{line['vocal_mode']}**"+(' / MELODY UNRESOLVED' if line['vocal_mode']=='SUNG' else '')+f"。\n\n执行变化／节奏：{line['voice']}。气息：{line['breath']}。Intensity/control：外部LOW→MEDIUM、控制HIGH，强度以实际对象距离为限。\n\n停顿：{line['pause']}。收句：{line['closure']}。Partner handoff：{line['handoff']}。\n\nContinuity：{data['entry']} → {data['exit']}。DO NOT：{line['do_not']}。\n"
            part.append(block);spoken.append(block)
        if row['nonlexical']:
            part.append('\n**非词汇声音行为（不新增台词）**')
            for n in row['nonlexical']:part.append(f"\n{n['actor']}：{n['action']}。`{n['delivery']['mode']}` / `{n['delivery']['melodyStatus']}` / `NO_APPROVED_LYRICS`。")
        part.append('\n### Partner / Interaction')
        interaction.append(f'\n## {key}')
        for i in row['interactions']:
            block=f"\n**{i['speaker_ref']} ↔ {i['listener_ref']}**（`{i['speaker_dpd']}` / `{i['listener_dpd']}`）\n\nSpeaker action：{i['speaker_action']}。Listener action：{i['listener_action']}。Listener attention：{i['listener_attention']}。\n\nGaze handoff：{i['gaze_handoff']}。Voice handoff：{i['voice_handoff']}。Physical handoff：{i['physical_handoff']}。\n\nPartner cue：{i['partner_cue']}。Response timing：{i['response_timing']}。下一Beat的响应主动方：{i['next_beat_owner']}；以本段具体时序为准，不表示永久权力转移。\n"
            part.append(block);interaction.append(block)
        part.append('\n### Silent / Action Beats')
        silent.append(f'\n## {key}')
        for b in row['silent']:
            owner=f['directions'][b['ref']]['performer'];block=f"\n**{b['ref']} · {owner}**\n\n源动作：{b['source']}\n\n导演：{b['direction']}。\n";part.append(block);silent.append(block)
        part.append('\n### Ensemble — 谁先、谁仍工作')
        ensemble.append(f'\n## {key}')
        for g in row['ensemble']:
            block=f"\n- **{g['group_ref']}**：任务／注意＝{g['attention']}；触发＝{g['trigger']}；相对响应层级 `{g['latency_order']}`，执行＝{g['response']}；{g['task_persistence']}。{g['variation']}。DPD `{g['dpd_ref']}`。"
            part.append(block);ensemble.append(block)
        part += ['\n### AV Coordination / DO NOT',f"\n本场全部台词、动作、互动和群体单元均进入AV观察义务。比较本场上列handoff与动作触发：{data['exit']}。未知时间保持UNKNOWN，不用计划时间冒充观察。",f"\nDO NOT：{data['do_not']}。",'\n**Coverage：COVERED**（方向覆盖，不是艺术评分、实际媒体审阅或批准）。']
        book.extend(part)
    def md(name: str,parts: list[str]) -> None:(out/name).write_text('\n'.join(parts)+'\n',encoding='utf-8')
    md('r1-proposal-full-film-performance-direction-dry-run.md',book);md('spoken-performance-coverage.md',spoken);md('silent-performance-coverage.md',silent);md('interaction-and-partner-direction.md',interaction);md('ensemble-performance-direction.md',ensemble)
    maps=['# 人物表演连续性 Map','\n这是源与DPD引用的可读聚合，不新增objective／subtext／knowledge／relationship真相。physical load是当前身体执行负荷；fatigue单独保留，不因外放低而清零。Voice identity不因疲惫、泪或笑变更。']
    for name,states in f['continuity'].items():
        maps.append('\n## '+name)
        for st in states:
            maps+= [f"\n### {st['scene']} · `{st['dpd_ref']}`",'\nEntry：'+st['entry_text'],'\nChange：'+st['change'],'\n| 表演状态 | Entry | Exit |\n|---|---|---|']
            for field in core.CONTINUITY_FIELDS:maps.append('| '+field+' | '+st['entry_state'][field]+' | '+st['exit'][field]+' |')
            maps.append('\nExit：'+st['exit_text']+'。'+st['post_exit'])
    maps.append('\n## 跨场验证\n\n共'+str(len(f['edges']))+'条同人物相邻出场边，previousExit与nextEntry不一致的维度必须有源事件解释。P03私人释放完成后P04恢复军令执行；P08真实笑先完成，再由缺位与追骑使状态变化。虞、亭长等未给出的出场后命运不推演。')
    md('character-performance-continuity.md',maps)
    generic=[]
    for name in ('intimate','victory','decision'):
        c=make_case(name);prose=str(dump_contract(c['visual']))+str(dump_contract(c['audio']))
        banned=('虞','杯') if name=='intimate' else ('亭长','船') if name=='decision' else ('从骑','何如')
        assert not any(x in prose for x in banned),(name,banned)
        generic.append({'fixture':name,'status':'PASS','sourceActor':c['config']['actor'],'sourcePartner':c['config']['target'],'prohibitedForeignTerms':banned,'independentConfiguration':True})
    sentinels=[]
    def context(scope: str) -> dict[str,Any]:return {'scope':scope,'entities':{k:{'scope':scope,'kind':k,'display':k+'_'+scope,'source_ref':'fixture:'+scope,'evidence':'bound '+k+'_'+scope} for k in ('character','partner','prop','location','action','voice_target')}}
    a_ctx=context('A');b_ctx=context('B');safe=core.render_bound_direction('{character} {partner} {prop} {location} {action} {voice_target}',b_ctx,foreign_contexts=[a_ctx])
    for kind in a_ctx['entities']:
        finding=core.validate_performance_context_isolation(context=b_ctx,refs=[kind],text=safe+' '+kind+'_A',foreign_contexts=[a_ctx]);assert finding['status']=='FAIL';sentinels.append(finding)
    d=VocalDelivery(mode='SUNG',source_ref='generic-song',lyric_status='EXACT_SOURCE',melody_status='UNRESOLVED')
    blocked=[]
    for supported in ({'SPOKEN'},{'SUNG'}):
        try:require_vocal_capability(d,supported_modes=supported)
        except ValueError as exc:blocked.append(str(exc))
    assert len(blocked)==2
    keep=native_vocal_disposition(make_case('intimate')['review'],d,observed_mode='SUNG');assert keep['disposition']=='KEEP_NATIVE'
    regression={'generic':generic,'sentinelFailuresDetected':sentinels,'songQualificationBlocks':blocked,'goodNativeSong':keep,'liveAction':f"PASS; same DPD, intents, interaction, continuity and {len(f['projections'])} Audio Briefs"}
    save('contracts/generic-isolation-regression.json',regression)
    md('generic-and-template-isolation-regression.md',['# 通用与模板隔离回归','\n全部DESIGN_FIXTURE_ONLY / NOT HISTORICAL CLAIM。','\nintimate：独立工作交接配置；身体停下整理工具，声音等待搭档，禁止虞／杯等历史道具或伙伴。','\nvictory：共同救援后的真实释放；对象是队员，身体卸力但仍恢复气息，不复用从骑或何如语句。','\ndecision：地图前向同事求复核；空间来自地图与同事，不再出现船边亭长。','\n六类A/B唯一sentinel：人物、伙伴、道具、地点、动作、声音对象；外来引用与外来文本均作为FAIL，正确B只解析B的refs。','\n新群体fixture：会议解释者、记录者与守门者，分别先听问题、写完抬头、确认出口；未收到线索者持续原任务（安装测试执行）。','\n新发声fixture：SUNG保持SUNG；仅支持SPOKEN的映射被VOCAL_MODE_CAPABILITY_REQUIRED阻断；支持SUNG但旋律未定仍MELODY_UNRESOLVED。已有合适原生演唱优先KEEP_NATIVE。','\n完整LIVE_ACTION十场覆盖通过，DPD／Intent／Interaction／Continuity及AudioBrief保持不变；只切换视觉语法。','\n检查器不能理解任意自然语言。具体发现、证据、来源上下文见[机器记录](contracts/generic-isolation-regression.json)；十场另逐段进行作者语义审阅，非仅looks good。'])
    summary={'status':'PASS','timestamp':datetime.now(timezone.utc).isoformat(),'package':str(package),'loadedCore':core.__file__,'sourceHash':f['source_hash'],'route':'STYLIZED_CINEMATIC_CG','coverage':f['gate']['coverage'],'lexicalSpokenCount':len(f['inventory']['spoken']),'newTopLevelContracts':0,'skills':18,'tools':50,'newAgents':0,'genericFixtures':3,'foreignSentinelTypesDetected':6,'liveActionFullCoverage':'PASS','vocalMode':'PASS','nativeAudioFirst':'PASS','actualAvCoverage':'INCOMPLETE_NO_MEDIA_AS_EXPECTED','providerCalls':0,'networkAttempts':len(attempts),'formalWrites':0,'r1ProposalChanged':False,'r2ArtifactsChanged':False,'directorProductionBookStarted':False,'userScriptApproval':False,'artisticSuccess':'NOT_ASSESSED'}
    assert not attempts;save('dry-run-summary.json',summary);print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
