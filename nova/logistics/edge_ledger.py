from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Iterable

from nova.logistics.epcis import FreightEvent


@dataclass(frozen=True)
class EdgeLedgerRecord:
    event: FreightEvent
    canonical_hash: str
    previous_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def canonical_event_payload(event: FreightEvent) -> bytes:
    payload = {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "occurred_at": event.occurred_at,
        "object_ids": sorted(event.object_ids),
        "location": event.location,
        "business_step": event.business_step,
        "disposition": event.disposition,
        "parent_id": event.parent_id,
        "sensor": event.sensor,
        "extensions": event.extensions,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_event_hash(event: FreightEvent) -> str:
    return sha256(canonical_event_payload(event)).hexdigest()


def append_record(records: Iterable[EdgeLedgerRecord], event: FreightEvent, *, metadata: dict[str, Any] | None = None) -> EdgeLedgerRecord:
    previous = None
    materialized = list(records)
    if materialized:
        previous = materialized[-1].canonical_hash
    return EdgeLedgerRecord(event, canonical_event_hash(event), previous, metadata or {})


def verify_record(record: EdgeLedgerRecord) -> bool:
    return record.canonical_hash == canonical_event_hash(record.event)


def verify_chain(records: Iterable[EdgeLedgerRecord]) -> tuple[bool, tuple[str, ...]]:
    failures: list[str] = []
    previous: str | None = None
    seen_event_ids: set[str] = set()
    for index, record in enumerate(records):
        if record.event.event_id in seen_event_ids:
            failures.append(f"duplicate_event:{record.event.event_id}")
        seen_event_ids.add(record.event.event_id)
        if not verify_record(record):
            failures.append(f"hash_mismatch:{record.event.event_id}")
        if record.previous_hash != previous:
            failures.append(f"chain_mismatch:{index}")
        previous = record.canonical_hash
    return (not failures, tuple(failures))


def reconcile_event_sets(local: Iterable[EdgeLedgerRecord], remote: Iterable[EdgeLedgerRecord]) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    local_map = {record.event.event_id: record.canonical_hash for record in local}
    remote_map = {record.event.event_id: record.canonical_hash for record in remote}
    missing_remote = tuple(sorted(set(local_map) - set(remote_map)))
    missing_local = tuple(sorted(set(remote_map) - set(local_map)))
    conflicts = tuple(sorted(event_id for event_id in set(local_map) & set(remote_map) if local_map[event_id] != remote_map[event_id]))
    return missing_remote, missing_local, conflicts
