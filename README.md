# RequantAi Dispatcher — AI Hauling System

CPU-first, offline-capable dispatch and truck-node runtime for RequantAi. The minimum supported target is a Raspberry Pi 5 without an AI accelerator. Hailo/Coral support is optional and must be capability-detected.

## Current operating layers

- OpenClaw load/route orchestration and operator-gated commitments
- Independent truck brains with GPS, CAN, OBD-II, reefer, load-sensor, MQTT, cargo-vision, and HOS adapter points
- TruckLM through optional local llama.cpp; deterministic routing works when no model is installed
- Permission Broker, AI Librarian, Repair Librarian, staged system recovery, and audit history
- Selected-event learning, post-drive review, and acknowledged 1:00 AM Pacific training batches
- CPU-only simulation for development before vehicle hardware is connected

Only hauling, dispatch, fleet, truck-node, cargo, compliance, learning, and recovery workflows belong in this repository.

## Minimum start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py --check --config config.sandbox.yaml
python -m pytest -q
python run.py --config config.sandbox.yaml
```

Open `http://127.0.0.1:8788`. No AI HAT, GGUF model, CAN adapter, camera, or MQTT broker is required for the sandbox baseline.

## Safety

Safe named actions may run automatically. Bookings, payments, signatures, HOS changes, safety overrides, model promotion, and other restricted actions require operator approval. Knowledge text and model output never become executable commands.

Model weights, runtime data, secrets, patents, proprietary mechanisms, and excluded legacy archives stay out of Git.
