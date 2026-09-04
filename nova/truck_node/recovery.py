from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from nova.truck_node.security_guard import SecurityGuard


@dataclass(frozen=True)
class RecoveryManifest:
    version: int
    slot: str
    image_sha256: str
    expires_at: str
    minimum_version: int = 0
    signature: str = ""

    @classmethod
    def from_dict(cls, raw: dict) -> "RecoveryManifest":
        return cls(
            version=int(raw["version"]),
            slot=str(raw["slot"]),
            image_sha256=str(raw["image_sha256"]).lower(),
            expires_at=str(raw["expires_at"]),
            minimum_version=int(raw.get("minimum_version", 0)),
            signature=str(raw.get("signature", "")).lower(),
        )

    def signing_payload(self) -> bytes:
        canonical = {
            "expires_at": self.expires_at,
            "image_sha256": self.image_sha256,
            "minimum_version": self.minimum_version,
            "slot": self.slot,
            "version": self.version,
        }
        return json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode("utf-8")

    def validate(self, *, current_version: int, now: datetime | None = None) -> None:
        if self.slot not in {"A", "B"}:
            raise ValueError("recovery slot must be A or B")
        if self.version < self.minimum_version or self.version < current_version:
            raise ValueError("rollback update rejected")
        if len(self.image_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in self.image_sha256):
            raise ValueError("image_sha256 must be a SHA-256 digest")
        if len(self.signature) != 64 or any(ch not in "0123456789abcdef" for ch in self.signature):
            raise ValueError("recovery manifest requires an authenticated signature")
        moment = now or datetime.now(timezone.utc)
        expiry = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if moment >= expiry:
            raise ValueError("recovery manifest expired")


def sign_manifest(manifest: RecoveryManifest, signing_key: bytes) -> str:
    if len(signing_key) < 32:
        raise ValueError("recovery signing key must contain at least 256 bits")
    return hmac.new(signing_key, manifest.signing_payload(), hashlib.sha256).hexdigest()


def verify_manifest_signature(manifest: RecoveryManifest, signing_key: bytes) -> bool:
    if len(signing_key) < 32:
        return False
    expected = sign_manifest(manifest, signing_key)
    return hmac.compare_digest(expected, manifest.signature)


def verify_image(path: str | Path, manifest: RecoveryManifest) -> bool:
    data = Path(path).read_bytes()
    return SecurityGuard.verify_sha256(data, manifest.image_sha256)


def load_manifest(
    path: str | Path,
    *,
    current_version: int,
    signing_key: bytes,
) -> RecoveryManifest:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    manifest = RecoveryManifest.from_dict(raw)
    manifest.validate(current_version=current_version)
    if not verify_manifest_signature(manifest, signing_key):
        raise ValueError("recovery manifest signature rejected")
    return manifest
