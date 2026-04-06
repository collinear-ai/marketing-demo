"""
gym_runtime — execution harness for the Long-Horizon Agent Evaluation Gym.

Loads a scenario package authored under gym/domains/<domain>/<scenario>/,
presents it to an agent via a tool-use loop, simulates NPC responses, captures
an action log, and scores it with the scenario's ScenarioVerifier.

Usage:

    uv run python -m gym_runtime.run hr_s1_termination_reorg \\
        --harness anthropic --model claude-sonnet-4-5 \\
        --out trajectories/

Or programmatically:

    from gym_runtime import Scenario, Session, AnthropicHarness
    scenario = Scenario.load("hr_s1_termination_reorg")
    harness = AnthropicHarness(model="claude-sonnet-4-5")
    result = Session(scenario, harness).run()
    print(result.verifier_report.summary())
"""

from gym_runtime.scenario import Scenario, ScenarioIndex
from gym_runtime.clock import SimClock
from gym_runtime.inbox import Inbox, InboxItem
from gym_runtime.recorder import ActionRecorder
from gym_runtime.session import Session, SessionConfig, SessionResult
from gym_runtime.harness.base import AgentHarness, AgentResponse, ToolCall
from gym_runtime.harness.dummy import DummyHarness, ScriptedHarness

__all__ = [
    "ActionRecorder",
    "AgentHarness",
    "AgentResponse",
    "AnthropicHarness",
    "DummyHarness",
    "Inbox",
    "InboxItem",
    "Scenario",
    "ScenarioIndex",
    "ScriptedHarness",
    "Session",
    "SessionConfig",
    "SessionResult",
    "SimClock",
    "ToolCall",
]


def __getattr__(name: str):
    # Lazy import the anthropic harness so gym_runtime works without the SDK installed.
    if name == "AnthropicHarness":
        from gym_runtime.harness.anthropic import AnthropicHarness
        return AnthropicHarness
    raise AttributeError(f"module 'gym_runtime' has no attribute {name!r}")
