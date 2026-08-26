from nova.federation.flower_eval import FederationRun, compare_flower_runs
from nova.routing.regression import RouteExpectation, RouteObservation, evaluate_route


def test_valhalla_regression_flags_forbidden_truck_road():
    expectation = RouteExpectation(
        case_id="low-clearance-bridge",
        expected_status="ok",
        forbidden_road_ids=("bridge-13ft",),
        max_distance_delta_pct=15.0,
    )
    observation = RouteObservation(
        case_id="low-clearance-bridge",
        status="ok",
        road_ids=("i5", "bridge-13ft"),
        distance_km=105.0,
        baseline_distance_km=100.0,
    )
    result = evaluate_route(expectation, observation)
    assert result.passed is False
    assert any(reason.startswith("forbidden_roads") for reason in result.reasons)


def test_valhalla_regression_accepts_expected_route():
    expectation = RouteExpectation("truck-safe", "ok", ("prohibited-road",), 10.0)
    observation = RouteObservation("truck-safe", "ok", ("truck-route-a",), 101.0, 100.0)
    assert evaluate_route(expectation, observation).passed is True


def test_flower_135_candidate_wins_on_runtime_recovery_improvement():
    baseline = FederationRun(
        "1.34", 20, 1500, 2, 8, True,
        interrupted_rounds_recovered=8,
        process_restarts_recovered=5,
        persistence_failures=1,
        rejoined_clients=7,
        runtime_api_reconnect_failures=2,
        wan_loss_recoveries=4,
        runtime_api_bound_localhost=True,
    )
    candidate = FederationRun(
        "1.35", 18, 1450, 1, 9, True,
        interrupted_rounds_recovered=9,
        process_restarts_recovered=6,
        persistence_failures=0,
        rejoined_clients=8,
        runtime_api_reconnect_failures=0,
        wan_loss_recoveries=6,
        runtime_api_bound_localhost=True,
    )
    comparison = compare_flower_runs(baseline, candidate)
    assert comparison.preferred == "1.35"
    assert "candidate has fewer runtime API reconnect failures" in comparison.reasons


def test_flower_holds_when_candidate_is_not_better():
    baseline = FederationRun("1.34", 20, 1400, 1, 9, True, 8, 5, 0, 7, 0, 5, True)
    candidate = FederationRun("1.35", 20, 1400, 1, 9, True, 8, 5, 0, 7, 0, 5, True)
    comparison = compare_flower_runs(baseline, candidate)
    assert comparison.preferred == "hold"


def test_flower_135_cannot_win_with_runtime_api_security_regression():
    baseline = FederationRun("1.34", 20, 1500, 2, 8, True, 8, 5, 0, 7, 0, 5, True)
    candidate = FederationRun("1.35", 15, 1200, 0, 10, True, 10, 6, 0, 9, 0, 6, False)
    comparison = compare_flower_runs(baseline, candidate)
    assert comparison.preferred == "1.34"
    assert any("recovery/security regression" in reason for reason in comparison.reasons)
