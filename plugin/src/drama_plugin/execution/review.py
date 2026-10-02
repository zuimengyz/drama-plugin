"""Independent creative reviewer port. Reviewers return observations, never STOP."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from drama_plugin.execution.contracts import (
    ExecutionOperation, MediaIdentity, ReviewObservation,
)
from drama_plugin.runtime.contracts import RunMode


@dataclass(frozen=True)
class ReviewResponse:
    outcome: Literal["PASS", "REVISE"]
    observations: tuple[ReviewObservation, ...] = ()


class CreativeReviewer(Protocol):
    @property
    def identity(self) -> str: ...
    @property
    def policy_version(self) -> str: ...
    async def review(self, operation: ExecutionOperation, media: MediaIdentity,
                     *, mode: RunMode) -> ReviewResponse: ...


class MockReviewer:
    identity = "deterministic-offline-reviewer"
    policy_version = "offline-candidate-review-v1"

    def __init__(self, outcome: Literal["PASS", "REVISE"] = "PASS"):
        self.outcome = outcome

    async def review(self, operation: ExecutionOperation, media: MediaIdentity,
                     *, mode: RunMode) -> ReviewResponse:
        observations = () if self.outcome == "PASS" else (ReviewObservation(
            code="PERFORMANCE_REVISION_REQUIRED", owner="dramatic-performance-direction",
            finding="Recorded fixture reports a performance mismatch.",
            required_revision="E2 creative owner must revise the pinned performance direction."),)
        return ReviewResponse(self.outcome, observations)
