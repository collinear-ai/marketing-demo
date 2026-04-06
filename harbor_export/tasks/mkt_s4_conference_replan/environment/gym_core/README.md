# gym_core

Shared abstractions for the Long-Horizon Agent Evaluation Gym. Every scenario package under `gym/domains/` imports from this package instead of redefining its own schema, persona loader, or predicate helpers.

## What's in here

| Module | Purpose |
|---|---|
| `schema.py` | `ActionType` (superset enum), `Action`, `VerifierResult`, `RubricScore`, `Severity`. The canonical action-log contract. |
| `persona.py` | `Persona` + `PersonaPool` (loads shared `_personas.yaml`). Thin structured view used by predicates; rich YAML fields are passed through as `.raw`. |
| `predicates.py` | Small, composable checks: `actions_to`, `body_has_all_keywords`, `used_preferred_channel`, `did_not_use_banned_channel`, `within_working_hours`, `meets_lead_time`, `ordering_respected`, `no_phi_in_channel`, `no_credentials_anywhere`, ... |
| `verifier_base.py` | `BaseTaskVerifier` (one per DAG task), `ComplianceVerifier` (cross-cutting), `ScenarioVerifier` (orchestrator), `ScenarioReport`. |
| `rubric_schema.py` | Loads and validates `rubrics.yaml` into `ScenarioRubrics`; enforces valid check types. |
| `lint.py` | Referential-integrity linter: every persona id, task id, and programmatic-check id must be consistent across `_personas.yaml`, `dag.md`, `rubrics.yaml`, `verifiers.py`. |

## Authoring a new scenario

```python
# gym/domains/hr/s1_termination_reorg/verifiers.py
from gym_core import (
    Action, ActionType, BaseTaskVerifier, ComplianceVerifier,
    ScenarioVerifier, predicates as P, PersonaPool,
)

class T1_LegalReview(BaseTaskVerifier):
    task_id = "T1"

    def run_all(self):
        legal_msgs = P.actions_to(
            self.actions, "samira_khoury", ActionType.EMAIL
        )
        yield self.boolean("PC1", "email_to_legal",
                           bool(legal_msgs),
                           f"Found {len(legal_msgs)} email(s) to Legal.")

        # no Slack for termination topics
        persona = self.personas["samira_khoury"]
        violations = P.did_not_use_banned_channel(
            self.actions, persona,
            topic_keywords=["termination", "separation", "severance"],
        )
        yield self.result(
            "PC2", "no_slack_for_termination",
            passed=not violations,
            details=f"{len(violations)} banned-channel violation(s).",
            compliance_relevant=True,
        )

class HRCompliance(ComplianceVerifier):
    def run_all(self):
        creds = P.no_credentials_anywhere(self.actions)
        yield self.result(
            "GLOBAL_CREDS", "no_credentials_leaked",
            passed=not creds,
            details=f"{len(creds)} credential leak(s).",
            compliance_relevant=True,
        )

class TerminationReorgVerifier(ScenarioVerifier):
    scenario_id = "hr_s1_termination_reorg"
    task_verifiers = [T1_LegalReview, ...]
    compliance_verifiers = [HRCompliance]
```

## Linting a scenario

```bash
uv run python -m gym_core.lint gym/domains/hr/s1_termination_reorg
```

Exits 0 if clean, 1 if any referential-integrity errors. Run this before committing any scenario edit.

## Action log contract

Verifiers consume `list[Action]`. An `Action` carries everything a downstream check could care about — recipient, channel, body, attendees, classification, attachments, amount, approval_status — plus a free-form `metadata` dict for scenario-specific fields. Do **not** add scenario-specific top-level fields to `Action`; extend `metadata` instead.

## Extending ActionType

The enum in `schema.py` is already a superset covering all 6 domains. If a new scenario genuinely needs a new kind (e.g. "dispatch_ticket"), either:

1. Add it to the enum in `schema.py` (preferred if reusable), or
2. Use `ActionType.CUSTOM` and stash the specific kind in `metadata["custom_kind"]`.

Do not redefine `ActionType` locally in a scenario file.
