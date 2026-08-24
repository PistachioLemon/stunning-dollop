from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class DeviceIdentity:
    node_id: str
    certificate_fingerprint: str

    def validate(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node_id is required")
        value = self.certificate_fingerprint.replace(":", "").lower()
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ValueError("certificate_fingerprint must be a SHA-256 fingerprint")


@dataclass(frozen=True)
class ArtifactTrustPolicy:
    allowed_repository: str
    allowed_workflow: str | None = None
    provenance_required: bool = True
    allow_hash_fallback: bool = False
    allowlist_expires_at: datetime | None = None


@dataclass(frozen=True)
class ArtifactEvidence:
    sha256: str
    expected_sha256: str
    provenance_present: bool
    provenance_valid: bool
    source_repository: str | None = None
    source_workflow: str | None = None


class SecurityGuard:
    """Deterministic identity, integrity, authorization, and artifact trust checks."""

    def __init__(self, identity: DeviceIdentity, *, allowed_topic_prefix: str):
        identity.validate()
        prefix = allowed_topic_prefix.strip("/")
        if not prefix:
            raise ValueError("allowed_topic_prefix is required")
        self.identity = identity
        self.allowed_topic_prefix = prefix

    def authorize_topic(self, topic: str, *, write: bool) -> bool:
        normalized = topic.strip("/")
        if not normalized.startswith(self.allowed_topic_prefix + "/"):
            return False
        # Vehicle-bus write topics are never remotely writable by default.
        if write and any(part in normalized.split("/") for part in {"can_write", "obd_write", "gpio_write"}):
            return False
        return True

    @staticmethod
    def sha256_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def verify_sha256(data: bytes, expected_hex: str) -> bool:
        actual = SecurityGuard.sha256_bytes(data)
        return hmac.compare_digest(actual, expected_hex.lower())

    @staticmethod
    def verify_artifact_trust(
        policy: ArtifactTrustPolicy,
        evidence: ArtifactEvidence,
        *,
        now: datetime | None = None,
    ) -> tuple[bool, list[str]]:
        """Evaluate already-verified provenance evidence without invoking network or shell tools.

        A separate verifier is responsible for cryptographically validating an upstream
        SLSA/GitHub attestation and translating its trusted claims into ArtifactEvidence.
        This method enforces RequantAi's local admission policy.
        """
        failures: list[str] = []
        current = now or datetime.now(timezone.utc)
        expiry = policy.allowlist_expires_at
        if expiry is not None:
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if current >= expiry:
                failures.append("allowlist_expired")

        if not hmac.compare_digest(evidence.sha256.lower(), evidence.expected_sha256.lower()):
            failures.append("sha256_mismatch")

        if evidence.provenance_present:
            if not evidence.provenance_valid:
                failures.append("invalid_provenance")
            if evidence.source_repository != policy.allowed_repository:
                failures.append("wrong_repository")
            if policy.allowed_workflow is not None and evidence.source_workflow != policy.allowed_workflow:
                failures.append("wrong_workflow")
        elif policy.provenance_required or not policy.allow_hash_fallback:
            failures.append("provenance_missing")

        return not failures, failures
