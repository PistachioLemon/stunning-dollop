from nova.healing.librarian import RepairLibrarian
from nova.healing.models import HealthFinding, RiskLevel


def test_exact_signature_and_component_rank_first():
    librarian = RepairLibrarian()
    librarian.ingest_text(
        source="local-manual",
        title="MQTT reconnect procedure",
        body="If the broker connection drops, reconnect the client and verify heartbeat.",
        trust=90,
        component="mqtt",
        signature="connection_lost",
        proposed_action="restart_mqtt_client",
        risk=RiskLevel.LOW,
    )
    librarian.ingest_text(
        source="generic-notes",
        title="Network notes",
        body="Check general network connectivity.",
        trust=80,
    )

    finding = HealthFinding(
        issue_id="mqtt-1",
        component="mqtt",
        signature="connection_lost",
        healthy=False,
        details={"error": "broker unavailable"},
    )
    hits = librarian.search(finding)
    assert hits[0]["title"] == "MQTT reconnect procedure"
    assert hits[0]["proposed_action"] == "restart_mqtt_client"


def test_low_trust_items_are_not_proposed():
    librarian = RepairLibrarian()
    librarian.ingest_text(
        source="unverified-note",
        title="Possible repair",
        body="Try deleting configuration and reinstalling everything.",
        trust=20,
        component="camera",
        signature="startup_failed",
        proposed_action="destructive_reinstall",
        risk=RiskLevel.HIGH,
    )
    finding = HealthFinding("cam-1", "camera", "startup_failed", False)
    assert librarian.propose(finding, minimum_trust=70) == []


def test_librarian_never_executes_actions():
    librarian = RepairLibrarian()
    librarian.ingest_text(
        source="vendor-manual",
        title="Service restart",
        body="Restart the service after checking configuration.",
        trust=95,
        component="llama",
        signature="server_unavailable",
        proposed_action="restart_llama_server",
        risk=RiskLevel.LOW,
    )
    finding = HealthFinding("llm-1", "llama", "server_unavailable", False)
    proposal = librarian.propose(finding)[0]
    assert proposal["proposed_action"] == "restart_llama_server"
    assert not hasattr(librarian, "execute")
