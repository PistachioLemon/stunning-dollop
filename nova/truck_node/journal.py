from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from nova.shared import TelemetryEnvelope


@dataclass(frozen=True)
class JournalRecord:
    sequence: int
    event: TelemetryEnvelope


class EventJournal:
    """Append-only JSONL journal with crash-tail tolerance and explicit acknowledgements."""

    def __init__(self, path: str | Path, *, fsync: bool = True):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ack_path = self.path.with_suffix(self.path.suffix + ".ack")
        self.fsync = fsync
        self._next_sequence = self._discover_next_sequence()

    def _discover_next_sequence(self) -> int:
        last = 0
        for record in self.iter_records(include_acknowledged=True):
            last = max(last, record.sequence)
        return last + 1

    def _acknowledged_sequence(self) -> int:
        try:
            return int(self.ack_path.read_text(encoding="utf-8").strip() or "0")
        except (FileNotFoundError, ValueError):
            return 0

    def append(self, event: TelemetryEnvelope) -> JournalRecord:
        record = JournalRecord(sequence=self._next_sequence, event=event)
        encoded = json.dumps(
            {"sequence": record.sequence, "event": event.to_dict()},
            separators=(",", ":"),
            sort_keys=True,
        ) + "\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            if self.fsync:
                os.fsync(handle.fileno())
        self._next_sequence += 1
        return record

    def iter_records(self, *, include_acknowledged: bool = False) -> Iterable[JournalRecord]:
        if not self.path.exists():
            return []
        acked = 0 if include_acknowledged else self._acknowledged_sequence()
        records: list[JournalRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    raw = json.loads(line)
                    sequence = int(raw["sequence"])
                    if sequence <= acked:
                        continue
                    event_raw = raw["event"]
                    event = TelemetryEnvelope(
                        source=event_raw["source"],
                        kind=event_raw["kind"],
                        payload=dict(event_raw["payload"]),
                        event_id=event_raw["event_id"],
                        created_at=event_raw["created_at"],
                    )
                    records.append(JournalRecord(sequence=sequence, event=event))
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    # A torn final write must not make earlier durable records unreadable.
                    continue
        return records

    def pending(self) -> list[JournalRecord]:
        return list(self.iter_records())

    def acknowledge(self, sequence: int) -> None:
        if sequence < self._acknowledged_sequence():
            return
        temp = self.ack_path.with_suffix(self.ack_path.suffix + ".tmp")
        temp.write_text(str(sequence), encoding="utf-8")
        os.replace(temp, self.ack_path)

    def compact(self) -> int:
        pending = self.pending()
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        with temp.open("w", encoding="utf-8") as handle:
            for record in pending:
                handle.write(json.dumps(
                    {"sequence": record.sequence, "event": record.event.to_dict()},
                    separators=(",", ":"), sort_keys=True,
                ) + "\n")
            handle.flush()
            if self.fsync:
                os.fsync(handle.fileno())
        os.replace(temp, self.path)
        return len(pending)
