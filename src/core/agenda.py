"""
Agenda module – conflict resolution and ordered activation execution.

The Agenda collects all pending rule activations and selects the next
one to fire based on a multi-criteria priority strategy.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set, Tuple, TYPE_CHECKING

from .nodes import TerminalNode, Token

if TYPE_CHECKING:
    from .network import ReteNetwork

logger = logging.getLogger(__name__)


class Activation:
    """A single pending rule event (terminal node + matching token)."""

    __slots__ = ("terminal", "token", "score")

    def __init__(self, terminal: TerminalNode, token: Token) -> None:
        self.terminal = terminal
        self.token = token
        self.score: float = 0.0


class Agenda:
    """
    Conflict-resolution queue for rule activations.

    Priority strategy (highest wins):
      1. ``salience``  – user-declared priority (highest weight)
      2. ``priority``  – secondary user priority
      3. ``specificity`` – more conditions = more specific
      4. ``recency``   – prefer recently asserted facts
    """

    def __init__(self) -> None:
        self._activations: List[Activation] = []
        self._fired_in_cycle: Set[str] = set()

    # ------------------------------------------------------------------
    # Population
    # ------------------------------------------------------------------
    def add(self, terminal: TerminalNode, token: Token) -> None:
        act = Activation(terminal, token)
        act.score = self._score(act)
        self._activations.append(act)

    def rebuild(self, terminals: Dict[str, TerminalNode]) -> None:
        """(Re)build agenda from all current terminal activations."""
        self._activations.clear()
        for terminal in terminals.values():
            for token in terminal.activations:
                self.add(terminal, token)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def execute_next(self, engine: "ReteNetwork") -> Optional[Dict]:
        """
        Fire the highest-priority activation that hasn't been fired yet
        in this cycle and whose facts are still in working memory.

        Returns the result dict from TerminalNode.execute(), or None when
        the agenda is exhausted.
        """
        ordered = sorted(self._activations, key=lambda a: a.score, reverse=True)

        for act in ordered:
            rule_id = act.terminal.rule_id
            if rule_id in self._fired_in_cycle:
                continue
            if not self._still_valid(act, engine):
                continue

            # Fire!
            result = act.terminal.execute(engine)
            self._fired_in_cycle.add(rule_id)
            self._activations.remove(act)
            logger.debug("Fired rule '%s' (score=%.1f)", rule_id, act.score)
            return result

        return None

    def execute_all(self, engine: "ReteNetwork", max_cycles: int = 100) -> List[Dict]:
        """Execute every pending activation respecting conflict resolution."""
        results = []
        for _ in range(max_cycles):
            result = self.execute_next(engine)
            if result is None:
                break
            results.append(result)
        return results

    def clear(self) -> None:
        self._activations.clear()
        self._fired_in_cycle.clear()

    def __len__(self) -> int:
        return len(self._activations)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _score(self, act: Activation) -> float:
        t = act.token
        recency = 0.0
        if t.wmes:
            last = t.wmes[-1]
            if last is not None:
                recency = last.timestamp.timestamp()
        return (
            act.terminal.salience * 10_000
            + act.terminal.priority * 100
            + len(t.wmes) * 10        # specificity
            + recency * 0.001         # recency (tiny weight)
        )

    def _still_valid(self, act: Activation, engine: "ReteNetwork") -> bool:
        """Return True if all WMEs in the token still exist in working memory."""
        for wme in act.token.wmes:
            if wme is not None and engine.working_memory.get_fact(wme.id) is None:
                return False
        return True
