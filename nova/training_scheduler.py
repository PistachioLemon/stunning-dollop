from __future__ import annotations

import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .learning import LearningService


class DailyTrainingScheduler:
    """Queues one TruckLM candidate batch each day at the configured local time.

    The scheduler automates candidate creation from approved lessons and selected
    occurrences. Promotion to the active GGUF remains a separate evaluated step.
    """

    def __init__(
        self,
        service: LearningService,
        *,
        timezone: str = "America/Los_Angeles",
        hour: int = 1,
        minute: int = 0,
        enabled: bool = True,
    ):
        self.service = service
        self.tz = ZoneInfo(timezone)
        self.hour = hour
        self.minute = minute
        self.enabled = enabled
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_result: dict | None = None

    def next_run(self, now: datetime | None = None) -> datetime:
        current = now.astimezone(self.tz) if now else datetime.now(self.tz)
        target = current.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
        if target <= current:
            target += timedelta(days=1)
        return target

    def start(self) -> None:
        if not self.enabled or (self._thread and self._thread.is_alive()):
            return
        self._thread = threading.Thread(target=self._loop, name="nova-daily-training", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _loop(self) -> None:
        while not self._stop.is_set():
            target = self.next_run()
            wait_seconds = max(1.0, (target - datetime.now(self.tz)).total_seconds())
            if self._stop.wait(wait_seconds):
                return
            try:
                self.last_result = self.service.create_training_batch(automatic=True)
            except ValueError as exc:
                self.last_result = {"status": "skipped", "reason": str(exc), "scheduled_for": target.isoformat()}
            except Exception as exc:
                self.last_result = {"status": "failed", "reason": str(exc), "scheduled_for": target.isoformat()}

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "timezone": str(self.tz),
            "hour": self.hour,
            "minute": self.minute,
            "next_run": self.next_run().isoformat() if self.enabled else None,
            "last_result": self.last_result,
        }
