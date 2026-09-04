from dataclasses import replace

from nova.logistics.edge_ledger import append_record, reconcile_event_sets, verify_chain
from nova.logistics.epcis import FreightEvent


def event(event_id: str, event_type: str, *, temp: float | None = None):
    sensor = {} if temp is None else {"type": "temperature", "value": temp, "uom": "CEL"}
    return FreightEvent(
        event_id=event_id,
        event_type=event_type,
        occurred_at="2026-09-03T18:00:00+00:00",
        object_ids=("urn:sscc:001",),
        location="dock-a",
        business_step=event_type,
        sensor=sensor,
    )


def test_shipping_receiving_chain_verifies():
    records = []
    for item in (event("arrive", "ARRIVAL"), event("receive", "RECEIVING"), event("ship", "SHIPPING")):
        records.append(append_record(records, item))
    passed, failures = verify_chain(records)
    assert passed is True
    assert failures == ()


def test_altered_sensor_event_is_detected():
    records = [append_record([], event("temp", "OBSERVATION", temp=2.0))]
    altered = replace(records[0], event=event("temp", "OBSERVATION", temp=9.0))
    passed, failures = verify_chain([altered])
    assert passed is False
    assert "hash_mismatch:temp" in failures


def test_duplicate_event_is_detected():
    first = append_record([], event("receive", "RECEIVING"))
    duplicate = append_record([first], event("receive", "RECEIVING"))
    passed, failures = verify_chain([first, duplicate])
    assert passed is False
    assert "duplicate_event:receive" in failures


def test_offline_reconciliation_finds_missing_and_conflicting_events():
    local = []
    local.append(append_record(local, event("receive", "RECEIVING")))
    local.append(append_record(local, event("temp", "OBSERVATION", temp=2.0)))

    remote = []
    remote.append(append_record(remote, event("temp", "OBSERVATION", temp=8.0)))
    remote.append(append_record(remote, event("pod", "DELIVERY")))

    missing_remote, missing_local, conflicts = reconcile_event_sets(local, remote)
    assert missing_remote == ("receive",)
    assert missing_local == ("pod",)
    assert conflicts == ("temp",)
