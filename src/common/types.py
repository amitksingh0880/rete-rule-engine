"""
Shared type definitions for the Finance Rule Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class FactType(str, Enum):
    """Standard fact types in the finance/insurance domain."""
    APPLICANT = "Applicant"
    POLICY = "Policy"
    CLAIM = "Claim"
    PAYMENT = "Payment"
    RISK_FACTOR = "RiskFactor"
    ML_PREDICTION = "MLPrediction"
    DECISION = "Decision"


class DecisionResult(str, Enum):
    """Standard decision outcomes."""
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    REFERRED = "REFERRED"
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


@dataclass
class RuleExecutionContext:
    """
    Carries execution metadata for a single rules-evaluation request.
    """
    request_id: str
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    facts: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    trace_enabled: bool = False
    max_cycles: int = 100


@dataclass
class RuleMatch:
    """Record of a single rule firing."""
    rule_id: str
    matched_fact_ids: List[str]
    bindings: Dict[str, Any]
    action_results: List[Dict]


@dataclass
class ExecutionResult:
    """Complete result of a rules-engine execution."""
    decision: Optional[str]
    rule_matches: List[RuleMatch] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    cycles: int = 0
    latency_ms: float = 0.0
    guardrail_violations: List[Dict] = field(default_factory=list)
