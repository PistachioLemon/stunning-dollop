from __future__ import annotations

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

    @classmethod
    def from_dict(cls, raw: dict) -> "RecoveryManifest":
        return cls(
            version=int(raw["version"]),
            slot=str(raw["slot"]),
            image_sha256=str(raw["image_sha256"]).lower(),
            expires_at=str(raw["expires_at"]),
            minimum_version=int(raw.get("minimum_version", 0)),
        )

    def validate(self, *, current_version: int, now: datetime | None = None) -> None:
        if self.slot not in {"A", "B"}:
            raise ValueError("recovery slot must be A or B")
        if self.version < self.minimum_version or self.version < current_version:
            raise ValueError("rollback update rejected")
        if len(self.image_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in self.image_sha256):
            raise ValueError("image_sha256 must be a SHA-256 digest")
        moment = now or datetime.now(timezone.utc)
        expiry = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if moment >= expiry:
            raise ValueError("recovery manifest expired")


def verify_image(path: str | Path, manifest: RecoveryManifest) -> bool:
    data = Path(path).read_bytes()
    return SecurityGuard.verify_sha256(data, manifest.image_sha256)


def load_manifest(path: str | Path, *, current_version: int) -> RecoveryManifest:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    manifest = RecoveryManifest.from_dict(raw)
    manifest.validate(current_version=current_version)
    return manifest
