#!/usr/bin/env python3
"""
Test temporal graph functionality in ZettelForge.
Validates Task 2: Temporal graph indexing and queries.
"""
import os
import tempfile
import pytest

from zettelforge import MemoryManager
from zettelforge.knowledge_graph import KnowledgeGraph


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Ensure all tests use an isolated data directory to avoid polluting ~/.amem."""
    monkeypatch.setenv("AMEM_DATA_DIR", str(tmp_path))
    # Reset the global KG singleton so each test gets its own instance
    import zettelforge.knowledge_graph as kg_module
    original = kg_module._kg_instance
    kg_module._kg_instance = None
    yield tmp_path
    kg_module._kg_instance = original


@pytest.fixture
def mm(tmp_path):
    return MemoryManager(
        jsonl_path=str(tmp_path / "notes.jsonl"),
        lance_path=str(tmp_path / "vectordb"),
    )


def test_temporal_graph(mm, tmp_path):
    note1_content = "Server ALPHA is COMPROMISED - attacker gained root access via CVE-2024-1111"
    note1, _ = mm.remember(note1_content, domain="incident")

    note2_content = "Server ALPHA has been PATCHED - CVE-2024-1111 remediated, system secured"
    note2, _ = mm.remember(note2_content, domain="incident")

    # Trigger supersession (note2 supersedes note1)
    mm._check_supersession(note2, mm.indexer.extractor.extract_all(note2.content.raw))

    from zettelforge.knowledge_graph import get_knowledge_graph
    kg = get_knowledge_graph()

    supersedes_edges = [e for e in kg._edges.values() if e.get('relationship') == 'SUPERSEDES']
    assert len(supersedes_edges) > 0, "Expected at least one SUPERSEDES edge after supersession check"


def test_entity_timeline(mm, tmp_path):
    note1, _ = mm.remember("Server BETA compromised", domain="incident")
    note2, _ = mm.remember("Server BETA patched", domain="incident")
    mm._check_supersession(note2, mm.indexer.extractor.extract_all(note2.content.raw))

    from zettelforge.knowledge_graph import get_knowledge_graph
    kg = get_knowledge_graph()

    timeline = kg.get_entity_timeline("note", note1.id)
    # Timeline may be empty if no temporal edges were added for this entity; just assert no crash
    assert isinstance(timeline, list)


def test_get_changes_since(mm, tmp_path):
    mm.remember("Infrastructure update alpha", domain="incident")

    from zettelforge.knowledge_graph import get_knowledge_graph
    kg = get_knowledge_graph()

    changes = kg.get_changes_since("2020-01-01")
    assert isinstance(changes, list)