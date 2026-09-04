from dataclasses import replace

from nova.truck_node.boot_firmware import BootFirmwareEvidence, BootFirmwareStatus, evaluate_boot_firmware


def good():
    return BootFirmwareEvidence(
        board_revision="pi5-rev", installed_version="2026-08-12", minimum_version="2026-01-01",
        eeprom_sha256="a" * 64, expected_boot_order="NVME>SD>RECOVERY", observed_boot_order="NVME>SD>RECOVERY",
        secure_boot_expected=True, secure_boot_enabled=True,
        firmware_key_lock_expected=True, firmware_key_lock_enabled=True,
        ab_update_verified=True, rollback_verified=True, corrupted_candidate_recovered=True,
        nvme_boot_verified=True, missing_nvme_recovery_verified=True, offline_recovery_verified=True,
        identity_persisted=True, truck_io_started_after_recovery=True,
    )


def test_complete_firmware_evidence_is_acceptable():
    assert evaluate_boot_firmware(good()).status is BootFirmwareStatus.ACCEPTABLE


def test_minimum_version_and_boot_order_are_enforced():
    result = evaluate_boot_firmware(replace(good(), installed_version="2025-01-01", observed_boot_order="SD>NVME"))
    assert result.status is BootFirmwareStatus.FIRMWARE_POLICY_VIOLATION
    assert {"below_minimum_firmware", "boot_order_changed"}.issubset(result.failures)


def test_security_controls_cannot_be_weakened():
    result = evaluate_boot_firmware(replace(good(), secure_boot_enabled=False, firmware_key_lock_enabled=False))
    assert result.status is BootFirmwareStatus.FIRMWARE_POLICY_VIOLATION
    assert {"secure_boot_weakened", "firmware_key_lock_weakened"}.issubset(result.failures)


def test_failed_recovery_blocks_candidate():
    result = evaluate_boot_firmware(replace(good(), rollback_verified=False, corrupted_candidate_recovered=False))
    assert result.status is BootFirmwareStatus.RECOVERY_FAILED
    assert {"rollback", "corrupted_candidate_recovery"}.issubset(result.failures)


def test_invalid_digest_is_unknown():
    assert evaluate_boot_firmware(replace(good(), eeprom_sha256="bad")).status is BootFirmwareStatus.UNKNOWN
