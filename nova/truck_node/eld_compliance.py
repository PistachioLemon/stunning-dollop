from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class ELDStatus(str, Enum):
    REGISTERED = "REGISTERED"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"
    REGISTRY_STALE = "REGISTRY_STALE"


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


@dataclass(frozen=True)
class ELDComplianceResult:
    status: ELDStatus
    snapshot_age_seconds: float
    replacement_deadline: datetime | None = None
    reason: str | None = None


def evaluate_eld_compliance(
    device: ELDDevice,
    snapshot: ELDRegistrySnapshot,
    *,
    now: datetime | None = None,
    max_snapshot_age_seconds: int = 7 * 24 * 3600,
) -> ELDComplianceResult:
    """Evaluate a locally cached, already-authenticated ELD registry snapshot.

    This is a warning/failover gate only. It does not certify an ELD, modify HOS
    records, or substitute RequantAi for a registered ELD.
    """
    current = now or datetime.now(timezone.utc)
    fetched = snapshot.fetched_at
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    age = max(0.0, (current - fetched).total_seconds())

    if not snapshot.verified:
        return ELDComplianceResult(ELDStatus.UNKNOWN, age, reason="registry_unverified")
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
        return ELDComplianceResult(
            ELDStatus.REVOKED,
            age,
            replacement_deadline=record.replacement_deadline,
            reason="device_revoked",
        )
    if record.registered:
        return ELDComplianceResult(ELDStatus.REGISTERED, age)
    return ELDComplianceResult(ELDStatus.UNKNOWN, age, reason="device_status_unknown")
