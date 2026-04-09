"""Integration tests for rewritten recall() with graph traversal."""
import os
import pytest
import tempfile
import time

from zettelforge.memory_manager import MemoryManager


@pytest.fixture(autouse=True)
def isolated_kg(tmp_path, monkeypatch):
    """Reset the global KG singleton so each test gets an isolated instance."""
    monkeypatch.setenv("AMEM_DATA_DIR", str(tmp_path))
    import zettelforge.knowledge_graph as kg_module
    original = kg_module._kg_instance
    kg_module._kg_instance = None
    yield
    kg_module._kg_instance = original


@pytest.fixture
def mm_with_graph(tmp_path):
    mm = MemoryManager(
        jsonl_path=str(tmp_path / "notes.jsonl"),
        lance_path=str(tmp_path / "vectordb"),
    )
    mm.remember("APT28 uses Cobalt Strike for lateral movement", domain="cti")
    mm.remember("Cobalt Strike exploits CVE-2024-1111 in edge devices", domain="cti")
    mm.remember("APT28 targets energy sector infrastructure", domain="cti")
    return mm


class TestRecallWithGraph:
    def test_recall_returns_results(self, mm_with_graph):
        results = mm_with_graph.recall("APT28", k=5)
        assert len(results) >= 1

    def test_relational_query_uses_graph(self, mm_with_graph):
        results = mm_with_graph.recall("What tools does APT28 use?", k=5)
        assert len(results) >= 1
        texts = [n.content.raw for n in results]
        assert any("Cobalt Strike" in t for t in texts)

    def test_multihop_finds_indirect_notes(self, mm_with_graph):
        results = mm_with_graph.recall("APT28 toolkit and vulnerabilities", k=10)
        texts = [n.content.raw for n in results]
        has_cve_note = any("CVE-2024-1111" in t for t in texts)
        has_tool_note = any("Cobalt Strike" in t for t in texts)
        assert has_cve_note or has_tool_note

    def test_exploratory_query_blends_both(self, mm_with_graph):
        results = mm_with_graph.recall("Tell me about threats to energy sector", k=5)
        assert len(results) >= 1

    def test_recall_excludes_superseded(self, mm_with_graph):
        note_old, _ = mm_with_graph.remember("Server ALPHA compromised", domain="incident")
        time.sleep(0.1)
        note_new, _ = mm_with_graph.remember("Server ALPHA remediated and patched", domain="incident")
        mm_with_graph.mark_note_superseded(note_old.id, note_new.id)
        results = mm_with_graph.recall("Server ALPHA status", k=10, exclude_superseded=True)
        result_ids = [r.id for r in results]
        assert note_old.id not in result_ids

    def test_recall_performance(self, mm_with_graph):
        start = time.perf_counter()
        mm_with_graph.recall("APT28 tools and techniques", k=10)
        duration = time.perf_counter() - start
        assert duration < 5.0, f"recall() took {duration:.2f}s (max 5s)"
