from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from nova.truck_node.uptane_eval import UptanePolicyEvaluator, UptaneTarget


def _target() -> UptaneTarget:
    return UptaneTarget(
        truck_id="truck-1",
        hardware_id="pi5-edge-v1",
        version=3,
        minimum_version=2,
        image_sha256=hashlib.sha256(b"image-v3").hexdigest(),
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        director_verified=True,
        image_repo_verified=True,
    )


def _evaluate(target: UptaneTarget, observed: str | None = None):
    return UptanePolicyEvaluator.evaluate(
        target,
        expected_truck_id="truck-1",
        expected_hardware_id="pi5-edge-v1",
        current_version=2,
        observed_image_sha256=observed or target.image_sha256,
    )


def test_uptane_accepts_dual_authorized_matching_target():
    assert _evaluate(_target()) == (True, "authorized")


def test_uptane_rejects_expired_and_rollback_metadata():
    expired = replace(_target(), expires_at=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat())
    assert _evaluate(expired)[1] == "metadata_expired"
    assert _evaluate(replace(_target(), version=1))[1] == "rollback_rejected"


def test_uptane_rejects_wrong_truck_hardware_and_modified_image():
    assert _evaluate(replace(_target(), truck_id="truck-99"))[1] == "wrong_truck"
    assert _evaluate(replace(_target(), hardware_id="other-board"))[1] == "wrong_hardware"
    assert _evaluate(_target(), hashlib.sha256(b"tampered").hexdigest())[1] == "image_digest_mismatch"


def test_uptane_requires_independent_director_and_image_authorization():
    assert _evaluate(replace(_target(), director_verified=False))[1] == "director_unverified"
    assert _evaluate(replace(_target(), image_repo_verified=False))[1] == "image_repository_unverified"
