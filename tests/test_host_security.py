from nova.truck_node.host_security import (
    HostImageEvidence,
    HostSecurityStatus,
    SecurityAdvisory,
    evaluate_host_image,
)

DIGEST = "a" * 64


def image(**overrides):
    values = dict(os_version="pi-os-production", kernel_version="6.x", image_sha256=DIGEST, boot_slot="B")
    values.update(overrides)
    return HostImageEvidence(**values)


def test_network_kernel_advisory_requires_security_update():
    advisory = SecurityAdvisory("USN-example", "high", True, True)
    result = evaluate_host_image(image(advisories=(advisory,)))
    assert result.status is HostSecurityStatus.SECURITY_UPDATE_REQUIRED
    assert "advisory:USN-example" in result.reasons


def test_unaffected_advisory_does_not_force_update():
    advisory = SecurityAdvisory("USN-other", "high", False, True)
    result = evaluate_host_image(image(advisories=(advisory,)))
    assert result.status is HostSecurityStatus.CURRENT


def test_candidate_requires_artifact_hardware_and_rollback_gates():
    partial = evaluate_host_image(image(artifact_trust_passed=True, hardware_regression_passed=True))
    assert partial.status is HostSecurityStatus.CURRENT
    ready = evaluate_host_image(
        image(artifact_trust_passed=True, hardware_regression_passed=True, rollback_test_passed=True)
    )
    assert ready.status is HostSecurityStatus.CANDIDATE_READY


def test_bad_digest_or_slot_is_unknown():
    assert evaluate_host_image(image(image_sha256="bad")).status is HostSecurityStatus.UNKNOWN
    assert evaluate_host_image(image(boot_slot="C")).status is HostSecurityStatus.UNKNOWN
