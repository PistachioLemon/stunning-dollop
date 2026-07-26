# Nova Home AI — PC Edition v3.0

Nova PC is a local, offline-first home-assistant desktop app for Windows 10/11.
It is created by **LaBrone Gaines** and distributed under Apache-2.0.

## What is included

- Native movable desktop window powered by a local FastAPI service
- Seven agents: Companion, Medication, Safety, Home, Family Notes, Librarian,
  and Package Guardian
- Medication records, family notes, daily check-ins, and an event audit trail
- Safe SOS drill with PIN cancellation; no claim of contacting 911
- Package verification with one-time QR or Code 128 access credentials
- Timed simulated locker unlock and automatic relock
- Home Assistant bridge for supported smart-home devices
- Home Security Cameras module with enrollment, privacy mode, event logging,
  safe preview simulation, and Home Assistant/RTSP/ONVIF adapter points
- Browser/desktop microphone, camera, QR scanner, Bluetooth, and network-device UI
- Optional private GGUF conversation model through `llama.cpp`
- Safe Mode that forces all locker and home actions into simulation

## Windows quick start

Requirements: Windows 10/11 and Python 3.11 or newer.

1. Right-click `install-windows.ps1` and choose **Run with PowerShell**.
2. If Windows blocks scripts, open PowerShell in this folder and run:

   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\install-windows.ps1
   ```

3. Double-click `Start-Nova-PC.bat`.

For a consequence-free test, use `Start-Nova-Safe-Mode.bat`. Nova binds only to
`127.0.0.1`, so its API is not exposed to the local network by default.

## Protected sandbox

Double-click `Start-Nova-Protected-Sandbox.bat` to launch an isolated test
environment at `http://127.0.0.1:8788`.

The protected sandbox:

- binds only to the local PC
- forces global, package-locker, and security-camera simulation
- disables Home Assistant, presence-camera access, voice, and outbound emergency actions
- uses `sandbox-data/nova.db` instead of the normal Nova database
- keeps local GGUF inference disabled by default

Run `Reset-Nova-Protected-Sandbox.ps1` to erase only the sandbox database and
start fresh. Close Nova before resetting. The reset script never touches the
normal `data/` directory.

## Browser-only option

```powershell
.\.venv\Scripts\python.exe run.py
```

Open `http://127.0.0.1:8787`.

## Local GGUF model

Download `llama.cpp` for Windows from its official release, put
`llama-server.exe` in `llama.cpp\`, and place a license-approved Q4 GGUF at:

```text
models\nova-assistant.gguf
```

Recommended starting point: a 1B–1.5B instruct model in Q4 quantization. Then:

```powershell
.\scripts\install-local-llm-windows.ps1
```

Set `local_llm.enabled: true` in `config.yaml`, then restart Nova. Companion and
Librarian may use the model. SOS, medication, locks, devices, and package access
remain controlled by deterministic authorization code.

The model weights are deliberately not included in this package or Git because
they are large and carry their own license terms.

## Real device connectivity

- Home Assistant is Nova's general bridge for lights, thermostats, plugs,
  scenes, cameras, and other vendor devices.
- Bluetooth discovery depends on Web Bluetooth support and always requires a
  user gesture and operating-system permission.
- Camera and microphone access require explicit Windows/WebView permission.
- Camera passwords and stream credentials stay outside Nova's repository.
  Nova stores camera metadata and events; authenticated adapters handle streams.
- ESP32 nodes can connect through Home Assistant or a local MQTT integration.
- Package-locker hardware requires a separate authenticated controller. PC
  Edition never tries to drive Raspberry Pi GPIO.

Keep `simulation: true` until each integration is configured and tested. Never
connect a solenoid directly to a PC or microcontroller output.

## Configuration

Start from `config.example.yaml`. Change the example SOS and locker PINs before
real use. Secrets such as `NOVA_HA_TOKEN` belong in environment variables and
must never be committed to Git.

## Validation

```powershell
.\.venv\Scripts\python.exe run.py --check
.\.venv\Scripts\python.exe -m pytest -q
```

API documentation is available at `http://127.0.0.1:8787/docs` while running.

## License and creator

Copyright © 2026 **LaBrone Gaines**. All rights reserved.

Licensed under the Apache License, Version 2.0. See `LICENSE` and `NOTICE`.
