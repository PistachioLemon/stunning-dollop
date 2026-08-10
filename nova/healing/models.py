from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable


class RiskLevel(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass(frozen=True)
class HealthFinding:
    issue_id: str
    component: str
    signature: str
    healthy: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RepairRecipe:
    recipe_id: str
    signature: str
    action: str
    risk: RiskLevel = RiskLevel.LOW
    sandbox_required: bool = False
    description: str = ""


@dataclass
class RepairHandler:
    execute: Callable[[HealthFinding], Any]
    verify: Callable[[HealthFinding], bool]
    rollback: Callable[[HealthFinding], Any] | None = None
    sandbox: Callable[[HealthFinding], bool] | None = None
