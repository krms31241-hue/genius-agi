"""Comprehensive tests for Skill Learning Engine."""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from learning.skill import Skill
from learning.skill_library import SkillLibrary
from learning.skill_extractor import SkillExtractor

@pytest.fixture
def library():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield SkillLibrary(data_dir=tmpdir)

def test_skill_creation():
    s = Skill(name="deploy", category="ops", tags=["ci", "cd"])
    assert s.id is not None
    assert s.status == "active"
    assert s.confidence == 0.5
    d = s.to_dict()
    restored = Skill.from_dict(d)
    assert restored.name == "deploy"
    assert restored.tags == ["ci", "cd"]

def test_duplicate_prevention(library):
    s1 = Skill(name="build", description="compile code", category="dev")
    assert library.add_skill(s1) is True
    s2 = Skill(name="build", description="compile code", category="dev")
    assert library.add_skill(s2) is False

def test_persistence(library):
    s = Skill(name="persist_test", category="test")
    library.add_skill(s)
    lib2 = SkillLibrary(data_dir=library.data_dir)
    loaded = lib2.get_skill(s.id)
    assert loaded is not None
    assert loaded.name == "persist_test"
    assert loaded.status == "active"

def test_versioning(library):
    s1 = Skill(name="api_call", version="1.0.0", description="v1 impl")
    library.add_skill(s1)
    s2 = Skill(name="api_call", version="2.0.0", description="v2 impl")
    assert library.add_skill(s2) is True
    assert len(library.search(query="api_call")) == 2

def test_dependency_graph(library):
    base = Skill(name="auth", id="base1")
    dep = Skill(name="login", id="dep1", dependencies=["base1"])
    library.add_skill(base)
    library.add_skill(dep)
    assert library.registry.get_dependencies("dep1") == ["base1"]
    assert library.registry.get_dependents("base1") == ["dep1"]
    issues = library.registry.validate_dependencies()
    assert len(issues) == 0

def test_confidence_and_metrics_updates(library):
    s = Skill(name="metric_test", id="m1")
    library.add_skill(s)
    library.record_execution("m1", success=True, duration=2.0)
    library.record_execution("m1", success=True, duration=3.0)
    library.record_execution("m1", success=False, duration=5.0)
    updated = library.get_skill("m1")
    assert updated.execution_count == 3
    assert abs(updated.success_rate - (2/3)) < 0.01
    assert updated.average_duration == pytest.approx(3.333, abs=0.1)
    assert updated.confidence > 0.5

def test_retirement(library):
    s = Skill(name="old_skill", id="old1")
    library.add_skill(s)
    assert library.retire_skill("old1", reason="obsolete") is True
    retired = library.get_skill("old1")
    assert retired.status == "retired"
    assert retired.metadata["retirement_reason"] == "obsolete"
    assert len(library.search(query="old_skill")) == 0

def test_extractor_learning(library):
    extractor = SkillExtractor(library, min_success_rate=0.8, min_executions=2)
    exec_data = {
        "success": True,
        "action": "optimize_db",
        "description": "Run vacuum and analyze",
        "category": "db",
        "tags": ["maintenance"],
        "duration": 1.5
    }
    skill = extractor.extract_from_execution(exec_data)
    assert skill is not None
    assert skill.name == "optimize_db"
    assert skill.category == "db"
    assert extractor.extract_from_execution(exec_data) is None

def test_extractor_promotion(library):
    extractor = SkillExtractor(library, min_success_rate=0.8, min_executions=2)
    s = Skill(name="promote_test", id="p1")
    library.add_skill(s)
    library.record_execution("p1", True, 1.0)
    library.record_execution("p1", True, 1.0)
    assert extractor.promote_to_stable("p1") is True
    assert library.get_skill("p1").metadata.get("promoted") is True
    assert library.get_skill("p1").confidence > 0.6

def test_search_by_capability_and_tags(library):
    library.add_skill(Skill(name="deploy_prod", category="ops", tags=["aws", "prod"]))
    library.add_skill(Skill(name="deploy_staging", category="ops", tags=["aws", "staging"]))
    library.add_skill(Skill(name="test_unit", category="dev", tags=["pytest"]))
    
    ops_skills = library.search(category="ops")
    assert len(ops_skills) == 2
    
    aws_prod = library.search(tags=["aws", "prod"])
    assert len(aws_prod) == 1
    assert aws_prod[0].name == "deploy_prod"
    
    deploy_query = library.search(query="deploy")
    assert len(deploy_query) == 2
