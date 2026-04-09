"""
ZettelForge Performance Test Suite
Compliant with GOV-007 (Testing Standards)
Tests performance, scalability, and correctness at various scales.
"""
import time
import tempfile
import pytest
from typing import List
import statistics

from zettelforge import MemoryManager
from zettelforge.note_schema import MemoryNote, Content, Semantic, Embedding, Metadata


class TestPerformance:
    """Performance and scalability tests for ZettelForge."""
    
    @pytest.fixture
    def mm(self, tmp_path):
        """Fresh, isolated MemoryManager for each test."""
        return MemoryManager(
            jsonl_path=str(tmp_path / "notes.jsonl"),
            lance_path=str(tmp_path / "vectordb"),
        )
    
    @pytest.mark.slow
    def test_insertion_performance(self, mm):
        """Test insertion performance at scale."""
        start = time.perf_counter()
        for i in range(1000):  # Small scale for CI
            content = f"Test memory entry number {i} about threat actor APT{i%28}"
            mm.remember(content, domain="cti")
        duration = time.perf_counter() - start
        
        assert duration < 30.0, f"Insertion too slow: {duration:.2f}s"
    
    @pytest.mark.slow
    def test_retrieval_performance(self, mm):
        """Test retrieval performance and quality."""
        # Seed some data
        for i in range(500):
            mm.remember(f"APT28 used malware {i} in campaign {i%5}", domain="cti")
        
        start = time.perf_counter()
        results = mm.recall("APT28 malware campaigns", k=10)
        duration = time.perf_counter() - start
        
        assert len(results) > 0
        assert duration < 5.0, f"Retrieval too slow: {duration:.2f}s"
    
    @pytest.mark.slow
    def test_cache_performance(self, mm):
        """Test cache hit rate."""
        # Warm cache
        for i in range(100):
            mm.remember(f"Cached query test {i}")
        
        # Measure cache effectiveness
        start = time.perf_counter()
        for i in range(50):
            mm.recall("Cached query test", k=5)
        duration = time.perf_counter() - start
        
        assert duration < 2.0, "Cache not providing expected performance benefit"
    
    def test_governance_compliance(self, mm):
        """Ensure governance validation is active."""
        validator = getattr(mm, 'governance', None)
        assert validator is not None, "Governance validator not present"
        
        # Test that validation is working
        is_valid, violations = validator.validate_operation("remember", "Valid content")
        assert is_valid
