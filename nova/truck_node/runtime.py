from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Any

from nova.shared import CommandEnvelope, CommandResult, TelemetryEnvelope


@dataclass(frozen=True)
class NamedAction:
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    restricted: bool = False


class TruckEdgeRuntime:
    """Deterministic Pi-side runtime. No model, training, or AI imports belong here."""

    def __init__(self, node_id: str, max_buffered_events: int = 5000):
        if not node_id.strip():
            raise ValueError("node_id is required")
        if max_buffered_events < 100:
            raise ValueError("max_buffered_events must be at least 100")
        self.node_id = node_id
        self._actions: dict[str, NamedAction] = {}
        self._buffer: deque[TelemetryEnvelope] = deque(maxlen=max_buffered_events)

    def register_action(
        self,
        name: str,
        handler: Callable[[dict[str, Any]], dict[str, Any]],
        *,
        restricted: bool = False,
    ) -> None:
        if not name or not name.replace("_", "").isalnum():
            raise ValueError("action names must be simple named operations")
        self._actions[name] = NamedAction(handler=handler, restricted=restricted)

    def execute(self, command: CommandEnvelope, *, approved: bool = False) -> CommandResult:
        action = self._actions.get(command.action)
        if action is None:
            return CommandResult(command.command_id, False, "unknown_action")
        if action.restricted and not approved:
            return CommandResult(command.command_id, False, "approval_required")
        try:
            data = action.handler(dict(command.arguments)) or {}
        except Exception as exc:  # adapter failure must not crash the edge loop
            return CommandResult(
                command.command_id,
                False,
                "adapter_error",
                {"error_type": type(exc).__name__},
            )
        return CommandResult(command.command_id, True, "completed", data)

    def record_telemetry(self, kind: str, payload: dict[str, Any]) -> TelemetryEnvelope:
        event = TelemetryEnvelope(source=self.node_id, kind=kind, payload=dict(payload))
        self._buffer.append(event)
        return event

    def buffered_events(self) -> list[TelemetryEnvelope]:
        return list(self._buffer)

    def acknowledge_through(self, event_id: str) -> int:
        removed = 0
        while self._buffer:
            event = self._buffer.popleft()
            removed += 1
            if event.event_id == event_id:
                return removed
        return 0

    def health(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "role": "truck_edge",
            "ai_enabled": False,
            "registered_actions": sorted(self._actions),
            "buffered_events": len(self._buffer),
        }
