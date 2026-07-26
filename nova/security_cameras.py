from __future__ import annotations

from typing import Any

from .database import Database


class SecurityCameraService:
    """Local-first camera registry and safety control plane.

    Nova stores camera metadata and events, but never stores credentials or
    proxies a live stream through this service.
    """

    ALLOWED_KINDS = {"indoor", "outdoor", "doorbell", "driveway", "locker"}

    def __init__(self, database: Database, config: dict[str, Any]):
        self.database = database
        self.config = config["security_cameras"]

    def status(self) -> dict[str, Any]:
        cameras = self.database.security_cameras()
        return {
            "enabled": bool(self.config["enabled"]),
            "mode": "simulation" if self.config["simulation"] else "live",
            "privacy_mode": self.database.camera_privacy_mode(),
            "camera_count": len(cameras),
            "online_count": sum(camera["status"] == "online" for camera in cameras),
            "recording_policy": self.config["recording_policy"],
        }

    def add_camera(
        self, name: str, kind: str, room: str, connection: str, stream_url: str | None
    ) -> int:
        if kind not in self.ALLOWED_KINDS:
            raise ValueError("Unsupported security camera type")
        if connection not in {"simulation", "home_assistant", "rtsp", "onvif"}:
            raise ValueError("Unsupported camera connection")
        if connection == "simulation":
            stream_url = None
        camera_id = self.database.add_security_camera(
            name=name,
            kind=kind,
            room=room,
            connection=connection,
            stream_url=stream_url,
            status="online" if connection == "simulation" else "configured",
        )
        self.database.event(
            "security_camera_added",
            {"camera_id": camera_id, "name": name, "connection": connection},
        )
        return camera_id

    def set_privacy(self, enabled: bool) -> dict[str, Any]:
        self.database.set_camera_privacy_mode(enabled)
        self.database.event("camera_privacy_changed", {"enabled": enabled})
        return self.status()

    def record_event(
        self, camera_id: int, event_type: str, confidence: float, description: str
    ) -> int:
        camera = self.database.security_camera(camera_id)
        if not camera:
            raise KeyError("Security camera not found")
        if self.database.camera_privacy_mode():
            raise PermissionError("Privacy mode is enabled")
        event_id = self.database.add_camera_event(
            camera_id, event_type, confidence, description
        )
        self.database.event(
            "security_camera_event",
            {
                "camera_id": camera_id,
                "event_id": event_id,
                "event_type": event_type,
                "confidence": confidence,
            },
        )
        return event_id

    def preview(self, camera_id: int) -> dict[str, Any]:
        camera = self.database.security_camera(camera_id)
        if not camera:
            raise KeyError("Security camera not found")
        if self.database.camera_privacy_mode():
            raise PermissionError("Privacy mode is enabled")
        if self.config["simulation"] or camera["connection"] == "simulation":
            return {
                "camera_id": camera_id,
                "mode": "simulation",
                "message": "Safe simulated preview; no camera was contacted.",
            }
        return {
            "camera_id": camera_id,
            "mode": "configured",
            "message": (
                "Open this camera through its authenticated Home Assistant, "
                "ONVIF, or RTSP adapter."
            ),
        }
