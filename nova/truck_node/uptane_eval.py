from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class UptaneTarget:
    truck_id: str
    hardware_id: str
    version: int
    minimum_version: int
    image_sha256: str
    expires_at: str
    director_verified: bool
    image_repo_verified: bool


class UptanePolicyEvaluator:
    """Policy-only Uptane evaluation gate; cryptographic verification happens elsewhere."""

    @staticmethod
    def evaluate(
        target: UptaneTarget,
        *,
        expected_truck_id: str,
        expected_hardware_id: str,
        current_version: int,
        observed_image_sha256: str,
        now: datetime | None = None,
    ) -> tuple[bool, str]:
        if not target.director_verified:
            return False, "director_unverified"
        if not target.image_repo_verified:
            return False, "image_repository_unverified"
        if target.truck_id != expected_truck_id:
            return False, "wrong_truck"
        if target.hardware_id != expected_hardware_id:
            return False, "wrong_hardware"
        if target.version < target.minimum_version or target.version < current_version:
            return False, "rollback_rejected"
        moment = now or datetime.now(timezone.utc)
        expiry = datetime.fromisoformat(target.expires_at.replace("Z", "+00:00"))
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if moment >= expiry:
            return False, "metadata_expired"
        if observed_image_sha256.lower() != target.image_sha256.lower():
            return False, "image_digest_mismatch"
        return True, "authorized"
