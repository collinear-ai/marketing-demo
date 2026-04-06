"""
OpenAI Responses API harness.

Drives an agent session against OpenAI reasoning models via the Responses API,
which preserves reasoning state server-side across turns (via
``previous_response_id``) so reasoning tokens are not thrown away between tool
calls. That matters a lot for long-horizon scenarios.

Usage:

    from gym_runtime.harness.openai import OpenAIHarness
    harness = OpenAIHarness(model="gpt-5.4", reasoning_effort="high")

Environment:

    OPENAI_API_KEY must be set, or pass api_key="..." to the constructor.

Statefulness:

    This harness is STATEFUL per Session. It tracks the last response_id and
    the number of Session.messages it has already consumed; on each `step`
    it sends only the delta (new tool_call_outputs and any fresh user input)
    plus ``previous_response_id``. Do not share one instance across Sessions.
"""

from __future__ import annotations

import json
import os
from typing import Any

from gym_runtime.harness.base import AgentHarness, AgentResponse, ToolCall


class OpenAIHarness(AgentHarness):
    def __init__(
        self,
        model: str = "gpt-5",
        reasoning_effort: str | None = "high",
        api_key: str | None = None,
        max_output_tokens: int | None = None,
        extra_client_kwargs: dict | None = None,
    ):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "The OpenAI SDK is required for OpenAIHarness. "
                "Install with: uv sync --extra openai"
            ) from exc

        self.model = model
        self.reasoning_effort = reasoning_effort
        self.max_output_tokens = max_output_tokens
        self.client = OpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY"),
            **(extra_client_kwargs or {}),
        )

        # Per-session state
        self._previous_response_id: str | None = None
        self._messages_seen: int = 0
        # Fallback flag: if "xhigh" (or any unknown effort) is rejected, retry with "high"
        self._effort_downgraded: bool = False

    # ------------------------------------------------------------------

    def step(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str,
    ) -> AgentResponse:
        # Extract only the messages the harness has not yet seen. The Session
        # appends tool_result blocks to the last user message each turn; on
        # turn 1 it's just the kickoff user text.
        new_messages = messages[self._messages_seen:]
        self._messages_seen = len(messages)

        input_items: list[dict] = []
        for msg in new_messages:
            role = msg.get("role")
            content = msg.get("content", [])
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            for block in content:
                btype = block.get("type")
                if role == "user" and btype == "text":
                    input_items.append({
                        "role": "user",
                        "content": [{"type": "input_text", "text": block["text"]}],
                    })
                elif role == "user" and btype == "tool_result":
                    output_val = block.get("content", "")
                    if not isinstance(output_val, str):
                        output_val = str(output_val)
                    input_items.append({
                        "type": "function_call_output",
                        "call_id": block["tool_use_id"],
                        "output": output_val,
                    })
                # assistant blocks are model output — no need to echo them
                # when using previous_response_id (server keeps them).

        kwargs: dict[str, Any] = {
            "model": self.model,
            "input": input_items,
            "tools": self._convert_tools(tools),
        }
        if self._previous_response_id is None:
            # First turn: send system prompt as instructions
            kwargs["instructions"] = system
        else:
            kwargs["previous_response_id"] = self._previous_response_id

        if self.reasoning_effort:
            kwargs["reasoning"] = {"effort": self.reasoning_effort}
        if self.max_output_tokens:
            kwargs["max_output_tokens"] = self.max_output_tokens

        response = self._create_with_fallback(kwargs)
        self._previous_response_id = response.id

        # Parse output items
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for item in response.output:
            itype = getattr(item, "type", None)
            if itype == "message":
                for c in getattr(item, "content", []):
                    ctype = getattr(c, "type", None)
                    if ctype in ("output_text", "text"):
                        text_parts.append(getattr(c, "text", "") or "")
            elif itype == "function_call":
                try:
                    args = json.loads(getattr(item, "arguments", "") or "{}")
                except json.JSONDecodeError:
                    args = {"_raw_arguments": getattr(item, "arguments", "")}
                tool_calls.append(ToolCall(
                    id=getattr(item, "call_id", ""),
                    name=getattr(item, "name", ""),
                    input=args,
                ))
            # reasoning items are preserved server-side via previous_response_id

        return AgentResponse(
            text="\n".join(t for t in text_parts if t) or None,
            tool_calls=tool_calls,
            stop_reason=getattr(response, "status", "completed") or "completed",
            raw=response,
        )

    # ------------------------------------------------------------------

    def _create_with_fallback(self, kwargs: dict) -> Any:
        try:
            return self.client.responses.create(**kwargs)
        except Exception as exc:
            msg = str(exc).lower()
            # If the reasoning.effort value is rejected (e.g. "xhigh"), downgrade once.
            if (
                not self._effort_downgraded
                and self.reasoning_effort
                and ("reasoning" in msg or "effort" in msg or "enum" in msg or "invalid" in msg)
            ):
                self._effort_downgraded = True
                old = self.reasoning_effort
                self.reasoning_effort = "high"
                print(
                    f"[OpenAIHarness] reasoning_effort={old!r} rejected; "
                    f"falling back to 'high'. Error: {exc}",
                    flush=True,
                )
                kwargs["reasoning"] = {"effort": "high"}
                return self.client.responses.create(**kwargs)
            raise

    def _convert_tools(self, anthropic_tools: list[dict]) -> list[dict]:
        """Convert Anthropic tool_use schemas to OpenAI Responses API format.
        Responses API uses a flat shape (no nested 'function' wrapper like
        chat.completions)."""
        out = []
        for t in anthropic_tools:
            out.append({
                "type": "function",
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t["input_schema"],
            })
        return out
