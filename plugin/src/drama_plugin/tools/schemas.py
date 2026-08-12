from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any, TypeAlias

from pydantic import TypeAdapter

from drama_plugin.exceptions import ContractValidationError

JsonSchema: TypeAlias = dict[str, Any]


def schema_for(annotation: Any) -> JsonSchema:
    """Build a stable JSON Schema from an explicitly declared domain type."""

    return TypeAdapter(annotation).json_schema(by_alias=True)


def object_schema(
    *,
    required: Mapping[str, Any] | None = None,
    optional: Mapping[str, Any] | None = None,
    defaults: Mapping[str, Any] | None = None,
) -> JsonSchema:
    """Build a callable-compatible object schema and hoist nested Pydantic definitions."""

    required_fields = required or {}
    optional_fields = optional or {}
    definitions: JsonSchema = {}
    properties: JsonSchema = {}

    for name, annotation in (*required_fields.items(), *optional_fields.items()):
        field_schema = deepcopy(schema_for(annotation))
        nested_definitions = field_schema.pop("$defs", {})
        for definition_name, definition in nested_definitions.items():
            existing = definitions.get(definition_name)
            if existing is not None and existing != definition:
                raise ContractValidationError(
                    f"Conflicting JSON Schema definition: {definition_name}"
                )
            definitions[definition_name] = definition
        properties[name] = field_schema

    for name, value in (defaults or {}).items():
        if name not in optional_fields:
            raise ContractValidationError(
                f"Default value requires an optional field: {name}"
            )
        properties[name]["default"] = deepcopy(value)

    result: JsonSchema = {
        "type": "object",
        "properties": properties,
        "required": list(required_fields),
        "additionalProperties": False,
    }
    if definitions:
        result["$defs"] = definitions
    return result
