"""
Phase 6 Tests — Temporal Knowledge Graph
=========================================

Test suite for Phase 6 temporal knowledge graph implementation:
- Event management with timestamps
- Temporal relationships (PRECEDES, FOLLOWS, CAUSES, etc.)
- Time-based queries
- Event chains and timeline reconstruction
- Temporal pattern detection

Usage:
    python test_phase_6_temporal.py

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
from memory.knowledge_graph import KnowledgeGraph
from memory.temporal_knowledge_graph import (
    TemporalKnowledgeGraph,
    TemporalRelationship,
    EventType,
    get_temporal_knowledge_graph
)
from memory.temporal_graph_retriever import TemporalGraphRetriever


# =============================================================================
# Test Data
# =============================================================================

TEST_EVENTS = [
    {
        'event_id': 'recon_001',
        'event_type': 'reconnaissance',
        'timestamp': '2024-03-15T08:00:00Z',
        'technique': 'T1595',
        'actor': 'apt28'
    },
    {
        'event_id': 'initial_access_001',
        'event_type': 'initial_access',
        'timestamp': '2024-03-15T09:30:00Z',
        'technique': 'T1566.001',
        'actor': 'apt28'
    },
    {
        'event_id': 'execution_001',
        'event_type': 'execution',
        'timestamp': '2024-03-15T10:15:00Z',
        'technique': 'T1059.001',
        'actor': 'apt28'
    },
    {
        'event_id': 'persistence_001',
        'event_type': 'persistence',
        'timestamp': '2024-03-15T11:00:00Z',
        'technique': 'T1547.001',
        'actor': 'apt28'
    },
    {
        'event_id': 'c2_001',
        'event_type': 'command_and_control',
        'timestamp': '2024-03-15T12:30:00Z',
        'technique': 'T1071.001',
        'actor': 'apt28'
    },
    {
        'event_id': 'exfil_001',
        'event_type': 'exfiltration',
        'timestamp': '2024-03-15T14:00:00Z',
        'technique': 'T1041',
        'actor': 'apt28'
    }
]


# =============================================================================
# Temporal Knowledge Graph Tests
# =============================================================================

class TestTemporalKnowledgeGraph(unittest.TestCase):
    """Test temporal knowledge graph core functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tmp_dir = tempfile.mkdtemp()
        self.kg = KnowledgeGraph(
            nodes_file=str(Path(self.tmp_dir) / 'nodes.jsonl'),
            edges_file=str(Path(self.tmp_dir) / 'edges.jsonl'),
            policies_file=str(Path(self.tmp_dir) / 'policies.jsonl')
        )
        self.tkg = TemporalKnowledgeGraph(
            kg=self.kg,
            temporal_edges_file=str(Path(self.tmp_dir) / 'temporal_edges.jsonl')
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
    
    def test_add_event(self):
        """Test adding an event with timestamp."""
        event = self.tkg.add_event(
            event_id='test_event_001',
            event_type='initial_access',
            timestamp='2024-03-15T09:30:00Z',
            properties={'technique': 'T1566.001'}
        )
        self.assertIsNotNone(event)
        self.assertEqual(event['entity_type'], 'event')
        self.assertEqual(event['entity_id'], 'test_event_001')
        self.assertEqual(event['properties']['event_type'], 'initial_access')
    
    def test_get_event(self):
        """Test retrieving an event."""
        self.tkg.add_event(
            event_id='test_event_002',
            event_type='execution',
            timestamp='2024-03-15T10:00:00Z'
        )
        event = self.tkg.get_event('test_event_002')
        self.assertIsNotNone(event)
        self.assertEqual(event['properties']['event_type'], 'execution')
    
    def test_get_event_timestamp(self):
        """Test getting parsed timestamp for an event."""
        self.tkg.add_event(
            event_id='test_event_003',
            event_type='persistence',
            timestamp='2024-03-15T11:30:00Z'
        )
        ts = self.tkg.get_event_timestamp('test_event_003')
        self.assertIsNotNone(ts)
        self.assertIsInstance(ts, datetime)
    
    def test_add_temporal_edge_precedes(self):
        """Test adding PRECEDES temporal relationship."""
        self.tkg.add_event('event_a', 'initial_access', '2024-03-15T09:00:00Z')
        self.tkg.add_event('event_b', 'execution', '2024-03-15T10:00:00Z')
        
        edge = self.tkg.add_temporal_edge('event_a', 'event_b', TemporalRelationship.PRECEDES)
        self.assertIsNotNone(edge)
        self.assertEqual(edge['relationship_type'], 'PRECEDES')
        self.assertEqual(edge['from_event_id'], 'event_a')
        self.assertEqual(edge['to_event_id'], 'event_b')
    
    def test_add_temporal_edge_causes(self):
        """Test adding CAUSES temporal relationship."""
        self.tkg.add_event('cause_event', 'initial_access', '2024-03-15T09:00:00Z')
        self.tkg.add_event('effect_event', 'execution', '2024-03-15T10:00:00Z')
        
        edge = self.tkg.add_temporal_edge('cause_event', 'effect_event', TemporalRelationship.CAUSES)
        self.assertIsNotNone(edge)
        self.assertEqual(edge['relationship_type'], 'CAUSES')
    
    def test_temporal_consistency_validation(self):
        """Test that temporal relationships enforce chronological consistency."""
        self.tkg.add_event('event_1', 'execution', '2024-03-15T10:00:00Z')
        self.tkg.add_event('event_2', 'initial_access', '2024-03-15T09:00:00Z')
        
        # PRECEDES should fail if from_time >= to_time
        with self.assertRaises(ValueError):
            self.tkg.add_temporal_edge('event_1', 'event_2', TemporalRelationship.PRECEDES)
    
    def test_get_preceding_events(self):
        """Test retrieving events that precede a given event."""
        # Create chain: A -> B -> C
        self.tkg.add_event('chain_a', 'reconnaissance', '2024-03-15T08:00:00Z')
        self.tkg.add_event('chain_b', 'initial_access', '2024-03-15T09:00:00Z')
        self.tkg.add_event('chain_c', 'execution', '2024-03-15T10:00:00Z')
        
        self.tkg.add_temporal_edge('chain_a', 'chain_b', TemporalRelationship.PRECEDES)
        self.tkg.add_temporal_edge('chain_b', 'chain_c', TemporalRelationship.PRECEDES)
        
        preceding = self.tkg.get_preceding_events('chain_c')
        self.assertEqual(len(preceding), 2)  # chain_a and chain_b
    
    def test_get_following_events(self):
        """Test retrieving events that follow a given event."""
        # Create chain: A -> B -> C
        self.tkg.add_event('chain_x', 'reconnaissance', '2024-03-15T08:00:00Z')
        self.tkg.add_event('chain_y', 'initial_access', '2024-03-15T09:00:00Z')
        self.tkg.add_event('chain_z', 'execution', '2024-03-15T10:00:00Z')
        
        self.tkg.add_temporal_edge('chain_x', 'chain_y', TemporalRelationship.PRECEDES)
        self.tkg.add_temporal_edge('chain_y', 'chain_z', TemporalRelationship.PRECEDES)
        
        following = self.tkg.get_following_events('chain_x')
        self.assertEqual(len(following), 2)  # chain_y and chain_z
    
    def test_get_event_chain(self):
        """Test retrieving complete event chain."""
        # Create chain
        events = [
            ('link_1', 'reconnaissance', '2024-03-15T08:00:00Z'),
            ('link_2', 'initial_access', '2024-03-15T09:00:00Z'),
            ('link_3', 'execution', '2024-03-15T10:00:00Z'),
            ('link_4', 'persistence', '2024-03-15T11:00:00Z'),
        ]
        
        for i, (eid, etype, ts) in enumerate(events):
            self.tkg.add_event(eid, etype, ts)
            if i > 0:
                self.tkg.add_temporal_edge(events[i-1][0], eid, TemporalRelationship.PRECEDES)
        
        chain = self.tkg.get_event_chain('link_2')
        self.assertEqual(len(chain), 4)  # All events in chain
        
        # Verify order
        event_ids = [e['properties']['event_id'] for e in chain]
        self.assertEqual(event_ids, ['link_1', 'link_2', 'link_3', 'link_4'])
    
    def test_get_events_before(self):
        """Test retrieving events before a timestamp."""
        for event_data in TEST_EVENTS:
            self.tkg.add_event(
                event_data['event_id'],
                event_data['event_type'],
                event_data['timestamp'],
                {k: v for k, v in event_data.items() if k not in ['event_id', 'event_type', 'timestamp']}
            )
        
        events = self.tkg.get_events_before('2024-03-15T11:00:00Z')
        self.assertGreater(len(events), 0)
        
        # All returned events should be before 11:00
        for event in events:
            ts = datetime.fromisoformat(event['properties']['timestamp'].replace('Z', '+00:00'))
            self.assertLess(ts, datetime.fromisoformat('2024-03-15T11:00:00+00:00'))
    
    def test_get_events_after(self):
        """Test retrieving events after a timestamp."""
        for event_data in TEST_EVENTS:
            self.tkg.add_event(
                event_data['event_id'],
                event_data['event_type'],
                event_data['timestamp'],
                {k: v for k, v in event_data.items() if k not in ['event_id', 'event_type', 'timestamp']}
            )
        
        events = self.tkg.get_events_after('2024-03-15T09:00:00Z')
        self.assertGreater(len(events), 0)
        
        # All returned events should be after 09:00
        for event in events:
            ts = datetime.fromisoformat(event['properties']['timestamp'].replace('Z', '+00:00'))
            self.assertGreater(ts, datetime.fromisoformat('2024-03-15T09:00:00+00:00'))
    
    def test_get_events_between(self):
        """Test retrieving events within a time range."""
        for event_data in TEST_EVENTS:
            self.tkg.add_event(
                event_data['event_id'],
                event_data['event_type'],
                event_data['timestamp']
            )
        
        events = self.tkg.get_events_between('2024-03-15T09:00:00Z', '2024-03-15T12:00:00Z')
        self.assertGreater(len(events), 0)
        self.assertLessEqual(len(events), 4)  # Should get events in that range
    
    def test_get_events_by_date(self):
        """Test retrieving events on a specific date."""
        for event_data in TEST_EVENTS:
            self.tkg.add_event(
                event_data['event_id'],
                event_data['event_type'],
                event_data['timestamp']
            )
        
        events = self.tkg.get_events_by_date('2024-03-15')
        self.assertEqual(len(events), 6)  # All test events
    
    def test_build_timeline(self):
        """Test building a timeline from events."""
        event_ids = []
        for event_data in TEST_EVENTS[:3]:
            self.tkg.add_event(
                event_data['event_id'],
                event_data['event_type'],
                event_data['timestamp']
            )
            event_ids.append(event_data['event_id'])
        
        timeline = self.tkg.build_timeline(event_ids)
        self.assertEqual(timeline['event_count'], 3)
        self.assertIsNotNone(timeline['start_time'])
        self.assertIsNotNone(timeline['end_time'])
    
    def test_infer_temporal_edges(self):
        """Test automatic inference of temporal edges."""
        # Add events out of order
        self.tkg.add_event('auto_c', 'execution', '2024-03-15T10:00:00Z')
        self.tkg.add_event('auto_a', 'reconnaissance', '2024-03-15T08:00:00Z')
        self.tkg.add_event('auto_b', 'initial_access', '2024-03-15T09:00:00Z')
        
        edges = self.tkg.infer_temporal_edges()
        self.assertGreater(len(edges), 0)  # Should create edges
    
    def test_detect_temporal_patterns(self):
        """Test detection of temporal patterns."""
        # Create fan-out pattern: A -> B, A -> C
        self.tkg.add_event('fan_a', 'initial_access', '2024-03-15T09:00:00Z')
        self.tkg.add_event('fan_b', 'execution', '2024-03-15T10:00:00Z')
        self.tkg.add_event('fan_c', 'persistence', '2024-03-15T10:30:00Z')
        
        self.tkg.add_temporal_edge('fan_a', 'fan_b', TemporalRelationship.PRECEDES)
        self.tkg.add_temporal_edge('fan_a', 'fan_c', TemporalRelationship.PRECEDES)
        
        patterns = self.tkg.detect_temporal_patterns()
        fan_out_patterns = [p for p in patterns if p['type'] == 'fan_out']
        self.assertEqual(len(fan_out_patterns), 1)
    
    def test_temporal_edge_inverse(self):
        """Test that inverse temporal edges are created automatically."""
        self.tkg.add_event('inv_a', 'initial_access', '2024-03-15T09:00:00Z')
        self.tkg.add_event('inv_b', 'execution', '2024-03-15T10:00:00Z')
        
        self.tkg.add_temporal_edge('inv_a', 'inv_b', TemporalRelationship.PRECEDES)
        
        # Check inverse edge was created
        edges_to_a = self.tkg.get_temporal_edges_to('inv_a')
        self.assertTrue(any(e['relationship_type'] == 'FOLLOWS' for e in edges_to_a))
        
        edges_from_b = self.tkg.get_temporal_edges_from('inv_b')
        self.assertTrue(any(e['relationship_type'] == 'FOLLOWS' for e in edges_from_b))
    
    def test_stats(self):
        """Test statistics reporting."""
        self.tkg.add_event('stats_1', 'initial_access', '2024-03-15T09:00:00Z')
        self.tkg.add_event('stats_2', 'execution', '2024-03-15T10:00:00Z')
        self.tkg.add_temporal_edge('stats_1', 'stats_2', TemporalRelationship.PRECEDES)
        
        stats = self.tkg.stats()
        self.assertIn('temporal_edges', stats)
        self.assertIn('events_with_temporal_data', stats)
        self.assertGreaterEqual(stats['temporal_edges'], 2)  # Edge + inverse
    
    def test_persistence(self):
        """Test that temporal edges persist to disk."""
        self.tkg.add_event('persist_1', 'initial_access', '2024-03-15T09:00:00Z')
        self.tkg.add_event('persist_2', 'execution', '2024-03-15T10:00:00Z')
        self.tkg.add_temporal_edge('persist_1', 'persist_2', TemporalRelationship.PRECEDES)
        
        # Create new instance pointing to same files
        tkg2 = TemporalKnowledgeGraph(
            kg=self.kg,
            temporal_edges_file=self.tkg.temporal_edges_file
        )
        
        edges = tkg2.get_temporal_edges_from('persist_1')
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]['relationship_type'], 'PRECEDES')


# =============================================================================
# Temporal Graph Retriever Tests
# =============================================================================

class TestTemporalGraphRetriever(unittest.TestCase):
    """Test temporal graph retriever functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tmp_dir = tempfile.mkdtemp()
        self.kg = KnowledgeGraph(
            nodes_file=str(Path(self.tmp_dir) / 'nodes.jsonl'),
            edges_file=str(Path(self.tmp_dir) / 'edges.jsonl'),
            policies_file=str(Path(self.tmp_dir) / 'policies.jsonl')
        )
        self.tkg = TemporalKnowledgeGraph(
            kg=self.kg,
            temporal_edges_file=str(Path(self.tmp_dir) / 'temporal_edges.jsonl')
        )
        self.retriever = TemporalGraphRetriever(kg=self.kg, tkg=self.tkg)
        
        # Add test events
        for event_data in TEST_EVENTS:
            self.tkg.add_event(
                event_data['event_id'],
                event_data['event_type'],
                event_data['timestamp'],
                {k: v for k, v in event_data.items() if k not in ['event_id', 'event_type', 'timestamp']}
            )
        
        # Create temporal chain
        for i in range(len(TEST_EVENTS) - 1):
            self.tkg.add_temporal_edge(
                TEST_EVENTS[i]['event_id'],
                TEST_EVENTS[i + 1]['event_id'],
                TemporalRelationship.PRECEDES
            )
    
    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
    
    def test_get_events_between(self):
        """Test retriever get_events_between."""
        events = self.retriever.get_events_between(
            '2024-03-15T09:00:00Z',
            '2024-03-15T12:00:00Z'
        )
        self.assertGreater(len(events), 0)
    
    def test_get_events_between_with_filter(self):
        """Test get_events_between with event type filter."""
        events = self.retriever.get_events_between(
            '2024-03-15T08:00:00Z',
            '2024-03-15T15:00:00Z',
            event_types=['initial_access', 'execution']
        )
        self.assertGreater(len(events), 0)
        for event in events:
            self.assertIn(event['properties']['event_type'], ['initial_access', 'execution'])
    
    def test_get_event_chain(self):
        """Test retrieving event chain via retriever."""
        chain = self.retriever.get_event_chain('initial_access_001')
        self.assertIn('events', chain)
        self.assertIn('edges', chain)
        self.assertGreater(chain['length'], 0)
    
    def test_get_attack_chain(self):
        """Test retrieving attack chain."""
        chain = self.retriever.get_attack_chain('initial_access_001')
        self.assertGreater(len(chain), 0)
        
        # All should be attack-related events
        attack_types = ['initial_access', 'execution', 'persistence', 'command_and_control', 'exfiltration']
        for entry in chain:
            self.assertIn(entry['event']['properties']['event_type'], attack_types)
    
    def test_get_causal_ancestors(self):
        """Test finding causal ancestors."""
        # Add causal relationship
        self.tkg.add_temporal_edge('recon_001', 'initial_access_001', TemporalRelationship.CAUSES)
        
        ancestors = self.retriever.get_causal_ancestors('initial_access_001')
        self.assertGreater(len(ancestors), 0)
        
        ancestor_ids = [a['event']['properties']['event_id'] for a in ancestors]
        self.assertIn('recon_001', ancestor_ids)
    
    def test_get_causal_descendants(self):
        """Test finding causal descendants."""
        # Add causal relationship
        self.tkg.add_temporal_edge('initial_access_001', 'execution_001', TemporalRelationship.CAUSES)
        
        descendants = self.retriever.get_causal_descendants('initial_access_001', max_depth=2)
        self.assertGreater(len(descendants), 0)
    
    def test_find_root_causes(self):
        """Test finding root cause events."""
        # Create chain: A -> B -> C (all causal)
        self.tkg.add_temporal_edge('recon_001', 'initial_access_001', TemporalRelationship.CAUSES)
        self.tkg.add_temporal_edge('initial_access_001', 'execution_001', TemporalRelationship.CAUSES)
        
        root_causes = self.retriever.find_root_causes('execution_001')
        
        # recon_001 should be a root cause (no further ancestors)
        root_ids = [rc['event']['properties']['event_id'] for rc in root_causes]
        self.assertIn('recon_001', root_ids)
    
    def test_reconstruct_timeline(self):
        """Test timeline reconstruction."""
        timeline = self.retriever.reconstruct_timeline()
        
        self.assertIn('events', timeline)
        self.assertIn('phases', timeline)
        self.assertIn('metrics', timeline)
        
        self.assertEqual(len(timeline['events']), 6)  # All test events
        self.assertGreater(len(timeline['phases']), 0)
    
    def test_query_interface(self):
        """Test unified query interface."""
        result = self.retriever.query('events_between', start_time='2024-03-15T09:00:00Z', end_time='2024-03-15T12:00:00Z')
        self.assertIn('events', result)
        self.assertGreater(len(result['events']), 0)
    
    def test_stats(self):
        """Test retriever statistics."""
        stats = self.retriever.stats()
        self.assertIn('total_events', stats)
        self.assertIn('event_type_distribution', stats)
        self.assertEqual(stats['total_events'], 6)


# =============================================================================
# Integration Tests
# =============================================================================

class TestTemporalIntegration(unittest.TestCase):
    """Integration tests for temporal knowledge graph."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tmp_dir = tempfile.mkdtemp()
        self.kg = KnowledgeGraph(
            nodes_file=str(Path(self.tmp_dir) / 'nodes.jsonl'),
            edges_file=str(Path(self.tmp_dir) / 'edges.jsonl'),
            policies_file=str(Path(self.tmp_dir) / 'policies.jsonl')
        )
        self.tkg = TemporalKnowledgeGraph(
            kg=self.kg,
            temporal_edges_file=str(Path(self.tmp_dir) / 'temporal_edges.jsonl')
        )
        self.retriever = TemporalGraphRetriever(kg=self.kg, tkg=self.tkg)
    
    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
    
    def test_full_attack_lifecycle(self):
        """Test complete attack lifecycle with temporal relationships."""
        # Simulate complete attack chain
        attack_events = [
            ('recon', 'reconnaissance', '2024-03-15T08:00:00Z', None),
            ('phishing', 'initial_access', '2024-03-15T09:30:00Z', 'T1566.001'),
            ('macro_exec', 'execution', '2024-03-15T09:32:00Z', 'T1059.001'),
            ('reg_persist', 'persistence', '2024-03-15T09:45:00Z', 'T1547.001'),
            ('token_steal', 'credential_access', '2024-03-15T10:00:00Z', 'T1003.001'),
            ('ps_exec', 'lateral_movement', '2024-03-15T10:30:00Z', 'T1021.002'),
            ('c2_beacon', 'command_and_control', '2024-03-15T11:00:00Z', 'T1071.001'),
            ('data_exfil', 'exfiltration', '2024-03-15T14:00:00Z', 'T1041'),
        ]
        
        # Create events
        for eid, etype, ts, technique in attack_events:
            props = {'technique': technique} if technique else {}
            self.tkg.add_event(eid, etype, ts, props)
        
        # Create temporal chain with PRECEDES
        for i in range(len(attack_events) - 1):
            self.tkg.add_temporal_edge(
                attack_events[i][0],
                attack_events[i + 1][0],
                TemporalRelationship.PRECEDES
            )
        
        # Add some causal relationships
        self.tkg.add_temporal_edge('phishing', 'macro_exec', TemporalRelationship.CAUSES)
        self.tkg.add_temporal_edge('token_steal', 'ps_exec', TemporalRelationship.ENABLES)
        
        # Verify chain retrieval
        chain = self.tkg.get_event_chain('phishing')
        # Chain should include most events (may be 7 or 8 depending on traversal)
        self.assertGreaterEqual(len(chain), 6)
        self.assertLessEqual(len(chain), 8)
        
        # Verify timeline reconstruction
        timeline = self.retriever.reconstruct_timeline()
        self.assertEqual(timeline['metrics']['total_events'], 8)
        self.assertEqual(len(timeline['phases']), 8)  # All different phases
        
        # Verify time span calculation
        self.assertIsNotNone(timeline['metrics']['time_span_minutes'])
        self.assertGreater(timeline['metrics']['time_span_minutes'], 0)
    
    def test_concurrent_events(self):
        """Test handling of concurrent events."""
        # Events happening at roughly the same time
        self.tkg.add_event('concurrent_1', 'discovery', '2024-03-15T10:00:00Z')
        self.tkg.add_event('concurrent_2', 'collection', '2024-03-15T10:05:00Z')
        
        edge = self.tkg.add_temporal_edge(
            'concurrent_1', 'concurrent_2', 
            TemporalRelationship.CONCURRENT_WITH
        )
        self.assertIsNotNone(edge)
        
        # Verify both directions
        edges_from = self.tkg.get_temporal_edges_from('concurrent_1')
        self.assertEqual(len(edges_from), 1)
    
    def test_pattern_detection_fan_out(self):
        """Test detection of fan-out pattern."""
        # Create fan-out: A -> B, A -> C, A -> D
        self.tkg.add_event('fan_source', 'initial_access', '2024-03-15T09:00:00Z')
        self.tkg.add_event('fan_target_1', 'execution', '2024-03-15T09:05:00Z')
        self.tkg.add_event('fan_target_2', 'persistence', '2024-03-15T09:10:00Z')
        self.tkg.add_event('fan_target_3', 'defense_evasion', '2024-03-15T09:15:00Z')
        
        self.tkg.add_temporal_edge('fan_source', 'fan_target_1', TemporalRelationship.PRECEDES)
        self.tkg.add_temporal_edge('fan_source', 'fan_target_2', TemporalRelationship.PRECEDES)
        self.tkg.add_temporal_edge('fan_source', 'fan_target_3', TemporalRelationship.PRECEDES)
        
        patterns = self.tkg.detect_temporal_patterns()
        fan_out = [p for p in patterns if p['type'] == 'fan_out']
        
        self.assertEqual(len(fan_out), 1)
        self.assertEqual(fan_out[0]['target_count'], 3)
    
    def test_pattern_detection_fan_in(self):
        """Test detection of fan-in pattern."""
        # Create fan-in: A -> C, B -> C
        self.tkg.add_event('fan_in_1', 'lateral_movement', '2024-03-15T10:00:00Z')
        self.tkg.add_event('fan_in_2', 'collection', '2024-03-15T10:05:00Z')
        self.tkg.add_event('fan_in_target', 'exfiltration', '2024-03-15T10:30:00Z')
        
        self.tkg.add_temporal_edge('fan_in_1', 'fan_in_target', TemporalRelationship.PRECEDES)
        self.tkg.add_temporal_edge('fan_in_2', 'fan_in_target', TemporalRelationship.PRECEDES)
        
        patterns = self.tkg.detect_temporal_patterns()
        fan_in = [p for p in patterns if p['type'] == 'fan_in']
        
        self.assertEqual(len(fan_in), 1)
        self.assertEqual(fan_in[0]['source_count'], 2)


# =============================================================================
# Test Runner
# =============================================================================

def run_all_tests():
    """Run all Phase 6 temporal tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTemporalKnowledgeGraph))
    suite.addTests(loader.loadTestsFromTestCase(TestTemporalGraphRetriever))
    suite.addTests(loader.loadTestsFromTestCase(TestTemporalIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
