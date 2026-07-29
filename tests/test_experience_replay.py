"""Comprehensive tests for Experience Replay Engine."""
import os
import sys
import time
import random
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from learning.experience import Experience
from learning.replay_buffer import ReplayBuffer
from learning.replay_scheduler import ReplayScheduler

@pytest.fixture
def buffer():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield ReplayBuffer(capacity=10, data_dir=tmpdir)

@pytest.fixture
def scheduler(buffer):
    return ReplayScheduler(buffer, default_strategy="prioritized")

def test_store_experience(buffer):
    exp = Experience(episode_id="ep1", action="move", success=True, priority=0.8)
    assert buffer.store(exp) is True
    assert exp.id in buffer.experiences
    assert buffer.metrics.total_stored == 1
    assert buffer.metrics.episodes_tracked == 1

def test_replay_ordering(buffer):
    random.seed(42)
    exps = [
        Experience(episode_id="ep1", action="a1", priority=0.5, timestamp=time.time() - 3600),
        Experience(episode_id="ep1", action="a2", priority=0.9, timestamp=time.time()),
        Experience(episode_id="ep1", action="a3", priority=0.7, timestamp=time.time() - 1800)
    ]
    for e in exps: buffer.store(e)
    
    sampled = buffer.sample_prioritized(3, decay_factor=0.99)
    assert len(sampled) == 3
    # a2 (0.9, fresh) > a3 (0.7, 0.5h old) > a1 (0.5, 1h old)
    assert sampled[0].action == "a2"
    assert sampled[1].action == "a3"
    assert sampled[2].action == "a1"

def test_prioritization_and_decay(buffer):
    old_high = Experience(action="old_high", priority=1.0, timestamp=time.time() - 7200) # 2h old
    new_low = Experience(action="new_low", priority=0.6, timestamp=time.time())
    buffer.store(old_high)
    buffer.store(new_low)
    
    # With decay 0.9 per hour: old_high -> 1.0 * 0.9^2 = 0.81. new_low -> 0.6
    sampled = buffer.sample_prioritized(2, decay_factor=0.9)
    assert sampled[0].action == "old_high"
    assert sampled[1].action == "new_low"

def test_compression(buffer):
    # Capacity is 10. Fill it.
    for i in range(10):
        buffer.store(Experience(action=f"step_{i}", priority=float(i)/10.0))
    assert len(buffer.experiences) == 10
    
    # Store one more -> triggers compression (keeps top 5)
    buffer.store(Experience(action="step_10", priority=1.0))
    assert len(buffer.experiences) == 5
    # Should keep highest priorities: 1.0, 0.9, 0.8, 0.7, 0.6
    kept_priorities = {e.priority for e in buffer.experiences.values()}
    assert 1.0 in kept_priorities
    assert 0.4 not in kept_priorities
    assert buffer.metrics.compression_ratio < 1.0

def test_persistence(buffer):
    exp = Experience(episode_id="ep_persist", action="save_test", priority=0.9)
    buffer.store(exp)
    
    buf2 = ReplayBuffer(capacity=10, data_dir=buffer.data_dir)
    assert exp.id in buf2.experiences
    assert buf2.metrics.total_stored == 1
    assert buf2.get_episode("ep_persist")[0].action == "save_test"

def test_statistics_tracking(buffer, scheduler):
    exps = [
        Experience(action="s1", success=True, priority=0.8),
        Experience(action="s2", success=False, priority=0.5),
        Experience(action="s3", success=True, priority=0.9)
    ]
    for e in exps: buffer.store(e)
    
    scheduler.schedule_replay(2, strategy="success")
    stats = scheduler.get_statistics()
    assert stats["total_stored"] == 3
    assert stats["total_replayed"] == 2
    assert stats["success_replays"] == 2
    assert stats["failure_replays"] == 0
    assert stats["avg_priority"] > 0.0

def test_filtering_success_failure(buffer):
    random.seed(10)
    buffer.store(Experience(action="ok1", success=True))
    buffer.store(Experience(action="ok2", success=True))
    buffer.store(Experience(action="fail1", success=False))
    
    successes = buffer.sample_success(5)
    assert all(e.success for e in successes)
    assert len(successes) == 2
    
    failures = buffer.sample_failure(5)
    assert all(not e.success for e in failures)
    assert len(failures) == 1

def test_episode_grouping(buffer):
    buffer.store(Experience(episode_id="epA", action="a1"))
    buffer.store(Experience(episode_id="epA", action="a2"))
    buffer.store(Experience(episode_id="epB", action="b1"))
    
    ep_a = buffer.get_episode("epA")
    assert len(ep_a) == 2
    actions = {e.action for e in ep_a}
    assert actions == {"a1", "a2"}
    assert len(buffer.get_episode("epB")) == 1
    assert len(buffer.get_episode("epC")) == 0
