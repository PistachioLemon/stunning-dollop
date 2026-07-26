from __future__ import annotations

import argparse
import os

import uvicorn

from nova.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Nova Home AI")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.check:
        print(f"Nova configuration OK: {config['_config_path']}")
        return
    os.environ["NOVA_CONFIG"] = str(args.config)
    uvicorn.run(
        "nova.app:create_app",
        factory=True,
        host=config["app"]["host"],
        port=config["app"]["port"],
        reload=False,
    )


if __name__ == "__main__":
    main()
