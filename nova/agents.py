from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Agent:
    key: str
    name: str
    responsibility: str
    state: str = "ready"
    requires_hardware: bool = False


AGENTS = (
    Agent("dispatcher", "OpenClaw Dispatcher", "Ranks loads, routes work, and coordinates fleet decisions"),
    Agent("trucklm", "TruckLM", "Local trucking language, classification, and tool selection"),
    Agent("telemetry", "Truck Telemetry", "GPS, CAN, OBD-II, reefer, load-sensor, and MQTT state", requires_hardware=True),
    Agent("cargo_vision", "Cargo Vision", "Load verification and chain-of-custody evidence", requires_hardware=True),
    Agent("compliance", "HOS and Compliance", "Hours-of-service and operating constraint checks"),
    Agent("permission_broker", "Permission Broker", "Default-deny tool authorization and restricted-action approval"),
    Agent("librarian", "AI Librarian", "Operational knowledge and bounded retrieval memory"),
    Agent("repair_librarian", "Repair Librarian", "Trusted repair retrieval and outcome memory"),
    Agent("self_healing", "System Recovery", "Diagnostics, sandboxed repairs, verification, and rollback"),
    Agent("learning", "Operational Learning", "Selected events, post-drive review, and acknowledged training batches"),
)


class AgentRouter:
    ROUTES = {
        "load": "dispatcher", "bid": "dispatcher", "route": "dispatcher", "profit": "dispatcher",
        "gps": "telemetry", "obd": "telemetry", "can": "telemetry", "reefer": "telemetry", "mqtt": "telemetry",
        "cargo": "cargo_vision", "securement": "cargo_vision", "camera": "cargo_vision",
        "hos": "compliance", "compliance": "compliance", "repair": "self_healing", "fault": "self_healing",
        "manual": "librarian", "learn": "learning", "training": "learning",
    }

    def route(self, text: str) -> dict:
        normalized = text.casefold()
        agent = next((value for word, value in self.ROUTES.items() if word in normalized), "trucklm")
        selected = next(item for item in AGENTS if item.key == agent)
        return {"agent": agent, "reply": f"{selected.name} received the request.", "mode": "deterministic_fallback"}


def agent_manifest() -> list[dict]:
    return [asdict(agent) for agent in AGENTS]
