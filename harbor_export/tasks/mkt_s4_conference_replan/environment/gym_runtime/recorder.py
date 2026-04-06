"""
Action log recorder.

Builds up a list[gym_core.Action] as the session runs, then hands it off to
the scenario's ScenarioVerifier for scoring. Also supports JSONL export of the
trajectory for downstream analysis (e.g. training data, error review).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from gym_core import Action, ActionType


@dataclass
class ActionRecorder:
    actions: list[Action] = field(default_factory=list)

    def record(self, action: Action) -> Action:
        self.actions.append(action)
        return action

    def build_and_record(
        self,
        action_type: ActionType,
        timestamp: datetime,
        tool: str,
        **kwargs: Any,
    ) -> Action:
        """Convenience: construct and append an Action in one call."""
        action = Action(
            action_type=action_type,
            timestamp=timestamp,
            tool=tool,
            **kwargs,
        )
        self.actions.append(action)
        return action

    def __len__(self) -> int:
        return len(self.actions)

    def to_jsonl(self) -> str:
        """Serialize the action log as JSONL (one action per line)."""
        return "\n".join(_action_to_json(a) for a in self.actions)

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            f.write(self.to_jsonl())


def _action_to_json(a: Action) -> str:
    return json.dumps({
        "action_type": a.action_type.value,
        "timestamp": a.timestamp.isoformat(),
        "tool": a.tool,
        "recipient": a.recipient,
        "cc": a.cc,
        "bcc": a.bcc,
        "channel": a.channel,
        "subject": a.subject,
        "body": a.body,
        "attachments": a.attachments,
        "attendees": a.attendees,
        "duration_minutes": a.duration_minutes,
        "start_time": a.start_time.isoformat() if a.start_time else None,
        "end_time": a.end_time.isoformat() if a.end_time else None,
        "classification": a.classification,
        "contains_pii": a.contains_pii,
        "contains_phi": a.contains_phi,
        "contains_financials": a.contains_financials,
        "amount": a.amount,
        "currency": a.currency,
        "approval_status": a.approval_status,
        "metadata": a.metadata,
    }, default=str)
