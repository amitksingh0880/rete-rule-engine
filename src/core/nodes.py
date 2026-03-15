"""
Rete Network Node implementations.

AlphaNode  – single-input node that tests individual fact attributes.
BetaNode   – two-input join node combining left-token partial matches with
             right-WME alpha matches.
TerminalNode – end of the network; fires rule actions upon activation.
Token       – partial match flowing through the beta network.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

from .memory import WME

if TYPE_CHECKING:
    from .network import ReteNetwork

logger = logging.getLogger(__name__)


# ===========================================================================
# Data-transfer types
# ===========================================================================

@dataclass
class Token:
    """
    Partial match in the Beta network.

    A token is an ordered sequence of WMEs that satisfy conditions left-to-right.
    Variable bindings are accumulated as the token moves downstream.
    """
    wmes: List[Optional[WME]] = field(default_factory=list)
    parent: Optional["Token"] = None
    bindings: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    def extend(self, wme: Optional[WME], new_bindings: Optional[Dict] = None) -> "Token":
        """Return a new child token extending this one by one WME."""
        merged = {**self.bindings, **(new_bindings or {})}
        return Token(wmes=self.wmes + [wme], parent=self, bindings=merged)

    def get_binding(self, var: str) -> Any:
        return self.bindings.get(var)

    def __hash__(self):
        return hash(tuple(w.id if w else "None" for w in self.wmes))

    def __eq__(self, other):
        return isinstance(other, Token) and self.wmes == other.wmes

    def __repr__(self):
        return f"Token(len={len(self.wmes)})"


@dataclass
class FieldConstraint:
    """A single test on one attribute of an incoming WME."""
    field: str
    operator: str          # '==', '!=', '>', '<', '>=', '<=', 'in', 'exists', 'matches'
    value: Any
    value_is_variable: bool = False   # If True, 'value' is a variable name for join-time binding


class TestType(Enum):
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    GREATER = "greater"
    LESS = "less"
    PREDICATE = "predicate"


@dataclass
class JoinTest:
    """A cross-condition test between a field in the left token and a field in the right WME."""
    type: TestType
    left_field: str
    right_field: str
    left_wme_index: int = -1          # Which WME in the left token; -1 = last
    predicate: Optional[Callable] = None


@dataclass
class Action:
    """Declarative description of a rule action."""
    type: str                         # 'insert' | 'retract' | 'modify' | 'call' | 'return' | 'predict'
    params: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0


# ===========================================================================
# Alpha Network
# ===========================================================================

class AlphaNode:
    """
    One-input node performing attribute tests on individual WMEs.
    Implements *node sharing* – identical constraint sets reuse the same node.
    """

    def __init__(self, constraints: List[FieldConstraint], node_id: str = "") -> None:
        self.node_id = node_id or f"alpha_{id(self):x}"
        self.constraints = constraints
        self.memory: Set[WME] = set()          # WMEs that passed all tests
        self.children: List[BetaNode] = []
        self.shared: bool = False
        self._compiled = self._compile()

    # ------------------------------------------------------------------
    # Compilation
    # ------------------------------------------------------------------
    def _compile(self) -> List[Callable[[WME], bool]]:
        """Pre-compile constraints to callable predicates for speed."""
        tests: List[Callable[[WME], bool]] = []
        for c in self.constraints:
            if c.value_is_variable:
                continue
            op = c.operator
            f, v = c.field, c.value

            def make_test(field: str, operator: str, value: Any):
                if operator == "==":
                    return lambda w: w.get(field) == value
                elif operator == "!=":
                    return lambda w: w.get(field) != value
                elif operator == ">":
                    return lambda w: (val := w.get(field)) is not None and val > value
                elif operator == "<":
                    return lambda w: (val := w.get(field)) is not None and val < value
                elif operator == ">=":
                    return lambda w: (val := w.get(field)) is not None and val >= value
                elif operator == "<=":
                    return lambda w: (val := w.get(field)) is not None and val <= value
                elif operator == "in":
                    return lambda w: w.get(field) in value
                elif operator == "exists":
                    return lambda w: w.get(field) is not None
                elif operator == "matches":
                    pattern = re.compile(str(value))
                    return lambda w: bool(pattern.match(str(w.get(field, ""))))
                return lambda w: True

            tests.append(make_test(f, op, v))
        return tests

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------
    def test(self, wme: WME) -> bool:
        try:
            return all(t(wme) for t in self._compiled)
        except Exception as exc:
            logger.error("AlphaNode %s test error for WME %s: %s", self.node_id, wme.id, exc)
            return False

    def activate(self, wme: WME) -> None:
        if not self.test(wme) or wme in self.memory:
            return
        self.memory.add(wme)
        logger.debug("AlphaNode %s matched WME %s", self.node_id, wme.id)
        for child in self.children:
            child.right_activate(wme)

    def deactivate(self, wme: WME) -> None:
        if wme not in self.memory:
            return
        self.memory.discard(wme)
        for child in self.children:
            child.right_deactivate(wme)

    def add_child(self, beta: "BetaNode") -> None:
        if beta not in self.children:
            self.children.append(beta)

    # ------------------------------------------------------------------
    # Node sharing support
    # ------------------------------------------------------------------
    def _key(self) -> Tuple:
        return tuple((c.field, c.operator, str(c.value), c.value_is_variable) for c in self.constraints)

    def __hash__(self):
        return hash(self._key())

    def __eq__(self, other):
        return isinstance(other, AlphaNode) and self._key() == other._key()


# ===========================================================================
# Beta Network
# ===========================================================================

class BetaNode:
    """
    Two-input join node.

    Left input  – tokens from the parent beta node (or bootstrap for first condition).
    Right input – WMEs from an alpha node.

    When ``is_not_node`` is True this acts as a *negated conjunctive condition*
    (NCC):  a left-token propagates only when *no* matching right-WME exists.
    """

    def __init__(
        self,
        join_tests: List[JoinTest],
        node_id: str = "",
        is_not_node: bool = False,
    ) -> None:
        self.node_id = node_id or f"beta_{id(self):x}"
        self.join_tests = join_tests
        self.is_not_node = is_not_node

        self.left_memory: List[Token] = []
        self.right_memory: Set[WME] = set()

        self.children: List["BetaNode"] = []
        self.terminal: Optional[TerminalNode] = None

    # ------------------------------------------------------------------
    # Left activation (from parent beta / bootstrap)
    # ------------------------------------------------------------------
    def left_activate(self, token: Token) -> None:
        self.left_memory.append(token)
        if self.is_not_node:
            # NCC: propagate only if nothing in right memory matches
            if not any(self._join_ok(token, w) for w in self.right_memory):
                self._propagate(token, None)
        else:
            for wme in self.right_memory:
                if self._join_ok(token, wme):
                    self._propagate(token, wme)

    # ------------------------------------------------------------------
    # Right activation (from alpha node)
    # ------------------------------------------------------------------
    def right_activate(self, wme: WME) -> None:
        self.right_memory.add(wme)
        if self.is_not_node:
            # Some previously propagated tokens may now be blocked
            for token in list(self.left_memory):
                if self._join_ok(token, wme):
                    self._retract(token)
        else:
            for token in self.left_memory:
                if self._join_ok(token, wme):
                    self._propagate(token, wme)

    def right_deactivate(self, wme: WME) -> None:
        if wme not in self.right_memory:
            return
        self.right_memory.discard(wme)
        if self.is_not_node:
            # Tokens that were blocked by this WME may now propagate
            for token in self.left_memory:
                if not any(self._join_ok(token, w) for w in self.right_memory):
                    self._propagate(token, None)

    # ------------------------------------------------------------------
    # Join testing
    # ------------------------------------------------------------------
    def _join_ok(self, token: Token, wme: WME) -> bool:
        for jt in self.join_tests:
            if not self._eval_test(jt, token, wme):
                return False
        return True

    def _eval_test(self, jt: JoinTest, token: Token, wme: WME) -> bool:
        if not token.wmes:
            return True
        idx = jt.left_wme_index
        if idx >= len(token.wmes):
            return True
        left_wme = token.wmes[idx]
        if left_wme is None:
            return True
        lv = left_wme.get(jt.left_field)
        rv = wme.get(jt.right_field)
        t = jt.type
        if t == TestType.EQUAL:
            return lv == rv
        elif t == TestType.NOT_EQUAL:
            return lv != rv
        elif t == TestType.GREATER:
            return lv is not None and rv is not None and lv > rv
        elif t == TestType.LESS:
            return lv is not None and rv is not None and lv < rv
        elif t == TestType.PREDICATE and jt.predicate is not None:
            return jt.predicate(lv, rv)
        return False

    # ------------------------------------------------------------------
    # Propagation
    # ------------------------------------------------------------------
    def _propagate(self, token: Token, wme: Optional[WME]) -> None:
        new_token = token.extend(wme)
        if self.terminal:
            self.terminal.activate(new_token)
        for child in self.children:
            child.left_activate(new_token)

    def _retract(self, token: Token) -> None:
        # Simplified retraction – full implementation tracks which tokens were propagated
        pass

    # ------------------------------------------------------------------
    # Wiring helpers
    # ------------------------------------------------------------------
    def add_child(self, node: "BetaNode") -> None:
        self.children.append(node)

    def set_terminal(self, t: "TerminalNode") -> None:
        self.terminal = t


# ===========================================================================
# Terminal Node
# ===========================================================================

class TerminalNode:
    """
    End of a rule's Rete sub-network.
    Activated when all conditions of its owner rule are satisfied.
    """

    def __init__(
        self,
        rule_id: str,
        actions: List[Action],
        priority: int = 0,
        salience: int = 0,
    ) -> None:
        self.rule_id = rule_id
        self.actions = actions
        self.priority = priority
        self.salience = salience
        self.activations: List[Token] = []

    def activate(self, token: Token) -> None:
        """Record a complete pattern match."""
        self.activations.append(token)
        logger.info("Rule '%s' activated (token len=%d)", self.rule_id, len(token.wmes))

    def execute(self, engine: "ReteNetwork") -> Dict[str, Any]:
        """Execute all actions in priority order; return a result dict."""
        results = []
        for act in sorted(self.actions, key=lambda a: a.priority, reverse=True):
            res = self._exec_action(act, engine)
            if res:
                results.append(res)
        return {"rule_id": self.rule_id, "action_results": results}

    def _exec_action(self, action: Action, engine: "ReteNetwork") -> Optional[Dict]:
        if action.type == "insert":
            wme = WME(
                fact_type=action.params["fact_type"],
                attributes=action.params.get("attributes", {}),
            )
            engine.assert_fact(wme)
            return {"action": "insert", "fact_type": wme.fact_type, "id": wme.id}

        elif action.type == "retract":
            wme_id = action.params.get("wme_id")
            if wme_id:
                engine.retract_fact(wme_id)
                return {"action": "retract", "wme_id": wme_id}

        elif action.type == "return":
            engine.set_decision(action.params)
            return {"action": "return", "result": action.params.get("result")}

        elif action.type == "call":
            func_name = action.params.get("function")
            handler = engine.action_handlers.get(func_name)
            if handler:
                result = handler(**action.params.get("kwargs", {}))
                return {"action": "call", "function": func_name, "result": result}
            else:
                logger.warning("No handler registered for function: %s", func_name)

        elif action.type == "predict":
            # AI prediction delegated to engine
            return engine.handle_predict_action(action.params)

        return None

    def clear_activations(self) -> None:
        self.activations.clear()
