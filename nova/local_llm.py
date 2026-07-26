from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LocalLLM:
    """Small OpenAI-compatible client for a local llama.cpp server."""

    def __init__(self, config: dict):
        self.config = config["local_llm"]
        self.project_root = Path(__file__).resolve().parent.parent

    def model_path(self) -> Path:
        path = Path(self.config["model_path"])
        return path if path.is_absolute() else self.project_root / path

    def status(self) -> dict:
        enabled = bool(self.config["enabled"])
        model = self.model_path()
        return {
            "enabled": enabled,
            "provider": "llama.cpp",
            "model_path": str(model),
            "model_present": model.is_file(),
            "server_url": self.config["server_url"],
            "fallback": "agent_router",
        }

    def chat(self, text: str) -> str:
        if not self.config["enabled"]:
            raise RuntimeError("Local model is disabled")
        if not self.model_path().is_file():
            raise RuntimeError(f"GGUF model not found: {self.model_path()}")

        payload = json.dumps(
            {
                "messages": [
                    {"role": "system", "content": self.config["system_prompt"]},
                    {"role": "user", "content": text},
                ],
                "temperature": self.config["temperature"],
                "max_tokens": self.config["max_tokens"],
                "stream": False,
            }
        ).encode("utf-8")
        request = Request(
            f"{self.config['server_url'].rstrip('/')}/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.config["timeout_seconds"]) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"Local llama.cpp server unavailable: {exc}") from exc
        try:
            return result["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Local model returned an invalid response") from exc
