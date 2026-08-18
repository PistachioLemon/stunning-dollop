# Uptane Evaluation Lane

Status: approved for isolated design and adversarial testing. Not production-enabled, merged, or deployed by this document.

RequantAi's current A/B recovery gate remains intact while this lane evaluates an Uptane-compatible vehicle update profile. Uptane Standard 2.1.0 is the design reference.

## Target architecture

Mini-PC update authority -> private router LAN -> authenticated truck Pi -> inactive A/B slot.

The truck must remain operational without the update authority. Updates are staged only to the inactive slot and promotion requires local boot-health verification.

## Required metadata concepts

- vehicle/truck identity and hardware identifier
- current and minimum accepted software versions
- target image digest and length
- expiration
- Director authorization for the specific truck
- Image repository authorization for the artifact
- independent offline root trust
- rollback/freeze protection
- audit record of stage, boot verification, promotion, and rollback

## Security boundary

The existing HMAC recovery manifest is an evaluation compatibility gate only. Fleet production must not distribute a shared signing secret to trucks. The Uptane lane must use asymmetric verification with private signing keys kept off truck nodes.

## Adversarial acceptance tests

1. Expired metadata is rejected.
2. Correctly signed old software is rejected after the minimum version advances.
3. An image authorized for another truck/hardware identifier is rejected.
4. A modified image is rejected before staging.
5. Director-only compromise cannot authorize an untrusted image.
6. Image-repository-only compromise cannot target an unauthorized truck.
7. Interrupted download leaves the active slot bootable.
8. Failed boot-health verification returns to the known-good slot.
9. Cached metadata/update behavior remains deterministic while disconnected.
10. Loss of the update service never disables normal truck telemetry or local deterministic safety functions.

No automatic update promotion is permitted during this evaluation.
