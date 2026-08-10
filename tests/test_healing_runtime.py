from pathlib import Path

import yaml

from nova.healing.runtime import HealingRuntime


def test_runtime_collects_evidence_without_enabling_execution(tmp_path: Path):
    (tmp_path / "data" / "logs").mkdir(parents=True)
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump({
        "app": {"host": "127.0.0.1", "simulation": True, "data_dir": str(tmp_path / "data")},
        "runtime": {"profile": "cpu_minimum", "accelerator": "none", "require_accelerator": False},
        "telemetry": {"simulation": True},
        "local_llm": {"enabled": False},
    }), encoding="utf-8")
    runtime = HealingRuntime(config)
    report = runtime.diagnose()
    assert report["execution_enabled"] is False
    assert any(finding["component"] == "local_llm" for finding in report["findings"])
