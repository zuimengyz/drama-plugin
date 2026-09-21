"""Character Art assembly from legacy production-design briefs, outside providers."""
from typing import Any
from .contracts.base import dump_contract, sha256_canonical
from .contracts.production_design import CastingBrief, CharacterVisualSpec
from .contracts.visual_medium import legacy_medium_intent
from .visual_medium import compile_character_art


def compile_casting_brief(brief: CastingBrief) -> dict[str, Any]:
    brief = CastingBrief.model_validate(dump_contract(brief))
    if sha256_canonical(brief.source_content) != brief.source_fingerprint:
        raise ValueError('Casting source changed')
    spec = brief.source_content.spec
    if not isinstance(spec, CharacterVisualSpec):
        raise ValueError('Character source required')
    r, c = brief.reconciliation, brief.conditions
    sections = [
        '仅一个人物选角候选；保持当前构图和人物事实。',
        '文化与人物方向：' + r.population_direction,
        f'角色：{spec.character_identity}；{spec.dramatic_role}。目标：{spec.visual_objective}',
        f'年龄印象：{r.apparent_age_min}–{r.apparent_age_max} 岁；具体年龄感与身份仅由当前角色规格决定。',
        '原创虚构人物脸，不模仿任何现实演员、明星或影视作品人物。',
        '统一发式：' + r.hair + '；统一胡须：' + r.beard,
        '脸部共同硬约束：' + '；'.join(r.face),
        '本候选独有的骨相路径：' + brief.variation,
        '身体共同硬约束：' + '；'.join(r.body),
        '源规格体态依据：' + '；'.join(str(v) for v in dump_contract(spec.body).values() if v),
        '权威来自人：' + r.authority,
        '统一测试服装：' + c.clothing + '。使用当前测试条件指定的衣物与道具；不额外添加身份装备。',
        '统一背景：' + c.background + '。只有一个人，不出现辅助演员或身高参照人物。',
        '统一灯光：' + c.lighting,
        '统一摄影：' + c.camera + '；' + c.framing,
        '统一身体朝向：' + c.orientation + '；统一姿态：' + c.posture,
        '明确排除：' + '；'.join(r.avoid),
        '源规格禁项：' + '；'.join(spec.avoid),
        '历史边界：' + '；'.join(spec.historical_constraints.constraints),
        '这是一张尚待用户选择的选角提案；比例和具体面孔是影视设计选择，不是历史人物真实肖像复原。无文字、标签、水印。',
    ]
    intent = brief.visual_medium_intent or legacy_medium_intent('LIVE_ACTION_REALIST')
    return compile_character_art(intent,
        [dict(id='casting.'+str(i), text=text, sources=['castingBrief']) for i, text in enumerate(sections)],
        legacy=brief.visual_medium_intent is None,
        source_intent='castingBrief.visualMediumIntent' if brief.visual_medium_intent else 'legacy:photographicCastingBrief')
