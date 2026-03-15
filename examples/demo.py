"""
Quick-start demo: run rules against sample applicant facts.

Usage:
    python examples/demo.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from dsl.compiler import DSLRuleEngine
from ai.model_registry import ModelRegistry
from ai.feature_store import FeatureStore
from ai.guardrails import GuardrailManager
from ai.inference import InferenceEngine


def main():
    print("=" * 60)
    print("  Finance Rule Engine – Demo")
    print("=" * 60)

    # ---------------------------------------------------------------
    # 1. Setup
    # ---------------------------------------------------------------
    model_registry = ModelRegistry(registry_path="./models")
    feature_store = FeatureStore(backend="memory")
    guardrails = GuardrailManager(enabled=True, confidence_threshold=0.6)
    inference = InferenceEngine(model_registry, feature_store, guardrails)

    engine = DSLRuleEngine()
    engine.network.register_predict_handler(inference.handle_predict)

    # ---------------------------------------------------------------
    # 2. Register a mock ML model (risk scorer)
    # ---------------------------------------------------------------
    def simple_risk_model(features):
        # Mock: higher score → lower risk
        credit_score = features[0] if features else 700
        return max(0.0, min(1.0, (850 - credit_score) / 250))

    model_registry.register_mock_model(
        model_name="RiskScorer",
        predict_fn=simple_risk_model,
        features=["credit_score"],
    )

    # ---------------------------------------------------------------
    # 3. Load rules from the example file
    # ---------------------------------------------------------------
    rules_path = os.path.join(os.path.dirname(__file__), "credit_underwriting.frl")
    print(f"\nLoading rules from: {rules_path}")
    rule_ids = engine.load_rules_from_file(rules_path)
    print(f"Compiled rules: {rule_ids}\n")

    # ---------------------------------------------------------------
    # 4. Test cases
    # ---------------------------------------------------------------
    test_cases = [
        {"name": "Prime Applicant",      "attrs": {"credit_score": 800, "annual_income": 80000, "debt_to_income_ratio": 0.25}},
        {"name": "Near-Prime Applicant", "attrs": {"credit_score": 700, "annual_income": 40000, "debt_to_income_ratio": 0.40}},
        {"name": "Borderline Applicant", "attrs": {"credit_score": 645, "annual_income": 35000, "debt_to_income_ratio": 0.50}},
        {"name": "Poor Credit",          "attrs": {"credit_score": 550, "annual_income": 30000, "debt_to_income_ratio": 0.60}},
        {"name": "Fraud Flag",           "attrs": {"credit_score": 750, "annual_income": 80000, "fraud_flag": True}},
        {"name": "Recent Bankruptcy",    "attrs": {"credit_score": 720, "annual_income": 60000, "bankruptcy_years_ago": 3}},
    ]

    for tc in test_cases:
        result = engine.execute([
            {"fact_type": "Applicant", "attributes": tc["attrs"]}
        ])
        decision = result.get("decision", "NO_MATCH")
        rules_fired = result.get("matched_rules", [])
        latency = result.get("latency_ms", 0)
        print(f"  {tc['name']:<25} → {decision:<12}  rules={rules_fired}  ({latency:.2f}ms)")

    print("\nDemo complete!")


if __name__ == "__main__":
    main()
