"""Provider-owned character budgets and lossless structural prompt compaction.

No free-text paraphrasing: creative values, actor scopes and dialogue survive.
Only generated labels/separators and explicitly identified provenance change.
"""
from __future__ import annotations

import re
from typing import Any


class PromptBudgetExceeded(ValueError):
    def __init__(self, budget: dict[str, Any]):
        self.budget = budget
        super().__init__('PROVIDER_PROMPT_BUDGET_EXCEEDED: '
                         f"model={budget['model']} original_length={budget['originalCharacters']} "
                         f"compressed_length={budget['compressedCharacters']} "
                         f"hard_limit={budget['hardMaxPromptCharacters']}")


def prompt_limit(capability: dict[str, Any], semantics: dict[str, Any], variant: str = '') -> tuple[int | None, str]:
    """Current node schema > adapter capability > reviewed static fallback."""
    node = capability.get('node_schema', {})
    limits = []
    if node.get('maxPromptCharacters') is not None:
        limits.append(node['maxPromptCharacters'])
    for field in node.get('input_details', []):
        if field['name'] != semantics['prompt'] or (field.get('applies_when') and variant not in field['applies_when']):
            continue
        for key in ('maxPromptCharacters', 'max_length'):
            if field.get(key) is not None:
                limits.append(field[key])
        # Some MCP nodes publish the hard bound only in human-readable metadata.
        match = re.search(r'(?:max(?:imum)?(?: length of)?\s+)(\d+)\s+characters', field.get('tooltip', ''), re.I)
        if match:
            limits.append(int(match[1]))
    if limits:
        source = 'runtime_node_schema'
    elif capability.get('maxPromptCharacters') is not None:
        limits = [capability['maxPromptCharacters']]
        source = 'provider_capability'
    elif semantics.get('prompt_limit') is not None:
        limits = [semantics['prompt_limit']]
        source = 'adapter_fallback'
    else:
        return None, 'NOT_DECLARED'
    if any(type(value) is not int or value <= 0 for value in limits):
        raise ValueError('INVALID_PROVIDER_PROMPT_LIMIT')
    return min(limits), source


# These are compiler-owned field labels, never replacements inside creative text.
LABELS = dict(zip(
    ('realism palette dominant accent lighting philosophy fill faceShadowAllowed imageCharacter saturation contrast highlight blackLevel '
     'materials skin costume metal environment atmosphere cameraPhilosophy forbidden '
     'interactionTarget spatialProjection externalExpression externalControl bodyLoad breath release continuityIn continuityOut coordination instructions '
     'body_state posture weight movement eyes head hands visible_breath prop partner distance timing continuity do_not '
     'voice_core interaction spatial_projection pace rhythm intensity breath_support phrase_attack articulation emphasis pause_function sentence_closure coloration '
     'startState actions actor behavior target trigger endState overlapReason '
     'shotSize composition placement height subjectOrientation lensIntent focusTarget focusTransition movementClass amplitude openingComposition endingComposition '
     'dimension allowed reason nativeAudioPolicy canonicalDialogueBindings diegetic ambience intentionalSilence generatedMusic route').split(),
    ('写实 色彩 主色 辅色 光线 光源 补光 允许脸影 影调 饱和 对比 高光 暗部 '
     '材质 皮肤 衣料 金属 环境 氛围 摄影原则 禁止 '
     '对象 声场 表达 克制 负荷 呼吸 释放 入场连续 出场连续 协同 指令 '
     '身体 姿态 重心 运动 眼神 头 手 可见呼吸 道具 对手 距离 时机 连续 禁止 '
     '音色 互动 声场 语速 节奏 强度 气息 起句 咬字 重音 停顿 句尾 声色 '
     '起态 动作 人 行为 对象 触发 终态 重叠理由 '
     '景别 构图 机位 高度 朝向 透视 焦点 转焦 运镜类 幅度 起幅 落幅 '
     '约束 允许 理由 原声 对白绑定 场内声 环境声 静默 音乐 风格').split(), strict=True))

PROVENANCE = {'directorIntentFingerprint', 'grammarFingerprint', 'beatId', 'spokenContentId'}


def compact_prose(value: Any, *, performance: bool = False) -> str:
    if isinstance(value, dict):
        return '；'.join(f'{LABELS.get(k, k)}:{compact_prose(v)}' for k, v in value.items()
                        if v is not None and v != [] and not (performance and k in PROVENANCE))
    if isinstance(value, (list, tuple)):
        # Brackets retain each actor/instruction object's scope.
        return '；'.join('{' + compact_prose(v) + '}' if isinstance(v, dict) else compact_prose(v) for v in value)
    return str(value)


def budget_prompt(original: str, compact: str, *, model: str, limit: int | None,
                  source: str, reserved: int = 0) -> tuple[str, dict[str, Any]]:
    if type(reserved) is not int or reserved < 0:
        raise ValueError('INVALID_PROMPT_RESERVATION')
    effective = None if limit is None else limit - reserved
    fits = effective is None or len(original) <= effective
    final = original if fits else compact
    status = 'FIT' if fits else 'COMPRESSIBLE' if effective is not None and len(compact) <= effective else 'EXCEEDED'
    budget = {'model': model, 'maxPromptCharacters': limit, 'hardMaxPromptCharacters': limit,
              'reservedPromptCharacters': reserved, 'effectivePromptBudget': effective,
              'limitSource': source, 'status': status, 'originalCharacters': len(original),
              'compressedCharacters': len(final), 'finalCharacters': len(final),
              'rule': 'structural-labels-and-provenance-v1' if not fits else 'unchanged'}
    if status == 'EXCEEDED':
        raise PromptBudgetExceeded(budget)
    return final, budget
