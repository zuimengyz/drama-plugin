"""User-authorized exact approval only. No screenplay, professional HOW or Runtime edits."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.creative_source import StageReview
from drama_plugin.contracts.interpretation import InterpretationFacet, InterpretationApproval
from drama_plugin.director import pin
from drama_plugin.hosts.creative_source import CreativeSourceHost
from drama_plugin.interpretation import (intent_pin, evidence_subject, evidence_fingerprint,
    validate_interpretation, approved_interpretation, project_board, department_handoff)

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
CREATIVE=PROJECT/'artifacts/flagship-literary-film-01/creative'
OUT=CREATIVE/'screenplay-r3c-r'
AUTH=Path('/Users/zy/.codex/attachments/f941a588-8b02-454d-aaef-6a9b91d964aa/已粘贴的文本.txt')


def main() -> None:
    OUT.mkdir(exist_ok=True)
    previous=json.loads((CREATIVE/'interpretation/interpretation-candidate.json').read_text())
    host=CreativeSourceHost(OUT/'interpretation-store')
    originals=deepcopy(previous['originals']);current=dict(previous['current'])
    for key,value in originals.items():host.store.put(key,value)
    auth_text=AUTH.read_text();auth_hash=hashlib.sha256(AUTH.read_bytes()).hexdigest()
    witness=host.store.put('user-instruction:r3c-r',{'kind':'USER_INSTRUCTION_EVIDENCE','attachmentPath':str(AUTH),
        'sha256':auth_hash,'text':auth_text,'scope':'Interpretation adoption only; no screenplay/production/media approval'})
    actor='USER:attachment-sha256:'+auth_hash
    chosen={'I-CORE','I-CHARACTER','I-RELATION','I-MOTIFS','I-DREAM','I-WORLD','I-BOUNDARIES','I-OPEN','H-S1','H-S2','H-S5'}
    items=[];changes=[];receipts={};receipt_refs={};trusted=[];rows=[]
    for original in previous['items']:
        item=deepcopy(original);identity=str(item['id']);old_ref=intent_pin(original)
        if identity in ('I-CORE','I-RELATION','I-WORLD'):
            f=InterpretationFacet.model_validate(item['interpretation']);f.version+=1
            if identity=='I-CORE':
                item['meaning']='一个把世界、他人乃至自己的存在逐渐体验为“与我无关”、并准备彻底退出的人，在具体生命不断要求他参与之后，经历爱、占有、痛苦、失败与责任，最终仍选择回应具体的人。'
                f.limitations=('本版工作解释，不是 Source Fact；不声称已建立完整虚无主义体系。','不把无能为力固定为自杀唯一或核心原因。','不抹掉同情、羞耻和对旧地球的爱。','参与本身不自动等于善；爱、占有、控制与伤害不能混为同一价值。')
                f.negative_boundaries=f.limitations
                f.supporting=(f.supporting[0].model_copy(update={'anchor_ids':('A003','A005','A009','A027','A036','A038','A040','A041'),
                    'basis':'STRUCTURAL_ECHO','reason':'A003逐渐体验无关并几乎停止思考；A005既有决定；A009同情与羞耻；A027旧地球之爱；A036/A038参与也能占有和伤害；A040/A041仍有局限而回应具体生命。'}),)
                f.reviewed_anchor_ids=tuple(dict.fromkeys((*f.reviewed_anchor_ids,'A005','A027','A036')))
                f.confidence_reason='HIGH 限于有直接文本与跨段结构支持的本版关系轴，不等于原作唯一主旨或心理病因。'
                f.implications=tuple(i.model_copy(update={'limitations':('具体 HOW 由专业 owner 决定；本批准仅授权解释输入，不批准专业方案或生产。',*f.limitations)}) for i in f.implications)
                reason='用户给出新 claim，保留全部四项限制并扩展重新核对的源锚点。'
            elif identity=='I-RELATION':
                f.limitations=(*f.limitations,'NON_EXCLUSIVE / NOT_THE_SOLE_THEME：可作为本版本正式专业输入，但不得提升为唯一作品主旨。')
                f.negative_boundaries=(*f.negative_boundaries,'不得提升为唯一作品主旨。')
                reason='claim 沿用现有候选；新增用户非唯一适用限制，因此新版本重新绑定。'
            else:
                item['meaning']='世界仍然有自己的生活、欲望、争论、劳动、苦难和声音；主人公正在退出的，是自己与这个世界之间的关系，而不是世界本身已经死亡。'
                f.limitations=(*f.limitations,'这是跨部门解释约束，不证明任何未记载的具体职业、街上劳动事件或城市活动；具体 World Fact 由 Source / Scene 决定。','不得默认全城死寂、所有人冷漠、所有画面极暗或所有声音悲伤；也不得推成幸福温暖或不存在贫困。')
                f.negative_boundaries=f.limitations
                f.confidence='MEDIUM'
                f.confidence_reason='A004/A006/A007直接支持他人生活、争论、需要、声音和苦难；扩展措辞中的劳动/欲望作为本版关系层概括，不足以声称具体源事件，故限定为 MEDIUM。'
                reason='采用用户扩展措辞，新版本；保留世界事实边界，扩展概括不冒充具体原文事实。'
            f.evidence_review=None;item['interpretation']=dump_contract(f)
            f.evidence_review=StageReview(authority='literary-source-analysis',subject_hash=evidence_subject(item),status='APPROVED',
                reviewer='R3C-R evidence revalidation / SELF_AUDIT',evidence=reason+' 支持、反证、scope 与限制逐项复核；这是证据审阅，USER 批准由附件原文单独绑定。')
            item['interpretation']=dump_contract(f)
            new_ref=host.retain_interpretation(item,current=current,previous_ref=old_ref)
            originals[new_ref.key]=item;current[new_ref.key]=new_ref.fingerprint
            changes.append(dict(id=identity,previousRef=dump_contract(old_ref),currentRef=dump_contract(new_ref),reason=reason))
        f=validate_interpretation(item,originals,current);ref=intent_pin(item);items.append(item)
        if identity not in chosen:continue
        mode='PRESERVE_AMBIGUITY' if identity in ('I-OPEN','H-S5') else 'APPROVED_FOR_THIS_ADAPTATION'
        receipt=InterpretationApproval.model_validate(dict(subjectId=identity,subjectFingerprint=fp(item),workRef=f.work_ref,
            branchId=f.branch_id,approvedBy=[actor],actorType='USER',decision='APPROVE',mode=mode,
            scope=dump_contract(f.scope),evidenceFingerprint=evidence_fingerprint(item),version=1))
        approval_ref=pin('interpretation-approval:'+ref.key,dump_contract(receipt))
        # The present user message explicitly grants these choices. Supply that
        # actual authorization through the existing Host trust boundary.
        retained=host.retain_interpretation_approval(ref,dump_contract(receipt),current=current,approved_refs=(approval_ref,))
        assert retained==approval_ref
        originals[retained.key]=dump_contract(receipt);current[retained.key]=retained.fingerprint;trusted.append(retained)
        approved_interpretation(ref,retained,originals,current,(retained,))
        receipts[identity]=dump_contract(receipt);receipt_refs[identity]=retained
        rows.append(dict(id=identity,version=f.version,interpretationRef=dump_contract(ref),approvalRef=dump_contract(retained),mode=mode))
    board=project_board(items,originals,current,approval_refs=receipt_refs,approved_refs=tuple(trusted))
    core=next(i for i in items if i['id']=='I-CORE');core_ref=intent_pin(core)
    handoffs=[department_handoff(core_ref,receipt_refs['I-CORE'],i.id,originals,current,approved_refs=tuple(trusted))
              for i in InterpretationFacet.model_validate(core['interpretation']).implications]
    result={'status':'USER_INTERPRETATION_APPROVAL_MATERIALIZED','screenplayStatus':'NOT_ADOPTED',
        'authorizationEvidenceRef':dump_contract(witness),'authorizationFileSha256':auth_hash,
        'items':items,'changes':changes,'approvalReceipts':receipts,'approvalRows':rows,
        'approvedRefs':[dump_contract(r) for r in trusted],'originals':originals,'current':current,'board':board,
        'handoffs':handoffs,'productionAuthorized':False,'professionalDesignApproved':False,
        'preservedUnapproved':{'H-S3':'OPEN','H-S4':'OPEN','H-S6':'UNSUPPORTED','H-S7':'REJECTED'}}
    (OUT/'interpretation-approved.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    lines=['# Literary Cinema R3C-R — Interpretation Approval Receipt','',
      '用户授权已通过真实 R3D Runtime 落盘。只批准本版解释及其适用范围；不批准 Source Fact、剧本、专业方案或生产。','',
      '授权附件 SHA-256：`'+auth_hash+'`。USER actor 追溯至原始附件，证据 SELF_AUDIT 与用户批准分离。','',
      '| Item | Version | Approval mode | Exact interpretation fingerprint | Exact approval fingerprint |','|---|---|---|---|---|']
    for r in rows:lines.append('| '+str(r['id'])+' | '+str(r['version'])+' | '+r['mode']+' | `'+r['interpretationRef']['fingerprint']+'` | `'+r['approvalRef']['fingerprint']+'` |')
    lines.extend(['','I-CORE、I-RELATION、I-WORLD 为 v2；旧版本保留。其余批准条目沿用 v1 精确 hash。H-S3/H-S4 保持 OPEN 且无正式传播批准；H-S6 UNSUPPORTED、H-S7 REJECTED 不传播。','',
      '沿用原 interpretation branch `r3d-candidate` 以保持版本链身份；目录名称不授予或取消批准。11 个 receipt 已通过 approved_interpretation；15 个 I-CORE 问题 handoff 已通过 department_handoff，没有专业 HOW。','',
      '[实际 artifact](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/creative/screenplay-r3c-r/interpretation-approved.json)',''])
    (HERE/'Literary-Cinema-R3C-R-Interpretation-Approval-Receipt.md').write_text('\n'.join(lines))
    print(json.dumps({'approved':len(rows),'newVersions':[r['id'] for r in changes],'questionHandoffs':len(handoffs),'screenplayEdited':False},ensure_ascii=False))

if __name__=='__main__':main()
