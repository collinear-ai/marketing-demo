"""
Scenario loader.

Reads a scenario package authored under gym/domains/<domain>/<scenario>/ and
assembles everything a Session needs: persona pool, dag text, initial inputs,
verifier class, kickoff time, and a briefing string presented to the agent at
turn 1.
"""

from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from gym_core import PersonaPool, ScenarioVerifier
from gym_core.rubric_schema import ScenarioRubrics, load_rubrics


REPO_ROOT = Path(__file__).resolve().parent.parent
DOMAINS_ROOT = REPO_ROOT / "gym" / "domains"
BRIEFS_PATH = REPO_ROOT / "gym" / "SCENARIO_BRIEFS.md"


@dataclass
class Scenario:
    scenario_id: str
    directory: Path
    domain: str
    dag_markdown: str
    rubrics: ScenarioRubrics
    personas: PersonaPool
    input_files: dict[str, bytes]          # relative_path -> raw bytes
    verifier_cls: type[ScenarioVerifier]
    kickoff_time: datetime
    anchor_tz: str
    agent_role: str                        # "Chief of Staff to Ayo Okafor"
    principal_id: str | None               # persona id of the agent's boss if resolvable
    briefing_text: str                     # raw brief section for this scenario from SCENARIO_BRIEFS.md
    company_context: str                   # domain header from SCENARIO_BRIEFS.md

    # ------------------------------------------------------------------

    @classmethod
    def load(cls, scenario_id: str) -> "Scenario":
        directory = _find_scenario_directory(scenario_id)
        if directory is None:
            raise FileNotFoundError(
                f"scenario {scenario_id!r} not found under {DOMAINS_ROOT}"
            )
        domain = directory.parent.name

        dag_path = directory / "dag.md"
        rubrics_path = directory / "rubrics.yaml"
        verifiers_path = directory / "verifiers.py"
        personas_path = directory.parent / "_personas.yaml"

        for required in (dag_path, rubrics_path, verifiers_path, personas_path):
            if not required.exists():
                raise FileNotFoundError(f"missing scenario artifact: {required}")

        dag_markdown = dag_path.read_text()
        rubrics = load_rubrics(str(rubrics_path))
        personas = PersonaPool.from_yaml(str(personas_path))
        input_files = _load_input_files(directory / "inputs")
        verifier_cls = _import_scenario_verifier(verifiers_path, scenario_id)

        briefing_text, company_context = _extract_brief(scenario_id, domain)
        agent_role, principal_id = _infer_principal(briefing_text, personas)
        kickoff_time, anchor_tz = _infer_kickoff(dag_markdown)

        return cls(
            scenario_id=scenario_id,
            directory=directory,
            domain=domain,
            dag_markdown=dag_markdown,
            rubrics=rubrics,
            personas=personas,
            input_files=input_files,
            verifier_cls=verifier_cls,
            kickoff_time=kickoff_time,
            anchor_tz=anchor_tz,
            agent_role=agent_role,
            principal_id=principal_id,
            briefing_text=briefing_text,
            company_context=company_context,
        )

    # ------------------------------------------------------------------

    def list_inputs(self) -> list[str]:
        return sorted(self.input_files.keys())

    def read_input(self, relative_path: str) -> bytes:
        if relative_path not in self.input_files:
            raise FileNotFoundError(f"input not found: {relative_path}")
        return self.input_files[relative_path]


class ScenarioIndex:
    """Discovery helper: list all scenarios in the gym."""

    @staticmethod
    def list_all() -> list[tuple[str, str]]:
        """Returns list of (scenario_id, domain) tuples."""
        out = []
        if not DOMAINS_ROOT.exists():
            return out
        for domain_dir in sorted(DOMAINS_ROOT.iterdir()):
            if not domain_dir.is_dir():
                continue
            for scen_dir in sorted(domain_dir.iterdir()):
                if not scen_dir.is_dir() or scen_dir.name.startswith("_"):
                    continue
                if (scen_dir / "dag.md").exists():
                    scenario_id = _canonical_scenario_id(domain_dir.name, scen_dir.name)
                    out.append((scenario_id, domain_dir.name))
        return out

    @staticmethod
    def by_domain(domain: str) -> list[str]:
        return [sid for sid, d in ScenarioIndex.list_all() if d == domain]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_DOMAIN_PREFIX = {
    "hr": "hr",
    "customer_support": "cs",
    "marketing": "mkt",
    "sales_procurement": "sp",
    "finance": "fin",
}


def _canonical_scenario_id(domain: str, scen_dirname: str) -> str:
    prefix = _DOMAIN_PREFIX.get(domain, domain)
    # scen_dirname is like "s1_termination_reorg"; canonical id is "hr_s1_termination_reorg"
    return f"{prefix}_{scen_dirname}"


def _find_scenario_directory(scenario_id: str) -> Path | None:
    # Parse scenario_id like "hr_s1_termination_reorg" -> domain "hr", dirname "s1_termination_reorg"
    for domain_key, prefix in _DOMAIN_PREFIX.items():
        if scenario_id.startswith(prefix + "_"):
            rest = scenario_id[len(prefix) + 1:]
            candidate = DOMAINS_ROOT / domain_key / rest
            if candidate.exists():
                return candidate
    # Fallback: scan all directories
    for _, d in ScenarioIndex.list_all():
        pass
    for domain_dir in DOMAINS_ROOT.iterdir() if DOMAINS_ROOT.exists() else []:
        if not domain_dir.is_dir():
            continue
        for scen_dir in domain_dir.iterdir():
            if not scen_dir.is_dir():
                continue
            if _canonical_scenario_id(domain_dir.name, scen_dir.name) == scenario_id:
                return scen_dir
    return None


def _load_input_files(inputs_dir: Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    if not inputs_dir.exists():
        return out
    for f in sorted(inputs_dir.rglob("*")):
        if not f.is_file():
            continue
        # Skip generator scripts that some subagents left in-tree
        if f.suffix == ".py" and f.name.startswith(("_build", "_generate", "build_")):
            continue
        rel = f.relative_to(inputs_dir).as_posix()
        out[rel] = f.read_bytes()
    return out


def _import_scenario_verifier(
    verifiers_path: Path, scenario_id: str,
) -> type[ScenarioVerifier]:
    module_name = f"_gym_scenario_{scenario_id}"
    spec = importlib.util.spec_from_file_location(module_name, verifiers_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load verifier module: {verifiers_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    found: list[type[ScenarioVerifier]] = []
    for name in dir(module):
        obj = getattr(module, name)
        if (
            isinstance(obj, type)
            and issubclass(obj, ScenarioVerifier)
            and obj is not ScenarioVerifier
        ):
            # Only count the top-level orchestrator (has task_verifiers populated)
            if getattr(obj, "task_verifiers", None):
                found.append(obj)
    if not found:
        raise ImportError(
            f"no ScenarioVerifier subclass with task_verifiers in {verifiers_path}"
        )
    # If multiple, prefer the one matching the scenario_id
    for cls in found:
        if getattr(cls, "scenario_id", "") == scenario_id:
            return cls
    return found[0]


def _extract_brief(scenario_id: str, domain: str) -> tuple[str, str]:
    """Pull this scenario's brief section + the domain header from SCENARIO_BRIEFS.md."""
    if not BRIEFS_PATH.exists():
        return ("", "")
    text = BRIEFS_PATH.read_text()

    # Company / domain header — section starting with "## <DOMAIN NAME>"
    domain_display = {
        "hr": "## HR",
        "customer_support": "## Customer Support",
        "marketing": "## Marketing",
        "sales_procurement": "## Sales & Procurement",
        "finance": "## Finance",
    }.get(domain, "## ")
    company_context = ""
    m = re.search(rf"({re.escape(domain_display)}[^\n]*\n\n.*?)(?=\n### )", text, re.DOTALL)
    if m:
        company_context = m.group(1).strip()

    # Scenario brief — starts at "### <scenario_id>" and runs to next "### " or "---"
    briefing = ""
    m = re.search(
        rf"### {re.escape(scenario_id)}\b.*?(?=\n### |\n---\n)",
        text,
        re.DOTALL,
    )
    if m:
        briefing = m.group(0).strip()

    return briefing, company_context


def _infer_principal(briefing: str, personas: PersonaPool) -> tuple[str, str | None]:
    """Extract 'Chief of Staff to <persona>' from the brief."""
    m = re.search(
        r"\*\*Agent role:\*\*\s*(?:Chief of Staff|Chief of staff)\s+to\s+([^.\n]+?)\.",
        briefing,
    )
    if not m:
        return ("Chief of Staff", None)
    blurb = m.group(1).strip()
    agent_role = f"Chief of Staff to {blurb}"

    # Try to match the blurb to a persona id by name substring.
    for pid in personas.ids():
        p = personas[pid]
        if p.name and p.name in blurb:
            return (agent_role, pid)
        # Also try last name
        last = (p.name or "").split()[-1] if p.name else ""
        if last and last in blurb:
            return (agent_role, pid)
    return (agent_role, None)


def _infer_kickoff(dag_text: str) -> tuple[datetime, str]:
    """Best-effort kickoff time extraction from dag.md. Falls back to a sane default."""
    # Look for ISO-ish dates in the dag.md
    m = re.search(r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", dag_text)
    if m:
        try:
            y, mo, d = map(int, m.groups())
            # Assume 09:00 local ET Monday-ish kickoff
            return (datetime(y, mo, d, 9, 0, tzinfo=ZoneInfo("America/New_York")),
                    "America/New_York")
        except ValueError:
            pass
    return (
        datetime(2026, 4, 6, 9, 0, tzinfo=ZoneInfo("America/New_York")),
        "America/New_York",
    )
