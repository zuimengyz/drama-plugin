"""Align known author aliases on new writes, never on historical reads."""
from copy import deepcopy

from drama_plugin.creative_engine.contracts import DesignBody

LIGHTING_ALIASES = {'motivatedSources': 'sources', 'negativeConstraints': 'constraints'}


def align_lighting_fields(design: DesignBody) -> DesignBody:
    if design.domain != 'LIGHTING' or not LIGHTING_ALIASES.keys() & design.facts.keys():
        return design
    facts = deepcopy(design.facts)
    for alias, canonical in LIGHTING_ALIASES.items():
        if alias not in facts:
            continue
        if canonical in facts and facts[canonical] != facts[alias]:
            raise ValueError(f'LIGHTING_FIELD_CONFLICT: {alias}/{canonical}')
        facts[canonical] = facts.pop(alias)
    return DesignBody(domain=design.domain, facts=facts)

