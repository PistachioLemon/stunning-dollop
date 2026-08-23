# Valhalla 3.8.3 Deployment Evaluation

Status: evaluation only. No deployment is authorized by this document.

Candidate routing engine: Valhalla 3.8.3 on the mini-PC/server.

## Immutable image rule

Production and hardware-test manifests must identify the ARM64 container image by an immutable digest (`image@sha256:...`), not by `latest` and not by a mutable version tag alone.

Do not invent or copy a digest from documentation. Record the digest only after pulling/inspecting the exact approved ARM64 image in the hardware-test environment, then preserve it in the release manifest and test evidence.

## Promotion gate

The digest-pinned image must pass the existing golden truck-route regression suite, including forbidden roads, low clearances, weight restrictions, toll preferences, hazmat-sensitive cases, distance drift, and route-status changes. A changed digest requires the routing regression suite to run again before promotion.

The Raspberry Pi 5 does not host the full routing engine; it consumes the stable routing service contract from the mini-PC/server and retains deterministic offline/degraded behavior.
