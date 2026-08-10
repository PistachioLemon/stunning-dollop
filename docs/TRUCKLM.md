# Requant TruckLM Development Plan

Nova's truck node should use a compact always-loaded language model and obtain detailed/current domain knowledge through retrieval, tools, and controlled research.

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
2. Evaluation set: create trucking questions, scenarios, classifications, and structured tool-call tasks.
3. Tune only after the dataset is clean and rights are understood.
4. Quantize the tuned model to GGUF and benchmark memory, speed, accuracy, and tool-call reliability on the Pi 5 target.
5. Keep changing regulations and rate/service information in retrieval rather than baking volatile facts permanently into the weights.

This gives Nova a true trucking-oriented LM without forcing the tiny model to memorize every manual, regulation, carrier rule, or parcel standard.
