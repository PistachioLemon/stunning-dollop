from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .agents import AGENTS, AgentRouter
from .config import load_config
from .database import Database
from .emergency import EmergencyService
from .healing.runtime import HealingRuntime
from .home_assistant import HomeAssistantClient
from .learning import LearningService
from .learning_routes import build_learning_router
from .local_llm import LocalLLM
from .package_guardian import PackageGuardian
from .presence import PresenceService
from .security_cameras import SecurityCameraService
from .training_scheduler import DailyTrainingScheduler
from .schemas import (
    ChatRequest,
    HomeControl,
    LockerLock,
    LockerUnlock,
    MedicationCreate,
    MedicationRecord,
    NoteCreate,
    PackageCodeCreate,
    PackageCodeScan,
    PackageCreate,
    PackageVerify,
    SOSCancel,
    SOSCreate,
    SecurityCameraCreate,
    SecurityCameraEventCreate,
    SecurityCameraPrivacy,
)


def create_app(config_path: str | None = None) -> FastAPI:
    config = load_config(config_path)
    project_root = Path(__file__).resolve().parent.parent
    data_dir = Path(config["app"]["data_dir"])
    if not data_dir.is_absolute():
        data_dir = project_root / data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    database = Database(data_dir / "nova.db")
    emergency = EmergencyService(database, config)
    home = HomeAssistantClient(config)
    presence = PresenceService(config)
    package_guardian = PackageGuardian(database, config)
    local_llm = LocalLLM(config)
    security_cameras = SecurityCameraService(database, config)
    healing_runtime = HealingRuntime(config["_config_path"])
    learning_service = LearningService(data_dir / "learning.db")
    learning_cfg = config["learning"]
    training_scheduler = DailyTrainingScheduler(
        learning_service,
        timezone=learning_cfg["training_timezone"],
        hour=learning_cfg["training_hour"],
        minute=learning_cfg["training_minute"],
        enabled=bool(learning_cfg["enabled"] and learning_cfg["auto_training_enabled"]),
    )
    router = AgentRouter()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        database.event("nova_started", {"version": __version__, "simulation": config["app"]["simulation"]})
        training_scheduler.start()
        yield
        training_scheduler.stop()
        package_guardian.shutdown()
        emergency.shutdown()
        database.event("nova_stopped", {"version": __version__})

    app = FastAPI(title="Nova Home AI", version=__version__, lifespan=lifespan)
    app.state.config = config
    app.state.database = database
    app.state.emergency = emergency
    app.state.package_guardian = package_guardian
    app.state.security_cameras = security_cameras
    app.state.healing_runtime = healing_runtime
    app.state.learning_service = learning_service
    app.state.training_scheduler = training_scheduler
    app.include_router(build_learning_router(learning_service, training_scheduler))

    static_dir = project_root / "web"
    app.mount("/assets", StaticFiles(directory=static_dir), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(static_dir / "index.html")

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "name": config["app"]["name"],
            "version": __version__,
            "simulation": config["app"]["simulation"],
            "home_assistant": home.status(),
            "presence": presence.state(),
            "package_locker": package_guardian.status(),
            "local_llm": local_llm.status(),
            "security_cameras": security_cameras.status(),
            "self_healing": {"diagnostics_enabled": True, "execution_enabled": False},
            "learning": {
                **learning_service.stats(),
                "weight_mutation_enabled": False,
                "schedule": training_scheduler.status(),
            },
        }

    @app.get("/api/healing/status")
    def healing_status():
        try:
            return healing_runtime.diagnose()
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Self-healing diagnostics unavailable: {exc}") from exc

    @app.get("/api/agents")
    def agents():
        return [agent.__dict__ for agent in AGENTS]

    @app.post("/api/chat")
    def chat(request: ChatRequest):
        result = router.route(request.text)
        if result["agent"] in {"companion", "librarian"} and config["local_llm"]["enabled"]:
            try:
                result["reply"] = local_llm.chat(request.text)
                result["model"] = "local_gguf"
            except RuntimeError as exc:
                result["model"] = "agent_router_fallback"
                result["model_error"] = str(exc)
        database.event("agent_routed", {"text": request.text, "agent": result["agent"]})
        return result

    @app.get("/api/medications")
    def medications():
        return database.medications()

    @app.post("/api/medications", status_code=201)
    def add_medication(request: MedicationCreate):
        medication_id = database.add_medication(request.name, request.dosage, request.due_time)
        database.event("medication_added", {"medication_id": medication_id, "name": request.name})
        return {"id": medication_id}

    @app.post("/api/medications/{medication_id}/record")
    def record_medication(medication_id: int, request: MedicationRecord):
        try:
            database.log_medication(medication_id, request.status)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        database.event("medication_recorded", {"medication_id": medication_id, "status": request.status})
        return {"ok": True}

    @app.get("/api/notes")
    def notes():
        return database.notes()

    @app.post("/api/notes", status_code=201)
    def add_note(request: NoteCreate):
        note_id = database.add_note(request.category, request.body)
        database.event("note_added", {"note_id": note_id, "category": request.category})
        return {"id": note_id}

    @app.post("/api/sos", status_code=201)
    def start_sos(request: SOSCreate):
        return emergency.start(request.reason).__dict__

    @app.post("/api/sos/cancel")
    def cancel_sos(request: SOSCancel):
        try:
            return emergency.cancel(request.session_id, request.pin)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/sos/{session_id}")
    def sos_state(session_id: str):
        result = database.emergency(session_id)
        if not result:
            raise HTTPException(status_code=404, detail="Emergency session not found")
        return result

    @app.post("/api/presence")
    def observe_presence():
        return presence.observe()

    @app.post("/api/home/control")
    def control_home(request: HomeControl):
        try:
            result = home.call_service(request.domain, request.service, request.entity_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        database.event("home_control", request.model_dump())
        return result

    @app.get("/api/packages")
    def packages():
        return database.deliveries()

    @app.post("/api/packages", status_code=201)
    def add_package(request: PackageCreate):
        try:
            package_guardian.require_authorized(request.operator_pin)
            delivery_id = package_guardian.add_expected_delivery(request.carrier, request.tracking_code, request.recipient, request.courier_pin)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"id": delivery_id}

    @app.post("/api/packages/verify")
    def verify_package(request: PackageVerify):
        try:
            return package_guardian.verify_delivery(request.tracking_code, request.courier_pin, request.confidence, request.evidence_sha256)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/packages/{delivery_id}/access-code", status_code=201)
    def create_package_access_code(delivery_id: int, request: PackageCodeCreate):
        try:
            return package_guardian.generate_access_code(delivery_id, request.operator_pin, request.code_type, request.expires_minutes)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/packages/scan")
    def scan_package_access_code(request: PackageCodeScan):
        try:
            return package_guardian.scan_access_code(request.code)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/locker/status")
    def locker_status():
        return package_guardian.status()

    @app.post("/api/locker/unlock")
    def unlock_locker(request: LockerUnlock):
        try:
            package_guardian.require_authorized(request.pin)
            return package_guardian.unlock(request.reason, request.duration_seconds)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/locker/lock")
    def lock_locker(request: LockerLock):
        try:
            package_guardian.require_authorized(request.pin)
            return package_guardian.lock(request.reason)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.get("/api/events")
    def events(limit: int = 50):
        return database.recent_events(min(max(limit, 1), 200))

    @app.get("/api/security-cameras")
    def list_security_cameras():
        return {"status": security_cameras.status(), "cameras": database.security_cameras(), "events": database.camera_events(50)}

    @app.post("/api/security-cameras", status_code=201)
    def add_security_camera(request: SecurityCameraCreate):
        try:
            camera_id = security_cameras.add_camera(request.name, request.kind, request.room, request.connection, request.stream_url)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"id": camera_id}

    @app.post("/api/security-cameras/privacy")
    def set_security_camera_privacy(request: SecurityCameraPrivacy):
        return security_cameras.set_privacy(request.enabled)

    @app.get("/api/security-cameras/{camera_id}/preview")
    def preview_security_camera(camera_id: int):
        try:
            return security_cameras.preview(camera_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/security-cameras/{camera_id}/events", status_code=201)
    def add_security_camera_event(camera_id: int, request: SecurityCameraEventCreate):
        try:
            event_id = security_cameras.record_event(camera_id, request.event_type, request.confidence, request.description)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"id": event_id}

    return app


app = create_app()
