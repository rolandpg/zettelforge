"""
Ontology Validator — Phase 6 Schema Validation
===============================================

Validates entities and relationships against the A-MEM ontology schema.
Provides validation for CVE, Actor, Tool, Campaign, Sector, and IEP_Policy types.

Usage:
    validator = OntologyValidator()
    valid, errors = validator.validate_entity('actor', 'muddywater', {'type': 'apt'})
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

MEMORY_DIR = Path("/home/rolandpg/.openclaw/workspace/memory")
SCHEMA_FILE = MEMORY_DIR / "memory/ontology_schema.json"


class OntologyValidator:
    """
    Validates entities against the A-MEM ontology schema.
    """

    def __init__(self, schema_file: str = None):
        self.schema_file = Path(schema_file) if schema_file else SCHEMA_FILE
        self.schema = None
        self._load_schema()

    def _load_schema(self) -> None:
        """Load the ontology schema from disk."""
        try:
            with open(self.schema_file) as f:
                self.schema = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to load ontology schema: {e}")

    # -------------------------------------------------------------------------
    # Entity Validation
    # -------------------------------------------------------------------------

    def validate_entity(
        self,
        entity_type: str,
        entity_id: str,
        properties: Dict,
        strict: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Validate an entity against the ontology schema.

        Args:
            entity_type: One of cve, actor, tool, campaign, sector, iep_policy
            entity_id: The entity identifier (canonical name or CVE ID)
            properties: Entity properties to validate
            strict: If True, require all required fields

        Returns:
            (is_valid: bool, errors: List[str])
        """
        errors = []

        # Check entity type exists
        if entity_type not in self.schema.get('entity_types', {}):
            errors.append(f"Unknown entity type: {entity_type}")
            return False, errors

        entity_schema = self.schema['entity_types'][entity_type]
        required_attrs = entity_schema.get('attributes', {})

        # Validate entity_id format if pattern exists
        if 'canonical_format' in entity_schema:
            pattern = entity_schema['canonical_format']
            if not re.match(pattern, entity_id, re.IGNORECASE):
                errors.append(
                    f"Entity ID '{entity_id}' does not match required format: {pattern}"
                )

        # Validate required attributes
        if strict:
            for attr_name, attr_schema in required_attrs.items():
                if attr_schema.get('required', False):
                    if attr_name not in properties:
                        errors.append(
                            f"Missing required attribute: {attr_name}"
                        )
                    elif properties[attr_name] is None:
                        errors.append(
                            f"Required attribute {attr_name} is null"
                        )

        # Validate each provided attribute
        for attr_name, value in properties.items():
            if attr_name not in required_attrs:
                errors.append(f"Unknown attribute: {attr_name}")
                continue

            attr_schema = required_attrs[attr_name]

            # Type check
            expected_type = attr_schema.get('type')
            if expected_type == 'string' and not isinstance(value, str):
                errors.append(f"Attribute {attr_name}: expected string, got {type(value).__name__}")
            elif expected_type == 'number' and not isinstance(value, (int, float)):
                errors.append(f"Attribute {attr_name}: expected number, got {type(value).__name__}")
            elif expected_type == 'integer' and not isinstance(value, int):
                errors.append(f"Attribute {attr_name}: expected integer, got {type(value).__name__}")
            elif expected_type == 'array' and not isinstance(value, list):
                errors.append(f"Attribute {attr_name}: expected array, got {type(value).__name__}")
            elif expected_type == 'object' and not isinstance(value, dict):
                errors.append(f"Attribute {attr_name}: expected object, got {type(value).__name__}")

            # Pattern check
            if 'pattern' in attr_schema and isinstance(value, str):
                if not re.match(attr_schema['pattern'], value):
                    errors.append(
                        f"Attribute {attr_name}: '{value}' does not match pattern {attr_schema['pattern']}"
                    )

            # Enum check
            if 'enum' in attr_schema and value not in attr_schema['enum']:
                errors.append(
                    f"Attribute {attr_name}: '{value}' not in allowed values: {attr_schema['enum']}"
                )

            # Min/max checks for numbers
            if isinstance(value, (int, float)):
                if 'min' in attr_schema and value < attr_schema['min']:
                    errors.append(
                        f"Attribute {attr_name}: {value} is less than minimum {attr_schema['min']}"
                    )
                if 'max' in attr_schema and value > attr_schema['max']:
                    errors.append(
                        f"Attribute {attr_name}: {value} is greater than maximum {attr_schema['max']}"
                    )

            # Array item type check
            if isinstance(value, list) and 'items' in attr_schema:
                item_schema = attr_schema['items']
                for i, item in enumerate(value):
                    if item_schema.get('type') == 'string' and not isinstance(item, str):
                        errors.append(
                            f"Attribute {attr_name}[{i}]: expected string, got {type(item).__name__}"
                        )

        return len(errors) == 0, errors

    def validate_cve(self, cve_id: str, properties: Dict, strict: bool = True) -> Tuple[bool, List[str]]:
        """Validate a CVE entity."""
        return self.validate_entity('cve', cve_id, properties, strict)

    def validate_actor(self, name: str, properties: Dict, strict: bool = True) -> Tuple[bool, List[str]]:
        """Validate an Actor entity."""
        return self.validate_entity('actor', name, properties, strict)

    def validate_tool(self, name: str, properties: Dict, strict: bool = True) -> Tuple[bool, List[str]]:
        """Validate a Tool entity."""
        return self.validate_entity('tool', name, properties, strict)

    def validate_campaign(self, name: str, properties: Dict, strict: bool = True) -> Tuple[bool, List[str]]:
        """Validate a Campaign entity."""
        return self.validate_entity('campaign', name, properties, strict)

    def validate_sector(self, name: str, properties: Dict, strict: bool = True) -> Tuple[bool, List[str]]:
        """Validate a Sector entity."""
        return self.validate_entity('sector', name, properties, strict)

    def validate_iep_policy(self, policy_id: str, properties: Dict, strict: bool = True) -> Tuple[bool, List[str]]:
        """Validate an IEP_Policy entity."""
        return self.validate_entity('iep_policy', policy_id, properties, strict)

    # -------------------------------------------------------------------------
    # Relationship Validation
    # -------------------------------------------------------------------------

    def validate_relationship(
        self,
        from_type: str,
        to_type: str,
        relationship_type: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate that a relationship type is allowed between entity types.

        Args:
            from_type: Source entity type
            to_type: Target entity type
            relationship_type: The relationship to validate

        Returns:
            (is_valid: bool, errors: List[str])
        """
        errors = []

        # Check relationship type exists
        if relationship_type not in self.schema.get('relationship_types', {}):
            errors.append(f"Unknown relationship type: {relationship_type}")
            return False, errors

        # Validate entity types
        if from_type not in self.schema.get('entity_types', {}):
            errors.append(f"Unknown source entity type: {from_type}")

        if to_type not in self.schema.get('entity_types', {}):
            errors.append(f"Unknown target entity type: {to_type}")

        return len(errors) == 0, errors

    def validate_edge(
        self,
        from_entity_type: str,
        from_entity_id: str,
        to_entity_type: str,
        to_entity_id: str,
        relationship_type: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate a complete edge before creation.

        Returns:
            (is_valid: bool, errors: List[str])
        """
        errors = []

        # Validate relationship type
        valid, rel_errors = self.validate_relationship(
            from_entity_type, to_entity_type, relationship_type
        )
        if not valid:
            errors.extend(rel_errors)

        # Validate entity types have proper IDs
        if from_entity_type == 'cve':
            if not re.match(r'^CVE-\d{4}-\d{4,}$', from_entity_id, re.IGNORECASE):
                errors.append(f"Invalid CVE format for source: {from_entity_id}")

        if to_entity_type == 'cve':
            if not re.match(r'^CVE-\d{4}-\d{4,}$', to_entity_id, re.IGNORECASE):
                errors.append(f"Invalid CVE format for target: {to_entity_id}")

        return len(errors) == 0, errors

    # -------------------------------------------------------------------------
    # Policy Validation
    # -------------------------------------------------------------------------

    def validate_hasl(self, hasl: Dict) -> Tuple[bool, List[str]]:
        """
        Validate the HASL (Handling, Action, Sharing, Licensing) object.

        Args:
            hasl: Dictionary with handling, action, sharing, licensing

        Returns:
            (is_valid: bool, errors: List[str])
        """
        errors = []
        required = ['handling', 'action', 'sharing', 'licensing']

        for field in required:
            if field not in hasl:
                errors.append(f"Missing HASL field: {field}")

        if 'handling' in hasl:
            valid_handling = ['OPEN', 'RESTRICTED', 'CONFIDENTIAL', 'PRIVATE']
            if hasl['handling'] not in valid_handling:
                errors.append(
                    f"Invalid handling value: {hasl['handling']}. "
                    f"Must be one of: {valid_handling}"
                )

        if 'action' in hasl:
            valid_actions = ['READ', 'WRITE', 'MODERATE', 'ADMIN']
            if hasl['action'] not in valid_actions:
                errors.append(
                    f"Invalid action value: {hasl['action']}. "
                    f"Must be one of: {valid_actions}"
                )

        if 'sharing' in hasl:
            valid_sharing = [
                'NONE', 'INTERNAL', 'TLP_WHITE', 'TLP_GREEN', 'TLP_AMBER', 'TLP_RED',
                'COMMERCIAL'
            ]
            if hasl['sharing'] not in valid_sharing:
                errors.append(
                    f"Invalid sharing value: {hasl['sharing']}. "
                    f"Must be one of: {valid_sharing}"
                )

        if 'licensing' in hasl:
            valid_licensing = [
                'CC0', 'CC-BY', 'CC-BY-SA', 'CC-BY-NC', 'CC-BY-ND',
                'CC-BY-NC-SA', 'CC-BY-NC-ND', 'ALL-RIGHTS-RESERVED', 'OPEN-GOVERNMENT'
            ]
            if hasl['licensing'] not in valid_licensing:
                errors.append(
                    f"Invalid licensing value: {hasl['licensing']}. "
                    f"Must be one of: {valid_licensing}"
                )

        return len(errors) == 0, errors

    def validate_policy(
        self,
        policy_id: str,
        policy: Dict,
        strict: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Validate an IEP 2.0 policy.

        Args:
            policy_id: Policy identifier (should match pattern)
            policy: Full policy document

        Returns:
            (is_valid: bool, errors: List[str])
        """
        errors = []

        # Validate policy_id format
        if not re.match(r'^IEP-[A-Z]{2,4}-\d{4}$', policy_id):
            errors.append(
                f"Invalid policy_id format: {policy_id}. "
                f"Expected format: IEP-XXXX-0000"
            )

        # Validate required fields
        if 'name' not in policy:
            errors.append("Missing required field: name")
        if 'description' not in policy:
            errors.append("Missing required field: description")

        # Validate HASL
        if 'hasl' not in policy:
            errors.append("Missing required field: hasl")
        else:
            valid, hasl_errors = self.validate_hasl(policy['hasl'])
            if not valid:
                errors.extend([f"hasl.{e}" for e in hasl_errors])

        # Validate status if present
        if 'status' in policy:
            valid_statuses = ['active', 'expired', 'revoked', 'draft']
            if policy['status'] not in valid_statuses:
                errors.append(
                    f"Invalid status: {policy['status']}. "
                    f"Must be one of: {valid_statuses}"
                )

        # Validate timestamps if present
        for ts_field in ['created_at', 'modified_at', 'expiration', 'revocation_date']:
            if ts_field in policy:
                try:
                    datetime.fromisoformat(policy[ts_field].replace('Z', '+00:00').replace('+00:00', ''))
                except (ValueError, TypeError):
                    errors.append(f"Invalid timestamp format: {ts_field} = {policy[ts_field]}")

        return len(errors) == 0, errors

    # -------------------------------------------------------------------------
    # Bulk Validation
    # -------------------------------------------------------------------------

    def validate_nodes(
        self,
        nodes: List[Dict]
    ) -> Dict[str, Tuple[bool, List[str]]]:
        """
        Validate multiple nodes at once.

        Returns:
            Dict[node_id_or_entity_id -> (is_valid, errors)]
        """
        results = {}
        for node in nodes:
            entity_type = node.get('entity_type')
            entity_id = node.get('entity_id')
            properties = node.get('properties', {})

            if not entity_type or not entity_id:
                results[str(node)] = (False, ["Missing entity_type or entity_id"])
                continue

            valid, errors = self.validate_entity(entity_type, entity_id, properties)
            results[entity_id] = (valid, errors)

        return results

    def validate_policies(
        self,
        policies: Dict[str, Dict]
    ) -> Dict[str, Tuple[bool, List[str]]]:
        """
        Validate multiple policies at once.

        Returns:
            Dict[policy_id -> (is_valid, errors)]
        """
        results = {}
        for policy_id, policy in policies.items():
            valid, errors = self.validate_policy(policy_id, policy)
            results[policy_id] = (valid, errors)

        return results

    # -------------------------------------------------------------------------
    # Schema Helpers
    # -------------------------------------------------------------------------

    def get_required_fields(self, entity_type: str) -> List[str]:
        """Get list of required fields for an entity type."""
        entity_schema = self.schema.get('entity_types', {}).get(entity_type, {})
        required_attrs = entity_schema.get('attributes', {})

        return [
            name for name, schema in required_attrs.items()
            if schema.get('required', False)
        ]

    def get_allowed_values(self, entity_type: str, field: str) -> Optional[List[str]]:
        """Get allowed values for a field if it has an enum."""
        entity_schema = self.schema.get('entity_types', {}).get(entity_type, {})
        attributes = entity_schema.get('attributes', {})

        field_schema = attributes.get(field, {})
        return field_schema.get('enum')

    def get_relationships_for_type(self, entity_type: str) -> List[str]:
        """Get relationship types that can originate from this entity type."""
        rel_types = self.schema.get('relationship_types', {})
        allowed = []

        for rel_name, rel_schema in rel_types.items():
            # Check if this entity type is mentioned in description
            description = rel_schema.get('description', '').lower()
            if entity_type.lower() in description:
                allowed.append(rel_name)

        return allowed


# =============================================================================
# CLI / Quick Test
# =============================================================================

if __name__ == "__main__":
    validator = OntologyValidator()

    print("Ontology Validator CLI")
    print("=" * 50)

    # Test CVE validation
    print("\n1. CVE Validation:")
    valid, errors = validator.validate_cve('CVE-2024-3094', {
        'description': 'ProxyLogon vulnerability',
        'cvss_score': 9.8,
        'severity': 'critical',
        'published_date': '2024-03-03'
    })
    print(f"   CVE-2024-3094: {'VALID' if valid else 'INVALID'}")
    if errors:
        for e in errors:
            print(f"      - {e}")

    # Test actor validation
    print("\n2. Actor Validation:")
    valid, errors = validator.validate_actor('muddywater', {
        'type': 'apt',
        'first_seen': '2023-01-01'
    })
    print(f"   muddywater: {'VALID' if valid else 'INVALID'}")

    # Test IEP policy validation
    print("\n3. IEP Policy Validation:")
    valid, errors = validator.validate_policy('IEP-US-0001', {
        'name': 'US Gov Threat Intel',
        'description': 'Threat intelligence for US government',
        'hasl': {
            'handling': 'RESTRICTED',
            'action': 'READ',
            'sharing': 'TLP_GREEN',
            'licensing': 'CC-BY'
        },
        'created_by': 'admin',
        'created_at': '2026-04-02T00:00:00'
    })
    print(f"   IEP-US-0001: {'VALID' if valid else 'INVALID'}")
    if errors:
        for e in errors:
            print(f"      - {e}")

    # Test HASL validation
    print("\n4. HASL Validation:")
    valid, errors = validator.validate_hasl({
        'handling': 'RESTRICTED',
        'action': 'READ',
        'sharing': 'TLP_GREEN',
        'licensing': 'CC-BY'
    })
    print(f"   HASL object: {'VALID' if valid else 'INVALID'}")

    # Test relationship validation
    print("\n5. Relationship Validation:")
    valid, errors = validator.validate_relationship('actor', 'cve', 'EXPLOITS')
    print(f"   actor -> cve (EXPLOITS): {'VALID' if valid else 'INVALID'}")

    # Get required fields
    print("\n6. Required Fields (Actor):")
    for field in validator.get_required_fields('actor'):
        allowed = validator.get_allowed_values('actor', field)
        print(f"   - {field}" + (f" (enum: {allowed})" if allowed else ""))
