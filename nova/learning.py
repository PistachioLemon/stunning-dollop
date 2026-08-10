from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class LearningService:
    """Stores operator-approved lessons without mutating model weights.

    LEARN writes retrieval-ready knowledge and training candidates. TRAIN creates
    a candidate batch manifest only; a separate offline QLoRA job must consume,
    evaluate, and explicitly promote that batch.
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
            CREATE TABLE IF NOT EXISTS training_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                lesson_ids_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self.db.commit()

    @staticmethod
    def _clean(text: str, limit: int = 250_000) -> str:
        compact = "\n".join(line.strip() for line in text.replace("\r", "\n").split("\n") if line.strip())
        return compact[:limit]

    def learn(
        self,
        *,
        mode: str,
        title: str,
        content: str,
        source_url: str | None = None,
        operator_notes: str | None = None,
        trust: int = 60,
        approve_for_training: bool = False,
    ) -> dict[str, Any]:
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

    def lessons(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT id, lesson_sha256, mode, title, source_url, trust, approved_for_training, created_at FROM lessons ORDER BY id DESC LIMIT ?",
            (max(1, min(limit, 500)),),
        ).fetchall()
        return [dict(row) for row in rows]

    def approve(self, lesson_id: int, approved: bool = True) -> dict[str, Any]:
        cur = self.db.execute("UPDATE lessons SET approved_for_training = ? WHERE id = ?", (int(approved), lesson_id))
        self.db.commit()
        if not cur.rowcount:
            raise KeyError("lesson not found")
        return {"id": lesson_id, "approved_for_training": approved}

    def create_training_batch(self) -> dict[str, Any]:
        rows = self.db.execute("SELECT id FROM lessons WHERE approved_for_training = 1 ORDER BY id").fetchall()
        ids = [int(row[0]) for row in rows]
        if not ids:
            raise ValueError("no approved lessons available for training")
        now = datetime.now(timezone.utc).isoformat()
        cur = self.db.execute(
            "INSERT INTO training_batches(status, lesson_ids_json, created_at) VALUES (?, ?, ?)",
            ("candidate_pending_offline_qlora", json.dumps(ids), now),
        )
        self.db.commit()
        return {"batch_id": cur.lastrowid, "status": "candidate_pending_offline_qlora", "lesson_ids": ids, "execution_started": False}

    def stats(self) -> dict[str, int]:
        total = self.db.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
        approved = self.db.execute("SELECT COUNT(*) FROM lessons WHERE approved_for_training = 1").fetchone()[0]
        batches = self.db.execute("SELECT COUNT(*) FROM training_batches").fetchone()[0]
        return {"lessons": int(total), "approved_for_training": int(approved), "training_batches": int(batches)}
