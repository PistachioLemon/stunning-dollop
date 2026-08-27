from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HostSecurityStatus(str, Enum):
    CURRENT = "CURRENT"
    SECURITY_UPDATE_REQUIRED = "SECURITY_UPDATE_REQUIRED"
    UNKNOWN = "UNKNOWN"
    CANDIDATE_READY = "CANDIDATE_READY"


@dataclass(frozen=True)
class SecurityAdvisory:
    advisory_id: str
    severity: str
    affects_installed_kernel: bool
    network_relevant: bool = False


@dataclass(frozen=True)
class HostImageEvidence:
    os_version: str
    kernel_version: str
    image_sha256: str
    boot_slot: str
    advisories: tuple[SecurityAdvisory, ...] = ()
    artifact_trust_passed: bool = False
    hardware_regression_passed: bool = False
    rollback_test_passed: bool = False


@dataclass(frozen=True)
class HostSecurityResult:
    status: HostSecurityStatus
    reasons: tuple[str, ...]


def evaluate_host_image(evidence: HostImageEvidence) -> HostSecurityResult:
    """Gate host-image promotion without auto-patching a field truck."""
    reasons: list[str] = []
    if not evidence.os_version.strip() or not evidence.kernel_version.strip():
        return HostSecurityResult(HostSecurityStatus.UNKNOWN, ("missing_os_or_kernel_version",))
    digest = evidence.image_sha256.lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        return HostSecurityResult(HostSecurityStatus.UNKNOWN, ("invalid_image_digest",))
    if evidence.boot_slot not in {"A", "B"}:
        return HostSecurityResult(HostSecurityStatus.UNKNOWN, ("invalid_boot_slot",))

    affected = [a for a in evidence.advisories if a.affects_installed_kernel]
    if affected:
        reasons.extend(f"advisory:{a.advisory_id}" for a in affected)
        if any(a.network_relevant or a.severity.casefold() in {"critical", "high"} for a in affected):
            return HostSecurityResult(HostSecurityStatus.SECURITY_UPDATE_REQUIRED, tuple(reasons))

    if evidence.artifact_trust_passed and evidence.hardware_regression_passed and evidence.rollback_test_passed:
        return HostSecurityResult(HostSecurityStatus.CANDIDATE_READY, tuple(reasons))

    if affected:
        return HostSecurityResult(HostSecurityStatus.SECURITY_UPDATE_REQUIRED, tuple(reasons))
    return HostSecurityResult(HostSecurityStatus.CURRENT, tuple(reasons))
