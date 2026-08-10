from __future__ import annotations

import sqlite3
from pathlib import Path


class RepairMemory:
    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS repair_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signature TEXT NOT NULL,
                recipe_id TEXT NOT NULL,
                success INTEGER NOT NULL,
                rolled_back INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.connection.commit()

    def record(self, signature: str, recipe_id: str, success: bool, rolled_back: bool = False) -> None:
        self.connection.execute(
            "INSERT INTO repair_history(signature, recipe_id, success, rolled_back) VALUES (?, ?, ?, ?)",
            (signature, recipe_id, int(success), int(rolled_back)),
        )
        self.connection.commit()

    def score(self, signature: str, recipe_id: str) -> tuple[int, int]:
        row = self.connection.execute(
            """
            SELECT COALESCE(SUM(success), 0), COUNT(*)
            FROM repair_history
            WHERE signature = ? AND recipe_id = ?
            """,
            (signature, recipe_id),
        ).fetchone()
        return int(row[0]), int(row[1])
