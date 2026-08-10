# Nova local models

Nova keeps model weights out of Git. Approved/test candidates are tracked in `models/registry.json` and loaded by `nova.model_registry.ModelRegistry`.

The current default candidate is:

- **Qwen2.5 1.5B Instruct Q4_K_M** — primary Nova local model candidate, Apache-2.0

Approved fallback candidate:

- **SmolLM2 1.7B Instruct Q4_K_M** — fallback/comparison candidate, Apache-2.0

Experimental only:

- **Gemma 3 1B IT Q4_K_M** — lightweight evaluation candidate; not approved for automated install because its model license differs from Nova's Apache-2.0 project license

## Inspect the registry

```bash
python scripts/model-registry.py
python scripts/model-registry.py --model qwen2.5-1.5b-instruct-q4_k_m --json
python scripts/model-registry.py --model qwen2.5-1.5b-instruct-q4_k_m --llama-command
```

## Guarded installer

Dry-run first:

```bash
python scripts/install-model.py --dry-run
```

After reviewing the selected model card and license:

```bash
python scripts/install-model.py --accept-license
```

The installer defaults to `models/nova-assistant.gguf`, refuses to overwrite an existing model, downloads through a `.part` file, and rejects obviously truncated downloads. Model weights are never committed to Git.

For direct llama.cpp-managed loading, the registry can produce an approved `-hf` reference instead of downloading the file into Nova.

## Pi 5 envelope

- 1B–1.7B parameters, Q4 quantization: fastest practical everyday choice
- 3B parameters, Q4 quantization: better answers, slower, best with 8–16 GB RAM

Always validate a newly installed model with Nova's health checks and protected sandbox before enabling it in the main runtime.
