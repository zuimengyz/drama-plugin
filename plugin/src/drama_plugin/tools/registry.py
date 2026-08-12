from __future__ import annotations

import builtins
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from drama_plugin.exceptions import ContractValidationError, DuplicateToolError, ToolNotFoundError

ToolHandler = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class ToolDefinition:
    code: str
    domain: str
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    handler: ToolHandler = field(repr=False, compare=False)

    def describe(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "domain": self.domain,
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.code in self._tools:
            raise DuplicateToolError(f"Tool already registered: {tool.code}")
        if tool.input_schema.get("type") != "object" or not isinstance(
            tool.input_schema.get("required"), list
        ):
            raise ContractValidationError(
                f"Tool {tool.code} must declare an object input schema with required"
            )
        if not tool.output_schema:
            raise ContractValidationError(
                f"Tool {tool.code} must declare an output schema"
            )
        self._tools[tool.code] = tool

    def get(self, code: str) -> ToolDefinition:
        try:
            return self._tools[code]
        except KeyError as exc:
            raise ToolNotFoundError(f"Tool not found: {code}") from exc

    def list(self, domain: str | None = None) -> list[ToolDefinition]:
        tools = list(self._tools.values())
        if domain is not None:
            tools = [tool for tool in tools if tool.domain == domain]
        return sorted(tools, key=lambda tool: tool.code)

    def exists(self, code: str) -> bool:
        return code in self._tools

    def describe(
        self, code: str | None = None
    ) -> dict[str, Any] | builtins.list[dict[str, Any]]:
        if code is not None:
            return self.get(code).describe()
        return [tool.describe() for tool in self.list()]

    async def invoke(self, code: str, **arguments: Any) -> Any:
        return await self.get(code).handler(**arguments)


def tool(
    code: str,
    description: str,
    handler: ToolHandler,
    *,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
) -> ToolDefinition:
    domain, name = code.split(".", 1)
    return ToolDefinition(
        code=code,
        domain=domain,
        name=name,
        description=description,
        handler=handler,
        input_schema=input_schema,
        output_schema=output_schema,
    )
