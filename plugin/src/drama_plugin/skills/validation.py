from __future__ import annotations

from drama_plugin.exceptions import SkillLoadError
from drama_plugin.skills.registry import SkillRegistry
from drama_plugin.tools.registry import ToolRegistry


class SkillToolReferenceValidator:
    """Validate Skill tool-code references after both registries are loaded."""

    @staticmethod
    def validate(skills: SkillRegistry, tools: ToolRegistry) -> None:
        for skill in skills.list():
            references = (*skill.tools.preferred, *skill.tools.allowed)
            for tool_code in references:
                if not tools.exists(tool_code):
                    raise SkillLoadError(
                        f"Skill {skill.code} references missing tool {tool_code}"
                    )
                registered = tools.get(tool_code)
                code_domain, separator, _ = tool_code.partition(".")
                if not separator or registered.domain != code_domain:
                    raise SkillLoadError(
                        f"Skill {skill.code} references tool {tool_code} with domain "
                        f"{registered.domain}"
                    )
