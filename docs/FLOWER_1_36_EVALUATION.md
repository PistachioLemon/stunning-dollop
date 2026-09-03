# Flower 1.36 Evaluation

Status: isolated benchmark only. No production federation upgrade is authorized.

Compare Flower 1.36 against the currently validated federation baseline using RequantAi's local/server deployment model. The Pi 5 is not an AI-training host; federation evaluation belongs on the mini-PC/server side, with truck nodes participating only through the approved edge contract.

Required evidence includes convergence, peak RAM, failed clients, malicious-update rejection, process/persistence recovery, rejoining clients, Runtime API reconnects, WAN-loss recovery, localhost scoping, duplicate content handling, interrupted transfer recovery, node-auth failures, TLS verification, and a long soak.

Hard regressions in recovery, authentication, TLS, localhost scoping, reproducibility, persistence, interrupted transfers, or soak completion block promotion even if throughput improves.

Bench/network simulation should include WAN removal, delayed/reordered packets, repeated reconnects, duplicate model content, interrupted transfer restart, malformed update rejection, and rollback to the previous federation runtime.
