from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RouteExpectation:
    case_id: str
    expected_status: str
    forbidden_road_ids: tuple[str, ...] = ()
    max_distance_delta_pct: float = 10.0


@dataclass(frozen=True)
class RouteObservation:
    case_id: str
    status: str
    road_ids: tuple[str, ...]
    distance_km: float
    baseline_distance_km: float


@dataclass(frozen=True)
class RouteRegressionResult:
    case_id: str
    passed: bool
    reasons: tuple[str, ...]


def evaluate_route(expectation: RouteExpectation, observation: RouteObservation) -> RouteRegressionResult:
    reasons: list[str] = []
    if observation.status != expectation.expected_status:
        reasons.append(f"status:{observation.status}!={expectation.expected_status}")

    forbidden = set(expectation.forbidden_road_ids)
    hit = forbidden.intersection(observation.road_ids)
    if hit:
        reasons.append("forbidden_roads:" + ",".join(sorted(hit)))

    if observation.baseline_distance_km > 0:
        delta_pct = abs(observation.distance_km - observation.baseline_distance_km) / observation.baseline_distance_km * 100
        if delta_pct > expectation.max_distance_delta_pct:
            reasons.append(f"distance_delta_pct:{delta_pct:.2f}")

    return RouteRegressionResult(expectation.case_id, not reasons, tuple(reasons))


def evaluate_suite(expectations: Iterable[RouteExpectation], observations: Iterable[RouteObservation]) -> list[RouteRegressionResult]:
    by_id = {item.case_id: item for item in observations}
    results: list[RouteRegressionResult] = []
    for expected in expectations:
        observed = by_id.get(expected.case_id)
        if observed is None:
            results.append(RouteRegressionResult(expected.case_id, False, ("missing_observation",)))
            continue
        results.append(evaluate_route(expected, observed))
    return results
