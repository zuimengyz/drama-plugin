from __future__ import annotations

from enum import StrEnum
from typing import Any

from drama_plugin.contracts.base import ContractModel


class GenerationTarget(StrEnum):
    SHOT_IMAGE = "SHOT_IMAGE"
    SHOT_VIDEO = "SHOT_VIDEO"
    ASSET_IMAGE = "ASSET_IMAGE"


class GenerationStatus(StrEnum):
    DRAFT = "DRAFT"
    COMPILED = "COMPILED"
    SUBMITTED = "SUBMITTED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class GenerationPlan(ContractModel):
    id: str
    generation_target: GenerationTarget
    resource_id: str
    workflow_code: str | None = None
    parameters: dict[str, Any] = {}
    compiled_payload: dict[str, Any] | None = None


class GenerationState(ContractModel):
    plan_id: str | None = None
    status: GenerationStatus = GenerationStatus.DRAFT
    progress: float = 0.0
    message: str | None = None


class GenerationResult(ContractModel):
    plan_id: str
    status: GenerationStatus
    media_ids: list[str] = []
    metadata: dict[str, Any] = {}
