from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class LearningService:
    """Stores operator-approved lessons and selected operational occurrences.

    LEARN writes retrieval-ready knowledge. Driver logoff produces a review
    prompt so the operator can add missing particulars. At the nightly window,
    Nova prepares or releases a candidate batch only after explicit acknowledgement.
    """

    def __init__(self, path: str | Path):
        self.path = str(path)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_sha256 TEXT UNIQUE NOT NULL,
                mode TEXT NOT NULL,
                title TEXT NOT NULL,
                source_url TEXT,
                content TEXT NOT NULL,
                operator_notes TEXT,
                trust INTEGER NOT NULL DEFAULT 60,
                approved_for_training INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS occurrences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                component TEXT NOT NULL,
                summary TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                selected_for_training INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS training_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                lesson_ids_json TEXT NOT NULL,
                occurrence_ids_json TEXT NOT NULL DEFAULT '[]',
                automatic INTEGER NOT NULL DEFAULT 0,
                acknowledged INTEGER NOT NULL DEFAULT 0,
                acknowledged_at TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(training_batches)").fetchall()}
        if "occurrence_ids_json" not in columns:
            self.db.execute("ALTER TABLE training_batches ADD COLUMN occurrence_ids_json TEXT NOT NULL DEFAULT '[]'")
        if "automatic" not in columns:
            self.db.execute("ALTER TABLE training_batches ADD COLUMN automatic INTEGER NOT NULL DEFAULT 0")
        if "acknowledged" not in columns:
            self.db.execute("ALTER TABLE training_batches ADD COLUMN acknowledged INTEGER NOT NULL DEFAULT 0")
        if "acknowledged_at" not in columns:
            self.db.execute("ALTER TABLE training_batches ADD COLUMN acknowledged_at TEXT")
        self.db.commit()

    @staticmethod
    def _clean(text: str, limit: int = 250_000) -> str:
        compact = "\n".join(line.strip() for line in text.replace("\r", "\n").split("\n") if line.strip())
        return compact[:limit]

    def learn(self, *, mode: str, title: str, content: str, source_url: str | None = None,
              operator_notes: str | None = None, trust: int = 60,
              approve_for_training: bool = False) -> dict[str, Any]:
        if mode not in {"page", "selection", "document", "screen_lesson", "manual"}:
            raise ValueError("unsupported learning mode")
        clean = self._clean(content)
        if not clean:
            raise ValueError("lesson content is empty")
        if not 0 <= trust <= 100:
            raise ValueError("trust must be from 0 to 100")
        digest = hashlib.sha256(f"{mode}\0{source_url or ''}\0{clean}".encode("utf-8")).hexdigest()
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            """INSERT OR IGNORE INTO lessons
            (lesson_sha256, mode, title, source_url, content, operator_notes, trust, approved_for_training, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (digest, mode, title[:200], source_url, clean, operator_notes, trust, int(approve_for_training), now),
        )
        self.db.commit()
        row = self.db.execute("SELECT * FROM lessons WHERE lesson_sha256 = ?", (digest,)).fetchone()
        return dict(row)

    def record_occurrence(self, *, event_type: str, component: str, summary: str,
                          payload: dict[str, Any] | None = None,
                          selected_for_training: bool = False) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        cur = self.db.execute(
            """INSERT INTO occurrences
            (event_type, component, summary, payload_json, selected_for_training, created_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (event_type[:80], component[:80], self._clean(summary, 4000), json.dumps(payload or {}, sort_keys=True), int(selected_for_training), now),
        )
        self.db.commit()
        return {"id": cur.lastrowid, "event_type": event_type, "component": component,
                "selected_for_training": selected_for_training, "created_at": now}

    def select_occurrence(self, occurrence_id: int, selected: bool = True) -> dict[str, Any]:
        cur = self.db.execute("UPDATE occurrences SET selected_for_training = ? WHERE id = ?", (int(selected), occurrence_id))
        self.db.commit()
        if not cur.rowcount:
            raise KeyError("occurrence not found")
        return {"id": occurrence_id, "selected_for_training": selected}

    def lessons(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT id, lesson_sha256, mode, title, source_url, trust, approved_for_training, created_at FROM lessons ORDER BY id DESC LIMIT ?",
            (max(1, min(limit, 500)),),
        ).fetchall()
        return [dict(row) for row in rows]

    def occurrences(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT id, event_type, component, summary, selected_for_training, created_at FROM occurrences ORDER BY id DESC LIMIT ?",
            (max(1, min(limit, 500)),),
        ).fetchall()
        return [dict(row) for row in rows]

    def approve(self, lesson_id: int, approved: bool = True) -> dict[str, Any]:
        cur = self.db.execute("UPDATE lessons SET approved_for_training = ? WHERE id = ?", (int(approved), lesson_id))
        self.db.commit()
        if not cur.rowcount:
            raise KeyError("lesson not found")
        return {"id": lesson_id, "approved_for_training": approved}

    def logoff_review(self, *, lookback_hours: int = 24) -> dict[str, Any]:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=max(1, lookback_hours))).isoformat()
        rows = self.db.execute(
            """SELECT id, event_type, component, summary, selected_for_training
            FROM occurrences WHERE created_at >= ? ORDER BY id DESC LIMIT 100""",
            (cutoff,),
        ).fetchall()
        selected = [dict(row) for row in rows if row["selected_for_training"]]
        unselected = [dict(row) for row in rows if not row["selected_for_training"]]
        prompts = []
        if selected:
            prompts.append("Review today's selected events. Add corrections, causes, or better actions Nova should learn.")
        if unselected:
            prompts.append("Check whether any unselected event from today should be included in TruckLM training.")
        if any(row["event_type"] in {"repair_failure", "load_exception", "receiving_exception"} for row in rows):
            prompts.append("Explain any exception or failed repair whose real-world cause was not captured automatically.")
        if any(row["event_type"] == "driver_correction" for row in rows):
            prompts.append("Confirm the driver correction and the preferred future decision or wording.")
        if not prompts:
            prompts.append("Anything from today's driving, dispatch, loading, receiving, or equipment behavior Nova should remember?")
        return {
            "selected_occurrences": selected,
            "unselected_occurrences": unselected,
            "prompts": prompts,
            "training_window": "1:00 AM America/Los_Angeles",
            "acknowledgement_required": True,
        }

    def create_training_batch(self, *, automatic: bool = False, lookback_hours: int = 24) -> dict[str, Any]:
        lesson_rows = self.db.execute("SELECT id FROM lessons WHERE approved_for_training = 1 ORDER BY id").fetchall()
        lesson_ids = [int(row[0]) for row in lesson_rows]
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=max(1, lookback_hours))).isoformat()
        occurrence_rows = self.db.execute(
            "SELECT id FROM occurrences WHERE selected_for_training = 1 AND created_at >= ? ORDER BY id",
            (cutoff,),
        ).fetchall()
        occurrence_ids = [int(row[0]) for row in occurrence_rows]
        if not lesson_ids and not occurrence_ids:
            raise ValueError("no approved lessons or selected recent occurrences available for training")
        now = datetime.now(timezone.utc).isoformat()
        status = "awaiting_operator_acknowledgement"
        cur = self.db.execute(
            """INSERT INTO training_batches
            (status, lesson_ids_json, occurrence_ids_json, automatic, acknowledged, created_at)
            VALUES (?, ?, ?, ?, 0, ?)""",
            (status, json.dumps(lesson_ids), json.dumps(occurrence_ids), int(automatic), now),
        )
        self.db.commit()
        return {
            "batch_id": cur.lastrowid,
            "status": status,
            "lesson_ids": lesson_ids,
            "occurrence_ids": occurrence_ids,
            "automatic": automatic,
            "acknowledgement_required": True,
            "execution_started": False,
        }

    def acknowledge_training_batch(self, batch_id: int) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        row = self.db.execute("SELECT status FROM training_batches WHERE id = ?", (batch_id,)).fetchone()
        if row is None:
            raise KeyError("training batch not found")
        if row["status"] not in {"awaiting_operator_acknowledgement", "approved_to_train"}:
            raise ValueError(f"training batch cannot be acknowledged from status {row['status']}")
        self.db.execute(
            "UPDATE training_batches SET status = ?, acknowledged = 1, acknowledged_at = ? WHERE id = ?",
            ("approved_to_train", now, batch_id),
        )
        self.db.commit()
        return {
            "batch_id": batch_id,
            "status": "approved_to_train",
            "acknowledged_at": now,
            "execution_started": False,
            "next_step": "wait for the 1 AM Pacific training window",
        }

    def release_acknowledged_batch_for_training(self) -> dict[str, Any]:
        row = self.db.execute(
            """SELECT id FROM training_batches
            WHERE status = 'approved_to_train' AND acknowledged = 1
            ORDER BY id DESC LIMIT 1"""
        ).fetchone()
        if row is None:
            raise ValueError("no operator-acknowledged TruckLM batch is ready for the 1 AM window")
        batch_id = int(row["id"])
        self.db.execute(
            "UPDATE training_batches SET status = ? WHERE id = ?",
            ("ready_for_training_runner", batch_id),
        )
        self.db.commit()
        return {
            "batch_id": batch_id,
            "status": "ready_for_training_runner",
            "execution_started": False,
            "note": "1 AM window reached; an installed QLoRA runner may now execute this acknowledged batch",
        }

    def pending_training_batches(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.db.execute(
            """SELECT id, status, lesson_ids_json, occurrence_ids_json, automatic,
            acknowledged, acknowledged_at, created_at FROM training_batches
            WHERE status IN ('awaiting_operator_acknowledgement', 'approved_to_train', 'ready_for_training_runner')
            ORDER BY id DESC LIMIT ?""",
            (max(1, min(limit, 100)),),
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["lesson_ids"] = json.loads(item.pop("lesson_ids_json"))
            item["occurrence_ids"] = json.loads(item.pop("occurrence_ids_json"))
            result.append(item)
        return result

    def stats(self) -> dict[str, int]:
        total = self.db.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
        approved = self.db.execute("SELECT COUNT(*) FROM lessons WHERE approved_for_training = 1").fetchone()[0]
        occurrences = self.db.execute("SELECT COUNT(*) FROM occurrences").fetchone()[0]
        selected = self.db.execute("SELECT COUNT(*) FROM occurrences WHERE selected_for_training = 1").fetchone()[0]
        batches = self.db.execute("SELECT COUNT(*) FROM training_batches").fetchone()[0]
        awaiting = self.db.execute("SELECT COUNT(*) FROM training_batches WHERE status = 'awaiting_operator_acknowledgement'").fetchone()[0]
        return {
            "lessons": int(total),
            "approved_for_training": int(approved),
            "occurrences": int(occurrences),
            "selected_occurrences": int(selected),
            "training_batches": int(batches),
            "awaiting_acknowledgement": int(awaiting),
        }
