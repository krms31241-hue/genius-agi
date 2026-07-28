"""Report generation with scoring."""
import json
import time
from typing import Dict, Any, List

class LabReporter:
    def generate(self, analyzer_results: List[Dict[str, Any]], sandbox_result: Dict[str, Any], patch_id: str) -> Dict[str, Any]:
        scores = {r["analyzer"]: r["score"] for r in analyzer_results}
        weights = {
            "syntax": 1.0, "imports": 0.8, "dependencies": 0.7, "circular_dependencies": 0.9,
            "security": 1.0, "memory": 0.8, "performance": 0.7, "style": 0.5,
            "architecture": 0.8, "regression": 0.9
        }
        total_weight = sum(weights.values())
        confidence = sum(scores.get(k, 0) * w for k, w in weights.items()) / total_weight

        risk = 100 - (scores.get("security", 0) * 0.5 + scores.get("architecture", 0) * 0.3 + scores.get("regression", 0) * 0.2)
        performance = scores.get("performance", 50)
        security = scores.get("security", 50)
        maintainability = (scores.get("style", 50) + scores.get("architecture", 50) + scores.get("memory", 50)) / 3

        passed_all = all(r["passed"] for r in analyzer_results) and sandbox_result.get("success", False)

        report = {
            "patch_id": patch_id,
            "timestamp": time.time(),
            "passed": passed_all,
            "scores": {
                "confidence": round(confidence, 2),
                "risk": round(risk, 2),
                "performance": round(performance, 2),
                "security": round(security, 2),
                "maintainability": round(maintainability, 2)
            },
            "sandbox": sandbox_result,
            "analyzers": analyzer_results
        }
        return report

    def save(self, report: Dict[str, Any], path: str = "lab_report.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return path
