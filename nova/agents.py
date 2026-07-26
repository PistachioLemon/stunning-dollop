from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Agent:
    key: str
    name: str
    purpose: str
    capabilities: tuple[str, ...]


AGENTS = (
    Agent("companion", "Companion", "Conversation, daily check-ins, and simple help", ("chat", "check_in")),
    Agent("medication", "Medication", "Schedules, reminders, and taken/skipped records", ("list", "record")),
    Agent("safety", "Safety", "SOS countdown, cancellation, and household safety", ("sos", "cancel")),
    Agent("home", "Home", "Home Assistant lights, climate, scenes, and status", ("status", "control")),
    Agent("family_notes", "Family Notes", "Record messages, memories, and caregiver notes", ("save", "list")),
    Agent("librarian", "Librarian", "Find local instructions and explain stored information", ("search", "answer")),
    Agent(
        "package_guardian",
        "Package Guardian",
        "Verify expected deliveries and securely control the package locker",
        ("verify_delivery", "status", "lock", "unlock"),
    ),
)


class AgentRouter:
    def __init__(self, handlers: dict[str, Callable[[str], dict]] | None = None):
        self.handlers = handlers or {}

    @staticmethod
    def classify(text: str) -> str:
        normalized = text.lower()
        if any(word in normalized for word in ("medicine", "medication", "pill", "dose")):
            return "medication"
        if any(word in normalized for word in ("help", "emergency", "sos", "fell", "fall")):
            return "safety"
        if any(word in normalized for word in ("light", "thermostat", "temperature", "home")):
            return "home"
        if any(word in normalized for word in ("remember", "note", "message for", "family")):
            return "family_notes"
        if any(
            phrase in normalized
            for phrase in ("package", "delivery", "courier", "locker", "tracking")
        ):
            return "package_guardian"
        if any(word in normalized for word in ("find", "document", "instructions", "what does")):
            return "librarian"
        return "companion"

    def route(self, text: str) -> dict:
        key = self.classify(text)
        handler = self.handlers.get(key)
        if handler:
            return {"agent": key, **handler(text)}
        responses = {
            "companion": "I’m right here. What would you like to do?",
            "medication": "I can show the medication schedule or record a dose.",
            "safety": "I can start the SOS countdown. Say or press SOS to continue.",
            "home": "Home controls are ready when Home Assistant is connected.",
            "family_notes": "I can save that as a family note.",
            "librarian": "I can search Nova’s local notes and instructions.",
            "package_guardian": (
                "I can check expected deliveries and show the locker status. "
                "Lock and unlock actions require authorization."
            ),
        }
        return {"agent": key, "reply": responses[key], "action_required": False}
