from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable


@dataclass(frozen=True)
class FederationRun:
    version: str
    convergence_rounds: int
    peak_ram_mb: float
    failed_clients: int
    malicious_updates_rejected: int
    reproducible: bool
    interrupted_rounds_recovered: int = 0
    process_restarts_recovered: int = 0
    persistence_failures: int = 0
    rejoined_clients: int = 0


@dataclass(frozen=True)
class FederationComparison:
    preferred: str
    reasons: tuple[str, ...]


def compare_flower_runs(baseline: FederationRun, candidate: FederationRun) -> FederationComparison:
    reasons: list[str] = []
    score_baseline = 0
    score_candidate = 0

    metrics = (
        (candidate.convergence_rounds, baseline.convergence_rounds, "candidate converges in fewer rounds", "baseline converges in fewer rounds", "lower"),
        (candidate.peak_ram_mb, baseline.peak_ram_mb, "candidate uses less peak RAM", "baseline uses less peak RAM", "lower"),
        (candidate.failed_clients, baseline.failed_clients, "candidate has fewer client failures", "baseline has fewer client failures", "lower"),
        (candidate.malicious_updates_rejected, baseline.malicious_updates_rejected, "candidate rejects more malicious updates", "baseline rejects more malicious updates", "higher"),
        (candidate.interrupted_rounds_recovered, baseline.interrupted_rounds_recovered, "candidate recovers more interrupted rounds", "baseline recovers more interrupted rounds", "higher"),
        (candidate.process_restarts_recovered, baseline.process_restarts_recovered, "candidate recovers more process restarts", "baseline recovers more process restarts", "higher"),
        (candidate.persistence_failures, baseline.persistence_failures, "candidate has fewer persistence failures", "baseline has fewer persistence failures", "lower"),
        (candidate.rejoined_clients, baseline.rejoined_clients, "candidate restores more rejoining clients", "baseline restores more rejoining clients", "higher"),
    )
    for candidate_value, baseline_value, candidate_reason, baseline_reason, direction in metrics:
        candidate_better = candidate_value < baseline_value if direction == "lower" else candidate_value > baseline_value
        baseline_better = candidate_value > baseline_value if direction == "lower" else candidate_value < baseline_value
        if candidate_better:
            score_candidate += 1
            reasons.append(candidate_reason)
        elif baseline_better:
            score_baseline += 1
            reasons.append(baseline_reason)

    if candidate.reproducible and not baseline.reproducible:
        score_candidate += 1
        reasons.append("candidate is reproducible")
    elif baseline.reproducible and not candidate.reproducible:
        score_baseline += 1
        reasons.append("baseline is reproducible")

    # Promotion is intentionally conservative: a candidate with a persistence
    # regression, lost restart recovery, or lost reproducibility cannot win on
    # aggregate score alone.
    hard_regression = (
        candidate.persistence_failures > baseline.persistence_failures
        or candidate.process_restarts_recovered < baseline.process_restarts_recovered
        or (baseline.reproducible and not candidate.reproducible)
    )
    if hard_regression:
        reasons.append("candidate has a federation recovery/reproducibility regression")
        return FederationComparison(baseline.version, tuple(reasons))

    preferred = candidate.version if score_candidate > score_baseline else baseline.version
    if score_candidate == score_baseline:
        preferred = "hold"
        reasons.append("no decisive improvement")
    return FederationComparison(preferred, tuple(reasons))


def average_peak_ram(runs: Iterable[FederationRun]) -> float:
    values = [run.peak_ram_mb for run in runs]
    if not values:
        raise ValueError("at least one run is required")
    return mean(values)
