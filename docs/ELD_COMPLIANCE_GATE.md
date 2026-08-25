# ELD Compliance Registry / Failover Gate

Status: evaluation only. RequantAi does not claim to be a registered/certified ELD and this feature must not alter legally required HOS records.

## Purpose

Maintain a locally cached, authenticated snapshot of the authoritative ELD registry/revocation data and compare the configured truck ELD against provider, model, and identifier fields.

Possible local states:

- `REGISTERED`
- `REVOKED`
- `UNKNOWN`
- `REGISTRY_STALE`

An unknown, unverified, duplicate, mismatched, or stale record must never be silently presented as compliant.

## Cloudless behavior

When WAN connectivity disappears, use the last verified local snapshot, expose its age, and preserve HOS-related telemetry in the truck journal. The registry gate is advisory/compliance-warning infrastructure; it does not rewrite HOS logs.

## Required tests

- registered device;
- newly revoked device;
- revocation while the truck is offline;
- stale registry snapshot;
- corrupted/unverified registry;
- provider/model/identifier mismatch;
- replacement device;
- revoked device later reinstated in a newer verified snapshot;
- replacement-deadline transition;
- complete WAN loss.

## Production follow-up

The registry ingestion component must authenticate the source snapshot, normalize identifiers without fuzzy matching, retain the previous verified snapshot for rollback/audit, and journal snapshot version/time. The exact government-data ingestion connector remains a separate implementation gate and should be tested against authoritative data before field use.
