from __future__ import annotations

from typing import Any

from nova.local_llm import LocalLLM
from nova.shared import CommandEnvelope, TelemetryEnvelope


class ServerRuntime:
    """Mini-PC runtime boundary for AI, orchestration, and decision services."""

    def __init__(self, config: dict[str, Any]):
        role = config.get("deployment", {}).get("role", "server")
        if role != "server":
            raise ValueError("ServerRuntime requires deployment.role=server")
        self.config = config
        self.llm = LocalLLM(config)

    def ai_status(self) -> dict[str, Any]:
        status = self.llm.status()
        status["runtime_role"] = "server"
        return status

    def build_command(
        self,
        action: str,
        arguments: dict[str, Any] | None = None,
        *,
        requested_by: str = "nova_core",
    ) -> CommandEnvelope:
        return CommandEnvelope(
            action=action,
            arguments=arguments or {},
            requested_by=requested_by,
        )

    def ingest_telemetry(self, event: TelemetryEnvelope) -> dict[str, Any]:
        return {
            "accepted": True,
            "event_id": event.event_id,
            "source": event.source,
            "kind": event.kind,
        }
