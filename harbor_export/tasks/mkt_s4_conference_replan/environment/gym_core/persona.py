"""
Persona pool loader.

Scenarios keep rich persona definitions in YAML. Verifiers only need a thin
structured view — timezone, working hours, channel preferences, hard
boundaries — which is what this module exposes. All other persona fields
(background, relationships, quirks, pain points) stay in the YAML and are
consumed by the LLM-as-judge rubric evaluator, not by programmatic checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

try:
    import yaml  # type: ignore
except ImportError:                              # pragma: no cover
    yaml = None


@dataclass
class Persona:
    id: str
    name: str
    role: str
    timezone: str = "America/New_York"
    working_hours_start: time = time(9, 0)
    working_hours_end: time = time(17, 0)
    preferred_channel: str | None = None         # "slack", "email", "outlook_encrypted", "phone"
    banned_channels: list[str] = field(default_factory=list)   # channels NEVER to use for this persona
    unavailable_days: list[str] = field(default_factory=list)  # "Tuesday", "Thursday"
    response_time_minutes: int | None = None     # expected response SLA during working hours
    hard_boundary_after_hours: bool = False
    requires_classification_header: bool = False
    reports_to: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)          # full YAML record

    # ------------------------------------------------------------------

    def is_working_hour(self, dt: datetime) -> bool:
        """True iff dt falls within this persona's working hours in their TZ."""
        local = dt.astimezone(ZoneInfo(self.timezone))
        weekday = local.strftime("%A")
        if weekday in ("Saturday", "Sunday"):
            return False
        if weekday in self.unavailable_days:
            return False
        t = local.time()
        return self.working_hours_start <= t <= self.working_hours_end

    def overlapping_window(self, others: list["Persona"]) -> tuple[time, time] | None:
        """Return the intersection of working hours across self+others in self.timezone,
        or None if empty. Days-of-week are ignored (caller picks the day)."""
        tz = ZoneInfo(self.timezone)
        today = datetime.now(tz).date()

        def to_self_tz(p: Persona, t: time) -> time:
            dt = datetime.combine(today, t, tzinfo=ZoneInfo(p.timezone))
            return dt.astimezone(tz).time()

        start = self.working_hours_start
        end = self.working_hours_end
        for p in others:
            s = to_self_tz(p, p.working_hours_start)
            e = to_self_tz(p, p.working_hours_end)
            start = max(start, s)
            end = min(end, e)
        if start >= end:
            return None
        return start, end


@dataclass
class PersonaPool:
    """
    A collection of personas loaded from one or more YAML files. Supports a
    shared _personas.yaml at the domain level plus optional scenario-specific
    overrides.
    """
    personas: dict[str, Persona] = field(default_factory=dict)

    def __contains__(self, persona_id: str) -> bool:
        return persona_id in self.personas

    def __getitem__(self, persona_id: str) -> Persona:
        return self.personas[persona_id]

    def get(self, persona_id: str) -> Persona | None:
        return self.personas.get(persona_id)

    def ids(self) -> list[str]:
        return list(self.personas.keys())

    # ------------------------------------------------------------------
    # loading
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, *paths: str) -> "PersonaPool":
        if yaml is None:
            raise RuntimeError("PyYAML required: `uv add pyyaml`")
        pool = cls()
        for path in paths:
            with open(path) as f:
                data = yaml.safe_load(f)
            records = data.get("personas", data) if isinstance(data, dict) else data
            if records is None:
                continue
            for rec in records:
                p = _persona_from_record(rec)
                pool.personas[p.id] = p
        return pool


def _persona_from_record(rec: dict[str, Any]) -> Persona:
    avail = rec.get("availability", {}) or {}
    wh_str = avail.get("working_hours") or rec.get("working_hours") or "09:00-17:00"
    start, end = _parse_working_hours(wh_str)
    comm = rec.get("communication_style", {}) or {}
    preferred = rec.get("preferred_channel") or _infer_preferred(comm)
    return Persona(
        id=rec["id"],
        name=rec.get("name", rec["id"]),
        role=rec.get("role", ""),
        timezone=rec.get("timezone", "America/New_York"),
        working_hours_start=start,
        working_hours_end=end,
        preferred_channel=preferred,
        banned_channels=rec.get("banned_channels", []) or [],
        unavailable_days=rec.get("unavailable_days")
            or avail.get("unavailable_days", []) or [],
        response_time_minutes=rec.get("response_time_minutes"),
        hard_boundary_after_hours=bool(rec.get("hard_boundary_after_hours", False)),
        requires_classification_header=bool(rec.get("requires_classification_header", False)),
        reports_to=rec.get("reports_to"),
        raw=rec,
    )


def _parse_working_hours(wh: str) -> tuple[time, time]:
    # Accept "07:30–18:30 CT", "08:00-17:30", "8-17", etc. Strip TZ suffix.
    import re
    m = re.match(r"\s*(\d{1,2}):?(\d{0,2})\s*[–\-to]+\s*(\d{1,2}):?(\d{0,2})", wh)
    if not m:
        return time(9, 0), time(17, 0)
    sh, sm, eh, em = m.groups()
    return (
        time(int(sh), int(sm or 0)),
        time(int(eh), int(em or 0)),
    )


def _infer_preferred(comm: dict[str, Any]) -> str | None:
    if "slack" in comm and "email" not in comm:
        return "slack"
    if "email" in comm and "slack" not in comm:
        return "email"
    return None
