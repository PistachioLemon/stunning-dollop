from __future__ import annotations

import argparse
import json

from nova.healing.runtime import HealingRuntime


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Nova self-healing diagnostics without executing repairs")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    runtime = HealingRuntime(args.config)
    print(json.dumps(runtime.diagnose(), indent=2, default=str))


if __name__ == "__main__":
    main()
