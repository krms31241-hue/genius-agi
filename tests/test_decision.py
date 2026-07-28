"""Comprehensive tests for Decision Core."""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from decision.decision_engine import DecisionEngine
from decision.candidate_generator import CandidateGenerator
from decision.rule_engine import RuleEngine
from decision.risk_estimator import RiskEstimator
from decision.scorer import Scorer
from decision.evaluator import BenefitEvaluator, AlignmentEvaluator, CostEvaluator
from decision.consensus import ConsensusEngine
from decision.uncertainty import UncertaintyEstimator
from decision.confidence import ConfidenceEstimator
from decision.explanation import ExplanationEngine
from decision.decision_models import Candidate

@pytest.fixture
def engine():
    return DecisionEngine()

@pytest.fixture
def sample_candidate():
    return Candidate(id="c1", action="optimize_db", description="test", metadata={"strategy_type": "standard", "estimated_cost": 40})

def test_candidate_generation(engine):
    cands = engine.generator.generate("fix_bug", {})
    assert len(cands) >= 2
    assert all(hasattr(c, "id") for c in cands)

def test_rule_engine_violations():
    rules = RuleEngine()
    bad = Candidate(id="b1", action="bypass sandbox", description="unsafe", metadata={"bypass_sandbox": True})
    passed, violations = rules.validate(bad, {})
    assert passed is False
    assert "never_bypass_sandbox" in violations

def test_rule_engine_pass():
    rules = RuleEngine()
    good = Candidate(id="g1", action="safe_update", description="safe", metadata={})
    passed, violations = rules.validate(good, {})
    assert passed is True
    assert len(violations) == 0

def test_risk_estimation(sample_candidate):
    est = RiskEstimator()
    risk = est.estimate(sample_candidate, {})
    assert "composite_risk" in risk
    assert 0.0 <= risk["composite_risk"] <= 1.0
    assert risk["failure_probability"] > 0.0

def test_scorer_and_evaluators(sample_candidate):
    scorer = Scorer([BenefitEvaluator(), AlignmentEvaluator(), CostEvaluator()])
    scores = scorer.score_candidate(sample_candidate, {"goal": "optimize_db"})
    assert "benefit" in scores
    assert "alignment" in scores
    assert "cost" in scores
    assert scores["alignment"] == 0.9

def test_consensus_aggregation():
    cons = ConsensusEngine()
    score = cons.aggregate([0.8, 0.7, 0.9])
    assert 0.0 <= score <= 1.0
    low_agreement = cons.aggregate([0.2, 0.9, 0.3])
    assert low_agreement < score

def test_uncertainty_calculation(sample_candidate):
    unc = UncertaintyEstimator()
    val = unc.calculate(sample_candidate, [0.8, 0.7, 0.9], 0.8)
    assert 0.0 <= val <= 1.0

def test_confidence_calculation(sample_candidate):
    conf = ConfidenceEstimator()
    val = conf.calculate(sample_candidate, risk=0.3, uncertainty=0.2, rule_passed=True)
    assert 0.0 <= val <= 1.0
    assert conf.calculate(sample_candidate, 0.3, 0.2, False) == 0.0

def test_explanation_generation(sample_candidate):
    expl = ExplanationEngine()
    reasons = expl.generate(sample_candidate, {"benefit": 0.6}, {"composite_risk": 0.2, "failure_probability": 0.2, "security_impact": 0.1},
                            0.7, 0.2, [], 0.65)
    assert isinstance(reasons, list)
    assert len(reasons) >= 3
    assert any("consensus score" in r for r in reasons)

def test_goal_alignment(engine):
    dec = engine.evaluate("security_patch", {"security_risk": "high"})
    assert dec.decision is not None
    assert dec.score >= 0.0
    assert len(dec.reason) > 0

def test_full_integration(engine):
    dec = engine.evaluate("optimize_performance", {"context": "production"})
    assert dec.decision is not None
    assert len(dec.alternatives) >= 1
    assert 0.0 <= dec.confidence <= 1.0
    assert 0.0 <= dec.uncertainty <= 1.0
    assert 0.0 <= dec.risk <= 1.0
    assert isinstance(dec.reason, list)
    assert all(isinstance(r, str) for r in dec.reason)
