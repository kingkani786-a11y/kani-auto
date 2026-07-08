"""Signal Lifecycle + Entry Trigger Engine.

States: SETUP -> WATCH -> ARMED -> TRIGGERED -> ENTRY -> TARGET -> EXIT
The state machine is fed by every AI cycle (context) and every spot tick
(price). Trigger levels come from structure: breakout level above /
breakdown level below, with the opposite level as invalidation.
"""
from __future__ import annotations

import time
from typing import Any


class Lifecycle:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.state = "SETUP"
        self.direction = "NONE"
        self.trigger: float | None = None
        self.invalidation: float | None = None
        self.entry: float | None = None
        self.stop: float | None = None
        self.targets: list[float] = []
        self.targets_hit = 0
        self.updated = time.time()
        self.history: list[dict] = []

    def _go(self, state: str, note: str = "") -> None:
        if state != self.state:
            self.history.append({"ts": time.time(), "from": self.state, "to": state, "note": note})
            self.history = self.history[-20:]
            self.state = state
            self.updated = time.time()

    # ---- called each AI cycle with fresh confluence context ----
    def on_analysis(self, packet: dict[str, Any], structure: dict[str, Any], spot: float) -> None:
        sig = packet["signal"]
        warning = packet.get("warning") or {}
        res = structure.get("resistance") or 0
        sup = structure.get("support") or 0

        if self.state in ("ENTRY", "TARGET"):
            return  # in-trade states are price-managed, not analysis-managed

        if sig["signal"] != "NO TRADE":
            self.direction = sig["direction"]
            self.entry = sig["entry"]
            self.stop = sig["stop_loss"]
            self.targets = [sig["target1"], sig["target2"], sig["target3"]]
            if self.direction == "BULL":
                self.trigger = max(res, spot) if res > spot else spot
                self.invalidation = sig["stop_loss"]
            else:
                self.trigger = min(sup, spot) if 0 < sup < spot else spot
                self.invalidation = sig["stop_loss"]
            # if price already through the trigger, it's live immediately
            crossed = (spot >= self.trigger) if self.direction == "BULL" else (spot <= self.trigger)
            self._go("TRIGGERED" if crossed else "ARMED",
                     f"{sig['signal']} confirmed at {sig['confidence']}%")
            if crossed:
                self._go("ENTRY", f"entry active at {spot:.1f}")
        elif warning.get("setup") not in (None, "NONE"):
            self.direction = "BULL" if warning["setup"] == "BULLISH_FORMING" else "BEAR"
            self.trigger = res if self.direction == "BULL" else sup
            self.invalidation = sup if self.direction == "BULL" else res
            self._go("WATCH" if warning.get("preparation", 0) >= 60 else "SETUP",
                     f"{warning['setup']} prep {warning.get('preparation')}%")
        else:
            if self.state in ("ARMED", "WATCH"):
                self._go("SETUP", "confluence faded — disarming")
            self.direction = "NONE"
            self.trigger = self.invalidation = None

    # ---- called on every spot tick (cheap) ----
    def on_tick(self, spot: float) -> bool:
        """Returns True when the state changed (caller broadcasts/alerts)."""
        before = self.state
        d = 1 if self.direction == "BULL" else -1 if self.direction == "BEAR" else 0
        if not d or not spot:
            return False

        if self.state == "ARMED" and self.trigger:
            if (spot - self.trigger) * d >= 0:
                self._go("TRIGGERED", f"trigger {self.trigger:.1f} crossed")
                self._go("ENTRY", f"entry active at {spot:.1f}")
            elif self.invalidation and (spot - self.invalidation) * d <= 0:
                self._go("EXIT", "invalidation hit before trigger")
                self.reset_soft()
        elif self.state in ("ENTRY", "TARGET"):
            if self.stop and (spot - self.stop) * d <= 0:
                self._go("EXIT", f"stop loss {self.stop:.1f} hit")
                self.reset_soft()
            else:
                while self.targets_hit < len(self.targets) and \
                        (spot - self.targets[self.targets_hit]) * d >= 0:
                    self.targets_hit += 1
                    self._go("TARGET", f"target {self.targets_hit} reached")
                if self.targets_hit >= len(self.targets):
                    self._go("EXIT", "all targets achieved")
                    self.reset_soft()
        return self.state != before

    def reset_soft(self) -> None:
        # keep EXIT visible until next analysis cycle re-evaluates
        self.direction = "NONE"
        self.targets_hit = 0

    def snapshot(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "direction": self.direction,
            "trigger_price": self.trigger,
            "invalidation_price": self.invalidation,
            "breakout_level": self.trigger if self.direction == "BULL" else None,
            "breakdown_level": self.trigger if self.direction == "BEAR" else None,
            "entry": self.entry,
            "stop": self.stop,
            "targets": self.targets,
            "targets_hit": self.targets_hit,
            "updated": self.updated,
            "history": self.history[-6:],
        }
