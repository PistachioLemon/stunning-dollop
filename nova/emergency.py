from __future__ import annotations

import hmac
import threading
import uuid
from dataclasses import dataclass
from typing import Callable

from .database import Database


@dataclass
class EmergencyResult:
    session_id: str
    state: str
    countdown_seconds: int
    outbound_enabled: bool


class EmergencyService:
    def __init__(
        self,
        database: Database,
        config: dict,
        notifier: Callable[[str, str], None] | None = None,
    ):
        self.database = database
        self.config = config
        self.notifier = notifier
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.RLock()

    def start(self, reason: str = "SOS button pressed") -> EmergencyResult:
        session_id = uuid.uuid4().hex
        seconds = int(self.config["safety"]["countdown_seconds"])
        self.database.create_emergency(session_id, reason)
        self.database.event("emergency_countdown_started", {"session_id": session_id, "reason": reason})
        timer = threading.Timer(seconds, self._escalate, args=(session_id,))
        timer.daemon = True
        with self._lock:
            self._timers[session_id] = timer
        timer.start()
        return EmergencyResult(
            session_id=session_id,
            state="countdown",
            countdown_seconds=seconds,
            outbound_enabled=bool(self.config["safety"]["outbound_emergency_enabled"]),
        )

    def cancel(self, session_id: str, pin: str) -> dict:
        expected = str(self.config["profile"]["emergency_pin"])
        if not hmac.compare_digest(str(pin), expected):
            self.database.event("emergency_cancel_rejected", {"session_id": session_id})
            raise PermissionError("Incorrect emergency PIN")
        current = self.database.emergency(session_id)
        if not current:
            raise KeyError("Emergency session not found")
        if current["state"] not in ("countdown", "ready"):
            return current
        with self._lock:
            timer = self._timers.pop(session_id, None)
        if timer:
            timer.cancel()
        self.database.set_emergency_state(session_id, "cancelled")
        self.database.event("emergency_cancelled", {"session_id": session_id})
        return self.database.emergency(session_id) or {}

    def _escalate(self, session_id: str) -> None:
        outbound = bool(self.config["safety"]["outbound_emergency_enabled"])
        state = "notified" if outbound and self.notifier else "ready"
        self.database.set_emergency_state(session_id, state)
        self.database.event("emergency_countdown_completed", {"session_id": session_id, "state": state})
        if outbound and self.notifier:
            self.notifier(session_id, "Nova SOS countdown completed")
        with self._lock:
            self._timers.pop(session_id, None)

    def shutdown(self) -> None:
        with self._lock:
            timers = list(self._timers.values())
            self._timers.clear()
        for timer in timers:
            timer.cancel()

