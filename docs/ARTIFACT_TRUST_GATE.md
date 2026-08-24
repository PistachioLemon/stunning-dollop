# Security Guard Artifact Trust Gate

Status: evaluation/staging only. This does not authorize deployment or automatic promotion.

## Admission pipeline

1. obtain candidate artifact;
2. calculate and compare SHA-256;
3. when the upstream supplier publishes provenance, cryptographically verify the attestation using an approved verifier;
4. extract trusted repository/workflow claims into `ArtifactEvidence`;
5. Security Guard checks the claims against the local allowlist and expiry;
6. run the candidate benchmark/test lane;
7. require operator approval before production promotion.

Security Guard's Python policy code does not pretend to cryptographically verify SLSA itself. The cryptographic verifier must fail closed and provide trusted claims to the policy layer.

## Policy

For suppliers that publish trusted provenance, provenance is required. A hash-only fallback is allowed only for a supplier explicitly configured for fallback. Never silently downgrade from required provenance to hash-only verification.

Cache the approved trust policy and verification material needed for disconnected validation so the local mini-PC/truck network can evaluate previously staged artifacts without cloud access.

## Adversarial tests

- valid artifact and valid attestation;
- modified binary;
- valid binary attributed to the wrong repository;
- unauthorized build workflow;
- invalid attestation;
- missing attestation where provenance is required;
- controlled hash fallback for an explicitly approved supplier without provenance;
- expired local allowlist;
- offline verification from cached trust material;
- rollback to the previously approved runtime.

## Architecture boundary

Runtime/model downloads and verification belong on the mini-PC/server side. The Pi 5 remains the deterministic truck edge controller. Security Guard policy can be shared, but no LLM decides whether an artifact is trusted.
