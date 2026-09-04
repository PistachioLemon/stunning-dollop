from pathlib import Path


def test_cpu_baseline_health_and_agents(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert body["name"] == "RequantAi Dispatcher"
    assert body["runtime"]["profile"] == "cpu_minimum"
    assert body["runtime"]["require_accelerator"] is False
    assert body["runtime"]["cpu_only_ready"] is True
    assert body["local_llm"]["provider"] == "llama.cpp"
    agents = client.get("/api/agents").json()
    assert {agent["key"] for agent in agents} == {
        "dispatcher", "trucklm", "telemetry", "cargo_vision", "compliance",
        "permission_broker", "librarian", "repair_librarian", "self_healing", "learning",
    }


def test_hauling_agent_routing(client):
    assert client.post("/api/chat", json={"text": "rank this load for profit"}).json()["agent"] == "dispatcher"
    assert client.post("/api/chat", json={"text": "check reefer telemetry"}).json()["agent"] == "telemetry"
    assert client.post("/api/chat", json={"text": "verify cargo securement"}).json()["agent"] == "cargo_vision"
    assert client.post("/api/chat", json={"text": "check HOS"}).json()["agent"] == "compliance"


def test_local_llm_missing_model_uses_safe_fallback(client):
    client.app.state.config["local_llm"]["enabled"] = True
    try:
        routed = client.post("/api/chat", json={"text": "explain detention pay"}).json()
    finally:
        client.app.state.config["local_llm"]["enabled"] = False
    assert routed["model"] == "deterministic_fallback"
    assert "GGUF model not found" in routed["model_error"]


def test_simulated_truck_telemetry_round_trip(client):
    response = client.post("/api/trucks/telemetry", json={
        "truck_id": "solo-01", "latitude": 47.6062, "longitude": -122.3321,
        "speed_mph": 42, "fuel_percent": 73, "hos_drive_minutes_remaining": 310,
        "mqtt_connected": True, "cargo_secure": True,
    })
    assert response.status_code == 202
    truck = client.get("/api/trucks").json()[0]
    assert truck["truck_id"] == "solo-01"
    assert truck["cargo_secure"] is True


def test_dispatch_profit_evaluation_is_operator_gated(client):
    result = client.post("/api/dispatch/evaluate", json={
        "truck_id": "solo-01", "load_id": "SEA-PDX-001", "gross_revenue": 1800,
        "estimated_cost": 900, "deadhead_miles": 20, "loaded_miles": 175, "risk_penalty": 100,
    })
    assert result.status_code == 200
    body = result.json()
    assert body["estimated_profit"] == 800
    assert body["recommendation"] == "review"
    assert body["requires_operator_approval"] is True


def test_protected_sandbox_configuration():
    from nova.config import load_config
    config = load_config(Path(__file__).resolve().parent.parent / "config.sandbox.yaml")
    assert config["app"]["host"] == "127.0.0.1"
    assert config["app"]["simulation"] is True
    assert config["runtime"] == {"profile": "cpu_minimum", "accelerator": "none", "require_accelerator": False}
    assert config["telemetry"]["simulation"] is True
