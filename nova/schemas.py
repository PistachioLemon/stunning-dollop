from pydantic import BaseModel, Field


class MedicationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    dosage: str = Field(min_length=1, max_length=100)
    due_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class MedicationRecord(BaseModel):
    status: str = Field(pattern=r"^(taken|skipped)$")


class NoteCreate(BaseModel):
    category: str = Field(default="family", min_length=1, max_length=40)
    body: str = Field(min_length=1, max_length=4000)


class SOSCreate(BaseModel):
    reason: str = Field(default="SOS button pressed", min_length=1, max_length=300)


class SOSCancel(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    pin: str = Field(min_length=4, max_length=20)


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class HomeControl(BaseModel):
    domain: str = Field(pattern=r"^[a-z_]+$")
    service: str = Field(pattern=r"^[a-z_]+$")
    entity_id: str = Field(pattern=r"^[a-z_]+\.[a-zA-Z0-9_]+$")


class PackageCreate(BaseModel):
    carrier: str = Field(min_length=1, max_length=80)
    tracking_code: str = Field(min_length=4, max_length=120, pattern=r"^[A-Za-z0-9_-]+$")
    recipient: str = Field(min_length=1, max_length=100)
    courier_pin: str | None = Field(default=None, min_length=4, max_length=20, pattern=r"^\d+$")
    operator_pin: str = Field(min_length=4, max_length=20)


class PackageVerify(BaseModel):
    tracking_code: str = Field(min_length=4, max_length=120, pattern=r"^[A-Za-z0-9_-]+$")
    courier_pin: str | None = Field(default=None, min_length=4, max_length=20, pattern=r"^\d+$")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")


class LockerUnlock(BaseModel):
    pin: str = Field(min_length=4, max_length=20)
    duration_seconds: int | None = Field(default=None, ge=5, le=300)
    reason: str = Field(default="authorized manual unlock", min_length=1, max_length=200)


class LockerLock(BaseModel):
    pin: str = Field(min_length=4, max_length=20)
    reason: str = Field(default="authorized manual lock", min_length=1, max_length=200)


class PackageCodeCreate(BaseModel):
    operator_pin: str = Field(min_length=4, max_length=20)
    code_type: str = Field(default="qr", pattern=r"^(qr|code128)$")
    expires_minutes: int = Field(default=30, ge=1, le=1440)


class PackageCodeScan(BaseModel):
    code: str = Field(min_length=16, max_length=300)
