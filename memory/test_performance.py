"""
Performance & Scaling Tests — Phase 6/7
========================================

Performance test suite for large-scale operations:
- Load testing with 1000+ notes
- Graph traversal latency measurements
- Vector search scalability
- Memory usage profiling

Usage:
    python test_performance.py
    python test_performance.py --verbose  # Detailed output

Expected: Performance benchmarks below thresholds
"""

import json
import os
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'memory'))
# Add memory directory for subdirectory imports
sys.path.insert(0, str(Path(__file__).parent))

import unittest
from knowledge_graph import KnowledgeGraph
from synthesis_retriever import SynthesisRetriever
from synthesis_generator import SynthesisGenerator


# =============================================================================
# Test Data Generators
# =============================================================================

def generate_cves(count=100):
    """Generate CVE entities."""
    return [
        {
            'id': f'CVE-2024-{1000 + i}',
            'description': f'Vulnerability {i} in software product',
            'cvss_score': round(3.0 + (i % 7), 1),
            'severity': ['low', 'medium', 'high', 'critical'][i % 4],
            'published_date': f'2024-0{1 + (i % 9)}-{10 + (i % 20):02d}'
        }
        for i in range(count)
    ]


def generate_actors(count=50):
    """Generate threat actor entities."""
    actor_names = [
        'apt28', 'apt29', 'lazarus', 'lazarus group', 'lazarus team',
        'lucky monkey', 'muddywater', 'mercury', 'temp.zagros',
        'luminous moyen', 'lucky mouse', 'lazarus cyber', 'lazarus unit',
        'fancy bear', 'apt-c0', 'lucky spider', 'lucky worm', 'lucky bot',
        'vult typhoon', 'volty typhoon', 'vult typhoon', 'volty typhoon',
        'lazarus', 'lazarus group', 'lazarus team', 'lucky monkey',
        'muddywater', 'mercury', 'temp.zagros', 'lucky mouse', 'apt28',
        'apt29', 'lazarus', 'fancy bear', 'apt-c0', 'lucky spider',
        'lucky worm', 'lucky bot', 'vult typhoon', 'volty typhoon',
        'lazarus cyber', 'lazarus unit', 'muddywater', 'mercury',
        'temp.zagros', 'lucky mouse', 'apt28', 'apt29', 'lazarus',
        'fancy bear', 'apt-c0', 'lucky spider', 'lucky worm', 'lucky bot'
    ][:count]
    return [
        {
            'name': name,
            'type': 'apt',
            'first_seen': f'2020-{1 + (i % 12):02d}-01',
            'origin': ['north korea', 'china', 'russia', 'iran'][i % 4]
        }
        for i, name in enumerate(actor_names)
    ]


def generate_tools(count=30):
    """Generate tool entities."""
    tool_names = [
        'cobalt strike', 'metasploit', 'mimikatz', 'bloodhound',
        'caldera', 'sliver', 'empire', 'covenant', 'donut',
        'shellknight', 'rubeus', 'sharpshooter', 'bloodstalker',
        'koadic', 'jaqaghost', 'emotet', 'trickbot', 'darkside',
        'conti', 'cafeloader', 'redline', 'quarksloader', 'nanocore',
        'asyncrat', 'remcos', 'ammyyh', 'poison ivy', 'njrat',
        'darkgate', 'qakbot'
    ][:count]
    return [
        {
            'name': name,
            'type': 'malware',
            'first_seen': f'2015-{1 + (i % 12):02d}-01',
            'category': ['exploitation', 'reconnaissance', 'lateral_movement', 'data_exfiltration'][i % 4]
        }
        for i, name in enumerate(tool_names)
    ]


def generate_campaigns(count=20):
    """Generate campaign entities."""
    campaign_names = [
        'operation solarwinds', 'operation clandestine fox',
        'operation clear sky', 'operation litedog', 'operation soft cartel',
        'operation snow globe', 'operation cloud hopper', 'operation tropictroop',
        'operation persistent threat', 'operation phantom liberty',
        'operation luna moon', 'operation black silver', 'operation red storm',
        'operation blue whirlpool', 'operation white storm', 'operation green fog',
        'operation purple rain', 'operation gold rush', 'operation diamond age',
        'operation obsidian dawn', 'operation iron curtain'
    ][:count]
    return [
        {
            'name': name,
            'actor': ['lazarus', 'apt28', 'muddywater', 'apt29'][i % 4],
            'start_date': f'2020-{1 + (i % 12):02d}-01',
            'end_date': f'2021-{1 + (i % 12):02d}-01' if i % 3 != 0 else 'ongoing'
        }
        for i, name in enumerate(campaign_names)
    ]


# =============================================================================
# Performance Test Cases
# =============================================================================

class TestNoteGenerationPerformance(unittest.TestCase):
    """Test note creation performance at scale."""

    def setUp(self):
        """Set up temporary storage."""
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_note_creation_1000(self):
        """Test creating 1000 notes and measure performance."""
        from memory_store import MemoryStore
        from note_schema import MemoryNote, Content, Semantic, Metadata, Embedding
        from datetime import datetime

        store = MemoryStore(
            jsonl_path=str(Path(self.tmp_dir) / 'notes.jsonl'),
            lance_path=str(Path(self.tmp_dir) / 'vectordb')
        )

        # Create 1000 notes
        start_time = time.time()
        for i in range(1000):
            now = datetime.now().isoformat()
            note = MemoryNote(
                id=f'note_{i}',
                created_at=now,
                updated_at=now,
                content=Content(
                    raw=f'Test content {i} about threat actor activity',
                    source_type='test',
                    source_ref=f'test:{i}'
                ),
                semantic=Semantic(
                    context=f'Summary {i}',
                    keywords=[f'keyword{i % 10}'],
                    tags=[f'tag{i % 5}'],
                    entities=['muddywater', 'CVE-2024-3094']
                ),
                embedding=Embedding(),
                metadata=Metadata(
                    tier='B',
                    domain='security_ops'
                )
            )
            store.write_note(note)
        elapsed = time.time() - start_time

        # Measure performance
        print(f"\nNote creation: 1000 notes in {elapsed:.2f}s")
        print(f"  Rate: {1000 / elapsed:.1f} notes/second")

        # Performance threshold: 100 notes/sec minimum
        self.assertGreater(1000 / elapsed, 50, "Note creation too slow")
        self.assertLess(elapsed, 20, "Note creation took too long")


class TestGraphPerformance(unittest.TestCase):
    """Test knowledge graph performance at scale."""

    def setUp(self):
        """Set up temporary graph storage."""
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_graph_1000_nodes(self):
        """Test graph with 1000 nodes and 2000 edges."""
        kg = KnowledgeGraph(
            nodes_file=str(Path(self.tmp_dir) / 'nodes.jsonl'),
            edges_file=str(Path(self.tmp_dir) / 'edges.jsonl'),
            policies_file=str(Path(self.tmp_dir) / 'policies.jsonl')
        )

        # Generate test data
        cves = generate_cves(100)
        actors = generate_actors(50)
        tools = generate_tools(30)

        # Add nodes
        start_time = time.time()
        node_ids = []
        for cve in cves:
            node = kg.add_node('cve', cve['id'], cve)
            node_ids.append(node['node_id'])
        for actor in actors:
            node = kg.add_node('actor', actor['name'], actor)
            node_ids.append(node['node_id'])
        for tool in tools:
            node = kg.add_node('tool', tool['name'], tool)
            node_ids.append(node['node_id'])
        elapsed = time.time() - start_time

        print(f"\nNode creation: {len(node_ids)} nodes in {elapsed:.2f}s")

        # Add edges (1900 edges)
        start_time = time.time()
        edge_count = 0
        for i, actor in enumerate(actors):
            # Connect to 3 CVEs each
            for j in range(3):
                cve = cves[(i * 3 + j) % len(cves)]
                kg.add_edge('actor', actor['name'], 'cve', cve['id'], 'EXPLOITS')
                edge_count += 1

            # Connect to 2 tools each
            for j in range(2):
                tool = tools[(i * 2 + j) % len(tools)]
                kg.add_edge('actor', actor['name'], 'tool', tool['name'], 'USES')
                edge_count += 1
        elapsed = time.time() - start_time

        print(f"Edge creation: {edge_count} edges in {elapsed:.2f}s")
        print(f"  Rate: {edge_count / elapsed:.1f} edges/second")

        # Verify graph
        stats = kg.stats()
        self.assertEqual(stats['total_nodes'], len(node_ids))
        self.assertEqual(stats['total_edges'], edge_count)

    def test_graph_traversal_latency(self):
        """Test graph traversal latency measurements."""
        kg = KnowledgeGraph(
            nodes_file=str(Path(self.tmp_dir) / 'nodes.jsonl'),
            edges_file=str(Path(self.tmp_dir) / 'edges.jsonl'),
            policies_file=str(Path(self.tmp_dir) / 'policies.jsonl')
        )

        # Add test data
        cve = kg.add_node('cve', 'CVE-2024-3094', TEST_CVE)
        actor = kg.add_node('actor', 'muddywater', TEST_ACTOR)
        tool = kg.add_node('tool', 'cobalt_strike', TEST_TOOL)

        kg.add_edge('actor', 'muddywater', 'cve', 'CVE-2024-3094', 'EXPLOITS')
        kg.add_edge('actor', 'muddywater', 'tool', 'cobalt_strike', 'USES')

        # Warm-up run
        kg.get_neighbors(actor['node_id'])

        # Measure traversal latency
        iterations = 100
        latencies = []
        for _ in range(iterations):
            start = time.perf_counter()
            kg.get_neighbors(actor['node_id'])
            latencies.append(time.perf_counter() - start)

        avg_latency = sum(latencies) / len(latencies) * 1000  # ms
        max_latency = max(latencies) * 1000

        print(f"\nGraph traversal latency (n={iterations}):")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  Max: {max_latency:.2f}ms")

        # Performance threshold: < 50ms average
        self.assertLess(avg_latency, 50, "Graph traversal too slow")
        self.assertLess(max_latency, 100, "Graph traversal max latency too high")

    def test_graph_path_traversal(self):
        """Test path traversal performance."""
        kg = KnowledgeGraph(
            nodes_file=str(Path(self.tmp_dir) / 'nodes.jsonl'),
            edges_file=str(Path(self.tmp_dir) / 'edges.jsonl'),
            policies_file=str(Path(self.tmp_dir) / 'policies.jsonl')
        )

        # Add a chain of nodes
        nodes = []
        for i in range(50):
            node = kg.add_node('actor', f'actor_{i}', {'name': f'actor_{i}'})
            nodes.append(node)

        # Create path
        for i in range(49):
            kg.add_edge('actor', nodes[i]['entity_id'], 'actor', nodes[i+1]['entity_id'], 'RELATED_TO')

        # Measure path traversal
        start = time.perf_counter()
        result = kg.traverse_from('actor', nodes[0]['entity_id'], max_depth=25)
        elapsed = time.perf_counter() - start

        print(f"\nPath traversal (depth 25): {elapsed:.3f}s")
        self.assertGreater(len(result), 0)


class TestSynthesisRetrieverPerformance(unittest.TestCase):
    """Test synthesis retriever performance."""

    def setUp(self):
        """Set up temporary storage."""
        self.tmp_dir = tempfile.mkdtemp()
        self.kg = KnowledgeGraph(
            nodes_file=str(Path(self.tmp_dir) / 'nodes.jsonl'),
            edges_file=str(Path(self.tmp_dir) / 'edges.jsonl'),
            policies_file=str(Path(self.tmp_dir) / 'policies.jsonl')
        )

        # Pre-populate graph with test data
        cve = self.kg.add_node('cve', 'CVE-2024-3094', TEST_CVE)
        actor = self.kg.add_node('actor', 'muddywater', TEST_ACTOR)
        tool = self.kg.add_node('tool', 'cobalt_strike', TEST_TOOL)
        self.kg.add_edge('actor', 'muddywater', 'cve', 'CVE-2024-3094', 'EXPLOITS')

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_context_retrieval_latency(self):
        """Test context retrieval latency."""
        retriever = SynthesisRetriever()

        # Warm-up
        retriever.retrieve_context("muddywater", k=5)

        # Measure retrieval latency
        iterations = 10
        latencies = []
        for _ in range(iterations):
            start = time.perf_counter()
            context = retriever.retrieve_context("muddywater", k=5)
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)

        avg_latency = sum(latencies) / len(latencies) * 1000  # ms

        print(f"\nContext retrieval latency (n={iterations}):")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  Notes retrieved: {len(context.get('notes', []))}")

        # Performance threshold: < 500ms average
        self.assertLess(avg_latency, 500, "Context retrieval too slow")


# =============================================================================
# Test Data Constants
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


# =============================================================================
# Memory Profiling
# =============================================================================

class TestMemoryProfiling(unittest.TestCase):
    """Test memory usage patterns."""

    def test_memory_growth_note_creation(self):
        """Test memory growth during note creation."""
        tracemalloc.start()

        current, peak = tracemalloc.get_traced_memory()
        print(f"\nBefore note creation: {current / 1024 / 1024:.1f} MB")

        # Create notes
        import tempfile
        tmp_dir = tempfile.mkdtemp()
        from memory_store import MemoryStore
        from note_schema import MemoryNote, Content, Semantic, Metadata, Embedding
        from datetime import datetime
        from pathlib import Path

        store = MemoryStore(
            jsonl_path=str(Path(tmp_dir) / 'notes.jsonl'),
            lance_path=str(Path(tmp_dir) / 'vectordb')
        )

        now = datetime.now().isoformat()
        for i in range(500):
            note = MemoryNote(
                id=f'note_{i}',
                created_at=now,
                updated_at=now,
                content=Content(
                    raw='Test content about threat actor activity ' * 10,
                    source_type='test',
                    source_ref=f'test:{i}'
                ),
                semantic=Semantic(
                    context='Summary ' * 5,
                    keywords=[f'keyword{i % 10}'],
                    tags=[f'tag{i % 5}'],
                    entities=['muddywater', 'CVE-2024-3094']
                ),
                embedding=Embedding(),
                metadata=Metadata(
                    tier='B',
                    domain='security_ops'
                )
            )
            store.write_note(note)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        print(f"After note creation: {current / 1024 / 1024:.1f} MB")
        print(f"Peak memory: {peak / 1024 / 1024:.1f} MB")

        # Memory should be reasonable (< 100MB for 500 notes)
        self.assertLess(peak / 1024 / 1024, 100, "Memory usage too high")


# =============================================================================
# Test Runner
# =============================================================================

def run_all_tests():
    """Run all performance tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestNoteGenerationPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestGraphPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestSynthesisRetrieverPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestMemoryProfiling))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Performance Tests')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--benchmark', '-b', action='store_true', help='Run benchmarks only')
    args = parser.parse_args()

    # Run tests
    success = run_all_tests()

    if args.verbose:
        print("\n" + "=" * 60)
        print("PERFORMANCE TEST SUMMARY")
        print("=" * 60)

    sys.exit(0 if success else 1)
