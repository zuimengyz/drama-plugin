"""Materialize only R3D-A audited findings. No approval or production operation."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.creative_source import StageReview
from drama_plugin.contracts.interpretation import InterpretationFacet, InterpretiveImplication, MotifOccurrence
from drama_plugin.hosts.creative_source import CreativeSourceHost
from drama_plugin.interpretation import evidence_subject, intent_pin, project_board, render_board

REPO=Path(__file__).resolve().parents[3]
CREATIVE=REPO.parent/'artifacts/flagship-literary-film-01/creative'
OUT=CREATIVE/'interpretation'

def main() -> None:
    OUT.mkdir(exist_ok=True)
    host=CreativeSourceHost(OUT/'store')
    source=json.loads((CREATIVE/'literary-package.json').read_text())
    thesis=json.loads((CREATIVE/'dramatic-bible.json').read_text())
    source_ref=host.store.put('literary-package:F01-LITERARY-R1',source)
    thesis_ref=host.store.put('dramatic-bible:F01',thesis)
    originals={source_ref.key:source,thesis_ref.key:thesis}
    current={k:fp(v) for k,v in originals.items()}
    scope={'kind':'WHOLE_WORK','refs':['flagship-literary-film-01']}
    rows=[
      ('I-CORE','Core Interpretive Spine','从试图退出关系，到在不能保证正确时仍回应具体生命。', ['A003','A009','A038','A040','A041'],['A036'], 'HIGH','MULTI_VALENT','参与也能伤害，不是直线上升；不把参与等同于善。'),
      ('I-CHARACTER','Character State Arc','无关的确信被感觉刺破；梦中接纳、排他、失败；醒后愿活却仍自负、笨拙。',['A005','A009','A027','A036','A040'],['A003','A027'],'HIGH','MULTI_VALENT','荒唐、无关、退出有依据；持续思考形成完整虚无体系过强，无能为力是自杀核心原因仍 OPEN；同情、羞耻、爱旧地球不能抹去。'),
      ('I-RELATION','Primary Relationship Axis','他人有自己的要求与拒绝权，不是主人公理解世界的道具。',['A006','A028','A038','A041'],['A040'],'MEDIUM','WORKING','结尾仍由叙述者讲述；S16具体要求属现有 D16 改编，不是原文事实。'),
      ('I-MOTIFS','Major Motifs','星：今夜决定与梦中回指；枪：准备、延期、醒后推开；接触与社会声音呈现多种关系。',['A005','A006','A007','A009','A019','A039'],['A020','A021'],'HIGH','MULTI_VALENT','星的触发机制未知；手可施压；袖褶和门只是本版候选载体。详见 H-S1–H-S7。'),
      ('I-DREAM','Reality / Dream Relation','梦改变他与生命、他人的关系，不客观证明来世；乐园有死亡并会分裂。',['A031','A034','A036','A039'],['A040'],'HIGH','MULTI_VALENT','人物的真理确信不等于客观证明；拒绝现实暗、梦全亮的总公式。'),
      ('I-WORLD','World Relation','世界继续有各自的生活与苦难，他将其体验为无关。',['A004','A006','A007'],['A004'],'HIGH','WORKING','正常运行不等于繁华、安全或人人快乐；不能删去原著的阴郁与苦难。'),
      ('I-BOUNDARIES','Do-Not-Interpret-As','星不自动是希望；女孩无已确证的神学身份；枪未在现实发射；梦非无死亡答案；衣脸不承担心理模板。',['A005','A006','A009','A031','A039'],['A009'],'MEDIUM','WORKING','女孩没有神学身份的证明，不否认叙述者说她救了他；避免衣脸模板是待批准的本版边界。'),
      ('I-OPEN','Open / Contested Questions','星的未知触发保留多少？求真确信与自我中心的张力强调多少？门与袖痕是否值得电影强化？',['A005','A018','A040'],['A019'],'MEDIUM','OPEN','保留不选边选项；门与袖痕不得伪装成原著 motif；不以模型置信代用户选择。'),
      ('H-S1','Major Motifs','星标定既有退出决定落实为今夜的时刻。',['A005','A007'],['A005'],'HIGH','MULTI_VALENT','只知关联，不知机制；两个月前已有决定，不是星首次产生自杀意念。'),
      ('H-S2','Major Motifs','现实星与梦中被明确认出的星形成现实／梦结构联系。',['A005','A018','A019'],['A020'],'HIGH','MULTI_VALENT','梦中识别不等于客观天文学；人物尚未转好，不能与其他天体合并。'),
      ('H-S3','Major Motifs','从想消失到不能割断旧世界关系，是梦旅中的有限解释。',['A019','A021','A024','A027'],['A021','A027'],'MEDIUM','OPEN','直接唤醒旧生活感觉的是另一太阳的熟悉光；他称从未停止爱旧地球，不是星创造了爱。'),
      ('H-S4','Major Motifs','梦旅与共同体的天体意象展开个体与宇宙关系尺度。',['A021','A030','A031'],['A019','A031'],'MEDIUM','OPEN','不同天体不是同一对象；不能推成宇宙冷漠，也不是全片唯一意义。'),
      ('H-S5','Open / Contested Questions','星的首次触发机制保持未知。',['A005','A018'],['A019'],'HIGH','MULTI_VALENT','原因未知有直接依据；电影强调何种不可解释性仅 MEDIUM；复现意味着它不能被降为无关布景。'),
      ('H-S6','Do-Not-Interpret-As','STAR = generic hope / redemption，不能作为默认等式。',[],['A005','A020','A021'],'LOW','UNSUPPORTED','无直接正面等同证据；不能用传统象征自动批准。'),
      ('H-S7','Do-Not-Interpret-As','星在物理路线上导航他回原世界，不成立。',[],['A023','A026','A028','A039'],'LOW','REJECTED','梦旅前往另一地球；返回通过梦醒，心理重新朝向仅在 H-S3 下有界保留。')]
    observations={
      'I-CORE':'叙述者说一切无关，仍对女孩有同情，醒后要活并找到女孩。',
      'I-CHARACTER':'叙述者保留羞耻、对旧地球的爱以及醒后的错误与确信。',
      'I-RELATION':'女孩向他求助又转向别人；共同体有自己的回应。',
      'I-MOTIFS':'星在现实与梦中被提及；枪在现实准备、延期并于醒后被推开。',
      'I-DREAM':'梦中共同体有死亡和分裂，叙述者后来醒回椅子。',
      'I-WORLD':'聚会、女孩求助与住处人声在叙述者自述无关的时期仍存在。',
      'I-BOUNDARIES':'叙述者区分梦中的死亡和醒后的枪，并说女孩救了他。',
      'I-OPEN':'叙述者说不知星为何使他想到今夜；梦中同行者明确回指它。',
      'H-S1':'原文先述两月前决定及购枪，再述见星后定为今夜。',
      'H-S2':'梦中同行者否认天狼星，并回指现实云间所见之星。',
      'H-S3':'另一太阳的熟悉光之后，他想到旧地球和女孩。',
      'H-S4':'另一太阳、另一地球以及居民谈及的群星出现于不同段落。',
      'H-S5':'叙述者明说不知道为什么因星想到今夜。',
      'H-S6':'第一次星的出现紧接既存死亡决定落实为今夜。',
      'H-S7':'梦旅抵达另一地球；叙述者醒回原来的椅子。'}
    questions={
      'story-architecture':'人物何时决定、观众何时知道及何时能回接？',
      'scene-development':'哪些已有关系、信息与 motif 在本场需要可感知？',
      'character-dramaturgy':'现有角色弧的各阶段如何区分退出、参与及参与中的伤害？',
      'director':'哪些关系需要观众感知，同时保留哪些未知与歧义？',
      'dramatic-performance-direction':'阶段状态在本场哪些已有动作中需要可感，而不替代当前 objective / tactic？',
      'costume-design':'当前自我照料与社会参与状态，提出什么需要服装回应的问题？',
      'specialized-asset-design':'已定角色状态与源身份给资产提出什么问题，哪些心理模板应避免？',
      'production-design':'怎样分别核对世界事实与人物对世界的关系，不让后者改写前者？',
      'cinematography':'哪些对象与注意变化的关系必须可被观众识别？',
      'lighting-design':'在原有天气与时间内，哪种识别关系需要保持可读？',
      'color-design':'如何保持不同天体身份与关系，避免把关联简化为善恶二色？',
      'sound-design':'社会接近或距离的问题有哪些源依据，哪些人仍有自主生活？',
      'music-direction':'这里是否应让位或不配乐，以保留歧义与源中关系？',
      'editorial-design':'哪些复现、后知与信息回声需要可读，哪些未知需要保留？',
      'shot-design':'现有场景中哪种关系需要覆盖，且不新增事件？'}
    items=[]
    for identity,section,claim,support,counter,confidence,status,limitation in rows:
        anchors=list(dict.fromkeys(support+counter))
        item: dict[str,Any]={'id':identity,'meaning':claim,'why':'沿用 R3D-A 已审计候选；供本版高杠杆用户审阅。','scopeLevel':'FILM','scopeRef':scope['refs'][0],'priority':'SHOULD','kind':'RELATIONSHIP'}
        fs=scope if not identity.startswith('H-') else {'kind':'MOTIF','refs':['STAR']}
        evidence=[dict(id='E-'+identity,anchorIds=support,basis='RECURRENCE' if identity=='H-S2' else 'DIRECT_TEXT',strength='STRONG' if confidence=='HIGH' else 'LIMITED',reason=claim+' 范围与反证见限定。')] if support else []
        f=InterpretationFacet.model_validate(dict(version=1,workRef=scope['refs'][0],branchId='r3d-candidate',scope=fs,
          layer='INTERPRETIVE_HYPOTHESIS' if status in ('UNSUPPORTED','REJECTED') else 'WORKING_INTERPRETATION',status=status,section=section,
          sourceRef=dump_contract(source_ref),thesisRefs=[dump_contract(thesis_ref)],factRefs=[],
          observations=[dict(id='O-'+identity,version=1,observation=observations[identity],scope=fs,anchorIds=anchors)],supporting=evidence,
          counterEvidence=[dict(id='C-'+identity,anchorIds=counter,basis='DIRECT_TEXT',strength='STRONG',reason=limitation)],counterSearch='COUNTER_EVIDENCE_FOUND',
          reviewedAnchorIds=anchors,counterAssessments=[dict(evidenceId='C-'+identity,effect='CONTRADICTS' if status in ('REJECTED','UNSUPPORTED') else 'LIMITS_SCOPE',reason=limitation)],
          limitations=[limitation],confidence=confidence,confidenceReason='R3D-A 的限定性证据判断；SELF_AUDIT，不是用户批准。',
          groupId='STAR' if identity.startswith('H-') else None,negativeBoundaries=[limitation],canonConsistency='PRESERVED',reviewBasis='SELF_AUDIT'))
        if identity=='I-CORE':
            f.implications=tuple(InterpretiveImplication.model_validate(dict(
                id='Q-'+dept,department=dept,scope=scope,form='QUESTION',question=q,limitations=['具体 HOW 由专业 owner 决定；待用户批准后才能正式下发。'],boundaryReview='QUESTIONS_ONLY',
                characterStateRef='C_MAN:sealed' if dept in ('character-dramaturgy','dramatic-performance-direction','costume-design','specialized-asset-design') else None,
                worldFactRefs=['E_VISIT','E_GIRL'] if dept in ('production-design','sound-design','director') else [],musicPolicy='YIELD' if dept=='music-direction' else 'OPEN')) for dept,q in questions.items())
        if identity in ('H-S1','H-S2'):
            f.occurrences=(MotifOccurrence.model_validate(dict(id='STAR-REALITY-01' if identity=='H-S1' else 'STAR-DREAM-01',anchorIds=['A005'] if identity=='H-S1' else ['A018','A019'],scope=fs,
                localFunction=claim,evolution='OPEN' if identity=='H-S1' else 'RECONTEXTUALIZE',relatedInterpretationIds=['H-S1','H-S2','H-S5'])),)
        item['interpretation']=dump_contract(f)
        f.evidence_review=StageReview(authority='literary-source-analysis',subject_hash=evidence_subject(item),status='APPROVED',reviewer='R3D materialization SELF_AUDIT',evidence='逐项保持 R3D-A Board Design / STAR Trace / Character-World-State Audit 的已审计支持、反证与限定；仅证据映射自审，不是用户采用批准。')
        item['interpretation']=dump_contract(f)
        ref=host.retain_interpretation(item,current={k:v for k,v in current.items() if k!=intent_pin(item).key})
        originals[ref.key]=item;current[ref.key]=ref.fingerprint;items.append(item)
    board=project_board(items,originals,current)
    primary={**board,'rows':board['rows'][:8]}
    result={'status':'CANDIDATE','adoption':'NOT_ADOPTED','approvalState':'AWAITING_USER_APPROVAL','approvalRefs':[],
            'sourceAudit':'Literary-Cinema-R3D-A','items':items,'board':board,'primaryRowIds':[i['id'] for i in items[:8]],
            'originals':originals,'current':current,'productionAuthorized':False}
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    (OUT/'interpretation-candidate.json').write_text(text)
    (OUT/'film-interpretation-board-r3d-candidate.md').write_text(render_board(primary))
    fixture=REPO/'plugin/tests/fixtures/r3d';fixture.mkdir(exist_ok=True)
    (fixture/'interpretation-candidate.json').write_text(text)
    print(json.dumps({'items':len(items),'boardRows':8,'approvals':0,'path':str(OUT)},ensure_ascii=False))

if __name__=='__main__':main()
