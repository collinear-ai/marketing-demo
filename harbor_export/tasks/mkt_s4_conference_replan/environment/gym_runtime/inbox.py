"""
Inbox — unread-message queue for the agent.

When an NPC responds to an agent action, the NPC simulator drops the reply
into the inbox rather than returning it synchronously from the tool call. The
agent then sees incoming messages by calling the `check_inbox` tool, which
mirrors how real assistants discover new messages between their own actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class InboxItem:
    channel: str                          # "slack", "email", "encrypted_email", "teams", "phone", "pagerduty", ...
    from_id: str                          # persona_id or external handle
    to_id: str                            # usually "agent" or the principal's id
    timestamp: datetime
    subject: str | None = None
    body: str = ""
    thread_id: str | None = None
    read: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def format(self) -> str:
        header = f"[{self.channel.upper()}] {self.timestamp.isoformat()} from {self.from_id}"
        if self.subject:
            header += f"\nSubject: {self.subject}"
        return f"{header}\n{self.body}"


@dataclass
class Inbox:
    items: list[InboxItem] = field(default_factory=list)

    def deliver(self, item: InboxItem) -> None:
        self.items.append(item)

    def unread(self) -> list[InboxItem]:
        return [i for i in self.items if not i.read]

    def unread_by_channel(self, channel: str) -> list[InboxItem]:
        return [i for i in self.items if not i.read and i.channel == channel]

    def mark_all_read(self) -> int:
        n = 0
        for item in self.items:
            if not item.read:
                item.read = True
                n += 1
        return n

    def snapshot(self, only_unread: bool = True) -> str:
        """Produce a human-readable dump for tool results / debug."""
        items = self.unread() if only_unread else self.items
        if not items:
            return "(inbox empty)"
        return "\n\n---\n\n".join(i.format() for i in items)
