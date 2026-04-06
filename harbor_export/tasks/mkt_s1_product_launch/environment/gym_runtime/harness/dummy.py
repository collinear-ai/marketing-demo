"""
Test doubles for the AgentHarness interface.

Two flavors:

- DummyHarness: returns end_turn immediately. Useful to prove the session
  plumbing starts, routes messages, and ends cleanly.
- ScriptedHarness: returns a pre-recorded sequence of AgentResponse objects.
  Use for plumbing tests that need to exercise specific tool calls without
  an LLM in the loop.
"""

from __future__ import annotations

from gym_runtime.harness.base import AgentHarness, AgentResponse, ToolCall


class DummyHarness(AgentHarness):
    model = "dummy"

    def __init__(self, finish_immediately: bool = True):
        self.finish_immediately = finish_immediately
        self.step_count = 0

    def step(self, messages, tools, system) -> AgentResponse:
        self.step_count += 1
        if self.finish_immediately:
            return AgentResponse(
                text="(dummy harness — finishing immediately)",
                tool_calls=[ToolCall(
                    id="dummy_finish_1",
                    name="finish_scenario",
                    input={"summary": "dummy harness has no agent logic"},
                )],
                stop_reason="tool_use",
            )
        return AgentResponse(text="(dummy)", stop_reason="end_turn")


class ScriptedHarness(AgentHarness):
    """Replay a list of pre-built AgentResponse objects. Loops forever on the
    last response once exhausted (usually a finish_scenario call)."""
    model = "scripted"

    def __init__(self, script: list[AgentResponse]):
        if not script:
            raise ValueError("ScriptedHarness requires at least one response")
        self.script = script
        self.cursor = 0

    def step(self, messages, tools, system) -> AgentResponse:
        if self.cursor < len(self.script):
            resp = self.script[self.cursor]
            self.cursor += 1
            return resp
        return self.script[-1]
