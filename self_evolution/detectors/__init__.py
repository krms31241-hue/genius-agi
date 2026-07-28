from .duplication import DuplicationDetector
from .dead_code import DeadCodeDetector
from .performance import PerformanceDetector
from .security import SecurityDetector
from .architecture import ArchitectureDetector
from .maintainability import MaintainabilityDetector
from .memory_leaks import MemoryLeakDetector
from .crash_risk import CrashRiskDetector
from .syntax import SyntaxDetector
from .logic import LogicDetector

ALL_DETECTORS = [
    DuplicationDetector,
    DeadCodeDetector,
    PerformanceDetector,
    SecurityDetector,
    ArchitectureDetector,
    MaintainabilityDetector,
    MemoryLeakDetector,
    CrashRiskDetector,
    SyntaxDetector,
    LogicDetector
]
