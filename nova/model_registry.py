from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelEntry:
    id: str
    name: str
    provider: str
    repo_id: str
    filename: str
    license: str
    parameters_billion: float
    quantization: str
    approx_size_bytes: int
    role: str
    approved: bool
    notes: str = ""
    llama_hf_ref: str | None = None
    download_url: str | None = None
    sha256: str | None = None


class ModelRegistry:
    """Read-only registry of approved RequantAi server-side GGUF models."""

    def __init__(self, path: str | Path | None = None):
        project_root = Path(__file__).resolve().parent.parent
        self.path = Path(path) if path else project_root / "models" / "registry.json"
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if raw.get("schema_version") != 1:
            raise ValueError("Unsupported RequantAi model registry schema")
        self.default_model = raw["default_model"]
        self._entries = {
            item["id"]: ModelEntry(
                id=item["id"],
                name=item["name"],
                provider=item["provider"],
                repo_id=item["repo_id"],
                filename=item["filename"],
                license=item["license"],
                parameters_billion=float(item["parameters_billion"]),
                quantization=item["quantization"],
                approx_size_bytes=int(item.get("approx_size_bytes", 0)),
                role=item["role"],
                approved=bool(item["approved"]),
                notes=item.get("notes", ""),
                llama_hf_ref=item.get("llama_hf_ref"),
                download_url=item.get("download_url"),
                sha256=item.get("sha256"),
            )
            for item in raw["models"]
        }
        if self.default_model not in self._entries:
            raise ValueError("Default model is missing from registry")
        if not self._entries[self.default_model].approved:
            raise ValueError("Default model must be approved")

    @staticmethod
    def require_server_role(runtime_role: str) -> None:
        if runtime_role != "server":
            raise PermissionError("Local AI model execution is authorized only on deployment.role=server")

    def get(self, model_id: str | None = None) -> ModelEntry:
        key = model_id or self.default_model
        try:
            return self._entries[key]
        except KeyError as exc:
            raise KeyError(f"Unknown RequantAi model: {key}") from exc

    def approved(self) -> list[ModelEntry]:
        return [entry for entry in self._entries.values() if entry.approved]

    def all(self) -> list[ModelEntry]:
        return list(self._entries.values())

    def install_target(self, model_id: str | None = None, *, runtime_role: str) -> Path:
        self.require_server_role(runtime_role)
        entry = self.get(model_id)
        return self.path.parent / entry.filename

    def llama_command(
        self,
        model_id: str | None = None,
        *,
        runtime_role: str,
        executable: str = "llama-server",
    ) -> list[str]:
        self.require_server_role(runtime_role)
        entry = self.get(model_id)
        if not entry.approved:
            raise PermissionError(f"Model is not approved for RequantAi install: {entry.id}")
        if entry.llama_hf_ref:
            return [executable, "-hf", entry.llama_hf_ref]
        return [executable, "-m", str(self.install_target(entry.id, runtime_role=runtime_role))]
