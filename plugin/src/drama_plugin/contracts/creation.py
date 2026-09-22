from __future__ import annotations

from typing import Any

from pydantic import Field, NonNegativeInt, model_validator

from drama_plugin.contracts.base import ContractModel


class Work(ContractModel):
    id: str
    title: str
    description: str | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    version: int = Field(default=1, gt=0)


    @model_validator(mode='after')
    def source_boundary(self) -> Work:
        from drama_plugin.creative_source import validate_work_content
        validate_work_content(self.content)
        return self


class Script(ContractModel):
    id: str
    work_id: str
    title: str
    content: dict[str, Any] = Field(default_factory=dict)


class Episode(ContractModel):
    id: str
    script_id: str
    episode_no: NonNegativeInt
    title: str
    content: dict[str, Any] = Field(default_factory=dict)


class Scene(ContractModel):
    id: str
    episode_id: str
    order: NonNegativeInt
    title: str
    location: str | None = None
    content: dict[str, Any] = Field(default_factory=dict)


class Shot(ContractModel):
    id: str
    scene_id: str
    shot_no: str
    title: str | None = None
    shot_type: str | None = None
    content: dict[str, Any] = Field(default_factory=dict)
