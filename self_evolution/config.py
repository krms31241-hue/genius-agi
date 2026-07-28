"""Engine configuration and constants."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
CANDIDATES_DIR = os.path.join(BASE_DIR, "candidates")
MEMORY_DB_PATH = os.path.join(BASE_DIR, "evolution_memory.db")

MAX_CANDIDATES_PER_CYCLE = 5
RISK_LEVELS = {"low": 0.3, "medium": 0.6, "high": 0.9}

IGNORE_DIRS = {
    ".git", "__pycache__", "venv", "env", ".project_versions",
    "self_evolution", "lab", "upgrade", "node_modules",
    ".pytest_cache", ".mypy_cache", "dist", "build"
}

SUPPORTED_EXTENSIONS = {".py"}
