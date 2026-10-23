"""Provider hard-limit measurement only; never shorten or rewrite a Prompt."""
from __future__ import annotations

import re
from typing import Any


class PromptBudgetExceeded(ValueError):
    def __init__(self, budget: dict[str, Any]):
        self.budget = budget
        super().__init__('PROVIDER_PROMPT_BUDGET_EXCEEDED: '
                         f"model={budget['model']} original_length={budget['originalCharacters']} "
                         f"final_length={budget['finalCharacters']} "
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


PROVENANCE = {'directorIntentFingerprint', 'grammarFingerprint', 'beatId', 'spokenContentId'}


def check_prompt_limit(prompt: str, *, model: str, limit: int | None,
                       source: str, reserved: int = 0) -> tuple[str, dict[str, Any]]:
    if type(reserved) is not int or reserved < 0:
        raise ValueError('INVALID_PROMPT_RESERVATION')
    effective = None if limit is None else limit - reserved
    fits = effective is None or len(prompt) <= effective
    budget = {'model': model, 'maxPromptCharacters': limit, 'hardMaxPromptCharacters': limit,
              'reservedPromptCharacters': reserved, 'effectivePromptBudget': effective,
              'limitSource': source, 'status': 'FIT' if fits else 'EXCEEDED',
              'originalCharacters': len(prompt), 'finalCharacters': len(prompt), 'rule': 'unchanged'}
    if not fits:
        raise PromptBudgetExceeded(budget)
    return prompt, budget
