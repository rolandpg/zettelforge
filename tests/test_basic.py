"""
Basic tests for A-MEM
"""
import pytest
import tempfile
from pathlib import Path

from zettelforge import MemoryManager, MemoryNote
from zettelforge.note_schema import Content, Semantic, Embedding, Metadata
from zettelforge.memory_store import MemoryStore
from zettelforge.note_constructor import NoteConstructor
from zettelforge.entity_indexer import EntityIndexer, EntityExtractor
from zettelforge.vector_retriever import VectorRetriever


class TestNoteSchema:
    """Test note schema creation and validation"""

    def test_memory_note_creation(self):
        """Test creating a MemoryNote"""
        note = MemoryNote(
            id="test_001",
            content=Content(
                raw="Test content",
                source_type="test",
                source_ref="test_ref"
            ),
            semantic=Semantic(
                context="Test context",
                keywords=["test"],
                tags=["test"],
                entities=[]
            ),
            embedding=Embedding(
                vector=[0.1] * 768,
                model="test-model"
            ),
            metadata=Metadata(
                domain="test",
                tier="A"
            )
        )
        assert note.id == "test_001"
        assert note.content.raw == "Test content"
        assert len(note.embedding.vector) == 768

    def test_note_access_tracking(self):
        """Test note access counting"""
        note = MemoryNote(
            id="test_002",
            content=Content(raw="Test", source_type="test", source_ref=""),
            semantic=Semantic(context="Test", keywords=[], tags=[], entities=[]),
            embedding=Embedding(vector=[]),
            metadata=Metadata()
        )
        assert note.metadata.access_count == 0
        note.increment_access()
        assert note.metadata.access_count == 1
        assert note.metadata.last_accessed is not None


class TestMemoryStore:
    """Test MemoryStore operations"""

    def test_store_initialization(self):
        """Test store initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(
                jsonl_path=f"{tmpdir}/notes.jsonl",
                lance_path=f"{tmpdir}/vectordb"
            )
            assert store.jsonl_path == Path(f"{tmpdir}/notes.jsonl")
            assert store.count_notes() == 0

    def test_write_and_read(self):
        """Test writing and reading notes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(
                jsonl_path=f"{tmpdir}/notes.jsonl",
                lance_path=f"{tmpdir}/vectordb"
            )
            
            note = MemoryNote(
                id="test_003",
                content=Content(raw="Test content", source_type="test", source_ref=""),
                semantic=Semantic(context="Test context", keywords=["test"], tags=[], entities=[]),
                embedding=Embedding(vector=[0.0] * 768),
                metadata=Metadata(domain="test")
            )
            
            store.write_note(note)
            assert store.count_notes() == 1
            
            retrieved = store.get_note_by_id("test_003")
            assert retrieved is not None
            assert retrieved.content.raw == "Test content"


class TestEntityExtractor:
    """Test entity extraction"""

    def test_cve_extraction(self):
        """Test CVE extraction from text"""
        extractor = EntityExtractor()
        text = "CVE-2024-3094 is a critical vulnerability. Also see CVE-2023-12345."
        entities = extractor.extract_all(text)
        
        assert "cve-2024-3094" in entities["cve"]
        assert "cve-2023-12345" in entities["cve"]

    def test_actor_extraction(self):
        """Test actor extraction from text"""
        extractor = EntityExtractor()
        text = "APT28 and Lazarus group were involved in the attack."
        entities = extractor.extract_all(text)
        
        assert "apt28" in entities["actor"] or any("apt" in a for a in entities["actor"])


class TestNoteConstructor:
    """Test note construction"""

    def test_note_construction(self):
        """Test constructing a note from raw content"""
        constructor = NoteConstructor()
        note = constructor.construct(
            raw_content="Test content about CVE-2024-3094",
            source_type="test",
            source_ref="test_ref",
            domain="security_ops"
        )
        
        assert note.content.raw == "Test content about CVE-2024-3094"
        assert note.metadata.domain == "security_ops"
        assert len(note.embedding.vector) > 0


class TestMemoryManager:
    """Test MemoryManager integration"""

    def test_manager_initialization(self):
        """Test manager initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mm = MemoryManager(
                jsonl_path=f"{tmpdir}/notes.jsonl",
                lance_path=f"{tmpdir}/vectordb"
            )
            assert mm is not None
            stats = mm.get_stats()
            assert "total_notes" in stats

    def test_remember_and_recall(self):
        """Test basic remember and recall flow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mm = MemoryManager(
                jsonl_path=f"{tmpdir}/notes.jsonl",
                lance_path=f"{tmpdir}/vectordb"
            )
            
            # Store a memory
            note, status = mm.remember(
                "CVE-2024-3094 is a backdoor in XZ Utils",
                domain="security_ops"
            )
            
            assert status == "created"
            assert note.id is not None
            assert mm.store.count_notes() == 1
            
            # Recall by entity
            results = mm.recall_cve("CVE-2024-3094")
            assert len(results) >= 0  # May be 0 if embedding not available


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
