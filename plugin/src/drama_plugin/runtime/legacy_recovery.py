"""Explicit, read-only handoff for an already recorded Legacy attempt."""
from __future__ import annotations

from typing import Any
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from drama_plugin.providers.base import MemoryProvider
from drama_plugin.runtime.legacy_boundary import (
    LegacyAccessDecision, LegacyAccessRequest, LegacyBoundary, LegacyOrigin, LegacyPurpose,
    LegacyRecoveryGrant, activate_recovery, deactivate_recovery,
)
from drama_plugin.visual.audit_view import project


class LegacyRecovery:
    lifecycle = "LEGACY_RECOVERY_ONLY"

    def __init__(self, memory: MemoryProvider, boundary: LegacyBoundary):
        self._memory = memory
        self._boundary = boundary

    async def resume_legacy_run(self, *, work_id: str, attempt_id: str) -> dict[str, Any]:
        """Locate the old attempt and decode its audit state; never dispatch it."""
        decision = self._boundary.decide(LegacyAccessRequest(
            origin=LegacyOrigin.HISTORICAL, work_id=work_id, run_id=attempt_id,
            capability="work.production_stage.recover", purpose=LegacyPurpose.RECOVERY,
            historical_attempt_id=attempt_id))
        if decision != LegacyAccessDecision.ALLOW_RECOVERY:
            raise ValueError("LEGACY_GUARD")
        work = await self._memory.get_work(work_id)
        route = work.content.get("productionRoute")
        stage = work.content.get("productionStage")
        if not isinstance(route, dict) or not isinstance(stage, dict):
            raise ValueError("LEGACY_RECOVERY_REQUIRES_EXISTING_STAGE")
        if (route.get("work_id") != work.id
                or stage.get("production_route", {}).get("work_id") != work.id
                or stage.get("stage", {}).get("id") != route.get("stage_id")):
            raise ValueError("LEGACY_RECOVERY_SCOPE_MISMATCH")
        matches = [a for a in stage.get("attempts", ()) if a.get("attempt_id") == attempt_id]
        if len(matches) != 1:
            raise ValueError("LEGACY_RECOVERY_REQUIRES_EXISTING_ATTEMPT")
        audit = project(work.model_dump(mode="json"))
        return {"workId": work.id, "workVersion": work.version,
                "routeId": route["route_id"], "stageId": route["stage_id"],
                "attemptId": attempt_id, "attemptStatus": matches[0]["status"],
                "auditSourceFingerprint": audit["sourceFingerprint"],
                "submissionAllowed": False}

    @asynccontextmanager
    async def session(self, *, work_id: str, attempt_id: str) -> AsyncIterator[dict[str, Any]]:
        """Bind old operations to one verified attempt for this async call scope."""
        snapshot = await self.resume_legacy_run(work_id=work_id, attempt_id=attempt_id)
        token = activate_recovery(LegacyRecoveryGrant(work_id, attempt_id, snapshot["stageId"]))
        try:
            yield snapshot
        finally:
            deactivate_recovery(token)
