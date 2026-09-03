from __future__ import annotations

from dataclasses import dataclass

from nova.logistics.edge_ledger import append_record, verify_chain
from nova.logistics.epcis import FreightEvent


@dataclass(frozen=True)
class BidScenario:
    gross_rate: float
    fuel_cost: float
    tolls: float
    other_trip_costs: float
    tax_reserve_pct: float
    minimum_net: float
    operator_approved: bool


@dataclass(frozen=True)
class BidResult:
    net_after_reserve: float
    acceptable: bool
    executable: bool


@dataclass(frozen=True)
class SystemScenario:
    dispatch_ready: bool
    route_safe: bool
    permits_valid: bool
    telematics_healthy: bool
    reefer_temp_ok: bool
    cargo_secure: bool
    payment_path_ready: bool
    recovery_ready: bool
    bid: BidScenario


@dataclass(frozen=True)
class SimulationResult:
    passed: bool
    stages: tuple[str, ...]
    failures: tuple[str, ...]
    bid: BidResult
    ledger_events: int


def evaluate_bid(bid: BidScenario) -> BidResult:
    pretax_net = bid.gross_rate - bid.fuel_cost - bid.tolls - bid.other_trip_costs
    reserve = max(0.0, pretax_net) * (bid.tax_reserve_pct / 100.0)
    net = pretax_net - reserve
    acceptable = net >= bid.minimum_net
    return BidResult(round(net, 2), acceptable, acceptable and bid.operator_approved)


def _freight_event(event_id: str, event_type: str, location: str, *, temp: float | None = None) -> FreightEvent:
    sensor = {} if temp is None else {"type": "temperature", "value": temp, "uom": "CEL"}
    return FreightEvent(
        event_id=event_id,
        event_type=event_type,
        occurred_at="2026-09-03T18:00:00+00:00",
        object_ids=("urn:sscc:SIM-001",),
        location=location,
        business_step=event_type,
        sensor=sensor,
    )


def run_end_to_end_simulation(scenario: SystemScenario) -> SimulationResult:
    stages: list[str] = []
    failures: list[str] = []

    bid_result = evaluate_bid(scenario.bid)
    if bid_result.acceptable:
        stages.append("bid_profitable")
    else:
        failures.append("bid_below_minimum")
    if bid_result.executable:
        stages.append("bid_operator_approved")
    else:
        failures.append("bid_not_executable")

    gates = {
        "dispatch_ready": scenario.dispatch_ready,
        "route_safe": scenario.route_safe,
        "permits_valid": scenario.permits_valid,
        "telematics_healthy": scenario.telematics_healthy,
        "reefer_temp_ok": scenario.reefer_temp_ok,
        "cargo_secure": scenario.cargo_secure,
        "payment_path_ready": scenario.payment_path_ready,
        "recovery_ready": scenario.recovery_ready,
    }
    for name, value in gates.items():
        if value:
            stages.append(name)
        else:
            failures.append(name)

    records = []
    if not failures:
        for event in (
            _freight_event("arrival", "ARRIVAL", "shipper-dock"),
            _freight_event("receiving", "RECEIVING", "shipper-dock"),
            _freight_event("loading", "LOADING", "shipper-dock"),
            _freight_event("temperature", "OBSERVATION", "trailer", temp=2.0),
            _freight_event("shipping", "SHIPPING", "shipper-dock"),
            _freight_event("delivery", "DELIVERY", "receiver-dock"),
            _freight_event("pod", "POD", "receiver-dock"),
        ):
            records.append(append_record(records, event))
        ledger_ok, ledger_failures = verify_chain(records)
        if ledger_ok:
            stages.extend(("shipping_complete", "receiving_complete", "pod_complete", "ledger_verified"))
        else:
            failures.extend(ledger_failures)

    return SimulationResult(not failures, tuple(stages), tuple(failures), bid_result, len(records))
