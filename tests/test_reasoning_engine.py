"""Comprehensive tests for Causal Reasoning Engine."""
import os
import sys
import time
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.reasoning.reasoning_engine import ReasoningEngine
from executive.reasoning.causal_graph import CausalGraph
from executive.reasoning.reasoning_models import CausalRelation, CausalType

@pytest.fixture
def engine():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield ReasoningEngine(data_dir=tmpdir)

@pytest.fixture
def populated_engine(engine):
    # A -> B -> C -> D
    # A -> E
    # F -> B
    engine.register_relation("A", "B", CausalType.CAUSES, 0.9, "Direct link")
    engine.register_relation("B", "C", CausalType.CAUSES, 0.8, "Dependency")
    engine.register_relation("C", "D", CausalType.CAUSES, 0.7, "Cascade")
    engine.register_relation("A", "E", CausalType.ENABLES, 0.6, "Side effect")
    engine.register_relation("F", "B", CausalType.CAUSES, 0.85, "Alt root")
    return engine

def test_causal_chain_creation(populated_engine):
    chains = populated_engine.builder.trace_back("D")
    assert len(chains) >= 1
    # Should find A->B->C->D and F->B->C->D
    roots = {c.root_cause_id for c in chains}
    assert "A" in roots
    assert "F" in roots

def test_indirect_inference(populated_engine):
    res = populated_engine.explain_why("D")
    assert len(res.causes) > 0
    assert res.causes[0]["cause_id"] in ("A", "F")
    assert res.confidence > 0.0

def test_multiple_causes(populated_engine):
    causes = populated_engine.root_analyzer.analyze(["D", "E"])
    # A causes both D (via chain) and E directly. Should rank high.
    top_cause = causes[0]["cause_id"]
    assert top_cause == "A"

def test_root_cause_ranking(populated_engine):
    ranked = populated_engine.root_analyzer.analyze(["D"])
    assert len(ranked) == 2 # A and F
    assert ranked[0]["score"] >= ranked[1]["score"]

def test_effect_prediction(populated_engine):
    pred = populated_engine.predict_effects("A")
    assert len(pred.effects) >= 3 # B, C, D, E
    ids = [e["entity_id"] for e in pred.effects]
    assert "B" in ids
    assert "C" in ids
    assert "D" in ids
    assert "E" in ids

def test_confidence_propagation(populated_engine):
    # A->B (0.9) -> C (0.8) -> D (0.7) => 0.9*0.8*0.7 = 0.504
    chains = populated_engine.builder.trace_back("D")
    a_chain = next(c for c in chains if c.root_cause_id == "A")
    assert abs(a_chain.confidence - 0.504) < 0.001

def test_explanation_generation(populated_engine):
    res = populated_engine.explain_why("C")
    assert "caused by" in res.explanation.lower() or "predecessors" in res.explanation.lower()
    assert len(res.explanation) > 10

def test_loop_detection():
    graph = CausalGraph()
    graph.add_relation(CausalRelation(cause_id="X", effect_id="Y", relation_type=CausalType.CAUSES))
    graph.add_relation(CausalRelation(cause_id="Y", effect_id="Z", relation_type=CausalType.CAUSES))
    graph.add_relation(CausalRelation(cause_id="Z", effect_id="X", relation_type=CausalType.CAUSES))
    cycles = graph.detect_cycles()
    assert len(cycles) == 1
    assert set(cycles[0]) == {"X", "Y", "Z", "X"}

def test_serialization_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        eng1 = ReasoningEngine(data_dir=tmpdir)
        eng1.register_relation("P", "Q", CausalType.CAUSES, 0.95)
        eng1._save_state()
        
        eng2 = ReasoningEngine(data_dir=tmpdir)
        assert "Q" in eng2.graph.adj.get("P", [])
        res = eng2.explain_why("Q")
        assert len(res.causes) == 1
        assert res.causes[0]["cause_id"] == "P"

def test_world_model_integration():
    """Verify reasoning engine can reference external entity IDs safely."""
    with tempfile.TemporaryDirectory() as tmpdir:
        eng = ReasoningEngine(data_dir=tmpdir)
        # Simulate world model entities
        entities = {"server_1", "db_1", "cache_1"}
        eng.register_relation("server_1", "db_1", CausalType.DEPENDS_ON, 0.9)
        eng.register_relation("db_1", "cache_1", CausalType.CAUSES, 0.8)
        
        validation = eng.validate_integrity(valid_ids=entities)
        assert validation["is_valid"] is True
        assert validation["dangling_references"] == 0
        
        # Introduce dangling ref
        eng.register_relation("db_1", "missing_svc", CausalType.CAUSES, 0.5)
        validation2 = eng.validate_integrity(valid_ids=entities)
        assert validation2["is_valid"] is False
        assert validation2["dangling_references"] == 1
