from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml


DEFAULTS: dict[str, Any] = {
    "app": {
        "name": "Nova",
        "host": "0.0.0.0",
        "port": 8787,
        "timezone": "America/Los_Angeles",
        "simulation": True,
        "data_dir": "./data",
    },
    "profile": {
        "display_name": "Mom",
        "emergency_pin": "2468",
        "medication_grace_minutes": 30,
    },
    "safety": {
        "countdown_seconds": 15,
        "require_confirmation": True,
        "outbound_emergency_enabled": False,
        "emergency_provider": "disabled",
        "trusted_contacts": [],
    },
    "presence": {
        "enabled": True,
        "camera_index": 0,
        "dim_after_seconds": 90,
        "sleep_after_seconds": 300,
    },
    "voice": {
        "enabled": False,
        "wake_phrase": "hey nova",
        "whisper_model": "tiny.en",
        "piper_command": "piper",
    },
    "local_llm": {
        "enabled": False,
        "server_url": "http://127.0.0.1:8080",
        "model_path": "./models/nova-assistant.gguf",
        "timeout_seconds": 45,
        "max_tokens": 256,
        "temperature": 0.3,
        "system_prompt": (
            "You are Nova, a concise offline home assistant. Never claim that an "
            "emergency call, door unlock, medication record, message, or device "
            "action occurred unless Nova's verified tools report that it occurred."
        ),
    },
    "home_assistant": {
        "enabled": False,
        "base_url": "http://homeassistant.local:8123",
        "token_env": "NOVA_HA_TOKEN",
    },
    "package_locker": {
        "enabled": True,
        "simulation": True,
        "operator_pin": "8642",
        "gpio_pin": 17,
        "active_high": True,
        "unlock_seconds": 20,
        "max_unlock_seconds": 60,
        "require_courier_pin": True,
        "minimum_verification_confidence": 0.80,
        "auto_unlock_verified_delivery": True,
    },
    "security_cameras": {
        "enabled": True,
        "simulation": True,
        "recording_policy": "events_only",
        "retention_days": 7,
        "minimum_event_confidence": 0.70,
    },
}


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path or os.getenv("NOVA_CONFIG", "config.yaml"))
    raw: dict[str, Any] = {}
    if config_path.exists():
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    config = _merge(DEFAULTS, raw)
    if os.getenv("NOVA_FORCE_SIMULATION") == "1":
        config["app"]["simulation"] = True
        config["package_locker"]["simulation"] = True
    validate_config(config)
    config["_config_path"] = str(config_path.resolve())
    return config


def validate_config(config: dict[str, Any]) -> None:
    port = config["app"]["port"]
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("app.port must be an integer from 1 to 65535")
    pin = str(config["profile"]["emergency_pin"])
    if len(pin) < 4 or not pin.isdigit():
        raise ValueError("profile.emergency_pin must contain at least four digits")
    countdown = config["safety"]["countdown_seconds"]
    if not isinstance(countdown, int) or countdown < 5:
        raise ValueError("safety.countdown_seconds must be at least 5")
    if config["safety"]["outbound_emergency_enabled"]:
        if config["safety"]["emergency_provider"] == "disabled":
            raise ValueError("An emergency provider is required when outbound alerts are enabled")
        if not config["safety"]["trusted_contacts"]:
            raise ValueError("At least one trusted contact is required for outbound alerts")
    locker = config["package_locker"]
    locker_pin = str(locker["operator_pin"])
    if len(locker_pin) < 4 or not locker_pin.isdigit():
        raise ValueError("package_locker.operator_pin must contain at least four digits")
    if not isinstance(locker["gpio_pin"], int) or not 2 <= locker["gpio_pin"] <= 27:
        raise ValueError("package_locker.gpio_pin must be a BCM GPIO number from 2 to 27")
    unlock_seconds = locker["unlock_seconds"]
    maximum = locker["max_unlock_seconds"]
    if not isinstance(unlock_seconds, int) or not isinstance(maximum, int):
        raise ValueError("package locker unlock durations must be integers")
    if not 5 <= unlock_seconds <= maximum <= 300:
        raise ValueError("package locker durations must satisfy 5 <= unlock <= max <= 300")
    confidence = locker["minimum_verification_confidence"]
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ValueError("package_locker.minimum_verification_confidence must be from 0 to 1")
    llm = config["local_llm"]
    if not isinstance(llm["timeout_seconds"], (int, float)) or llm["timeout_seconds"] <= 0:
        raise ValueError("local_llm.timeout_seconds must be positive")
    if not isinstance(llm["max_tokens"], int) or not 16 <= llm["max_tokens"] <= 4096:
        raise ValueError("local_llm.max_tokens must be from 16 to 4096")
    cameras = config["security_cameras"]
    if cameras["recording_policy"] not in {"off", "events_only", "continuous"}:
        raise ValueError("security_cameras.recording_policy is invalid")
    if not isinstance(cameras["retention_days"], int) or not 0 <= cameras["retention_days"] <= 365:
        raise ValueError("security_cameras.retention_days must be from 0 to 365")
    camera_confidence = cameras["minimum_event_confidence"]
    if not isinstance(camera_confidence, (int, float)) or not 0 <= camera_confidence <= 1:
        raise ValueError("security_cameras.minimum_event_confidence must be from 0 to 1")
