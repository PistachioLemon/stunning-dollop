from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any

import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties


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


class Mqtt5Transport:
    """MQTT 5 client with mandatory TLS/mTLS and persistent broker sessions."""

    def __init__(
        self,
        node_id: str,
        policy: MqttPolicy,
        *,
        ca_file: str | Path,
        cert_file: str | Path,
        key_file: str | Path,
        on_command: Callable[[dict[str, Any]], None] | None = None,
    ):
        policy.validate()
        self.node_id = node_id
        self.policy = policy
        self.on_command = on_command
        self._connected = False
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=node_id,
            protocol=mqtt.MQTTv5,
        )
        self._client.tls_set(
            ca_certs=str(ca_file),
            certfile=str(cert_file),
            keyfile=str(key_file),
        )
        self._client.tls_insecure_set(False)
        self._client.on_connect = self._handle_connect
        self._client.on_disconnect = self._handle_disconnect
        self._client.on_message = self._handle_message
        self._client.reconnect_delay_set(min_delay=1, max_delay=60)

    @property
    def connected(self) -> bool:
        return self._connected

    def _handle_connect(self, client, userdata, flags, reason_code, properties) -> None:
        self._connected = int(reason_code) == 0
        if self._connected:
            client.subscribe(command_topic(self.node_id), qos=self.policy.qos)

    def _handle_disconnect(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        self._connected = False

    def _handle_message(self, client, userdata, message) -> None:
        if message.topic != command_topic(self.node_id) or self.on_command is None:
            return
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        if isinstance(payload, dict):
            self.on_command(payload)

    def connect(self) -> None:
        properties = Properties(PacketTypes.CONNECT)
        properties.SessionExpiryInterval = self.policy.session_expiry_seconds
        self._client.connect(
            self.policy.broker_host,
            self.policy.broker_port,
            keepalive=self.policy.keepalive_seconds,
            clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY,
            properties=properties,
        )
        self._client.loop_start()

    def disconnect(self) -> None:
        self._client.disconnect()
        self._client.loop_stop()
        self._connected = False

    def publish_json(self, topic: str, payload: dict[str, Any]) -> int:
        properties = Properties(PacketTypes.PUBLISH)
        properties.MessageExpiryInterval = self.policy.message_expiry_seconds
        info = self._client.publish(
            topic,
            json.dumps(payload, separators=(",", ":"), sort_keys=True),
            qos=self.policy.qos,
            retain=False,
            properties=properties,
        )
        return int(info.rc)
