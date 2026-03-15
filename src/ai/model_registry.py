"""
Model Registry – ONNX model versioning, hot-swap, and A/B testing.

When ONNX Runtime is not installed the registry falls back to a callable-based
*mock* model, so the rest of the system can be tested without ML dependencies.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import ONNX Runtime; fall back gracefully
try:
    import numpy as np
    import onnxruntime as ort
    _ONNX_AVAILABLE = True
except ImportError:
    _ONNX_AVAILABLE = False
    logger.warning("onnxruntime not installed – ModelRegistry will use mock models only.")


# ===========================================================================
# Metadata
# ===========================================================================

@dataclass
class ModelVersion:
    version: int
    model_name: str
    features: List[str]
    output_name: str = "output"
    checksum: str = ""
    created_at: str = ""
    is_active: bool = False
    traffic_percentage: float = 100.0
    performance_metrics: Dict[str, float] = field(default_factory=dict)


# ===========================================================================
# ModelRegistry
# ===========================================================================

class ModelRegistry:
    """
    Central registry for ML models.

    * Supports real ONNX models (when onnxruntime is installed).
    * Falls back to Python callable mocks for testing / demo.
    * Provides version management and simple A/B routing.
    """

    def __init__(self, registry_path: str = "./models") -> None:
        self._path = Path(registry_path)
        self._path.mkdir(parents=True, exist_ok=True)

        # model_name -> version -> session/callable
        self._sessions: Dict[str, Dict[int, Any]] = {}
        self._metadata: Dict[str, Dict[int, ModelVersion]] = {}

        if _ONNX_AVAILABLE:
            self._scan_registry()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register_model(
        self,
        model_name: str,
        model_path: str,
        features: List[str],
        description: str = "",
    ) -> int:
        """Register a new model version from an ONNX file."""
        if not _ONNX_AVAILABLE:
            raise RuntimeError("onnxruntime not installed; use register_mock_model() instead.")

        existing = self._metadata.get(model_name, {})
        next_ver = max(existing.keys(), default=0) + 1

        model_dir = self._path / model_name
        model_dir.mkdir(exist_ok=True)
        dest = model_dir / f"{model_name}@{next_ver}.onnx"
        shutil.copy(model_path, dest)

        self._load_onnx(model_name, next_ver, dest, features)
        return next_ver

    def register_mock_model(
        self,
        model_name: str,
        predict_fn: Callable[[List[float]], float],
        features: List[str],
        version: Optional[int] = None,
    ) -> int:
        """Register a Python callable as a model (for testing / demos)."""
        existing = self._metadata.get(model_name, {})
        ver = version or (max(existing.keys(), default=0) + 1)

        self._sessions.setdefault(model_name, {})[ver] = predict_fn
        self._metadata.setdefault(model_name, {})[ver] = ModelVersion(
            version=ver,
            model_name=model_name,
            features=features,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            is_active=True,
        )
        logger.info("Registered mock model '%s'@v%d", model_name, ver)
        return ver

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------
    def predict(
        self,
        model_name: str,
        features: List[float],
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run inference.  Returns dict with prediction, confidence, latency_ms.
        """
        start = time.perf_counter()
        session, meta = self._resolve(model_name, version)

        if session is None:
            raise ValueError(f"Model '{model_name}' not found.")

        # Callable mock
        if callable(session) and not _ONNX_AVAILABLE:
            prediction = session(features)
            confidence = None
        elif callable(session):
            prediction = session(features)
            confidence = None
        else:
            # ONNX Session
            input_name = session.get_inputs()[0].name
            import numpy as np  # type: ignore
            arr = np.array(features, dtype=np.float32).reshape(1, -1)
            outputs = session.run(None, {input_name: arr})
            prediction = float(outputs[0][0])
            confidence = float(outputs[1][0]) if len(outputs) > 1 else None

        latency = (time.perf_counter() - start) * 1000
        return {
            "prediction": float(prediction),
            "confidence": confidence,
            "model_name": model_name,
            "model_version": meta.version if meta else version,
            "latency_ms": round(latency, 3),
        }

    # ------------------------------------------------------------------
    # Version management
    # ------------------------------------------------------------------
    def set_active_version(self, model_name: str, version: int) -> None:
        if model_name not in self._metadata:
            raise ValueError(f"Unknown model: {model_name}")
        for v, meta in self._metadata[model_name].items():
            meta.is_active = v == version
        logger.info("Set '%s' active version → v%d", model_name, version)

    def list_versions(self, model_name: str) -> List[Dict]:
        metas = self._metadata.get(model_name, {})
        return [
            {
                "version": m.version,
                "is_active": m.is_active,
                "features": m.features,
                "created_at": m.created_at,
            }
            for m in metas.values()
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve(self, model_name: str, version: Optional[int]):
        versions = self._sessions.get(model_name, {})
        metas = self._metadata.get(model_name, {})
        if not versions:
            return None, None

        if version is not None:
            return versions.get(version), metas.get(version)

        # Latest active, or just highest
        active = [v for v, m in metas.items() if m.is_active]
        chosen = max(active) if active else max(versions.keys())
        return versions[chosen], metas.get(chosen)

    def _load_onnx(
        self, model_name: str, version: int, path: Path, features: List[str]
    ) -> None:
        if not _ONNX_AVAILABLE:
            return
        session = ort.InferenceSession(
            str(path), providers=["CPUExecutionProvider"]
        )
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        self._sessions.setdefault(model_name, {})[version] = session
        self._metadata.setdefault(model_name, {})[version] = ModelVersion(
            version=version,
            model_name=model_name,
            features=features,
            checksum=checksum,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            is_active=True,
        )
        logger.info("Loaded ONNX model '%s'@v%d", model_name, version)

    def _scan_registry(self) -> None:
        for model_dir in self._path.iterdir():
            if not model_dir.is_dir():
                continue
            for onnx_file in model_dir.glob("*.onnx"):
                try:
                    # filename pattern: <name>@<version>.onnx
                    stem = onnx_file.stem
                    name, _, ver_str = stem.rpartition("@")
                    if not name:
                        name = stem
                    version = int(ver_str) if ver_str.isdigit() else 1
                    # Load feature list from companion JSON if present
                    meta_file = onnx_file.with_suffix(".json")
                    features = []
                    if meta_file.exists():
                        features = json.loads(meta_file.read_text()).get("features", [])
                    self._load_onnx(name, version, onnx_file, features)
                except Exception as exc:
                    logger.warning("Could not load %s: %s", onnx_file, exc)
