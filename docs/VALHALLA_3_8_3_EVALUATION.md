# Valhalla 3.8.3 Deployment Evaluation

Status: evaluation only. No deployment is authorized by this document.

Candidate routing engine: Valhalla 3.8.3 on the mini-PC/server.

## Immutable image rule

Production and hardware-test manifests must identify the ARM64 container image by an immutable digest (`image@sha256:...`), not by `latest` and not by a mutable version tag alone.

Current ARM64 candidate digest from the package registry:

`sha256:58c7dd3fb256f306b00c558fb76aea9fd4fb804edd831e2b4847c26511cca507`

The software evaluation pin uses that exact digest. Hardware promotion still requires independently pulling/inspecting the exact ARM64 image on the intended mini-PC, confirming that the observed digest matches, and preserving that evidence through the Security Guard Artifact Trust Gate. A digest mismatch fails closed.

## Promotion gate

The digest-pinned image must pass the existing golden truck-route regression suite, including forbidden roads, low clearances, weight restrictions, toll preferences, hazmat-sensitive cases, distance drift, and route-status changes. A changed digest requires the routing regression suite to run again before promotion.

The Raspberry Pi 5 does not host the full routing engine; it consumes the stable routing service contract from the mini-PC/server and retains deterministic offline/degraded behavior.
