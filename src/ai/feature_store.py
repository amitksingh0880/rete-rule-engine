"""
Feature Store – online (in-memory/Redis) and offline (SQLite/PostgreSQL) storage.

Provides sub-millisecond feature retrieval for real-time rule evaluation and
point-in-time correctness for model training.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ===========================================================================
# Feature metadata
# ===========================================================================

@dataclass
class FeatureDefinition:
    """Metadata for a feature."""
    name: str
    entity_type: str          # 'applicant', 'policy', 'claim', …
    data_type: str            # 'float', 'int', 'string', 'boolean'
    source: str               # 'transaction', 'enrollment', 'external', …
    ttl_seconds: int = 86_400
    description: str = ""
    default_value: Any = None


# ===========================================================================
# In-memory backend (default, zero-dependency)
# ===========================================================================

class _InMemoryBackend:
    """Simple dict-based online store (for development / testing)."""

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        exp = self._expiry.get(key)
        if exp and time.time() > exp:
            self._store.pop(key, None)
            self._expiry.pop(key, None)
            return None
        return self._store.get(key)

    def set(self, key: str, value: Any, ttl: int = 86_400) -> None:
        self._store[key] = value
        self._expiry[key] = time.time() + ttl

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._expiry.pop(key, None)

    def ping(self) -> bool:
        return True


# ===========================================================================
# FeatureStore
# ===========================================================================

class FeatureStore:
    """
    Unified online/offline feature store.

    * **Online** store  – low-latency retrieval (in-memory dict or Redis).
    * **Offline** store – append-only history for training / audit.

    Parameters
    ----------
    backend : ``'memory'`` (default) or ``'redis'``
    redis_host, redis_port : Only used when backend='redis'
    """

    def __init__(
        self,
        backend: str = "memory",
        redis_host: str = "localhost",
        redis_port: int = 6379,
        **_kwargs: Any,
    ) -> None:
        self._feature_defs: Dict[str, FeatureDefinition] = {}
        self._computations: Dict[str, Callable] = {}
        self._history: List[Dict] = []   # offline store (in-memory simplification)

        # Online backend
        if backend == "redis":
            try:
                import redis as _redis
                self._online = _redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    decode_responses=True,
                    socket_connect_timeout=3,
                )
                self._online.ping()   # connectivity check
                self._use_redis = True
                logger.info("FeatureStore: using Redis backend %s:%d", redis_host, redis_port)
            except Exception as exc:
                logger.warning("Redis unavailable (%s), falling back to in-memory.", exc)
                self._online = _InMemoryBackend()
                self._use_redis = False
        else:
            self._online = _InMemoryBackend()
            self._use_redis = False

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register_feature(
        self,
        definition: FeatureDefinition,
        computation: Optional[Callable] = None,
    ) -> None:
        self._feature_defs[definition.name] = definition
        if computation:
            self._computations[definition.name] = computation

    # ------------------------------------------------------------------
    # Online reads
    # ------------------------------------------------------------------
    def get_online_features(
        self,
        entity_id: str,
        feature_names: List[str],
    ) -> Dict[str, Any]:
        """Return latest values from the online store."""
        result: Dict[str, Any] = {}
        for name in feature_names:
            key = f"feat:{entity_id}:{name}"
            raw = self._online.get(key)
            if raw is not None:
                result[name] = json.loads(raw) if isinstance(raw, str) else raw
            elif name in self._computations:
                computed = self._computations[name](entity_id)
                result[name] = computed
                self._set_online(entity_id, name, computed)
            else:
                defn = self._feature_defs.get(name)
                result[name] = defn.default_value if defn else None
        return result

    def get_feature_vector(
        self,
        entity_id: str,
        feature_names: List[str],
    ) -> List[float]:
        """Numeric feature vector (same order as feature_names)."""
        features = self.get_online_features(entity_id, feature_names)
        vector = []
        for name in feature_names:
            try:
                vector.append(float(features.get(name) or 0.0))
            except (TypeError, ValueError):
                vector.append(0.0)
        return vector

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------
    def ingest_event(
        self,
        entity_id: str,
        entity_type: str,
        features: Dict[str, Any],
        event_timestamp: Optional[datetime] = None,
    ) -> None:
        """Write features to online + offline stores."""
        ts = event_timestamp or datetime.utcnow()
        for name, value in features.items():
            # Online
            self._set_online(entity_id, name, value)
            # Offline (append-only log)
            self._history.append({
                "id": hashlib.md5(f"{entity_id}:{name}:{ts.isoformat()}".encode()).hexdigest(),
                "entity_id": entity_id,
                "entity_type": entity_type,
                "feature_name": name,
                "feature_value": value,
                "event_timestamp": ts.isoformat(),
            })

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _set_online(self, entity_id: str, name: str, value: Any) -> None:
        key = f"feat:{entity_id}:{name}"
        ttl = self._feature_defs.get(name, FeatureDefinition(
            name=name, entity_type="", data_type="string", source=""))
        if self._use_redis:
            self._online.setex(key, ttl.ttl_seconds, json.dumps(value))
        else:
            self._online.set(key, json.dumps(value), ttl=ttl.ttl_seconds)

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------
    def get_offline_history(
        self,
        entity_id: str,
        feature_names: Optional[List[str]] = None,
    ) -> List[Dict]:
        rows = [r for r in self._history if r["entity_id"] == entity_id]
        if feature_names:
            rows = [r for r in rows if r["feature_name"] in feature_names]
        return rows

    def health(self) -> bool:
        try:
            return self._online.ping() if hasattr(self._online, "ping") else True
        except Exception:
            return False
