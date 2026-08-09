from __future__ import annotations

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
