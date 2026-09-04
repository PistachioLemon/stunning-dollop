# RequantAi System Recovery

Recovery follows: detect → diagnose → retrieve trusted repair knowledge → select named recipe → sandbox → execute registered handler → verify → rollback if needed → remember outcome.

The truck Pi is a deterministic edge controller. It does not run local LLMs or model training. Truck telemetry is written to a durable append-only journal before synchronization so server or WAN loss does not erase the event trail.

## Truck recovery boundary

- A/B image slots are represented as active and standby slots.
- Recovery manifests carry version, minimum accepted version, target slot, image SHA-256, expiration, and an authenticated manifest signature.
- Rollback versions, expired manifests, invalid image hashes, and invalid signatures are rejected before promotion.
- Recovery mode blocks remote named-action execution until the local recovery health gate clears.
- Production deployments must keep recovery signing material outside Git and provision it through the Security Guard process.

The current authenticated-manifest implementation uses HMAC-SHA256 as the first deterministic trust gate. It is suitable for isolated evaluation but should be replaced by an asymmetric offline-root signing scheme before field release so a compromised truck node cannot mint trusted updates.

Current read-only probes cover llama.cpp/GGUF state on the server, dispatcher logs, MQTT logs, configuration isolation, and trusted local documentation. Repair text is never executed. Production handlers require explicit host callbacks, verification, rollback, and Permission Broker authorization.

The web dashboard exposes diagnostics and proposals; it does not expose arbitrary repair execution.
