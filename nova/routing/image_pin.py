from __future__ import annotations

from dataclasses import dataclass
import re


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class RoutingImagePin:
    engine: str
    version: str
    architecture: str
    image: str
    digest: str

    def validate(self) -> None:
        if self.engine != "valhalla":
            raise ValueError("unsupported routing engine")
        if self.version != "3.8.3":
            raise ValueError("unexpected Valhalla evaluation version")
        if self.architecture != "linux/arm64":
            raise ValueError("Valhalla evaluation pin must target linux/arm64")
        if not _SHA256_RE.fullmatch(self.digest):
            raise ValueError("digest must be a lowercase SHA-256 hex string")
        expected_suffix = f"@sha256:{self.digest}"
        if not self.image.endswith(expected_suffix):
            raise ValueError("image must be pinned by the declared sha256 digest")
        if ":latest" in self.image:
            raise ValueError("latest is not allowed for routing images")


VALHALLA_3_8_3_ARM64 = RoutingImagePin(
    engine="valhalla",
    version="3.8.3",
    architecture="linux/arm64",
    image=(
        "ghcr.io/gis-ops/docker-valhalla/valhalla@sha256:"
        "58c7dd3fb256f306b00c558fb76aea9fd4fb804edd831e2b4847c26511cca507"
    ),
    digest="58c7dd3fb256f306b00c558fb76aea9fd4fb804edd831e2b4847c26511cca507",
)
