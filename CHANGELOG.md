# Changelog

## 2.2.0 — Local GGUF intelligence

- Added an optional offline llama.cpp integration for GGUF instruct models.
- Added local-model health reporting and configurable model/server settings.
- Limited free-form model use to Companion and Librarian conversations.
- Preserved deterministic authorization for SOS, medication, smart-home,
  package-verification, and locker actions.
- Added automatic agent-router fallback when the model or server is unavailable.
- Added a Raspberry Pi llama.cpp build/model installation helper.

## 2.1.0 — Package Guardian

- Added a seventh agent for expected-delivery verification and package-locker
  control.
- Added one-time expiring QR and Code 128 generation.
- Added USB scanner, browser camera scanner, and manual scan input.
- Added hashed courier credentials, atomic single-use code consumption, replay
  denial, and complete event auditing.
- Added fail-locked GPIO relay control, operator authorization, timed unlocks,
  and automatic relocking.
- Documented Home Assistant, direct Pi hardware, and future ESP32/MQTT device
  connections.

## 2.0.0 — Rebuild

- Rebuilt Nova as a standalone offline-first Raspberry Pi 5 application.
- Added a touch-first kiosk dashboard and local FastAPI service.
- Added medication schedules and dose records.
- Added auditable SOS countdown and PIN cancellation.
- Added safe, disabled-by-default outbound emergency integration boundary.
- Added Home Assistant simulation/live bridge.
- Added presence-based awake, dim, and sleep states.
- Added family notes, daily check-ins, and six-agent request routing.
- Added SQLite WAL storage, configuration validation, tests, systemd service,
  and a Raspberry Pi installer.
# 3.0.0-pc

- Added a Windows desktop wrapper and local-only binding.
- Added one-click PowerShell installation and batch launchers.
- Added forced simulation Safe Mode.
- Added Windows llama.cpp/GGUF launch helper.
- Removed Raspberry Pi GPIO, systemd, and kiosk-install packaging from PC edition.
