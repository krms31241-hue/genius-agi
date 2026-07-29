"""Executive Engine: Full autonomous planning pipeline with strategic layer integration."""
import time
import logging
from typing import Dict, Any, List, Optional
from .goal_generator import GoalGenerator
from .goal_priority import GoalPriorityEngine
from .goal_decomposer import GoalDecomposer
from .planner import Planner
from .task_graph import TaskGraph
from .scheduler import Scheduler
from .progress_tracker import ProgressTracker
from .execution_monitor import ExecutionMonitor
from .replanner import Replanner
from .goal import GoalManager
from .mission import MissionManager, Mission, MissionStatus
from .strategic_planner import StrategicPlanner
from .resource_manager import ResourceManager
from .adaptive_scheduler import AdaptiveScheduler
from .executive_metrics import ExecutiveMetrics
from .meta_executive import MetaExecutive
from .dashboard import ExecutiveDashboard
from .executive_models import Goal, GoalStatus, ExecutionMetrics

logger = logging.getLogger(__name__)

class ExecutiveEngine:
    """Orchestrates tactical and strategic executive pipelines."""
    def __init__(self, data_dir: str = "executive_data"):
        self.data_dir = data_dir
        self.goal_mgr = GoalManager(data_dir=data_dir)
        self.mission_mgr = MissionManager(data_dir=data_dir)
        self.generator = GoalGenerator()
        self.prioritizer = GoalPriorityEngine()
        self.decomposer = GoalDecomposer()
        self.planner = Planner()
        self.strategic_planner = StrategicPlanner()
        self.tracker = ProgressTracker()
        self.replanner = Replanner()
        self.resource_mgr = ResourceManager(data_dir=data_dir)
        self.metrics = ExecutiveMetrics(data_dir=data_dir)
        self.meta = MetaExecutive(self.metrics)
        self.graph: Optional[TaskGraph] = None
        self.scheduler: Optional[Scheduler] = None
        self.adaptive_scheduler: Optional[AdaptiveScheduler] = None
        self.monitor: Optional[ExecutionMonitor] = None
        self.dashboard = ExecutiveDashboard(self.mission_mgr, self.goal_mgr, self.tracker, self.resource_mgr, self.metrics)

    def run_pipeline(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Original tactical pipeline. Preserved for backward compatibility."""
        context = context or {}
        logger.info("Executive pipeline started")
        raw_goals = self.generator.generate(context)
        for g in raw_goals: self.goal_mgr.add_goal(g)
        prioritized = self.prioritizer.score_goals(raw_goals)
        all_goals = []
        for g in prioritized:
            all_goals.extend(self.decomposer.decompose(g))
            self.goal_mgr.transition_status(g, GoalStatus.PLANNED)
        plan_nodes = self.planner.create_plan(all_goals)
        self.graph = TaskGraph()
        for n in plan_nodes: self.graph.add_node(n)
        if not self.graph.validate_deps(): return {"status": "failed", "reason": "Invalid dependencies"}
        if self.graph.detect_cycle(): return {"status": "failed", "reason": "Cyclic dependencies detected"}
        priorities = {n.metadata.get("goal_id", n.id): g.priority for g in all_goals for n in plan_nodes if n.metadata.get("goal_id") == g.id}
        self.scheduler = Scheduler(self.graph, priorities)
        scheduled = self.scheduler.schedule()
        self.tracker.init_tasks(scheduled)
        self.monitor = ExecutionMonitor(self.graph, self.tracker.states)
        for g in all_goals:
            if g.metadata.get("atomic"): self.goal_mgr.transition_status(g, GoalStatus.SCHEDULED)
        logger.info("Executive pipeline completed successfully")
        return {"status": "success", "goals_generated": len(raw_goals), "tasks_scheduled": len(scheduled), "graph_valid": True, "progress": self.tracker.get_progress(), "timestamp": time.time()}

    def run_strategic_pipeline(self, mission: Mission, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Strategic pipeline: Mission -> Strategic Goals -> Adaptive Schedule -> Monitor -> Meta Analysis."""
        context = context or {}
        logger.info("Strategic pipeline started for mission %s", mission.id)
        self.mission_mgr.create_mission(mission)
        self.mission_mgr.transition_status(mission, MissionStatus.ACTIVE)

        strat_goals = self.strategic_planner.decompose_mission(mission)
        strat_goals = self.strategic_planner.reprioritize(strat_goals, context)
        for g in strat_goals: self.goal_mgr.add_goal(g)

        plan_nodes = self.planner.create_plan(strat_goals)
        self.graph = TaskGraph()
        for n in plan_nodes: self.graph.add_node(n)
        if not self.graph.validate_deps(): return {"status": "failed", "reason": "Invalid strategic dependencies"}

        priorities = {n.metadata.get("goal_id", n.id): g.priority for g in strat_goals for n in plan_nodes if n.metadata.get("goal_id") == g.id}
        self.adaptive_scheduler = AdaptiveScheduler(self.graph, self.resource_mgr, priorities)
        scheduled = self.adaptive_scheduler.schedule()

        self.tracker.init_tasks(scheduled)
        self.monitor = ExecutionMonitor(self.graph, self.tracker.states)
        self.metrics.record_planning(len(strat_goals))
        self.metrics.update_mission(completed=0, failed=0)

        meta_proposals = self.meta.analyze(self.graph)
        logger.info("Strategic pipeline completed. Scheduled %d tasks.", len(scheduled))
        return {
            "status": "success", "mission_id": mission.id, "strategic_goals": len(strat_goals),
            "tasks_scheduled": len(scheduled), "meta_proposals": meta_proposals,
            "dashboard": self.dashboard.generate_summary(), "timestamp": time.time()
        }

    def monitor_execution(self) -> ExecutionMetrics:
        if not self.monitor: return ExecutionMetrics()
        return self.monitor.analyze()

    def handle_failure(self, failed_task_id: str) -> Dict[str, Any]:
        if not self.graph: return {"status": "no_graph"}
        self.tracker.update(failed_task_id, GoalStatus.FAILED, error="Execution failure")
        if self.adaptive_scheduler:
            self.adaptive_scheduler.handle_failure(failed_task_id)
        new_graph = self.replanner.replan(self.graph, self.tracker.states, [failed_task_id])
        self.graph = new_graph
        self.adaptive_scheduler = AdaptiveScheduler(self.graph, self.resource_mgr, {})
        new_schedule = self.adaptive_scheduler.schedule()
        self.tracker.init_tasks(new_schedule)
        self.monitor = ExecutionMonitor(self.graph, self.tracker.states)
        self.metrics.record_recovery(success=True)
        return {"status": "replanned", "new_tasks": len(new_schedule)}
