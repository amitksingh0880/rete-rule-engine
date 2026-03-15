"""
InferenceEngine – bridges DSL predict actions with the ModelRegistry.

This layer is registered as the ``predict_handler`` on ReteNetwork so that
predict actions in rule DSL are seamlessly executed.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .feature_store import FeatureStore
from .model_registry import ModelRegistry
from .guardrails import GuardrailManager, GuardrailViolation

logger = logging.getLogger(__name__)


class InferenceEngine:
    """
    Orchestrates ML inference for rule actions.

    Integrates:
      * ``ModelRegistry``   – model retrieval and execution
      * ``FeatureStore``    – feature retrieval (entity-based)
      * ``GuardrailManager`` – safety checks on predictions

    Usage
    -----
    Attach to a ReteNetwork so that 'predict' actions in rules invoke this engine:

    >>> engine = InferenceEngine(registry, store)
    >>> rete_network.register_predict_handler(engine.handle_predict)
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        feature_store: Optional[FeatureStore] = None,
        guardrails: Optional[GuardrailManager] = None,
    ) -> None:
        self.registry = registry or ModelRegistry()
        self.feature_store = feature_store or FeatureStore()
        self.guardrails = guardrails or GuardrailManager()
        self._prediction_log: List[Dict] = []

    # ------------------------------------------------------------------
    # Handler (registered on ReteNetwork)
    # ------------------------------------------------------------------
    def handle_predict(self, params: Dict) -> Dict[str, Any]:
        """
        Called by TerminalNode when a 'predict' action fires.

        ``params`` keys:
          - ``model``    : str   – model name
          - ``version``  : int | None
          - ``features`` : dict  – name → value (raw feature values)
          - ``entity_id``: str | None – for feature-store lookup
          - ``store_as`` : str | None – variable name for result
        """
        model_name = params.get("model", "")
        version = params.get("version")
        feature_map: Dict[str, Any] = params.get("features", {})
        entity_id: Optional[str] = params.get("entity_id")

        # Resolve feature vector
        if entity_id:
            # Merge feature store values with inline overrides
            feature_names = list(feature_map.keys())
            store_features = self.feature_store.get_online_features(entity_id, feature_names)
            merged = {**store_features, **{k: v for k, v in feature_map.items() if v is not None}}
            feature_vector = [float(merged.get(n, 0.0)) for n in feature_names]
        else:
            # Use inline values directly
            feature_vector = [float(v or 0.0) for v in feature_map.values()]

        # Run inference
        try:
            result = self.registry.predict(model_name, feature_vector, version)
        except Exception as exc:
            logger.error("Inference failed for model '%s': %s", model_name, exc)
            result = {"prediction": None, "error": str(exc)}

        # Guardrail check
        violations = self.guardrails.evaluate(
            context={"entity_id": entity_id, "feature_map": feature_map},
            decision=result,
            rule_id=f"predict:{model_name}",
        )
        result["guardrail_violations"] = [v.to_dict() for v in violations]

        # Log
        self._prediction_log.append({**result, "model": model_name, "params": params})
        return result

    # ------------------------------------------------------------------
    # Batch inference (for offline / training)
    # ------------------------------------------------------------------
    def batch_predict(
        self,
        model_name: str,
        records: List[Dict[str, Any]],
        feature_names: List[str],
        version: Optional[int] = None,
    ) -> List[Dict]:
        results = []
        for record in records:
            vec = [float(record.get(f, 0.0)) for f in feature_names]
            try:
                res = self.registry.predict(model_name, vec, version)
            except Exception as exc:
                res = {"prediction": None, "error": str(exc)}
            results.append(res)
        return results

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------
    def get_prediction_log(self) -> List[Dict]:
        return list(self._prediction_log)
