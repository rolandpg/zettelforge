"""
Phase 6 Tests — Ontology, Knowledge Graph & IEP Governance
==========================================================

Test suite for Phase 6 implementation:
- Ontology Schema validation
- Knowledge Graph CRUD operations
- IEP 2.0 Policy management
- Graph-based retrieval
- Integration with existing memory system

Usage:
    python test_phase_6.py

Expected: All tests passing
"""

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'memory'))

import unittest
import json
from memory.knowledge_graph import KnowledgeGraph
from memory.ontology_validator import OntologyValidator
from memory.graph_retriever import GraphRetriever, IEPStore
from memory.iep_policy import IEPManager, HANDLING_LEVELS, ACTION_LEVELS, SHARING_LEVELS, LICENSE_LEVELS


# =============================================================================
# Test Data
# =============================================================================

TEST_CVE = {
    'id': 'CVE-2024-3094',
    'description': 'ProxyLogon vulnerability in Microsoft Exchange',
    'cvss_score': 9.8,
    'severity': 'critical',
    'published_date': '2024-03-03'
}

TEST_ACTOR = {
    'name': 'muddywater',
    'type': 'apt',
    'first_seen': '2023-01-01'
}

TEST_TOOL = {
    'name': 'cobalt_strike',
    'type': 'malware',
    'first_seen': '2015-01-01'
}

TEST_CAMPAIGN = {
    'name': '_operation_solarwinds',
    'actor': 'lazarus',
    'start_date': '2020-12-01'
}

TEST_SECTOR = {
    'name': 'government',
    'category': 'government'
}

TEST_IEP_POLICY = {
    'policy_id': 'IEP-US-0001',
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
}


class TestOntologySchema(unittest.TestCase):
    """Test ontology schema structure and constants."""

    def test_schema_exists(self):
        """Schema file should exist."""
        schema_path = Path(__file__).parent / 'memory' / 'ontology_schema.json'
        self.assertTrue(schema_path.exists())

    def test_entity_types_defined(self):
        """Schema should define all required entity types."""
        schema_path = Path(__file__).parent / 'memory' / 'ontology_schema.json'
        with open(schema_path) as f:
            schema = json.load(f)

        required_types = ['cve', 'actor', 'tool', 'campaign', 'sector', 'iep_policy']
        for etype in required_types:
            self.assertIn(etype, schema['entity_types'])

    def test_relationship_types_defined(self):
        """Schema should define required relationship types."""
        schema_path = Path(__file__).parent / 'memory' / 'ontology_schema.json'
        with open(schema_path) as f:
            schema = json.load(f)

        required_rels = ['USES', 'TARGETS', 'EXPLOITS', 'MITIGATES', 'APPLIES_TO']
        for rel in required_rels:
            self.assertIn(rel, schema['relationship_types'])

    def test_hasl_fields_defined(self):
        """Schema should define HASL structure."""
        schema_path = Path(__file__).parent / 'memory' / 'ontology_schema.json'
        with open(schema_path) as f:
            schema = json.load(f)
        # Check that HASL structure exists in the schema
        self.assertIn('iep_policy', schema['entity_types'])
        self.assertIn('hasl', schema['entity_types']['iep_policy']['attributes'])


class TestKnowledgeGraph(unittest.TestCase):
    """Test knowledge graph CRUD operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.tmp_dir = tempfile.mkdtemp()
        self.nodes_file = Path(self.tmp_dir) / 'nodes.jsonl'
        self.edges_file = Path(self.tmp_dir) / 'edges.jsonl'
        self.policies_file = Path(self.tmp_dir) / 'policies.jsonl'

        self.kg = KnowledgeGraph(
            nodes_file=str(self.nodes_file),
            edges_file=str(self.edges_file),
            policies_file=str(self.policies_file)
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_add_node_cve(self):
        """Test adding a CVE node."""
        node = self.kg.add_node('cve', 'CVE-2024-3094', TEST_CVE)
        self.assertIsNotNone(node)
        self.assertEqual(node['entity_type'], 'cve')
        self.assertEqual(node['entity_id'], 'CVE-2024-3094')
        self.assertEqual(node['properties']['description'], TEST_CVE['description'])

    def test_add_node_actor(self):
        """Test adding an actor node."""
        node = self.kg.add_node('actor', 'muddywater', TEST_ACTOR)
        self.assertIsNotNone(node)
        self.assertEqual(node['entity_type'], 'actor')
        self.assertEqual(node['entity_id'], 'muddywater')

    def test_get_node(self):
        """Test retrieving a node by ID."""
        node = self.kg.add_node('cve', 'CVE-2024-3094', TEST_CVE)
        retrieved = self.kg.get_node(node['node_id'])
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['entity_id'], 'CVE-2024-3094')

    def test_get_node_by_entity(self):
        """Test retrieving a node by entity type and ID."""
        self.kg.add_node('cve', 'CVE-2024-3094', TEST_CVE)
        node = self.kg.get_node_by_entity('cve', 'CVE-2024-3094')
        self.assertIsNotNone(node)

    def test_add_edge(self):
        """Test adding an edge between nodes."""
        cve = self.kg.add_node('cve', 'CVE-2024-3094', TEST_CVE)
        actor = self.kg.add_node('actor', 'muddywater', TEST_ACTOR)

        edge = self.kg.add_edge(
            'actor', 'muddywater',
            'cve', 'CVE-2024-3094',
            'EXPLOITS'
        )
        self.assertIsNotNone(edge)
        self.assertEqual(edge['relationship_type'], 'EXPLOITS')
        self.assertEqual(edge['from_node_id'], actor['node_id'])
        self.assertEqual(edge['to_node_id'], cve['node_id'])

    def test_get_edges_from(self):
        """Test getting edges from a node."""
        cve = self.kg.add_node('cve', 'CVE-2024-3094', TEST_CVE)
        actor = self.kg.add_node('actor', 'muddywater', TEST_ACTOR)
        self.kg.add_edge('actor', 'muddywater', 'cve', 'CVE-2024-3094', 'EXPLOITS')

        edges = self.kg.get_edges_from(actor['node_id'])
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]['relationship_type'], 'EXPLOITS')

    def test_traverse_from(self):
        """Test graph traversal from a node."""
        cve = self.kg.add_node('cve', 'CVE-2024-3094', TEST_CVE)
        actor = self.kg.add_node('actor', 'muddywater', TEST_ACTOR)
        self.kg.add_edge('actor', 'muddywater', 'cve', 'CVE-2024-3094', 'EXPLOITS')

        neighbors = self.kg.traverse_from('actor', 'muddywater', max_depth=1)
        self.assertGreater(len(neighbors), 0)

    def test_stats(self):
        """Test graph statistics."""
        self.kg.add_node('cve', 'CVE-2024-3094', TEST_CVE)
        self.kg.add_node('actor', 'muddywater', TEST_ACTOR)
        self.kg.add_edge('actor', 'muddywater', 'cve', 'CVE-2024-3094', 'EXPLOITS')

        stats = self.kg.stats()
        self.assertEqual(stats['total_nodes'], 2)
        self.assertEqual(stats['total_edges'], 1)

    def test_persistence(self):
        """Test that graph data persists to disk."""
        # Create and add data
        self.kg.add_node('cve', 'CVE-2024-3094', TEST_CVE)
        self.kg.add_edge('actor', 'muddywater', 'cve', 'CVE-2024-3094', 'EXPLOITS')

        # Reload from disk
        new_kg = KnowledgeGraph(
            nodes_file=str(self.nodes_file),
            edges_file=str(self.edges_file),
            policies_file=str(self.policies_file)
        )

        # Verify data persisted
        node = new_kg.get_node_by_entity('cve', 'CVE-2024-3094')
        self.assertIsNotNone(node)


class TestOntologyValidator(unittest.TestCase):
    """Test ontology validation logic."""

    def setUp(self):
        """Set up validator."""
        self.validator = OntologyValidator()

    def test_validate_cve(self):
        """Test CVE validation."""
        valid, errors = self.validator.validate_cve('CVE-2024-3094', TEST_CVE)
        self.assertTrue(valid)

    def test_validate_cve_invalid_format(self):
        """Test CVE validation with invalid format."""
        valid, errors = self.validator.validate_cve('INVALID', TEST_CVE)
        self.assertFalse(valid)
        self.assertTrue(len(errors) > 0)

    def test_validate_actor(self):
        """Test actor validation."""
        valid, errors = self.validator.validate_actor('muddywater', TEST_ACTOR)
        self.assertTrue(valid)

    def test_validate_hasl(self):
        """Test HASL validation."""
        hasl = TEST_IEP_POLICY['hasl']
        valid, errors = self.validator.validate_hasl(hasl)
        self.assertTrue(valid)

    def test_validate_hasl_invalid_handling(self):
        """Test HASL validation with invalid handling."""
        hasl = TEST_IEP_POLICY['hasl'].copy()
        hasl['handling'] = 'INVALID'
        valid, errors = self.validator.validate_hasl(hasl)
        self.assertFalse(valid)
        self.assertTrue(len(errors) > 0)

    def test_validate_policy(self):
        """Test IEP policy validation."""
        valid, errors = self.validator.validate_policy(
            TEST_IEP_POLICY['policy_id'],
            TEST_IEP_POLICY
        )
        self.assertTrue(valid)

    def test_validate_relationship(self):
        """Test relationship type validation."""
        valid, errors = self.validator.validate_relationship(
            'actor', 'cve', 'EXPLOITS'
        )
        self.assertTrue(valid)

    def test_validate_edge(self):
        """Test complete edge validation."""
        valid, errors = self.validator.validate_edge(
            'actor', 'muddywater',
            'cve', 'CVE-2024-3094',
            'EXPLOITS'
        )
        self.assertTrue(valid)


class TestIEPManager(unittest.TestCase):
    """Test IEP 2.0 policy management."""

    def setUp(self):
        """Set up IEP manager."""
        self.tmp_dir = tempfile.mkdtemp()
        self.policy_file = Path(self.tmp_dir) / 'policies.jsonl'
        self.kg_tmp = tempfile.mkdtemp()
        self.kg = KnowledgeGraph(
            nodes_file=str(Path(self.kg_tmp) / 'nodes.jsonl'),
            edges_file=str(Path(self.kg_tmp) / 'edges.jsonl'),
            policies_file=str(Path(self.kg_tmp) / 'policies.jsonl')
        )
        self.manager = IEPManager(kg=self.kg, policy_file=str(self.policy_file))

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        shutil.rmtree(self.kg_tmp, ignore_errors=True)

    def test_create_policy(self):
        """Test creating a policy."""
        policy = self.manager.create_policy(
            policy_id='IEP-US-0001',
            name='US Gov Test',
            hasl=TEST_IEP_POLICY['hasl'],
            created_by='admin'
        )
        self.assertIsNotNone(policy)
        self.assertEqual(policy['policy_id'], 'IEP-US-0001')
        self.assertEqual(policy['name'], 'US Gov Test')

    def test_create_policy_invalid_id(self):
        """Test creating a policy with invalid ID."""
        with self.assertRaises(ValueError):
            self.manager.create_policy(
                policy_id='INVALID',
                name='Test',
                hasl=TEST_IEP_POLICY['hasl']
            )

    def test_create_policy_missing_hasl(self):
        """Test creating a policy with missing HASL fields."""
        with self.assertRaises(ValueError):
            self.manager.create_policy(
                policy_id='IEP-US-0001',
                name='Test',
                hasl={'handling': 'OPEN'}  # Missing fields
            )

    def test_create_tlp_policy(self):
        """Test creating a TLP-based policy."""
        policy = self.manager.create_tlp_policy(
            tlp_level='TLP_GREEN',
            name='Share with Partners',
            country='US',
            created_by='admin'
        )
        self.assertIsNotNone(policy)
        self.assertEqual(policy['hasl']['handling'], 'RESTRICTED')
        self.assertEqual(policy['hasl']['sharing'], 'TLP_GREEN')

    def test_list_policies(self):
        """Test listing policies."""
        self.manager.create_policy(
            policy_id='IEP-US-0001',
            name='Policy 1',
            hasl=TEST_IEP_POLICY['hasl'],
            created_by='admin'
        )
        self.manager.create_policy(
            policy_id='IEP-US-0002',
            name='Policy 2',
            hasl=TEST_IEP_POLICY['hasl'],
            created_by='admin'
        )

        policies = self.manager.list_policies()
        self.assertEqual(len(policies), 2)

    def test_check_compliance(self):
        """Test compliance checking."""
        self.manager.create_policy(
            policy_id='IEP-US-0001',
            name='Read Only',
            hasl={
                'handling': 'OPEN',
                'action': 'READ',
                'sharing': 'TLP_WHITE',
                'licensing': 'CC0'
            },
            created_by='admin'
        )

        # Should be compliant
        compliant, violations = self.manager.check_compliance('actor', 'muddywater', 'READ')
        self.assertTrue(compliant)
        self.assertEqual(len(violations), 0)

    def test_check_compliance_violation(self):
        """Test compliance violation detection."""
        self.manager.create_policy(
            policy_id='IEP-US-0001',
            name='Read Only',
            hasl={
                'handling': 'OPEN',
                'action': 'READ',
                'sharing': 'TLP_WHITE',
                'licensing': 'CC0'
            },
            created_by='admin'
        )

        # ADMIN should violate READ-only policy
        compliant, violations = self.manager.check_compliance('actor', 'muddywater', 'ADMIN')
        self.assertFalse(compliant)
        self.assertGreater(len(violations), 0)

    def test_get_active_policies(self):
        """Test getting active policies."""
        self.manager.create_policy(
            policy_id='IEP-US-0001',
            name='Active Policy',
            hasl=TEST_IEP_POLICY['hasl'],
            created_by='admin'
        )

        active = self.manager.get_active_policies()
        self.assertEqual(len(active), 1)

    def test_stats(self):
        """Test policy statistics."""
        self.manager.create_policy(
            policy_id='IEP-US-0001',
            name='Policy 1',
            hasl=TEST_IEP_POLICY['hasl'],
            created_by='admin'
        )

        stats = self.manager.stats()
        self.assertEqual(stats['total_policies'], 1)
        self.assertEqual(stats['active_policies'], 1)


class TestGraphRetriever(unittest.TestCase):
    """Test graph-based retrieval."""

    def setUp(self):
        """Set up retriever."""
        self.tmp_dir = tempfile.mkdtemp()
        self.kg = KnowledgeGraph(
            nodes_file=str(Path(self.tmp_dir) / 'nodes.jsonl'),
            edges_file=str(Path(self.tmp_dir) / 'edges.jsonl'),
            policies_file=str(Path(self.tmp_dir) / 'policies.jsonl')
        )
        self.retriever = GraphRetriever(kg=self.kg)

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_recall(self):
        """Test basic recall."""
        self.kg.add_node('cve', 'CVE-2024-3094', TEST_CVE)
        results = self.retriever.recall('CVE-2024-3094', k=5)
        self.assertGreater(len(results), 0)

    def test_expand(self):
        """Test neighbor expansion."""
        cve = self.kg.add_node('cve', 'CVE-2024-3094', TEST_CVE)
        actor = self.kg.add_node('actor', 'muddywater', TEST_ACTOR)
        self.kg.add_edge('actor', 'muddywater', 'cve', 'CVE-2024-3094', 'EXPLOITS')

        expanded = self.retriever.expand('actor', 'muddywater', depth=1)
        self.assertIsNotNone(expanded)
        self.assertGreater(len(expanded.get('neighbors', [])), 0)

    def test_recall_with_path(self):
        """Test path-based recall - find path between two known entities."""
        cve = self.kg.add_node('cve', 'CVE-2024-3094', TEST_CVE)
        actor = self.kg.add_node('actor', 'muddywater', TEST_ACTOR)
        self.kg.add_edge('actor', 'muddywater', 'cve', 'CVE-2024-3094', 'EXPLOITS')

        # Path is from actor to CVE - type is guessed from entity names
        path = self.retriever.recall_with_path('muddywater', 'CVE-2024-3094')
        self.assertIsNotNone(path)
        self.assertGreater(len(path['path']), 0)

    def test_traverse_from(self):
        """Test traversal from a node."""
        cve = self.kg.add_node('cve', 'CVE-2024-3094', TEST_CVE)
        actor = self.kg.add_node('actor', 'muddywater', TEST_ACTOR)
        self.kg.add_edge('actor', 'muddywater', 'cve', 'CVE-2024-3094', 'EXPLOITS')

        traversal = self.retriever.traverse_from('actor', 'muddywater', max_depth=2)
        self.assertGreater(len(traversal), 0)

    def test_stats(self):
        """Test retriever statistics."""
        stats = self.retriever.stats()
        self.assertIn('total_nodes', stats)
        self.assertIn('total_edges', stats)


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration(unittest.TestCase):
    """Integration tests across components."""

    def setUp(self):
        """Set up integration test fixtures."""
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_full_workflow(self):
        """Test complete workflow: create -> validate -> store -> retrieve."""
        # Create knowledge graph
        kg = KnowledgeGraph(
            nodes_file=str(Path(self.tmp_dir) / 'nodes.jsonl'),
            edges_file=str(Path(self.tmp_dir) / 'edges.jsonl'),
            policies_file=str(Path(self.tmp_dir) / 'policies.jsonl')
        )

        # Create validator
        validator = OntologyValidator()

        # Create IEP manager
        iep_file = Path(self.tmp_dir) / 'iep_policies.jsonl'
        iep_manager = IEPManager(kg=kg, policy_file=str(iep_file))

        # Create retriever
        retriever = GraphRetriever(kg=kg)

        # Step 1: Add entities
        cve = kg.add_node('cve', 'CVE-2024-3094', TEST_CVE)
        actor = kg.add_node('actor', 'muddywater', TEST_ACTOR)
        tool = kg.add_node('tool', 'cobalt_strike', TEST_TOOL)

        # Step 2: Add relationships
        kg.add_edge('actor', 'muddywater', 'cve', 'CVE-2024-3094', 'EXPLOITS')
        kg.add_edge('actor', 'muddywater', 'tool', 'cobalt_strike', 'USES')

        # Step 3: Create policy
        policy = iep_manager.create_policy(
            policy_id='IEP-US-0001',
            name='US Gov Threat Intel',
            hasl={
                'handling': 'RESTRICTED',
                'action': 'READ',
                'sharing': 'TLP_GREEN',
                'licensing': 'CC-BY'
            },
            created_by='admin'
        )

        # Step 4: Apply policy to entities
        iep_manager.apply_policy('IEP-US-0001', 'actor', 'muddywater')

        # Step 5: Verify retrieval
        results = retriever.recall('muddywater', k=5)
        self.assertGreater(len(results), 0)

        # Step 6: Check compliance
        compliant, violations = iep_manager.check_compliance('actor', 'muddywater', 'READ')
        self.assertTrue(compliant)

        # Step 7: Verify graph stats
        stats = kg.stats()
        self.assertEqual(stats['total_nodes'], 3)
        self.assertEqual(stats['total_edges'], 2)

        # Step 8: Verify IEP stats
        iep_stats = iep_manager.stats()
        self.assertEqual(iep_stats['total_policies'], 1)


def run_all_tests():
    """Run all Phase 6 tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestOntologySchema))
    suite.addTests(loader.loadTestsFromTestCase(TestKnowledgeGraph))
    suite.addTests(loader.loadTestsFromTestCase(TestOntologyValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestIEPManager))
    suite.addTests(loader.loadTestsFromTestCase(TestGraphRetriever))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
