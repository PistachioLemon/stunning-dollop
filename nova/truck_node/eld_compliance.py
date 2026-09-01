from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class ELDStatus(str, Enum):
    REGISTERED = "REGISTERED"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"
    REGISTRY_STALE = "REGISTRY_STALE"


class ELDEnforcementPhase(str, Enum):
    REGISTERED = "REGISTERED"
    REVOKED_GRACE = "REVOKED_GRACE"
    REPLACEMENT_DUE_SOON = "REPLACEMENT_DUE_SOON"
    ENFORCEMENT_ACTIVE = "ENFORCEMENT_ACTIVE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ELDDevice:
    provider: str
    model: str
    identifier: str


@dataclass(frozen=True)
class ELDRegistryRecord:
    provider: str
    model: str
    identifier: str
    registered: bool
    revoked: bool = False
    effective_at: datetime | None = None
    replacement_deadline: datetime | None = None


@dataclass(frozen=True)
class ELDRegistrySnapshot:
    fetched_at: datetime
    verified: bool
    records: tuple[ELDRegistryRecord, ...]
    conflicts: tuple[str, ...] = ()


@dataclass(frozen=True)
class ELDComplianceResult:
    status: ELDStatus
    snapshot_age_seconds: float
    replacement_deadline: datetime | None = None
    reason: str | None = None
    enforcement_phase: ELDEnforcementPhase = ELDEnforcementPhase.UNKNOWN
    days_until_deadline: float | None = None
    dispatch_ready: bool | None = None


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def evaluate_eld_compliance(
    device: ELDDevice,
    snapshot: ELDRegistrySnapshot,
    *,
    now: datetime | None = None,
    max_snapshot_age_seconds: int = 7 * 24 * 3600,
    due_soon_days: int = 30,
) -> ELDComplianceResult:
    """Evaluate a locally cached, already-authenticated ELD registry snapshot.

    This is a deterministic warning/failover and fleet-readiness gate only. It
    does not certify an ELD, modify HOS records, or substitute RequantAi for a
    registered ELD. An LLM must not override the result.
    """
    current = _aware(now or datetime.now(timezone.utc))
    fetched = _aware(snapshot.fetched_at)
    age = max(0.0, (current - fetched).total_seconds())

    if not snapshot.verified:
        return ELDComplianceResult(ELDStatus.UNKNOWN, age, reason="registry_unverified")
    if snapshot.conflicts:
        return ELDComplianceResult(ELDStatus.UNKNOWN, age, reason="official_source_conflict")
    if age > max_snapshot_age_seconds:
        return ELDComplianceResult(ELDStatus.REGISTRY_STALE, age, reason="registry_stale")

    matches = [
        record
        for record in snapshot.records
        if record.provider.casefold() == device.provider.casefold()
        and record.model.casefold() == device.model.casefold()
        and record.identifier.casefold() == device.identifier.casefold()
    ]
    if len(matches) != 1:
        return ELDComplianceResult(ELDStatus.UNKNOWN, age, reason="device_not_uniquely_matched")

    record = matches[0]
    if record.revoked:
        if record.replacement_deadline is None:
            return ELDComplianceResult(
                ELDStatus.REVOKED,
                age,
                reason="revoked_without_deadline",
                enforcement_phase=ELDEnforcementPhase.UNKNOWN,
                dispatch_ready=None,
            )

        deadline = _aware(record.replacement_deadline)
        seconds_remaining = (deadline - current).total_seconds()
        days_remaining = seconds_remaining / 86400.0
        if seconds_remaining <= 0:
            phase = ELDEnforcementPhase.ENFORCEMENT_ACTIVE
            dispatch_ready = False
        elif days_remaining <= due_soon_days:
            phase = ELDEnforcementPhase.REPLACEMENT_DUE_SOON
            dispatch_ready = True
        else:
            phase = ELDEnforcementPhase.REVOKED_GRACE
            dispatch_ready = True

        return ELDComplianceResult(
            ELDStatus.REVOKED,
            age,
            replacement_deadline=deadline,
            reason="device_revoked",
            enforcement_phase=phase,
            days_until_deadline=days_remaining,
            dispatch_ready=dispatch_ready,
        )
    if record.registered:
        return ELDComplianceResult(
            ELDStatus.REGISTERED,
            age,
            enforcement_phase=ELDEnforcementPhase.REGISTERED,
            dispatch_ready=True,
        )
    return ELDComplianceResult(ELDStatus.UNKNOWN, age, reason="device_status_unknown")
