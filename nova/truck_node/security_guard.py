from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass


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


class SecurityGuard:
    """Deterministic identity, integrity, and authorization checks for the Pi edge."""

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
