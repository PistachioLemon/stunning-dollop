import json
from pathlib import Path

import pytest

from nova.model_registry import ModelRegistry


def test_default_server_model_is_approved():
    registry = ModelRegistry()
    entry = registry.get()
    assert entry.approved is True
    assert entry.id == "smollm2-360m-instruct-q4_k_m"
    assert entry.role == "server_trucklm_compact"
    assert entry.quantization == "Q4_K_M"


def test_registry_separates_approved_and_unapproved_server_models():
    registry = ModelRegistry()
    approved = {entry.id for entry in registry.approved()}
    assert "smollm2-360m-instruct-q4_k_m" in approved
    assert "qwen2.5-1.5b-instruct-q4_k_m" in approved
    assert "smollm2-1.7b-instruct-q4_k_m" not in approved


def test_truck_edge_cannot_build_model_launch_command():
    registry = ModelRegistry()
    with pytest.raises(PermissionError, match="deployment.role=server"):
        registry.llama_command(runtime_role="truck_edge")


def test_server_can_build_approved_model_launch_command():
    registry = ModelRegistry()
    command = registry.llama_command(runtime_role="server")
    assert command[0] == "llama-server"


def test_unapproved_model_cannot_build_launch_command():
    registry = ModelRegistry()
    with pytest.raises(PermissionError):
        registry.llama_command("smollm2-1.7b-instruct-q4_k_m", runtime_role="server")


def test_unknown_model_is_rejected():
    registry = ModelRegistry()
    with pytest.raises(KeyError):
        registry.llama_command("unknown-model", runtime_role="server")


def test_registry_rejects_unapproved_default(tmp_path: Path):
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "default_model": "test",
        "models": [{
            "id": "test",
            "name": "Test",
            "provider": "Test",
            "repo_id": "test/test",
            "filename": "test.gguf",
            "llama_hf_ref": "test/test:Q4_K_M",
            "license": "test",
            "parameters_billion": 1,
            "quantization": "Q4_K_M",
            "approx_size_bytes": 1,
            "role": "server_experimental",
            "approved": False
        }]
    }), encoding="utf-8")
    with pytest.raises(ValueError):
        ModelRegistry(path)
