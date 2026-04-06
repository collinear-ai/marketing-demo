"""
gym_core — shared abstractions for the Long-Horizon Agent Evaluation Gym.

All scenario packages import their schema, predicates, and verifier base classes
from this package. Scenarios should NOT redefine ActionType, Action,
VerifierResult, or predicate helpers locally.

Typical scenario verifier file:

    from gym_core import (
        Action, ActionType, BaseTaskVerifier, ScenarioVerifier,
        VerifierResult, predicates as P, PersonaPool,
    )

    class T1_PullMetrics(BaseTaskVerifier):
        task_id = "T1"
        def run_all(self):
            msgs = P.actions_to(self.actions, "kenji_watanabe",
                                ActionType.SLACK_MESSAGE)
            yield self.boolean("T1_PC1", "slack_message_sent", bool(msgs),
                               f"Found {len(msgs)} message(s) to Kenji.")
            ...
"""

from gym_core.schema import (
    Action,
    ActionType,
    RubricScore,
    Severity,
    VerifierResult,
)
from gym_core.persona import Persona, PersonaPool
from gym_core.verifier_base import (
    BaseTaskVerifier,
    ComplianceVerifier,
    ScenarioVerifier,
)
from gym_core import predicates

__all__ = [
    "Action",
    "ActionType",
    "BaseTaskVerifier",
    "ComplianceVerifier",
    "Persona",
    "PersonaPool",
    "RubricScore",
    "ScenarioVerifier",
    "Severity",
    "VerifierResult",
    "predicates",
]
