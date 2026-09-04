from nova.healing.engine import SelfHealingEngine
from nova.healing.host_repairs import LowRiskHostActions, register_low_risk_repairs
from nova.healing.models import HealthFinding


def test_no_callbacks_registers_nothing():
    engine = SelfHealingEngine()
    assert register_low_risk_repairs(engine, LowRiskHostActions()) == []


def test_mqtt_reconnect_requires_sandbox_and_verifies():
    calls = []
    engine = SelfHealingEngine()
    engine.register_probe(
        "mqtt",
        lambda: HealthFinding(
            issue_id="mqtt:1",
            component="mqtt",
            signature="mqtt_disconnected",
            healthy=False,
        ),
    )
    actions = LowRiskHostActions(
        reconnect_mqtt=lambda: calls.append("reconnect"),
        verify_mqtt=lambda: True,
        sandbox_check=lambda recipe_id: recipe_id == "mqtt-reconnect-v1",
    )
    assert register_low_risk_repairs(engine, actions) == ["mqtt-reconnect-v1"]
    report = engine.run_cycle()
    assert calls == ["reconnect"]
    assert report["repairs"][0]["status"] == "healed"


def test_llama_restart_fails_closed_without_sandbox():
    calls = []
    engine = SelfHealingEngine()
    engine.register_probe(
        "llama",
        lambda: HealthFinding(
            issue_id="llama:1",
            component="llama",
            signature="llama_server_unavailable",
            healthy=False,
        ),
    )
    actions = LowRiskHostActions(
        restart_llama=lambda: calls.append("restart"),
        verify_llama=lambda: True,
        sandbox_check=lambda _: False,
    )
    register_low_risk_repairs(engine, actions)
    report = engine.run_cycle()
    assert calls == []
    assert report["repairs"][0]["status"] == "sandbox_failed"
