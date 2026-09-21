"""Medium-neutral inputs, independent of provider-facing language and control axes."""
from typing import Literal
from pydantic import Field
from .base import ContractModel

FactDomain = Literal['form', 'skin', 'groom', 'materials', 'shape', 'rendering', 'constraint']


class CharacterPromptFact(ContractModel):
    id: str = Field(min_length=1)
    domain: FactDomain
    text: str = Field(min_length=1)
    sources: tuple[str, ...] = ()
    derived_summary: bool = False


class StructuredCharacterFacts(ContractModel):
    """Costume facts and composition intent use materials/rendering respectively.

    Text describes observable choices, not photography, shaders or rendering.
    Medium declarations are validated at the shared compiler boundary.
    """
    facts: tuple[CharacterPromptFact, ...]
