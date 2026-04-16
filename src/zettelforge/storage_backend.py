"""
Storage Backend ABC -- unified interface for JSONL and SQLite persistence.

Defines the abstract interface that all storage backends (JSONL, SQLite,
PostgreSQL) must implement.  Decouples the retrieval and memory-management
layers from the specific storage technology.

BLOCKER-2 fix: includes reindex_vector() for LanceDB sync.
BLOCKER-3 prep: KG edge methods accept note_id for provenance tracking.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional

from zettelforge.note_schema import MemoryNote


class StorageBackend(ABC):
    """Abstract storage backend for ZettelForge persistence layer."""

    # ── Note Operations ──────────────────────────────────────────────────

    @abstractmethod
    def write_note(self, note: MemoryNote) -> None:
        """Persist a new note.  Must assign note.id if empty."""
        ...

    @abstractmethod
    def rewrite_note(self, note: MemoryNote) -> None:
        """Update an existing note in place (atomic)."""
        ...

    @abstractmethod
    def get_note_by_id(self, note_id: str) -> Optional[MemoryNote]:
        """O(1) lookup by note ID."""
        ...

    @abstractmethod
    def get_note_by_source_ref(self, source_ref: str) -> Optional[MemoryNote]:
        """O(1) lookup by source_ref.  Returns None if not found."""
        ...

    @abstractmethod
    def iterate_notes(self) -> Iterator[MemoryNote]:
        """Yield all notes.  Used by entity index rebuild, exports."""
        ...

    @abstractmethod
    def get_notes_by_domain(self, domain: str) -> List[MemoryNote]:
        """All notes in a domain.  Used by vector retriever domain filter."""
        ...

    @abstractmethod
    def get_recent_notes(self, limit: int = 10) -> List[MemoryNote]:
        """Most recent notes by created_at."""
        ...

    @abstractmethod
    def count_notes(self) -> int:
        """Total note count."""
        ...

    @abstractmethod
    def delete_note(self, note_id: str) -> bool:
        """Delete a note by ID.  Returns True if the note existed."""
        ...

    # ── Vector Index Sync (BLOCKER-2 fix) ────────────────────────────────

    @abstractmethod
    def reindex_vector(self, note_id: str, vector: List[float]) -> None:
        """Update a note's embedding vector and trigger LanceDB re-sync.

        Called by rebuild_index.py when re-embedding notes with a new model.
        Must update both the persistence layer and the LanceDB table.
        """
        ...

    # ── Knowledge Graph Operations ───────────────────────────────────────

    @abstractmethod
    def add_kg_node(
        self,
        entity_type: str,
        entity_value: str,
        properties: Optional[Dict] = None,
    ) -> str:
        """Add or update a KG node.  Returns node_id."""
        ...

    @abstractmethod
    def add_kg_edge(
        self,
        from_type: str,
        from_value: str,
        to_type: str,
        to_value: str,
        relationship: str,
        note_id: Optional[str] = None,
        properties: Optional[Dict] = None,
    ) -> str:
        """Add a KG edge.  note_id tracks provenance (BLOCKER-3 fix).

        When note_id is provided, uniqueness is per
        (from, to, relationship, note_id) -- allowing multiple notes to
        independently assert the same relationship.
        """
        ...

    @abstractmethod
    def get_kg_node(self, entity_type: str, entity_value: str) -> Optional[Dict]:
        """Lookup a KG node by type + value."""
        ...

    @abstractmethod
    def get_kg_neighbors(
        self,
        entity_type: str,
        entity_value: str,
        relationship: Optional[str] = None,
    ) -> List[Dict]:
        """Get adjacent nodes via outgoing edges."""
        ...

    @abstractmethod
    def traverse_kg(
        self,
        start_type: str,
        start_value: str,
        max_depth: int = 2,
    ) -> List[List[Dict]]:
        """BFS/DFS traversal up to max_depth.  Returns list of paths."""
        ...

    @abstractmethod
    def get_entity_timeline(self, entity_type: str, entity_value: str) -> List[Dict]:
        """Get temporal timeline of states for an entity."""
        ...

    @abstractmethod
    def get_changes_since(self, timestamp: str) -> List[Dict]:
        """Get all entity changes since a given ISO-8601 timestamp."""
        ...

    # ── Entity Index Operations ──────────────────────────────────────────

    @abstractmethod
    def add_entity_mapping(self, entity_type: str, entity_value: str, note_id: str) -> None:
        """Map an entity occurrence to a note ID."""
        ...

    @abstractmethod
    def remove_entity_mappings_for_note(self, note_id: str) -> None:
        """Remove all entity mappings for a given note."""
        ...

    @abstractmethod
    def get_note_ids_for_entity(self, entity_type: str, entity_value: str) -> List[str]:
        """Get note IDs associated with an entity."""
        ...

    @abstractmethod
    def search_entities(self, query: str, limit: int = 10) -> Dict[str, List[str]]:
        """Prefix search across entity types.  Returns type -> matching values."""
        ...

    # ── Lifecycle ────────────────────────────────────────────────────────

    @abstractmethod
    def initialize(self) -> None:
        """Perform any one-time setup (create tables, warm caches, etc.)."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Flush pending writes and release resources."""
        ...

    def health_check(self) -> Dict[str, Any]:
        """Return backend health status.  Override for richer diagnostics."""
        return {"status": "ok", "backend": self.__class__.__name__}

    @abstractmethod
    def export_snapshot(self, output_path: str) -> None:
        """Export full state for backup / cold storage."""
        ...
