from __future__ import annotations

import argparse
import hashlib
import shutil
import urllib.request
from pathlib import Path

from nova.model_registry import ModelRegistry


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(entry, destination: Path) -> None:
    url = entry.download_url or f"https://huggingface.co/{entry.repo_id}/resolve/main/{entry.filename}?download=true"
    part = destination.with_suffix(destination.suffix + ".part")
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "RequantAi-Model-Installer/2"})
    try:
        with urllib.request.urlopen(request, timeout=90) as response, part.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        if entry.approx_size_bytes and part.stat().st_size < max(1, int(entry.approx_size_bytes * 0.90)):
            raise RuntimeError("Downloaded file is smaller than the registry expectation")
        if entry.sha256:
            actual = sha256_file(part)
            if actual.lower() != entry.sha256.lower():
                raise RuntimeError(f"SHA-256 mismatch: expected {entry.sha256}, got {actual}")
        part.replace(destination)
    except Exception:
        part.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Install an approved RequantAi GGUF model")
    parser.add_argument("--model", help="Registry model id; defaults to the truck-node model")
    parser.add_argument("--output", default="models/trucklm-small.gguf", help="Destination GGUF path")
    parser.add_argument("--accept-license", action="store_true", help="Confirm you reviewed and accept the model license")
    parser.add_argument("--dry-run", action="store_true", help="Show the selected model without downloading")
    args = parser.parse_args()

    registry = ModelRegistry()
    entry = registry.get(args.model)
    if not entry.approved:
        raise SystemExit(f"Model is experimental and not approved for automated install: {entry.id}")

    print(f"Model: {entry.name}")
    print(f"Source: https://huggingface.co/{entry.repo_id}")
    print(f"License: {entry.license}")
    print(f"Quantization: {entry.quantization}")
    if entry.approx_size_bytes:
        print(f"Approx size: {entry.approx_size_bytes / 1_000_000:.0f} MB")
    if entry.sha256:
        print(f"Pinned SHA-256: {entry.sha256}")

    if args.dry_run:
        print("Dry run only; no model downloaded.")
        return
    if not args.accept_license:
        raise SystemExit("Refusing download: review the model card/license, then rerun with --accept-license")

    destination = Path(args.output)
    if destination.exists():
        raise SystemExit(f"Refusing to overwrite existing model: {destination}")
    try:
        download(entry, destination)
    except Exception as exc:
        raise SystemExit(f"Model download failed safely: {exc}") from exc
    print(f"Installed and verified: {destination}")
    print("Next: start llama.cpp and run the model/system-recovery checks before enabling local_llm.")


if __name__ == "__main__":
    main()
