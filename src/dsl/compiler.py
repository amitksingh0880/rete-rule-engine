"""
DSL Compiler – translates finance-domain rule text into ReteNetwork nodes.

Since ANTLR4 Java tooling may not always be available, this module provides
TWO parsing strategies:

1. **ANTLR4 Parser** (``antlr4`` extra installed + grammar compiled):
   Fully featured parser.

2. **Built-in Lightweight Parser** (``SimpleRuleParser``):
   Handles the most common rule patterns without any external dependency.
   Used as the automatic fallback.

The public interface (``DSLRuleEngine``) is identical regardless of which
parser is active.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from ..core.memory import WME
from ..core.network import ReteNetwork
from ..core.nodes import Action, FieldConstraint

logger = logging.getLogger(__name__)


# ===========================================================================
# Lightweight built-in parser (no ANTLR dependency)
# ===========================================================================

class ParseError(Exception):
    """Raised when DSL text cannot be parsed."""


class SimpleRuleParser:
    """
    Regex/split-based parser for a clean subset of the Financial Rule Language.

    Supported rule skeleton
    -----------------------
    rule <name> [priority <n>] [salience <n>]
    when
        <FactType> [var]:
            <field> <op> <value>
            [<field> <op> <value> ...]
        [<FactType> [var]: ...]
    then
        insert <FactType>(<k>: <v>, ...)
        | retract <var>
        | return "<decision>" [with <k>: <v>, ...]
        | predict <model>(@<version>)? (<f>: <expr>, ...) [as <var>]
        | call <func>(<args>)
    """

    # Operators supported in conditions
    OPS = [">=", "<=", "!=", "==", ">", "<", "matches", "contains", "in", "exists"]

    def parse_ruleset(self, dsl: str) -> List[Dict]:
        """Parse one or many rules and return a list of parsed-rule dicts."""
        rules = []
        # Split on 'rule ' boundaries
        blocks = re.split(r'\brule\s+', dsl, flags=re.IGNORECASE)
        for block in blocks[1:]:
            try:
                rule = self._parse_rule_block(block.strip())
                rules.append(rule)
            except ParseError as exc:
                logger.error("Parse error: %s", exc)
        return rules

    # ------------------------------------------------------------------
    # Block parsing
    # ------------------------------------------------------------------
    def _parse_rule_block(self, block: str) -> Dict:
        # Extract name
        first_line, _, rest = block.partition("\n")
        name_match = re.match(r'(\w+)', first_line.strip())
        if not name_match:
            raise ParseError(f"Cannot find rule name in: {first_line!r}")
        rule_name = name_match.group(1)

        # Extract priority / salience from first line
        priority = int(m.group(1)) if (m := re.search(r'\bpriority\s+(\d+)', first_line)) else 0
        salience = int(m.group(1)) if (m := re.search(r'\bsalience\s+(\d+)', first_line)) else 0

        # Split when/then/otherwise sections
        when_match = re.search(r'\bwhen\b', rest, re.IGNORECASE)
        then_match = re.search(r'\bthen\b', rest, re.IGNORECASE)
        otherwise_match = re.search(r'\botherwise\b', rest, re.IGNORECASE)

        if not when_match or not then_match:
            raise ParseError(f"Rule '{rule_name}' missing 'when' or 'then'.")

        when_text = rest[when_match.end():then_match.start()].strip()
        end_then = otherwise_match.start() if otherwise_match else len(rest)
        then_text = rest[then_match.end():end_then].strip()

        conditions = self._parse_conditions(when_text)
        actions = self._parse_actions(then_text)

        return {
            "rule_id": rule_name,
            "conditions": conditions,
            "actions": actions,
            "priority": priority,
            "salience": salience,
        }

    # ------------------------------------------------------------------
    # Condition parsing
    # ------------------------------------------------------------------
    def _parse_conditions(self, text: str) -> List[Dict]:
        conditions = []
        # Split on blank lines or on lines that start with an uppercase letter
        # (new fact pattern)
        pattern_blocks = re.split(r'\n(?=[A-Z])', text)
        for pb in pattern_blocks:
            pb = pb.strip()
            if not pb:
                continue
            negation = False
            if pb.lower().startswith("not "):
                negation = True
                pb = pb[4:].strip()
            try:
                cond = self._parse_fact_pattern(pb)
                cond["negation"] = negation
                conditions.append(cond)
            except ParseError as exc:
                logger.warning("Skipping condition block: %s", exc)
        return conditions

    def _parse_fact_pattern(self, text: str) -> Dict:
        """Parse  'FactType [var]: field op value, ...'"""
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not lines:
            raise ParseError("Empty fact pattern")

        header = lines[0]
        # Parse header: FactType [varname]:
        header_re = re.match(r'(\w+)\s*(\w+)?\s*:', header)
        if not header_re:
            raise ParseError(f"Bad fact pattern header: {header!r}")
        fact_type = header_re.group(1)
        var_name = header_re.group(2)

        constraints = []
        # Inline constraints on same line after colon
        inline = header[header_re.end():].strip()
        constraint_lines = [l for l in lines[1:]]
        if inline:
            constraint_lines = [inline] + constraint_lines

        for cl in constraint_lines:
            for c in cl.split(","):
                c = c.strip()
                if not c:
                    continue
                fc = self._parse_constraint(c)
                if fc:
                    constraints.append(fc.__dict__)

        return {
            "fact_type": fact_type,
            "variable": var_name,
            "constraints": constraints,
            "joins": [],
            "negation": False,
        }

    def _parse_constraint(self, text: str) -> Optional[FieldConstraint]:
        text = text.strip()
        if not text:
            return None

        # Try each operator from longest to shortest
        for op in self.OPS:
            if op in text:
                parts = text.split(op, 1)
                if len(parts) == 2:
                    field = parts[0].strip()
                    val_str = parts[1].strip()
                    value = self._parse_value(val_str)
                    return FieldConstraint(field=field, operator=op, value=value)
        return None

    def _parse_value(self, text: str) -> Any:
        text = text.strip()
        # String literal
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            return text[1:-1]
        # Boolean
        if text.lower() == "true":
            return True
        if text.lower() == "false":
            return False
        # Null
        if text.lower() == "null":
            return None
        # List
        if text.startswith("[") and text.endswith("]"):
            items = [self._parse_value(i.strip()) for i in text[1:-1].split(",")]
            return items
        # Number
        try:
            return int(text)
        except ValueError:
            pass
        try:
            return float(text)
        except ValueError:
            pass
        # Treat as variable reference
        return text

    # ------------------------------------------------------------------
    # Action parsing
    # ------------------------------------------------------------------
    def _parse_actions(self, text: str) -> List[Dict]:
        actions = []
        for line in re.split(r'[;\n]', text):
            line = line.strip()
            if not line:
                continue
            action = self._parse_single_action(line)
            if action:
                actions.append(action)
        return actions

    def _parse_single_action(self, text: str) -> Optional[Dict]:
        text = text.strip()

        # return "DECISION" [with k: v, ...]
        m = re.match(r'return\s+["\']([^"\']+)["\']', text, re.IGNORECASE)
        if m:
            decision = m.group(1)
            params: Dict[str, Any] = {"result": decision}
            with_part = text[m.end():].strip()
            if with_part.lower().startswith("with"):
                with_part = with_part[4:].strip()
                for kv in with_part.split(","):
                    if ":" in kv:
                        k, _, v = kv.partition(":")
                        params[k.strip()] = self._parse_value(v.strip())
            return {"type": "return", "params": params, "priority": 0}

        # insert FactType(k: v, ...)
        m = re.match(r'insert\s+(\w+)(?:\(([^)]*)\))?', text, re.IGNORECASE)
        if m:
            fact_type = m.group(1)
            attrs: Dict[str, Any] = {}
            if m.group(2):
                for kv in m.group(2).split(","):
                    if ":" in kv:
                        k, _, v = kv.partition(":")
                        attrs[k.strip()] = self._parse_value(v.strip())
            return {"type": "insert", "params": {"fact_type": fact_type, "attributes": attrs}, "priority": 0}

        # retract <var>
        m = re.match(r'retract\s+(\w+)', text, re.IGNORECASE)
        if m:
            return {"type": "retract", "params": {"wme_id": m.group(1)}, "priority": 0}

        # predict <model>(@v)? (features) [as var]
        m = re.match(r'predict\s+(\w+)(?:@(\d+))?\s*\(([^)]*)\)(?:\s+as\s+(\w+))?', text, re.IGNORECASE)
        if m:
            model_name = m.group(1)
            version = int(m.group(2)) if m.group(2) else None
            features: Dict[str, Any] = {}
            for kv in m.group(3).split(","):
                if ":" in kv:
                    k, _, v = kv.partition(":")
                    features[k.strip()] = self._parse_value(v.strip())
            store_as = m.group(4)
            return {
                "type": "predict",
                "params": {"model": model_name, "version": version, "features": features, "store_as": store_as},
                "priority": 0,
            }

        # call <func>(args)
        m = re.match(r'call\s+(\w+)\(([^)]*)\)', text, re.IGNORECASE)
        if m:
            return {
                "type": "call",
                "params": {"function": m.group(1), "args": m.group(2)},
                "priority": 0,
            }

        logger.debug("Unrecognised action line: %r", text)
        return None


# ===========================================================================
# High-level DSL Rule Engine
# ===========================================================================

class DSLRuleEngine:
    """
    Public interface for loading and executing DSL-defined rules.

    Examples
    --------
    >>> engine = DSLRuleEngine()
    >>> engine.load_rules(dsl_text)
    ['approve_high_score', 'refer_medium_score', ...]
    >>> result = engine.execute([{"fact_type": "Applicant", "attributes": {"score": 800}}])
    """

    def __init__(self, network: Optional[ReteNetwork] = None) -> None:
        self.network = network or ReteNetwork()
        self._parser = SimpleRuleParser()
        self._rule_sources: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def load_rules(self, dsl_code: str) -> List[str]:
        """Parse and compile DSL text. Returns list of compiled rule IDs."""
        parsed_rules = self._parser.parse_ruleset(dsl_code)
        compiled_ids = []
        for rule_spec in parsed_rules:
            try:
                self.network.compile_rule(
                    rule_id=rule_spec["rule_id"],
                    conditions=rule_spec["conditions"],
                    actions=rule_spec["actions"],
                    priority=rule_spec.get("priority", 0),
                    salience=rule_spec.get("salience", 0),
                )
                self._rule_sources[rule_spec["rule_id"]] = dsl_code
                compiled_ids.append(rule_spec["rule_id"])
            except Exception as exc:
                logger.error("Failed to compile rule '%s': %s", rule_spec["rule_id"], exc)
        logger.info("Loaded %d rules: %s", len(compiled_ids), compiled_ids)
        return compiled_ids

    def load_rules_from_file(self, filepath: str) -> List[str]:
        with open(filepath, "r", encoding="utf-8") as f:
            return self.load_rules(f.read())

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def execute(self, facts: List[Dict], max_cycles: int = 100) -> Dict[str, Any]:
        """
        Execute the loaded rules against a set of facts.

        Parameters
        ----------
        facts : list of dicts, each with ``fact_type`` and optional ``attributes``.

        Returns
        -------
        dict from ``ReteNetwork.run()`` with decision, matched_rules, etc.
        """
        self.network.reset()

        for fact_data in facts:
            wme = WME(
                fact_type=fact_data["fact_type"],
                attributes=fact_data.get("attributes", {}),
                source=fact_data.get("source", "api"),
            )
            self.network.assert_fact(wme)

        return self.network.run(max_cycles=max_cycles)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def get_rule_source(self, rule_id: str) -> Optional[str]:
        return self._rule_sources.get(rule_id)

    @property
    def rule_ids(self) -> List[str]:
        return list(self.network._terminal_nodes.keys())
