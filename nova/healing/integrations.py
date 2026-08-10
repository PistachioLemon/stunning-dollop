from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from .engine import SelfHealingEngine
from .librarian import RepairLibrarian
from .models import HealthFinding


@dataclass(frozen=True)
class KnowledgeSource:
    """Approved local source of repair knowledge.

    Only explicitly configured roots are scanned. Files are read as text and are
    never executed by the librarian.
    """

    root: str | Path
    trust: int
    component: str | None = None
    recursive: bool = True
    max_bytes: int = 1_000_000
    extensions: tuple[str, ...] = (".md", ".txt", ".log", ".json", ".yaml", ".yml")


class RepairEvidenceLoader:
    """Ingest trusted Nova manuals, capsule notes, logs, and local documentation."""

    def __init__(self, librarian: RepairLibrarian):
        self.librarian = librarian

    def ingest_source(self, source: KnowledgeSource) -> list[str]:
        root = Path(source.root).resolve()
        if not root.exists():
            return []
        candidates = root.rglob("*") if source.recursive and root.is_dir() else ([root] if root.is_file() else root.glob("*"))
        ingested: list[str] = []
        for path in candidates:
            try:
                resolved = path.resolve()
            except OSError:
                continue
            # Prevent traversal through symlinks outside the approved root.
            try:
                resolved.relative_to(root if root.is_dir() else root.parent)
            except ValueError:
                continue
            if not resolved.is_file() or resolved.suffix.lower() not in source.extensions:
                continue
            try:
                size = resolved.stat().st_size
            except OSError:
                continue
            if size <= 0 or size > source.max_bytes:
                continue
            item = self.librarian.ingest_file(resolved, trust=source.trust, component=source.component)
            ingested.append(item.knowledge_id)
        return ingested

    def ingest_many(self, sources: Iterable[KnowledgeSource]) -> list[str]:
        result: list[str] = []
        for source in sources:
            result.extend(self.ingest_source(source))
        return result


def local_llm_probe(local_llm) -> HealthFinding:
    """Read-only health probe for Nova's existing llama.cpp integration."""

    status = local_llm.status()
    if not status.get("enabled"):
        return HealthFinding(
            issue_id="local_llm:disabled",
            component="local_llm",
            signature="disabled_by_config",
            healthy=True,
            details=status,
        )
    if not status.get("model_present"):
        return HealthFinding(
            issue_id="local_llm:model_missing",
            component="local_llm",
            signature="gguf_model_missing",
            healthy=False,
            details=status,
        )
    return HealthFinding(
        issue_id="local_llm:configured",
        component="local_llm",
        signature="configured",
        healthy=True,
        details=status,
    )


def log_signature_probe(
    *,
    name: str,
    component: str,
    path: str | Path,
    signatures: Mapping[str, str],
    tail_bytes: int = 64_000,
) -> HealthFinding:
    """Inspect the tail of a local log for known error signatures.

    `signatures` maps stable Nova signature names to regex patterns. This probe
    does not invoke a shell, follow commands from logs, or alter the log file.
    """

    log_path = Path(path)
    if not log_path.is_file():
        return HealthFinding(
            issue_id=f"log:{name}:missing",
            component=component,
            signature="log_missing",
            healthy=True,
            details={"path": str(log_path)},
        )
    size = log_path.stat().st_size
    with log_path.open("rb") as handle:
        handle.seek(max(0, size - max(1024, tail_bytes)))
        text = handle.read().decode("utf-8", errors="replace")
    for signature, pattern in signatures.items():
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return HealthFinding(
                issue_id=f"log:{name}:{signature}",
                component=component,
                signature=signature,
                healthy=False,
                details={"path": str(log_path), "match": match.group(0)[:240]},
            )
    return HealthFinding(
        issue_id=f"log:{name}:healthy",
        component=component,
        signature="no_known_error",
        healthy=True,
        details={"path": str(log_path), "bytes_scanned": min(size, tail_bytes)},
    )


def protected_sandbox_probe(config: dict) -> HealthFinding:
    """Fail closed unless the configured repair sandbox is actually isolated."""

    app = config.get("app", {})
    locker = config.get("package_locker", {})
    host = str(app.get("host", ""))
    simulation = bool(app.get("simulation")) and bool(locker.get("simulation", True))
    isolated_host = host in {"127.0.0.1", "localhost", "::1"}
    healthy = simulation and isolated_host
    return HealthFinding(
        issue_id="sandbox:protected",
        component="protected_sandbox",
        signature="sandbox_ready" if healthy else "sandbox_not_isolated",
        healthy=healthy,
        details={"host": host, "simulation": simulation, "isolated_host": isolated_host},
    )


def register_default_evidence(
    *,
    engine: SelfHealingEngine,
    librarian: RepairLibrarian,
    local_llm,
    project_root: str | Path,
    data_dir: str | Path | None = None,
) -> dict:
    """Wire safe, read-only Nova evidence sources into the healing prototype.

    This intentionally registers probes and knowledge only. It does not register
    destructive repair handlers or grant new permissions.
    """

    root = Path(project_root).resolve()
    engine.register_probe("local_llm", lambda: local_llm_probe(local_llm))

    sources = [
        KnowledgeSource(root / "README.md", trust=80, component="nova"),
        KnowledgeSource(root / "docs", trust=80, component="nova"),
        KnowledgeSource(root / "capsules", trust=75, component="capsules"),
    ]
    if data_dir is not None:
        data = Path(data_dir)
        if not data.is_absolute():
            data = root / data
        # Runtime logs are evidence, not authority: deliberately lower trust.
        sources.append(KnowledgeSource(data / "logs", trust=45, component="runtime"))

    loader = RepairEvidenceLoader(librarian)
    ids = loader.ingest_many(sources)
    return {"probes": ["local_llm"], "knowledge_items": len(ids), "knowledge_ids": ids}
