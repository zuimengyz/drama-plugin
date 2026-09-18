"""Offline authored music foundation proof. Writes only requested local artifacts."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
PACKAGE=Path(__file__).parents[1]
for sub in ('src','integration/fixtures'):sys.path.insert(0,str(PACKAGE/sub))
from drama_plugin import DramaPlugin
from drama_plugin.contracts.base import dump_contract,sha256_canonical as fp
from drama_plugin.contracts.performance_direction import VocalDelivery
from drama_plugin.contracts.audio_projection import AudioPerformanceBrief
from drama_plugin.audio.projection import fingerprint_audio_projection
from drama_plugin.vocal_direction import historical_verse_realization
from drama_plugin.music_direction import composer_brief,qualify_music_requirements,validate_score_context
from music_fixture_builder import gaixia_score,generic_score
from r3_fixture_builder import build_fixture


def save(path:Path,value:Any) -> None:
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main() -> None:
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--policy',type=Path,required=True);args=parser.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=True);contracts=out/'contracts';contracts.mkdir(exist_ok=True)
    plugin=DramaPlugin.load(PACKAGE);assert len(plugin.skills.list())==19 and len(plugin.tools.list())==50
    source=(PACKAGE/'integration/fixtures/r3_source_proposal.md').read_text(encoding='utf-8');policy=hashlib.sha256(args.policy.read_bytes()).hexdigest()
    film=build_fixture(source,'a'*64,music_constraints={'P02':('NO_SCORE',),'P03':('NO_SCORE',),'P08':('PRESERVE_REAL_JOY',),'P09':('NO_FATALISTIC_FORESHADOWING',)})
    score=gaixia_score(film,policy);assert score['review']['status']=='SCORE_DESIGN_REVIEW_READY';plan=score['plan']
    save(contracts/'gaixia-film-score-plan.json',dump_contract(plan));save(contracts/'composer-briefs.json',score['composer_briefs'])
    save(contracts/'gaixia-performance-intents.json',{k:dump_contract(v) for k,v in film['intents'].items()})
    amended={}
    for local in ('N04','N05'):
        ref='P03:spoken:'+local
        brief=AudioPerformanceBrief.model_validate(film['projections'][ref]['audioPerformanceBrief'])
        assert brief.director_performance and brief.director_performance.vocal_delivery
        delivery=historical_verse_realization(brief.director_performance.vocal_delivery,policy_ref='historical-verse-policy',policy_fingerprint=policy,current={'historical-verse-policy':policy})
        projection=brief.director_performance.model_copy(update={'vocal_delivery':delivery})
        new=brief.model_copy(update={'director_performance':projection})
        new=new.model_copy(update={'fingerprint':fingerprint_audio_projection(new)})
        assert new.text_fingerprint==brief.text_fingerprint and new.dpd_fingerprint==brief.dpd_fingerprint
        amended[ref]={'beforeMode':brief.director_performance.vocal_delivery.mode,'currentVocalDelivery':dump_contract(delivery),'audioPerformanceBrief':dump_contract(new),'textUnchanged':True,'dpdUnchanged':True}
    shared=historical_verse_realization(VocalDelivery(mode='SHARED_RESPONSE',source_ref='P03:nonlexical-vocal',lyric_status='NO_APPROVED_LYRICS',melody_status='UNRESOLVED'),policy_ref='historical-verse-policy',policy_fingerprint=policy,current={'historical-verse-policy':policy},shared_response=True)
    amended['P03:nonlexical-vocal']=dump_contract(shared);save(contracts/'historical-verse-reconciliation.json',amended)
    generic=[];generic_md=['# 通用配乐与静默 Dry-run','DESIGN_FIXTURE_ONLY · NOT HISTORICAL CLAIM · NO MEDIA / NO PROVIDER','']
    for name in ('war','intimate','political','silence'):
        result=generic_score(name);assert result['review']['status']=='SCORE_DESIGN_REVIEW_READY'
        save(contracts/(name+'-film-score-plan.json'),dump_contract(result['plan']));generic.append({'fixture':name,**result['review']})
        d=result['plan'].scene_music_decisions[0]
        generic_md += ['## '+name, '源动作：'+result['source']['action'],'', '**决定：'+d.decision+'**',d.rationale,'','进入：'+d.entry_trigger,'退出：'+d.exit_trigger,'表演对齐：'+d.performance_alignment,'对白 / 原生声：'+d.dialogue_native_priority,'禁止：'+'；'.join(d.do_not),'']
    # Repeat known-foreign structural/context attacks beyond Chinese sample keywords.
    isolation=[]
    for category in ('motif','character','location','prop','cue','score_strategy','historical_assumption'):
        def context(label:str) -> dict[str,Any]:return {'scope':label,'entities':{'sentinel':{'scope':label,'kind':category,'display':category+'_'+label,'source_ref':'fixture:'+label,'evidence':'exclusive '+label}}}
        a,b=context('A'),context('B');bad=plan.model_copy(update={'score_thesis':category+'_A'})
        review=validate_score_context(bad,b,foreign_contexts=[a]);assert review['status']=='FAIL';isolation.append({'category':category,**review})
    save(contracts/'template-isolation-findings.json',isolation)
    generic_md+=['## Template isolation','七类专属 sentinel（motif / character / location / prop / cue / score strategy / historical assumption）全部检出。复用 R3 refs + 已知外来词验证，不声称自动理解任意自然语言。','NO_SCORE 两例均完整通过，未创建 Cue 或生成要求。']
    (out/'12-generic-film-score-dry-run.md').write_text('\n\n'.join(generic_md),encoding='utf-8')
    film_md=['# 《垓下之战》P01—P10 音乐导演方案','APPROVED PROPOSAL · NOT FORMAL SOURCE · DESIGN ONLY · MUSIC AUDIO FILES = 0','']
    for d in plan.scene_music_decisions:
        film_md += ['## '+d.scene_id+'　'+next(r['scene']['title'] for r in film['scenes'] if r['scene']['ref']==d.scene_id),
            '**Scene Music Decision：'+d.decision+'**','Rationale：'+d.rationale,'Score Function：'+d.score_function,'Entry Trigger：'+d.entry_trigger,'Exit Trigger：'+d.exit_trigger,
            'Performance Alignment：'+d.performance_alignment,'Dialogue / Native Sound Priority：'+d.dialogue_native_priority,'Source Strategy：'+d.source_strategy,
            'DO NOT：'+'；'.join(d.do_not),'']
    (out/'14-gaixia-p01-p10-music-direction-dry-run.md').write_text('\n\n'.join(film_md),encoding='utf-8')
    bible=['# 《垓下之战》Film Score Bible Proposal','PROPOSAL ONLY · 用户已批剧本，不代表已批配乐。','## Score Thesis',plan.score_thesis,'## Score Palette',*[k+'：'+str(v) for k,v in dump_contract(plan.score_palette).items()],'## Motif System',*[m.motif_id+' — '+m.dramatic_function+'；'+m.identity+'；'+m.development+'；'+m.payoff_or_withholding for m in plan.motifs],plan.character_theme_policy,'## Silence Policy',plan.silence_policy,plan.diegetic_boundary,'## Music Dynamic Range',plan.score_dynamic_range,'## P01—P10 Scene Music Map','|Scene|Decision|Cue|','|---|---|---|',*[f'|{d.scene_id}|{d.decision}|{", ".join(d.cue_refs) or "—"}|' for d in plan.scene_music_decisions],'## Cue Sheet']
    for c in plan.music_cues:bible += [f'### {c.cue_id} / {", ".join(c.scene_ids)}',c.narrative_function,'进入：'+c.entry_trigger,'退出：'+c.exit_trigger,'发展：'+' → '.join(c.energy_arc),'预计素材时长范围：'+str(c.generation_requirements.duration_range)+' 秒，仅作资格需求，不是 Picture in/out。',c.rights_requirement]
    bible+=['## Source Strategies',plan.source_strategy_policy,'## Unresolved Questions',*['- '+q for q in plan.unresolved_questions]]
    (out/'13-gaixia-film-score-bible-proposal.md').write_text('\n\n'.join(bible),encoding='utf-8')
    result={'package':str(PACKAGE),'loadedMusicRuntime':str(sys.modules['drama_plugin.music_direction'].__file__),'skills':19,'tools':50,'gaixia':score['review'],'generic':generic,'isolationCategories':len(isolation),
            'historicalVerseModes':{k:amended[k]['currentVocalDelivery']['mode'] for k in ('P03:spoken:N04','P03:spoken:N05')},'sharedResponseRealization':shared.realization_status,
            'qualification':{c.cue_id:qualify_music_requirements(c,{}) for c in plan.music_cues},'providerCalls':0,'formalWrites':0,'musicAudioFiles':0,'aiMusicProviderImplemented':False,'userMusicApproval':False}
    save(out/'music-dry-run-result.json',result)
    print(json.dumps({k:result[k] for k in ('package','skills','tools','historicalVerseModes','sharedResponseRealization','providerCalls','formalWrites')},ensure_ascii=False))

if __name__=='__main__':main()
