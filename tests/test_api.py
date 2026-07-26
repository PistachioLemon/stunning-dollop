def test_health_and_agents(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["local_llm"]["provider"] == "llama.cpp"
    agents = client.get("/api/agents").json()
    assert len(agents) == 7
    assert {agent["key"] for agent in agents} == {
        "companion", "medication", "safety", "home", "family_notes", "librarian",
        "package_guardian",
    }


def test_medication_workflow(client):
    created = client.post(
        "/api/medications",
        json={"name": "Vitamin D", "dosage": "1 tablet", "due_time": "09:00"},
    )
    assert created.status_code == 201
    medication_id = created.json()["id"]
    recorded = client.post(f"/api/medications/{medication_id}/record", json={"status": "taken"})
    assert recorded.status_code == 200
    medication = client.get("/api/medications").json()[0]
    assert medication["last_status"] == "taken"


def test_notes_and_routing(client):
    assert client.post("/api/notes", json={"category": "family", "body": "Call LaBrone"}).status_code == 201
    assert client.get("/api/notes").json()[0]["body"] == "Call LaBrone"
    routed = client.post("/api/chat", json={"text": "Did I take my medicine?"}).json()
    assert routed["agent"] == "medication"
    package = client.post("/api/chat", json={"text": "Find my package delivery"}).json()
    assert package["agent"] == "package_guardian"


def test_local_llm_missing_model_uses_safe_fallback(client):
    client.app.state.config["local_llm"]["enabled"] = True
    try:
        routed = client.post("/api/chat", json={"text": "Tell me hello"}).json()
    finally:
        client.app.state.config["local_llm"]["enabled"] = False
    assert routed["agent"] == "companion"
    assert routed["model"] == "agent_router_fallback"
    assert "GGUF model not found" in routed["model_error"]


def test_sos_requires_correct_pin(client):
    started = client.post("/api/sos", json={"reason": "test"}).json()
    wrong = client.post("/api/sos/cancel", json={"session_id": started["session_id"], "pin": "0000"})
    assert wrong.status_code == 403
    cancelled = client.post("/api/sos/cancel", json={"session_id": started["session_id"], "pin": "2468"})
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "cancelled"


def test_home_control_simulation(client):
    result = client.post(
        "/api/home/control",
        json={"domain": "light", "service": "turn_on", "entity_id": "light.living_room"},
    )
    assert result.status_code == 200
    assert result.json()["mode"] == "simulation"


def test_package_guardian_qr_workflow_and_replay_denial(client):
    created = client.post(
        "/api/packages",
        json={
            "carrier": "USPS",
            "tracking_code": "PKG12345",
            "recipient": "Mom",
            "courier_pin": "4321",
            "operator_pin": "8642",
        },
    )
    assert created.status_code == 201
    delivery_id = created.json()["id"]
    generated = client.post(
        f"/api/packages/{delivery_id}/access-code",
        json={"operator_pin": "8642", "code_type": "qr", "expires_minutes": 30},
    )
    assert generated.status_code == 201
    assert generated.json()["image_data_url"].startswith("data:image/png;base64,")

    guardian = client.app.state.package_guardian
    # The raw token is intentionally not returned by the public generator API.
    # Generate a second token through a test seam and capture it by temporarily
    # replacing the renderer-independent randomness source.
    import nova.package_guardian as module

    original = module.secrets.token_urlsafe
    module.secrets.token_urlsafe = lambda _: "test-scan-token-1234567890"
    try:
        second = guardian.generate_access_code(delivery_id, "8642", "code128", 30)
    finally:
        module.secrets.token_urlsafe = original
    assert second["image_data_url"].startswith("data:image/svg+xml;base64,")
    raw_code = "NOVA-PKG-test-scan-token-1234567890"
    scanned = client.post("/api/packages/scan", json={"code": raw_code})
    assert scanned.status_code == 200
    assert scanned.json()["verified"] is True
    assert scanned.json()["locker"]["state"] == "unlocked"
    replay = client.post("/api/packages/scan", json={"code": raw_code})
    assert replay.status_code == 403


def test_package_locker_manual_authorization(client):
    denied = client.post(
        "/api/locker/unlock",
        json={"pin": "0000", "duration_seconds": 5, "reason": "test"},
    )
    assert denied.status_code == 403
    unlocked = client.post(
        "/api/locker/unlock",
        json={"pin": "8642", "duration_seconds": 5, "reason": "test"},
    )
    assert unlocked.status_code == 200
    assert unlocked.json()["state"] == "unlocked"
    locked = client.post(
        "/api/locker/lock", json={"pin": "8642", "reason": "test complete"}
    )
    assert locked.status_code == 200
    assert locked.json()["state"] == "locked"
