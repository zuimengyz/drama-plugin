"""Small semantic projection at the Host adapter boundary, not another director.

Explicit prose sections consume the frozen beats verbatim. The manifest covers
every present leaf; critical omissions fail before request sealing. No truncation.
"""
from __future__ import annotations
from typing import Any
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.visual.cinematic import verify_frozen
from drama_plugin.hosts.prompt_budget import compact_prose, prompt_limit, budget_prompt, PROVENANCE
from drama_plugin.visual.payload_scope import review_compiled


INTERNAL_FIELDS = set(PROVENANCE) | {'reason', 'sourceRefs', 'sourceMap', 'approvedBy', 'scenePurpose',
    'audienceInterpretation', 'misreadRisk', 'futureContinuity', 'musicPlanning', 'grammarFingerprint',
    'nativeAudioPolicy', 'canonicalDialogueBindings', 'generatedMusic', 'intentionalSilence'}


def executable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: executable(v) for k, v in value.items() if k not in INTERNAL_FIELDS}
    if isinstance(value, list):
        return [executable(v) for v in value]
    return value


def leaves(value: Any, path: str = '') -> dict[str, Any]:
    if isinstance(value, dict):
        return {p:v for k,x in value.items() for p,v in leaves(x, f'{path}.{k}' if path else k).items()}
    if isinstance(value, (list, tuple)):
        return {p:v for i,x in enumerate(value) for p,v in leaves(x, f'{path}[{i}]').items()}
    return {path:value}


def prose(value: Any) -> str:
    if isinstance(value, dict):
        return '；'.join(f'{k}: {prose(v)}' for k,v in value.items() if v is not None and v != [])
    if isinstance(value, (list, tuple)):
        return '；'.join(prose(v) for v in value)
    return str(value)


def source_audio(spec: Any, sound: str) -> bool:
    intent = spec.source_sound_intent
    if intent is None:
        raise ValueError('SOURCE_SOUND_INTENT_REQUIRED_FOR_NEW_REQUEST')
    from drama_plugin.vocal_direction import require_vocal_capability
    for delivery in (*intent.vocal_performances, *(d.voice_performance.vocal_delivery for d in spec.dialogue if d.voice_performance and d.voice_performance.vocal_delivery)):
        require_vocal_capability(delivery, supported_modes={'SPOKEN'})
    enabled = sound != 'SILENT'
    if (intent.native_audio_policy == 'REQUIRED' and not enabled or
            intent.native_audio_policy == 'DISABLED' and enabled):
        raise ValueError('SOURCE_SOUND_ROUTE_CONFLICT')
    if not enabled and intent.canonical_dialogue_bindings:
        raise ValueError('CANONICAL_DIALOGUE_CANNOT_BE_SILENCED')
    return enabled


def project(r: Any, c: Any, inspected: dict[str, Any]) -> dict[str, Any]:
    spec = verify_frozen(r.frozen_creative['cinematic_direction'])
    audio = source_audio(spec, r.sound)
    authority = getattr(r, 'authority_context', None)
    if authority is not None:
        from drama_plugin.hosts.specialized_asset import validate_authority_context
        validate_authority_context(authority, r.frozen_creative['cinematic_direction'])
        if authority['workId'] != spec.work_id:
            raise ValueError('MOVIE_VISUAL_AUTHORITY_MISMATCH')
    raw = dump_contract(spec); all_fields = leaves(raw)
    manifest: dict[str, Any] = {}; sections: list[str] = []; compact_sections: list[str] = []
    missing_references: list[str] = []
    from drama_plugin.hosts.comfy_video import NODES
    semantics = NODES[inspected['class_type']]
    prompt_field = semantics['prompt']
    duration_field = semantics['duration']
    def append(full: str, compact: str) -> None:
        sections.append(full)
        compact_sections.append(compact)
    def mark(path: str, destination: str, field: str, reason: str, critical: bool = True) -> None:
        matched = {k:v for k,v in all_fields.items() if k == path or k.startswith(path+'.') or k.startswith(path+'[')}
        for key,value in matched.items():
            manifest[key] = {'canonical_field': key, 'required_for_execution': critical and value is not None,
                'destination': destination if value is not None else 'NOT_APPLICABLE', 'provider_field': field,
                'status': 'RETAINED' if critical else 'NOT_REQUIRED_FOR_EXECUTION', 'reason': reason,
                'source_hash': sha256_canonical(value)}
    def emit(title: str, path: str, value: Any) -> None:
        if value is not None and value != []:
            titles = {'GLOBAL VISUAL / WORLD': '视觉', 'OPENING STATE': '开场', 'BEHAVIOR ANCHOR': '行为锚',
                      'ACTOR DIRECTION / SHARED PERFORMANCE INTENT': '表演', 'CAMERA': '摄影',
                      'ACTIVE LIGHT': '光', 'SECONDARY MOTION': '次动作', 'ENVIRONMENT INTERACTION': '环境互动',
                      'STABILITY / DO NOT CHANGE': '连续约束', 'SOURCE SOUND': '声音', 'ENDING STATE': '结束',
                      'PERFORMANCE objective': '目的', 'PERFORMANCE interactionTarget': '对象',
                      'PERFORMANCE intendedBelief': '希望对方相信', 'PERFORMANCE concealed': '隐藏', 'PERFORMANCE emotionalArc': '情绪'}
            append(title + ': ' + prose(executable(value)), titles.get(title, title) + ':' +
                   compact_prose(executable(value), performance=path == 'performance.directorPerformance'))
        mark(path, 'PROMPT', prompt_field, f'完整保留于 {title}；不生成第二套时间轴')
        for field in list(manifest):
            if field.startswith(path + '.') and field.rsplit('.', 1)[-1] in INTERNAL_FIELDS:
                mark(field, 'UPSTREAM_LOCK', 'frozen', 'Scope: internal evidence, not executable text', False)
    for key in ('schemaVersion','workId','sceneId','shotId','creativeRevision','sourceFingerprint','visualBibleFingerprint','narrativeIntent',
                'anchorOmissionReason','secondaryMotionOmissionReason'):
        mark(key, 'UPSTREAM_LOCK', 'frozen', '来源/创作推理由冻结合同约束', False)
    if spec.expression_direction is not None:
        from drama_plugin.expression import project_action_expression
        expression = project_action_expression([dump_contract(x) for x in spec.performance.beats], spec.expression_direction)
        append('ROUTE-OWNED EXPRESSION / ONLY ' + spec.expression_direction.core.identity + ': ' + prose(expression),
               '仅角色' + spec.expression_direction.core.identity + ':' + compact_prose(expression))
        mark('expressionDirection', 'UPSTREAM_LOCK', 'frozen', '冻结的角色路线与导演幅度约束；只投影该角色，不改变剧情事件')
        mark('expressionDirection.director', 'PROMPT', prompt_field, '导演、动作和摄影原文投影；不生成新动作')
        mark('expressionDirection.profile.design.actionSignature', 'PROMPT', prompt_field, '角色专属动作语言')
    emit('GLOBAL VISUAL / WORLD', 'visualBible', raw['visualBible'])
    emit('OPENING STATE', 'openingState', raw['openingState'])
    emit('BEHAVIOR ANCHOR', 'behaviorAnchor', raw['behaviorAnchor'])
    if spec.behavior_anchor:
        mark('behaviorAnchor.continuityBasis','UPSTREAM_LOCK','frozen','历史/连续性依据，无需作为独立动作',False)
    for key in ('objective','interactionTarget','intendedBelief','concealed','emotionalArc'):
        if key in {'intendedBelief', 'concealed'}:
            mark('performance.' + key, 'UPSTREAM_LOCK', 'frozen', 'Internal performance interpretation', False)
            continue
        emit('PERFORMANCE '+key, 'performance.'+key, raw['performance'][key])
    if spec.performance.director_performance:
        emit('ACTOR DIRECTION / SHARED PERFORMANCE INTENT', 'performance.directorPerformance', raw['performance']['directorPerformance'])
    for i,beat in enumerate(spec.performance.beats):
        data = raw['performance']['beats'][i]
        # Formatting only: no quantization, retiming or invented beat.
        emit(f'TIMELINE [{beat.start:g}–{beat.end:g}s] {beat.kind}', f'performance.beats[{i}]',
             {k:v for k,v in data.items() if k not in ('start','end','kind')})
    for i,d in enumerate(spec.dialogue):
        text = d.text if d.text_range is None else d.text[d.text_range[0]:d.text_range[1]]
        dialogue = (f'[{d.start:g}–{d.end:g}s] {d.coverage_intent} '
                    f'{d.speaker_key} → {d.target}: "{text}"；{d.delivery}；after: {d.after_line}')
        append('AUDIO / DIALOGUE ' + dialogue, '对白' + dialogue)
        if d.voice_performance:
            append('NATIVE VOICE DIRECTION / SAME PERFORMANCE: ' + prose(executable(dump_contract(d.voice_performance))),
                   '声音表演:' + compact_prose(executable(dump_contract(d.voice_performance)), performance=True))
        mark(f'dialogue[{i}]','PROMPT',prompt_field,'仅说当前覆盖片段；整句正文保留为 Canon，不重复整句')
        if d.text_range is not None:
            manifest[f'dialogue[{i}].text']['executed_text_range'] = list(d.text_range)
            manifest[f'dialogue[{i}].text']['executed_text_hash'] = sha256_canonical(text)
            manifest[f'dialogue[{i}].text']['full_sentence_lock'] = 'canonicalDialogue'
        for key in ('spokenContentId','canonicalInterval','textRange'):
            mark(f'dialogue[{i}].{key}','UPSTREAM_LOCK','canonicalDialogue','绑定与切片依据',False)
    for title,key in [('CAMERA','cinematography'),('ACTIVE LIGHT','lighting'),('SECONDARY MOTION','secondaryMotion'),
                      ('ENVIRONMENT INTERACTION','environmentInteraction'),('STABILITY / DO NOT CHANGE','stabilityContract'),
                      ('SOURCE SOUND','sourceSoundIntent'),('ENDING STATE','endingState')]:
        if key == 'sourceSoundIntent' and not audio:
            mark(key, 'UPSTREAM_LOCK', 'frozen', 'Silent route: no provider sound execution', False)
            continue
        emit(title,key,raw[key])
    for i,_ in enumerate(spec.stability_contract):
        mark(f'stabilityContract[{i}].reason','UPSTREAM_LOCK','frozen','约束依据；允许/禁止行为已投影',False)
    audio_field = semantics.get('audio', 'generate_audio' if inspected['class_type'].startswith('Flux') else 'model.generate_audio')
    mark('sourceSoundIntent.nativeAudioPolicy','PARAMETER' if audio_field in c.parameters else 'UPSTREAM_LOCK',
         audio_field if audio_field in c.parameters else 'native AV node contract', '源声音意图与路线声音共同决定；固定原生AV节点只能启用')
    mark('sourceSoundIntent.canonicalDialogueBindings','UPSTREAM_LOCK','canonicalDialogue','对白绑定锁；实际台词见 AUDIO / DIALOGUE')
    mark('durationSeconds','PARAMETER',duration_field,'使用正式 Shot 时长')
    mark('executionRequirements','UPSTREAM_LOCK','qualification','V2-06能力要求，非另一个Prompt')
    mark('executionRequirements.durationSeconds','PARAMETER',duration_field,'路线时长一致性')
    for i,ref in enumerate(spec.reference_requirements):
        duty = next((d for d in r.reference_duties if (d.role,d.subject)==(ref.role,ref.subject)),None)
        if duty:
            destination = 'PROMPT' if duty.status == 'EQUIVALENT' else 'REFERENCE'
            mark(f'referenceRequirements[{i}]',destination,duty.provider_slot,duty.evidence)
            if duty.status == 'EQUIVALENT':
                append(f'EXPLICIT REFERENCE SUBSTITUTE {duty.role}: {duty.equivalent_text}',
                       f'参考替代{duty.role}:{duty.equivalent_text}')
            else:
                append(f'REFERENCE DUTY {duty.provider_slot}: {duty.role} / {duty.subject} / {duty.purpose}; '
                       '仅承担所列职责，不默认复制原图姿态或构图。',
                       f'参考{duty.provider_slot}:{duty.role}/{duty.subject}/{duty.purpose}；仅此职责，不默认复制姿态构图。')
        else:
            mark(f'referenceRequirements[{i}]','NOT_APPLICABLE','none','PREFERRED未提供；不是已履行',False)
            if ref.necessity == 'REQUIRED':
                missing_references.append(f'{ref.role}/{ref.subject}/{ref.purpose}')
                mark(f'referenceRequirements[{i}]','UNSUPPORTED','none','必需参考尚未履行')
    for path in list(manifest):
        if manifest[path]['destination'] == 'PROMPT' and any(part.split('[')[0] in INTERNAL_FIELDS for part in path.split('.')):
            mark(path, 'UPSTREAM_LOCK', 'frozen', 'Scope: internal evidence retained upstream', False)
    if set(manifest) != set(all_fields):
        raise ValueError('UNPROJECTED_CANONICAL_FIELDS:' + ','.join(set(all_fields)-set(manifest)))
    if authority is not None:
        from drama_plugin.hosts.specialized_asset import authority_semantics
        asset_text = authority_semantics(authority)
        append('ASSET CONTINUITY:\n' + asset_text, '资产连续:\n' + asset_text)
    # Unified scope review precedes the existing prompt-budget gate.
    full_prompt = review_compiled('\n\n'.join(sections), 'VIDEO')
    compact_prompt = review_compiled('\n'.join(compact_sections), 'VIDEO')
    result: dict[str, Any] = {'schema':'provider-semantic-projection-v1','prompt':full_prompt,
              # Map iteration order is not a creative instruction. Formal JSON
              # storage may reorder object keys; the audit manifest must not drift.
              'generate_audio':audio,'manifest':[manifest[k] for k in sorted(manifest)]}
    if authority is not None:
        result['authority_context_fingerprint'] = authority['fingerprint']
    capability = getattr(c, 'capability', {})
    limit, source = prompt_limit(capability, semantics, getattr(c, 'variant', ''))
    # All reference/wrapper text is already included, so reserve exactly zero.
    result['prompt'], budget = budget_prompt(result['prompt'], compact_prompt,
        model=getattr(c, 'model', semantics['model']), limit=limit, source=source)
    result['prompt_budget'] = budget
    from drama_plugin.visual.positive_projection import normalize
    result['prompt'], normalization = normalize(result['prompt'], 'VIDEO', getattr(r, 'prompt_normalization', None), audio=audio)
    if normalization is not None:
        result['normalization'] = {**normalization, 'pre_normalization_budget': budget}
        # Positive wording can grow: retain the final provider hard-limit gate.
        result['prompt'], result['prompt_budget'] = budget_prompt(result['prompt'], result['prompt'],
            model=getattr(c, 'model', semantics['model']), limit=limit, source=source)
    result['scope_review'] = {'gate': 'VISUAL_PROVIDER_SCOPE_REVIEW', 'task': 'VIDEO',
                              'prompt_fingerprint': sha256_canonical(result['prompt'])}
    if budget['status'] == 'COMPRESSIBLE':
        for item in result['manifest']:
            path = item['canonical_field']
            if (path.startswith('performance.directorPerformance.') or '.voicePerformance.' in path) and path.rsplit('.', 1)[-1] in PROVENANCE:
                item.update(destination='UPSTREAM_LOCK', provider_field='frozen', required_for_execution=False,
                            reason='审计标识保留在完整意图与封存中，不发送给模型')
    if missing_references:
        error = ValueError('REQUIRED_REFERENCE_UNFULFILLED')
        # Diagnostic only. Never return a successful projection for missing media.
        error.projection = result  # type: ignore[attr-defined]
        raise error
    validate_projection(result)
    return {**result,'fingerprint':sha256_canonical(result)}


def validate_projection(projection: dict[str, Any]) -> None:
    budget = projection.get('prompt_budget')
    if budget:
        if (budget['finalCharacters'] != len(projection['prompt']) or budget['status'] not in {'FIT', 'COMPRESSIBLE'}
                or (budget['hardMaxPromptCharacters'] is not None
                    and len(projection['prompt']) + budget['reservedPromptCharacters'] > budget['hardMaxPromptCharacters'])):
            raise ValueError('PROVIDER_PROMPT_BUDGET_INVALID')
    for item in projection['manifest']:
        if item['required_for_execution'] and item['destination'] not in {'PROMPT','PARAMETER','REFERENCE','UPSTREAM_LOCK'}:
            raise ValueError('EXECUTION_CRITICAL_UNSUPPORTED:' + item['canonical_field'])
