# Flower 1.35 Federation Evaluation

Status: isolated mini-PC/server evaluation only.

Baseline: Flower 1.34
Candidate: Flower 1.35

The Raspberry Pi 5 remains a deterministic truck edge node and does not run federated training.

## Focus

Flower 1.35 changes Runtime API behavior and address defaults. RequantAi must verify that the candidate improves or preserves local recovery behavior without widening network exposure.

Measure:

- convergence rounds;
- peak RAM/CPU;
- client failures;
- malicious-update rejection;
- interrupted-round recovery;
- process restart recovery;
- persistence failures;
- participant rejoin;
- Runtime API reconnect failures;
- WAN-loss recovery;
- whether Runtime API endpoints remain localhost-scoped unless explicitly approved.

## Promotion gate

1.35 must show a decisive measured improvement over 1.34 and may not regress persistence, restart recovery, Runtime API reconnection, reproducibility, or localhost-only binding policy.

Do not adopt experimental agent/runtime features into Dispatcher during this evaluation. The goal is federation reliability, not another agent framework.
