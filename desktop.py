from __future__ import annotations

import os
import socket
import threading
import time
from pathlib import Path

import uvicorn
import webview

from nova.config import load_config


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.yaml"


def wait_for_server(host: str, port: int, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.25):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("Nova local server did not start within 15 seconds")


def main() -> None:
    os.chdir(ROOT)
    os.environ["NOVA_CONFIG"] = str(CONFIG)
    config = load_config(CONFIG)
    # Desktop mode is local-only. Safe mode additionally forces simulation.
    host = "127.0.0.1"
    port = int(config["app"]["port"])
    if os.getenv("NOVA_FORCE_SIMULATION") == "1":
        config["app"]["simulation"] = True
        config["package_locker"]["simulation"] = True

    server = uvicorn.Server(
        uvicorn.Config("nova.app:create_app", factory=True, host=host, port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, name="nova-api", daemon=True)
    thread.start()
    wait_for_server(host, port)
    try:
        webview.create_window(
            "Nova Home AI — PC Edition",
            f"http://{host}:{port}",
            width=1280,
            height=820,
            min_size=(900, 650),
        )
        webview.start(private_mode=False)
    finally:
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
