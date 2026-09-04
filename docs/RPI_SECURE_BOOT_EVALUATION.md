# Raspberry Pi Secure-Boot / Encrypted-Image Evaluation Lane

Status: approved for isolated evaluation only. This does not enable secure boot, burn OTP/eFuse policy, rotate production keys, deploy an image, or replace the Uptane update authorization lane.

## Goal

Evaluate Raspberry Pi `rpi-sb-provisioner` as the low-level provisioning layer beneath RequantAi Security Guard and the Uptane-compatible A/B update design.

Target stack:

Uptane authorization -> signed image -> secure-boot capable Pi provisioning -> encrypted system image -> inactive A/B slot -> local health verification -> promotion or rollback.

## Required properties

- asymmetric signing keys remain off truck nodes
- repeatable provisioning records per truck Pi
- secure boot rejects unsigned or wrongly signed boot artifacts
- encrypted root/data design does not prevent deterministic edge recovery
- replacement NVMe/media has a documented re-provision path
- active slot remains bootable if inactive-slot provisioning/update fails
- truck telemetry/safety collection remains available whenever the active slot is healthy
- provisioning actions are auditable and never triggered by an LLM

## Hardware-only acceptance tests

1. Known-good signed image boots.
2. Modified/unsigned boot artifact is rejected.
3. Image signed by the wrong key is rejected.
4. Inactive-slot corruption leaves the active slot bootable.
5. Interrupted provisioning/update does not destroy the known-good slot.
6. Replacement NVMe follows the documented recovery/provisioning path.
7. Full network isolation does not prevent booting the last known-good image.
8. Recovery-key loss is simulated and documented before any production key policy is committed.
9. A/B rollback still works with secure boot enforcement enabled.
10. Provisioning database/audit records map to the correct truck and hardware identity.

## Safety boundary

Do not enable irreversible Raspberry Pi secure-boot/OTP policies during CI or software-only evaluation. Those tests require dedicated sacrificial/bench hardware first.
