from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MqttPolicy:
    broker_host: str
    broker_port: int = 8883
    keepalive_seconds: int = 30
    session_expiry_seconds: int = 86400
    message_expiry_seconds: int = 3600
    qos: int = 1
    tls_required: bool = True

    def validate(self) -> None:
        if not self.broker_host.strip():
            raise ValueError("broker_host is required")
        if not 1 <= self.broker_port <= 65535:
            raise ValueError("broker_port is invalid")
        if self.keepalive_seconds < 10:
            raise ValueError("keepalive_seconds must be at least 10")
        if self.session_expiry_seconds < self.message_expiry_seconds:
            raise ValueError("session expiry must be >= message expiry")
        if self.qos not in {1, 2}:
            raise ValueError("telemetry qos must be 1 or 2")
        if not self.tls_required:
            raise ValueError("truck MQTT transport requires TLS")


def topic_root(node_id: str) -> str:
    clean = node_id.strip().replace("/", "-")
    if not clean:
        raise ValueError("node_id is required")
    return f"requantai/trucks/{clean}"


def telemetry_topic(node_id: str, kind: str) -> str:
    clean_kind = kind.strip().replace("/", "_") or "event"
    return f"{topic_root(node_id)}/telemetry/{clean_kind}"


def command_topic(node_id: str) -> str:
    return f"{topic_root(node_id)}/commands"


def result_topic(node_id: str) -> str:
    return f"{topic_root(node_id)}/results"


def heartbeat_topic(node_id: str) -> str:
    return f"{topic_root(node_id)}/health/heartbeat"
