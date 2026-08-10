# Requant TruckLM Development Plan

Nova's truck node should use a compact always-loaded language model and obtain detailed/current domain knowledge through retrieval, tools, controlled research, and compact knowledge packs.

## Primary model strategy

- SmolLM2 360M Instruct Q4_K_M is the primary development base.
- Qwen2.5 1.5B Q4_K_M remains a quality/reference benchmark for desktop or HQ nodes.
- The truck-node objective is a small TruckLM specialized around trucking language, workflow selection, structured outputs, fault classification, dispatch reasoning, and tool selection.

## Domain knowledge pipeline

Knowledge should be collected as cited evidence before it is considered for model training.

Priority domains:

- CDL and commercial-driver training
- FMCSA hours of service and ELD guidance
- cargo securement and load inspection
- shipping and receiving
- bills of lading and freight documentation
- dispatch and route operations
- reefer and temperature-sensitive freight
- parcel and postal shipping
- warehouse receiving and exception handling
- vehicle, trailer, sensor, CAN/OBD, MQTT, and edge-device troubleshooting

## Controlled web research

Nova should not crawl the open web indiscriminately. `data/trucking_sources.json` defines an allowlist of trusted sources. Initial sources prioritize FMCSA, state CDL material, and USPS manuals/standards.

A web-research adapter may fetch approved pages, but fetched content is evidence only. It cannot execute tools, shell commands, repairs, or host actions. The system records the source URL, retrieval time, source class, and trust score. Copyrighted material should be summarized/indexed rather than copied wholesale unless redistribution or training rights are clear.

Private trucking-school manuals, paid curricula, or restricted course material require permission before bulk ingestion or use as training data.

## Compact knowledge-pack architecture

Quantization applies to neural-network weights; it is not a useful general compression method for manuals, code, regulations, or PDFs. Nova therefore uses the right storage format for each kind of asset:

- GGUF quantization for TruckLM model weights.
- Nova Knowledge Packs (`*.nkp.zip`) for text, JSONL, manual summaries, rules, and retrieval chunks.
- SQLite/FTS for live mutable indexes and repair memory after data is promoted into Nova's local data directory.
- PDF as a human-facing export or portable reference, not the primary machine-runtime database.

`nova/knowledge_pack.py` can read a ZIP entry on demand without extracting the whole archive to disk. The requested entry is decompressed into bounded memory and used directly by Nova. Large libraries should be divided into independent numbered packs such as:

`truck-core-0001.nkp.zip`
`truck-fmcsa-0001.nkp.zip`
`truck-usps-0001.nkp.zip`
`truck-repair-0001.nkp.zip`

This is preferred over a traditional split ZIP (`.z01`, `.z02`, `.zip`) because traditional split archives normally depend on all volumes and the final central directory. Independent packs allow a truck node to mount only the knowledge it needs.

Every pack contains a manifest with per-entry SHA-256 hashes. Nova verifies entries while streaming them. This lets updates replace one small pack instead of replacing the entire knowledge library.

Pure Python modules can also be distributed in ZIP-compatible packages in some cases, but executable/privileged host actions remain registered outside knowledge packs. Native libraries and services still require normal installation because they need operating-system loaders, permissions, or real filesystem paths.

## If-this-then-that actions

`nova/trucking_rules.py` provides a deterministic rule layer. Example future rules:

- IF reefer temperature exceeds allowed range THEN create a temperature exception and alert the driver.
- IF a load-securement check fails THEN block departure status and open the securement checklist.
- IF remaining HOS cannot cover the planned leg THEN request route/appointment replanning.
- IF MQTT truck-node heartbeat disappears THEN enter diagnostics and propose the registered reconnect workflow.
- IF receiving reports damaged freight THEN open chain-of-custody evidence capture.

The model may recommend a rule or tool, but only named host-registered actions may execute.

## Learning path

1. Retrieval first: build a cited TruckLM knowledge library from trusted sources.
2. Package stable retrieval material into independently readable Nova Knowledge Packs.
3. Evaluation set: create trucking questions, scenarios, classifications, and structured tool-call tasks.
4. Tune only after the dataset is clean and rights are understood.
5. Quantize the tuned model to GGUF and benchmark memory, speed, accuracy, and tool-call reliability on the Pi 5 target.
6. Keep changing regulations and rate/service information in retrieval rather than baking volatile facts permanently into the weights.

This gives Nova a true trucking-oriented LM without forcing the tiny model to memorize every manual, regulation, carrier rule, or parcel standard.
