from pathlib import Path

from nova.healing.engine import SelfHealingEngine
from nova.healing.integrations import (
    KnowledgeSource,
    RepairEvidenceLoader,
    local_llm_probe,
    log_signature_probe,
    protected_sandbox_probe,
    register_default_evidence,
)
from nova.healing.librarian import RepairLibrarian


class FakeLLM:
    def __init__(self, *, enabled=True, model_present=True):
        self._status = {
            "enabled": enabled,
            "provider": "llama.cpp",
            "model_path": "/tmp/trucklm.gguf",
            "model_present": model_present,
            "server_url": "http://127.0.0.1:8080",
            "fallback": "agent_router",
        }

    def status(self):
        return dict(self._status)


def test_local_llm_missing_model_is_unhealthy():
    finding = local_llm_probe(FakeLLM(model_present=False))
    assert finding.healthy is False
    assert finding.signature == "gguf_model_missing"


def test_log_probe_detects_known_signature(tmp_path: Path):
    log = tmp_path / "dispatcher.log"
    log.write_text("worker ready\nERROR mqtt connection refused\n", encoding="utf-8")
    finding = log_signature_probe(
        name="mqtt",
        component="mqtt",
        path=log,
        signatures={"mqtt_connection_refused": r"mqtt connection refused"},
    )
    assert finding.healthy is False
    assert finding.signature == "mqtt_connection_refused"


def test_sandbox_probe_fails_closed():
    unsafe = protected_sandbox_probe({"app": {"host": "0.0.0.0", "simulation": True}})
    assert unsafe.healthy is False
    assert unsafe.signature == "sandbox_not_isolated"

    safe = protected_sandbox_probe(
        {
            "app": {"host": "127.0.0.1", "simulation": True},
            "telemetry": {"simulation": True},
        }
    )
    assert safe.healthy is True


def test_evidence_loader_does_not_ingest_unsupported_files(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "repair.md").write_text("restart the local service", encoding="utf-8")
    (docs / "payload.sh").write_text("echo should-not-be-ingested", encoding="utf-8")
    librarian = RepairLibrarian()
    ids = RepairEvidenceLoader(librarian).ingest_source(KnowledgeSource(docs, trust=80))
    assert len(ids) == 1


def test_register_default_evidence_wires_probe_and_docs(tmp_path: Path):
    (tmp_path / "README.md").write_text("RequantAi local repair documentation", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "llm.md").write_text("GGUF model troubleshooting", encoding="utf-8")
    (tmp_path / "capsules").mkdir()
    librarian = RepairLibrarian()
    engine = SelfHealingEngine(enabled=False)
    result = register_default_evidence(
        engine=engine,
        librarian=librarian,
        local_llm=FakeLLM(),
        project_root=tmp_path,
    )
    assert result["knowledge_items"] == 2
    report = engine.run_cycle()
    assert report["findings"][0]["component"] == "local_llm"
