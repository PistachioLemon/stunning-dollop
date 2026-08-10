def test_healing_status_is_read_only_and_structured(client):
    response = client.get("/api/healing/status")
    assert response.status_code == 200
    data = response.json()
    assert data["execution_enabled"] is False
    assert isinstance(data["findings"], list)
    assert isinstance(data["repair_proposals"], dict)
    assert "knowledge_items_bootstrapped" in data


def test_health_endpoint_advertises_gated_self_healing(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["self_healing"] == {
        "diagnostics_enabled": True,
        "execution_enabled": False,
    }
