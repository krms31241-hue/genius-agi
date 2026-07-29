"""Comprehensive tests for Transfer Learning Engine."""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from learning.skill import Skill
from learning.skill_library import SkillLibrary
from learning.transfer_learning import TransferLearningEngine

@pytest.fixture
def library():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield SkillLibrary(data_dir=tmpdir)

@pytest.fixture
def engine(library):
    with tempfile.TemporaryDirectory() as tmpdir:
        eng = TransferLearningEngine(skill_library=library, data_dir=tmpdir)
        eng.register_domain("robotics", "Robotics", ["motion", "sensors", "control", "physics"])
        eng.register_domain("simulation", "Simulation", ["physics", "rendering", "control", "virtual"])
        eng.register_domain("cooking", "Cooking", ["heat", "ingredients", "timing"])
        
        lib_skill = Skill(id="nav1", name="Navigate", category="robotics", confidence=0.9, tags=["motion"])
        library.add_skill(lib_skill)
        yield eng

def test_domain_similarity(engine):
    sim_rs = engine.compute_similarity("robotics", "simulation")
    # intersection: physics, control (2). union: motion, sensors, control, physics, rendering, virtual (6). 2/6 = 0.3333
    assert abs(sim_rs - 0.3333) < 0.001
    
    sim_rc = engine.compute_similarity("robotics", "cooking")
    assert sim_rc == 0.0

def test_suggest_transfers(engine):
    suggestions = engine.suggest_transfers("robotics", "simulation", min_similarity=0.2)
    assert len(suggestions) == 1
    assert suggestions[0]["skill_id"] == "nav1"
    assert suggestions[0]["similarity"] > 0.3
    
    # Low similarity threshold blocks transfer
    suggestions_cook = engine.suggest_transfers("robotics", "cooking", min_similarity=0.1)
    assert len(suggestions_cook) == 0

def test_transfer_skill(engine, library):
    adapted = engine.transfer_skill("nav1", "simulation", adaptation_factor=1.0)
    assert adapted is not None
    assert adapted.category == "simulation"
    assert "transferred_from_robotics" in adapted.tags
    assert adapted.confidence < 0.9
    assert library.get_skill(adapted.id) is not None

def test_transfer_confidence_scaling(engine):
    adapted = engine.transfer_skill("nav1", "simulation", adaptation_factor=0.5)
    # conf = 0.9 * 0.3333 * 0.5 ≈ 0.15
    assert abs(adapted.confidence - 0.15) < 0.01

def test_record_outcome_and_metrics(engine):
    adapted = engine.transfer_skill("nav1", "simulation")
    record_id = engine.transfers[-1].id
    
    engine.record_transfer_outcome(record_id, success=True)
    metrics = engine.get_cross_domain_metrics()
    assert metrics["total_transfers"] == 1
    assert metrics["success_rate"] == 1.0
    assert metrics["avg_similarity"] > 0.3

def test_persistence(library):
    with tempfile.TemporaryDirectory() as tmpdir:
        eng1 = TransferLearningEngine(skill_library=library, data_dir=tmpdir)
        eng1.register_domain("d1", "D1", ["a", "b"])
        eng1.register_domain("d2", "D2", ["a", "c"])
        
        eng2 = TransferLearningEngine(skill_library=library, data_dir=tmpdir)
        assert "d1" in eng2.domains
        # Note: Jaccard similarity for {a,b} & {a,c} is 1/3 ≈ 0.3333. 
        # Assertion adjusted to match mathematical reality of Jaccard metric used in production.
        assert abs(eng2.compute_similarity("d1", "d2") - 0.3333) < 0.001

def test_knowledge_reuse_and_adaptation(engine):
    # Verify metadata carries over correctly
    adapted = engine.transfer_skill("nav1", "simulation")
    assert adapted.metadata["source_skill_id"] == "nav1"
    assert adapted.metadata["source_domain"] == "robotics"
    assert adapted.dependencies == []
    assert adapted.execution_count == 0
