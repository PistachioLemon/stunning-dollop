from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Rule:
    rule_id: str
    trigger: str
    action: str
    description: str = ""
    enabled: bool = True


class TruckingRuleEngine:
    """Small deterministic if-this-then-that layer for Nova trucking workflows.

    Rules map named triggers to named actions. The engine never evaluates
    arbitrary Python or shell text. Host code must register both trigger
    evaluators and action callbacks explicitly.
    """

    def __init__(self):
        self._rules: list[Rule] = []
        self._triggers: dict[str, Callable[[dict[str, Any]], bool]] = {}
        self._actions: dict[str, Callable[[dict[str, Any]], Any]] = {}

    def register_trigger(self, name: str, evaluator: Callable[[dict[str, Any]], bool]) -> None:
        self._triggers[name] = evaluator

    def register_action(self, name: str, callback: Callable[[dict[str, Any]], Any]) -> None:
        self._actions[name] = callback

    def add_rule(self, rule: Rule) -> None:
        self._rules.append(rule)

    def evaluate(self, context: dict[str, Any], *, execute: bool = False) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for rule in self._rules:
            if not rule.enabled:
                continue
            trigger = self._triggers.get(rule.trigger)
            if trigger is None:
                results.append({"rule_id": rule.rule_id, "status": "missing_trigger"})
                continue
            matched = bool(trigger(context))
            item: dict[str, Any] = {
                "rule_id": rule.rule_id,
                "matched": matched,
                "action": rule.action,
                "description": rule.description,
            }
            if matched and execute:
                action = self._actions.get(rule.action)
                if action is None:
                    item["status"] = "missing_action"
                else:
                    item["result"] = action(context)
                    item["status"] = "executed"
            elif matched:
                item["status"] = "actionable"
            else:
                item["status"] = "not_matched"
            results.append(item)
        return results
