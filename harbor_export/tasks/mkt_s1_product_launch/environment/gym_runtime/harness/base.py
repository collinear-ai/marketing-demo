"""
Agent harness interface.

An AgentHarness abstracts whatever backend is driving the agent (Claude,
Gemini, a scripted test double). The Session talks to the harness through a
single `step(messages, tools, system)` method that mirrors the Anthropic
tool-use message format:

    messages = [
        {"role": "user", "content": [{"type": "text", "text": "..."}]},
        {"role": "assistant", "content": [
            {"type": "text", "text": "..."},
            {"type": "tool_use", "id": "...", "name": "...", "input": {...}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "...", "content": "..."},
        ]},
        ...
    ]

The harness returns a structured `AgentResponse` holding the model's text + any
tool_use blocks it emitted. Ports to other SDKs convert into this shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class AgentResponse:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"       # "tool_use" | "end_turn" | "max_tokens" | "error"
    raw: Any = None                      # original SDK response for debug

    def to_assistant_message(self) -> dict:
        """Convert to an Anthropic-shape assistant message for appending to
        the session's message history."""
        content = []
        if self.text:
            content.append({"type": "text", "text": self.text})
        for tc in self.tool_calls:
            content.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.name,
                "input": tc.input,
            })
        return {"role": "assistant", "content": content}


class AgentHarness:
    """Base interface. Subclass for a concrete backend."""

    model: str = "unknown"

    def step(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str,
    ) -> AgentResponse:
        raise NotImplementedError

    def close(self) -> None:
        """Optional cleanup hook."""
        pass
