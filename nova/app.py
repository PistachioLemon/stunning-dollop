from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .agents import AgentRouter, agent_manifest
from .config import load_config
from .database import Database
from .healing.runtime import HealingRuntime
from .learning import LearningService
from .learning_routes import build_learning_router
from .local_llm import LocalLLM
from .schemas import ChatRequest, DispatchEvaluation, TruckTelemetry
from .training_scheduler import DailyTrainingScheduler


def create_app(config_path: str | None = None) -> FastAPI:
    config = load_config(config_path)
    project_root = Path(__file__).resolve().parent.parent
    data_dir = Path(config["app"]["data_dir"])
    if not data_dir.is_absolute():
        data_dir = project_root / data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    database = Database(data_dir / "dispatcher.db")
    local_llm = LocalLLM(config)
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
        database.event("dispatcher_started", {"version": __version__, "simulation": config["app"]["simulation"]})
        training_scheduler.start()
        yield
        training_scheduler.stop()
        database.event("dispatcher_stopped", {"version": __version__})

    app = FastAPI(title="RequantAi Dispatcher", version=__version__, lifespan=lifespan)
    app.state.config = config
    app.state.database = database
    app.state.healing_runtime = healing_runtime
    app.state.learning_service = learning_service
    app.state.training_scheduler = training_scheduler
    app.include_router(build_learning_router(learning_service, training_scheduler, learning_cfg.get("auto_select_event_types", [])))

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
            "runtime": {**config["runtime"], "cpu_only_ready": not config["runtime"]["require_accelerator"]},
            "telemetry": config["telemetry"],
            "local_llm": local_llm.status(),
            "system_recovery": {"diagnostics_enabled": True, "execution_enabled": False},
            "learning": {**learning_service.stats(), "weight_mutation_enabled": False, "schedule": training_scheduler.status()},
        }

    @app.get("/api/healing/status")
    def healing_status():
        try:
            return healing_runtime.diagnose()
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"System recovery diagnostics unavailable: {exc}") from exc

    @app.get("/api/agents")
    def agents():
        return agent_manifest()

    @app.post("/api/chat")
    def chat(request: ChatRequest):
        result = router.route(request.text)
        if result["agent"] in {"trucklm", "librarian"} and config["local_llm"]["enabled"]:
            try:
                result.update(reply=local_llm.chat(request.text), model="local_gguf")
            except RuntimeError as exc:
                result.update(model="deterministic_fallback", model_error=str(exc))
        database.event("agent_routed", {"text": request.text, "agent": result["agent"]})
        return result

    @app.get("/api/trucks")
    def trucks():
        return database.trucks()

    @app.post("/api/trucks/telemetry", status_code=202)
    def update_telemetry(request: TruckTelemetry):
        payload = request.model_dump(exclude={"truck_id"}, exclude_none=True)
        state = database.update_truck(request.truck_id, payload)
        database.event("truck_telemetry", {"truck_id": request.truck_id, "fields": sorted(payload)})
        return state

    @app.post("/api/dispatch/evaluate")
    def evaluate_load(request: DispatchEvaluation):
        profit = request.gross_revenue - request.estimated_cost - request.risk_penalty
        total_miles = request.deadhead_miles + request.loaded_miles
        score = round((profit / total_miles) if total_miles else 0, 2)
        result = {"truck_id": request.truck_id, "load_id": request.load_id, "estimated_profit": round(profit, 2), "profit_per_total_mile": score, "recommendation": "review" if profit > 0 else "reject", "requires_operator_approval": True}
        database.event("dispatch_decision", result)
        return result

    @app.get("/api/events")
    def events(limit: int = 50):
        return database.recent_events(min(max(limit, 1), 200))

    return app


app = create_app()
