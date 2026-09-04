from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


@dataclass(frozen=True)
class PackEntry:
    name: str
    sha256: str
    size: int
    kind: str


class KnowledgePack:
    """Read RequantAi knowledge directly from a ZIP container without full extraction.

    Individual entries are decompressed on demand into memory. The archive is not
    unpacked to disk. This is intended for text/JSONL/manual chunks, not GGUF
    weights or SQLite databases that require true random-access file semantics.
    """

    MANIFEST = "manifest.json"

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def manifest(self) -> dict:
        with zipfile.ZipFile(self.path, "r") as zf:
            return json.loads(zf.read(self.MANIFEST).decode("utf-8"))

    def names(self) -> list[str]:
        with zipfile.ZipFile(self.path, "r") as zf:
            return [n for n in zf.namelist() if n != self.MANIFEST]

    def read_bytes(self, name: str, *, max_bytes: int = 8 * 1024 * 1024) -> bytes:
        with zipfile.ZipFile(self.path, "r") as zf:
            info = zf.getinfo(name)
            if info.file_size > max_bytes:
                raise ValueError(f"Pack entry too large for bounded read: {name}")
            data = zf.read(name)
        return data

    def read_text(self, name: str, *, max_bytes: int = 8 * 1024 * 1024) -> str:
        return self.read_bytes(name, max_bytes=max_bytes).decode("utf-8", errors="replace")

    def iter_jsonl(self, name: str, *, max_bytes: int = 32 * 1024 * 1024) -> Iterator[dict]:
        raw = self.read_bytes(name, max_bytes=max_bytes)
        for line in io.BytesIO(raw):
            line = line.strip()
            if line:
                yield json.loads(line)

    def verify(self) -> dict:
        manifest = self.manifest()
        expected = {entry["name"]: entry for entry in manifest.get("entries", [])}
        results = []
        with zipfile.ZipFile(self.path, "r") as zf:
            for name, meta in expected.items():
                h = hashlib.sha256()
                with zf.open(name, "r") as stream:
                    while True:
                        chunk = stream.read(1024 * 1024)
                        if not chunk:
                            break
                        h.update(chunk)
                results.append({
                    "name": name,
                    "ok": h.hexdigest() == meta["sha256"],
                    "sha256": h.hexdigest(),
                })
        return {"ok": all(item["ok"] for item in results), "entries": results}


def build_pack(
    output: str | Path,
    files: Iterable[tuple[str, str | Path, str]],
    *,
    pack_id: str,
    metadata: dict | None = None,
) -> Path:
    """Build an independently readable RequantAi knowledge pack.

    `files` contains (archive_name, source_path, kind). Each pack is a complete
    ZIP by itself. Large libraries should be split into multiple independent
    packs instead of one traditional split-ZIP set, so the dispatcher can mount/read any
    pack without requiring all volume parts.
    """
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    entries: list[PackEntry] = []

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for archive_name, source_path, kind in files:
            source = Path(source_path)
            data = source.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            zf.writestr(archive_name, data)
            entries.append(PackEntry(archive_name, digest, len(data), kind))

        manifest = {
            "schema_version": 1,
            "pack_id": pack_id,
            "format": "nova-knowledge-pack",
            "read_mode": "entry-streaming-no-full-extract",
            "metadata": metadata or {},
            "entries": [entry.__dict__ for entry in entries],
        }
        zf.writestr(
            KnowledgePack.MANIFEST,
            json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8"),
        )

    return output
