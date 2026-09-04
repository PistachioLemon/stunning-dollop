from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .models import HealthFinding, RiskLevel


@dataclass(frozen=True)
class RepairKnowledge:
    knowledge_id: str
    source: str
    title: str
    body: str
    trust: int = 50
    component: str | None = None
    signature: str | None = None
    proposed_action: str | None = None
    risk: RiskLevel = RiskLevel.MEDIUM


class RepairLibrarian:
    """Local, auditable repair-knowledge store.

    The librarian can ingest trusted local documentation, capsule notes, logs,
    manuals, and successful repair write-ups. It only retrieves and proposes
    knowledge; it never executes repair commands itself.
    """

    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS repair_knowledge (
                knowledge_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                trust INTEGER NOT NULL,
                component TEXT,
                signature TEXT,
                proposed_action TEXT,
                risk INTEGER NOT NULL
            )
            """
        )
        self.db.commit()

    @staticmethod
    def _id(source: str, title: str, body: str) -> str:
        raw = f"{source}\0{title}\0{body}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def ingest_text(
        self,
        *,
        source: str,
        title: str,
        body: str,
        trust: int = 50,
        component: str | None = None,
        signature: str | None = None,
        proposed_action: str | None = None,
        risk: RiskLevel = RiskLevel.MEDIUM,
    ) -> RepairKnowledge:
        if not 0 <= trust <= 100:
            raise ValueError("trust must be from 0 to 100")
        item = RepairKnowledge(
            knowledge_id=self._id(source, title, body),
            source=source,
            title=title,
            body=body,
            trust=trust,
            component=component,
            signature=signature,
            proposed_action=proposed_action,
            risk=risk,
        )
        self.db.execute(
            """
            INSERT OR REPLACE INTO repair_knowledge
            (knowledge_id, source, title, body, trust, component, signature, proposed_action, risk)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.knowledge_id,
                item.source,
                item.title,
                item.body,
                item.trust,
                item.component,
                item.signature,
                item.proposed_action,
                int(item.risk),
            ),
        )
        self.db.commit()
        return item

    def ingest_file(self, path: str | Path, *, trust: int = 60, component: str | None = None) -> RepairKnowledge:
        file_path = Path(path)
        return self.ingest_text(
            source=str(file_path.resolve()),
            title=file_path.name,
            body=file_path.read_text(encoding="utf-8", errors="replace"),
            trust=trust,
            component=component,
        )

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {token for token in re.findall(r"[a-zA-Z0-9_.:-]{3,}", text.lower())}

    def search(self, finding: HealthFinding, *, limit: int = 5) -> list[dict]:
        query_tokens = self._tokens(
            " ".join(
                [
                    finding.component,
                    finding.signature,
                    " ".join(f"{k} {v}" for k, v in finding.details.items()),
                ]
            )
        )
        rows = self.db.execute("SELECT * FROM repair_knowledge").fetchall()
        ranked: list[tuple[float, sqlite3.Row]] = []
        for row in rows:
            haystack = self._tokens(f"{row['title']} {row['body']} {row['component'] or ''} {row['signature'] or ''}")
            overlap = len(query_tokens & haystack)
            exact_signature = 5 if row["signature"] == finding.signature else 0
            exact_component = 2 if row["component"] == finding.component else 0
            score = overlap + exact_signature + exact_component + (row["trust"] / 100.0)
            if score > 0:
                ranked.append((score, row))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "knowledge_id": row["knowledge_id"],
                "source": row["source"],
                "title": row["title"],
                "body": row["body"],
                "trust": row["trust"],
                "component": row["component"],
                "signature": row["signature"],
                "proposed_action": row["proposed_action"],
                "risk": RiskLevel(row["risk"]).name.lower(),
                "score": score,
            }
            for score, row in ranked[:limit]
        ]

    def propose(self, finding: HealthFinding, *, minimum_trust: int = 70) -> list[dict]:
        """Return high-trust repair suggestions without registering or executing them."""
        return [
            hit
            for hit in self.search(finding)
            if hit["trust"] >= minimum_trust and hit["proposed_action"]
        ]

    def ingest_many(self, items: Iterable[RepairKnowledge]) -> None:
        for item in items:
            self.ingest_text(
                source=item.source,
                title=item.title,
                body=item.body,
                trust=item.trust,
                component=item.component,
                signature=item.signature,
                proposed_action=item.proposed_action,
                risk=item.risk,
            )
