"""Simulation Engine Core: Safe world cloning, action simulation, and prediction."""
__version__ = "1.0.0"
from .simulation_models import SimulationAction, SimulationPlan
from .simulation_result import SimulationResult
from .scenario import SimulationScenario
from .simulator import SimulationEngine
