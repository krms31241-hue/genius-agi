"""Hard constraint validation for candidate decisions."""
from typing import List, Dict, Any, Tuple
from .decision_models import Candidate

class RuleEngine:
    """Enforces absolute safety constraints. Side-effect free."""
    HARD_RULES = [
        "never_delete_files",
        "never_overwrite_backups",
        "never_bypass_sandbox",
        "never_ignore_laboratory",
        "never_execute_unknown_code",
        "never_ignore_security_analyzer"
    ]

    def validate(self, candidate: Candidate, context: Dict[str, Any]) -> Tuple[bool, List[str]]:
        violations = []
        meta = candidate.metadata
        action = candidate.action.lower()
        
        if meta.get("bypass_sandbox") or "bypass sandbox" in action:
            violations.append("never_bypass_sandbox")
        if meta.get("delete_files") or "delete files" in action:
            violations.append("never_delete_files")
        if meta.get("overwrite_backups") or "overwrite backup" in action:
            violations.append("never_overwrite_backups")
        if meta.get("ignore_lab") or "ignore laboratory" in action:
            violations.append("never_ignore_laboratory")
        if meta.get("unknown_code") or "execute unknown" in action:
            violations.append("never_execute_unknown_code")
        if meta.get("ignore_security") or "ignore security" in action:
            violations.append("never_ignore_security_analyzer")
            
        if context.get("security_risk") == "critical" and meta.get("strategy_type") == "experimental":
            violations.append("never_ignore_security_analyzer")
            
        return len(violations) == 0, violations
