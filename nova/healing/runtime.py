from __future__ import annotations

from pathlib import Path

from nova.config import load_config
from nova.local_llm import LocalLLM

from .engine import SelfHealingEngine
from .integrations import (
    log_signature_probe,
    protected_sandbox_probe,
    register_default_evidence,
)
from .librarian import RepairLibrarian
from .memory import RepairMemory


DEFAULT_LOG_SIGNATURES = {
    "nova": {
        "python_traceback": r"Traceback \(most recent call last\)",
        "permission_denied": r"Permission(?:Error| denied)",
        "database_locked": r"database is locked",
    },
    "llama": {
        "llama_server_unavailable": r"(?:llama\.cpp|server).*(?:unavailable|connection refused|timed out)",
        "gguf_load_failed": r"(?:failed|error).*(?:gguf|model).*(?:load|open)",
        "out_of_memory": r"(?:out of memory|cannot allocate memory|bad_alloc)",
    },
    "mqtt": {
        "mqtt_connection_refused": r"mqtt.*(?:connection refused|not authorized|unreachable)",
        "mqtt_disconnected": r"mqtt.*(?:disconnected|connection lost|broken pipe)",
    },
}


class HealingRuntime:
    """Read-mostly integration layer between Nova and the self-healing prototype.

    The runtime collects evidence and proposes repairs. It does not add repair
    execution handlers by itself, so merely enabling diagnostics cannot execute
    commands or mutate host services.
    """

    def __init__(self, config_path: str | Path = "config.yaml"):
        self.config = load_config(config_path)
        self.project_root = Path(__file__).resolve().parent.parent.parent
        data_dir = Path(self.config["app"]["data_dir"])
        if not data_dir.is_absolute():
            data_dir = self.project_root / data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = data_dir

        self.memory = RepairMemory(data_dir / "repair_history.db")
        self.librarian = RepairLibrarian(data_dir / "repair_knowledge.db")
        # Diagnostics run even while repair execution remains disabled.
        self.engine = SelfHealingEngine(memory=self.memory, enabled=False)
        self.local_llm = LocalLLM(self.config)

        self.bootstrap = register_default_evidence(
            engine=self.engine,
            librarian=self.librarian,
            local_llm=self.local_llm,
            project_root=self.project_root,
            data_dir=data_dir,
        )
        self._register_log_probes()
        self._register_sandbox_probe()

    def _register_log_probes(self) -> None:
        log_dir = self.data_dir / "logs"
        for name, signatures in DEFAULT_LOG_SIGNATURES.items():
            path = log_dir / f"{name}.log"
            self.engine.register_probe(
                f"log:{name}",
                lambda name=name, path=path, signatures=signatures: log_signature_probe(
                    name=name,
                    component=name,
                    path=path,
                    signatures=signatures,
                ),
            )

    def _register_sandbox_probe(self) -> None:
        sandbox_path = self.project_root / "config.sandbox.yaml"
        if sandbox_path.is_file():
            sandbox_config = load_config(sandbox_path)
            self.engine.register_probe("protected_sandbox", lambda: protected_sandbox_probe(sandbox_config))

    def diagnose(self) -> dict:
        report = self.engine.run_cycle()
        proposals: dict[str, list[dict]] = {}
        for finding in self.engine.diagnose():
            if finding.healthy:
                continue
            proposals[finding.issue_id] = self.librarian.propose(finding)
        report["repair_proposals"] = proposals
        report["knowledge_items_bootstrapped"] = self.bootstrap["knowledge_items"]
        report["execution_enabled"] = False
        return report
