from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .learning import LearningService
from .schemas import LearnCapture, LessonApproval


def build_learning_router(service: LearningService) -> APIRouter:
    router = APIRouter(prefix="/api/learning", tags=["learning"])

    @router.get("/status")
    def status():
        return {
            **service.stats(),
            "learn_writes_weights": False,
            "train_starts_qlora": False,
            "policy": "learn immediately; train only from operator-approved candidates",
        }

    @router.get("/lessons")
    def lessons(limit: int = 100):
        return service.lessons(limit)

    @router.post("/learn", status_code=201)
    def learn(request: LearnCapture):
        try:
            return service.learn(**request.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/lessons/{lesson_id}/approval")
    def approve(lesson_id: int, request: LessonApproval):
        try:
            return service.approve(lesson_id, request.approved)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/training-batches", status_code=201)
    def create_training_batch():
        try:
            return service.create_training_batch()
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return router
