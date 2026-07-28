"""Governance Manager: Unified API for policy lifecycle and axiom enforcement."""
import os
import logging
from typing import List, Dict, Any, Optional
from .core_axioms import CoreAxiom, DEFAULT_AXIOMS
from .policy import Policy
from .policy_store import PolicyStore
from .policy_engine import PolicyEngine

logger = logging.getLogger(__name__)

class GovernanceManager:
    def __init__(self, data_dir: str = "governance_data"):
        self.store = PolicyStore(data_dir=data_dir)
        self.axioms = self._load_axioms()
        self.engine = PolicyEngine(store=self.store, axioms=self.axioms)
        logger.info("GovernanceManager initialized with %d axioms", len(self.axioms))

    def _load_axioms(self) -> List[CoreAxiom]:
        stored = self.store.load_axioms()
        if not stored:
            self.store.save_axioms(DEFAULT_AXIOMS)
            return list(DEFAULT_AXIOMS)
        return stored

    def load_policies(self) -> List[Policy]:
        return self.store.load_policies()

    def get_active_policies(self) -> List[Policy]:
        all_policies = self.load_policies()
        return [p for p in all_policies if p.status == "active"]

    def register_policy(self, policy: Policy) -> bool:
        return self.engine.register_policy(policy)

    def enable_policy(self, policy_id: str) -> bool:
        return self.engine.enable_policy(policy_id)

    def disable_policy(self, policy_id: str) -> bool:
        return self.engine.disable_policy(policy_id)

    def evaluate_policy(self, policy: Policy, context: Dict[str, Any] = None) -> Dict[str, Any]:
        return self.engine.evaluate(policy, context)

    def validate_policy(self, policy: Policy) -> bool:
        return self.engine.validate(policy)

    def rollback_policy(self, policy_id: str, target_version: str) -> bool:
        return self.engine.rollback(policy_id, target_version)

    def get_history(self, policy_id: str = None) -> List[Dict[str, Any]]:
        return self.store.history(policy_id)

    def get_axioms(self) -> List[CoreAxiom]:
        return self.axioms
