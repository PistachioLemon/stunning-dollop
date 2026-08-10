from __future__ import annotations

import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .learning import LearningService


class DailyTrainingScheduler:
    """Queues TruckLM candidate batches during driver downtime.

    Preferred trigger: a verified driver logoff/end-of-driving event. Fallback:
    the configured local nightly time (default 1:00 AM Pacific). Promotion to the
    active GGUF remains a separate evaluated step.
    """

    def __init__(
        self,
        service: LearningService,
        *,
        timezone: str = "America/Los_Angeles",
        hour: int = 1,
        minute: int = 0,
        enabled: bool = True,
        train_on_driver_logoff: bool = True,
        min_minutes_after_logoff: int = 10,
    ):
        self.service = service
        self.tz = ZoneInfo(timezone)
        self.hour = hour
        self.minute = minute
        self.enabled = enabled
        self.train_on_driver_logoff = train_on_driver_logoff
        self.min_minutes_after_logoff = max(0, int(min_minutes_after_logoff))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._trigger_lock = threading.Lock()
        self.last_result: dict | None = None
        self.last_driver_logoff: str | None = None

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

    def _queue_batch(self, *, trigger: str, occurred_at: datetime | None = None) -> dict:
        when = (occurred_at or datetime.now(self.tz)).astimezone(self.tz)
        with self._trigger_lock:
            try:
                result = self.service.create_training_batch(automatic=True)
                result["trigger"] = trigger
                result["triggered_at"] = when.isoformat()
                self.last_result = result
            except ValueError as exc:
                self.last_result = {
                    "status": "skipped",
                    "reason": str(exc),
                    "trigger": trigger,
                    "triggered_at": when.isoformat(),
                }
            except Exception as exc:
                self.last_result = {
                    "status": "failed",
                    "reason": str(exc),
                    "trigger": trigger,
                    "triggered_at": when.isoformat(),
                }
        return self.last_result

    def driver_logged_off(self, *, occurred_at: datetime | None = None, verified: bool = True) -> dict:
        """Queue training after a verified ELD/app logoff or end-of-driving event.

        The scheduler does not infer logoff from silence. A caller must provide a
        verified status transition from the driver/ELD integration.
        """
        if not self.enabled:
            return {"status": "disabled", "trigger": "driver_logoff"}
        if not self.train_on_driver_logoff:
            return {"status": "ignored", "reason": "driver-logoff training disabled"}
        if not verified:
            return {"status": "ignored", "reason": "driver logoff was not verified"}

        when = (occurred_at or datetime.now(self.tz)).astimezone(self.tz)
        self.last_driver_logoff = when.isoformat()

        if self.min_minutes_after_logoff <= 0:
            return self._queue_batch(trigger="driver_logoff", occurred_at=when)

        delay = self.min_minutes_after_logoff * 60

        def delayed() -> None:
            if not self._stop.wait(delay):
                self._queue_batch(trigger="driver_logoff", occurred_at=when)

        threading.Thread(target=delayed, name="nova-training-after-logoff", daemon=True).start()
        return {
            "status": "scheduled",
            "trigger": "driver_logoff",
            "driver_logged_off_at": when.isoformat(),
            "delay_minutes": self.min_minutes_after_logoff,
        }

    def _loop(self) -> None:
        while not self._stop.is_set():
            target = self.next_run()
            wait_seconds = max(1.0, (target - datetime.now(self.tz)).total_seconds())
            if self._stop.wait(wait_seconds):
                return
            self._queue_batch(trigger="nightly_fallback_1am", occurred_at=target)

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "timezone": str(self.tz),
            "hour": self.hour,
            "minute": self.minute,
            "next_run": self.next_run().isoformat() if self.enabled else None,
            "train_on_driver_logoff": self.train_on_driver_logoff,
            "min_minutes_after_logoff": self.min_minutes_after_logoff,
            "last_driver_logoff": self.last_driver_logoff,
            "last_result": self.last_result,
        }
