from dataclasses import replace

from nova.simulations.end_to_end import BidScenario, SystemScenario, evaluate_bid, run_end_to_end_simulation


def good_bid():
    return BidScenario(
        gross_rate=4200.0,
        fuel_cost=900.0,
        tolls=150.0,
        other_trip_costs=350.0,
        tax_reserve_pct=20.0,
        minimum_net=2000.0,
        operator_approved=True,
    )


def good_scenario():
    return SystemScenario(
        dispatch_ready=True,
        route_safe=True,
        permits_valid=True,
        telematics_healthy=True,
        reefer_temp_ok=True,
        cargo_secure=True,
        payment_path_ready=True,
        recovery_ready=True,
        bid=good_bid(),
    )


def test_bid_math_and_operator_gate():
    result = evaluate_bid(good_bid())
    assert result.net_after_reserve == 2240.0
    assert result.acceptable is True
    assert result.executable is True


def test_end_to_end_shipping_receiving_and_pod_pass():
    result = run_end_to_end_simulation(good_scenario())
    assert result.passed is True
    assert result.ledger_events == 7
    assert {"shipping_complete", "receiving_complete", "pod_complete", "ledger_verified"}.issubset(result.stages)


def test_unapproved_bid_never_executes():
    scenario = replace(good_scenario(), bid=replace(good_bid(), operator_approved=False))
    result = run_end_to_end_simulation(scenario)
    assert result.passed is False
    assert "bid_not_executable" in result.failures
    assert result.ledger_events == 0


def test_route_permit_or_eld_readiness_blocks_dispatch_flow():
    for field in ("route_safe", "permits_valid", "dispatch_ready"):
        result = run_end_to_end_simulation(replace(good_scenario(), **{field: False}))
        assert result.passed is False
        assert field in result.failures
        assert result.ledger_events == 0


def test_telematics_reefer_cargo_and_payment_fail_closed():
    for field in ("telematics_healthy", "reefer_temp_ok", "cargo_secure", "payment_path_ready", "recovery_ready"):
        result = run_end_to_end_simulation(replace(good_scenario(), **{field: False}))
        assert result.passed is False
        assert field in result.failures
