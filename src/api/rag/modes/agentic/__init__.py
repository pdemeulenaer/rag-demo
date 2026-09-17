"""Bounded Agentic RAG mode.

Phase 4 contains contracts only. The Phase 5 executor will be exposed from this
package without changing the Vanilla or Hybrid implementations.
"""

from .contracts import (
    AgentBudget,
    AgentPlan,
    BudgetUsage,
    EvidenceNeed,
    NeedAssessment,
    QuestionScope,
    StopReason,
    SufficiencyDecision,
    ToolAction,
    action_fingerprint,
    budget_stop_reason,
    validate_decision_for_plan,
)

__all__ = [
    "AgentBudget",
    "AgentPlan",
    "BudgetUsage",
    "EvidenceNeed",
    "NeedAssessment",
    "QuestionScope",
    "StopReason",
    "SufficiencyDecision",
    "ToolAction",
    "action_fingerprint",
    "budget_stop_reason",
    "validate_decision_for_plan",
]
