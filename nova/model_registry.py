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
    llama_hf_ref: str
    license: str
    parameters_billion: float
    quantization: str
    approx_size_bytes: int
    role: str
    approved: bool
    notes: str = ""


class ModelRegistry:
    """Read-only registry of Nova-approved local GGUF models."""

    def __init__(self, path: str | Path | None = None):
        project_root = Path(__file__).resolve().parent.parent
        self.path = Path(path) if path else project_root / "models" / "registry.json"
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if raw.get("schema_version") != 1:
            raise ValueError("Unsupported Nova model registry schema")
        self.default_model = raw["default_model"]
        self._entries = {
            item["id"]: ModelEntry(
                id=item["id"],
                name=item["name"],
                provider=item["provider"],
                repo_id=item["repo_id"],
                filename=item["filename"],
                llama_hf_ref=item["llama_hf_ref"],
                license=item["license"],
                parameters_billion=float(item["parameters_billion"]),
                quantization=item["quantization"],
                approx_size_bytes=int(item["approx_size_bytes"]),
                role=item["role"],
                approved=bool(item["approved"]),
                notes=item.get("notes", ""),
            )
            for item in raw["models"]
        }
        if self.default_model not in self._entries:
            raise ValueError("Default model is missing from registry")
        if not self._entries[self.default_model].approved:
            raise ValueError("Default model must be approved")

    def get(self, model_id: str | None = None) -> ModelEntry:
        key = model_id or self.default_model
        try:
            return self._entries[key]
        except KeyError as exc:
            raise KeyError(f"Unknown Nova model: {key}") from exc

    def approved(self) -> list[ModelEntry]:
        return [entry for entry in self._entries.values() if entry.approved]

    def all(self) -> list[ModelEntry]:
        return list(self._entries.values())

    def install_target(self, model_id: str | None = None) -> Path:
        entry = self.get(model_id)
        return self.path.parent / entry.filename

    def llama_command(self, model_id: str | None = None, *, executable: str = "llama-server") -> list[str]:
        entry = self.get(model_id)
        if not entry.approved:
            raise PermissionError(f"Model is not approved for Nova install: {entry.id}")
        return [executable, "-hf", entry.llama_hf_ref]
