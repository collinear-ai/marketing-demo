"""
NPC simulator — decides whether and how NPCs respond to agent actions.

When the agent sends a message or schedules something that targets an NPC
persona, the simulator:

1. Looks up the persona record.
2. Checks whether the NPC "would" respond (working hours, banned-channel
   violations, responsiveness SLA).
3. If yes, either:
   a) uses a scripted response (from events.yaml in the scenario, if present), OR
   b) calls an LLM with the persona's full YAML context + conversation
      history + the agent's latest message, asking the LLM to respond in
      character.
4. Drops the reply into the agent's inbox.

The LLM responder is optional — if no llm_client is provided, the simulator
falls back to a deterministic stub ("<persona_name> acknowledges: ...") so the
runtime can operate without API keys for plumbing tests.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Protocol

from gym_core import Action, ActionType, PersonaPool
from gym_core.persona import Persona
from gym_runtime.clock import SimClock
from gym_runtime.inbox import Inbox, InboxItem
from gym_runtime.recorder import ActionRecorder


class LLMClient(Protocol):
    """Minimal protocol for whatever client the NPC simulator uses for LLM-as-NPC."""
    def respond_as_persona(
        self,
        persona: Persona,
        conversation: list[dict[str, str]],
        latest_agent_message: str,
        scenario_context: str,
    ) -> str:
        ...


@dataclass
class ScriptedEvent:
    """A pre-scripted NPC action that fires at a specific sim time or in response
    to a specific trigger. Optional enhancement for scenarios with proactive NPCs."""
    trigger_time: datetime | None = None
    trigger_on_action_type: ActionType | None = None
    trigger_on_recipient: str | None = None
    from_persona: str = ""
    channel: str = "slack"
    subject: str | None = None
    body: str = ""
    fired: bool = False


@dataclass
class NPCSimulator:
    personas: PersonaPool
    clock: SimClock
    scenario_context: str = ""
    llm_client: LLMClient | None = None
    recorder: ActionRecorder | None = None
    events: list[ScriptedEvent] = field(default_factory=list)
    conversation_history: dict[str, list[dict[str, str]]] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Reaction to agent actions
    # ------------------------------------------------------------------

    def react_to_action(self, action: Action, inbox: Inbox) -> list[InboxItem]:
        """Generate zero or more NPC replies to an agent action. Drops them into
        the inbox with a small response delay based on persona responsiveness."""
        if action.recipient is None:
            return []
        persona = self.personas.get(action.recipient)
        if persona is None:
            # External NPC not in pool — no autoreply
            return []

        # Channel mismatch / banned channel — NPC does not respond (and a
        # verifier will catch the violation).
        if self._is_banned_channel(persona, action):
            return self._maybe_reject(persona, action, inbox)

        # Out-of-hours — NPC defers reply until next working hour window.
        reply_time = self._compute_reply_time(persona, action)
        if reply_time is None:
            return []

        # Build the reply text.
        body = self._build_reply_body(persona, action)
        reply_subject = f"Re: {action.subject}" if action.subject else None
        item = InboxItem(
            channel=_channel_for_reply(action.action_type),
            from_id=persona.id,
            to_id="agent",
            timestamp=reply_time,
            subject=reply_subject,
            body=body,
            thread_id=(action.metadata or {}).get("thread_id"),
            metadata={"auto_npc_reply": True},
        )
        inbox.deliver(item)

        # Track conversation history for this persona
        hist = self.conversation_history.setdefault(persona.id, [])
        hist.append({"role": "agent", "content": action.body or ""})
        hist.append({"role": "persona", "content": body})

        # Stamp the NPC reply into the action recorder so verifiers can see it.
        # For APPROVAL_REQUEST, emit APPROVAL_GRANT if the reply reads like an
        # approval; otherwise emit a matching inbound message Action.
        if self.recorder is not None:
            self._stamp_npc_reply(persona, action, body, reply_time, reply_subject)

        return [item]

    # ------------------------------------------------------------------

    def _stamp_npc_reply(
        self,
        persona: Persona,
        incoming: Action,
        body: str,
        when: datetime,
        subject: str | None,
    ) -> None:
        """Append a structured Action for the NPC's reply so verifiers can detect
        approvals, confirmations, and content-bearing responses."""
        assert self.recorder is not None
        body_lc = body.lower()

        # Heuristic: did the NPC grant an approval?
        approval_words = (
            "approved", "approve this", "approve it", "approve the",
            "looks good", "lgtm", "go ahead", "proceed", "ship it",
            "signed off", "sign off", "signoff granted", "greenlit", "green light",
            "ok to send", "ok to proceed", "i approve", "grant approval",
            "authoriz", "authorise",
        )
        refusal_words = (
            "do not approve", "not approve", "cannot approve", "can't approve",
            "hold off", "hold on", "not yet", "needs changes", "revise",
            "reject", "decline", "blocked", "pause",
        )
        granted = any(w in body_lc for w in approval_words) and not any(
            w in body_lc for w in refusal_words
        )

        shared_fields = dict(
            recipient="agent",
            cc=[], bcc=[],
            subject=subject,
            body=body,
            attachments=[],
            attendees=[],
            metadata={
                "from": persona.id,
                "auto_npc_reply": True,
                "in_reply_to_action_type": incoming.action_type.value,
                "in_reply_to_subject": incoming.subject,
                "in_reply_to_thread_id": (incoming.metadata or {}).get("thread_id"),
            },
        )

        if incoming.action_type == ActionType.APPROVAL_REQUEST and granted:
            self.recorder.build_and_record(
                action_type=ActionType.APPROVAL_GRANT,
                timestamp=when,
                tool="npc_auto",
                channel=_channel_for_reply(incoming.action_type),
                approval_status="approved",
                **shared_fields,
            )
            return

        # Non-approval reply: stamp as the channel-appropriate inbound message.
        reply_atype = {
            ActionType.SLACK_MESSAGE: ActionType.SLACK_MESSAGE,
            ActionType.TEAMS_MESSAGE: ActionType.TEAMS_MESSAGE,
            ActionType.EMAIL: ActionType.EMAIL_REPLY,
            ActionType.EMAIL_REPLY: ActionType.EMAIL_REPLY,
            ActionType.ENCRYPTED_EMAIL: ActionType.EMAIL_REPLY,
            ActionType.APPROVAL_REQUEST: ActionType.EMAIL_REPLY,
        }.get(incoming.action_type, ActionType.EMAIL_REPLY)

        self.recorder.build_and_record(
            action_type=reply_atype,
            timestamp=when,
            tool="npc_auto",
            channel=_channel_for_reply(incoming.action_type),
            **shared_fields,
        )

    # ------------------------------------------------------------------
    # Scripted time-triggered events
    # ------------------------------------------------------------------

    def tick(self, inbox: Inbox) -> list[InboxItem]:
        """Fire any scripted events whose trigger time has arrived."""
        delivered: list[InboxItem] = []
        for evt in self.events:
            if evt.fired:
                continue
            if evt.trigger_time is not None and self.clock.now >= evt.trigger_time:
                item = InboxItem(
                    channel=evt.channel,
                    from_id=evt.from_persona,
                    to_id="agent",
                    timestamp=self.clock.now,
                    subject=evt.subject,
                    body=evt.body,
                    metadata={"scripted_event": True},
                )
                inbox.deliver(item)
                delivered.append(item)
                evt.fired = True
        return delivered

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _is_banned_channel(self, persona: Persona, action: Action) -> bool:
        atype_str = {
            ActionType.SLACK_MESSAGE: "slack",
            ActionType.TEAMS_MESSAGE: "teams",
            ActionType.SMS: "sms",
            ActionType.PHONE_CALL: "phone",
            ActionType.EMAIL: "email",
            ActionType.ENCRYPTED_EMAIL: "email",
            ActionType.EMAIL_REPLY: "email",
        }.get(action.action_type)
        if atype_str is None:
            return False
        return any(atype_str in b.lower() for b in (persona.banned_channels or []))

    def _maybe_reject(
        self, persona: Persona, action: Action, inbox: Inbox,
    ) -> list[InboxItem]:
        # Some personas send a terse refusal rather than silent ignore. Keep it
        # deterministic so verifiers can detect the violation even without an LLM.
        body = (
            f"[auto-rejection] {persona.name} does not discuss topics like this on "
            f"{action.action_type.value}. Please use the approved channel per "
            f"{persona.role} protocol."
        )
        item = InboxItem(
            channel=_channel_for_reply(action.action_type),
            from_id=persona.id,
            to_id="agent",
            timestamp=self.clock.now + timedelta(minutes=5),
            subject=f"Re: {action.subject}" if action.subject else None,
            body=body,
            metadata={"auto_npc_reply": True, "channel_violation": True},
        )
        inbox.deliver(item)
        return [item]

    def _compute_reply_time(self, persona: Persona, action: Action) -> datetime | None:
        """Schedule when this NPC would reply. Returns None if the NPC simply
        ignores the action (out of scope, weekend + hard boundary, etc.)."""
        base_delay_min = persona.response_time_minutes or 45
        reply_at = self.clock.now + timedelta(minutes=base_delay_min)

        # If reply_at falls outside working hours and persona has a hard boundary,
        # push to start of next working day.
        if persona.hard_boundary_after_hours and not persona.is_working_hour(reply_at):
            # Push forward up to 24h to next working hour
            for hours_ahead in range(1, 48):
                candidate = self.clock.now + timedelta(hours=hours_ahead)
                if persona.is_working_hour(candidate):
                    return candidate.replace(minute=0)
            return None
        return reply_at

    def _build_reply_body(self, persona: Persona, action: Action) -> str:
        if self.llm_client is not None:
            try:
                return self.llm_client.respond_as_persona(
                    persona=persona,
                    conversation=self.conversation_history.get(persona.id, []),
                    latest_agent_message=action.body or "",
                    scenario_context=self.scenario_context,
                )
            except Exception as exc:
                # Fall through to stub on any LLM error
                return f"[stub: LLM error] {persona.name} acknowledges the message. ({exc})"
        # Deterministic stub — enough for plumbing tests without API keys
        return (
            f"[auto-stub] {persona.name} ({persona.role}) acknowledges your message. "
            f"Real response would depend on the scenario context; this stub exists so "
            f"the runtime can operate without an LLM configured for NPCs."
        )


class OpenAINPCClient:
    """LLM-as-NPC client that uses the OpenAI Responses API to generate
    in-character replies from NPC personas. Stateless across calls — the
    persona's conversation history is passed in every time by NPCSimulator.

    Uses a lighter reasoning effort than the agent since NPC replies don't
    need deep reasoning, just persona fidelity and consistent preference signaling.
    """

    def __init__(
        self,
        model: str = "gpt-5.4",
        reasoning_effort: str | None = "low",
        api_key: str | None = None,
        max_output_tokens: int = 800,
    ):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "OpenAI SDK required for OpenAINPCClient. Install with: uv sync --extra openai"
            ) from exc
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.max_output_tokens = max_output_tokens
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self._effort_downgraded = False

    def respond_as_persona(
        self,
        persona: Persona,
        conversation: list[dict[str, str]],
        latest_agent_message: str,
        scenario_context: str,
    ) -> str:
        system_prompt = self._build_persona_system_prompt(persona, scenario_context)
        history_text = self._format_history(conversation, latest_agent_message)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "instructions": system_prompt,
            "input": [
                {"role": "user", "content": [{"type": "input_text", "text": history_text}]},
            ],
            "max_output_tokens": self.max_output_tokens,
        }
        if self.reasoning_effort:
            kwargs["reasoning"] = {"effort": self.reasoning_effort}

        try:
            response = self.client.responses.create(**kwargs)
        except Exception as exc:
            msg = str(exc).lower()
            if (
                not self._effort_downgraded
                and self.reasoning_effort
                and ("reasoning" in msg or "effort" in msg or "enum" in msg or "invalid" in msg)
            ):
                self._effort_downgraded = True
                self.reasoning_effort = "minimal"
                kwargs["reasoning"] = {"effort": "minimal"}
                response = self.client.responses.create(**kwargs)
            else:
                raise

        text_parts: list[str] = []
        for item in response.output:
            if getattr(item, "type", None) == "message":
                for c in getattr(item, "content", []):
                    if getattr(c, "type", None) in ("output_text", "text"):
                        text_parts.append(getattr(c, "text", "") or "")
        return "\n".join(t for t in text_parts if t).strip() or f"[{persona.name} has no response.]"

    def _build_persona_system_prompt(self, persona: Persona, scenario_context: str) -> str:
        raw = persona.raw or {}
        # Keep the full persona record but drop fields the NPC shouldn't need to reason about
        # (relationships to other NPCs are fine; blind spots and rubric hints are not).
        persona_yaml = json.dumps(raw, default=str, indent=2)[:6000]
        return (
            f"You are role-playing an NPC in an enterprise simulation. The agent (a senior "
            f"executive assistant / chief of staff) will send you messages; reply in character.\n\n"
            f"## Your persona\n"
            f"- id: {persona.id}\n"
            f"- name: {persona.name}\n"
            f"- role: {persona.role}\n"
            f"- timezone: {persona.timezone}\n"
            f"- working hours: {persona.working_hours_start}–{persona.working_hours_end}\n"
            f"- preferred channel: {persona.preferred_channel or 'unspecified'}\n"
            f"- banned channels: {', '.join(persona.banned_channels) or 'none'}\n"
            f"\n## Full persona record (communication style, quirks, relationships, boundaries):\n"
            f"```yaml\n{persona_yaml}\n```\n\n"
            f"## Scenario context (so you know what's going on)\n"
            f"{scenario_context or '(no briefing)'}\n\n"
            f"## Reply rules\n"
            f"1. Stay strictly in character. Use the tone, verbal tics, and communication preferences described above.\n"
            f"2. Keep replies to 3–8 sentences unless the agent explicitly asks for something longer.\n"
            f"3. If the agent asks about your preferences (working hours, channel, format, deadlines), ANSWER HONESTLY — share your actual working hours, timezone, preferred channel, and any conventions you follow (e.g. subject-line labels, structured field requirements). This is how the agent learns to work with you.\n"
            f"4. If the agent sends you content for review or approval and it looks reasonable given your persona's role and constraints, explicitly APPROVE it with a phrase like 'Approved — go ahead', 'LGTM', or 'You have my sign-off'. If it's missing something important, say what's needed instead of approving.\n"
            f"5. If the agent violates one of your hard preferences (wrong channel, wrong hours, missing required fields), point it out politely but don't be a pushover — insist on the correction.\n"
            f"6. Do NOT invent new facts about the scenario beyond what's in your persona record and the scenario context. If you don't know something, say so.\n"
            f"7. Do NOT break the fourth wall or mention that this is a simulation.\n"
            f"8. Do NOT produce any system/meta content — just the reply body as the persona would write it.\n"
        )

    def _format_history(self, conversation: list[dict[str, str]], latest: str) -> str:
        lines: list[str] = []
        if conversation:
            lines.append("## Prior exchanges with the agent in this scenario")
            for turn in conversation[-12:]:  # last 6 round-trips
                role = "agent" if turn.get("role") == "agent" else "you"
                content = (turn.get("content") or "").strip()
                if content:
                    lines.append(f"[{role}]: {content[:1500]}")
            lines.append("")
        lines.append("## Latest message from the agent (respond to this in character)")
        lines.append(latest[:4000] if latest else "(empty message)")
        return "\n".join(lines)


def _channel_for_reply(atype: ActionType) -> str:
    if atype == ActionType.SLACK_MESSAGE:
        return "slack"
    if atype in (ActionType.EMAIL, ActionType.EMAIL_REPLY):
        return "email"
    if atype == ActionType.ENCRYPTED_EMAIL:
        return "encrypted_email"
    if atype == ActionType.TEAMS_MESSAGE:
        return "teams"
    if atype == ActionType.CALENDAR_INVITE:
        return "calendar"
    if atype == ActionType.APPROVAL_REQUEST:
        return "email"
    return atype.value
