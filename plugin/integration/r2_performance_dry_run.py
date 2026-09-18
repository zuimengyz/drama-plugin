"""Work-specific integration EXAMPLE/TEST HARNESS, not a generic preset.
Offline R2 chain from an explicitly selected source/installed package.

No formal owner, media generation, provider dispatch, or screenplay mutation.
Observations below are synthetic design fixtures, never actual playback.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--proposal', type=Path, required=True)
    parser.add_argument('--grammar', type=Path, required=True)
    args = parser.parse_args()
    package = args.package.resolve(); out = args.output.resolve()
    sys.path[:0] = [str(package / 'src'), str(package / 'tests')]
    network_attempts: list[str] = []
    def forbidden_connect(*unused: Any, **kwargs: Any) -> Any:
        network_attempts.append('BLOCKED')
        raise RuntimeError('R2_OFFLINE_NETWORK_FORBIDDEN')
    socket.socket.connect = forbidden_connect  # type: ignore[method-assign]
    from drama_plugin import DramaPlugin
    from drama_plugin.contracts.base import dump_contract
    from drama_plugin.contracts.sequence import FilmFinding
    from drama_plugin.contracts.media import Media, MediaType
    from drama_plugin.visual.performance import build_realized_performance_snapshot
    from drama_plugin.audio.video_conditioning import condition_audio_on_video
    from drama_plugin.sequence import film_review_verdict
    import drama_plugin.performance_direction as core
    from performance_direction_helpers import make_case, CASES
    assert Path(core.__file__).is_relative_to(package)
    plugin = DramaPlugin.load(package)
    assert len(plugin.skills.list()) == 19 and len(plugin.tools.list()) == 50
    out.mkdir(parents=True, exist_ok=True); (out/'contracts').mkdir(exist_ok=True)
    def save(path: Path, value: Any) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    def case(name: str, route: Literal['stylized_cinematic_cg', 'live_action'] = 'stylized_cinematic_cg') -> dict[str, Any]:
        result: dict[str,Any] = make_case(name, route, args.proposal, args.grammar if route == 'stylized_cinematic_cg' else None)
        return result
    def review(c: dict[str, Any]) -> Any:
        return core.review_av_performance(dpd=c['dpd'], intent=c['intent'], visual=c['visual'], audio=c['audio'], realized=c['realized'], review=c['review'], current=c['current'])
    def change(c: dict[str, Any], channel: str, updates: dict[str, Any]) -> None:
        key = 'visual_observation' if channel == 'VISUAL' else 'voice_observation'
        observed = c[key].model_copy(update=updates)
        c[key] = observed
        if channel == 'VISUAL':
            c['realized'] = build_realized_performance_snapshot({**dump_contract(c['realized']), 'performanceObservations':[dump_contract(observed)]})
        else:
            c['review'] = c['review'].model_copy(update={'performance_observations':(observed,)})
    results: list[dict[str, Any]] = []
    books: dict[str, str] = {}
    for name in CASES:
        c = case(name); r = review(c)
        assert set(r.performance_alignment.values()) == {'PASS'}
        native = core.native_audio_disposition(r)
        assert native['disposition'] == 'KEEP_NATIVE'
        assert film_review_verdict(r, r.media_hash)['status'] == 'REVIEW_INCOMPLETE'
        result = {'fixture':name,'basis':'DESIGN_FIXTURE_ONLY','alignment':dict(r.performance_alignment),'native':native,'adopted':False}
        results.append(result)
        save(out/'contracts'/f'{name}.json', {'fixture':name,'sourceStatus':'R1_PROPOSAL_ONLY_NOT_FORMAL_SCENE' if name.startswith('P') else 'DESIGN_FIXTURE_ONLY_NOT_HISTORICAL_CLAIM','currentFingerprints':c['current'], **{k:dump_contract(c[k]) for k in ('dpd','intent','visual','audio','realized')},'review':dump_contract(r),'result':result})
        e = c['dpd'].effective
        prose = f"## {name} · {c['config']['purpose']}\n\n"
        prose += ('**R1 PROPOSAL FIXTURE · PROPOSAL ONLY · NOT FORMAL GAIXIA SOURCE**\n\n' if name.startswith('P') else '**DESIGN_FIXTURE_ONLY · NOT HISTORICAL CLAIM**\n\n')
        prose += f"剧本文字：\n\n> {c['config']['text']}\n\n"
        prose += f"DPD preview：目的＝{e.objective}；阻力＝{c['config']['obstacle']}；策略＝{e.tactic}；潜台词＝{e.subtext}；对象＝{e.interaction_target}。这是候选文本的设计预览，未冒充正式 SceneDPD。来源、Scene/Beat/Line 与完整合同见 [该fixture合同](contracts/{name}.json)。\n\n"
        prose += f"Internal Pressure **{e.internal_activation.value}** / External Expression **{c['config']['expression']}** / Self Control **{e.external_control.value}**。内压／控制来自同一DPD，外放是Director envelope下的投射。\n\n### Director Performance Intent 与双通道执行\n\n"
        prose += core.render_performance_pair(c['dpd'],c['intent'],c['visual'],c['audio'],c['current'])
        prose += f"\n演员细节：{c['config']['hands']}。{c['config']['eyes']}。\n\n配音细节：{c['config']['attack']}；{c['config']['emphasis']}；{c['config']['closure']}。声音身份始终保持同一个人。\n\n### AV Beat Coordination\n\n"
        for cue in c['intent'].coordination:
            prose += f"- {cue.reason}（`{cue.event} {cue.relation} {cue.anchor}`" + (f" → `{cue.end_anchor}`" if cue.end_anchor else '') + "）。\n"
        prose += '\n事件毫秒数仅用于构造可重复的设计测试，不是正式对白时长或已经观察到的视频。\n\n'
        prose += f"Continuity out：{c['intent'].continuity_out}。\n\nExpected Alignment Findings：理想fixture的13项对照PASS；缺观察为UNKNOWN。若违反上述禁演或事件先后，生成带证据和repair owner的FilmFinding；声音问题退audio-production，身体问题退shot-production，意图连续性退director。当前仍不可adopt。\n\n"
        books[name] = prose
    live = case('decision','live_action'); cg = case('decision')
    assert live['dpd'] == cg['dpd'] and live['intent'] == cg['intent'] and live['audio'] == cg['audio']
    assert live['visual'] != cg['visual'] and set(review(live).performance_alignment.values()) == {'PASS'}
    save(out/'contracts/live-action.json', {'basis':'DESIGN_FIXTURE_ONLY','sameDpdIntentVoice':True,'visual':dump_contract(live['visual']),'review':dump_contract(review(live))})
    adversarial: list[tuple[str, str, str, dict[str, Any], str, str]] = [
        ('高控制身体崩溃','P03','VISUAL',{'behaviors':('sobbing','collapse'),'external_expression':'HIGH'},'emotional_amplitude','shot-production'),
        ('克制泪落配持续哭声','P03','VOICE',{'behaviors':('sobbing',)},'emotional_amplitude','audio-production'),
        ('战后疲惫配满气宣讲','P08','VOICE',{'behaviors':('unbroken_ceremonial_breath',)},'body_voice_effort','audio-production'),
        ('近距离对话配军令投射','P03','VOICE',{'spatial_projection':'army-command scale'},'spatial_projection','audio-production'),
        ('眼看同伴声对人群','P03','VOICE',{'interaction_target':'crowd'},'interaction_target','audio-production'),
        ('听虞时提前起身','P03','VISUAL',{'event_times_ms':{**case('P03')['visual_observation'].event_times_ms,'rise_start':5000}},'timing','shot-production'),
        ('自身声尾覆盖同伴四秒','P03','VOICE',{'event_times_ms':{**case('P03')['voice_observation'].event_times_ms,'own_voice_end':7600}},'timing','audio-production'),
        ('真实笑被苦笑替代','P08','VISUAL',{'behaviors':('bitter_smile',)},'emotional_amplitude','shot-production'),
        ('拒渡从第一句葬礼腔','P09','VOICE',{'behaviors':('funeral_tone',)},'emotional_amplitude','audio-production'),
        ('一滴泪永久污染后续','P03','VOICE',{'continuity_out':'permanent sadness'},'continuity','director'),
    ]
    failures: list[dict[str, Any]] = []
    for label, name, channel, updates, facet, owner in adversarial:
        c = case(name); change(c,channel,updates); r = review(c)
        finding = next(f for f in r.findings if f.key.endswith(':'+facet))
        assert r.performance_alignment[facet]=='FAIL' and finding.repair_owner==owner
        failures.append({'case':label,'expected':'FAIL','actual':'FAIL','facet':facet,'finding':dump_contract(finding)})
    c = case('P03'); r = review(c)
    local = r.model_copy(update={'findings':(FilmFinding(key='one-broken-phrase', start=2,end=2.4,domain='SOUND',severity='MAJOR',observation='single bounded synthetic defect',consequence='one phrase requires repair',repair_owner='audio-production',proposed_repair='local only'),)})
    local_decision=core.native_audio_disposition(local);assert local_decision['disposition']=='LOCAL_REPAIR'
    try:core.native_audio_disposition(local,replacement_reason='unusable_speech')
    except ValueError:pass
    else:raise AssertionError('Local defect escalated to full dubbing')
    bad=r.model_copy(update={'native_audio_suitability':{**r.native_audio_suitability,'dialogue':'FAIL'}})
    dubbing=core.native_audio_disposition(bad,replacement_reason='dialogue_missing');assert dubbing['disposition']=='DUBBING_REQUIRED' and not dubbing['generationAuthorized']
    c=case('P03');change(c,'VISUAL',{'event_times_ms':{**c['visual_observation'].event_times_ms,'rise_start':7900}});rp=c['realized']
    reconciliation=core.reconcile_realized_performance(c['dpd'],c['intent'],c['visual'],rp,c['current'])
    conditioned=condition_audio_on_video(base_request=c['request'],dpd_snapshot=c['dpd'],realized_snapshot=rp,video_media=Media(id=rp.video_media_id,work_id='fixture-work',shot_id=rp.shot_id,media_type=MediaType.VIDEO,source_ref='DESIGN_FIXTURE_ONLY',content_hash=rp.video_content_hash),shot_id=rp.shot_id,shot_scene_id=c['dpd'].effective.scene_id,shot_spoken_content_ids=(c['audio'].spoken_content_id,),canonical_spoken_content=c['spoken'],observed_speaker_key=c['audio'].speaker_key,bound_voice_id=c['audio'].voice_identity_ref,voice_content_hash='a'*64,accepted_realized_fingerprint=rp.fingerprint,director_intent=c['intent'],visual_brief=c['visual'],current_fingerprints=c['current'])
    assert conditioned.audio_performance_brief is not None
    assert '7900' in conditioned.audio_performance_brief.pause_strategy and conditioned.exact_text==c['spoken']['text']
    change(c,'VISUAL',{'meaning_preserved':'FAIL'})
    changed=core.reconcile_realized_performance(c['dpd'],c['intent'],c['visual'],c['realized'],c['current'])
    assert changed['status']=='VISUAL_REVISION_REQUIRED'
    save(out/'contracts/reconciliation.json',{'basis':'DESIGN_FIXTURE_ONLY','reconciliation':reconciliation,'conditionedRequest':dump_contract(conditioned),'meaningChange':changed})
    save(out/'contracts/native-decisions.json', {'keep':core.native_audio_disposition(r),'local':local_decision,'dubbing':dubbing})
    save(out/'contracts/adversarial.json',failures)
    (out/'r1-proposal-performance-direction-dry-run.md').write_text('# R1候选 · 跨模态表演方向设计验证\n\nPROPOSAL ONLY / DESIGN FIXTURE ONLY / NOT FORMAL GAIXIA SOURCE。未批准R1、未生成视频或声音、未开始Director Production Book。以下DPD是候选设计预览，不替代正式DPD。\n\n《垓下歌》的次序：N04力量自陈 → 失势收束 → N05向虞发问。先读P03-strength，再读P03的接收与泪落。\n\n'+''.join(books[k] for k in ('P03-strength','P03','P08','P09')),encoding='utf-8')
    table='| 对抗案例 | 结果 | Repair owner |\n|---|---|---|\n'+''.join(f"| {x['case']} | {x['actual']}（预期） | {x['finding']['repairOwner']} |\n" for x in failures)
    (out/'generic-cross-modal-performance-dry-run.md').write_text('# 通用跨模态表演设计验证\n\n全部DESIGN_FIXTURE_ONLY / NOT HISTORICAL CLAIM。\n\n'+''.join(books[k] for k in ('intimate','victory','decision'))+'## 对抗案例\n\n'+table+'\n上述FAIL是正确发现错误，不是正向链执行失败。\n\n## 真人路线兼容\n\n同一decision fixture在LIVE_ACTION与STYLIZED_CINEMATIC_CG中DPD、Director Intent与AudioPerformanceBrief完全相等。只更换视觉投射与grammar pin。真人身体保留自然微调，不要求CG轮廓强化；两条路线的设计对齐均通过。真人语法引用是标明的设计fixture，不冒充正式美术批准。\n',encoding='utf-8')
    summary={'status':'PASS','timestamp':datetime.now(timezone.utc).isoformat(),'package':str(package),'loadedCore':core.__file__,'coreHash':hashlib.sha256(Path(core.__file__).read_bytes()).hexdigest(),'proposalHash':hashlib.sha256(args.proposal.read_bytes()).hexdigest(),'grammarHash':hashlib.sha256(args.grammar.read_bytes()).hexdigest(),'skills':19,'tools':50,'positiveFixtures':len(results),'liveActionCompatibility':True,'adversarialCases':len(failures),'adversarialDetected':len(failures),'nativeDecisions':['KEEP_NATIVE','LOCAL_REPAIR','DUBBING_REQUIRED'],'realizedTimingConsumed':True,'storyMeaningChange':'VISUAL_REVISION_REQUIRED','basis':'DESIGN_FIXTURE_ONLY','actualMediaReviewed':False,'providerCalls':0,'networkAttempts':len(network_attempts),'formalWrites':0,'newMedia':0,'artisticSuccess':'NOT_ASSESSED','userApproval':False}
    assert not network_attempts
    save(out/'dry-run-summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    main()
