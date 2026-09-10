"""Director IR composition, offline review and the existing selection handoff.

The Host authors behavior, not this module. No planner, provider or paid call.
"""
from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.cinematic import CinematicShotSpec, VisualBible


def resolve_visual_bible(base: dict[str, Any], overrides: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Work base, then explicit Episode/Scene/Shot overlays; arrays replace."""
    if set(overrides) - {'episode', 'scene', 'shot'}:
        raise ValueError('Unknown visual inheritance scope')
    effective = dump_contract(VisualBible.model_validate(base))
    layers = []
    def merge(old: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
        result = deepcopy(old)
        for key, value in patch.items():
            if key not in old or value is None:
                raise ValueError('Unknown override key or ambiguous null: ' + key)
            if isinstance(value, dict) and isinstance(old[key], dict):
                result[key] = merge(old[key], value)
            else:
                result[key] = deepcopy(value)
        return result
    for scope in ('episode', 'scene', 'shot'):
        patch = overrides.get(scope, {})
        inherited = deepcopy(effective)
        effective = dump_contract(VisualBible.model_validate(merge(effective, patch)))
        layers.append({'scope': scope, 'inherited': inherited, 'override': patch, 'effective': deepcopy(effective)})
    material = {'base': dump_contract(VisualBible.model_validate(base)), 'overrides': overrides, 'effective': effective}
    return {**material, 'layers': layers, 'fingerprint': sha256_canonical(material)}


def narrative_source(context: dict[str, Any]) -> dict[str, Any]:
    """Pin selected formal creative context; unrelated Media/ledger is not canon."""
    result: dict[str, Any] = {}
    for kind in ('work', 'script', 'episode', 'scene', 'shot'):
        entity = context[kind]
        content = {k: v for k, v in entity['content'].items() if k not in {
            'mediaBindings', 'creativeArtifacts', 'productionArtifacts', 'productionStage',
            'productionRoute', 'finishingRevisions', 'finishingReferences', 'mediaAuthorization',
            'productionPolicy', 'productionMediaInputs'}}
        result[kind] = {'id': entity['id'], 'title': entity.get('title'), 'content': content}
    if (context['shot']['scene_id'] != context['scene']['id'] or
            context['scene']['episode_id'] != context['episode']['id'] or
            context['episode']['script_id'] != context['script']['id'] or
            context['script']['work_id'] != context['work']['id']):
        raise ValueError('Formal narrative parent chain mismatch')
    return result


def validate_canon(spec: CinematicShotSpec, context: dict[str, Any]) -> None:
    if spec.source_fingerprint != sha256_canonical(narrative_source(context)):
        raise ValueError('STALE_CINEMATIC_NARRATIVE_SOURCE')
    if (spec.work_id, spec.scene_id, spec.shot_id) != (context['work']['id'], context['scene']['id'], context['shot']['id']):
        raise ValueError('Cinematic scope mismatch')
    shot = context['shot']['content']
    if spec.duration_seconds * 1000 != shot['plannedDurationMs']:
        raise ValueError('Director cannot silently change formal Shot duration')
    bound = [x['spokenContentId'] for x in shot.get('spokenContentBindings', [])]
    spoken = {x['id']: x for x in context['scene']['content'].get('spokenContent', [])}
    if [d.spoken_content_id for d in spec.dialogue] != bound:
        raise ValueError('Director cannot add, omit or reorder canonical dialogue')
    coverage = context.get('dialogueCoverage')
    intervals = {}
    if coverage:
        from drama_plugin.visual.dialogue_coverage import coverage_intervals
        intervals = coverage_intervals(context, coverage).get(spec.shot_id, {})
    bindings = {b['spokenContentId']: b for b in shot.get('spokenContentBindings', [])}
    for d in spec.dialogue:
        original = spoken[d.spoken_content_id]
        if (d.text, d.speaker_key) != (original['text'], original['speakerKey']):
            raise ValueError('Director cannot rewrite canonical words or speakers')
        role = bindings[d.spoken_content_id].get('coverageIntent', 'ON_SCREEN_SPEAKER')
        if d.coverage_intent != role:
            raise ValueError('CANONICAL_COVERAGE_ROLE_CHANGED')
        if coverage:
            expected = intervals.get(d.spoken_content_id)
            if expected is None or any(getattr(d, key) != value for key,value in expected.items()):
                raise ValueError('DIRECTOR_DIALOGUE_SLICE_CHANGED')
        elif d.canonical_interval is not None or d.text_range is not None:
            raise ValueError('SHARED_DIALOGUE_COVERAGE_EVIDENCE_REQUIRED')
        elif (d.end-d.start)*1000 + .001 < original['estimatedDurationMs']:
            raise ValueError('Dialogue slot is shorter than the canonical planning estimate')
    if spec.source_sound_intent and list(spec.source_sound_intent.canonical_dialogue_bindings) != bound:
        raise ValueError('SOURCE_SOUND_CANONICAL_BINDINGS_CHANGED')


def review_direction(spec: CinematicShotSpec, *, neighbors: tuple[CinematicShotSpec, ...] = ()) -> dict[str, Any]:
    """Focused findings, not an art score or substitute for Host narrative review."""
    findings: list[dict[str, str]] = []
    def note(severity: str, field: str, evidence: str, revise: str) -> None:
        findings.append({'severity': severity, 'field': field, 'evidence': evidence, 'revise': revise})
    empty_words = re.compile(r'电影感|史诗感|悲伤|紧张|愤怒|英勇|高级感|大片感|震撼|真实|cinematic|epic|dramatic|masterpiece', re.I)
    actions = [a.behavior for b in spec.performance.beats for a in b.actions]
    for i, text in enumerate(actions):
        remainder = re.sub(r'[\s，。！、,.!;；/→]+', '', empty_words.sub('', text))
        if not remainder:
            note('MAJOR', f'actions[{i}]', f'只有抽象标签：{text}', '改成角色对具体对象采取的可见行为及触发点；不改剧情结果。')
    if len(actions) > 1 and len(set(actions)) == 1:
        note('WARN', 'performance.beats', '各节拍重复同一个行为，未显示变化或持续原因。', '确认是有意义的持续动作，或仅修订转折后的视线/反应。')
    if spec.behavior_anchor is None and not spec.anchor_omission_reason:
        note('WARN', 'behaviorAnchor', '未说明开场正在做什么，也未解释省略。', '由开场连续性决定是否需要anchor；已在行动中的镜头可说明不另加程序。')
    camera = spec.cinematography
    if camera.movement_class != 'LOCKED' and (not camera.trigger or not camera.motivation):
        note('WARN', 'cinematography.movement', f'运动“{camera.movement}”缺触发或观察动机。', '补充为何此刻移动；没有动机可改固定机位。')
    if neighbors and camera.movement_class != 'LOCKED' and all(x.cinematography.movement == camera.movement for x in neighbors):
        note('WARN', 'cinematography.sequence', '所供相邻镜头采用同种运动。', '审查各自戏剧动机，保留确有用途的重复，不按运动数量评分。')
    if any(x.scene_id == spec.scene_id and x.visual_bible.palette != spec.visual_bible.palette for x in neighbors):
        note('WARN', 'visualBible.sequence', '同场相邻镜头的有效色系不同。', '核对是否有显式局部override及动机；无依据则恢复继承，不重写场景。')
    if not spec.secondary_motion and not spec.secondary_motion_omission_reason:
        note('WARN', 'secondaryMotion', '未说明相关二级运动或为何不需要。', '只补当前动作实际引起的一项反馈；无需满屏特效。')
    environmental = [m for m in spec.secondary_motion if any(k in m.element for k in ('火', '雨', '尘', '水', '烟', '雪'))]
    if environmental and not spec.environment_interaction:
        note('WARN', 'environmentInteraction', '存在环境效果，却没有受影响对象、遮挡或材质反馈。', '补明确因果和空间层次；不新造场外事件。')
    for rule in spec.stability_contract:
        if rule.allowed == rule.forbidden:
            note('MAJOR', 'stabilityContract', f'{rule.dimension}同一行为既允许又禁止。', '只界定当前镜头自由度，不全局锁死。')
    return {'status': 'FAIL' if any(f['severity'] == 'MAJOR' for f in findings) else 'PASS_WITH_NOTES' if findings else 'PASS',
            'findings': findings, 'scope': 'OFFLINE_EXECUTABILITY_ONLY; historical meaning and performance choices require Host review'}


def execution_brief(spec: CinematicShotSpec) -> str:
    """Neutral projection; no universal length target or provider syntax."""
    c = spec.cinematography
    b = spec.visual_bible
    lines = [f'用途：{spec.narrative_intent}', f'开场：{spec.opening_state}',
             f'视觉：{b.realism}；主色{",".join(b.palette.dominant)}；{b.lighting.philosophy}；{spec.lighting}',
             f'质感：{b.image_character.saturation}；{b.image_character.contrast}；{b.image_character.highlight}；{b.image_character.black_level}',
             f'材质：{b.materials.skin}；{b.materials.costume}；{b.materials.metal}；{b.materials.environment}',
             f'摄影：{c.shot_size}，{c.placement}，{c.height}；{c.composition}；{c.subject_orientation}；{c.lens_intent}',
             f'运动：{c.movement}，幅度{c.amplitude}；触发{c.trigger or "保持观察"}；动机{c.motivation or "固定构图容纳行动"}',
             f'焦点：{c.focus_target}；{c.focus_transition}；构图{c.opening_composition}→{c.ending_composition}',
             f'表演目的：{spec.performance.objective}；对象{spec.performance.interaction_target}']
    if spec.behavior_anchor:
        a = spec.behavior_anchor
        lines.append(f'正在进行：{a.actor}{a.ongoing_activity}；被{a.interruption}打断/改变。')
    for beat in spec.performance.beats:
        lines.append(f'{beat.start:g}–{beat.end:g}秒 {beat.kind}：' + '；'.join(
            f'{a.actor}：{a.behavior}' + (f'（因{a.trigger}）' if a.trigger else '') for a in beat.actions))
    for d in spec.dialogue:
        lines.append(f'{d.start:g}–{d.end:g}秒 {d.speaker_key}对{d.target}说：“{d.text}” {d.delivery}；说完{d.after_line}')
    lines += [f'二级运动：{m.cause}→{m.element}{m.response}；边界{m.limit}' for m in spec.secondary_motion]
    lines += [f'物理反馈：{m.source}{m.effect}→{m.affected}{m.response}；{m.occlusion_or_depth}' for m in spec.environment_interaction]
    lines += [f'稳定边界 {r.dimension}：允许{r.allowed}；不允许{r.forbidden}' for r in spec.stability_contract]
    lines.append('收尾：' + spec.ending_state)
    return '\n'.join(lines)


def validated_upstream_performance(raw: dict[str, Any], spec: CinematicShotSpec) -> dict[str, Any]:
    """Reuse existing DPD authority when supplied, without inventing it for silent Shots."""
    from drama_plugin.contracts.dpd import DPDSnapshot
    from drama_plugin.dpd import compose_dpd
    snapshot = DPDSnapshot.model_validate(raw)
    if snapshot != compose_dpd(snapshot.scene, snapshot.beat, snapshot.line):
        raise ValueError('STALE_UPSTREAM_DPD')
    if snapshot.effective.scene_id != spec.scene_id or not any(
            d.spoken_content_id == snapshot.line.spoken_content_id and d.speaker_key == snapshot.line.speaker
            for d in spec.dialogue):
        raise ValueError('UPSTREAM_DPD_SCOPE_OR_SPEAKER_MISMATCH')
    return dump_contract(snapshot)


def freeze_direction(spec: CinematicShotSpec, *, context: dict[str, Any], visual_resolution: dict[str, Any],
                     host_review: str) -> dict[str, Any]:
    spec = CinematicShotSpec.model_validate(dump_contract(spec))
    validate_canon(spec, context)
    resolved = resolve_visual_bible(visual_resolution['base'], visual_resolution['overrides'])
    if (resolved != visual_resolution or resolved['fingerprint'] != spec.visual_bible_fingerprint
            or resolved['effective'] != dump_contract(spec.visual_bible)):
        raise ValueError('Stale/inconsistent inherited VisualBible')
    review = review_direction(spec)
    if review['status'] == 'FAIL' or not host_review.strip():
        raise ValueError('Resolve major direction findings and record Host canon review before freeze')
    material = {'state': 'CINEMATIC_DIRECTION_FROZEN', 'spec': dump_contract(spec),
                'visualResolution': {k: v for k, v in resolved.items() if k != 'layers'},
                'review': review, 'hostReview': host_review}
    material['canonicalDialogue'] = context['scene']['content'].get('spokenContent', [])
    if context.get('dialogueCoverage'):
        material['dialogueCoverage'] = context['dialogueCoverage']
    if context.get('dpdSnapshot'):
        material['upstreamPerformance'] = validated_upstream_performance(context['dpdSnapshot'], spec)
    return {**material, 'fingerprint': sha256_canonical(material)}


def verify_frozen(raw: dict[str, Any]) -> CinematicShotSpec:
    if raw.get('state') != 'CINEMATIC_DIRECTION_FROZEN' or raw.get('fingerprint') != sha256_canonical({k:v for k,v in raw.items() if k!='fingerprint'}):
        raise ValueError('CINEMATIC_DIRECTION_NOT_FROZEN_OR_CHANGED')
    spec = CinematicShotSpec.model_validate(raw['spec'])
    if spec.source_sound_intent and list(spec.source_sound_intent.canonical_dialogue_bindings) != [d.spoken_content_id for d in spec.dialogue]:
        raise ValueError('SOURCE_SOUND_CANONICAL_BINDINGS_CHANGED')
    if 'canonicalDialogue' in raw:
        canonical = {line['id']: line for line in raw['canonicalDialogue']}
        for d in spec.dialogue:
            original = canonical.get(d.spoken_content_id, {})
            if (original.get('text'), original.get('speakerKey')) != (d.text,d.speaker_key):
                raise ValueError('FROZEN_CANONICAL_DIALOGUE_CHANGED')
    if any(d.canonical_interval is not None or d.text_range is not None for d in spec.dialogue):
        from drama_plugin.visual.dialogue_coverage import coverage_intervals
        coverage = raw.get('dialogueCoverage')
        if not coverage:
            raise ValueError('SHARED_DIALOGUE_COVERAGE_EVIDENCE_REQUIRED')
        snapshots = [{'id':s['id'],'scene_id':s['scene_id'], 'content':{'plannedDurationMs':s['duration'],
                      'spokenContentBindings':s['bindings']}} for s in coverage['shots']]
        intervals = coverage_intervals({'scene':{'id':spec.scene_id,'content':{'spokenContent':raw['canonicalDialogue']}},
                                        'sceneShots':snapshots},coverage).get(spec.shot_id,{})
        for d in spec.dialogue:
            expected = intervals.get(d.spoken_content_id)
            if expected is None or any(getattr(d,k) != v for k,v in expected.items()):
                raise ValueError('FROZEN_DIALOGUE_COVERAGE_CHANGED')
    if review_direction(spec)['status'] == 'FAIL':
        raise ValueError('Frozen direction has major execution findings')
    if raw.get('upstreamPerformance'):
        validated_upstream_performance(raw['upstreamPerformance'], spec)
    vr = raw['visualResolution']; resolved = resolve_visual_bible(vr['base'], vr['overrides'])
    if (vr != {k:v for k,v in resolved.items() if k!='layers'} or
            resolved['fingerprint'] != spec.visual_bible_fingerprint or resolved['effective'] != dump_contract(spec.visual_bible)):
        raise ValueError('Frozen visual inheritance changed')
    return spec


def selection_handoff(raw: dict[str, Any]) -> dict[str, Any]:
    spec = verify_frozen(raw)
    return {'creative_schema': 'cinematic-shot-v1', 'cinematic_direction': raw,
            'execution_requirements': dump_contract(spec.execution_requirements),
            'reference_requirements': [dump_contract(r) for r in spec.reference_requirements],
            'motion_prompt': execution_brief(spec)}


def validate_selection_handoff(material: dict[str, Any], *, work_id: str, scene_id: str,
                               shot_id: str, duration: float) -> CinematicShotSpec | None:
    if 'cinematic_direction' not in material and material.get('creative_schema') != 'cinematic-shot-v1':
        return None  # Existing adopted/archived routes remain byte-compatible.
    expected = selection_handoff(material['cinematic_direction'])
    if any(material.get(k) != v for k, v in expected.items()):
        raise ValueError('CINEMATIC_SELECTION_PROJECTION_CHANGED')
    if any(k in material for k in ('visual_performance_brief', 'visualPerformanceBrief', 'legacy_motion_prompt', 'performance_prompt')):
        raise ValueError('DOUBLE_VISUAL_EXECUTION_PROJECTION')
    spec = verify_frozen(material['cinematic_direction'])
    if (spec.work_id,spec.scene_id,spec.shot_id,spec.duration_seconds) != (work_id,scene_id,shot_id,duration):
        raise ValueError('CINEMATIC_SELECTION_SCOPE_OR_DURATION_CHANGED')
    return spec
