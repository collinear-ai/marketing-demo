"""
Referential integrity linter for scenario packages.

Catches the failure mode where a persona rename, task renumbering, or rubric
tweak in one file silently breaks the other three. Run it on a scenario
directory and it will report every cross-file mismatch.

Usage:
    uv run python -m gym_core.lint path/to/scenario_dir

Or in a test:
    from gym_core.lint import lint_scenario
    issues = lint_scenario("gym/domains/hr/s1_termination_reorg")
    assert not issues, issues
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from gym_core.persona import PersonaPool
from gym_core.rubric_schema import load_rubrics


@dataclass
class LintIssue:
    severity: str          # "error" | "warning"
    file: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.file}: {self.message}"


def lint_scenario(scenario_dir: str | Path) -> list[LintIssue]:
    scenario_dir = Path(scenario_dir)
    issues: list[LintIssue] = []

    personas_path = _find_personas_file(scenario_dir)
    dag_path = scenario_dir / "dag.md"
    if not dag_path.exists():
        dag_path = scenario_dir / "project_dag.md"
    rubrics_path = scenario_dir / "rubrics.yaml"
    verifiers_path = scenario_dir / "verifiers.py"

    for required, p in [
        ("personas", personas_path),
        ("dag", dag_path),
        ("rubrics", rubrics_path),
        ("verifiers", verifiers_path),
    ]:
        if p is None or not Path(p).exists():
            issues.append(LintIssue("error", str(scenario_dir), f"missing {required} file"))
    if issues:
        return issues

    # ----- load each file -----
    pool = PersonaPool.from_yaml(str(personas_path))
    persona_ids = set(pool.ids())

    dag_text = dag_path.read_text()
    dag_task_ids = _extract_task_ids(dag_text)
    dag_persona_refs = _extract_persona_refs(dag_text, persona_ids)

    rubrics = load_rubrics(str(rubrics_path))
    rubric_check_ids = rubrics.programmatic_check_ids()
    rubric_task_ids = {t.task_id for t in rubrics.tasks.values()}

    verifier_src = verifiers_path.read_text()
    verifier_check_ids = _extract_verifier_check_ids(verifier_src)
    verifier_persona_refs = _extract_persona_refs(verifier_src, persona_ids)

    # ----- checks -----

    # 1. Every rubric task has a DAG task.
    missing_in_dag = rubric_task_ids - dag_task_ids
    for tid in sorted(missing_in_dag):
        issues.append(LintIssue(
            "error", "rubrics.yaml",
            f"rubric references task {tid} not present in DAG",
        ))

    # 2. Every DAG task has at least one rubric entry.
    missing_in_rubrics = dag_task_ids - rubric_task_ids
    for tid in sorted(missing_in_rubrics):
        issues.append(LintIssue(
            "warning", "rubrics.yaml",
            f"DAG task {tid} has no rubric entries",
        ))

    # 3. Every programmatic check id in rubrics is emitted by some verifier.
    missing_impl = rubric_check_ids - verifier_check_ids
    for cid in sorted(missing_impl):
        issues.append(LintIssue(
            "error", "verifiers.py",
            f"programmatic check {cid} declared in rubrics has no verifier implementation",
        ))

    # 4. Every check id emitted by a verifier is declared in rubrics.
    orphan_checks = verifier_check_ids - rubric_check_ids
    for cid in sorted(orphan_checks):
        issues.append(LintIssue(
            "warning", "verifiers.py",
            f"verifier emits check {cid} not declared in rubrics",
        ))

    # 5. Every persona_id referenced in dag/verifiers exists in persona pool.
    all_refs = dag_persona_refs | verifier_persona_refs
    unknown = {r for r in all_refs if r not in persona_ids}
    for ref in sorted(unknown):
        issues.append(LintIssue(
            "error", "personas.yaml",
            f"persona '{ref}' referenced in DAG or verifier but not defined",
        ))

    # 6. Anti-pattern sweep on verifier source.
    issues.extend(_scan_anti_patterns(verifier_src))

    return issues


# ---------------------------------------------------------------------------
# anti-pattern source scanner
# ---------------------------------------------------------------------------

# Known bug classes from real trajectory runs, documented in gym/AUTHORING_GUIDE.md
# and scope_doc_cohere_long_horizon_gym.md errata. Each entry is
# (label, regex, advice).

_ANTI_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    # --- ActionType.EMAIL without encrypted variant ---
    (
        "ActionType.EMAIL filter likely misses ENCRYPTED_EMAIL",
        re.compile(r"ActionType\.EMAIL(?!_)"),
        "Use P.EMAIL_LIKE (or P.email_like_to sugar) instead of ActionType.EMAIL. "
        "Raw ActionType.EMAIL silently drops ENCRYPTED_EMAIL / EMAIL_REPLY / "
        "EMAIL_FORWARD, which causes false negatives when an agent correctly "
        "uses the encrypted channel (often the *required* channel for legal, "
        "HR privileged, or security topics).",
    ),
    # --- Naive substring negation on commonly-negated rationale words ---
    (
        "naive substring negation on rationale word 'performance'",
        re.compile(r'["\']performance["\']\s+not\s+in\b'),
        "Use P.contains_affirmative_phrase() or P.rationale_check() instead. "
        "A naive `\"performance\" not in body` check fires on the exact "
        "correct phrasing agents use to assert lawful rationale ('not a "
        "performance issue', 'no performance / fit / pretext language').",
    ),
    (
        "naive substring negation on rationale word 'terminate'",
        re.compile(r'["\']terminate["\']\s+not\s+in\b'),
        "Use P.contains_affirmative_phrase(). A careful agent may write "
        "'not a termination for cause' or 'will not be terminated' and trip "
        "this check.",
    ),
    (
        "naive substring negation on rationale word 'pretext'",
        re.compile(r'["\']pretext["\']\s+not\s+in\b'),
        "Use P.contains_affirmative_phrase(). 'no pretext' is the standard "
        "affirmative-rationale phrasing.",
    ),
    (
        "naive substring negation on rationale word 'discriminat'",
        re.compile(r'["\']discriminat[\w]*["\']\s+not\s+in\b'),
        "Use P.contains_affirmative_phrase(). A careful ER/HR agent will "
        "write 'no discriminatory intent' or 'not discriminatory' — both "
        "trip naive substring checks.",
    ),
    # --- Substring check on morphologically variable stems without siblings ---
    (
        "substring 'rescind' without accepting 'rescission'",
        re.compile(r'["\']rescind["\']\s+in\b'),
        "The standard HR/legal noun is 'rescission'. "
        "`'rescind' in 'rescission'` evaluates to False. Use a regex like "
        "re.search(r'rescin[ds]', ...) or accept both forms explicitly.",
    ),
    (
        "substring 'terminate' without accepting 'termination'",
        re.compile(r'["\']terminate["\']\s+in\b'),
        "Use re.search(r'terminat(e|ion|ed)', ...) or accept all morphological "
        "variants explicitly. Agents use whichever form fits the sentence.",
    ),
    # --- actions_to with body scan ignoring attachments ---
    (
        "cover-only body scan (may miss attached document content)",
        re.compile(r"(?:body|content)_has_all_keywords\b.*ActionType\.EMAIL"),
        "If the agent can fulfill this check by attaching a document_create "
        "action to a cover email, use P.doc_bundle_text(cover, all_actions) "
        "to concatenate cover body + attached document text before scanning.",
    ),
]


def _scan_anti_patterns(verifier_src: str) -> list["LintIssue"]:
    """Scan verifier source for known anti-patterns and return warnings.

    For the ``ActionType.EMAIL`` rule specifically we suppress warnings when
    ``ENCRYPTED_EMAIL`` or ``P.EMAIL_LIKE`` appears within the same logical
    block (±4 lines) — those sites are already handling the encrypted variant
    explicitly.
    """
    out: list[LintIssue] = []
    seen: set[tuple[int, str]] = set()

    lines = verifier_src.splitlines()
    for label, pat, advice in _ANTI_PATTERNS:
        for m in pat.finditer(verifier_src):
            line_num = verifier_src[:m.start()].count("\n") + 1
            line_content = lines[line_num - 1] if line_num - 1 < len(lines) else ""
            stripped = line_content.strip()
            if stripped.startswith("#"):
                continue

            # Suppress ActionType.EMAIL warnings when the same block already
            # handles ENCRYPTED_EMAIL (either in the same line or in the 4
            # lines above/below, which covers multi-line set literals).
            if label.startswith("ActionType.EMAIL filter"):
                lo = max(0, line_num - 5)
                hi = min(len(lines), line_num + 4)
                block = "\n".join(lines[lo:hi])
                if "ENCRYPTED_EMAIL" in block or "EMAIL_LIKE" in block:
                    continue

            key = (line_num, label)
            if key in seen:
                continue
            seen.add(key)
            out.append(LintIssue(
                severity="warning",
                file="verifiers.py",
                message=f"line {line_num}: {label}. {advice}",
            ))
    return out


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _find_personas_file(scenario_dir: Path) -> Path | None:
    # Prefer scenario-local personas.yaml, then climb to domain shared file.
    local = scenario_dir / "personas.yaml"
    if local.exists():
        return local
    parent = scenario_dir.parent
    for name in ("_personas.yaml", "personas.yaml"):
        candidate = parent / name
        if candidate.exists():
            return candidate
    return None


def _extract_task_ids(text: str) -> set[str]:
    # Match T1, T12, etc. used as task identifiers.
    return set(re.findall(r"\bT\d{1,2}\b", text))


_PERSONA_ID_RE = re.compile(r"\b([a-z][a-z0-9_]{2,})\b")


def _extract_persona_refs(text: str, known_ids: set[str]) -> set[str]:
    # Cheap: only flag tokens that look like persona ids AND are in known_ids
    # reverse-lookup pattern. Returns {} for free text.
    found = set()
    for m in _PERSONA_ID_RE.finditer(text):
        token = m.group(1)
        if token in known_ids:
            found.add(token)
    return found


def _extract_verifier_check_ids(src: str) -> set[str]:
    """Parse verifiers.py, find string literals like 'T1_PC1' passed as
    check_id argument to result/boolean/checklist calls."""
    ids = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return ids
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # self.result(check_id="T1_PC1", ...) or self.result("T1_PC1", ...)
        for kw in node.keywords:
            if kw.arg == "check_id" and isinstance(kw.value, ast.Constant):
                if isinstance(kw.value.value, str):
                    ids.add(kw.value.value)
        if node.args and isinstance(node.args[0], ast.Constant):
            val = node.args[0].value
            if isinstance(val, str) and re.match(r"^T\d+_[A-Z0-9_]+$", val):
                ids.add(val)
        # VerifierResult(check_id=...)
        if isinstance(node.func, ast.Name) and node.func.id == "VerifierResult":
            for kw in node.keywords:
                if kw.arg == "check_id" and isinstance(kw.value, ast.Constant):
                    if isinstance(kw.value.value, str):
                        ids.add(kw.value.value)
    return ids


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m gym_core.lint <scenario_dir> [...]")
        return 2
    any_errors = False
    for d in sys.argv[1:]:
        issues = lint_scenario(d)
        if not issues:
            print(f"OK  {d}")
            continue
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]
        print(f"{'FAIL' if errors else 'WARN'}  {d}  ({len(errors)} errors, {len(warnings)} warnings)")
        for i in issues:
            print(f"  {i}")
        if errors:
            any_errors = True
    return 1 if any_errors else 0


if __name__ == "__main__":
    sys.exit(main())
