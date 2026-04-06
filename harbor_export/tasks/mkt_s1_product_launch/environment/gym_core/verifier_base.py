"""
Base classes for scenario verifiers.

A scenario's ``verifiers.py`` should define one ``BaseTaskVerifier`` subclass
per DAG task, plus an optional ``ComplianceVerifier`` subclass for cross-cutting
regulatory checks. A single ``ScenarioVerifier`` instance wires them together
and runs them against an action log.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from gym_core.schema import Action, Severity, VerifierResult
from gym_core.persona import PersonaPool


class BaseTaskVerifier:
    """
    Subclass per DAG task. Set ``task_id`` (e.g. "T1") and implement
    ``run_all`` as a generator that yields ``VerifierResult``.

    Use ``self.result(...)`` / ``self.boolean(...)`` / ``self.checklist(...)``
    to construct results with the task_id prefix auto-applied.
    """
    task_id: str = "T?"

    def __init__(self, actions: list[Action], personas: PersonaPool | None = None):
        self.actions = actions
        self.personas = personas or PersonaPool()

    # ------------------------------------------------------------------
    # result constructors (sugar)
    # ------------------------------------------------------------------

    def result(
        self,
        check_id: str,
        name: str,
        passed: bool,
        details: str,
        severity: Severity = Severity.ERROR,
        compliance_relevant: bool = False,
    ) -> VerifierResult:
        return VerifierResult(
            check_id=self._ensure_prefix(check_id),
            name=name,
            passed=passed,
            details=details,
            severity=severity,
            compliance_relevant=compliance_relevant,
        )

    def boolean(self, check_id: str, name: str, passed: bool, details: str) -> VerifierResult:
        return self.result(check_id, name, passed, details)

    def checklist(
        self,
        check_id: str,
        name: str,
        missing: list[str],
        total: int,
    ) -> VerifierResult:
        passed = len(missing) == 0
        details = (
            f"All {total} items present."
            if passed
            else f"Missing {len(missing)}/{total}: {', '.join(missing)}"
        )
        return self.result(check_id, name, passed, details)

    def warning(self, check_id: str, name: str, passed: bool, details: str) -> VerifierResult:
        return self.result(check_id, name, passed, details, severity=Severity.WARNING)

    def _ensure_prefix(self, check_id: str) -> str:
        if check_id.startswith(self.task_id + "_"):
            return check_id
        return f"{self.task_id}_{check_id}"

    # ------------------------------------------------------------------
    # override point
    # ------------------------------------------------------------------

    def run_all(self) -> Iterator[VerifierResult]:
        raise NotImplementedError


class ComplianceVerifier(BaseTaskVerifier):
    """Cross-cutting verifier that runs against the entire action log rather
    than one DAG task. Still uses the same result API. task_id defaults to
    'GLOBAL'."""
    task_id = "GLOBAL"


@dataclass
class ScenarioReport:
    scenario_id: str
    results: list[VerifierResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results if r.severity == Severity.ERROR
                                                   or r.severity == Severity.CRITICAL)

    def summary(self) -> dict:
        total = len(self.results)
        by_sev: dict[str, int] = {}
        failed: list[VerifierResult] = []
        for r in self.results:
            key = r.severity.value if r.passed else f"failed_{r.severity.value}"
            by_sev[key] = by_sev.get(key, 0) + 1
            if not r.passed:
                failed.append(r)
        return {
            "scenario_id": self.scenario_id,
            "total_checks": total,
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "by_severity": by_sev,
            "failures": [r.to_dict() for r in failed],
        }


class ScenarioVerifier:
    """
    Wire up per-task verifiers + cross-cutting compliance verifiers and run
    them over an action log. Scenarios construct a ScenarioVerifier in their
    module and expose ``run(action_log) -> ScenarioReport``.

    Example:
        class QBRVerifier(ScenarioVerifier):
            scenario_id = "cerulean_qbr"
            task_verifiers = [T1, T2, T3, ...]
            compliance_verifiers = [CeruleanCompliance]
    """
    scenario_id: str = "unknown"
    task_verifiers: list[type[BaseTaskVerifier]] = []
    compliance_verifiers: list[type[ComplianceVerifier]] = []

    def __init__(self, personas: PersonaPool | None = None):
        self.personas = personas or PersonaPool()

    def run(self, actions: Iterable[Action]) -> ScenarioReport:
        action_list = list(actions)
        report = ScenarioReport(scenario_id=self.scenario_id)
        for cls in self.task_verifiers:
            verifier = cls(action_list, self.personas)
            for r in verifier.run_all():
                report.results.append(r)
        for cls in self.compliance_verifiers:
            verifier = cls(action_list, self.personas)
            for r in verifier.run_all():
                report.results.append(r)
        return report
