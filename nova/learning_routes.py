from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from .learning import LearningService
from .schemas import LearnCapture, LessonApproval, OccurrenceCapture, OccurrenceSelection


MAX_SCREEN_RECORDING_BYTES = 100 * 1024 * 1024


def build_learning_router(service: LearningService, scheduler=None, auto_select_event_types=None) -> APIRouter:
    router = APIRouter(prefix="/api/learning", tags=["learning"])
    auto_select = set(auto_select_event_types or [])

    @router.get("/status")
    def status():
        payload = {
            **service.stats(),
            "learn_writes_weights": False,
            "nightly_training": True,
            "auto_promote_model": False,
            "auto_select_event_types": sorted(auto_select),
            "policy": "learn immediately; selected lessons/occurrences batch automatically at 1 AM Pacific; promotion remains evaluated",
        }
        if scheduler is not None:
            payload["schedule"] = scheduler.status()
        return payload

    @router.get("/lessons")
    def lessons(limit: int = 100):
        return service.lessons(limit)

    @router.get("/occurrences")
    def occurrences(limit: int = 100):
        return service.occurrences(limit)

    @router.post("/learn", status_code=201)
    def learn(request: LearnCapture):
        try:
            return service.learn(**request.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/screen-recording", status_code=201)
    async def screen_recording(
        recording: UploadFile = File(...),
        title: str = Form("Operator screen lesson"),
        operator_notes: str = Form(""),
        approve_for_training: bool = Form(False),
    ):
        media_dir = Path(service.path).resolve().parent / "learning-media"
        media_dir.mkdir(parents=True, exist_ok=True)
        suffix = ".webm" if "webm" in (recording.content_type or "") else ".bin"
        target = media_dir / f"screen-{uuid.uuid4().hex}{suffix}"
        total = 0
        try:
            with target.open("wb") as output:
                while True:
                    chunk = await recording.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_SCREEN_RECORDING_BYTES:
                        raise HTTPException(status_code=413, detail="screen lesson exceeds 100 MB limit")
                    output.write(chunk)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        lesson = service.learn(
            mode="screen_lesson",
            title=title,
            content=json.dumps({
                "media_path": str(target),
                "bytes": total,
                "content_type": recording.content_type,
                "processing_state": "pending_audio_visual_extraction",
            }),
            operator_notes=operator_notes,
            trust=70,
            approve_for_training=approve_for_training,
        )
        return {"lesson": lesson, "media_saved": True, "processing_state": "pending_audio_visual_extraction"}

    @router.post("/occurrences", status_code=201)
    def record_occurrence(request: OccurrenceCapture):
        payload = request.model_dump()
        payload["selected_for_training"] = bool(
            request.selected_for_training or request.event_type in auto_select
        )
        return service.record_occurrence(**payload)

    @router.post("/lessons/{lesson_id}/approval")
    def approve(lesson_id: int, request: LessonApproval):
        try:
            return service.approve(lesson_id, request.approved)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/occurrences/{occurrence_id}/selection")
    def select_occurrence(occurrence_id: int, request: OccurrenceSelection):
        try:
            return service.select_occurrence(occurrence_id, request.selected)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/training-batches", status_code=201)
    def create_training_batch():
        try:
            return service.create_training_batch(automatic=False)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return router
