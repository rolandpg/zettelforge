"""
Memory Manager - Primary Agent Interface
A-MEM Agentic Memory Architecture V1.0

Main interface for agent memory operations.
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from amem.note_schema import MemoryNote
from amem.memory_store import MemoryStore, get_default_data_dir
from amem.note_constructor import NoteConstructor
from amem.entity_indexer import EntityIndexer
from amem.vector_retriever import VectorRetriever


class MemoryManager:
    """
    Main interface for agent memory operations.
    """

    def __init__(
        self,
        jsonl_path: Optional[str] = None,
        lance_path: Optional[str] = None
    ):
        self.store = MemoryStore(jsonl_path=jsonl_path, lance_path=lance_path)
        self.constructor = NoteConstructor()
        self.indexer = EntityIndexer()
        self.retriever = VectorRetriever(memory_store=self.store)

        self.stats = {
            'notes_created': 0,
            'retrievals': 0,
            'entity_index_hits': 0
        }

    def remember(
        self,
        content: str,
        source_type: str = "conversation",
        source_ref: str = "",
        domain: str = "general"
    ) -> Tuple[MemoryNote, str]:
        """
        Create a new memory note from content.
        
        Returns: (note, status)
        """
        # Construct note
        note = self.constructor.construct(
            raw_content=content,
            source_type=source_type,
            source_ref=source_ref,
            domain=domain
        )

        # Write to store
        self.store.write_note(note)
        self.stats['notes_created'] += 1

        # Index entities
        entities = self.indexer.extractor.extract_all(note.content.raw)
        self.indexer.add_note(note.id, entities)

        return note, "created"

    def recall(
        self,
        query: str,
        domain: Optional[str] = None,
        k: int = 10,
        include_links: bool = True
    ) -> List[MemoryNote]:
        """
        Retrieve memories relevant to query.
        """
        self.stats['retrievals'] += 1
        return self.retriever.retrieve(
            query=query,
            domain=domain,
            k=k,
            include_links=include_links
        )

    def recall_entity(
        self,
        entity_type: str,
        entity_value: str,
        k: int = 5
    ) -> List[MemoryNote]:
        """
        Fast lookup by entity type and value.
        entity_type: 'cve', 'actor', 'tool', 'campaign', 'sector'
        """
        self.stats['entity_index_hits'] += 1
        note_ids = self.indexer.get_note_ids(entity_type, entity_value.lower())
        notes = []
        for nid in note_ids[:k]:
            note = self.store.get_note_by_id(nid)
            if note:
                notes.append(note)
        return notes

    def recall_cve(self, cve_id: str, k: int = 5) -> List[MemoryNote]:
        """Fast lookup by CVE-ID (case-insensitive)"""
        return self.recall_entity('cve', cve_id.upper(), k)

    def recall_actor(self, actor_name: str, k: int = 5) -> List[MemoryNote]:
        """Fast lookup by threat actor name"""
        return self.recall_entity('actor', actor_name.lower(), k)

    def recall_tool(self, tool_name: str, k: int = 5) -> List[MemoryNote]:
        """Fast lookup by tool name"""
        return self.recall_entity('tool', tool_name.lower(), k)

    def get_context(
        self,
        query: str,
        domain: Optional[str] = None,
        k: int = 10,
        token_budget: int = 4000
    ) -> str:
        """
        Get formatted memory context for agent prompt injection.
        """
        return self.retriever.get_memory_context(
            query=query,
            domain=domain,
            k=k,
            token_budget=token_budget
        )

    def get_stats(self) -> Dict:
        """Get memory system statistics"""
        return {
            **self.stats,
            'total_notes': self.store.count_notes(),
            'entity_index': self.indexer.stats()
        }

    def snapshot(self) -> str:
        """Export memory snapshot"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_dir = get_default_data_dir()
        snapshot_dir = data_dir / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Export JSONL
        self.store.export_snapshot(str(snapshot_dir))

        return str(snapshot_dir / f"notes_{timestamp}.jsonl")


# Global memory manager instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get or create global memory manager instance"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
