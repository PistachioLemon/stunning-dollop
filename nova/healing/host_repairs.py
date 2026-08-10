from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .engine import SelfHealingEngine
from .models import HealthFinding, RepairHandler, RepairRecipe, RiskLevel


@dataclass
class LowRiskHostActions:
    """Explicit host callbacks for low-risk repairs.

    The system never invents shell commands here. The embedding host must provide
    these callables, which keeps the repair surface small, auditable, and
    testable.
    """

    reconnect_mqtt: Callable[[], None] | None = None
    verify_mqtt: Callable[[], bool] | None = None
    restart_llama: Callable[[], None] | None = None
    verify_llama: Callable[[], bool] | None = None
    sandbox_check: Callable[[str], bool] | None = None


def _sandbox(actions: LowRiskHostActions, recipe_id: str) -> Callable[[HealthFinding], bool]:
    def check(_: HealthFinding) -> bool:
        return bool(actions.sandbox_check and actions.sandbox_check(recipe_id))

    return check


def register_low_risk_repairs(engine: SelfHealingEngine, actions: LowRiskHostActions) -> list[str]:
    """Register only low-risk, named recovery actions that have real callbacks.

    Returns the recipe IDs that were registered. Nothing is registered unless
    both the execution and verification callbacks exist.
    """

    registered: list[str] = []

    if actions.reconnect_mqtt and actions.verify_mqtt:
        recipe = RepairRecipe(
            recipe_id="mqtt-reconnect-v1",
            signature="mqtt_disconnected",
            action="reconnect_mqtt",
            risk=RiskLevel.LOW,
            sandbox_required=True,
            description="Reconnect the configured local MQTT client and verify connectivity.",
        )
        engine.register_recipe(
            recipe,
            RepairHandler(
                execute=lambda _: actions.reconnect_mqtt(),
                verify=lambda _: bool(actions.verify_mqtt()),
                sandbox=_sandbox(actions, recipe.recipe_id),
            ),
        )
        registered.append(recipe.recipe_id)

    if actions.restart_llama and actions.verify_llama:
        recipe = RepairRecipe(
            recipe_id="llama-restart-v1",
            signature="llama_server_unavailable",
            action="restart_llama",
            risk=RiskLevel.LOW,
            sandbox_required=True,
            description="Restart the configured local llama.cpp service and verify its API.",
        )
        engine.register_recipe(
            recipe,
            RepairHandler(
                execute=lambda _: actions.restart_llama(),
                verify=lambda _: bool(actions.verify_llama()),
                sandbox=_sandbox(actions, recipe.recipe_id),
            ),
        )
        registered.append(recipe.recipe_id)

    return registered
