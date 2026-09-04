from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


@dataclass(frozen=True)
class RfidRead:
    epc: str
    reader_id: str
    antenna: str | None = None
    rssi: float | None = None
    observed_at: str | None = None


@dataclass(frozen=True)
class ReceivingResult:
    unique_epcs: tuple[str, ...]
    duplicate_reads: int
    missing_expected: tuple[str, ...]
    unexpected: tuple[str, ...]


def normalize_epc(value: str) -> str:
    clean = value.strip()
    if not clean:
        raise ValueError("EPC is required")
    return clean


def reconcile_receiving(reads: Iterable[RfidRead], expected_epcs: Iterable[str]) -> ReceivingResult:
    expected = {normalize_epc(item) for item in expected_epcs}
    observed: set[str] = set()
    duplicates = 0
    for read in reads:
        epc = normalize_epc(read.epc)
        if epc in observed:
            duplicates += 1
        observed.add(epc)

    return ReceivingResult(
        unique_epcs=tuple(sorted(observed)),
        duplicate_reads=duplicates,
        missing_expected=tuple(sorted(expected - observed)),
        unexpected=tuple(sorted(observed - expected)),
    )


def receiving_event_payload(result: ReceivingResult, *, reader_id: str) -> dict:
    return {
        "reader_id": reader_id,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "unique_epcs": list(result.unique_epcs),
        "duplicate_reads": result.duplicate_reads,
        "missing_expected": list(result.missing_expected),
        "unexpected": list(result.unexpected),
        "status": "exception" if result.missing_expected or result.unexpected else "matched",
    }
