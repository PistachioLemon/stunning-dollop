from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CapsuleManifest:
    """Description of a portable Nova knowledge/agent capsule.

    A capsule deliberately does not receive direct hardware access. It may
    request named capabilities, but the host permission broker decides what
    can actually execute.
    """

    name: str
    version: str
    model: str | None = None
    system_prompt: str = ""
    knowledge: tuple[str, ...] = ()
    requested_tools: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "CapsuleManifest":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            name=data["name"],
            version=data.get("version", "0.1"),
            model=data.get("model"),
            system_prompt=data.get("system_prompt", ""),
            knowledge=tuple(data.get("knowledge", [])),
            requested_tools=tuple(data.get("requested_tools", [])),
            metadata=dict(data.get("metadata", {})),
        )

    def digest(self) -> str:
        canonical = json.dumps(
            {
                "name": self.name,
                "version": self.version,
                "model": self.model,
                "system_prompt": self.system_prompt,
                "knowledge": self.knowledge,
                "requested_tools": self.requested_tools,
                "metadata": self.metadata,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


class PermissionBroker:
    """Host-side capability gate for capsule tool requests.

    The default policy is deny. This keeps portable documents and future PDF
    experiments from becoming an implicit path to sensors, files, messaging,
    shell commands, GPIO, or other privileged host capabilities.
    """

    def __init__(self, allowed_tools: set[str] | None = None):
        self.allowed_tools = set(allowed_tools or ())

    def authorize(self, manifest: CapsuleManifest, tool: str) -> bool:
        return tool in manifest.requested_tools and tool in self.allowed_tools

    def require(self, manifest: CapsuleManifest, tool: str) -> None:
        if not self.authorize(manifest, tool):
            raise PermissionError(f"Capsule tool denied: {tool}")

    def evaluate(self, manifest: CapsuleManifest, tool: str, arguments: dict[str, Any] | None = None) -> dict:
        return {
            "capsule": manifest.name,
            "capsule_digest": manifest.digest(),
            "tool": tool,
            "arguments": arguments or {},
            "authorized": self.authorize(manifest, tool),
        }
