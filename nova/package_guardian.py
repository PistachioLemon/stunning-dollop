from __future__ import annotations

import hashlib
import hmac
import base64
import io
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from .database import Database


def _pin_hash(pin: str) -> str:
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


class PackageGuardian:
    """Expected-delivery verification and fail-locked locker control."""

    def __init__(self, database: Database, config: dict[str, Any]):
        self.database = database
        self.settings = config["package_locker"]
        self.simulation = bool(config["app"]["simulation"] or self.settings["simulation"])
        self.enabled = bool(self.settings["enabled"])
        self._timer: threading.Timer | None = None
        self._lock = threading.RLock()
        self._output = None
        if self.enabled and not self.simulation:
            try:
                from gpiozero import OutputDevice

                self._output = OutputDevice(
                    self.settings["gpio_pin"],
                    active_high=bool(self.settings["active_high"]),
                    initial_value=False,
                )
            except Exception as exc:
                raise RuntimeError(f"Package locker GPIO failed safe: {exc}") from exc
        self.lock("safe service startup")

    def _authorized(self, pin: str) -> bool:
        return hmac.compare_digest(str(pin), str(self.settings["operator_pin"]))

    def require_authorized(self, pin: str) -> None:
        if not self._authorized(pin):
            self.database.event("locker_authorization_denied", {"operation": "operator"})
            raise PermissionError("Invalid package locker operator PIN")

    def status(self) -> dict[str, Any]:
        return {
            **self.database.locker_state(),
            "enabled": self.enabled,
            "mode": "simulation" if self.simulation else "gpio",
            "gpio_pin": None if self.simulation else self.settings["gpio_pin"],
        }

    def lock(self, reason: str = "lock requested") -> dict[str, Any]:
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            if self._output is not None:
                self._output.off()
            self.database.set_locker_state("locked", reason)
            self.database.event("package_locker_locked", {"reason": reason})
            return self.status()

    def unlock(self, reason: str, duration_seconds: int | None = None) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Package locker is disabled")
        duration = duration_seconds or int(self.settings["unlock_seconds"])
        duration = min(duration, int(self.settings["max_unlock_seconds"]))
        with self._lock:
            if self._output is not None:
                self._output.on()
            self.database.set_locker_state("unlocked", reason)
            self.database.event(
                "package_locker_unlocked",
                {"reason": reason, "duration_seconds": duration},
            )
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(
                duration, self.lock, kwargs={"reason": "automatic timeout relock"}
            )
            self._timer.daemon = True
            self._timer.start()
            return {**self.status(), "relock_after_seconds": duration}

    def add_expected_delivery(
        self,
        carrier: str,
        tracking_code: str,
        recipient: str,
        courier_pin: str | None,
    ) -> int:
        if self.settings["require_courier_pin"] and not courier_pin:
            raise ValueError("A courier PIN is required for expected deliveries")
        try:
            delivery_id = self.database.add_delivery(
                carrier,
                tracking_code,
                recipient,
                _pin_hash(courier_pin) if courier_pin else None,
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("That tracking code is already registered") from exc
        self.database.event(
            "package_expected",
            {"delivery_id": delivery_id, "carrier": carrier, "tracking_code": tracking_code.upper()},
        )
        return delivery_id

    def verify_delivery(
        self,
        tracking_code: str,
        courier_pin: str | None,
        confidence: float,
        evidence_sha256: str | None,
    ) -> dict[str, Any]:
        delivery = self.database.delivery_by_tracking(tracking_code)
        if not delivery or delivery["state"] != "expected":
            self.database.event(
                "package_verification_denied",
                {"tracking_code": tracking_code.upper(), "reason": "not expected"},
            )
            raise PermissionError("Package is not on the expected-delivery list")
        expected_hash = delivery["courier_pin_hash"]
        if expected_hash and (
            not courier_pin or not hmac.compare_digest(expected_hash, _pin_hash(courier_pin))
        ):
            self.database.event(
                "package_verification_denied",
                {"delivery_id": delivery["id"], "reason": "invalid courier PIN"},
            )
            raise PermissionError("Invalid courier PIN")
        minimum = float(self.settings["minimum_verification_confidence"])
        if confidence < minimum:
            self.database.event(
                "package_verification_denied",
                {
                    "delivery_id": delivery["id"],
                    "reason": "confidence below threshold",
                    "confidence": confidence,
                },
            )
            raise PermissionError("Delivery verification confidence is below the required threshold")
        self.database.verify_delivery(delivery["id"], confidence, evidence_sha256)
        self.database.event(
            "package_verified",
            {
                "delivery_id": delivery["id"],
                "confidence": confidence,
                "evidence_sha256": evidence_sha256,
            },
        )
        result: dict[str, Any] = {
            "verified": True,
            "delivery_id": delivery["id"],
            "tracking_code": delivery["tracking_code"],
        }
        if self.settings["auto_unlock_verified_delivery"]:
            result["locker"] = self.unlock(
                f"verified delivery {delivery['id']}",
                int(self.settings["unlock_seconds"]),
            )
        return result

    def generate_access_code(
        self,
        delivery_id: int,
        operator_pin: str,
        code_type: str,
        expires_minutes: int,
    ) -> dict[str, Any]:
        self.require_authorized(operator_pin)
        delivery = self.database.delivery(delivery_id)
        if not delivery or delivery["state"] != "expected":
            raise KeyError("Expected delivery not found")
        token = f"NOVA-PKG-{secrets.token_urlsafe(24)}"
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        expires_at = (
            datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
        ).isoformat()
        code_id = self.database.add_package_access_code(
            delivery_id, token_hash, code_type, expires_at
        )
        if code_type == "qr":
            import qrcode

            image = qrcode.make(token)
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            mime_type = "image/png"
        else:
            from barcode import Code128
            from barcode.writer import SVGWriter

            buffer = io.BytesIO()
            Code128(token, writer=SVGWriter()).write(
                buffer,
                options={"write_text": False, "module_height": 12.0, "quiet_zone": 4.0},
            )
            mime_type = "image/svg+xml"
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        self.database.event(
            "package_access_code_created",
            {
                "code_id": code_id,
                "delivery_id": delivery_id,
                "code_type": code_type,
                "expires_at": expires_at,
            },
        )
        return {
            "id": code_id,
            "delivery_id": delivery_id,
            "code_type": code_type,
            "expires_at": expires_at,
            "image_data_url": f"data:{mime_type};base64,{encoded}",
        }

    def scan_access_code(self, code: str) -> dict[str, Any]:
        token_hash = hashlib.sha256(code.strip().encode("utf-8")).hexdigest()
        now = datetime.now(timezone.utc).isoformat()
        access = self.database.consume_package_access_code(token_hash, now)
        if not access:
            self.database.event(
                "package_code_denied", {"reason": "unknown or concurrent replay"}
            )
            raise PermissionError("Package code is invalid")
        if access["used_at"] != now:
            reason = "expired" if access["expires_at"] < now else "already used"
            self.database.event(
                "package_code_denied", {"code_id": access["id"], "reason": reason}
            )
            raise PermissionError(f"Package code is {reason}")
        if access["delivery_state"] != "expected":
            self.database.event(
                "package_code_denied",
                {"code_id": access["id"], "reason": "delivery is not expected"},
            )
            raise PermissionError("Delivery is no longer expected")
        self.database.verify_delivery(access["delivery_id"], 1.0, token_hash)
        self.database.event(
            "package_code_accepted",
            {
                "code_id": access["id"],
                "delivery_id": access["delivery_id"],
                "code_type": access["code_type"],
            },
        )
        return {
            "verified": True,
            "delivery_id": access["delivery_id"],
            "tracking_code": access["tracking_code"],
            "locker": self.unlock(
                f"scanned {access['code_type']} for delivery {access['delivery_id']}"
            ),
        }

    def shutdown(self) -> None:
        self.lock("safe service shutdown")
        if self._output is not None:
            self._output.close()
