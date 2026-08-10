from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from typing import Any


@dataclass(frozen=True)
class ResearchSource:
    source_id: str
    name: str
    domain: str
    category: str
    trust: int
    enabled: bool = True


class TruckingResearchPolicy:
    """Allowlist and provenance policy for Nova trucking research.

    This module does not perform network requests itself. A host web-research
    adapter must supply fetched text and metadata. That separation keeps web
    content from gaining direct execution privileges.
    """

    def __init__(self, registry_path: str | Path):
        data = json.loads(Path(registry_path).read_text(encoding="utf-8"))
        self.rules = dict(data.get("rules", {}))
        self.sources = {
            item["id"]: ResearchSource(
                source_id=item["id"],
                name=item["name"],
                domain=item["domain"].lower(),
                category=item["category"],
                trust=int(item["trust"]),
                enabled=bool(item.get("enabled", True)),
            )
            for item in data.get("sources", [])
        }

    def source_for_url(self, url: str) -> ResearchSource | None:
        host = (urlparse(url).hostname or "").lower()
        for source in self.sources.values():
            if source.enabled and (host == source.domain or host.endswith("." + source.domain)):
                return source
        return None

    def authorize_url(self, url: str) -> bool:
        return self.source_for_url(url) is not None

    def normalize_evidence(self, *, url: str, title: str, text: str) -> dict[str, Any]:
        source = self.source_for_url(url)
        if source is None:
            raise PermissionError(f"Research source is not allowlisted: {url}")
        compact = " ".join(text.split())
        # Keep a bounded evidence excerpt. Full copyrighted manuals should be
        # stored only when the project has explicit permission or a compatible license.
        excerpt = compact[:6000]
        return {
            "source_id": source.source_id,
            "source_name": source.name,
            "category": source.category,
            "trust": source.trust,
            "url": url,
            "title": title,
            "excerpt": excerpt,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "actionable": False,
        }
