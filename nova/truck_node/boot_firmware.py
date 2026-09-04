from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BootFirmwareStatus(str, Enum):
    ACCEPTABLE = "ACCEPTABLE"
    FIRMWARE_POLICY_VIOLATION = "FIRMWARE_POLICY_VIOLATION"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class BootFirmwareEvidence:
    board_revision: str
    installed_version: str
    minimum_version: str
    eeprom_sha256: str
    expected_boot_order: str
    observed_boot_order: str
    secure_boot_expected: bool
    secure_boot_enabled: bool
    firmware_key_lock_expected: bool
    firmware_key_lock_enabled: bool
    ab_update_verified: bool
    rollback_verified: bool
    corrupted_candidate_recovered: bool
    nvme_boot_verified: bool
    missing_nvme_recovery_verified: bool
    offline_recovery_verified: bool
    identity_persisted: bool
    truck_io_started_after_recovery: bool


@dataclass(frozen=True)
class BootFirmwareResult:
    status: BootFirmwareStatus
    failures: tuple[str, ...]


def evaluate_boot_firmware(evidence: BootFirmwareEvidence) -> BootFirmwareResult:
    if not evidence.board_revision.strip() or not evidence.installed_version.strip() or not evidence.minimum_version.strip():
        return BootFirmwareResult(BootFirmwareStatus.UNKNOWN, ("missing_firmware_identity",))
    digest = evidence.eeprom_sha256.lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        return BootFirmwareResult(BootFirmwareStatus.UNKNOWN, ("invalid_eeprom_digest",))

    policy: list[str] = []
    if evidence.installed_version < evidence.minimum_version:
        policy.append("below_minimum_firmware")
    if evidence.observed_boot_order != evidence.expected_boot_order:
        policy.append("boot_order_changed")
    if evidence.secure_boot_expected and not evidence.secure_boot_enabled:
        policy.append("secure_boot_weakened")
    if evidence.firmware_key_lock_expected and not evidence.firmware_key_lock_enabled:
        policy.append("firmware_key_lock_weakened")
    if policy:
        return BootFirmwareResult(BootFirmwareStatus.FIRMWARE_POLICY_VIOLATION, tuple(policy))

    recovery = {
        "ab_update": evidence.ab_update_verified,
        "rollback": evidence.rollback_verified,
        "corrupted_candidate_recovery": evidence.corrupted_candidate_recovered,
        "nvme_boot": evidence.nvme_boot_verified,
        "missing_nvme_recovery": evidence.missing_nvme_recovery_verified,
        "offline_recovery": evidence.offline_recovery_verified,
        "identity_persistence": evidence.identity_persisted,
        "truck_io_after_recovery": evidence.truck_io_started_after_recovery,
    }
    failures = tuple(name for name, passed in recovery.items() if not passed)
    if failures:
        return BootFirmwareResult(BootFirmwareStatus.RECOVERY_FAILED, failures)
    return BootFirmwareResult(BootFirmwareStatus.ACCEPTABLE, ())
