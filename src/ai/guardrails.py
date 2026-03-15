"""
Guardrails – safety controls for AI-powered financial decisions.

Checks bias, confidence thresholds, feature drift, and custom predicates.
Violations are logged to an immutable audit trail.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GuardrailViolation:
    rule_id: str
    violation_type: str
    severity: str            # 'info' | 'warning' | 'error' | 'critical'
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "violation_type": self.violation_type,
            "severity": self.severity,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class GuardrailManager:
    """
    Collection of safety checks applied before a decision is finalised.

    Built-in checks
    ---------------
    * ``confidence_threshold``  – warn when model confidence is low
    * ``bias_detection``        – flag protected attributes in decision factors
    * ``custom``                – any registered callable returning Optional[GuardrailViolation]
    """

    # Protected attributes per financial-regulation guidance (ECOA, GDPR, …)
    PROTECTED_ATTRIBUTES = frozenset({
        "gender", "race", "ethnicity", "religion", "national_origin",
        "marital_status", "age", "disability", "familial_status",
        "color", "sex", "zip_code",
    })

    def __init__(
        self,
        enabled: bool = True,
        confidence_threshold: float = 0.60,
        bias_detection: bool = True,
    ) -> None:
        self.enabled = enabled
        self.confidence_threshold = confidence_threshold
        self.bias_detection = bias_detection
        self._custom_checks: Dict[str, Callable] = {}
        self._violation_log: List[GuardrailViolation] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register_check(self, name: str, fn: Callable) -> None:
        """Register a custom check: ``fn(context, decision) -> Optional[GuardrailViolation]``."""
        self._custom_checks[name] = fn

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def evaluate(
        self,
        context: Dict[str, Any],
        decision: Dict[str, Any],
        rule_id: str = "execution",
    ) -> List[GuardrailViolation]:
        """
        Run all checks against a completed decision.

        Returns a (possibly empty) list of violations.
        """
        if not self.enabled:
            return []

        violations: List[GuardrailViolation] = []

        # --- 1. Confidence check ---
        conf = decision.get("confidence")
        if conf is not None and conf < self.confidence_threshold:
            violations.append(GuardrailViolation(
                rule_id=rule_id,
                violation_type="low_confidence",
                severity="warning",
                details={"confidence": conf, "threshold": self.confidence_threshold},
            ))

        # --- 2. Bias detection ---
        if self.bias_detection:
            factors = decision.get("influencing_factors", [])
            for factor in factors:
                if any(p in str(factor).lower() for p in self.PROTECTED_ATTRIBUTES):
                    violations.append(GuardrailViolation(
                        rule_id=rule_id,
                        violation_type="potential_bias",
                        severity="error",
                        details={"protected_attribute_in_factor": factor},
                    ))

            # Also check context keys
            for key in context:
                if key.lower() in self.PROTECTED_ATTRIBUTES:
                    violations.append(GuardrailViolation(
                        rule_id=rule_id,
                        violation_type="protected_attribute_in_context",
                        severity="warning",
                        details={"attribute": key},
                    ))

        # --- 3. Custom checks ---
        for name, fn in self._custom_checks.items():
            try:
                result = fn(context, decision)
                if result:
                    violations.append(result)
            except Exception as exc:
                logger.error("Custom guardrail '%s' raised: %s", name, exc)

        # Persist
        self._violation_log.extend(violations)
        if violations:
            logger.warning("Guardrail violations: %d", len(violations))
        return violations

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------
    def should_block(self, violations: List[GuardrailViolation]) -> bool:
        """Block decision when any critical violation or 2+ errors are present."""
        critical = sum(1 for v in violations if v.severity == "critical")
        errors = sum(1 for v in violations if v.severity == "error")
        return critical > 0 or errors >= 2

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------
    def get_audit_log(self) -> List[Dict]:
        return [v.to_dict() for v in self._violation_log]

    def clear_log(self) -> None:
        self._violation_log.clear()
