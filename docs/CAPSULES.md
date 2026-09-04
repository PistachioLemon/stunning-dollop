# RequantAi Portable Capsules

Capsules package model references, offline knowledge, prompts, and requested tools. The RequantAi host remains the security boundary: requested tools receive no access unless the Permission Broker explicitly allows them. Capsules cannot execute arbitrary shell text or directly access vehicle buses, files, cameras, GPIO, or MQTT.

PDF exports are human-facing references, not privileged runtimes.
