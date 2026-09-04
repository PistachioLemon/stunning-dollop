# rpi-image-gen 2.7.0 Evaluation

Status: isolated evaluation only. This document does not authorize production-image replacement, merge, or deployment.

## Goal

Evaluate Raspberry Pi `rpi-image-gen` 2.7.0 as the repeatable builder for the deterministic Pi 5 truck-node image while preserving the existing mini-PC/server AI boundary.

Proposed release chain:

`source/config -> repeatable image build -> SBOM/package manifest -> Artifact Trust Gate -> signed/encrypted A/B image -> bench Pi regression -> operator-approved release`

## Promotion evidence

Build the same ARM64 truck image twice from the same inputs. Record and compare normalized package manifests and SBOMs. Verify expected filesystem/configuration content separately; raw whole-image byte identity is not assumed because timestamps/partition metadata may differ unless the builder guarantees deterministic bytes.

The candidate must also prove:

- no unintended passwordless sudo;
- A and B slots boot;
- corruption of the candidate slot returns to the known-good slot;
- encrypted storage works through normal boot/recovery;
- boot and degraded operation without WAN;
- travel-router networking via the intended NetworkManager/iwd path;
- Bluetooth;
- CAN/OBD;
- GPS;
- MQTT 5 + mTLS;
- cameras;
- USB/NVMe;
- interrupted-update recovery;
- an Artifact Trust rejection can never become active.

## Safety boundary

Secure-boot/OTP operations, destructive A/B corruption tests, encrypted-media replacement, and hard-power-loss testing require dedicated bench hardware. CI validates policy and evidence handling only.

Do not migrate field images merely because 2.7.0 builds successfully. Promotion requires the complete bench evidence and a separate operator approval.
