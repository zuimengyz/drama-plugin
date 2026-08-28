from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ContractModel(BaseModel):
    """Base for transport-neutral domain contracts with JSON-friendly aliases."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        frozen=False,
    )


def dump_contract(
    contract: BaseModel,
    *,
    exclude: set[str] | None = None,
) -> dict[str, Any]:
    """Return the canonical cross-boundary JSON representation for a contract."""

    return contract.model_dump(mode="json", by_alias=True, exclude=exclude)


def canonical_json(value: Any) -> str:
    """Serialize a contract value deterministically for material fingerprints."""

    if isinstance(value, BaseModel):
        value = dump_contract(value)
    elif isinstance(value, Enum):
        value = value.value
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_canonical(value: Any) -> str:
    """Hash the deterministic JSON representation of a contract value."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
