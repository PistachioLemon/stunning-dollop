from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class TruckTelemetry(BaseModel):
    truck_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.:-]+$")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    speed_mph: float | None = Field(default=None, ge=0, le=200)
    engine_rpm: int | None = Field(default=None, ge=0, le=10000)
    fuel_percent: float | None = Field(default=None, ge=0, le=100)
    reefer_f: float | None = Field(default=None, ge=-100, le=200)
    load_weight_lb: float | None = Field(default=None, ge=0, le=200000)
    hos_drive_minutes_remaining: int | None = Field(default=None, ge=0, le=24 * 60)
    cargo_secure: bool | None = None
    mqtt_connected: bool | None = None
    faults: list[str] = Field(default_factory=list, max_length=100)


class DispatchEvaluation(BaseModel):
    truck_id: str = Field(min_length=1, max_length=80)
    load_id: str = Field(min_length=1, max_length=120)
    gross_revenue: float = Field(gt=0)
    estimated_cost: float = Field(ge=0)
    deadhead_miles: float = Field(default=0, ge=0)
    loaded_miles: float = Field(gt=0)
    risk_penalty: float = Field(default=0, ge=0)


class LearnCapture(BaseModel):
    mode: str = Field(pattern=r"^(page|selection|document|screen_lesson|manual)$")
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=250000)
    source_url: str | None = Field(default=None, max_length=2000)
    operator_notes: str | None = Field(default=None, max_length=8000)
    trust: int = Field(default=60, ge=0, le=100)
    approve_for_training: bool = False


class LessonApproval(BaseModel):
    approved: bool = True


class OccurrenceCapture(BaseModel):
    event_type: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.:-]+$")
    component: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.:-]+$")
    summary: str = Field(min_length=1, max_length=4000)
    payload: dict[str, Any] = Field(default_factory=dict)
    selected_for_training: bool = False


class OccurrenceSelection(BaseModel):
    selected: bool = True
