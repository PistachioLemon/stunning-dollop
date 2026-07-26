from __future__ import annotations

import os

import httpx


class HomeAssistantClient:
    def __init__(self, config: dict):
        self.config = config["home_assistant"]
        self.enabled = bool(self.config["enabled"])

    def _headers(self) -> dict[str, str]:
        token = os.getenv(self.config["token_env"], "")
        if not token:
            raise RuntimeError(f"Missing Home Assistant token environment variable: {self.config['token_env']}")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def status(self) -> dict:
        if not self.enabled:
            return {"enabled": False, "connected": False, "mode": "simulation"}
        try:
            response = httpx.get(
                f"{self.config['base_url'].rstrip('/')}/api/",
                headers=self._headers(),
                timeout=4,
            )
            response.raise_for_status()
            return {"enabled": True, "connected": True, "mode": "live"}
        except (httpx.HTTPError, RuntimeError) as exc:
            return {"enabled": True, "connected": False, "mode": "live", "error": str(exc)}

    def call_service(self, domain: str, service: str, entity_id: str) -> dict:
        if not self.enabled:
            return {"accepted": True, "mode": "simulation", "entity_id": entity_id}
        response = httpx.post(
            f"{self.config['base_url'].rstrip('/')}/api/services/{domain}/{service}",
            headers=self._headers(),
            json={"entity_id": entity_id},
            timeout=8,
        )
        response.raise_for_status()
        return {"accepted": True, "mode": "live", "result": response.json()}

