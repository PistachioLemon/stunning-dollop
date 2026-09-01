# Deadline-Aware ELD Enforcement & Fleet-Readiness Gate

Status: staged evaluation only. This does not certify an ELD, rewrite HOS records, merge code, or authorize deployment.

## Purpose

Extend the existing ELD registry-status gate into a deterministic deadline-aware fleet-readiness decision. Revoked devices are not operationally equivalent throughout the grace period.

State progression:

`REGISTERED -> REVOKED_GRACE -> REPLACEMENT_DUE_SOON -> ENFORCEMENT_ACTIVE`

Unknown, stale, unverified, conflicting, or non-unique registry evidence never silently becomes compliant.

## Security Guard evidence

Record exact provider, model, ELD identifier, authenticated snapshot time, snapshot age, revocation/effective date when present, replacement deadline, enforcement phase, and dispatch-readiness state.

The LLM, Librarian, dispatcher agent, and tool-calling layer may explain or display the decision but may not override the deterministic Security Guard result.

## Dispatch behavior

- `REGISTERED`: normal compliance readiness.
- `REVOKED_GRACE`: revoked status visible; replacement planning required.
- `REPLACEMENT_DUE_SOON`: progressively stronger operational alerts; default threshold is 30 days and UI may highlight 14/7/3/1-day milestones.
- `ENFORCEMENT_ACTIVE`: do not treat the truck as normally dispatch-ready based on that ELD.
- `UNKNOWN`, stale, unverified, conflicting, or missing deadline evidence: do not guess readiness.

This remains advisory/failover logic. It must not impersonate an ELD, alter driver logs, manufacture HOS records, or claim regulatory certification.

## Source-conflict policy

An authoritative ingestion connector should retain evidence from official FMCSA registry/news sources. If official sources conflict on a compliance-critical date or status and the conflict cannot be deterministically reconciled, mark the snapshot conflict and fail closed to `UNKNOWN` rather than choosing a date silently.

## Tests

Freeze time at deadline minus 30, 14, 7, 3, and 1 days, at the exact deadline, and after the deadline. Also test restoration to registered status before the deadline, stale and unverified snapshots, duplicate identifiers, WAN-disconnected cached operation with snapshot age visible, missing deadlines, conflicting official-source evidence, and attempts by higher-level AI/tool layers to override `ENFORCEMENT_ACTIVE`.

CI validates policy transitions only. Current real-world ELD status and deadlines must come from an authenticated authoritative connector and cannot be hard-coded from old test fixtures.
