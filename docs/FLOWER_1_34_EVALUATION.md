# Flower 1.34 Federation Evaluation

Status: evaluation only. Do not promote, deploy, or train on the Raspberry Pi 5 from this document.

## Architecture boundary

- Raspberry Pi 5 truck node: deterministic data collection, journaling, MQTT, device permissions, and approved training-artifact capture only.
- Mini-PC/server nodes: federated-learning participants and coordination workloads.
- Security Guard: validates participant identity and model/update promotion policy.

## Comparison

Baseline: Flower 1.33
Candidate: Flower 1.34

Use identical datasets, seeds, federation topology, client counts, and server hardware for both runs.

Measure:

1. convergence rounds;
2. peak RAM and CPU;
3. client failures/dropouts;
4. malicious-update rejection;
5. reproducibility;
6. interrupted-round recovery;
7. coordinator/process restart recovery;
8. persistence/database failures after forced interruption;
9. participant dropout and later rejoin.

## Promotion gate

Flower 1.34 is not promoted merely because it is newer. The candidate must show a decisive measured improvement and must not regress persistence, restart recovery, or reproducibility. A hard regression in those areas keeps 1.33 as the preferred version regardless of aggregate score.

## Hardware test

Run the final comparison on the intended mini-PC/server hardware with local networking. Include a forced process kill and power-loss/restart scenario against the evaluation database. Do not represent GitHub CI as proof of physical power-loss durability.
