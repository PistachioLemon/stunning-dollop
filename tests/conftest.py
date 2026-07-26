from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from nova.app import create_app


@pytest.fixture()
def client(tmp_path: Path):
    config = {
        "app": {"data_dir": str(tmp_path), "simulation": True},
        "profile": {"emergency_pin": "2468"},
        "safety": {"countdown_seconds": 30},
    }
    config_path = tmp_path / "test-config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    app = create_app(str(config_path))
    with TestClient(app) as test_client:
        yield test_client

