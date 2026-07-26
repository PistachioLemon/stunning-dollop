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
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            dosage TEXT NOT NULL,
            due_time TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS medication_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medication_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            FOREIGN KEY(medication_id) REFERENCES medications(id)
        );
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS emergency_sessions (
            id TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS package_deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            carrier TEXT NOT NULL,
            tracking_code TEXT NOT NULL UNIQUE,
            recipient TEXT NOT NULL,
            courier_pin_hash TEXT,
            state TEXT NOT NULL DEFAULT 'expected',
            confidence REAL,
            evidence_sha256 TEXT,
            verified_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS package_locker_state (
            singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
            state TEXT NOT NULL,
            reason TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS package_access_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            code_type TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used_at TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(delivery_id) REFERENCES package_deliveries(id)
        );
        """
        with self._lock, self.connect() as connection:
            connection.executescript(schema)
            connection.execute(
                """INSERT OR IGNORE INTO package_locker_state(singleton, state, reason, updated_at)
                VALUES (1, 'locked', 'safe startup default', ?)""",
                (self.now(),),
            )

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def event(self, kind: str, payload: dict[str, Any]) -> int:
        with self._lock, self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO events(kind, payload, created_at) VALUES (?, ?, ?)",
                (kind, json.dumps(payload, separators=(",", ":")), self.now()),
            )
            return int(cursor.lastrowid)

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {
                "id": row["id"],
                "kind": row["kind"],
                "payload": json.loads(row["payload"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def add_medication(self, name: str, dosage: str, due_time: str) -> int:
        with self._lock, self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO medications(name, dosage, due_time) VALUES (?, ?, ?)",
                (name.strip(), dosage.strip(), due_time),
            )
            return int(cursor.lastrowid)

    def medications(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT m.*,
                (SELECT status FROM medication_log l WHERE l.medication_id=m.id
                 ORDER BY l.id DESC LIMIT 1) AS last_status,
                (SELECT recorded_at FROM medication_log l WHERE l.medication_id=m.id
                 ORDER BY l.id DESC LIMIT 1) AS last_recorded_at
                FROM medications m WHERE active=1 ORDER BY due_time"""
            ).fetchall()
        return [dict(row) for row in rows]

    def log_medication(self, medication_id: int, status: str) -> None:
        with self._lock, self.connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM medications WHERE id=? AND active=1", (medication_id,)
            ).fetchone()
            if not exists:
                raise KeyError("Medication not found")
            connection.execute(
                "INSERT INTO medication_log(medication_id, status, recorded_at) VALUES (?, ?, ?)",
                (medication_id, status, self.now()),
            )

    def add_note(self, category: str, body: str) -> int:
        with self._lock, self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO notes(category, body, created_at) VALUES (?, ?, ?)",
                (category, body.strip(), self.now()),
            )
            return int(cursor.lastrowid)

    def notes(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM notes ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def create_emergency(self, session_id: str, reason: str) -> None:
        now = self.now()
        with self._lock, self.connect() as connection:
            connection.execute(
                """INSERT INTO emergency_sessions(id, state, reason, created_at, updated_at)
                VALUES (?, 'countdown', ?, ?, ?)""",
                (session_id, reason, now, now),
            )

    def set_emergency_state(self, session_id: str, state: str) -> None:
        with self._lock, self.connect() as connection:
            cursor = connection.execute(
                "UPDATE emergency_sessions SET state=?, updated_at=? WHERE id=?",
                (state, self.now(), session_id),
            )
            if cursor.rowcount != 1:
                raise KeyError("Emergency session not found")

    def emergency(self, session_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM emergency_sessions WHERE id=?", (session_id,)
            ).fetchone()
        return dict(row) if row else None

    def add_delivery(
        self,
        carrier: str,
        tracking_code: str,
        recipient: str,
        courier_pin_hash: str | None,
    ) -> int:
        now = self.now()
        with self._lock, self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO package_deliveries(
                    carrier, tracking_code, recipient, courier_pin_hash, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    carrier.strip(),
                    tracking_code.strip().upper(),
                    recipient.strip(),
                    courier_pin_hash,
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def deliveries(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT id, carrier, tracking_code, recipient, state, confidence,
                          evidence_sha256, verified_at, created_at, updated_at
                   FROM package_deliveries ORDER BY id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delivery_by_tracking(self, tracking_code: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM package_deliveries WHERE tracking_code=?",
                (tracking_code.strip().upper(),),
            ).fetchone()
        return dict(row) if row else None

    def delivery(self, delivery_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM package_deliveries WHERE id=?", (delivery_id,)
            ).fetchone()
        return dict(row) if row else None

    def verify_delivery(
        self,
        delivery_id: int,
        confidence: float,
        evidence_sha256: str | None,
    ) -> None:
        now = self.now()
        with self._lock, self.connect() as connection:
            cursor = connection.execute(
                """UPDATE package_deliveries
                   SET state='verified', confidence=?, evidence_sha256=?,
                       verified_at=?, updated_at=?
                   WHERE id=? AND state='expected'""",
                (confidence, evidence_sha256, now, now, delivery_id),
            )
            if cursor.rowcount != 1:
                raise KeyError("Expected delivery not found or already verified")

    def set_locker_state(self, state: str, reason: str) -> None:
        with self._lock, self.connect() as connection:
            connection.execute(
                """UPDATE package_locker_state SET state=?, reason=?, updated_at=?
                   WHERE singleton=1""",
                (state, reason, self.now()),
            )

    def locker_state(self) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT state, reason, updated_at FROM package_locker_state WHERE singleton=1"
            ).fetchone()
        return dict(row)

    def add_package_access_code(
        self,
        delivery_id: int,
        token_hash: str,
        code_type: str,
        expires_at: str,
    ) -> int:
        with self._lock, self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO package_access_codes(
                    delivery_id, token_hash, code_type, expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?)""",
                (delivery_id, token_hash, code_type, expires_at, self.now()),
            )
            return int(cursor.lastrowid)

    def consume_package_access_code(self, token_hash: str, now: str) -> dict[str, Any] | None:
        with self._lock, self.connect() as connection:
            row = connection.execute(
                """SELECT c.*, d.tracking_code, d.state AS delivery_state
                   FROM package_access_codes c
                   JOIN package_deliveries d ON d.id=c.delivery_id
                   WHERE c.token_hash=?""",
                (token_hash,),
            ).fetchone()
            if not row:
                return None
            result = dict(row)
            if result["used_at"] or result["expires_at"] < now:
                return result
            cursor = connection.execute(
                """UPDATE package_access_codes SET used_at=?
                   WHERE id=? AND used_at IS NULL AND expires_at>=?""",
                (now, result["id"], now),
            )
            if cursor.rowcount != 1:
                return None
            result["used_at"] = now
            return result
