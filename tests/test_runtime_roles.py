from __future__ import annotations

import copy

import pytest

from nova.config import DEFAULTS, validate_config
from nova.server import ServerRuntime
from nova.shared import CommandEnvelope
from nova.truck_node import TruckEdgeRuntime


def test_truck_edge_rejects_ai_features():
    config = copy.deepcopy(DEFAULTS)
    config["deployment"]["role"] = "truck_edge"
    config["local_llm"]["enabled"] = True
    config["learning"]["enabled"] = False
    with pytest.raises(ValueError, match="AI belongs on the server"):
        validate_config(config)


def test_truck_edge_profile_accepts_ai_disabled():
    config = copy.deepcopy(DEFAULTS)
    config["deployment"]["role"] = "truck_edge"
    config["runtime"]["accelerator"] = "none"
    config["local_llm"]["enabled"] = False
    config["learning"]["enabled"] = False
    config["learning"]["auto_training_enabled"] = False
    validate_config(config)


def test_edge_named_action_and_approval_gate():
    edge = TruckEdgeRuntime("truck-7")
    edge.register_action("read_gps", lambda args: {"lat": 47.6, "lon": -122.3})
    edge.register_action("can_write", lambda args: {"sent": True}, restricted=True)

    gps = edge.execute(CommandEnvelope(action="read_gps"))
    denied = edge.execute(CommandEnvelope(action="can_write"))
    approved = edge.execute(CommandEnvelope(action="can_write"), approved=True)

    assert gps.ok is True
    assert denied.ok is False
    assert denied.status == "approval_required"
    assert approved.ok is True
    assert edge.health()["ai_enabled"] is False


def test_edge_buffers_telemetry_during_disconnect():
    edge = TruckEdgeRuntime("truck-8")
    event = edge.record_telemetry("reefer_temperature", {"fahrenheit": 36.5})
    assert edge.buffered_events() == [event]
    assert edge.acknowledge_through(event.event_id) == 1
    assert edge.buffered_events() == []


def test_server_runtime_rejects_truck_edge_role():
    config = copy.deepcopy(DEFAULTS)
    config["deployment"]["role"] = "truck_edge"
    config["learning"]["enabled"] = False
    config["runtime"]["accelerator"] = "none"
    with pytest.raises(ValueError, match="deployment.role=server"):
        ServerRuntime(config)
