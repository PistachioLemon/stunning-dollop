from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml

DEFAULTS: dict[str, Any] = {
    "app": {"name": "RequantAi Dispatcher", "host": "0.0.0.0", "port": 8787, "timezone": "America/Los_Angeles", "simulation": True, "data_dir": "./data"},
    "runtime": {"profile": "cpu_minimum", "accelerator": "auto", "require_accelerator": False},
    "local_llm": {"enabled": False, "server_url": "http://127.0.0.1:8080", "model_path": "./models/trucklm-small.gguf", "timeout_seconds": 45, "max_tokens": 256, "temperature": 0.2, "system_prompt": "You are the RequantAi Dispatcher TruckLM. Prioritize safe, profitable, compliant hauling operations. Never claim a tool or vehicle action ran unless the Permission Broker returns a verified result."},
    "learning": {"enabled": True, "auto_training_enabled": False, "training_timezone": "America/Los_Angeles", "training_hour": 1, "training_minute": 0, "occurrence_lookback_hours": 24, "auto_select_event_types": ["repair_success", "repair_failure", "dispatch_decision", "load_exception", "receiving_exception", "driver_correction", "operator_teach"], "auto_promote_model": False},
    "telemetry": {"simulation": True, "mqtt_enabled": False, "gps_enabled": True, "can_enabled": False, "obd_enabled": False, "reefer_enabled": False, "load_sensors_enabled": False, "cargo_vision_enabled": False},
}

def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        result[key] = _merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else value
    return result

def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path or os.getenv("REQUANT_CONFIG", "config.yaml"))
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    config = _merge(DEFAULTS, raw or {})
    if os.getenv("REQUANT_FORCE_SIMULATION") == "1":
        config["app"]["simulation"] = True
        config["telemetry"]["simulation"] = True
    validate_config(config)
    config["_config_path"] = str(config_path.resolve())
    return config

def validate_config(config: dict[str, Any]) -> None:
    port = config["app"]["port"]
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("app.port must be an integer from 1 to 65535")
    runtime = config["runtime"]
    if runtime["profile"] not in {"cpu_minimum", "cpu_balanced", "accelerated"}:
        raise ValueError("runtime.profile is invalid")
    if runtime["accelerator"] not in {"auto", "none", "hailo", "coral"}:
        raise ValueError("runtime.accelerator is invalid")
    if runtime["profile"] == "cpu_minimum" and runtime["require_accelerator"]:
        raise ValueError("cpu_minimum cannot require an accelerator")
    llm = config["local_llm"]
    if not isinstance(llm["timeout_seconds"], (int, float)) or llm["timeout_seconds"] <= 0:
        raise ValueError("local_llm.timeout_seconds must be positive")
    if not isinstance(llm["max_tokens"], int) or not 16 <= llm["max_tokens"] <= 4096:
        raise ValueError("local_llm.max_tokens must be from 16 to 4096")
    learning = config["learning"]
    if not 0 <= learning["training_hour"] <= 23 or not 0 <= learning["training_minute"] <= 59:
        raise ValueError("learning training time is invalid")
    if not 1 <= learning["occurrence_lookback_hours"] <= 168:
        raise ValueError("learning.occurrence_lookback_hours must be from 1 to 168")
    if learning.get("auto_promote_model"):
        raise ValueError("model candidates require evaluation and operator promotion")
