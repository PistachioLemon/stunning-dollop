# RequantAi System Recovery

Recovery follows: detect → diagnose → retrieve trusted repair knowledge → select named recipe → sandbox → execute registered handler → verify → rollback if needed → remember outcome.

Current read-only probes cover llama.cpp/GGUF state, dispatcher logs, MQTT logs, configuration isolation, and trusted local documentation. Repair text is never executed. Production handlers require explicit host callbacks, verification, rollback, and Permission Broker authorization.

The web dashboard exposes diagnostics and proposals; it does not expose arbitrary repair execution.
