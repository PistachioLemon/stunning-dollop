# RequantAi Logistics Interoperability Evaluation

Status: approved evaluation lane only. Not merged or deployed.

## A. EPCIS 2.0.1 adapter

RequantAi keeps its own internal freight event vocabulary and maps external EPCIS events through `nova/logistics/epcis.py`. The adapter currently preserves event ID, event time, object identifiers, business step, read point/location, disposition, pallet/container parent-child relationships, and one normalized sensor observation.

Promotion requires round-trip tests for shipping, receiving, aggregation, reefer temperature, damaged freight, seal events, rejected loads, and multi-stop handling. Raw GS1 vocabulary must not leak into Dispatcher decision logic.

## B. Flower 1.33 benchmark

`nova/federation/flower_eval.py` compares measured federation runs only. A newer version is not promoted merely because it is newer. Compare convergence rounds, peak RAM, failed clients, malicious-update rejection, and reproducibility against the validated baseline. Training remains server/mini-PC side; Pi truck nodes collect approved training artifacts only.

## C. Valhalla truck routing regression

`nova/routing/regression.py` defines a golden-route regression gate independent of the routing engine. Candidate Valhalla builds must not introduce forbidden road segments, unexpected status changes, or unacceptable route-length deviations.

The hardware/road-data suite should cover low-clearance bridges, posted weight limits, truck-prohibited roads, toll preference, rural low-class roads, hazmat constraints, and route deviation. Legal permit/compliance decisions remain outside Valhalla and inside RequantAi's deterministic compliance engine.

## D. GS1 Gen2 RFID receiving adapter

`nova/logistics/rfid.py` normalizes RFID reads, suppresses duplicates, and reconciles observed EPCs against the expected receiving set. RFID remains optional hardware. Receiving must continue to support barcode/QR/manual evidence when no reader is present.

Hardware validation must test duplicate reads, missing tags, unexpected tags, mixed barcode/RFID loads, offline operation, reader disconnects, and reconciliation against BOL quantities.
