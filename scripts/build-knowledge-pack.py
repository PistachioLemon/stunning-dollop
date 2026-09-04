from __future__ import annotations

import argparse
from pathlib import Path

from nova.knowledge_pack import build_pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a RequantAi streamable knowledge pack")
    parser.add_argument("--output", required=True)
    parser.add_argument("--pack-id", required=True)
    parser.add_argument("paths", nargs="+", help="Text/JSON/JSONL/Markdown/PDF-summary files to include")
    args = parser.parse_args()

    files = []
    for raw in args.paths:
        path = Path(raw)
        if not path.is_file():
            raise SystemExit(f"Not a file: {path}")
        kind = path.suffix.lower().lstrip(".") or "blob"
        files.append((path.name, path, kind))

    output = build_pack(
        args.output,
        files,
        pack_id=args.pack_id,
        metadata={"purpose": "RequantAi/TruckLM retrieval knowledge"},
    )
    print(output)


if __name__ == "__main__":
    main()
