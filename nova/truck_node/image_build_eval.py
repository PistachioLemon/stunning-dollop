from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImageBuildEvidence:
    builder: str
    version: str
    architecture: str
    build_a_manifest_sha256: str
    build_b_manifest_sha256: str
    build_a_sbom_sha256: str
    build_b_sbom_sha256: str
    unintended_passwordless_sudo: bool
    slot_a_booted: bool
    slot_b_booted: bool
    corrupted_slot_recovered: bool
    encrypted_storage_verified: bool
    offline_boot_verified: bool
    router_network_verified: bool
    bluetooth_verified: bool
    can_obd_verified: bool
    gps_verified: bool
    mqtt_mtls_verified: bool
    camera_verified: bool
    usb_nvme_verified: bool
    interrupted_update_recovered: bool
    artifact_trust_rejection_verified: bool


@dataclass(frozen=True)
class ImageBuildResult:
    passed: bool
    failures: tuple[str, ...]


def evaluate_rpi_image_gen_27(evidence: ImageBuildEvidence) -> ImageBuildResult:
    failures: list[str] = []
    if evidence.builder != "rpi-image-gen" or evidence.version != "2.7.0":
        failures.append("wrong_builder_or_version")
    if evidence.architecture.lower() not in {"arm64", "aarch64"}:
        failures.append("wrong_architecture")
    if evidence.build_a_manifest_sha256 != evidence.build_b_manifest_sha256:
        failures.append("package_manifest_not_reproducible")
    if evidence.build_a_sbom_sha256 != evidence.build_b_sbom_sha256:
        failures.append("sbom_not_reproducible")
    if evidence.unintended_passwordless_sudo:
        failures.append("unintended_passwordless_sudo")

    required = {
        "slot_a_boot": evidence.slot_a_booted,
        "slot_b_boot": evidence.slot_b_booted,
        "corrupted_slot_recovery": evidence.corrupted_slot_recovered,
        "encrypted_storage": evidence.encrypted_storage_verified,
        "offline_boot": evidence.offline_boot_verified,
        "travel_router_network": evidence.router_network_verified,
        "bluetooth": evidence.bluetooth_verified,
        "can_obd": evidence.can_obd_verified,
        "gps": evidence.gps_verified,
        "mqtt_mtls": evidence.mqtt_mtls_verified,
        "camera": evidence.camera_verified,
        "usb_nvme": evidence.usb_nvme_verified,
        "interrupted_update_recovery": evidence.interrupted_update_recovered,
        "artifact_trust_rejection": evidence.artifact_trust_rejection_verified,
    }
    failures.extend(name for name, passed in required.items() if not passed)
    return ImageBuildResult(not failures, tuple(failures))
