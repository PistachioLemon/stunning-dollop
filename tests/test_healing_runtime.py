from pathlib import Path

import yaml

from nova.healing.runtime import HealingRuntime


def test_runtime_collects_evidence_without_enabling_execution(tmp_path: Path, monkeypatch):
    project = tmp_path
    (project / "data" / "logs").mkdir(parents=True)
    (project / "docs").mkdir()
    (project / "capsules").mkdir()
    (project / "README.md").write_text("Nova repair notes", encoding="utf-8")
    (project / "docs" / "repair.md").write_text("GGUF model repair information", encoding="utf-8")
    (project / "data" / "logs" / "mqtt.log").write_text("mqtt connection refused", encoding="utf-8")
    (project / "config.sandbox.yaml").write_text(
        yaml.safe_dump(
            {
                "app": {"host": "127.0.0.1", "port": 8788, "simulation": True, "data_dir": "./sandbox-data"},
                "profile": {"emergency_pin": "2468"},
                "safety": {"countdown_seconds": 10, "outbound_emergency_enabled": False},
                "package_locker": {
                    "operator_pin": "8642",
                    "gpio_pin": 17,
                    "unlock_seconds": 5,
                    "max_unlock_seconds": 10,
                    "minimum_verification_confidence": 0.8,
                    "simulation": True,
                },
                "security_cameras": {"recording_policy": "events_only", "retention_days": 1, "minimum_event_confidence": 0.7},
                "local_llm": {"timeout_seconds": 45, "max_tokens": 256},
            }
        ),
        encoding="utf-8",
    )
    config = project / "config.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "app": {"host": "127.0.0.1", "port": 8787, "simulation": True, "data_dir": str(project / "data")},
                "profile": {"emergency_pin": "2468"},
                "safety": {"countdown_seconds": 15, "outbound_emergency_enabled": False},
                "package_locker": {
                    "operator_pin": "8642",
                    "gpio_pin": 17,
                    "unlock_seconds": 20,
                    "max_unlock_seconds": 60,
                    "minimum_verification_confidence": 0.8,
                    "simulation": True,
                },
                "security_cameras": {"recording_policy": "events_only", "retention_days": 7, "minimum_event_confidence": 0.7},
                "local_llm": {"enabled": False, "timeout_seconds": 45, "max_tokens": 256},
            }
        ),
        encoding="utf-8",
    )

    # HealingRuntime derives project_root from the installed package in normal operation.
    # For this isolated test, substitute the temporary fixture root.
    monkeypatch.setattr("nova.healing.runtime.Path.resolve", Path.resolve)
    runtime = HealingRuntime(config)
    runtime.project_root = project
    report = runtime.diagnose()
    assert report["execution_enabled"] is False
    assert any(finding["component"] == "local_llm" for finding in report["findings"])
