from datetime import datetime, timedelta, timezone

from nova.truck_node.eld_compliance import (
    ELDDevice,
    ELDEnforcementPhase,
    ELDRegistryRecord,
    ELDRegistrySnapshot,
    ELDStatus,
    evaluate_eld_compliance,
)

NOW = datetime(2026, 8, 25, 17, 0, tzinfo=timezone.utc)
DEVICE = ELDDevice("Example ELD Co", "RoadLog X", "ELD-123")


def snapshot(record, *, age_hours=1, verified=True, conflicts=()):
    return ELDRegistrySnapshot(NOW - timedelta(hours=age_hours), verified, (record,), conflicts)


def record(**overrides):
    values = dict(provider="Example ELD Co", model="RoadLog X", identifier="ELD-123", registered=True)
    values.update(overrides)
    return ELDRegistryRecord(**values)


def revoked(deadline):
    return record(registered=False, revoked=True, replacement_deadline=deadline)


def test_registered_device_is_recognized_from_verified_cache():
    result = evaluate_eld_compliance(DEVICE, snapshot(record()), now=NOW)
    assert result.status is ELDStatus.REGISTERED
    assert result.enforcement_phase is ELDEnforcementPhase.REGISTERED
    assert result.dispatch_ready is True


def test_revoked_device_surfaces_replacement_deadline():
    deadline = NOW + timedelta(days=45)
    result = evaluate_eld_compliance(DEVICE, snapshot(revoked(deadline)), now=NOW)
    assert result.status is ELDStatus.REVOKED
    assert result.replacement_deadline == deadline
    assert result.enforcement_phase is ELDEnforcementPhase.REVOKED_GRACE


def test_thirty_day_boundary_is_due_soon():
    result = evaluate_eld_compliance(DEVICE, snapshot(revoked(NOW + timedelta(days=30))), now=NOW)
    assert result.enforcement_phase is ELDEnforcementPhase.REPLACEMENT_DUE_SOON
    assert result.dispatch_ready is True


def test_seven_one_and_three_day_boundaries_are_due_soon():
    for days in (7, 3, 1):
        result = evaluate_eld_compliance(DEVICE, snapshot(revoked(NOW + timedelta(days=days))), now=NOW)
        assert result.enforcement_phase is ELDEnforcementPhase.REPLACEMENT_DUE_SOON


def test_deadline_instant_activates_enforcement_and_blocks_dispatch_ready():
    result = evaluate_eld_compliance(DEVICE, snapshot(revoked(NOW)), now=NOW)
    assert result.enforcement_phase is ELDEnforcementPhase.ENFORCEMENT_ACTIVE
    assert result.dispatch_ready is False


def test_after_deadline_enforcement_remains_active():
    result = evaluate_eld_compliance(DEVICE, snapshot(revoked(NOW - timedelta(days=1))), now=NOW)
    assert result.enforcement_phase is ELDEnforcementPhase.ENFORCEMENT_ACTIVE
    assert result.dispatch_ready is False


def test_revoked_without_deadline_does_not_guess_dispatch_readiness():
    result = evaluate_eld_compliance(
        DEVICE, snapshot(record(registered=False, revoked=True, replacement_deadline=None)), now=NOW
    )
    assert result.status is ELDStatus.REVOKED
    assert result.enforcement_phase is ELDEnforcementPhase.UNKNOWN
    assert result.dispatch_ready is None


def test_stale_registry_never_silently_marks_device_compliant():
    result = evaluate_eld_compliance(DEVICE, snapshot(record(), age_hours=24 * 8), now=NOW)
    assert result.status is ELDStatus.REGISTRY_STALE
    assert result.dispatch_ready is None


def test_corrupted_or_unverified_registry_is_unknown():
    result = evaluate_eld_compliance(DEVICE, snapshot(record(), verified=False), now=NOW)
    assert result.status is ELDStatus.UNKNOWN
    assert result.reason == "registry_unverified"


def test_conflicting_official_sources_fail_closed():
    result = evaluate_eld_compliance(
        DEVICE,
        snapshot(record(), conflicts=("registry_vs_news_deadline",)),
        now=NOW,
    )
    assert result.status is ELDStatus.UNKNOWN
    assert result.reason == "official_source_conflict"
    assert result.dispatch_ready is None


def test_provider_model_identifier_mismatch_is_unknown():
    wrong = record(identifier="OTHER-ID")
    result = evaluate_eld_compliance(DEVICE, snapshot(wrong), now=NOW)
    assert result.status is ELDStatus.UNKNOWN


def test_duplicate_registry_match_is_unknown_not_compliant():
    rec = record()
    snap = ELDRegistrySnapshot(NOW - timedelta(hours=1), True, (rec, rec))
    result = evaluate_eld_compliance(DEVICE, snap, now=NOW)
    assert result.status is ELDStatus.UNKNOWN
