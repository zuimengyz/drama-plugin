"""Small source-pinned final projection edits, never a moderation word filter."""
from copy import deepcopy
from typing import Any
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.visual.payload_scope import review_text


def normalize(prompt: str, task: str, plan: dict[str, Any] | None = None, *, audio: bool = True) -> tuple[str, dict[str, Any] | None]:
    if plan is None:
        return prompt, None
    if (plan.get('task') != task or plan.get('source_prompt_fingerprint') != fp(prompt)
            or not isinstance(plan.get('rules'), list) or not plan['rules']):
        raise ValueError('VISUAL_NORMALIZATION_SOURCE_CHANGED')
    review_text(prompt, task, audio=audio)
    lines = prompt.split('\n')
    changed = set()
    for rule in plan['rules']:
        if (not isinstance(rule, dict) or set(rule) != {'before', 'after', 'kind', 'reason', 'basis'}
                or rule['kind'] not in {'POSITIVE_EQUIVALENT', 'CURRENT_VISIBLE_ONLY'}
                or not all(isinstance(rule[k], str) and rule[k].strip() for k in ('before', 'after', 'reason'))
                or '\n' in rule['after'] or '\n' in rule['before']
                or rule['before'] == rule['after'] or rule['before'] in changed
                or lines.count(rule['before']) != 1):
            raise ValueError('VISUAL_NORMALIZATION_INVALID_RULE')
        if not isinstance(rule['basis'], list) or not rule['basis'] or any(
                not isinstance(text, str) or not text or text not in prompt for text in rule['basis']):
            raise ValueError('VISUAL_NORMALIZATION_BASIS_REQUIRED')
        if rule['kind'] == 'CURRENT_VISIBLE_ONLY' and task not in {'IMAGE', 'FIRST_FRAME', 'KEY_FRAME'}:
            raise ValueError('VISUAL_NORMALIZATION_CANNOT_REMOVE_CLIP_ACTION')
        review_text(rule['after'], task, audio=audio)
        lines[lines.index(rule['before'])] = rule['after']
        changed.add(rule['before'])
    result = '\n'.join(lines)
    review_text(result, task, audio=audio)
    return result, {'schema': 'positive-visual-projection-v1', 'task': task,
        'source_prompt_fingerprint': fp(prompt), 'prompt_fingerprint': fp(result),
        'rules': deepcopy(plan['rules']), 'moderationOutcome': 'NOT_TESTED',
        'onSubsequentModeration': 'PROVIDER_MODERATION_INCOMPATIBILITY'}
