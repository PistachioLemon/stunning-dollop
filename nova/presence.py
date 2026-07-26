from __future__ import annotations

import time
from threading import Lock


class PresenceService:
    """Hardware-neutral presence state; a camera/PIR adapter can call observe()."""

    def __init__(self, config: dict):
        self.config = config["presence"]
        self._last_seen = time.monotonic()
        self._lock = Lock()

    def observe(self) -> dict:
        with self._lock:
            self._last_seen = time.monotonic()
        return self.state()

    def state(self) -> dict:
        with self._lock:
            idle = max(0, int(time.monotonic() - self._last_seen))
        if idle >= int(self.config["sleep_after_seconds"]):
            display = "sleep"
        elif idle >= int(self.config["dim_after_seconds"]):
            display = "dim"
        else:
            display = "awake"
        return {"present_recently": display == "awake", "idle_seconds": idle, "display": display}

