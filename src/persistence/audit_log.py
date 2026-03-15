"""
AuditLogger – immutable decision audit trail (SQLite default, extensible to PostgreSQL).

Financial regulations (ECOA, GDPR, SOX) mandate 7-year retention of decision records.
All writes are append-only; no update or delete methods are exposed.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS decision_log (
    id           TEXT PRIMARY KEY,
    request_id   TEXT NOT NULL,
    decision     TEXT,
    matched_rules TEXT,
    facts        TEXT,
    violations   TEXT,
    latency_ms   REAL,
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_request_id ON decision_log(request_id);
CREATE INDEX IF NOT EXISTS idx_created_at ON decision_log(created_at);
CREATE INDEX IF NOT EXISTS idx_decision   ON decision_log(decision);
"""


class AuditLogger:
    """
    Append-only audit logger.

    Writes one row per ``log_decision()`` call.
    Designed to work out-of-the-box with SQLite; swap backend by overriding
    ``_write()``.
    """

    def __init__(self, db_url: str = "sqlite:///./data/audit.db") -> None:
        self._db_url = db_url
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db(db_url)

    def _init_db(self, url: str) -> None:
        # Only SQLite supported natively; other backends can be plugged in later
        db_path = url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._conn.executescript(_DDL)
            self._conn.commit()
            logger.info("AuditLogger initialised at %s", db_path)
        except Exception as exc:
            logger.warning("AuditLogger DB init failed (%s) – using in-memory fallback.", exc)
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._conn.executescript(_DDL)
            self._conn.commit()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def log_decision(
        self,
        request_id: str,
        facts: List[Dict],
        result: Dict[str, Any],
        violations: Optional[List[Dict]] = None,
        latency_ms: float = 0.0,
    ) -> str:
        """
        Persist a single decision record.  Returns the generated row ID.
        This method is safe to call from a background asyncio task.
        """
        row_id = uuid.uuid4().hex
        row = (
            row_id,
            request_id,
            result.get("decision"),
            json.dumps(result.get("matched_rules", [])),
            json.dumps(facts),
            json.dumps(violations or []),
            latency_ms,
            datetime.utcnow().isoformat(),
        )
        try:
            assert self._conn
            self._conn.execute(
                "INSERT INTO decision_log VALUES (?,?,?,?,?,?,?,?)", row
            )
            self._conn.commit()
        except Exception as exc:
            logger.error("AuditLogger write failed: %s", exc)
        return row_id

    # ------------------------------------------------------------------
    # Read (compliance queries)
    # ------------------------------------------------------------------
    def search(
        self,
        decision: Optional[str] = None,
        from_dt: Optional[str] = None,
        to_dt: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Search audit records (read-only)."""
        assert self._conn
        clauses, params = [], []
        if decision:
            clauses.append("decision = ?")
            params.append(decision)
        if from_dt:
            clauses.append("created_at >= ?")
            params.append(from_dt)
        if to_dt:
            clauses.append("created_at <= ?")
            params.append(to_dt)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"SELECT id, request_id, decision, matched_rules, latency_ms, created_at "
            f"FROM decision_log {where} ORDER BY created_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()

        return [
            {
                "id": r[0],
                "request_id": r[1],
                "decision": r[2],
                "matched_rules": json.loads(r[3]),
                "latency_ms": r[4],
                "created_at": r[5],
            }
            for r in rows
        ]

    def count(self) -> int:
        assert self._conn
        return self._conn.execute("SELECT COUNT(*) FROM decision_log").fetchone()[0]
