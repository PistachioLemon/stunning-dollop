from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .learning import LearningService
from .schemas import LearnCapture, LessonApproval, OccurrenceCapture, OccurrenceSelection


def build_learning_router(service: LearningService, scheduler=None) -> APIRouter:
    router = APIRouter(prefix="/api/learning", tags=["learning"])

    @router.get("/status")
    def status():
        payload = {
            **service.stats(),
            "learn_writes_weights": False,
            "nightly_training": True,
            "auto_promote_model": False,
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

    @router.post("/occurrences", status_code=201)
    def record_occurrence(request: OccurrenceCapture):
        return service.record_occurrence(**request.model_dump())

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
