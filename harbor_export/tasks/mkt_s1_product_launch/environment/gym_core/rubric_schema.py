"""
Minimal validation for rubrics.yaml files.

Rubrics are authored in YAML, consumed by two things: the programmatic verifier
layer (which expects a 1:1 mapping between programmatic_checks[].id and verifier
method output check_ids) and an LLM-as-judge layer (which scores the
rubric_criteria). This module validates structure and provides a lookup API;
LLM-as-judge execution itself is out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:                              # pragma: no cover
    yaml = None


VALID_CHECK_TYPES = {
    "boolean",
    "checklist",
    "exact_value",
    "threshold",
    "time_range",
    "time_window",
    "conditional",
    "ordering",
    "compliance",
}


@dataclass
class ProgrammaticCheck:
    id: str
    name: str
    description: str
    type: str
    items: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class RubricCriterion:
    id: str
    name: str
    dimension: str
    description: str
    scoring: dict[int, str] = field(default_factory=dict)


@dataclass
class TaskRubric:
    task_id: str
    programmatic_checks: list[ProgrammaticCheck] = field(default_factory=list)
    rubric_criteria: list[RubricCriterion] = field(default_factory=list)


@dataclass
class ScenarioRubrics:
    tasks: dict[str, TaskRubric] = field(default_factory=dict)
    project_level: list[RubricCriterion] = field(default_factory=list)

    def programmatic_check_ids(self) -> set[str]:
        out = set()
        for task in self.tasks.values():
            for pc in task.programmatic_checks:
                out.add(pc.id)
        return out

    def rubric_criterion_ids(self) -> set[str]:
        out = {c.id for c in self.project_level}
        for task in self.tasks.values():
            for c in task.rubric_criteria:
                out.add(c.id)
        return out


def load_rubrics(path: str) -> ScenarioRubrics:
    if yaml is None:
        raise RuntimeError("PyYAML required: `uv add pyyaml`")
    with open(path) as f:
        raw = yaml.safe_load(f)
    return parse_rubrics(raw)


def parse_rubrics(raw: dict[str, Any]) -> ScenarioRubrics:
    scen = ScenarioRubrics()
    for key, val in raw.items():
        if not isinstance(val, dict):
            continue
        if "programmatic_checks" not in val and "rubric_criteria" not in val:
            # Probably scoring_scale or organization metadata; skip.
            continue
        task_id = key.split("_", 1)[0]    # "T1_pull_metrics" -> "T1"
        task = TaskRubric(task_id=task_id)
        for pc in val.get("programmatic_checks", []) or []:
            check_type = pc.get("type", "boolean")
            if check_type not in VALID_CHECK_TYPES:
                raise ValueError(
                    f"Invalid check type '{check_type}' on {pc.get('id')}; "
                    f"must be one of {sorted(VALID_CHECK_TYPES)}"
                )
            task.programmatic_checks.append(ProgrammaticCheck(
                id=pc["id"],
                name=pc["name"],
                description=pc.get("description", ""),
                type=check_type,
                items=pc.get("items", []) or [],
                extra={k: v for k, v in pc.items()
                       if k not in {"id", "name", "description", "type", "items"}},
            ))
        for rc in val.get("rubric_criteria", []) or []:
            task.rubric_criteria.append(RubricCriterion(
                id=rc["id"],
                name=rc["name"],
                dimension=rc.get("dimension", ""),
                description=rc.get("description", ""),
                scoring={int(k): v for k, v in (rc.get("scoring") or {}).items()},
            ))
        scen.tasks[key] = task
    return scen
