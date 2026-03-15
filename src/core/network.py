"""
ReteNetwork – main orchestrator for the Rete algorithm.

Manages:
  * Compilation of declarative rule specs into Alpha/Beta/Terminal nodes.
  * Working-memory mutations and network propagation.
  * The match-resolve-act execution cycle via the Agenda.
  * External action handlers and AI/ML hooks.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from .agenda import Agenda
from .memory import WME, WorkingMemory
from .nodes import (
    Action, AlphaNode, BetaNode, FieldConstraint,
    JoinTest, TerminalNode, TestType, Token,
)

logger = logging.getLogger(__name__)


class ReteNetwork:
    """
    Production-grade Rete network.

    Usage
    -----
    >>> net = ReteNetwork()
    >>> net.compile_rule("approve_high_score", conditions=[...], actions=[...])
    >>> net.assert_fact(WME("Applicant", {"score": 800}))
    >>> result = net.run()
    """

    def __init__(self) -> None:
        self.working_memory = WorkingMemory()
        self.agenda = Agenda()

        # Alpha nodes keyed by their constraint fingerprint (enables node sharing)
        self._alpha_nodes: Dict[Tuple, AlphaNode] = {}

        # Storage for compiled nodes
        self._beta_nodes: List[BetaNode] = []
        self._terminal_nodes: Dict[str, TerminalNode] = {}

        # Registered external handlers
        self.action_handlers: Dict[str, Callable] = {}

        # Predict action handler (set externally by AI layer)
        self._predict_handler: Optional[Callable[[Dict], Dict]] = None

        # Decision state for the current `run()` call
        self._current_decision: Optional[str] = None
        self._decision_data: Dict[str, Any] = {}
        self._action_log: List[Dict] = []
        self._matched_rules: List[str] = []

    # =========================================================================
    # Rule compilation
    # =========================================================================

    def compile_rule(
        self,
        rule_id: str,
        conditions: List[Dict],
        actions: List[Dict],
        priority: int = 0,
        salience: int = 0,
    ) -> TerminalNode:
        """
        Compile a declarative rule specification into the Rete network.

        Parameters
        ----------
        rule_id    : Unique identifier for the rule.
        conditions : List of condition dicts, each containing:
                       - ``fact_type``  str
                       - ``constraints`` list[dict] – see FieldConstraint
                       - ``joins``       list[dict] – see JoinTest
                       - ``negation``    bool       (optional, default False)
        actions    : List of action dicts matching Action dataclass fields.
        priority   : Tie-breaking weight (secondary to salience).
        salience   : Highest-priority conflict-resolution weight.

        Returns
        -------
        The compiled TerminalNode.
        """
        if not conditions:
            raise ValueError(f"Rule '{rule_id}' must have at least one condition.")

        if rule_id in self._terminal_nodes:
            logger.warning("Rule '%s' already compiled – overwriting.", rule_id)
            self._terminal_nodes.pop(rule_id)

        # ------------------------------------------------------------------
        # Build Alpha nodes (with node sharing)
        # ------------------------------------------------------------------
        alpha_nodes: List[AlphaNode] = []
        for cond in conditions:
            alpha = self._get_or_create_alpha(cond)
            alpha_nodes.append(alpha)

        # ------------------------------------------------------------------
        # Build Beta chain
        # ------------------------------------------------------------------
        current_beta: Optional[BetaNode] = None

        for i, (cond, alpha) in enumerate(zip(conditions, alpha_nodes)):
            join_tests = self._build_join_tests(cond.get("joins", []))
            is_not = cond.get("negation", False)
            new_beta = BetaNode(join_tests, is_not_node=is_not)
            self._beta_nodes.append(new_beta)

            alpha.add_child(new_beta)

            if current_beta is not None:
                current_beta.add_child(new_beta)
            else:
                # First condition: bootstrap left memory with an empty token
                new_beta.left_memory.append(Token())

            current_beta = new_beta

        # ------------------------------------------------------------------
        # Terminal node
        # ------------------------------------------------------------------
        action_objs = [Action(**a) for a in actions]
        terminal = TerminalNode(rule_id, action_objs, priority, salience)
        current_beta.set_terminal(terminal)  # type: ignore[union-attr]
        self._terminal_nodes[rule_id] = terminal

        logger.info(
            "Compiled rule '%s' | conditions=%d | actions=%d",
            rule_id, len(conditions), len(actions),
        )
        return terminal

    # =========================================================================
    # Working memory operations
    # =========================================================================

    def assert_fact(self, wme: WME) -> None:
        """Assert a new fact and propagate through the Alpha network."""
        self.working_memory.assert_fact(wme)
        self._propagate_assert(wme)

    def retract_fact(self, wme_id: str) -> Optional[WME]:
        """Retract a fact and propagate the removal through the network."""
        wme = self.working_memory.retract_fact(wme_id)
        if wme:
            for alpha in self._alpha_nodes.values():
                alpha.deactivate(wme)
        return wme

    def update_fact(self, wme: WME) -> None:
        """Retract the old version of a fact and assert the updated version."""
        self.retract_fact(wme.id)
        self.assert_fact(wme)

    def _propagate_assert(self, wme: WME) -> None:
        for alpha in self._alpha_nodes.values():
            alpha.activate(wme)

    # =========================================================================
    # Execution cycle
    # =========================================================================

    def run(self, max_cycles: int = 100) -> Dict[str, Any]:
        """
        Execute the match → resolve → act cycle.

        Returns
        -------
        A dict with keys:
          - ``decision``      str | None
          - ``data``          dict – extra decision metadata
          - ``matched_rules`` list[str]
          - ``actions``       list[dict]
          - ``cycles``        int
          - ``latency_ms``    float
        """
        start = time.perf_counter()
        self._current_decision = None
        self._decision_data = {}
        self._action_log = []
        self._matched_rules = []

        # Rebuild agenda from current terminal activations
        self.agenda.rebuild(self._terminal_nodes)

        cycles = 0
        for cycles in range(1, max_cycles + 1):
            result = self.agenda.execute_next(self)
            if result is None:
                break  # Agenda exhausted
            self._action_log.append(result)
            self._matched_rules.append(result["rule_id"])
            if self._current_decision:
                break   # Halt on explicit decision

        latency_ms = (time.perf_counter() - start) * 1000

        return {
            "decision": self._current_decision,
            "data": self._decision_data,
            "matched_rules": self._matched_rules,
            "actions": self._action_log,
            "cycles": cycles,
            "latency_ms": round(latency_ms, 3),
        }

    # =========================================================================
    # Action helpers (called from TerminalNode._exec_action)
    # =========================================================================

    def set_decision(self, params: Dict[str, Any]) -> None:
        """Called by 'return' actions to record the final decision."""
        self._current_decision = params.get("result", "UNKNOWN")
        self._decision_data.update(params)

    def handle_predict_action(self, params: Dict) -> Optional[Dict]:
        """Delegate ML prediction to the registered predict handler."""
        if self._predict_handler:
            try:
                return self._predict_handler(params)
            except Exception as exc:
                logger.error("Predict action failed: %s", exc)
        else:
            logger.warning("No predict handler registered.")
        return None

    def register_action_handler(self, name: str, handler: Callable) -> None:
        self.action_handlers[name] = handler

    def register_predict_handler(self, handler: Callable[[Dict], Dict]) -> None:
        self._predict_handler = handler

    # =========================================================================
    # State management
    # =========================================================================

    def reset(self) -> None:
        """Clear all facts and activation state (keep compiled rules)."""
        self.working_memory.clear()
        self.agenda.clear()
        for terminal in self._terminal_nodes.values():
            terminal.clear_activations()
        # Also reset left memory for bootstrap beta nodes (first in chain)
        for beta in self._beta_nodes:
            beta.left_memory.clear()
            beta.right_memory.clear()
            # Re-bootstrap first-in-chain betas
        self._bootstrap_beta_nodes()
        self._current_decision = None
        self._decision_data = {}

    def _bootstrap_beta_nodes(self) -> None:
        """Re-add empty tokens to beta nodes that are first in a chain."""
        # Nodes without alpha parents on their *left* input need bootstrap
        # Heuristic: beta nodes that have no left children pointing to them
        all_children: set = set()
        for b in self._beta_nodes:
            for c in b.children:
                all_children.add(id(c))
        for b in self._beta_nodes:
            if id(b) not in all_children:
                b.left_memory.append(Token())

    # =========================================================================
    # Compilation helpers
    # =========================================================================

    def _get_or_create_alpha(self, condition: Dict) -> AlphaNode:
        raw = condition.get("constraints", [])
        constraints = [
            FieldConstraint(**c) if isinstance(c, dict) else c for c in raw
        ]
        key = tuple(
            (c.field, c.operator, str(c.value), c.value_is_variable)
            for c in constraints
        )
        if key in self._alpha_nodes:
            node = self._alpha_nodes[key]
            node.shared = True
            return node
        node = AlphaNode(constraints)
        self._alpha_nodes[key] = node
        return node

    def _build_join_tests(self, joins: List[Dict]) -> List[JoinTest]:
        tests: List[JoinTest] = []
        for j in joins:
            try:
                t = TestType(j.get("type", "equal"))
            except ValueError:
                t = TestType.EQUAL
            tests.append(
                JoinTest(
                    type=t,
                    left_field=j["left_field"],
                    right_field=j["right_field"],
                    left_wme_index=j.get("left_index", -1),
                )
            )
        return tests

    # =========================================================================
    # Introspection
    # =========================================================================

    @property
    def rule_count(self) -> int:
        return len(self._terminal_nodes)

    @property
    def fact_count(self) -> int:
        return len(self.working_memory)

    def describe(self) -> Dict[str, Any]:
        """Return a summary of the current network state."""
        return {
            "rules": list(self._terminal_nodes.keys()),
            "alpha_nodes": len(self._alpha_nodes),
            "beta_nodes": len(self._beta_nodes),
            "facts": self.fact_count,
        }
