from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class KernelABIStatus(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    KERNEL_ABI_INCOMPATIBLE = "KERNEL_ABI_INCOMPATIBLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class KernelModuleEvidence:
    name: str
    expected_version: str
    observed_version: str
    loaded: bool
    hardware_functional: bool


@dataclass(frozen=True)
class KernelABIEvidence:
    expected_kernel_abi: str
    observed_kernel_abi: str
    modules: tuple[KernelModuleEvidence, ...]
    can_obd_verified: bool
    gps_serial_verified: bool
    camera_verified: bool
    bluetooth_verified: bool
    usb_nvme_verified: bool
    router_network_verified: bool
    mqtt_mtls_verified: bool
    gpio_spi_i2c_verified: bool
    offline_reboot_verified: bool
    slot_update_verified: bool
    rollback_verified: bool
    kernel_log_clean: bool


@dataclass(frozen=True)
class KernelABIResult:
    status: KernelABIStatus
    failures: tuple[str, ...]


def evaluate_kernel_abi(evidence: KernelABIEvidence) -> KernelABIResult:
    failures: list[str] = []
    if not evidence.expected_kernel_abi.strip() or not evidence.observed_kernel_abi.strip():
        return KernelABIResult(KernelABIStatus.UNKNOWN, ("missing_kernel_abi",))
    if evidence.expected_kernel_abi != evidence.observed_kernel_abi:
        failures.append("kernel_abi_mismatch")

    for module in evidence.modules:
        if not module.loaded:
            failures.append(f"module_not_loaded:{module.name}")
        if module.expected_version and module.expected_version != module.observed_version:
            failures.append(f"module_version_mismatch:{module.name}")
        if not module.hardware_functional:
            failures.append(f"module_hardware_failure:{module.name}")

    required = {
        "can_obd": evidence.can_obd_verified,
        "gps_serial": evidence.gps_serial_verified,
        "camera": evidence.camera_verified,
        "bluetooth": evidence.bluetooth_verified,
        "usb_nvme": evidence.usb_nvme_verified,
        "travel_router_network": evidence.router_network_verified,
        "mqtt_mtls": evidence.mqtt_mtls_verified,
        "gpio_spi_i2c": evidence.gpio_spi_i2c_verified,
        "offline_reboot": evidence.offline_reboot_verified,
        "slot_update": evidence.slot_update_verified,
        "rollback": evidence.rollback_verified,
        "kernel_log_clean": evidence.kernel_log_clean,
    }
    failures.extend(name for name, passed in required.items() if not passed)
    status = KernelABIStatus.COMPATIBLE if not failures else KernelABIStatus.KERNEL_ABI_INCOMPATIBLE
    return KernelABIResult(status, tuple(failures))
