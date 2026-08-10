# Nova Experimental Upgrades

This page tracks the current self-healing and portable-agent work on the `feature/nova-portable-capsules` branch. These features are under test and are not merged into `main` yet.

## Self-healing architecture

Nova now has a staged recovery path:

`detect -> diagnose -> retrieve repair knowledge -> select recipe -> sandbox -> execute named handler -> verify -> rollback if needed -> remember outcome`

The controller does not execute arbitrary repair text. Only host-registered handlers can perform actions.

## Repair Librarian

The Repair Librarian stores and retrieves repair knowledge in an auditable SQLite database. It can ingest approved local documentation, capsule notes, README/manual content, and diagnostic evidence. Runtime logs are treated as low-trust evidence rather than executable instructions.

Repair proposals are ranked by component, failure signature, text overlap, and trust score.

## Live evidence adapters

Nova can currently collect evidence from:

- local `llama.cpp` / GGUF status
- Nova runtime logs
- llama.cpp logs
- MQTT logs
- local documentation and manuals
- portable capsule metadata and notes
- protected-sandbox configuration

Recognized signatures include Python tracebacks, permission failures, SQLite lock errors, GGUF/model load failures, local LLM server outages, out-of-memory errors, MQTT disconnects, and MQTT connection refusals.

## Low-risk repair handlers

The first explicit low-risk handler framework is now present for:

- MQTT reconnect + connectivity verification
- local llama.cpp restart + API verification

These handlers are callback-based and require a sandbox check before execution. If the host has not explicitly supplied both an execution callback and a verification callback, Nova registers no repair for that action.

This keeps the repair surface small and prevents the language model from inventing shell commands.

## Self-Healing Dashboard

Nova's main touchscreen/web UI now includes a **Self-Healing** tile. It calls the read-only `/api/healing/status` endpoint and shows:

- current probe health
- detected failure signatures
- high-trust Repair Librarian proposals
- knowledge items loaded
- whether repair execution is enabled or gated

The dashboard escapes diagnostic/log content before rendering it and does not expose a repair-execution button. Its refresh action only reruns diagnostics. `/api/health` also advertises the current self-healing safety state so other clients can see that diagnostics are enabled while repair execution remains disabled.

## Nova Model Registry

Nova now has a versioned local-model registry at `models/registry.json` plus a read-only `ModelRegistry` loader.

Current candidates:

- **Qwen2.5 1.5B Instruct Q4_K_M** — approved primary model and current default
- **SmolLM2 1.7B Instruct Q4_K_M** — approved fallback/comparison model
- **Gemma 3 1B IT Q4_K_M** — experimental only and blocked from automated install by default

The registry stores provider, repository, GGUF filename, llama.cpp Hugging Face reference, license, quantization, approximate size, role, and approval state. Model weights remain outside Git.

A guarded installer at `scripts/install-model.py` defaults to Qwen2.5, requires explicit model-license acknowledgement, refuses to overwrite an existing model, downloads to a temporary `.part` file, and rejects obviously truncated downloads. `scripts/model-registry.py` exposes registry inspection and approved llama.cpp launch references.

## Portable Nova capsules

Portable capsules can carry model references, offline knowledge, system instructions, and requested capabilities. A default-deny permission broker controls whether the host grants any requested tool access.

The PDF/portable-document concept remains an export/interface layer, not a privileged hardware runtime.

## Repair memory

Nova records repair attempts in SQLite so successful fixes can be prioritized when the same failure signature appears again. Verification failures can trigger rollback and are also recorded.

## Continuous validation

A GitHub Actions workflow is present to validate the protected-sandbox configuration and run the complete pytest suite for pushes and pull requests involving this branch. No completed Actions run has been reported for the latest branch commits yet, so CI should still be treated as pending.

## Current safety state

Diagnostics, the operator dashboard, and the model registry are wired into the experimental branch. Production repair execution remains intentionally gated. The branch should stay separate from `main` until CI passes and the real host callbacks are tested against the protected sandbox.

## Next engineering gates

1. Confirm the full GitHub Actions test suite passes.
2. Dry-run the Qwen2.5 installer and verify registry tests.
3. Benchmark Qwen2.5 and SmolLM2 on the target PC/Pi hardware before selecting a production default.
4. Connect MQTT reconnect to Nova's actual MQTT client implementation.
5. Connect llama.cpp restart to the installed local service manager without exposing arbitrary command execution.
6. Add post-repair telemetry and repair-memory scoring to the dashboard.
7. Test real low-risk handlers inside the protected sandbox.
8. Only after those checks, review the branch for merge into `main`.
