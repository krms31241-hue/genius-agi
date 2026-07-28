from .syntax import SyntaxAnalyzer
from .imports import ImportAnalyzer
from .dependencies import DependencyAnalyzer
from .circular import CircularDependencyAnalyzer
from .security import SecurityAnalyzer
from .memory import MemoryAnalyzer
from .performance import PerformanceAnalyzer
from .style import StyleAnalyzer
from .architecture import ArchitectureAnalyzer
from .regression import RegressionAnalyzer

ALL_ANALYZERS = [
    SyntaxAnalyzer,
    ImportAnalyzer,
    DependencyAnalyzer,
    CircularDependencyAnalyzer,
    SecurityAnalyzer,
    MemoryAnalyzer,
    PerformanceAnalyzer,
    StyleAnalyzer,
    ArchitectureAnalyzer,
    RegressionAnalyzer
]
