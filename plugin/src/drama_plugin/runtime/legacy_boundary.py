"""The small, explicit door between Target runs and retained Legacy data."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from contextvars import ContextVar, Token


class LegacyOrigin(str, Enum):
    TARGET = "TARGET"
    HISTORICAL = "HISTORICAL"


class LegacyPurpose(str, Enum):
    READ_ONLY = "READ_ONLY"
    RECOVERY = "RECOVERY"


class LegacyAccessDecision(str, Enum):
    ALLOW_READ_ONLY = "ALLOW_READ_ONLY"
    ALLOW_RECOVERY = "ALLOW_RECOVERY"
    REJECT_TARGET_FALLBACK = "REJECT_TARGET_FALLBACK"


@dataclass(frozen=True)
class LegacyAccessRequest:
    origin: LegacyOrigin
    work_id: str
    run_id: str
    capability: str
    purpose: LegacyPurpose
    historical_attempt_id: str | None = None


class LegacyBoundary:
    """Only a named Canon read or an evidenced historical attempt may cross."""

    lifecycle = "TARGET"
    migration_reads = frozenset({"work.get_work"})
    recovery_entries = frozenset({"work.production_stage.recover"})

    def decide(self, request: LegacyAccessRequest) -> LegacyAccessDecision:
        if not request.work_id or not request.run_id:
            return LegacyAccessDecision.REJECT_TARGET_FALLBACK
        if (request.origin == LegacyOrigin.TARGET and request.purpose == LegacyPurpose.READ_ONLY
                and request.capability in self.migration_reads
                and request.historical_attempt_id is None):
            return LegacyAccessDecision.ALLOW_READ_ONLY
        if (request.origin == LegacyOrigin.HISTORICAL and request.purpose == LegacyPurpose.RECOVERY
                and request.capability in self.recovery_entries
                and request.historical_attempt_id == request.run_id):
            return LegacyAccessDecision.ALLOW_RECOVERY
        return LegacyAccessDecision.REJECT_TARGET_FALLBACK


@dataclass
class LegacyRecoveryGrant:
    work_id: str
    attempt_id: str
    stage_id: str
    active: bool = True


_active_recovery: ContextVar[LegacyRecoveryGrant | None] = ContextVar("drama_legacy_recovery", default=None)


def activate_recovery(grant: LegacyRecoveryGrant) -> Token[LegacyRecoveryGrant | None]:
    return _active_recovery.set(grant)


def deactivate_recovery(token: Token[LegacyRecoveryGrant | None]) -> None:
    grant = _active_recovery.get()
    if grant is not None:
        grant.active = False
    _active_recovery.reset(token)


def require_legacy_recovery(work_id: str, stage: object) -> None:
    """Old mutation/dispatch is usable only within a verified recovery session."""
    grant = _active_recovery.get()
    if (grant is None or not grant.active or grant.work_id != work_id or not isinstance(stage, dict)
            or not isinstance(stage.get("stage"), dict)
            or stage["stage"].get("id") != grant.stage_id
            or not any(isinstance(a, dict) and a.get("attempt_id") == grant.attempt_id
                       for a in stage.get("attempts", ()))):
        raise ValueError("LEGACY_GUARD: explicit historical recovery required")
