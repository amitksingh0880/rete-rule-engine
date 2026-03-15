"""
Unit tests for ReteNetwork core engine.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

import pytest
from core.memory import WME, WorkingMemory
from core.nodes import (
    AlphaNode, BetaNode, TerminalNode, Token,
    FieldConstraint, JoinTest, TestType, Action
)
from core.network import ReteNetwork


# ===========================================================================
# WME / WorkingMemory tests
# ===========================================================================

class TestWME:
    def test_create_wme(self):
        wme = WME("Applicant", {"score": 750, "age": 30})
        assert wme.fact_type == "Applicant"
        assert wme.get("score") == 750
        assert wme.get("missing", "default") == "default"

    def test_wme_immutable(self):
        wme = WME("Applicant", {"score": 750})
        with pytest.raises(Exception):
            wme.fact_type = "Policy"  # frozen dataclass

    def test_wme_serialization(self):
        wme = WME("Policy", {"premium": 1200.0})
        d = wme.to_dict()
        wme2 = WME.from_dict(d)
        assert wme.id == wme2.id
        assert wme2.get("premium") == 1200.0


class TestWorkingMemory:
    def test_assert_and_retrieve(self):
        wm = WorkingMemory()
        wme = WME("Applicant", {"score": 700})
        wm.assert_fact(wme)
        assert wm.get_fact(wme.id) is wme

    def test_duplicate_raises(self):
        wm = WorkingMemory()
        wme = WME("Applicant", {"score": 700})
        wm.assert_fact(wme)
        with pytest.raises(ValueError):
            wm.assert_fact(wme)

    def test_retract(self):
        wm = WorkingMemory()
        wme = WME("Applicant", {"score": 700})
        wm.assert_fact(wme)
        wm.retract_fact(wme.id)
        assert wm.get_fact(wme.id) is None

    def test_type_index(self):
        wm = WorkingMemory()
        wme1 = WME("Applicant", {"score": 700})
        wme2 = WME("Policy", {"premium": 500})
        wm.assert_fact(wme1)
        wm.assert_fact(wme2)
        assert len(wm.get_facts_by_type("Applicant")) == 1
        assert len(wm.get_facts_by_type("Policy")) == 1
        assert len(wm.get_facts_by_type("Claim")) == 0

    def test_attribute_index(self):
        wm = WorkingMemory()
        wme = WME("Applicant", {"status": "ACTIVE"})
        wm.assert_fact(wme)
        results = wm.get_facts_by_attribute("status", "ACTIVE")
        assert wme in results


# ===========================================================================
# AlphaNode tests
# ===========================================================================

class TestAlphaNode:
    def _make_alpha(self, field, op, value):
        return AlphaNode([FieldConstraint(field, op, value)])

    def test_equality_pass(self):
        alpha = self._make_alpha("score", "==", 750)
        wme = WME("Applicant", {"score": 750})
        assert alpha.test(wme)

    def test_equality_fail(self):
        alpha = self._make_alpha("score", "==", 750)
        wme = WME("Applicant", {"score": 600})
        assert not alpha.test(wme)

    def test_greater_than(self):
        alpha = self._make_alpha("score", ">", 700)
        assert alpha.test(WME("A", {"score": 750}))
        assert not alpha.test(WME("A", {"score": 700}))

    def test_in_operator(self):
        alpha = self._make_alpha("status", "in", ["ACTIVE", "PENDING"])
        assert alpha.test(WME("A", {"status": "ACTIVE"}))
        assert not alpha.test(WME("A", {"status": "CLOSED"}))

    def test_activation_adds_to_memory(self):
        alpha = self._make_alpha("score", ">", 700)
        wme = WME("A", {"score": 800})
        alpha.activate(wme)
        assert wme in alpha.memory


# ===========================================================================
# ReteNetwork end-to-end tests
# ===========================================================================

class TestReteNetwork:
    def _build_approve_rule(self):
        """Simple rule: Applicant with score >= 750 → APPROVED."""
        net = ReteNetwork()
        net.compile_rule(
            rule_id="approve_high_score",
            conditions=[{
                "fact_type": "Applicant",
                "constraints": [{"field": "credit_score", "operator": ">=", "value": 750, "value_is_variable": False}],
                "joins": [],
                "negation": False,
            }],
            actions=[{"type": "return", "params": {"result": "APPROVED"}, "priority": 0}],
            salience=10,
        )
        return net

    def test_rule_compiles(self):
        net = self._build_approve_rule()
        assert "approve_high_score" in net._terminal_nodes

    def test_fact_assertion(self):
        net = self._build_approve_rule()
        wme = WME("Applicant", {"credit_score": 800})
        net.assert_fact(wme)
        assert len(net.working_memory) == 1

    def test_decision_approved(self):
        net = self._build_approve_rule()
        net.assert_fact(WME("Applicant", {"credit_score": 800}))
        result = net.run()
        assert result["decision"] == "APPROVED"

    def test_decision_not_triggered(self):
        net = self._build_approve_rule()
        net.assert_fact(WME("Applicant", {"credit_score": 600}))
        result = net.run()
        assert result["decision"] is None  # No rule fired

    def test_reset_clears_facts(self):
        net = self._build_approve_rule()
        net.assert_fact(WME("Applicant", {"credit_score": 800}))
        net.reset()
        assert len(net.working_memory) == 0

    def test_multiple_rules(self):
        net = ReteNetwork()
        net.compile_rule(
            "approve",
            conditions=[{"fact_type": "Applicant", "constraints": [
                {"field": "credit_score", "operator": ">=", "value": 750, "value_is_variable": False}
            ], "joins": [], "negation": False}],
            actions=[{"type": "return", "params": {"result": "APPROVED"}, "priority": 0}],
            salience=10,
        )
        net.compile_rule(
            "decline",
            conditions=[{"fact_type": "Applicant", "constraints": [
                {"field": "credit_score", "operator": "<", "value": 600, "value_is_variable": False}
            ], "joins": [], "negation": False}],
            actions=[{"type": "return", "params": {"result": "DECLINED"}, "priority": 0}],
            salience=5,
        )
        net.assert_fact(WME("Applicant", {"credit_score": 500}))
        result = net.run()
        assert result["decision"] == "DECLINED"

    def test_describe(self):
        net = self._build_approve_rule()
        desc = net.describe()
        assert desc["rules"] == ["approve_high_score"]
        assert desc["alpha_nodes"] >= 1


# ===========================================================================
# DSL Engine tests
# ===========================================================================

class TestDSLEngine:
    def test_load_and_execute_simple_rule(self):
        from dsl.compiler import DSLRuleEngine

        dsl = """
rule approve_high_score salience 10
when
    Applicant app:
        credit_score >= 750
then
    return "APPROVED" with reason: "high_score"
"""
        engine = DSLRuleEngine()
        rule_ids = engine.load_rules(dsl)
        assert "approve_high_score" in rule_ids

        result = engine.execute([
            {"fact_type": "Applicant", "attributes": {"credit_score": 800}}
        ])
        assert result["decision"] == "APPROVED"

    def test_declined_below_threshold(self):
        from dsl.compiler import DSLRuleEngine

        dsl = """
rule decline_low_score salience 5
when
    Applicant:
        credit_score < 600
then
    return "DECLINED"
"""
        engine = DSLRuleEngine()
        engine.load_rules(dsl)
        result = engine.execute([
            {"fact_type": "Applicant", "attributes": {"credit_score": 500}}
        ])
        assert result["decision"] == "DECLINED"
