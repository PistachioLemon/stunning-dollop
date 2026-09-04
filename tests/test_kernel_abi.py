from dataclasses import replace

from nova.truck_node.kernel_abi import (
    KernelABIEvidence,
    KernelABIStatus,
    KernelModuleEvidence,
    evaluate_kernel_abi,
)


def module():
    return KernelModuleEvidence("can_driver", "1.0", "1.0", True, True)


def good():
    return KernelABIEvidence(
        expected_kernel_abi="6.x-requant", observed_kernel_abi="6.x-requant", modules=(module(),),
        can_obd_verified=True, gps_serial_verified=True, camera_verified=True,
        bluetooth_verified=True, usb_nvme_verified=True, router_network_verified=True,
        mqtt_mtls_verified=True, gpio_spi_i2c_verified=True, offline_reboot_verified=True,
        slot_update_verified=True, rollback_verified=True, kernel_log_clean=True,
    )


def test_complete_kernel_abi_evidence_is_compatible():
    assert evaluate_kernel_abi(good()).status is KernelABIStatus.COMPATIBLE


def test_abi_change_blocks_promotion():
    result = evaluate_kernel_abi(replace(good(), observed_kernel_abi="6.x-new"))
    assert result.status is KernelABIStatus.KERNEL_ABI_INCOMPATIBLE
    assert "kernel_abi_mismatch" in result.failures


def test_module_must_load_match_and_drive_hardware():
    bad = KernelModuleEvidence("can_driver", "1.0", "2.0", False, False)
    result = evaluate_kernel_abi(replace(good(), modules=(bad,)))
    assert result.status is KernelABIStatus.KERNEL_ABI_INCOMPATIBLE
    assert "module_not_loaded:can_driver" in result.failures
    assert "module_version_mismatch:can_driver" in result.failures
    assert "module_hardware_failure:can_driver" in result.failures


def test_hardware_and_rollback_regression_blocks_promotion():
    result = evaluate_kernel_abi(replace(good(), can_obd_verified=False, rollback_verified=False))
    assert result.status is KernelABIStatus.KERNEL_ABI_INCOMPATIBLE
    assert {"can_obd", "rollback"}.issubset(result.failures)


def test_missing_abi_is_unknown():
    result = evaluate_kernel_abi(replace(good(), observed_kernel_abi=""))
    assert result.status is KernelABIStatus.UNKNOWN
