"""Executive Intelligence Core - Autonomous Planning & Strategic Layer."""
__version__ = "2.0.0"
from .executive_engine import ExecutiveEngine
from .executive_models import Goal, GoalStatus, PlanNode, ExecutionMetrics
from .mission import Mission, MissionStatus, MissionManager
from .strategic_planner import StrategicPlanner
from .resource_manager import ResourceManager
from .adaptive_scheduler import AdaptiveScheduler
from .executive_metrics import ExecutiveMetrics
from .meta_executive import MetaExecutive
from .dashboard import ExecutiveDashboard
