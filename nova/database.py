from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        with self.connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS truck_state (
                    truck_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def event(self, kind: str, payload: dict[str, Any]) -> int:
        with self._lock, self.connect() as connection:
            cursor = connection.execute("INSERT INTO events(kind,payload,created_at) VALUES (?,?,?)", (kind, json.dumps(payload), self.now()))
            return int(cursor.lastrowid)

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]

    def update_truck(self, truck_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        updated_at = self.now()
        with self._lock, self.connect() as connection:
            connection.execute("INSERT INTO truck_state(truck_id,payload,updated_at) VALUES (?,?,?) ON CONFLICT(truck_id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at", (truck_id, json.dumps(payload), updated_at))
        return {"truck_id": truck_id, **payload, "updated_at": updated_at}

    def trucks(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM truck_state ORDER BY truck_id").fetchall()
        return [{"truck_id": row["truck_id"], **json.loads(row["payload"]), "updated_at": row["updated_at"]} for row in rows]
