"""
Anthropic Claude harness.

Drives an agent session using the Anthropic Messages API with tool_use. Maps
the Anthropic SDK response shape into the gym_runtime AgentResponse contract
so the Session loop stays SDK-agnostic.

Usage:

    from gym_runtime.harness.anthropic import AnthropicHarness
    harness = AnthropicHarness(model="claude-sonnet-4-5", max_tokens=4096)

Environment:

    ANTHROPIC_API_KEY must be set, or pass api_key="..." to the constructor.
"""

from __future__ import annotations

import os
from typing import Any

from gym_runtime.harness.base import AgentHarness, AgentResponse, ToolCall


class AnthropicHarness(AgentHarness):
    def __init__(
        self,
        model: str = "claude-sonnet-4-5",
        max_tokens: int = 4096,
        api_key: str | None = None,
        extra_client_kwargs: dict | None = None,
    ):
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise ImportError(
                "The Anthropic SDK is required for AnthropicHarness. "
                "Install with: uv sync --extra anthropic"
            ) from exc

        self.model = model
        self.max_tokens = max_tokens
        self.client = Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
            **(extra_client_kwargs or {}),
        )

    # ------------------------------------------------------------------

    def step(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str,
    ) -> AgentResponse:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            tools=tools,
            messages=messages,
        )

        text_chunks: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                text_chunks.append(getattr(block, "text", "") or "")
            elif btype == "tool_use":
                tool_calls.append(ToolCall(
                    id=getattr(block, "id", ""),
                    name=getattr(block, "name", ""),
                    input=dict(getattr(block, "input", {}) or {}),
                ))

        return AgentResponse(
            text="\n".join(c for c in text_chunks if c) or None,
            tool_calls=tool_calls,
            stop_reason=getattr(resp, "stop_reason", "end_turn") or "end_turn",
            raw=resp,
        )
