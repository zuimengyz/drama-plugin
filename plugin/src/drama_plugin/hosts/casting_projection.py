"""Deterministic casting projection. No provider calls, billing or asset writes."""
from __future__ import annotations
from typing import Any
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.production_design import CastingBrief, CharacterVisualSpec


def full_body_seedream_projection(brief: dict[str, Any], evidence: dict[str, Any], *, seed: int) -> dict[str, Any]:
    """Existing official T2I route, qualified for exactly one whole-body candidate."""
    from datetime import datetime, timezone
    if (brief.get('status') != 'EXECUTABLE_SINGLE_CANDIDATE'
            or brief.get('purpose') != 'CHARACTER_FULL_BODY_CASTING'
            or brief.get('maxOutputs') != 1 or not brief.get('stopAfterFirstResult')
            or sha256_canonical(brief['prompt']) != brief['promptFingerprint']):
        raise ValueError('EXECUTABLE_FULL_BODY_BRIEF_REQUIRED')
    schema = evidence['schema']
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(evidence['checkedAt'])).total_seconds()
    nodes = {n['id']: n for n in schema['nodes']}
    if (not 0 <= age <= 900 or schema['id'] != 'api_bytedance_seedream_5_0_pro_t2i'
            or nodes['3']['class_type'] != 'ByteDanceSeedreamNodeV3'
            or nodes['2']['class_type'] != 'SaveImageAdvanced'
            or not {'model.width', 'model.height', 'prompt'} <= nodes['3']['inputs'].keys()
            or not 0 <= seed <= 2147483647):
        raise ValueError('CURRENT_OFFICIAL_IMAGE_TEMPLATE_REQUIRED')
    return {'name': schema['id'], 'input_overrides': {'3': {
        'prompt': brief['prompt'], 'model': 'seedream 5.0 pro', 'model.size_preset': 'Custom',
        'model.width': 1664, 'model.height': 2496, 'model.prompt_optimization': 'standard',
        'model.seed': seed, 'model.watermark': False, 'model.thinking': True}}}


def seedream_casting_projection(brief: CastingBrief, *, seed: int) -> dict[str, Any]:
    brief = CastingBrief.model_validate(dump_contract(brief))
    if sha256_canonical(brief.source_content) != brief.source_fingerprint:
        raise ValueError('Casting source changed')
    spec = brief.source_content.spec
    if not isinstance(spec, CharacterVisualSpec):
        raise ValueError('Character source required')
    if not 0 <= seed <= 2147483647:
        raise ValueError('Provider seed out of range')
    r, c = brief.reconciliation, brief.conditions
    sections = [
        '生成一张真实人物选角测试照片，仅一个人。不是插画、海报或多人拼图。',
        '文化与人物方向：' + r.population_direction,
        f'角色：{spec.character_identity}；{spec.dramatic_role}。目标：{spec.visual_objective}',
        f'年龄印象：{r.apparent_age_min}–{r.apparent_age_max} 岁；是青年成年统帅，不是老将。',
        '原创虚构人物脸，不模仿任何现实演员、明星或影视作品人物。',
        '统一发式：' + r.hair + '；统一胡须：' + r.beard,
        '脸部共同硬约束：' + '；'.join(r.face),
        '本候选独有的骨相路径：' + brief.variation,
        '身体共同硬约束：' + '；'.join(r.body),
        '源规格体态依据：' + '；'.join(str(v) for v in dump_contract(spec.body).values() if v),
        '权威来自人：' + r.authority,
        '统一测试服装：' + c.clothing + '。无甲、无护肩、无兵器；衣服不是候选差异。',
        '统一背景：' + c.background + '。只有一个人，不出现辅助演员或身高参照人物。',
        '统一灯光：' + c.lighting,
        '统一摄影：' + c.camera + '；' + c.framing,
        '统一身体朝向：' + c.orientation + '；统一姿态：' + c.posture,
        '明确排除：' + '；'.join(r.avoid),
        '源规格禁项：' + '；'.join(spec.avoid),
        '历史边界：' + '；'.join(spec.historical_constraints.constraints),
        '这是一张尚待用户选择的选角提案；比例和具体面孔是影视设计选择，不是历史人物真实肖像复原。无文字、标签、水印。',
    ]
    return {'tool': 'run_template', 'name': 'api_bytedance_seedream_5_0_pro_t2i',
            'description': brief.candidate_id,
            'input_overrides': {'3': {'prompt': '\n'.join(sections), 'model': 'seedream 5.0 pro',
                'model.size_preset': 'Custom', 'model.width': 1664, 'model.height': 2496,
                'model.prompt_optimization': 'standard', 'model.seed': seed,
                'model.watermark': False, 'model.thinking': True}}}


def audit_casting_batch(briefs: list[CastingBrief], items: list[dict[str, Any]],
                        *, expected_count: int = 4) -> dict[str, Any]:
    if len(briefs) != expected_count or len(items) != expected_count:
        raise ValueError('Unexpected casting count')
    if len({b.candidate_id for b in briefs}) != expected_count or len({b.variation for b in briefs}) != expected_count:
        raise ValueError('Duplicate candidate direction')
    for field in ('conditions', 'reconciliation', 'source_content'):
        if len({sha256_canonical(getattr(b, field)) for b in briefs}) != 1:
            raise ValueError('Unequal casting test or source')
    for brief, item in zip(briefs, items):
        seed = item.get('input_overrides', {}).get('3', {}).get('model.seed')
        if not isinstance(seed, int) or item != seedream_casting_projection(brief, seed=seed):
            raise ValueError('Provider projection differs from the audited casting brief')
    return {'status': 'PASS', 'transport': 'MCP', 'modality': 'IMAGE', 'desktopFallback': False,
            'candidateCount': expected_count, 'oldReferenceInputs': [],
            'uniformConditionsFingerprint': sha256_canonical(briefs[0].conditions),
            'sourceFingerprint': briefs[0].source_fingerprint,
            'reconciliationFingerprint': sha256_canonical(briefs[0].reconciliation),
            'briefFingerprints': [sha256_canonical(b) for b in briefs],
            'projectionFingerprints': [sha256_canonical(i) for i in items],
            'meaning': 'Projection integrity only; generated-image conformity needs visual review.'}


def costume_fit_eligible(reviews: dict[str, str]) -> bool:
    """Shortlisting permits a fit test, never formal adoption or video."""
    if any(v not in {'PASS', 'PARTIAL', 'REJECT', 'SHORTLIST'} for v in reviews.values()):
        raise ValueError('Unknown casting review')
    return sum(v == 'PASS' for v in reviews.values()) >= 2 or sum(v == 'SHORTLIST' for v in reviews.values()) >= 2
