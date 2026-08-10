from __future__ import annotations

from dataclasses import asdict
from typing import Callable

from .memory import RepairMemory
from .models import HealthFinding, RepairHandler, RepairRecipe, RiskLevel


class SelfHealingEngine:
    """Fail-closed self-healing controller.

    It never executes arbitrary shell text. The host must register named handlers.
    Low-risk repairs may auto-run. Medium/high-risk repairs can be held for approval.
    Sandboxed recipes must provide and pass a sandbox callback before execution.
    """

    def __init__(
        self,
        memory: RepairMemory | None = None,
        *,
        enabled: bool = True,
        auto_risk: RiskLevel = RiskLevel.LOW,
    ):
        self.enabled = enabled
        self.auto_risk = auto_risk
        self.memory = memory or RepairMemory()
        self._probes: dict[str, Callable[[], HealthFinding]] = {}
        self._recipes: list[RepairRecipe] = []
        self._handlers: dict[str, RepairHandler] = {}

    def register_probe(self, name: str, probe: Callable[[], HealthFinding]) -> None:
        self._probes[name] = probe

    def register_recipe(self, recipe: RepairRecipe, handler: RepairHandler) -> None:
        self._recipes.append(recipe)
        self._handlers[recipe.action] = handler

    def diagnose(self) -> list[HealthFinding]:
        findings: list[HealthFinding] = []
        for name, probe in self._probes.items():
            try:
                finding = probe()
            except Exception as exc:
                finding = HealthFinding(
                    issue_id=f"probe:{name}",
                    component=name,
                    signature="probe_exception",
                    healthy=False,
                    details={"error": str(exc)},
                )
            findings.append(finding)
        return findings

    def _candidate_recipes(self, finding: HealthFinding) -> list[RepairRecipe]:
        candidates = [recipe for recipe in self._recipes if recipe.signature == finding.signature]
        return sorted(
            candidates,
            key=lambda recipe: self.memory.score(finding.signature, recipe.recipe_id),
            reverse=True,
        )

    def run_cycle(self, approved_recipe_ids: set[str] | None = None) -> dict:
        approvals = approved_recipe_ids or set()
        report = {"enabled": self.enabled, "findings": [], "repairs": []}
        findings = self.diagnose()
        report["findings"] = [asdict(finding) for finding in findings]
        if not self.enabled:
            return report

        for finding in findings:
            if finding.healthy:
                continue
            candidates = self._candidate_recipes(finding)
            if not candidates:
                report["repairs"].append({"issue_id": finding.issue_id, "status": "no_recipe"})
                continue

            recipe = candidates[0]
            handler = self._handlers[recipe.action]
            allowed = recipe.risk <= self.auto_risk or recipe.recipe_id in approvals
            if not allowed:
                report["repairs"].append(
                    {
                        "issue_id": finding.issue_id,
                        "recipe_id": recipe.recipe_id,
                        "status": "approval_required",
                        "risk": recipe.risk.name.lower(),
                    }
                )
                continue

            if recipe.sandbox_required:
                if handler.sandbox is None or not handler.sandbox(finding):
                    self.memory.record(finding.signature, recipe.recipe_id, False)
                    report["repairs"].append(
                        {
                            "issue_id": finding.issue_id,
                            "recipe_id": recipe.recipe_id,
                            "status": "sandbox_failed",
                        }
                    )
                    continue

            rolled_back = False
            try:
                handler.execute(finding)
                verified = bool(handler.verify(finding))
                if not verified and handler.rollback is not None:
                    handler.rollback(finding)
                    rolled_back = True
                self.memory.record(finding.signature, recipe.recipe_id, verified, rolled_back)
                report["repairs"].append(
                    {
                        "issue_id": finding.issue_id,
                        "recipe_id": recipe.recipe_id,
                        "status": "healed" if verified else "verification_failed",
                        "rolled_back": rolled_back,
                    }
                )
            except Exception as exc:
                if handler.rollback is not None:
                    try:
                        handler.rollback(finding)
                        rolled_back = True
                    except Exception:
                        pass
                self.memory.record(finding.signature, recipe.recipe_id, False, rolled_back)
                report["repairs"].append(
                    {
                        "issue_id": finding.issue_id,
                        "recipe_id": recipe.recipe_id,
                        "status": "repair_failed",
                        "rolled_back": rolled_back,
                        "error": str(exc),
                    }
                )
        return report
