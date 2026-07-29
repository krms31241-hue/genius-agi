"""Comprehensive tests for Capability Discovery Engine."""
import os
import sys
import json
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from learning.skill import Skill
from learning.skill_library import SkillLibrary
from learning.replay_buffer import ReplayBuffer
from learning.meta_learning import MetaLearningEngine
from learning.curriculum import CurriculumEngine, CurriculumTask
from learning.transfer_learning import TransferLearningEngine
from learning.capability_discovery import CapabilityDiscoveryEngine

@pytest.fixture
def integration_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        lib = SkillLibrary(data_dir=os.path.join(tmpdir, "lib"))
        lib.add_skill(Skill(id="s1", name="navigate", category="robotics", confidence=0.9, success_rate=0.8, execution_count=5))
        lib.add_skill(Skill(id="s2", name="grasp", category="robotics", confidence=0.4, success_rate=0.3, execution_count=2))
        
        replay = ReplayBuffer(capacity=100, data_dir=os.path.join(tmpdir, "replay"))
        replay.metrics.success_replays = 10
        replay.metrics.failure_replays = 2
        
        meta = MetaLearningEngine(data_dir=os.path.join(tmpdir, "meta"))
        meta.record_execution("strat1", "Aggressive", success=True, duration=1.0, confidence=0.8)
        
        curr = CurriculumEngine(data_dir=os.path.join(tmpdir, "curr"))
        t1 = CurriculumTask(id="c1", name="basics", status="mastered", success_rate=1.0, attempts=5)
        curr.add_task(t1)
        
        transfer = TransferLearningEngine(skill_library=lib, data_dir=os.path.join(tmpdir, "transfer"))
        transfer.register_domain("robotics", "Robotics", ["motion", "control"])
        transfer.register_domain("sim", "Simulation", ["motion", "virtual"])
        
        yield {
            "tmpdir": tmpdir,
            "lib": lib, "replay": replay, "meta": meta,
            "curr": curr, "transfer": transfer
        }

def test_capability_scanning(integration_env):
    env = integration_env
    engine = CapabilityDiscoveryEngine(
        data_dir=env["tmpdir"],
        skill_library=env["lib"], meta_learning=env["meta"],
        curriculum=env["curr"], transfer_learning=env["transfer"]
    )
    caps = engine.scan_capabilities()
    assert len(caps) >= 4
    assert any(c.cap_type == "skill" for c in caps.values())
    assert any(c.cap_type == "strategy" for c in caps.values())
    assert any(c.cap_type == "curriculum" for c in caps.values())

def test_gap_detection(integration_env):
    env = integration_env
    engine = CapabilityDiscoveryEngine(data_dir=env["tmpdir"], skill_library=env["lib"])
    engine.scan_capabilities()
    gaps = engine.detect_gaps(["navigate", "grasp", "fly", "swim"])
    assert set(gaps) == {"fly", "swim"}

def test_graph_building(integration_env):
    env = integration_env
    engine = CapabilityDiscoveryEngine(data_dir=env["tmpdir"], curriculum=env["curr"])
    engine.scan_capabilities()
    graph = engine.build_capability_graph()
    assert isinstance(graph, dict)

def test_capability_scoring(integration_env):
    env = integration_env
    engine = CapabilityDiscoveryEngine(data_dir=env["tmpdir"], skill_library=env["lib"])
    engine.scan_capabilities()
    scores = engine.score_capabilities()
    assert scores["s1"] > scores["s2"]
    assert all(0.0 <= s <= 1.0 for s in scores.values())

def test_coverage_analysis(integration_env):
    env = integration_env
    engine = CapabilityDiscoveryEngine(data_dir=env["tmpdir"], skill_library=env["lib"])
    engine.scan_capabilities()
    coverage = engine.analyze_coverage(["navigate", "grasp", "fly"])
    assert coverage["total_required"] == 3
    assert coverage["covered"] == 2
    assert coverage["missing"] == 1
    assert abs(coverage["coverage_percentage"] - 66.67) < 0.1

def test_growth_recommendations(integration_env):
    env = integration_env
    engine = CapabilityDiscoveryEngine(
        data_dir=env["tmpdir"],
        skill_library=env["lib"], replay_buffer=env["replay"],
        curriculum=env["curr"], transfer_learning=env["transfer"]
    )
    engine.scan_capabilities()
    recs = engine.recommend_growth(["navigate", "grasp", "fly"])
    assert len(recs) >= 1
    fly_rec = next(r for r in recs if r.get("target") == "fly")
    assert fly_rec["type"] == "acquisition"
    assert "cross-domain transfer" in fly_rec.get("suggestion", "")

def test_report_generation_and_persistence(integration_env):
    env = integration_env
    report_path = os.path.join(env["tmpdir"], "learning_report.json")
    engine = CapabilityDiscoveryEngine(
        data_dir=env["tmpdir"],
        skill_library=env["lib"], meta_learning=env["meta"],
        curriculum=env["curr"], transfer_learning=env["transfer"],
        replay_buffer=env["replay"]
    )
    report = engine.generate_report(["navigate", "grasp", "fly"], path=report_path)
    
    assert os.path.exists(report_path)
    with open(report_path, 'r') as f:
        saved = json.load(f)
    assert saved["capabilities_discovered"] >= 4
    assert "coverage_analysis" in saved
    assert "recommendations" in saved
    assert saved["system_integration"]["skill_library"] is True
    assert report == saved

def test_empty_adapter_graceful_handling():
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = CapabilityDiscoveryEngine(data_dir=tmpdir)
        caps = engine.scan_capabilities()
        assert len(caps) == 0
        gaps = engine.detect_gaps(["a", "b"])
        assert gaps == ["a", "b"]
        coverage = engine.analyze_coverage(["a", "b"])
        assert coverage["coverage_percentage"] == 0.0
        recs = engine.recommend_growth(["a"])
        assert len(recs) == 1
        assert recs[0]["type"] == "acquisition"
