from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from nova.learning import LearningService
from nova.training_scheduler import DailyTrainingScheduler


def test_scheduler_targets_next_1am_pacific(tmp_path: Path):
    service = LearningService(tmp_path / "learning.db")
    scheduler = DailyTrainingScheduler(service, timezone="America/Los_Angeles", hour=1, minute=0)
    now = datetime(2026, 8, 9, 22, 30, tzinfo=ZoneInfo("America/Los_Angeles"))
    target = scheduler.next_run(now)
    assert target.hour == 1
    assert target.minute == 0
    assert target.date().isoformat() == "2026-08-10"


def test_automatic_batch_uses_approved_lessons_and_selected_occurrences(tmp_path: Path):
    service = LearningService(tmp_path / "learning.db")
    lesson = service.learn(
        mode="manual",
        title="Load securement lesson",
        content="Verify securement before departure.",
        approve_for_training=True,
    )
    occurrence = service.record_occurrence(
        event_type="dispatch_decision",
        component="dispatcher",
        summary="Rejected load because HOS could not cover appointment.",
        selected_for_training=True,
    )
    batch = service.create_training_batch(automatic=True)
    assert lesson["id"] in batch["lesson_ids"]
    assert occurrence["id"] in batch["occurrence_ids"]
    assert batch["automatic"] is True
    assert batch["execution_started"] is False
