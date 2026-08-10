from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from nova.model_registry import ModelRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Nova's approved local GGUF model registry")
    parser.add_argument("--model", help="Model id to inspect")
    parser.add_argument("--llama-command", action="store_true", help="Print llama.cpp launch command")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    registry = ModelRegistry()
    if args.model:
        entry = registry.get(args.model)
        if args.llama_command:
            print(" ".join(registry.llama_command(entry.id)))
            return
        print(json.dumps(asdict(entry), indent=2) if args.json else entry)
        return

    entries = registry.all()
    if args.json:
        print(json.dumps({"default_model": registry.default_model, "models": [asdict(item) for item in entries]}, indent=2))
        return

    print(f"Default: {registry.default_model}")
    for entry in entries:
        state = "APPROVED" if entry.approved else "EXPERIMENTAL"
        print(f"{state:12} {entry.id:38} {entry.license}")


if __name__ == "__main__":
    main()
