from __future__ import annotations

import copy
import hashlib
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from nova.config import DEFAULTS, validate_config
from nova.shared import CommandEnvelope
from nova.truck_node.journal import EventJournal
from nova.truck_node.recovery import RecoveryManifest, sign_manifest, verify_manifest_signature
from nova.truck_node.runtime import TruckEdgeRuntime
from nova.truck_node.security_guard import DeviceIdentity, SecurityGuard
from nova.truck_node.state import DegradedMode
from nova.truck_node.transport import MqttPolicy, telemetry_topic


def test_journal_survives_restart_and_acknowledges(tmp_path):
    path = tmp_path / "events.jsonl"
    edge = TruckEdgeRuntime("truck-9", journal_path=path)
    first = edge.record_telemetry("gps", {"lat": 47.6})
    second = edge.record_telemetry("reefer", {"fahrenheit": 36.0})

    restarted = TruckEdgeRuntime("truck-9", journal_path=path)
    assert restarted.buffered_events() == [first, second]
    assert restarted.acknowledge_through(first.event_id) == 1
    assert restarted.buffered_events() == [second]


def test_journal_ignores_torn_tail(tmp_path):
    path = tmp_path / "events.jsonl"
    edge = TruckEdgeRuntime("truck-10", journal_path=path)
    event = edge.record_telemetry("gps", {"lat": 47.6})
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"sequence":2,"event":')

    journal = EventJournal(path)
    assert [record.event for record in journal.pending()] == [event]


def test_recovery_mode_blocks_remote_commands():
    edge = TruckEdgeRuntime("truck-11")
    edge.register_action("read_gps", lambda args: {"lat": 47.6})
    edge.set_mode(DegradedMode.RECOVERY_MODE, True)
    result = edge.execute(CommandEnvelope(action="read_gps"))
    assert result.ok is False
    assert result.status == "recovery_mode"


def test_security_guard_scopes_topics_and_blocks_vehicle_writes():
    fingerprint = "ab" * 32
    guard = SecurityGuard(
        DeviceIdentity("truck-12", fingerprint),
        allowed_topic_prefix="requantai/trucks/truck-12",
    )
    assert guard.authorize_topic("requantai/trucks/truck-12/telemetry/gps", write=True)
    assert not guard.authorize_topic("requantai/trucks/truck-13/telemetry/gps", write=True)
    assert not guard.authorize_topic("requantai/trucks/truck-12/can_write", write=True)


def test_mqtt_policy_requires_tls_and_valid_expiry():
    MqttPolicy("requantai-server.local").validate()
    with pytest.raises(ValueError, match="requires TLS"):
        MqttPolicy("requantai-server.local", tls_required=False).validate()
    with pytest.raises(ValueError, match="session expiry"):
        MqttPolicy(
            "requantai-server.local",
            session_expiry_seconds=60,
            message_expiry_seconds=120,
        ).validate()
    assert telemetry_topic("truck-12", "reefer/temp") == "requantai/trucks/truck-12/telemetry/reefer_temp"


def test_recovery_manifest_rejects_tampering_and_rollback():
    key = b"k" * 32
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    image_hash = hashlib.sha256(b"image").hexdigest()
    unsigned = RecoveryManifest(
        version=3,
        slot="B",
        image_sha256=image_hash,
        expires_at=expires,
        minimum_version=2,
    )
    signed = replace(unsigned, signature=sign_manifest(unsigned, key))
    signed.validate(current_version=2)
    assert verify_manifest_signature(signed, key)

    tampered = replace(signed, version=4)
    assert not verify_manifest_signature(tampered, key)

    rollback = replace(unsigned, version=1, signature="00" * 32)
    with pytest.raises(ValueError, match="rollback"):
        rollback.validate(current_version=2)


def test_production_truck_mqtt_requires_identity_fingerprint():
    config = copy.deepcopy(DEFAULTS)
    config["deployment"]["role"] = "truck_edge"
    config["runtime"]["accelerator"] = "none"
    config["local_llm"]["enabled"] = False
    config["learning"]["enabled"] = False
    config["learning"]["auto_training_enabled"] = False
    config["app"]["simulation"] = False
    config["telemetry"]["mqtt_enabled"] = True
    config["mqtt"]["tls_required"] = True
    config["security_guard"]["certificate_fingerprint"] = ""
    with pytest.raises(ValueError, match="certificate fingerprint"):
        validate_config(config)

    config["security_guard"]["certificate_fingerprint"] = "cd" * 32
    validate_config(config)
