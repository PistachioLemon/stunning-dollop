# Pi 5 Boot-Firmware Security & Recovery Gate

Status: staged evaluation only. No EEPROM update, OTP change, merge, or field deployment is authorized by this document.

## Purpose

Protect the layer below the Linux image and kernel. Security Guard should treat the Pi 5 boot firmware as measured platform state rather than an invisible prerequisite.

## Evidence

Record board revision, installed EEPROM version and SHA-256, minimum permitted firmware, expected/observed boot order, secure-boot state, firmware-key-lock state, and recovery-test results.

Conceptual measured chain:

`board revision -> minimum firmware -> EEPROM version/digest -> boot policy -> OS image -> kernel ABI -> modules -> services`

## Blocking conditions

A candidate is blocked when it is below the configured minimum, unexpectedly changes boot order, weakens required secure-boot/key-lock policy, fails A/B update/rollback, cannot recover a corrupted candidate, loses the intended NVMe/recovery behavior, cannot recover without WAN, loses Security Guard identity, or fails to restore truck I/O after recovery.

## Bench tests

- cold boot from intended NVMe;
- repeated reboot/cold-boot soak (target 50-100 cycles);
- A/B firmware update and rollback;
- corrupted-candidate recovery;
- removed-NVMe recovery behavior;
- controlled power interruption during candidate update;
- WAN-disconnected recovery;
- board revision/minimum-version enforcement;
- secure-boot and firmware-key policy verification;
- Security Guard identity persistence;
- CAN/GPS/MQTT startup after recovery.

EEPROM/OTP and destructive recovery testing can brick or strand a board and therefore requires dedicated Pi 5 bench hardware plus known-good recovery media. CI validates policy only.

The experimental persistent boot-count mechanism is intentionally not a production dependency. It may be evaluated later as a hardware-level boot-loop signal after upstream stabilization.
