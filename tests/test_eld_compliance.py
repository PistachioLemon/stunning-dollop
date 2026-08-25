from datetime import datetime, timedelta, timezone

from nova.truck_node.eld_compliance import (
    ELDDevice,
    ELDRegistryRecord,
    ELDRegistrySnapshot,
    ELDStatus,
    evaluate_eld_compliance,
)

NOW = datetime(2026, 8, 25, 17, 0, tzinfo=timezone.utc)
DEVICE = ELDDevice("Example ELD Co", "RoadLog X", "ELD-123")


def snapshot(record, *, age_hours=1, verified=True):
    return ELDRegistrySnapshot(NOW - timedelta(hours=age_hours), verified, (record,))


def record(**overrides):
    values = dict(provider="Example ELD Co", model="RoadLog X", identifier="ELD-123", registered=True)
    values.update(overrides)
    return ELDRegistryRecord(**values)


def test_registered_device_is_recognized_from_verified_cache():
    result = evaluate_eld_compliance(DEVICE, snapshot(record()), now=NOW)
    assert result.status is ELDStatus.REGISTERED


def test_revoked_device_surfaces_replacement_deadline():
    deadline = NOW + timedelta(days=30)
    result = evaluate_eld_compliance(
        DEVICE, snapshot(record(registered=False, revoked=True, replacement_deadline=deadline)), now=NOW
    )
    assert result.status is ELDStatus.REVOKED
    assert result.replacement_deadline == deadline


def test_stale_registry_never_silently_marks_device_compliant():
    result = evaluate_eld_compliance(DEVICE, snapshot(record(), age_hours=24 * 8), now=NOW)
    assert result.status is ELDStatus.REGISTRY_STALE


def test_corrupted_or_unverified_registry_is_unknown():
    result = evaluate_eld_compliance(DEVICE, snapshot(record(), verified=False), now=NOW)
    assert result.status is ELDStatus.UNKNOWN
    assert result.reason == "registry_unverified"


def test_provider_model_identifier_mismatch_is_unknown():
    wrong = record(identifier="OTHER-ID")
    result = evaluate_eld_compliance(DEVICE, snapshot(wrong), now=NOW)
    assert result.status is ELDStatus.UNKNOWN


def test_duplicate_registry_match_is_unknown_not_compliant():
    rec = record()
    snap = ELDRegistrySnapshot(NOW - timedelta(hours=1), True, (rec, rec))
    result = evaluate_eld_compliance(DEVICE, snap, now=NOW)
    assert result.status is ELDStatus.UNKNOWN
