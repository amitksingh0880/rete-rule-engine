"""
FactValidator – validates incoming fact payloads before assertion.

Supports:
  * Required field checking
  * Type coercion / enforcement
  * Range / regex constraints
  * Custom per-type validators
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from .exceptions import FactValidationError


# Validation schema for built-in fact types
_BUILT_IN_SCHEMAS: Dict[str, Dict[str, Dict]] = {
    "Applicant": {
        "credit_score": {"type": int, "min": 300, "max": 850, "required": False},
        "annual_income": {"type": (int, float), "min": 0, "required": False},
        "age": {"type": int, "min": 18, "required": False},
    },
    "Policy": {
        "policy_number": {"type": str, "required": False},
        "premium": {"type": (int, float), "min": 0, "required": False},
    },
    "Claim": {
        "amount": {"type": (int, float), "min": 0, "required": False},
        "status": {
            "type": str,
            "choices": ["OPEN", "CLOSED", "PENDING", "DISPUTED"],
            "required": False,
        },
    },
}


class FactValidator:
    """
    Validates WME attribute payloads.

    Usage
    -----
    >>> validator = FactValidator()
    >>> validator.validate("Applicant", {"credit_score": 750, "annual_income": 60000})
    []  # no errors
    """

    def __init__(self) -> None:
        self._schemas: Dict[str, Dict[str, Dict]] = dict(_BUILT_IN_SCHEMAS)
        self._custom: Dict[str, List[Callable]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register_schema(self, fact_type: str, schema: Dict[str, Dict]) -> None:
        """Register or override a validation schema for a fact type."""
        self._schemas[fact_type] = schema

    def register_custom_validator(self, fact_type: str, fn: Callable) -> None:
        """Register an additional callable validator.
        ``fn(attributes) -> List[str]`` returns a list of error messages.
        """
        self._custom.setdefault(fact_type, []).append(fn)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self, fact_type: str, attributes: Dict[str, Any]) -> List[str]:
        """
        Validate attributes against the schema for the given fact type.
        Returns a list of human-readable error messages (empty = valid).
        """
        errors: List[str] = []
        schema = self._schemas.get(fact_type, {})

        # Check required fields
        for field, rules in schema.items():
            if rules.get("required") and field not in attributes:
                errors.append(f"Required field '{field}' is missing.")

        # Check each provided attribute
        for field, value in attributes.items():
            rules = schema.get(field)
            if rules is None:
                continue  # Unknown field – allowed by default

            # Type check
            expected_type = rules.get("type")
            if expected_type and not isinstance(value, expected_type):
                errors.append(
                    f"Field '{field}': expected {expected_type}, got {type(value).__name__}."
                )
                continue  # Skip further checks for this field

            # Numeric bounds
            if rules.get("min") is not None and value is not None and value < rules["min"]:
                errors.append(f"Field '{field}'={value} is below minimum {rules['min']}.")
            if rules.get("max") is not None and value is not None and value > rules["max"]:
                errors.append(f"Field '{field}'={value} exceeds maximum {rules['max']}.")

            # Choices / enum
            choices = rules.get("choices")
            if choices and value not in choices:
                errors.append(f"Field '{field}'={value!r} not in allowed values {choices}.")

            # Regex pattern
            pattern = rules.get("pattern")
            if pattern and isinstance(value, str):
                if not re.match(pattern, value):
                    errors.append(f"Field '{field}'={value!r} does not match pattern {pattern!r}.")

        # Custom validators
        for fn in self._custom.get(fact_type, []):
            errors.extend(fn(attributes))

        return errors

    def validate_or_raise(self, fact_type: str, attributes: Dict[str, Any]) -> None:
        """Validate and raise ``FactValidationError`` on first failure."""
        errors = self.validate(fact_type, attributes)
        if errors:
            raise FactValidationError(
                fact_type=fact_type,
                field="(multiple)" if len(errors) > 1 else errors[0].split("'")[1],
                reason="; ".join(errors),
            )
