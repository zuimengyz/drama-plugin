"""A model generator translates approved IR; it cannot fill creative gaps."""
from typing import Any, Protocol
from drama_plugin.contracts.visual_prompt import VisualPromptIR


class ModelPromptGenerator(Protocol):
    family: str
    version: str
    supported_modes: tuple[str, ...]

    def generate(self, ir: VisualPromptIR, rows: list[dict[str, Any]], *,
                 context: dict[str, Any], hard_limit: int) -> dict[str, Any]: ...
