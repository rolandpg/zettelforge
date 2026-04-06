"""
IEP Policy — FIRST IEP 2.0 Information Exchange Policy Management
==================================================================

Implements FIRST IEP 2.0 (Information Exchange Policy) framework for A-MEM.
Provides IEP policy creation, validation, temporal resolution, and compliance checking.

Usage:
    from iep_policy import IEPManager

    manager = IEPManager()
    policy = manager.create_policy({
        'policy_id': 'IEP-US-0001',
        'name': 'US Gov Threat Intel',
        'hasl': {
            'handling': 'RESTRICTED',
            'action': 'READ',
            'sharing': 'TLP_GREEN',
            'licensing': 'CC-BY'
        }
    })
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import uuid

from .knowledge_graph import get_knowledge_graph, KnowledgeGraph
from ontology_validator import OntologyValidator


# =============================================================================
# IEP 2.0 Constants
# =============================================================================

HANDLING_LEVELS = ['OPEN', 'RESTRICTED', 'CONFIDENTIAL', 'PRIVATE']
ACTION_LEVELS = ['READ', 'WRITE', 'MODERATE', 'ADMIN']
SHARING_LEVELS = [
    'NONE', 'INTERNAL', 'TLP_WHITE', 'TLP_GREEN', 'TLP_AMBER', 'TLP_RED', 'COMMERCIAL'
]
LICENSE_LEVELS = [
    'CC0', 'CC-BY', 'CC-BY-SA', 'CC-BY-NC', 'CC-BY-ND',
    'CC-BY-NC-SA', 'CC-BY-NC-ND', 'ALL-RIGHTS-RESERVED', 'OPEN-GOVERNMENT'
]

TLP_MAP = {
    'TLP_WHITE': {'handling': 'OPEN', 'sharing': 'TLP_WHITE'},
    'TLP_GREEN': {'handling': 'RESTRICTED', 'sharing': 'TLP_GREEN'},
    'TLP_AMBER': {'handling': 'CONFIDENTIAL', 'sharing': 'TLP_AMBER'},
    'TLP_RED': {'handling': 'PRIVATE', 'sharing': 'TLP_RED'},
}


class IEPManager:
    """
    FIRST IEP 2.0 Policy Manager for A-MEM.
    Handles policy creation, validation, temporal resolution, and compliance.
    """

    def __init__(
        self,
        kg: KnowledgeGraph = None,
        policy_file: str = None
    ):
        self.kg = kg if kg else get_knowledge_graph()
        self.validator = OntologyValidator()
        self.policy_file = Path(policy_file) if policy_file else None
        self._policies: Dict[str, Dict] = {}
        self._lock = threading.RLock()
        self._load_policies()

    def _load_policies(self) -> None:
        """Load policies from file if specified."""
        if self.policy_file and self.policy_file.exists():
            try:
                with open(self.policy_file) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                policy = json.loads(line)
                                self._policies[policy['policy_id']] = policy
                            except (json.JSONDecodeError, KeyError):
                                continue
            except IOError:
                pass

    def _save_policies(self) -> None:
        """Save policies to file if specified."""
        if self.policy_file:
            tmp_file = self.policy_file.with_suffix('.jsonl.tmp')
            with open(tmp_file, 'w') as f:
                for policy in self._policies.values():
                    f.write(json.dumps(policy) + '\n')
            tmp_file.rename(self.policy_file)

    # -------------------------------------------------------------------------
    # Policy Creation and Management
    # -------------------------------------------------------------------------

    def create_policy(
        self,
        policy_id: str,
        name: str,
        hasl: Dict[str, str],
        description: str = None,
        **kwargs
    ) -> Dict:
        """
        Create a new IEP 2.0 policy.

        Args:
            policy_id: Policy identifier (IEP-XXX-0000 format)
            name: Policy name
            hasl: Dictionary with handling, action, sharing, licensing
            description: Policy description
            **kwargs: Additional policy fields

        Returns:
            Created policy dictionary

        Raises:
            ValueError: If policy_id format is invalid or hasl is incomplete
        """
        # Validate policy_id format
        if not self._validate_policy_id(policy_id):
            raise ValueError(
                f"Invalid policy_id format: {policy_id}. "
                f"Expected: IEP-XXX-0000 (e.g., IEP-US-0001)"
            )

        # Validate HASL
        required = ['handling', 'action', 'sharing', 'licensing']
        for field in required:
            if field not in hasl:
                raise ValueError(f"Missing required HASL field: {field}")

        # Validate individual HASL values
        self._validate_hasl(hasl)

        # Build policy
        now = datetime.utcnow().isoformat() + 'Z'
        policy = {
            'policy_id': policy_id,
            'name': name,
            'description': description or '',
            'version': '1.0.0',
            'hasl': hasl.copy(),
            'created_by': kwargs.get('created_by', 'system'),
            'created_at': now,
            'modified_by': kwargs.get('created_by', 'system'),
            'modified_at': now,
            'status': 'active'
        }

        # Add optional fields
        if 'applies_to_entities' in kwargs:
            policy['applies_to_entities'] = kwargs['applies_to_entities']
        if 'expiration' in kwargs:
            policy['expiration'] = kwargs['expiration']

        # Store policy
        with self._lock:
            self._policies[policy_id] = policy
            self._save_policies()

            # Add to knowledge graph
            self.kg.add_policy(policy)

        return policy

    def _validate_policy_id(self, policy_id: str) -> bool:
        """Validate policy_id format."""
        import re
        pattern = r'^IEP-[A-Z]{2,4}-\d{4}$'
        return bool(re.match(pattern, policy_id))

    def _validate_hasl(self, hasl: Dict) -> bool:
        """Validate HASL values."""
        if hasl.get('handling') not in HANDLING_LEVELS:
            raise ValueError(
                f"Invalid handling: {hasl['handling']}. "
                f"Must be one of: {HANDLING_LEVELS}"
            )
        if hasl.get('action') not in ACTION_LEVELS:
            raise ValueError(
                f"Invalid action: {hasl['action']}. "
                f"Must be one of: {ACTION_LEVELS}"
            )
        if hasl.get('sharing') not in SHARING_LEVELS:
            raise ValueError(
                f"Invalid sharing: {hasl['sharing']}. "
                f"Must be one of: {SHARING_LEVELS}"
            )
        if hasl.get('licensing') not in LICENSE_LEVELS:
            raise ValueError(
                f"Invalid licensing: {hasl['licensing']}. "
                f"Must be one of: {LICENSE_LEVELS}"
            )
        return True

    def update_policy(
        self,
        policy_id: str,
        **kwargs
    ) -> Optional[Dict]:
        """Update an existing policy."""
        with self._lock:
            if policy_id not in self._policies:
                return None

            policy = self._policies[policy_id]
            policy['modified_by'] = kwargs.get('modified_by', 'system')
            policy['modified_at'] = datetime.utcnow().isoformat() + 'Z'

            # Update fields
            for key, value in kwargs.items():
                if key not in ['created_at', 'created_by', 'policy_id']:
                    policy[key] = value

            # Re-validate if HASL changed
            if 'hasl' in kwargs:
                self._validate_hasl(policy['hasl'])

            self._save_policies()
            self.kg._policies[policy_id] = policy
            self.kg._save_policies()

            return policy

    def get_policy(self, policy_id: str) -> Optional[Dict]:
        """Get a policy by ID."""
        with self._lock:
            return self._policies.get(policy_id)

    def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy."""
        with self._lock:
            if policy_id not in self._policies:
                return False

            del self._policies[policy_id]
            self._save_policies()
            self.kg._policies.pop(policy_id, None)
            self.kg._save_policies()
            return True

    def list_policies(self, status: str = None) -> List[Dict]:
        """List all policies, optionally filtered by status."""
        with self._lock:
            policies = list(self._policies.values())
            if status:
                policies = [p for p in policies if p.get('status') == status]
            return policies

    # -------------------------------------------------------------------------
    # Policy Application and Compliance
    # -------------------------------------------------------------------------

    def apply_policy(
        self,
        policy_id: str,
        entity_type: str,
        entity_id: str
    ) -> bool:
        """
        Apply a policy to an entity.

        Args:
            policy_id: Policy to apply
            entity_type: Type of entity
            entity_id: ID of entity

        Returns:
            True if policy was applied
        """
        policy = self.get_policy(policy_id)
        if not policy:
            return False

        with self._lock:
            # Add to applies_to_entities if not already present
            entities = policy.get('applies_to_entities', [])
            entity_key = f"{entity_type}:{entity_id}"
            if entity_key not in entities:
                entities.append(entity_key)
                policy['applies_to_entities'] = entities
                policy['modified_at'] = datetime.utcnow().isoformat() + 'Z'
                self._save_policies()

            # Add policy to knowledge graph
            self.kg.add_policy(policy)

            return True

    def check_compliance(
        self,
        entity_type: str,
        entity_id: str,
        action: str
    ) -> Tuple[bool, List[str]]:
        """
        Check if an action on an entity complies with all applicable policies.

        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            action: Action to check (READ, WRITE, MODERATE, ADMIN)

        Returns:
            (compliant: bool, violations: List[str])
        """
        violations = []

        with self._lock:
            # Get all active policies
            policies = self.get_active_policies()

            if not policies:
                return True, []  # No policies = no restrictions

            # Check each applicable policy
            for policy in policies:
                # Check if policy applies to this entity
                applies_to = policy.get('applies_to_entities', [])
                entity_key = f"{entity_type}:{entity_id}"

                if applies_to and entity_key not in applies_to:
                    continue  # Policy doesn't apply to this entity

                # Check action compliance
                policy_action = policy.get('hasl', {}).get('action', 'READ')
                if not self._action_complies(policy_action, action):
                    violations.append(
                        f"Policy {policy['policy_id']} restricts {action} "
                        f"(requires: {policy_action})"
                    )

        return len(violations) == 0, violations

    def _action_complies(self, policy_action: str, requested_action: str) -> bool:
        """Check if requested action complies with policy action level."""
        action_levels = {'READ': 1, 'WRITE': 2, 'MODERATE': 3, 'ADMIN': 4}
        policy_level = action_levels.get(policy_action, 1)
        requested_level = action_levels.get(requested_action, 1)
        return requested_level <= policy_level

    # -------------------------------------------------------------------------
    # Temporal Resolution
    # -------------------------------------------------------------------------

    def get_active_policies(self) -> List[Dict]:
        """Get all active (non-expired, non-revoked) policies."""
        with self._lock:
            now = datetime.utcnow()
            active = []

            for policy in self._policies.values():
                if policy.get('status', 'active') != 'active':
                    continue

                # Check expiration
                if 'expiration' in policy:
                    try:
                        exp = datetime.fromisoformat(policy['expiration'].replace('Z', ''))
                        if exp < now:
                            continue
                    except (ValueError, TypeError):
                        pass

                # Check revocation
                if 'revocation_date' in policy:
                    try:
                        rev = datetime.fromisoformat(policy['revocation_date'].replace('Z', ''))
                        if rev < now:
                            continue
                    except (ValueError, TypeError):
                        pass

                active.append(policy)

            return active

    def get_expired_policies(self) -> List[Dict]:
        """Get policies that have expired."""
        with self._lock:
            now = datetime.utcnow()
            expired = []

            for policy in self._policies.values():
                if 'expiration' in policy:
                    try:
                        exp = datetime.fromisoformat(policy['expiration'].replace('Z', ''))
                        if exp < now:
                            expired.append(policy)
                    except (ValueError, TypeError):
                        pass

            return expired

    def expire_policy(self, policy_id: str) -> bool:
        """Mark a policy as expired."""
        policy = self.get_policy(policy_id)
        if not policy:
            return False

        policy['status'] = 'expired'
        policy['modified_at'] = datetime.utcnow().isoformat() + 'Z'
        self.update_policy(policy_id)
        return True

    def revoke_policy(self, policy_id: str, reason: str = None) -> bool:
        """Revoke a policy immediately."""
        policy = self.get_policy(policy_id)
        if not policy:
            return False

        policy['status'] = 'revoked'
        policy['revocation_date'] = datetime.utcnow().isoformat() + 'Z'
        if reason:
            policy['revocation_reason'] = reason
        policy['modified_at'] = datetime.utcnow().isoformat() + 'Z'
        self.update_policy(policy_id)
        return True

    # -------------------------------------------------------------------------
    # TLP Integration
    # -------------------------------------------------------------------------

    def create_tlp_policy(
        self,
        tlp_level: str,
        name: str,
        description: str = None,
        **kwargs
    ) -> Dict:
        """
        Create an IEP policy based on TLP color.

        Args:
            tlp_level: TLP color (TLP_WHITE, TLP_GREEN, TLP_AMBER, TLP_RED)
            name: Policy name
            description: Optional description
            **kwargs: Additional policy fields

        Returns:
            Created policy dictionary
        """
        if tlp_level not in TLP_MAP:
            raise ValueError(
                f"Invalid TLP level: {tlp_level}. "
                f"Must be one of: {list(TLP_MAP.keys())}"
            )

        tlp_config = TLP_MAP[tlp_level]
        hasl = {
            'handling': tlp_config['handling'],
            'action': kwargs.get('action', 'READ'),
            'sharing': tlp_config['sharing'],
            'licensing': kwargs.get('licensing', 'CC-BY')
        }

        # Use numeric ID to match format IEP-XXX-0000
        policy_id = f"IEP-{kwargs.get('country', 'GEN')}-0001"
        return self.create_policy(policy_id, name, hasl, description, **kwargs)

    # -------------------------------------------------------------------------
    # Statistics and Reporting
    # -------------------------------------------------------------------------

    def stats(self) -> Dict:
        """Return policy statistics."""
        with self._lock:
            policies = list(self._policies.values())
            active = [p for p in policies if p.get('status') == 'active']
            expired = [p for p in policies if p.get('status') == 'expired']
            revoked = [p for p in policies if p.get('status') == 'revoked']

            # Count by handling level
            handling_counts = {}
            for p in policies:
                h = p.get('hasl', {}).get('handling', 'UNKNOWN')
                handling_counts[h] = handling_counts.get(h, 0) + 1

            # Count by sharing level
            sharing_counts = {}
            for p in policies:
                s = p.get('hasl', {}).get('sharing', 'NONE')
                sharing_counts[s] = sharing_counts.get(s, 0) + 1

            return {
                'total_policies': len(policies),
                'active_policies': len(active),
                'expired_policies': len(expired),
                'revoked_policies': len(revoked),
                'by_handling': handling_counts,
                'by_sharing': sharing_counts
            }

    def get_policy_compliance_report(self) -> List[Dict]:
        """Generate a compliance report across all entities."""
        report = []
        with self._lock:
            for policy in self._policies.values():
                applies_to = policy.get('applies_to_entities', [])
                if not applies_to:
                    continue

                for entity_key in applies_to:
                    report.append({
                        'policy_id': policy['policy_id'],
                        'entity': entity_key,
                        'action_level': policy['hasl']['action'],
                        'handling': policy['hasl']['handling']
                    })
        return report

    # -------------------------------------------------------------------------
    # Policy ID Generation Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def generate_policy_id(country: str = 'US', category: str = 'INTL') -> str:
        """Generate a new policy ID in the correct format."""
        return f"IEP-{country.upper()}-{category.upper()}-0001"

    @staticmethod
    def next_policy_id(country: str = 'US', category: str = 'INTL', current_ids: List[str] = None) -> str:
        """Generate the next sequential policy ID."""
        if not current_ids:
            return IEPManager.generate_policy_id(country, category)

        # Find highest sequence number
        import re
        pattern = rf'^IEP-{country.upper()}-{category.upper()}-\d{{4}}$'
        max_seq = 0
        for cid in current_ids:
            match = re.match(pattern, cid)
            if match:
                seq = int(match.group(1)[-4:])
                max_seq = max(max_seq, seq)

        return f"IEP-{country.upper()}-{category.upper()}-{max_seq + 1:04d}"


# =============================================================================
# Global Access
# =============================================================================

_iep_manager: Optional[IEPManager] = None
_iep_lock = threading.Lock()


def get_iep_manager() -> IEPManager:
    """Get or create the global IEP manager instance."""
    global _iep_manager
    if _iep_manager is None:
        with _iep_lock:
            if _iep_manager is None:
                _iep_manager = IEPManager()
    return _iep_manager


# =============================================================================
# CLI / Quick Test
# =============================================================================

if __name__ == "__main__":
    manager = IEPManager()

    print("IEP Manager CLI")
    print("=" * 50)

    # Test policy creation
    print("\n1. Creating IEP-US-0001...")
    policy = manager.create_policy(
        policy_id='IEP-US-0001',
        name='US Government Threat Intelligence',
        hasl={
            'handling': 'RESTRICTED',
            'action': 'READ',
            'sharing': 'TLP_GREEN',
            'licensing': 'CC-BY'
        },
        description='Threat intelligence for US government agencies',
        created_by='admin'
    )
    print(f"   Policy ID: {policy['policy_id']}")
    print(f"   HASL: {policy['hasl']}")

    # Test TLP policy creation
    print("\n2. Creating TLP Amber policy...")
    amber_policy = manager.create_tlp_policy(
        tlp_level='TLP_AMBER',
        name='Share with Industry Partners',
        country='US',
        created_by='admin'
    )
    print(f"   Policy ID: {amber_policy['policy_id']}")
    print(f"   TLP: TLP_AMBER -> Handling: {amber_policy['hasl']['handling']}")

    # Test policy listing
    print("\n3. Listing policies...")
    policies = manager.list_policies()
    print(f"   Total policies: {len(policies)}")

    # Test policy compliance check
    print("\n4. Testing compliance check...")
    compliant, violations = manager.check_compliance('actor', 'muddywater', 'READ')
    print(f"   READ on muddywater: {'COMPLIANT' if compliant else 'VIOLATION'}")
    if violations:
        for v in violations:
            print(f"      - {v}")

    # Test policy stats
    print("\n5. Policy statistics:")
    stats = manager.stats()
    print(f"   Active: {stats['active_policies']}")
    print(f"   By handling: {stats['by_handling']}")
    print(f"   By sharing: {stats['by_sharing']}")
