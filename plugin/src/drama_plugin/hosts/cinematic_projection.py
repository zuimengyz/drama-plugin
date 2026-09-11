"""Small semantic projection at the Host adapter boundary, not another director.

Explicit prose sections consume the frozen beats verbatim. The manifest covers
every present leaf; critical omissions fail before request sealing. No truncation.
"""
from __future__ import annotations
from typing import Any
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.visual.cinematic import verify_frozen


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
    enabled = sound != 'SILENT'
    if (intent.native_audio_policy == 'REQUIRED' and not enabled or
            intent.native_audio_policy == 'DISABLED' and enabled):
        raise ValueError('SOURCE_SOUND_ROUTE_CONFLICT')
    if not enabled and intent.canonical_dialogue_bindings:
        raise ValueError('CANONICAL_DIALOGUE_CANNOT_BE_SILENCED')
    return enabled


def project(r: Any, c: Any, inspected: dict[str, Any]) -> dict[str, Any]:
    spec = verify_frozen(r.frozen_creative['cinematic_direction'])
    raw = dump_contract(spec); all_fields = leaves(raw)
    manifest: dict[str, Any] = {}; sections: list[str] = []
    prompt_field = 'prompt' if inspected['class_type'].startswith('Flux') else 'model.prompt'
    duration_field = 'duration' if inspected['class_type'].startswith('Flux') else 'model.duration'
    def mark(path: str, destination: str, field: str, reason: str, critical: bool = True) -> None:
        matched = {k:v for k,v in all_fields.items() if k == path or k.startswith(path+'.') or k.startswith(path+'[')}
        for key,value in matched.items():
            manifest[key] = {'canonical_field': key, 'required_for_execution': critical and value is not None,
                'destination': destination if value is not None else 'NOT_APPLICABLE', 'provider_field': field,
                'status': 'RETAINED' if critical else 'NOT_REQUIRED_FOR_EXECUTION', 'reason': reason,
                'source_hash': sha256_canonical(value)}
    def emit(title: str, path: str, value: Any) -> None:
        if value is not None and value != []:
            sections.append(title + ': ' + prose(value))
        mark(path, 'PROMPT', prompt_field, f'完整保留于 {title}；不生成第二套时间轴')
    for key in ('schemaVersion','workId','sceneId','shotId','creativeRevision','sourceFingerprint','visualBibleFingerprint','narrativeIntent',
                'anchorOmissionReason','secondaryMotionOmissionReason'):
        mark(key, 'UPSTREAM_LOCK', 'frozen', '来源/创作推理由冻结合同约束', False)
    emit('GLOBAL VISUAL / WORLD', 'visualBible', raw['visualBible'])
    emit('OPENING STATE', 'openingState', raw['openingState'])
    emit('BEHAVIOR ANCHOR', 'behaviorAnchor', raw['behaviorAnchor'])
    if spec.behavior_anchor:
        mark('behaviorAnchor.continuityBasis','UPSTREAM_LOCK','frozen','历史/连续性依据，无需作为独立动作',False)
    for key in ('objective','interactionTarget','intendedBelief','concealed','emotionalArc'):
        emit('PERFORMANCE '+key, 'performance.'+key, raw['performance'][key])
    for i,beat in enumerate(spec.performance.beats):
        data = raw['performance']['beats'][i]
        # Formatting only: no quantization, retiming or invented beat.
        emit(f'TIMELINE [{beat.start:g}–{beat.end:g}s] {beat.kind}', f'performance.beats[{i}]',
             {k:v for k,v in data.items() if k not in ('start','end','kind')})
    for i,d in enumerate(spec.dialogue):
        text = d.text if d.text_range is None else d.text[d.text_range[0]:d.text_range[1]]
        sections.append(f'AUDIO / DIALOGUE [{d.start:g}–{d.end:g}s] {d.coverage_intent} '
                        f'{d.speaker_key} → {d.target}: "{text}"；{d.delivery}；after: {d.after_line}')
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
        emit(title,key,raw[key])
    for i,_ in enumerate(spec.stability_contract):
        mark(f'stabilityContract[{i}].reason','UPSTREAM_LOCK','frozen','约束依据；允许/禁止行为已投影',False)
    audio = source_audio(spec,r.sound)
    audio_field = 'generate_audio' if inspected['class_type'].startswith('Flux') else 'model.generate_audio'
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
                sections.append(f'EXPLICIT REFERENCE SUBSTITUTE {duty.role}: {duty.equivalent_text}')
            else:
                sections.append(f'REFERENCE DUTY {duty.provider_slot}: {duty.role} / {duty.subject} / {duty.purpose}; '
                                '仅承担所列职责，不默认复制原图姿态或构图。')
        else:
            mark(f'referenceRequirements[{i}]','NOT_APPLICABLE','none','PREFERRED未提供；不是已履行',False)
            if ref.necessity == 'REQUIRED':
                raise ValueError('REQUIRED_REFERENCE_UNFULFILLED')
    if set(manifest) != set(all_fields):
        raise ValueError('UNPROJECTED_CANONICAL_FIELDS:' + ','.join(set(all_fields)-set(manifest)))
    result = {'schema':'provider-semantic-projection-v1','prompt':'\n\n'.join(sections),
              # Map iteration order is not a creative instruction. Formal JSON
              # storage may reorder object keys; the audit manifest must not drift.
              'generate_audio':audio,'manifest':[manifest[k] for k in sorted(manifest)]}
    validate_projection(result)
    return {**result,'fingerprint':sha256_canonical(result)}


def validate_projection(projection: dict[str, Any]) -> None:
    for item in projection['manifest']:
        if item['required_for_execution'] and item['destination'] not in {'PROMPT','PARAMETER','REFERENCE','UPSTREAM_LOCK'}:
            raise ValueError('EXECUTION_CRITICAL_UNSUPPORTED:' + item['canonical_field'])
