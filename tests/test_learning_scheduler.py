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


def test_driver_logoff_opens_review_not_training(tmp_path: Path):
    service = LearningService(tmp_path / "learning.db")
    service.record_occurrence(
        event_type="load_exception",
        component="driver",
        summary="Receiver reported damaged freight.",
        selected_for_training=True,
    )
    scheduler = DailyTrainingScheduler(service, timezone="America/Los_Angeles", hour=1, minute=0)
    result = scheduler.driver_logged_off(verified=True)
    assert result["status"] == "review_required"
    assert result["acknowledgement_required"] is True
    assert result["prompts"]
    assert service.stats()["training_batches"] == 0


def test_acknowledgement_gate_releases_batch_for_1am(tmp_path: Path):
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
    batch = service.create_training_batch(automatic=False)
    assert lesson["id"] in batch["lesson_ids"]
    assert occurrence["id"] in batch["occurrence_ids"]
    assert batch["status"] == "awaiting_operator_acknowledgement"
    assert batch["execution_started"] is False

    acknowledged = service.acknowledge_training_batch(batch["batch_id"])
    assert acknowledged["status"] == "approved_to_train"

    released = service.release_acknowledged_batch_for_training()
    assert released["status"] == "ready_for_training_runner"
    assert released["execution_started"] is False
