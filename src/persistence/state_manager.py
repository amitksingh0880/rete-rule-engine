"""
StateManager – lightweight distributed-state / session manager.

Tracks active inference sessions and accumulates stats.
In production, swap the in-memory backend for Redis.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StateManager:
    """
    Thread-safe in-memory state manager.

    Responsibilities:
      * Track concurrent inference sessions
      * Store ephemeral session context (partial results, mid-saga state)
      * Accumulate runtime statistics
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._stats: Dict[str, Any] = {
            "total_executions": 0,
            "total_decisions": {},
            "errors": 0,
            "uptime_start": time.time(),
        }

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------
    def create_session(self, session_id: str, context: Optional[Dict] = None) -> None:
        with self._lock:
            self._sessions[session_id] = {
                "context": context or {},
                "created_at": time.time(),
                "state": "active",
                "results": [],
            }

    def update_session(self, session_id: str, key: str, value: Any) -> bool:
        with self._lock:
            if session_id not in self._sessions:
                return False
            self._sessions[session_id][key] = value
            return True

    def get_session(self, session_id: str) -> Optional[Dict]:
        with self._lock:
            return dict(self._sessions.get(session_id, {}))

    def close_session(self, session_id: str) -> None:
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]["state"] = "closed"

    def purge_closed_sessions(self) -> int:
        with self._lock:
            before = len(self._sessions)
            self._sessions = {
                sid: s for sid, s in self._sessions.items() if s["state"] != "closed"
            }
            return before - len(self._sessions)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def record_execution(self, decision: Optional[str], error: bool = False) -> None:
        with self._lock:
            self._stats["total_executions"] += 1
            if error:
                self._stats["errors"] += 1
            elif decision:
                d = self._stats["total_decisions"]
                d[decision] = d.get(decision, 0) + 1

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            uptime = round(time.time() - self._stats["uptime_start"], 1)
            return {**self._stats, "uptime_seconds": uptime, "active_sessions": len(self._sessions)}
