from __future__ import annotations

import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .learning import LearningService


class DailyTrainingScheduler:
    """Coordinates driver-logoff review and the 1 AM Pacific training window.

    Driver logoff does not start training. It opens a review period so the driver
    or operator can add missing particulars and acknowledge a candidate batch.
    At the configured nightly time, only an acknowledged batch is released to the
    training runner. Model promotion remains a separate evaluated step.
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

    def driver_logged_off(self, *, occurred_at: datetime | None = None, verified: bool = True) -> dict:
        """Return Nova's post-drive training review prompts after verified logoff."""
        if not self.enabled:
            return {"status": "disabled", "trigger": "driver_logoff"}
        if not verified:
            return {"status": "ignored", "reason": "driver logoff was not verified"}
        when = (occurred_at or datetime.now(self.tz)).astimezone(self.tz)
        self.last_driver_logoff = when.isoformat()
        review = self.service.logoff_review()
        return {
            "status": "review_required",
            "trigger": "driver_logoff",
            "driver_logged_off_at": when.isoformat(),
            "next_training_window": self.next_run(when).isoformat(),
            **review,
        }

    def _release_acknowledged_batch(self, *, scheduled_for: datetime) -> dict:
        with self._trigger_lock:
            try:
                result = self.service.release_acknowledged_batch_for_training()
                result["trigger"] = "nightly_1am_window"
                result["scheduled_for"] = scheduled_for.isoformat()
                self.last_result = result
            except ValueError as exc:
                self.last_result = {
                    "status": "skipped",
                    "reason": str(exc),
                    "trigger": "nightly_1am_window",
                    "scheduled_for": scheduled_for.isoformat(),
                }
            except Exception as exc:
                self.last_result = {
                    "status": "failed",
                    "reason": str(exc),
                    "trigger": "nightly_1am_window",
                    "scheduled_for": scheduled_for.isoformat(),
                }
        return self.last_result

    def _loop(self) -> None:
        while not self._stop.is_set():
            target = self.next_run()
            wait_seconds = max(1.0, (target - datetime.now(self.tz)).total_seconds())
            if self._stop.wait(wait_seconds):
                return
            self._release_acknowledged_batch(scheduled_for=target)

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "timezone": str(self.tz),
            "hour": self.hour,
            "minute": self.minute,
            "next_run": self.next_run().isoformat() if self.enabled else None,
            "driver_logoff_behavior": "review_and_prompt_only",
            "acknowledgement_required_before_1am": True,
            "last_driver_logoff": self.last_driver_logoff,
            "last_result": self.last_result,
        }
