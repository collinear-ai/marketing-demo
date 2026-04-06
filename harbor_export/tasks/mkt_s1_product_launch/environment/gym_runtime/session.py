"""
Session loop — the main orchestrator.

A Session takes a loaded Scenario and an AgentHarness and runs the agent
through the scenario end-to-end:

    scenario = Scenario.load("hr_s1_termination_reorg")
    harness = AnthropicHarness(model="claude-sonnet-4-5")
    result = Session(scenario, harness).run()
    print(result.verifier_report.summary())
    result.save_trajectory("trajectories/hr_s1_run1.json")

Loop invariant:
1. Build system prompt + initial user message from the scenario briefing.
2. Ask harness for next step.
3. Execute any tool calls via ToolExecutor, append tool_result blocks.
4. Let the NPC simulator tick between turns (scripted events).
5. Stop when executor.finished, max_turns reached, or an unrecoverable error.
6. Run scenario.verifier_cls against the action log, return ScenarioReport.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gym_core import ScenarioVerifier
from gym_core.verifier_base import ScenarioReport
from gym_runtime.clock import SimClock
from gym_runtime.harness.base import AgentHarness, AgentResponse, ToolCall
from gym_runtime.inbox import Inbox
from gym_runtime.npc import NPCSimulator
from gym_runtime.recorder import ActionRecorder
from gym_runtime.scenario import Scenario
from gym_runtime.tools import TOOL_SCHEMAS, ToolExecutor


@dataclass
class SessionConfig:
    max_turns: int = 80
    max_wall_seconds: float = 1200.0
    fail_on_harness_error: bool = True
    use_npc_llm: bool = False


@dataclass
class SessionResult:
    scenario_id: str
    action_log: list = field(default_factory=list)
    verifier_report: ScenarioReport | None = None
    turns_used: int = 0
    tool_calls_made: int = 0
    elapsed_sim_minutes: float = 0.0
    elapsed_wall_seconds: float = 0.0
    stopped_reason: str = "not_run"
    messages: list[dict] = field(default_factory=list)
    finish_summary: str | None = None

    def summary(self) -> dict[str, Any]:
        d = {
            "scenario_id": self.scenario_id,
            "stopped_reason": self.stopped_reason,
            "turns_used": self.turns_used,
            "tool_calls_made": self.tool_calls_made,
            "actions_logged": len(self.action_log),
            "elapsed_sim_minutes": self.elapsed_sim_minutes,
            "elapsed_wall_seconds": self.elapsed_wall_seconds,
            "finish_summary": self.finish_summary,
        }
        if self.verifier_report is not None:
            d["verifier"] = self.verifier_report.summary()
        return d

    def save_trajectory(self, path: str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "summary": self.summary(),
            "messages": self.messages,
        }
        p.write_text(json.dumps(payload, indent=2, default=str))


class Session:
    def __init__(
        self,
        scenario: Scenario,
        harness: AgentHarness,
        config: SessionConfig | None = None,
        npc_llm_client=None,
    ):
        self.scenario = scenario
        self.harness = harness
        self.config = config or SessionConfig()

        self.clock = SimClock(now=scenario.kickoff_time, anchor_tz=scenario.anchor_tz)
        self.inbox = Inbox()
        self.recorder = ActionRecorder()
        self.npc = NPCSimulator(
            personas=scenario.personas,
            clock=self.clock,
            scenario_context=scenario.briefing_text,
            llm_client=npc_llm_client,
            recorder=self.recorder,
        )
        self.executor = ToolExecutor(
            scenario=scenario,
            recorder=self.recorder,
            clock=self.clock,
            inbox=self.inbox,
            npc=self.npc,
        )

    # ------------------------------------------------------------------

    def run(self) -> SessionResult:
        start_wall = time.monotonic()
        system_prompt = self._build_system_prompt()
        kickoff_message = self._build_kickoff_message()
        messages: list[dict] = [
            {"role": "user", "content": [{"type": "text", "text": kickoff_message}]},
        ]

        turns_used = 0
        tool_calls_made = 0
        stopped_reason = "max_turns"

        for turn in range(self.config.max_turns):
            if time.monotonic() - start_wall > self.config.max_wall_seconds:
                stopped_reason = "wall_timeout"
                break

            # Fire any scripted NPC events that have reached their trigger time.
            self.npc.tick(self.inbox)

            try:
                response = self.harness.step(messages, TOOL_SCHEMAS, system_prompt)
            except Exception as exc:
                stopped_reason = f"harness_error: {type(exc).__name__}: {exc}"
                if self.config.fail_on_harness_error:
                    break
                response = AgentResponse(text=f"(harness error: {exc})", stop_reason="end_turn")

            turns_used += 1
            messages.append(response.to_assistant_message())

            if not response.tool_calls:
                # Model stopped without tool calls — treat as end of session.
                stopped_reason = "end_turn_no_tools"
                break

            tool_result_blocks = []
            for tc in response.tool_calls:
                result = self.executor.execute(tc.name, tc.input)
                tool_calls_made += 1
                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": result.result,
                    "is_error": not result.ok,
                })
                if self.executor.finished:
                    break

            messages.append({"role": "user", "content": tool_result_blocks})

            if self.executor.finished:
                stopped_reason = "agent_finished"
                break

        # Run the scenario verifier
        verifier_instance: ScenarioVerifier = self.scenario.verifier_cls(
            personas=self.scenario.personas,
        )
        report = verifier_instance.run(self.recorder.actions)

        elapsed_sim = (self.clock.now - self.scenario.kickoff_time).total_seconds() / 60.0

        return SessionResult(
            scenario_id=self.scenario.scenario_id,
            action_log=self.recorder.actions,
            verifier_report=report,
            turns_used=turns_used,
            tool_calls_made=tool_calls_made,
            elapsed_sim_minutes=elapsed_sim,
            elapsed_wall_seconds=time.monotonic() - start_wall,
            stopped_reason=stopped_reason,
            messages=messages,
            finish_summary=self.executor.finish_summary,
        )

    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        s = self.scenario
        parts = [
            f"You are a senior executive assistant / chief of staff operating in a simulated enterprise environment.",
            f"",
            f"## Scenario: {s.scenario_id}",
            f"**Your role:** {s.agent_role}",
            f"**Simulated start time:** {self.clock.iso()} ({s.anchor_tz})",
            f"",
            f"## Company context",
            s.company_context or "(no company context available)",
            f"",
            f"## Your brief",
            s.briefing_text or "(no brief available — inspect inputs/ and the DAG)",
            f"",
            f"## How to operate",
            "- Start by calling `list_files` and reading the most relevant inputs under inputs/ "
            "(emails, chat logs, spreadsheets, reports, policy docs). These files pre-populate the "
            "scenario with context you must absorb before acting.",
            "- **Read `inputs/handbook/` FIRST.** It contains org-wide norms (ticket formats, "
            "channel policies, escalation paths, audit trail requirements, data classification rules) "
            "that apply across tasks in this domain. These are the conventions you will be held to.",
            "- **Discovery protocol — persona preferences are NOT in the system prompt.** You know each "
            "persona's name, role, preferred channel, and banned channels. You do NOT automatically know "
            "their timezone, working hours, subject-line conventions, format requirements, or personal "
            "pet peeves. Discover these in one of two ways:\n"
            "    (a) If an unfamiliar persona's preference might affect how you send something to them, "
            "send a short clarifying message asking (e.g. 'Quick check before I send — what's your "
            "preferred format/time-window/subject convention for X?'). NPCs answer honestly.\n"
            "    (b) Cross-reference prior emails / chat logs in inputs/ to infer conventions.\n"
            "  Don't barrel ahead on assumptions for personas you haven't worked with before — "
            "one clarifying message saves rework.",
            "- **Before executing each task**, take a moment to identify: (i) which handbook sections "
            "apply, (ii) which personas you'll touch and whether you need any discovery, "
            "(iii) what deliverable shape (structured ticket fields? specific subject keywords? "
            "timezone constraints?) is required. Then act.",
            "- Reference people by their **persona_id** (snake_case) when calling tools.",
            "- Timestamps are simulated. `check_inbox` reveals NPC replies that have arrived since "
            "your last check. **Always check_inbox after sending a question or an approval request** — "
            "don't assume silence is agreement.",
            "- When you believe every required deliverable is complete and every dependency satisfied, "
            "call `finish_scenario` with a short summary. This ends the session and triggers scoring.",
            "- Work efficiently. Do not narrate at length between tool calls. The evaluation grades "
            "your action log, not your narration.",
            f"",
            f"## Available personas (id | name | role | preferred_channel)",
        ]
        for pid in s.personas.ids():
            p = s.personas[pid]
            bc = f" [banned: {', '.join(p.banned_channels)}]" if p.banned_channels else ""
            parts.append(f"- `{pid}` | {p.name} | {p.role} | {p.preferred_channel or 'unspecified'}{bc}")
        return "\n".join(parts)

    def _build_kickoff_message(self) -> str:
        return (
            f"It is {self.clock.iso()}. The scenario begins now.\n\n"
            f"Your principal (if any) is "
            f"{self.scenario.principal_id or '(inferable from brief)'}. "
            f"Begin by exploring the inputs/ directory, then coordinate with NPCs and produce the "
            f"scenario's deliverables. Call `finish_scenario` when done."
        )
