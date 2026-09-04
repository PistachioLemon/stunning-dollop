# Kernel ABI Compatibility Gate

Status: staged evaluation only. No field kernel update is authorized by this document.

## Purpose

A security-fixed kernel can still make a truck node unusable if an ABI change breaks a third-party or hardware-facing module. This gate complements the Host Security Gate and reproducible image pipeline by requiring module and physical-device evidence before a candidate kernel/image can be promoted.

## Evidence manifest

Record the expected and observed kernel ABI and, for every required kernel-dependent module, its name, expected/observed version, load state, and associated hardware functional result. Preserve relevant kernel logs with the candidate-image evidence.

## Required bench regression

- CAN / OBD adapters;
- GPS / USB serial;
- camera interfaces;
- Bluetooth;
- USB/NVMe storage;
- travel-router networking;
- MQTT 5 + mTLS;
- required GPIO/SPI/I2C interfaces;
- offline reboot/degraded operation;
- A-to-B update;
- forced candidate-slot failure and rollback;
- kernel log review for module/driver errors.

Any ABI mismatch, required module load/version failure, hardware regression, or rollback failure produces `KERNEL_ABI_INCOMPATIBLE` and blocks promotion.

## Promotion chain

`security advisory -> candidate kernel/image -> ABI/module inventory -> Artifact Trust -> hardware regression -> A/B rollback -> operator approval`

CI tests the policy only. Module rebuilding, physical bus/device tests, destructive slot failure, and hard-power-loss behavior require the intended Pi 5 bench hardware.
