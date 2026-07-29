"""Comprehensive tests for Curriculum Learning Engine."""
import os
import sys
import time
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from learning.curriculum import CurriculumEngine, CurriculumTask

@pytest.fixture
def engine():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield CurriculumEngine(data_dir=tmpdir)

def test_difficulty_estimation(engine):
    base = CurriculumTask(id="t1", name="Basic", base_difficulty=1.0)
    adv = CurriculumTask(id="t2", name="Advanced", base_difficulty=2.0, prerequisites=["t1"])
    engine.add_task(base)
    engine.add_task(adv)
    
    assert engine.estimate_difficulty("t1") == 1.0
    # Depth 1 -> 2.0 * (1 + 0.2) = 2.4
    assert engine.estimate_difficulty("t2") == 2.4

def test_prerequisites_and_ordering(engine):
    t1 = CurriculumTask(id="A", name="A", base_difficulty=1.0)
    t2 = CurriculumTask(id="B", name="B", base_difficulty=1.5, prerequisites=["A"])
    t3 = CurriculumTask(id="C", name="C", base_difficulty=2.0, prerequisites=["B"])
    engine.add_task(t1)
    engine.add_task(t2)
    engine.add_task(t3)
    
    path = engine.generate_curriculum("C")
    assert path == ["A", "B", "C"]

def test_automatic_curriculum_generation(engine):
    # Diamond dependency: D depends on B,C. B,C depend on A.
    a = CurriculumTask(id="A", name="A", base_difficulty=1.0)
    b = CurriculumTask(id="B", name="B", base_difficulty=1.2, prerequisites=["A"])
    c = CurriculumTask(id="C", name="C", base_difficulty=1.1, prerequisites=["A"])
    d = CurriculumTask(id="D", name="D", base_difficulty=2.0, prerequisites=["B", "C"])
    for t in [a,b,c,d]: engine.add_task(t)
    
    path = engine.generate_curriculum("D")
    assert path[0] == "A"
    assert path.index("B") < path.index("D")
    assert path.index("C") < path.index("D")
    assert len(path) == 4

def test_mastery_tracking(engine):
    t = CurriculumTask(id="m1", name="MasteryTest", mastery_threshold=0.8, min_attempts=3)
    engine.add_task(t)
    engine.path = ["m1"]
    
    engine.record_attempt("m1", True)
    engine.record_attempt("m1", True)
    assert engine.tasks["m1"].status == "active" # Not enough attempts
    
    engine.record_attempt("m1", True)
    assert engine.tasks["m1"].status == "mastered"
    assert engine.tasks["m1"].success_rate == 1.0

def test_retry_scheduling(engine):
    t = CurriculumTask(id="r1", name="RetryTest")
    engine.add_task(t)
    engine.path = ["r1"]
    
    before = time.time()
    engine.record_attempt("r1", False)
    after = time.time()
    
    task = engine.tasks["r1"]
    assert task.status == "active"
    assert task.next_retry > before
    # Exponential backoff: 60 * 2^0 = 60s
    assert abs(task.next_retry - (before + 60)) < 2.0

def test_curriculum_optimization(engine):
    t1 = CurriculumTask(id="o1", name="Step1")
    t2 = CurriculumTask(id="o2", name="Step2", prerequisites=["o1"])
    t3 = CurriculumTask(id="o3", name="Step3", prerequisites=["o2"])
    for t in [t1,t2,t3]: engine.add_task(t)
    
    engine.generate_curriculum("o3")
    assert len(engine.path) == 3
    
    # Master first step
    engine.tasks["o1"].status = "mastered"
    engine.optimize()
    
    # Path should now start from o2
    assert engine.path[0] == "o2"
    assert "o1" not in engine.path

def test_learning_path_generation(engine):
    t1 = CurriculumTask(id="p1", name="Path1")
    t2 = CurriculumTask(id="p2", name="Path2")
    engine.add_task(t1)
    engine.add_task(t2)
    engine.path = ["p1", "p2"]
    
    path_data = engine.get_learning_path()
    assert len(path_data) == 2
    assert path_data[0]["name"] == "Path1"
    assert path_data[1]["name"] == "Path2"

def test_persistence(engine):
    t = CurriculumTask(id="pers1", name="Persist", base_difficulty=1.5)
    engine.add_task(t)
    engine.generate_curriculum("pers1")
    
    eng2 = CurriculumEngine(data_dir=engine.data_dir)
    assert "pers1" in eng2.tasks
    assert eng2.path == ["pers1"]
    assert eng2.tasks["pers1"].base_difficulty == 1.5

def test_get_next_task_logic(engine):
    t1 = CurriculumTask(id="n1", name="Next1")
    t2 = CurriculumTask(id="n2", name="Next2", prerequisites=["n1"])
    engine.add_task(t1)
    engine.add_task(t2)
    engine.generate_curriculum("n2")
    
    # Prereq not mastered -> returns n1
    nxt = engine.get_next_task()
    assert nxt.id == "n1"
    
    # Master n1
    engine.tasks["n1"].status = "mastered"
    nxt2 = engine.get_next_task()
    assert nxt2.id == "n2"
