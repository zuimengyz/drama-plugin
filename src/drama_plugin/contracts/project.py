from __future__ import annotations

from drama_plugin.contracts.base import ContractModel


class Project(ContractModel):
    id: str
    name: str
    description: str | None = None


class Story(ContractModel):
    id: str
    project_id: str
    title: str
    premise: str


class Episode(ContractModel):
    id: str
    story_id: str
    number: int
    title: str
    summary: str


class Scene(ContractModel):
    id: str
    episode_id: str
    number: int
    heading: str
    location_id: str
    character_ids: list[str] = []
    summary: str


class Shot(ContractModel):
    id: str
    scene_id: str
    number: int
    description: str
    character_ids: list[str] = []
    duration_seconds: float | None = None


class Character(ContractModel):
    id: str
    name: str
    role: str | None = None
    description: str | None = None


class Location(ContractModel):
    id: str
    name: str
    period: str | None = None
    description: str | None = None


class Prop(ContractModel):
    id: str
    name: str
    description: str | None = None
