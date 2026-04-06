"""
Simulated clock.

Agent actions advance sim time deterministically. This lets scenarios evaluate
behavior that depends on time-of-day (working hours, deadlines, earnings
blackouts) without requiring the agent to wait in wall-clock time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


@dataclass
class SimClock:
    now: datetime
    anchor_tz: str = "America/New_York"

    def advance(self, minutes: float) -> None:
        self.now = self.now + timedelta(minutes=minutes)

    def advance_to(self, target: datetime) -> None:
        if target < self.now:
            raise ValueError(f"Cannot advance clock backward: {self.now} -> {target}")
        self.now = target

    def local(self, tz: str | None = None) -> datetime:
        return self.now.astimezone(ZoneInfo(tz or self.anchor_tz))

    def iso(self) -> str:
        return self.now.isoformat()

    def __str__(self) -> str:
        return f"SimClock({self.iso()})"
