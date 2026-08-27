# Host OS / Kernel Security Promotion Gate

Status: staged evaluation only. This gate does not authorize automatic patching of a field truck.

## Purpose

Security Guard records the installed OS/kernel version, image SHA-256, active/candidate A/B boot slot, applicable security advisories, Artifact Trust result, hardware-regression result, and rollback-test result.

A high/critical or network-relevant advisory affecting the installed kernel marks the image `SECURITY_UPDATE_REQUIRED`. That state creates a candidate-image workflow; it does not overwrite the currently verified field image.

## Promotion flow

`advisory -> candidate image -> Artifact Trust Gate -> hardware regression -> rollback test -> signed/A-B staging -> operator-approved promotion`

## Hardware regression

Before promotion, verify at minimum:

- CAN / OBD adapters;
- GPS;
- MQTT 5 and mTLS;
- travel-router LAN and WAN-loss recovery;
- Bluetooth;
- USB/NVMe storage;
- cargo/driver camera interfaces;
- journal replay;
- server heartbeat/degraded modes;
- A/B rollback.

## Fail-safe policy

Never auto-install a kernel simply because an advisory exists. Never mark an affected image current because WAN is unavailable. Cache authenticated advisory metadata for disconnected evaluation, preserve the known-good slot, and retain evidence identifying which image/kernel was tested.

CI validates policy behavior only. Physical device/driver compatibility and destructive rollback tests require bench Pi/server hardware.
