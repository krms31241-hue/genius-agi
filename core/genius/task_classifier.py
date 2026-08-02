import re
from typing import Dict, List, Optional

from core.genius.models import ClassificationResult, TaskType


class TaskClassifier:
    """Deterministic keyword‑based task classifier."""

    _KEYWORDS: Dict[TaskType, List[str]] = {
        TaskType.CHAT: ["hello", "hi", "how are you", "what's up", "good morning", "tell me a joke", "thanks", "thank you"],
        TaskType.REASONING: ["analyze", "compare", "why", "reason", "logic", "deduce", "explain", "proof", "strategy", "evaluate", "assess", "infer", "conclude", "hypothesis", "argument", "justify"],
        TaskType.CODING: ["python", "javascript", "typescript", "bug", "fix", "function", "class", "compile", "terminal", "docker", "api", "database", "sql", "react", "next", "fastapi", "flask", "code", "programming", "algorithm", "debug", "syntax", "error", "exception", "stacktrace", "method", "variable", "loop", "condition", "pull request", "merge", "commit", "deploy"],
        TaskType.ARCHITECTURE: ["architecture", "design", "system design", "microservices", "scalability", "performance", "high availability", "distributed", "cloud", "aws", "azure", "gcp", "kubernetes", "terraform"],
        TaskType.RESEARCH: ["research", "paper", "article", "journal", "cite", "reference", "study", "experiment", "findings", "literature", "survey"],
        TaskType.PLANNING: ["plan", "roadmap", "timeline", "milestone", "schedule", "objective", "goal", "deliverable", "sprint", "backlog"],
        TaskType.ANALYSIS: ["analysis", "metric", "kpi", "statistics", "data", "trend", "insight", "dashboard", "report", "forecast", "predict"],
        TaskType.TRANSLATION: ["translate", "translation", "arabic", "english", "french", "german", "spanish", "chinese", "japanese", "russian", "portuguese", "language"],
        TaskType.SUMMARIZATION: ["summarize", "summary", "condense", "brief", "shorten", "tl;dr", "gist"],
        TaskType.DOCUMENTATION: ["document", "documentation", "readme", "markdown", "wiki", "how to", "guide", "tutorial", "manual", "reference"],
        TaskType.SELF_EVOLUTION: ["evolve", "improve yourself", "update your knowledge", "learn from", "adapt", "self modify"],
        TaskType.LEARNING: ["learn", "teach me", "understand", "concept", "tutorial", "lesson", "course", "training"],
        TaskType.UNKNOWN: [],
    }

    _COMPLEXITY_TERMS = ["complex", "difficult", "advanced", "expert", "deep", "intricate", "sophisticated", "nuanced", "multifaceted"]

    def __init__(self) -> None:
        self._patterns: Dict[TaskType, List[re.Pattern]] = {}
        for task_type, keywords in self._KEYWORDS.items():
            patterns = [re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE) for kw in keywords]
            self._patterns[task_type] = patterns

    def classify(self, prompt: str) -> ClassificationResult:
        normalized = " ".join(prompt.lower().split())
        word_count = len(normalized.split())
        scores: Dict[TaskType, int] = {}
        for task_type, patterns in self._patterns.items():
            count = 0
            for pattern in patterns:
                count += len(pattern.findall(normalized))
            scores[task_type] = count

        best_type = TaskType.CHAT
        best_score = 0
        for task_type, score in scores.items():
            if score > best_score:
                best_score = score
                best_type = task_type

        confidence = min(1.0, (best_score / max(1, word_count)) * 2.0)
        complexity_word_count = 0
        for term in self._COMPLEXITY_TERMS:
            if re.search(rf"\b{re.escape(term)}\b", normalized, re.IGNORECASE):
                complexity_word_count += 1
        complexity_score = min(1.0, (word_count / 100) * 0.5 + (complexity_word_count / 10))
        estimated_tokens = int(word_count * 1.3) + 50

        return ClassificationResult(
            task_type=best_type,
            confidence=confidence,
            complexity=complexity_score,
            estimated_tokens=estimated_tokens,
            recommended_provider=None,
            reasoning=f"Keyword scoring: {best_type} with score {best_score}",
        )
