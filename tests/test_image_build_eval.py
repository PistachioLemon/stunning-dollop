from dataclasses import replace

from nova.truck_node.image_build_eval import ImageBuildEvidence, evaluate_rpi_image_gen_27

DIGEST = "a" * 64
SBOM = "b" * 64


def good_evidence():
    return ImageBuildEvidence(
        builder="rpi-image-gen", version="2.7.0", architecture="arm64",
        build_a_manifest_sha256=DIGEST, build_b_manifest_sha256=DIGEST,
        build_a_sbom_sha256=SBOM, build_b_sbom_sha256=SBOM,
        unintended_passwordless_sudo=False,
        slot_a_booted=True, slot_b_booted=True, corrupted_slot_recovered=True,
        encrypted_storage_verified=True, offline_boot_verified=True,
        router_network_verified=True, bluetooth_verified=True, can_obd_verified=True,
        gps_verified=True, mqtt_mtls_verified=True, camera_verified=True,
        usb_nvme_verified=True, interrupted_update_recovered=True,
        artifact_trust_rejection_verified=True,
    )


def test_complete_rpi_image_gen_27_evidence_passes():
    result = evaluate_rpi_image_gen_27(good_evidence())
    assert result.passed is True
    assert result.failures == ()


def test_reproducibility_mismatch_blocks_promotion():
    result = evaluate_rpi_image_gen_27(replace(good_evidence(), build_b_manifest_sha256="c" * 64))
    assert result.passed is False
    assert "package_manifest_not_reproducible" in result.failures


def test_passwordless_sudo_blocks_promotion():
    result = evaluate_rpi_image_gen_27(replace(good_evidence(), unintended_passwordless_sudo=True))
    assert result.passed is False
    assert "unintended_passwordless_sudo" in result.failures


def test_missing_hardware_or_recovery_gate_blocks_promotion():
    result = evaluate_rpi_image_gen_27(
        replace(good_evidence(), can_obd_verified=False, interrupted_update_recovered=False)
    )
    assert result.passed is False
    assert {"can_obd", "interrupted_update_recovery"}.issubset(result.failures)


def test_wrong_builder_version_is_rejected():
    result = evaluate_rpi_image_gen_27(replace(good_evidence(), version="2.6.0"))
    assert result.passed is False
    assert "wrong_builder_or_version" in result.failures
