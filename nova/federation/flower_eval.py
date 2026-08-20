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


@dataclass(frozen=True)
class FederationComparison:
    preferred: str
    reasons: tuple[str, ...]


def compare_flower_runs(baseline: FederationRun, candidate: FederationRun) -> FederationComparison:
    reasons: list[str] = []
    score_baseline = 0
    score_candidate = 0

    if candidate.convergence_rounds < baseline.convergence_rounds:
        score_candidate += 1
        reasons.append("candidate converges in fewer rounds")
    elif candidate.convergence_rounds > baseline.convergence_rounds:
        score_baseline += 1
        reasons.append("baseline converges in fewer rounds")

    if candidate.peak_ram_mb < baseline.peak_ram_mb:
        score_candidate += 1
        reasons.append("candidate uses less peak RAM")
    elif candidate.peak_ram_mb > baseline.peak_ram_mb:
        score_baseline += 1
        reasons.append("baseline uses less peak RAM")

    if candidate.failed_clients < baseline.failed_clients:
        score_candidate += 1
        reasons.append("candidate has fewer client failures")
    elif candidate.failed_clients > baseline.failed_clients:
        score_baseline += 1
        reasons.append("baseline has fewer client failures")

    if candidate.malicious_updates_rejected > baseline.malicious_updates_rejected:
        score_candidate += 1
        reasons.append("candidate rejects more malicious updates")
    elif candidate.malicious_updates_rejected < baseline.malicious_updates_rejected:
        score_baseline += 1
        reasons.append("baseline rejects more malicious updates")

    if candidate.reproducible and not baseline.reproducible:
        score_candidate += 1
        reasons.append("candidate is reproducible")
    elif baseline.reproducible and not candidate.reproducible:
        score_baseline += 1
        reasons.append("baseline is reproducible")

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
