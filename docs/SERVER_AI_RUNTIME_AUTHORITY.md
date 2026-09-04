# Server-Only AI Runtime Authority

Status: evaluation/staging only. This lane does not merge, deploy, or install a runtime.

## Architecture rule

Raspberry Pi truck nodes are deterministic edge controllers. They may collect telemetry, enforce Security Guard policy, journal events, operate degraded/offline, and execute approved named actions. They do not run TruckLM, Librarian inference, federated training, or llama.cpp.

The mini-PC/server is the only deployment role permitted to execute local AI models.

## Promotion chain

`server role -> llama.cpp source identity -> verified provenance -> binary SHA-256 -> approved GGUF identity/digest -> benchmark -> tool JSON test -> restart recovery -> soak -> operator approval`

The evaluator consumes externally verified provenance claims. It does not claim to perform SLSA cryptographic verification itself.

## Required runtime evidence

- deployment role equals `server`
- exact llama.cpp repository and commit
- llama.cpp binary SHA-256
- provenance present and verified
- provenance repository and workflow match approved values
- exact model ID and GGUF SHA-256
- quantization and context size
- benchmark pass
- structured tool JSON pass
- restart recovery pass
- soak pass
- explicit operator approval

Any missing or contradictory evidence rejects promotion. No provenance-to-hash silent downgrade is allowed.

## Model registry correction

The model registry now describes compact/HQ models as server-side roles. Historical wording implying a permanent AI "truck brain" on Raspberry Pi is removed. Truck-side config continues to set `local_llm.enabled: false`.

## Test plan

Software simulation:

1. valid server release -> approved
2. truck-edge role -> rejected
3. modified llama binary -> rejected
4. missing/unverified provenance -> rejected
5. wrong repository/workflow -> rejected
6. corrupted/swapped GGUF -> rejected
7. benchmark/tool/restart/soak failure -> rejected
8. missing operator approval -> rejected
9. server launch command allowed only for approved models
10. truck-edge launch command denied

Bench/server validation before any production promotion:

- verify provenance with the approved external verifier
- record observed llama.cpp binary digest
- record GGUF digest
- tokens/sec and time-to-first-token
- peak RAM/CPU/temperature
- long-context retrieval
- structured tool-call reliability
- corrupted model rejection
- process restart recovery
- WAN-disconnected local operation
- 8-12 hour soak
- rollback to previous approved runtime

No Raspberry Pi AI workload should be introduced by this lane.
