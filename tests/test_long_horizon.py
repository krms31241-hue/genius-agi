"""Comprehensive tests for Long Horizon Planning."""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.long_horizon_planner import LongHorizonPlanner
from executive.goal_tree import NodeType, NodeStatus

@pytest.fixture
def planner():
    return LongHorizonPlanner()

def test_hierarchy_generation(planner):
    res = planner.decompose_mission("m1", "Expand Market", ["research", "launch"])
    assert res["mission_id"] == "m1"
    assert len(res["campaigns"]) == 2
    assert res["tree_nodes"] > 10
    hierarchy = planner.get_hierarchy()
    assert len(hierarchy) == 1
    assert hierarchy[0]["type"] == "mission"
    assert len(hierarchy[0]["children"]) == 2

def test_dependency_graph(planner):
    planner.decompose_mission("m2", "Tech Upgrade", ["backend", "frontend"])
    graph = planner.tree.build_dependency_graph()
    assert isinstance(graph, dict)
    assert planner.tree.detect_cycles() is False
    order = planner.get_execution_plan()
    assert len(order) == len(planner.tree.nodes)
    for nid, node in planner.tree.nodes.items():
        for dep in node.dependencies:
            if dep in order and nid in order:
                assert order.index(dep) < order.index(nid)

def test_priority_updates(planner):
    planner.decompose_mission("m3", "Priority Test", ["obj1"])
    initial_priorities = {nid: n.priority for nid, n in planner.tree.nodes.items()}
    planner.update_priorities({"urgency_multiplier": 2.0})
    for nid, n in planner.tree.nodes.items():
        if n.status == NodeStatus.PENDING:
            assert n.priority >= initial_priorities[nid]
        assert n.updated_at > 0

def test_completion_propagation(planner):
    planner.decompose_mission("m4", "Completion Test", ["phase1"])
    actions = [nid for nid, n in planner.tree.nodes.items() if n.node_type == NodeType.ACTION]
    assert len(actions) > 0
    leaf = actions[0]
    propagated = planner.mark_completed(leaf)
    assert leaf in propagated
    for nid in propagated:
        assert planner.tree.nodes[nid].status == NodeStatus.COMPLETED
        assert planner.tree.nodes[nid].progress == 1.0

def test_dynamic_updates_and_merge(planner):
    planner.decompose_mission("m5", "Merge Test", ["alpha"])
    goals = [nid for nid, n in planner.tree.nodes.items() if n.node_type == NodeType.GOAL]
    if len(goals) >= 2:
        g1, g2 = goals[0], goals[1]
        merged_id = "merged_goal"
        assert planner.merge_goals([g1, g2], merged_id, "Combined Goal") is True
        assert merged_id in planner.tree.nodes
        assert g1 not in planner.tree.nodes
        assert g2 not in planner.tree.nodes
        assert planner.tree.nodes[merged_id].title == "Combined Goal"
        assert planner.tree.detect_cycles() is False
