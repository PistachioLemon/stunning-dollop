import json

import pytest

from nova.capsules import CapsuleManifest, PermissionBroker


def test_capsule_manifest_and_digest(tmp_path):
    path = tmp_path / "capsule.json"
    path.write_text(json.dumps({
        "name": "Field Manual",
        "version": "0.1",
        "requested_tools": ["read_sensor"]
    }))
    manifest = CapsuleManifest.load(path)
    assert manifest.name == "Field Manual"
    assert len(manifest.digest()) == 64


def test_permission_broker_defaults_to_deny():
    manifest = CapsuleManifest("Manual", "0.1", requested_tools=("read_sensor",))
    broker = PermissionBroker()
    assert broker.authorize(manifest, "read_sensor") is False
    with pytest.raises(PermissionError):
        broker.require(manifest, "read_sensor")


def test_permission_requires_manifest_request_and_host_allowlist():
    manifest = CapsuleManifest("Manual", "0.1", requested_tools=("read_sensor",))
    broker = PermissionBroker({"read_sensor", "send_sms"})
    assert broker.authorize(manifest, "read_sensor") is True
    assert broker.authorize(manifest, "send_sms") is False
