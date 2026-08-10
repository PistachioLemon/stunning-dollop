# Nova Portable Capsules (experimental)

Nova Capsules adapt the self-contained local-AI-document idea into Nova without making PDF JavaScript the trusted runtime.

## Architecture

A capsule can package or reference:

- a small GGUF model for llama.cpp
- a system prompt
- offline knowledge/manual files
- a manifest of requested host tools
- metadata for future portable exports, including experimental PDF exports

The Nova host remains the security boundary. Capsules never receive direct access to files, cameras, messaging, sensors, GPIO, shell commands, Home Assistant, or other host capabilities merely because they request them.

```text
Capsule / portable document
        |
        | structured tool request
        v
Nova PermissionBroker  -- default deny
        |
        +--> approved host adapter --> sensor / camera / GPIO / MQTT / etc.
```

A tool is authorized only when both conditions are true:

1. the capsule declares the tool in `requested_tools`; and
2. the Nova host explicitly allowlists that tool.

## Why not put Nova entirely inside a PDF?

PDF JavaScript support varies by viewer and is deliberately restricted. A future PDF exporter can therefore be treated as a degraded/offline interface, while the normal Nova host continues to provide llama.cpp inference and controlled tools when available.

## Current prototype

`nova/capsules.py` contains:

- `CapsuleManifest` for loading and hashing capsule manifests
- `PermissionBroker` for default-deny capability authorization

`capsules/example-manual/capsule.json` demonstrates an offline manual capsule requesting `read_sensor` without automatically receiving that permission.

## Next experimental stage

Do not merge into the main Nova runtime until tested and explicitly approved.

1. Add a capsule loader that validates paths and hashes packaged knowledge.
2. Add a local llama.cpp capsule inference adapter.
3. Define typed tool-request/result envelopes.
4. Add auditable user approval for privileged capabilities.
5. Build an optional PDF export proof of concept only after the host architecture passes tests.
