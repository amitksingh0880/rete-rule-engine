"""
Custom exception hierarchy for the Finance Rule Engine.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class RuleEngineError(Exception):
    """Base exception for all rule engine errors."""

    def __init__(self, message: str, code: str = "ENGINE_ERROR", details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {"error": self.code, "message": self.message, "details": self.details}


class RuleCompilationError(RuleEngineError):
    """Raised when a rule cannot be compiled (syntax/semantic error)."""
    def __init__(self, rule_id: str, reason: str, line: Optional[int] = None):
        super().__init__(
            f"Compilation error in rule '{rule_id}': {reason}",
            code="COMPILATION_ERROR",
            details={"rule_id": rule_id, "reason": reason, "line": line},
        )


class RuleExecutionError(RuleEngineError):
    """Raised when rule execution fails at runtime."""
    def __init__(self, rule_id: str, reason: str):
        super().__init__(
            f"Execution error in rule '{rule_id}': {reason}",
            code="EXECUTION_ERROR",
            details={"rule_id": rule_id, "reason": reason},
        )


class FactValidationError(RuleEngineError):
    """Raised when a fact fails schema validation."""
    def __init__(self, fact_type: str, field: str, reason: str):
        super().__init__(
            f"Validation failed for '{fact_type}.{field}': {reason}",
            code="VALIDATION_ERROR",
            details={"fact_type": fact_type, "field": field, "reason": reason},
        )


class GuardrailViolationError(RuleEngineError):
    """Raised when a critical guardrail is violated and execution must halt."""
    def __init__(self, violations: List[Dict]):
        super().__init__(
            f"Critical guardrail violations: {len(violations)}",
            code="GUARDRAIL_VIOLATION",
            details={"violations": violations},
        )


class ModelNotFoundError(RuleEngineError):
    """Raised when a requested ML model is not registered."""
    def __init__(self, model_name: str, version: Optional[int] = None):
        ver_str = f"@v{version}" if version else ""
        super().__init__(
            f"Model '{model_name}{ver_str}' not found in registry.",
            code="MODEL_NOT_FOUND",
            details={"model_name": model_name, "version": version},
        )


class CycleLimitExceededError(RuleEngineError):
    """Raised when the execution cycle limit is hit (possible infinite loop)."""
    def __init__(self, limit: int):
        super().__init__(
            f"Rule execution exceeded {limit} cycles – possible infinite loop.",
            code="CYCLE_LIMIT_EXCEEDED",
            details={"limit": limit},
        )
