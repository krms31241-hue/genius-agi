"""
Task Analyzer for Genius AGI.

Deterministic task classification.
No LLM is used.
"""

from __future__ import annotations

import re

from collections import defaultdict

from core.router.model_registry import TaskType


class TaskAnalyzer:

    KEYWORDS = {

        TaskType.CHAT: {
            1: [],
        },

        TaskType.CODING: {
            5: [
                "python",
                "javascript",
                "typescript",
                "java",
                "c++",
                "c#",
                "bug",
                "debug",
                "error",
                "exception",
                "fix",
                "function",
                "class",
                "terminal",
                "docker",
                "api",
                "database",
                "sql",
                "react",
                "next",
                "fastapi",
                "flask",
                "code",
                "programming",
                "algorithm",
                "كود",
                "برمجة",
                "بايثون",
                "جافاسكريبت",
                "إصلاح",
                "خطأ",
                "تصحيح",
                "دالة",
                "قاعدة بيانات",
            ],
            2: [
                "method",
                "variable",
                "loop",
                "compile",
                "syntax",
            ],
        },

        TaskType.REASONING: {
            5: [
                "analyze",
                "analysis",
                "reason",
                "logic",
                "why",
                "deduce",
                "infer",
                "strategy",
                "explain",
                "proof",
                "evaluate",
                "compare",
                "حلل",
                "تحليل",
                "اشرح",
                "فسر",
                "قارن",
                "منطق",
                "استنتج",
                "سبب",
            ],
        },

        TaskType.VISION: {
            5: [
                "image",
                "photo",
                "picture",
                "vision",
                "ocr",
                "detect",
                "recognize",
                "visual",
            ],
        },

        TaskType.IMAGE: {
            5: [
                "draw",
                "logo",
                "illustration",
                "design",
                "art",
                "render",
            ],
        },

        TaskType.AUDIO: {
            5: [
                "speech",
                "voice",
                "audio",
                "microphone",
                "transcribe",
            ],
        },

        TaskType.VIDEO: {
            5: [
                "video",
                "movie",
                "animation",
                "clip",
            ],
        },


        TaskType.DOCUMENT: {
            5: [
                "pdf",
                "ملف",
                "مستند",
                "وثيقة",
                "تقرير",
                "doc",
                "docx",
                "markdown",
                "readme",
                "document",
                "report",
                "text",
                "file",
            ],
        },

        TaskType.TRANSLATION: {
            5: [
                "translate",
                "ترجم",
                "ترجمة",
                "عربي",
                "إنجليزي",
                "فرنسي",
                "لغة",
                "translation",
                "arabic",
                "english",
                "french",
                "german",
                "spanish",
                "japanese",
                "chinese",
                "language",
            ],
        },

        TaskType.SEARCH: {
            5: [
                "search",
                "ابحث",
                "بحث",
                "ابحث في الإنترنت",
                "ويب",
                "lookup",
                "find",
                "browse",
                "internet",
                "web",
                "google",
            ],
        },

        TaskType.EMBEDDING: {
            5: [
                "embedding",
                "embed",
                "vector",
                "semantic",
                "similarity",
            ],
        },

        TaskType.AGENT: {
            5: [
                "agent",
                "workflow",
                "planner",
                "executor",
                "orchestrator",
                "delegate",
                "autonomous",
            ],
        },

    }

    def __init__(self) -> None:

        self._patterns = {}

        for task_type, groups in self.KEYWORDS.items():

            compiled = []

            for weight, keywords in groups.items():

                for keyword in keywords:

                    compiled.append(
                        (
                            weight,
                            re.compile(
                                rf"\b{re.escape(keyword.lower())}\b",
                                re.IGNORECASE,
                            ),
                        )
                    )

            self._patterns[task_type] = compiled

    @staticmethod
    def _normalize(text: str) -> str:

        return " ".join(text.lower().split())


    def analyze(self, prompt: str) -> TaskType:

        text = self._normalize(prompt)

        if not text:
            return TaskType.CHAT

        scores = defaultdict(int)

        for task_type, patterns in self._patterns.items():

            for weight, pattern in patterns:

                if pattern.search(text):

                    scores[task_type] += weight

        if not scores:

            return TaskType.CHAT

        return max(
            scores,
            key=lambda task: scores[task],
        )

    def analyze_details(self, prompt: str) -> dict:

        text = self._normalize(prompt)

        scores = defaultdict(int)
        matched = defaultdict(list)

        for task_type, patterns in self._patterns.items():

            for weight, pattern in patterns:

                match = pattern.search(text)

                if match:

                    scores[task_type] += weight
                    matched[task_type].append(match.group(0))

        task = self.analyze(prompt)

        total = sum(scores.values())

        confidence = (
            round(scores.get(task, 0) / total, 3)
            if total
            else 0.0
        )

        return {
            "task_type": task,
            "confidence": confidence,
            "scores": {
                str(k.value): v
                for k, v in scores.items()
            },
            "matched_keywords": {
                str(k.value): v
                for k, v in matched.items()
            },
        }


__all__ = [
    "TaskAnalyzer",
]
