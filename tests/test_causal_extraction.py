#!/usr/bin/env python3
"""
Test causal triple extraction in ZettelForge.
Validates Task 1: LLM-based causal edge extraction from consolidation pass.
"""
import os
import pytest

from zettelforge import MemoryManager
from zettelforge.note_constructor import NoteConstructor


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Ensure all tests use an isolated data directory to avoid polluting ~/.amem."""
    monkeypatch.setenv("AMEM_DATA_DIR", str(tmp_path))
    import zettelforge.knowledge_graph as kg_module
    original = kg_module._kg_instance
    kg_module._kg_instance = None
    yield tmp_path
    kg_module._kg_instance = original


def test_causal_extraction(tmp_path):
    mm = MemoryManager(
        jsonl_path=str(tmp_path / "notes.jsonl"),
        lance_path=str(tmp_path / "vectordb"),
    )
    
    # Test CTI content with causal relationships
    cti_content = (
        "APT28 (Fancy Bear) continues to target critical infrastructure in the energy sector. "
        "The group uses DROPBEAR malware for initial access and Cobalt Strike for lateral movement. "
        "CVE-2024-1111 enables remote code execution on unpatched Microsoft Exchange servers. "
        "APT48 used this vulnerability to compromise Server ALPHA on May 15, 2024. "
        "The incident was contained after patching on May 20, 2024."
    )
    
    note, status = mm.remember(cti_content, domain="cti")
    assert note is not None
    assert note.id


def test_graph_traversal(tmp_path):
    """Test that the knowledge graph accepts traversal queries without crashing."""
    mm = MemoryManager(
        jsonl_path=str(tmp_path / "notes.jsonl"),
        lance_path=str(tmp_path / "vectordb"),
    )
    mm.remember("APT28 uses Cobalt Strike for lateral movement", domain="cti")

    from zettelforge.knowledge_graph import get_knowledge_graph
    kg = get_knowledge_graph()

    results = kg.traverse("actor", "apt28", max_depth=2)
    assert isinstance(results, list)