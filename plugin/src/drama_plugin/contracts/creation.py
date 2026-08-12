from __future__ import annotations

from typing import Any

from pydantic import Field

from drama_plugin.contracts.base import ContractModel


class Work(ContractModel):
    id: str
    title: str
    description: str | None = None
    content: dict[str, Any] = Field(default_factory=dict)


class Script(ContractModel):
    id: str
    work_id: str
    title: str
    content: dict[str, Any] = Field(default_factory=dict)


class Episode(ContractModel):
    id: str
    script_id: str
    number: int
    title: str
    content: dict[str, Any] = Field(default_factory=dict)


class Scene(ContractModel):
    id: str
    episode_id: str
    number: int
    heading: str
    content: dict[str, Any] = Field(default_factory=dict)


class Shot(ContractModel):
    id: str
    scene_id: str
    number: int
    description: str
    duration_seconds: float | None = None
    content: dict[str, Any] = Field(default_factory=dict)
