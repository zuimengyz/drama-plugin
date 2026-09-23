"""Task-scoped visual execution boundary. No moderation keyword substitutions."""
from __future__ import annotations
import re
from typing import Any
from drama_plugin.contracts.base import sha256_canonical

STATIC = {'identity', 'costume', 'prop', 'environment', 'pose', 'blocking', 'composition',
          'lighting', 'material', 'medium', 'visual_continuity', 'reference', 'visible_text'}
SCOPES = {'IMAGE': STATIC, 'FIRST_FRAME': STATIC, 'KEY_FRAME': STATIC,
          'VIDEO': STATIC | {'action', 'performance', 'camera_motion', 'clip_continuity',
                              'opening_state', 'ending_state', 'rhythm', 'dialogue', 'sound'}}
# Structural control-plane labels, not words describing violence or conflict.
CONTROL = re.compile(r'(?i)(director constraints\s*:|audience[_ ]interpretation\s*[:=]|scene[_ ]purpose\s*[:=]|'
    r'misread[_ ]risk\s*[:=]|approval[_ ]metadata\s*[:=]|budget[_ ]credits\s*[:=]|'
    r'"?(?:assetBible|sourceMap|compilationFingerprint|approvedBy)"?\s*[:=])')
FUTURE = re.compile(r'(?i)(future[_ ](?:scene|action|continuity)|later scene|后续S\d+|未来场景|后续镜头|下一场)')
NONVISUAL = re.compile(r'(?i)(?:^|[\n;；])\s*(?:sound|dialogue|narration|music direction|声音|旁白|音乐)\s*[:=：]')


def review_text(text: str, task: str, *, authority_texts: tuple[str, ...] = (), audio: bool = True) -> None:
    if task not in SCOPES:
        raise ValueError('VISUAL_PROVIDER_PAYLOAD_SCOPE_VIOLATION:task')
    if any(value and value in text for value in authority_texts):
        raise ValueError('VISUAL_PROVIDER_PAYLOAD_CONTAINS_AUTHORITY_CONTEXT')
    if CONTROL.search(text) or FUTURE.search(text) or ((task != 'VIDEO' or not audio) and NONVISUAL.search(text)):
        raise ValueError('VISUAL_PROVIDER_PAYLOAD_SCOPE_VIOLATION:unscoped source text')
    blocks = [line.strip() for line in text.splitlines() if line.strip()]
    if len(blocks) != len(set(blocks)):
        raise ValueError('VISUAL_PROVIDER_PAYLOAD_DUPLICATED_BLOCK')


def compile_payload(task: str, context: dict[str, Any], *, audio: bool = False) -> dict[str, Any]:
    """Read only context.execution[task]; everything else remains internal.

    Blocks require a task-owned semantic field and source path; selection is
    replayable against the full original. Mixed legacy strings fail closed.
    """
    blocks = context.get('execution', {}).get(task)
    if task not in SCOPES or not isinstance(blocks, list) or not blocks:
        raise ValueError('VISUAL_PROVIDER_PAYLOAD_SCOPE_VIOLATION:execution required')
    output = []; mapping = []; seen = set()
    for block in blocks:
        if not {'field', 'source'} <= set(block) or set(block) - {'field', 'source', 'subject'} or block['field'] not in SCOPES[task]:
            raise ValueError('VISUAL_PROVIDER_PAYLOAD_SCOPE_VIOLATION:field')
        if block['field'] in {'sound', 'dialogue'} and not audio:
            raise ValueError('VISUAL_PROVIDER_PAYLOAD_SCOPE_VIOLATION:audio unsupported')
        forbidden = {'authority', 'sourceMap', 'approval', 'approvalMetadata', 'budget', 'cost', 'quote', 'rights',
                     'director', 'directorIntent', 'directorConstraints', 'screenplay', 'literarySource', 'sceneSummary', 'scenePurpose',
                     'audienceInterpretation', 'futureContinuity', 'futureAction', 'musicPlanning', 'narration'}
        if task != 'VIDEO':
            forbidden |= {'sound', 'dialogue', 'narration', 'music', 'endingState', 'beats'}
        normalize = lambda key: str(key).replace('_', '').lower()
        denied = {normalize(key) for key in forbidden}
        paths = [block['source']] + ([block['subject']] if 'subject' in block else [])
        if any(not isinstance(path, list) or not path or any(not isinstance(p, (str, int)) for p in path) for path in paths):
            raise ValueError('VISUAL_PROVIDER_PAYLOAD_SCOPE_VIOLATION:source path')
        if any(normalize(part) in denied for path in paths for part in path):
            raise ValueError('VISUAL_PROVIDER_PAYLOAD_SCOPE_VIOLATION:source')
        value: Any = context['sources']
        try:
            for part in block['source']:
                value = value[part]
        except (KeyError, IndexError, TypeError):
            raise ValueError('VISUAL_PROVIDER_PAYLOAD_SCOPE_VIOLATION:source path') from None
        if not isinstance(value, str) or not value.strip():
            raise ValueError('VISUAL_PROVIDER_PAYLOAD_SCOPE_VIOLATION:non-text source')
        review_text(value, task)
        if 'subject' in block:
            subject: Any = context['sources']
            for part in block['subject']:
                subject = subject[part]
            if not isinstance(subject, str):
                raise ValueError('VISUAL_PROVIDER_PAYLOAD_SCOPE_VIOLATION:subject')
            review_text(subject, task)
            rendered = subject + ': ' + value
        else:
            rendered = value
        normalized = ' '.join(rendered.split())
        mapping.append({**block, 'source_hash': sha256_canonical(value), 'deduplicated': normalized in seen})
        if normalized not in seen:
            output.append(rendered); seen.add(normalized)
    prompt = '\n'.join(output)
    authority = context.get('authority') or {}
    authority_texts = ((authority['prompt'],) if 'prompt' in authority else ())
    authority_texts += tuple(row['receipt']['prompt'] for row in context.get('authority_context', {}).get('assets', []))
    review_text(prompt, task, authority_texts=authority_texts)
    return {'prompt': prompt, 'scope_review': {'gate': 'VISUAL_PROVIDER_SCOPE_REVIEW', 'task': task,
        'context_fingerprint': sha256_canonical(context), 'prompt_fingerprint': sha256_canonical(prompt),
        'source_map': mapping}}


def review_compiled(prompt: str, task: str, *, audio: bool = True) -> str:
    """For existing typed compilers: deduplicate exact blocks, then fail closed."""
    prompt = '\n'.join(dict.fromkeys(prompt.splitlines()))
    review_text(prompt, task, audio=audio)
    return prompt


ASSET_FIELDS = {'CHARACTER': {'age_presentation', 'face', 'body', 'body_proportion', 'hair', 'facial_hair', 'surface_state'},
                'COSTUME': {'garment_structure', 'material', 'wear'},
                'SCENE': {'architecture', 'spatial_hierarchy', 'surface_material', 'lived_in_state', 'period_visible_details'}}


def asset_payload(receipt: dict[str, Any]) -> dict[str, Any]:
    asset = next(a for a in receipt['assetBible']['assets'] if a['id'] == receipt['assetId'])
    sources = {k: v['text'] for k, v in asset['decisions'].items() if k in ASSET_FIELDS[asset['kind']]}
    sources['medium'] = 'LIVE_ACTION' if receipt['medium'] == 'LIVE_ACTION' else 'CINEMATIC_CG'
    medium = receipt.get('legacyMediumCompilation', {}).get('visualMediumIntent')
    if medium:
        from drama_plugin.visual_medium import compile_visual_medium
        from drama_plugin.contracts.visual_medium import VisualMediumIntent
        grammar = compile_visual_medium(VisualMediumIntent.model_validate(medium))
        sources['medium'] = grammar['rendering']
    context = {'sources': sources, 'authority': receipt, 'execution': {'IMAGE': [
        {'field': 'medium' if key == 'medium' else 'identity' if asset['kind'] == 'CHARACTER' else 'costume' if asset['kind'] == 'COSTUME' else 'environment',
         'source': [key]} for key in sources]}}
    return compile_payload('IMAGE', context)
