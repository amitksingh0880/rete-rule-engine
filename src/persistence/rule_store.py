"""
RuleStore – versioned, persistent rule storage.

Stores rule DSL source alongside metadata so rules survive server restarts
and can be rolled back.
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
CREATE TABLE IF NOT EXISTS rules (
    id          TEXT PRIMARY KEY,
    rule_id     TEXT NOT NULL,
    version     INTEGER NOT NULL,
    dsl_source  TEXT NOT NULL,
    metadata    TEXT,
    is_active   INTEGER DEFAULT 1,
    created_at  TEXT NOT NULL,
    UNIQUE(rule_id, version)
);
CREATE INDEX IF NOT EXISTS idx_rule_id   ON rules(rule_id);
CREATE INDEX IF NOT EXISTS idx_is_active ON rules(is_active);
"""


class RuleStore:
    """Versioned rule persistence (SQLite default)."""

    def __init__(self, db_url: str = "sqlite:///./data/rules.db") -> None:
        db_path = db_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
        except Exception:
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._conn.executescript(_DDL)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def save_rule(
        self,
        rule_id: str,
        dsl_source: str,
        metadata: Optional[Dict] = None,
    ) -> int:
        """
        Persist a rule version.  Increments version automatically.
        Returns the new version number.
        """
        cur_version = self._latest_version(rule_id)
        next_version = cur_version + 1

        # Deactivate previous versions
        self._conn.execute(
            "UPDATE rules SET is_active=0 WHERE rule_id=?", (rule_id,)
        )
        self._conn.execute(
            "INSERT INTO rules VALUES (?,?,?,?,?,?,?)",
            (
                uuid.uuid4().hex,
                rule_id,
                next_version,
                dsl_source,
                json.dumps(metadata or {}),
                1,
                datetime.utcnow().isoformat(),
            ),
        )
        self._conn.commit()
        logger.info("Saved rule '%s' as version %d", rule_id, next_version)
        return next_version

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    def get_rule(self, rule_id: str, version: Optional[int] = None) -> Optional[Dict]:
        if version is None:
            row = self._conn.execute(
                "SELECT * FROM rules WHERE rule_id=? AND is_active=1 ORDER BY version DESC LIMIT 1",
                (rule_id,),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM rules WHERE rule_id=? AND version=?",
                (rule_id, version),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_rules(self, active_only: bool = True) -> List[Dict]:
        q = "SELECT * FROM rules"
        if active_only:
            q += " WHERE is_active=1"
        q += " ORDER BY rule_id, version DESC"
        rows = self._conn.execute(q).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_versions(self, rule_id: str) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT * FROM rules WHERE rule_id=? ORDER BY version DESC", (rule_id,)
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------
    def rollback(self, rule_id: str, target_version: int) -> bool:
        row = self._conn.execute(
            "SELECT id FROM rules WHERE rule_id=? AND version=?",
            (rule_id, target_version),
        ).fetchone()
        if not row:
            return False
        self._conn.execute("UPDATE rules SET is_active=0 WHERE rule_id=?", (rule_id,))
        self._conn.execute(
            "UPDATE rules SET is_active=1 WHERE rule_id=? AND version=?",
            (rule_id, target_version),
        )
        self._conn.commit()
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _latest_version(self, rule_id: str) -> int:
        row = self._conn.execute(
            "SELECT MAX(version) FROM rules WHERE rule_id=?", (rule_id,)
        ).fetchone()
        return (row[0] or 0) if row else 0

    @staticmethod
    def _row_to_dict(row) -> Dict:
        return {
            "id": row[0], "rule_id": row[1], "version": row[2],
            "dsl_source": row[3], "metadata": json.loads(row[4]),
            "is_active": bool(row[5]), "created_at": row[6],
        }
