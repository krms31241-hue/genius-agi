"""Comprehensive tests for Meta Learning Engine."""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from learning.meta_learning import MetaLearningEngine, StrategyRecord

@pytest.fixture
def engine():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield MetaLearningEngine(data_dir=tmpdir)

def test_strategy_comparison(engine):
    engine.record_execution("s1", "Strategy A", success=True, duration=2.0, confidence=0.8)
    engine.record_execution("s2", "Strategy B", success=False, duration=5.0, confidence=0.4)
    ranked = engine.rank_strategies()
    assert len(ranked) == 2
    assert ranked[0].id == "s1"
    assert ranked[0].composite_score > ranked[1].composite_score

def test_adaptation_and_metrics(engine):
    # Feed pattern: failures first, then successes -> positive adaptation & failure reduction
    for _ in range(5):
        engine.record_execution("adapt1", "Adapting", success=False, duration=3.0, confidence=0.3)
    for _ in range(5):
        engine.record_execution("adapt1", "Adapting", success=True, duration=1.0, confidence=0.9)
        
    rec = engine.strategies["adapt1"]
    assert rec.adaptation_score > 0.0
    assert rec.failure_reduction > 0.0
    assert rec.confidence_improvement > 0.0
    assert rec.efficiency_score > 0.0
    assert rec.composite_score > 0.0

def test_automatic_ranking_and_selection(engine):
    engine.record_execution("low", "Low Perf", success=False, duration=5.0, confidence=0.2)
    engine.record_execution("high", "High Perf", success=True, duration=1.0, confidence=0.9)
    best = engine.select_best_strategy()
    assert best.id == "high"
    assert best.composite_score > engine.strategies["low"].composite_score

def test_persistence(engine):
    engine.record_execution("p1", "Persist", success=True, duration=1.5, confidence=0.7)
    original_score = engine.strategies["p1"].composite_score
    
    eng2 = MetaLearningEngine(data_dir=engine.data_dir)
    assert "p1" in eng2.strategies
    assert eng2.strategies["p1"].successes == 1
    assert eng2.strategies["p1"].composite_score == original_score

def test_integration_hooks(engine):
    class MockSkillLib:
        def search(self, query): return []
    class MockReasoner:
        def predict_effects(self, name): return {"predicted_effects": ["eff1", "eff2"]}

    engine.skill_library = MockSkillLib()
    engine.reasoner = MockReasoner()
    engine.simulator = True
    engine.counterfactual = True
    engine.executive = True

    engine.record_execution("int1", "Integrated", success=True, duration=1.0, confidence=0.8)
    analysis = engine.analyze_with_integrations("int1")
    
    assert analysis["strategy_id"] == "int1"
    assert len(analysis["insights"]) == 5
    assert "related skills" in analysis["insights"][0]
    assert "Causal prediction" in analysis["insights"][1]
    assert "Simulation engine attached" in analysis["insights"][2]
    assert "Counterfactual engine attached" in analysis["insights"][3]
    assert "Executive engine attached" in analysis["insights"][4]

def test_empty_selection(engine):
    assert engine.select_best_strategy() is None
    assert engine.rank_strategies() == []

def test_metadata_tracking(engine):
    engine.record_execution("meta1", "MetaTrack", success=True, duration=1.0, confidence=0.8, metadata={"env": "prod"})
    rec = engine.strategies["meta1"]
    assert rec.metadata.get("env") == "prod"
