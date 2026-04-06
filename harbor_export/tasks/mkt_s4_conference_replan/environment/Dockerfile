FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency spec first for layer caching
COPY pyproject.toml uv.lock* ./

# Install uv and dependencies
RUN pip install uv && uv sync --extra openai

# Copy the bundled gym code + scenario data
COPY gym_core/ gym_core/
COPY gym_runtime/ gym_runtime/
COPY gym/ gym/
COPY SKILLS.md SKILLS.md

# Validate the scenario loads inside the container
RUN uv run python -c "from gym_runtime.scenario import Scenario; s = Scenario.load('mkt_s4_conference_replan'); print(f'OK: {len(s.input_files)} inputs, {len(s.personas.ids())} personas')"

ENV SCENARIO_ID="mkt_s4_conference_replan"

# Default: run the agent. Harbor overrides this with its own agent runner.
CMD ["uv", "run", "python", "-m", "gym_runtime.run", "mkt_s4_conference_replan", \
     "--harness", "openai", "--model", "gpt-5.4", "--max-turns", "200"]
