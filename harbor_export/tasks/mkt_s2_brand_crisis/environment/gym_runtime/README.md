# gym_runtime

Execution harness for the Long-Horizon Agent Evaluation Gym. Loads a scenario package authored under `gym/domains/<domain>/<scenario>/`, presents it to an agent via a tool-use loop, simulates NPC responses, captures an action log, and scores it with the scenario's `ScenarioVerifier`.

## Install

The runtime itself has zero external deps beyond the core gym. For real LLM-driven runs, install the provider extras:

```bash
uv sync --extra anthropic   # Claude
uv sync --extra google      # Gemini (harness stub — contribute a PR)
```

## Quick start

List scenarios:
```bash
uv run python -m gym_runtime.run --list
```

Null baseline run (no API key needed — proves the plumbing works):
```bash
uv run python -m gym_runtime.run hr_s1_termination_reorg --harness dummy
```

Real run with Claude:
```bash
export ANTHROPIC_API_KEY=...
uv run python -m gym_runtime.run hr_s1_termination_reorg \
    --harness anthropic --model claude-sonnet-4-5 \
    --out trajectories/
```

Outputs land in `trajectories/`:
- `<scenario>__<model>.json` — full message history + verifier report
- `<scenario>__<model>.jsonl` — action log in the verifier-expected schema

## Architecture

```
Scenario ──────────┐
(personas, inputs, │
 dag, verifier)    │
                   ▼
              ┌─────────┐      ┌────────────┐
              │ Session │──────│  Harness   │  (AnthropicHarness / DummyHarness / ...)
              └────┬────┘      └────────────┘
                   │
        ┌──────────┼──────────┬─────────────┐
        ▼          ▼          ▼             ▼
   ┌──────┐   ┌───────┐  ┌───────┐    ┌────────┐
   │Clock │   │Inbox  │  │Tool   │    │  NPC   │
   │      │   │       │  │Exec.  │    │  Sim   │
   └──────┘   └───────┘  └───┬───┘    └────┬───┘
                              │             │
                              ▼             ▼
                        ┌─────────────────────┐
                        │  ActionRecorder     │
                        │  (list[Action])     │
                        └──────────┬──────────┘
                                   │
                                   ▼
                         scenario.verifier_cls.run(actions)
                                   │
                                   ▼
                            ScenarioReport
```

### Modules

| Module | Responsibility |
|---|---|
| `scenario.py` | Dynamic loader: personas.yaml, dag.md, rubrics.yaml, verifiers.py (importlib), input files, brief extraction from SCENARIO_BRIEFS.md |
| `clock.py` | Deterministic sim time; agent actions advance it |
| `inbox.py` | Unread-message queue the agent polls via `check_inbox` |
| `recorder.py` | Wraps `gym_core.Action` construction; JSONL serialization |
| `tools.py` | 10 tool schemas (Anthropic tool-use format) + `ToolExecutor` — handles all scenario action surface |
| `npc.py` | Decides NPC responses — respects banned_channels, working hours, hard boundaries; LLM-as-NPC pluggable via `llm_client` |
| `session.py` | Main loop: build system prompt → agent turn → tool execution → NPC reactions → repeat → score |
| `harness/base.py` | `AgentHarness` interface + `AgentResponse`/`ToolCall` dataclasses |
| `harness/dummy.py` | `DummyHarness` (finish-immediately) and `ScriptedHarness` (replay) for plumbing tests |
| `harness/anthropic.py` | Claude integration via Anthropic SDK |
| `run.py` | CLI |

## Tool surface

The executor exposes 10 tools covering the action surface of all 25 scenarios:

| Tool | Maps to `ActionType` |
|---|---|
| `send_slack_message` | `SLACK_MESSAGE` |
| `send_email` (with `encrypted` flag) | `EMAIL` / `ENCRYPTED_EMAIL` |
| `create_calendar_invite` | `CALENDAR_INVITE` |
| `create_document` | `DOCUMENT_CREATE` |
| `request_approval` | `APPROVAL_REQUEST` |
| `docusign_envelope` | `DOCUSIGN_ENVELOPE` |
| `list_files` | — (reads scenario.inputs/) |
| `read_file` | — (xlsx via openpyxl, pdf via pypdf, text verbatim) |
| `check_inbox` | — (surfaces NPC replies) |
| `finish_scenario` | ends session |

Adding a tool: add a schema to `TOOL_SCHEMAS` in `tools.py` and a `_tool_<name>` handler method on `ToolExecutor`.

## NPC behavior

When the agent sends a message to a persona, the `NPCSimulator`:

1. Looks up the persona from the scenario's `PersonaPool`.
2. Checks **banned_channels** — if the action uses a banned channel for this persona (e.g. legal counsel + Slack for privileged topics), the NPC sends an auto-rejection reply and the verifier catches the violation.
3. Checks **working hours** — if the persona has a hard boundary and the message arrives out-of-hours, the reply is deferred to the next working hour.
4. Generates the reply body:
   - If an `llm_client` is configured, calls it with the persona's full YAML record as system context and the agent's message. Replies are in-character.
   - Otherwise emits a deterministic stub so plumbing tests work without API keys.
5. Drops the reply into the agent's inbox with a timestamp based on the persona's `response_time_minutes`.

Scripted time-triggered events are supported via `NPCSimulator.events` — a scenario can pre-plant a list of `ScriptedEvent` objects that fire at specific sim times (e.g. "at T+4h, Deborah DMs the agent demanding a status update").

## Scoring

After the session ends (`finish_scenario` or `max_turns`), the runtime imports the scenario's `verifiers.py` dynamically, instantiates the `ScenarioVerifier` subclass, and runs it against the action log. The resulting `ScenarioReport` contains per-check pass/fail plus severity metadata.

Only programmatic checks run in the base runtime. Qualitative `rubric_criteria` (1–5 scoring) are intended for an LLM-as-judge layer that reads the YAML directly — not yet built in this module.

## Null baseline (sanity check)

Running `DummyHarness` against every scenario reports 1,381 total programmatic checks across the gym. With no agent actions, ~234 pass (vacuously / info severity) and ~1,147 fail — the headroom a real agent needs to close:

```bash
for s in $(uv run python -m gym_runtime.run --list | awk '{print $1}' | grep _); do
    uv run python -m gym_runtime.run "$s" --harness dummy --quiet | \
        python3 -c "import sys,json; r=json.load(sys.stdin)['verifier']; print(f\"{r['scenario_id']}: {r['passed']}/{r['total_checks']}\")"
done
```

## Known limitations (MVP)

1. **LLM-as-judge not integrated.** Programmatic checks only. Qualitative rubric scoring is a separate workstream.
2. **Time-triggered events are pluggable but no scenarios ship with scripted events.** Add events to a scenario via `NPCSimulator.events` before calling `Session.run()`.
3. **Binary file reading.** xlsx summaries show the first 50 rows per sheet; pdfs extract first 5 pages. Large files return truncated views.
4. **No retry / backoff on Anthropic rate limits.** A 429 will kill the session with a harness_error. Add retries in a subclass if needed.
5. **Single-agent only.** No multi-agent orchestration, no sub-agent spawning from within a scenario.
6. **Gemini harness is a stub.** Contribute `harness/google.py` the same shape as `harness/anthropic.py`.
