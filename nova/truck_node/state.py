from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class DegradedMode(StrEnum):
    NORMAL = "NORMAL"
    SERVER_OFFLINE = "SERVER_OFFLINE"
    WAN_OFFLINE = "WAN_OFFLINE"
    ROUTER_OFFLINE = "ROUTER_OFFLINE"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    GPS_UNAVAILABLE = "GPS_UNAVAILABLE"
    CAN_DEGRADED = "CAN_DEGRADED"
    REEFER_CRITICAL = "REEFER_CRITICAL"
    STORAGE_LOW = "STORAGE_LOW"
    RECOVERY_MODE = "RECOVERY_MODE"


@dataclass
class EdgeState:
    active: set[DegradedMode] = field(default_factory=set)

    def set(self, mode: DegradedMode, enabled: bool = True) -> None:
        if mode is DegradedMode.NORMAL:
            if enabled:
                self.active.clear()
            return
        if enabled:
            self.active.add(mode)
        else:
            self.active.discard(mode)

    def snapshot(self) -> list[str]:
        if not self.active:
            return [DegradedMode.NORMAL.value]
        return sorted(mode.value for mode in self.active)

    def allows_remote_commands(self) -> bool:
        return DegradedMode.RECOVERY_MODE not in self.active

    def allows_financial_or_contractual_actions(self) -> bool:
        blocked = {
            DegradedMode.SERVER_OFFLINE,
            DegradedMode.WAN_OFFLINE,
            DegradedMode.ROUTER_OFFLINE,
            DegradedMode.RECOVERY_MODE,
        }
        return not bool(self.active & blocked)
