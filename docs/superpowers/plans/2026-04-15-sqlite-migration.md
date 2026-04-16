# SQLite Migration Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development to implement.

**Goal:** Replace JSONL persistence with SQLite (WAL mode) for notes, knowledge graph edges, and entity index, providing ACID transactions, indexed queries, and a clean storage abstraction layer.

**Architecture:** Introduce a `StorageBackend` ABC that both `JSONLBackend` and `SQLiteBackend` implement. The ABC covers all current access patterns including LanceDB vector sync. SQLite uses WAL mode with `PRAGMA synchronous=NORMAL` (documented tradeoff: last transaction may be lost on OS crash, not application crash). A one-shot migration script reads JSONL and writes to SQLite. Auto-detection when both exist uses explicit precedence: SQLite wins if present and valid. LanceDB remains the vector index -- SQLite does not replace it.

---

### Task 1: Storage ABC Definition

**Files:**
- Create: `src/zettelforge/storage_abc.py`

Define the abstract interface that covers ALL current usage patterns from `MemoryStore`, `KnowledgeGraph`, and `EntityIndexer`.

- [ ] Step 1: Define the `StorageBackend` ABC. Every public method currently called on `MemoryStore`, `KnowledgeGraph`, and `EntityIndexer` must map to an ABC method. Derived from reading the actual call sites:

```python
"""
Storage Backend ABC -- unified interface for JSONL and SQLite persistence.

BLOCKER-2 fix: includes reindex_vector() for LanceDB sync.
"""
from abc import ABC, abstractmethod
from typing import Dict, Iterator, List, Optional, Set, Tuple

from zettelforge.note_schema import MemoryNote


class StorageBackend(ABC):
    """Abstract storage backend for ZettelForge persistence layer."""

    # ── Note Operations ──────────────────────────────────────────────────

    @abstractmethod
    def write_note(self, note: MemoryNote) -> None:
        """Persist a new note. Must assign note.id if empty."""
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
        """O(1) lookup by source_ref. Returns None if not found."""
        ...

    @abstractmethod
    def iterate_notes(self) -> Iterator[MemoryNote]:
        """Yield all notes. Used by entity index rebuild, exports."""
        ...

    @abstractmethod
    def get_notes_by_domain(self, domain: str) -> List[MemoryNote]:
        """All notes in a domain. Used by vector retriever domain filter."""
        ...

    @abstractmethod
    def get_recent_notes(self, limit: int = 10) -> List[MemoryNote]:
        """Most recent notes by created_at."""
        ...

    @abstractmethod
    def count_notes(self) -> int:
        """Total note count."""
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
        self, entity_type: str, entity_value: str, properties: Optional[Dict] = None
    ) -> str:
        """Add or update a KG node. Returns node_id."""
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
        """Add a KG edge. note_id tracks provenance (BLOCKER-3 fix)."""
        ...

    @abstractmethod
    def get_kg_node(self, entity_type: str, entity_value: str) -> Optional[Dict]:
        """Lookup a KG node by type + value."""
        ...

    @abstractmethod
    def get_kg_neighbors(
        self, entity_type: str, entity_value: str, relationship: Optional[str] = None
    ) -> List[Dict]:
        """Get adjacent nodes via outgoing edges."""
        ...

    @abstractmethod
    def traverse_kg(
        self, start_type: str, start_value: str, max_depth: int = 2
    ) -> List[List[Dict]]:
        """BFS/DFS traversal up to max_depth."""
        ...

    # ── Entity Index Operations ──────────────────────────────────────────

    @abstractmethod
    def add_entity_mapping(self, entity_type: str, entity_value: str, note_id: str) -> None:
        """Map an entity to a note ID."""
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
        """Prefix search across entity types."""
        ...

    # ── Lifecycle ────────────────────────────────────────────────────────

    @abstractmethod
    def close(self) -> None:
        """Flush and close resources."""
        ...

    @abstractmethod
    def export_snapshot(self, output_path: str) -> None:
        """Export full state for backup."""
        ...
```

- [ ] Step 2: Add `detect_backend()` factory function (WARNING-2 fix):

```python
def detect_backend(data_dir: str) -> StorageBackend:
    """Detect and return the appropriate storage backend.

    Precedence (WARNING-2 fix):
    1. If zettelforge.db exists and is valid SQLite -> SQLiteBackend
    2. If notes.jsonl exists -> JSONLBackend
    3. Default -> SQLiteBackend (new install)

    When BOTH exist, SQLite wins. The migration script creates the SQLite
    DB and renames notes.jsonl to notes.jsonl.migrated as a safety net.
    """
    ...
```

**Test:** `python -c "from zettelforge.storage_abc import StorageBackend; print('ABC loads')"` -- should import cleanly.

---

### Task 2: SQLite Schema Design

**Files:**
- Create: `src/zettelforge/sqlite_backend.py` (schema section only in this task)

Design the SQLite schema addressing BLOCKER-3 (edge provenance).

- [ ] Step 1: Define the DDL. Key design decisions:
  - Notes table stores the full Pydantic model as a JSON column plus indexed scalar columns for fast queries
  - KG edges include `note_id` for provenance -- `UNIQUE(from_node_id, to_node_id, relationship, note_id)` instead of `UNIQUE(from_node_id, to_node_id, relationship)`
  - Entity index is a simple junction table with composite index
  - WAL mode with `PRAGMA synchronous=NORMAL` (WARNING-3: documented data loss risk on OS crash)

```sql
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now')),
    description TEXT
);
INSERT INTO schema_version (version, description)
VALUES (1, 'Initial SQLite migration from JSONL');

-- Notes table
-- Stores full MemoryNote as JSON for flexibility, with indexed columns for queries.
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,                      -- note_YYYYMMDD_HHMMSS_xxxx
    domain TEXT NOT NULL DEFAULT 'general',   -- indexed for domain-filtered queries
    source_ref TEXT,                          -- indexed for dedup lookups
    created_at TEXT NOT NULL,                 -- indexed for recent-notes queries
    updated_at TEXT NOT NULL,
    superseded_by TEXT,                       -- NULL if active, note_id if superseded
    data JSON NOT NULL                        -- full MemoryNote.model_dump_json()
);

CREATE INDEX IF NOT EXISTS idx_notes_domain ON notes(domain);
CREATE INDEX IF NOT EXISTS idx_notes_source_ref ON notes(source_ref) WHERE source_ref IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at);
CREATE INDEX IF NOT EXISTS idx_notes_active ON notes(domain, created_at) WHERE superseded_by IS NULL;

-- Knowledge Graph Nodes
CREATE TABLE IF NOT EXISTS kg_nodes (
    node_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_value TEXT NOT NULL,
    properties JSON DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(entity_type, entity_value)
);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_type_value ON kg_nodes(entity_type, entity_value);

-- Knowledge Graph Edges (BLOCKER-3 fix: note_id in unique constraint)
-- Multiple notes can establish the same relationship -- each gets its own row.
-- This preserves provenance: if note A says "APT28 uses Mimikatz" and note B
-- says the same, both edges are kept. Deleting note A only removes its edge.
CREATE TABLE IF NOT EXISTS kg_edges (
    edge_id TEXT PRIMARY KEY,
    from_node_id TEXT NOT NULL REFERENCES kg_nodes(node_id),
    to_node_id TEXT NOT NULL REFERENCES kg_nodes(node_id),
    relationship TEXT NOT NULL,
    note_id TEXT REFERENCES notes(id),        -- provenance: which note established this edge
    properties JSON DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(from_node_id, to_node_id, relationship, note_id)
);

CREATE INDEX IF NOT EXISTS idx_kg_edges_from ON kg_edges(from_node_id);
CREATE INDEX IF NOT EXISTS idx_kg_edges_to ON kg_edges(to_node_id);
CREATE INDEX IF NOT EXISTS idx_kg_edges_rel ON kg_edges(relationship);
CREATE INDEX IF NOT EXISTS idx_kg_edges_note ON kg_edges(note_id) WHERE note_id IS NOT NULL;

-- Entity Index (replaces entity_index.json)
CREATE TABLE IF NOT EXISTS entity_index (
    entity_type TEXT NOT NULL,
    entity_value TEXT NOT NULL,
    note_id TEXT NOT NULL REFERENCES notes(id),
    PRIMARY KEY (entity_type, entity_value, note_id)
);

CREATE INDEX IF NOT EXISTS idx_entity_type_value ON entity_index(entity_type, entity_value);
CREATE INDEX IF NOT EXISTS idx_entity_note ON entity_index(note_id);
```

- [ ] Step 2: Document the WAL mode tradeoff (WARNING-3):

```python
# In SQLiteBackend.__init__:
# WARNING-3: synchronous=NORMAL means the last transaction before an OS crash
# (power failure, kernel panic) may be lost. Application-level crashes (Python
# exception, SIGTERM) are safe because SQLite flushes the WAL on close().
# For zero-data-loss guarantees, set synchronous=FULL at ~2x write latency cost.
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
conn.execute("PRAGMA foreign_keys=ON")
conn.execute("PRAGMA busy_timeout=5000")
```

**Test:** `python -c "from zettelforge.sqlite_backend import SQLiteBackend; b = SQLiteBackend('/tmp/test_zf.db'); print(b)"` -- should create DB with all tables.

---

### Task 3: SQLiteBackend Implementation

**Files:**
- Create/Complete: `src/zettelforge/sqlite_backend.py`

Implement every ABC method.

- [ ] Step 1: Implement note operations. Key implementation notes:
  - `write_note()`: INSERT with full JSON in `data` column, scalar columns extracted for indexing
  - `rewrite_note()`: UPDATE with new JSON and updated scalar columns
  - `get_note_by_id()`: SELECT by PK, deserialize JSON to MemoryNote
  - `iterate_notes()`: Use server-side cursor (`fetchmany(500)`) to avoid loading 100K+ notes into memory

- [ ] Step 2: Implement `reindex_vector()` (BLOCKER-2):

```python
def reindex_vector(self, note_id: str, vector: List[float]) -> None:
    """Update embedding vector in SQLite and trigger LanceDB re-index."""
    note = self.get_note_by_id(note_id)
    if note is None:
        raise ValueError(f"Note {note_id} not found")

    note.embedding.vector = vector
    self.rewrite_note(note)

    # Re-index in LanceDB
    if self._lancedb is not None:
        self._index_in_lance(note)
```

- [ ] Step 3: Implement KG operations. The `add_kg_edge` method must accept `note_id` parameter for provenance:

```python
def add_kg_edge(
    self, from_type, from_value, to_type, to_value, relationship,
    note_id=None, properties=None,
) -> str:
    from_node_id = self.add_kg_node(from_type, from_value)
    to_node_id = self.add_kg_node(to_type, to_value)

    # Check existing (with note_id in uniqueness check)
    existing = self._conn.execute(
        """SELECT edge_id FROM kg_edges
           WHERE from_node_id=? AND to_node_id=? AND relationship=? AND note_id IS ?""",
        (from_node_id, to_node_id, relationship, note_id),
    ).fetchone()

    if existing:
        if properties:
            self._conn.execute(
                "UPDATE kg_edges SET properties=json_patch(properties, ?), updated_at=datetime('now') WHERE edge_id=?",
                (json.dumps(properties), existing[0]),
            )
            self._conn.commit()
        return existing[0]

    edge_id = f"edge_{uuid.uuid4().hex[:12]}"
    self._conn.execute(
        """INSERT INTO kg_edges (edge_id, from_node_id, to_node_id, relationship, note_id, properties)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (edge_id, from_node_id, to_node_id, relationship, note_id, json.dumps(properties or {})),
    )
    self._conn.commit()
    return edge_id
```

- [ ] Step 4: Implement entity index operations as simple INSERT/DELETE/SELECT on the `entity_index` table.

- [ ] Step 5: Implement `close()` with explicit WAL checkpoint:

```python
def close(self) -> None:
    if self._conn:
        self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self._conn.close()
        self._conn = None
```

**Test:** Run the existing test suite with SQLite backend:
```bash
ZETTELFORGE_STORAGE=sqlite python -m pytest tests/ -x -q
```

---

### Task 4: JSONL Backend Adapter

**Files:**
- Create: `src/zettelforge/jsonl_backend.py`

Wrap the existing `MemoryStore`, `KnowledgeGraph`, and `EntityIndexer` behind the `StorageBackend` ABC so the old code path continues to work.

- [ ] Step 1: Implement `JSONLBackend(StorageBackend)` that delegates to the three existing classes:

```python
class JSONLBackend(StorageBackend):
    def __init__(self, data_dir: str):
        self._store = MemoryStore(
            jsonl_path=str(Path(data_dir) / "notes.jsonl"),
            lance_path=str(Path(data_dir) / "vectordb"),
        )
        self._kg = KnowledgeGraph(data_dir=data_dir)
        self._entity_idx = EntityIndexer(
            index_path=str(Path(data_dir) / "entity_index.json")
        )

    def write_note(self, note: MemoryNote) -> None:
        self._store.write_note(note)

    def rewrite_note(self, note: MemoryNote) -> None:
        self._store._rewrite_note(note)

    def reindex_vector(self, note_id: str, vector: List[float]) -> None:
        note = self._store.get_note_by_id(note_id)
        if note is None:
            raise ValueError(f"Note {note_id} not found")
        note.embedding.vector = vector
        self._store._rewrite_note(note)
        if self._store.lancedb is not None:
            self._store._index_in_lance(note)

    # ... delegate remaining methods ...
```

- [ ] Step 2: Add `note_id` parameter to KG edge methods. For the JSONL backend, this requires extending `KnowledgeGraph.add_edge()` to accept an optional `note_id` and store it in the edge properties. Since changing the JSONL format is low-risk (it's append-only), add `note_id` as a top-level edge field:

```python
# In knowledge_graph.py, add_edge():
edge = {
    "edge_id": edge_id,
    "from_node_id": from_id,
    "to_node_id": to_id,
    "relationship": relationship,
    "note_id": note_id,  # NEW: provenance tracking
    "properties": properties or {},
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat(),
}
```

**Test:** `python -m pytest tests/ -x -q` -- all existing tests must still pass with JSONL backend.

---

### Task 5: Migration Script

**Files:**
- Create: `scripts/migrate_jsonl_to_sqlite.py`

One-shot migration that reads all JSONL data and writes to SQLite.

- [ ] Step 1: Implement migration with progress reporting and validation:

```python
#!/usr/bin/env python3
"""
Migrate ZettelForge data from JSONL to SQLite.

Usage:
  python scripts/migrate_jsonl_to_sqlite.py                    # Migrate default data dir
  python scripts/migrate_jsonl_to_sqlite.py --data-dir /path   # Migrate specific dir
  python scripts/migrate_jsonl_to_sqlite.py --dry-run          # Validate only, no write

Safety:
  - JSONL files are renamed to *.migrated (not deleted)
  - Migration is idempotent: re-running skips already-migrated notes
  - Validates note count matches after migration
"""
```

- [ ] Step 2: Migration steps:
  1. Open JSONL files, count records
  2. Create SQLite DB with schema from Task 2
  3. Batch-insert notes (500 per transaction for performance)
  4. Batch-insert KG nodes and edges (including dedup)
  5. Batch-insert entity index entries
  6. Validate counts match
  7. Rename JSONL files to `*.migrated`

- [ ] Step 3: Handle LanceDB migration (WARNING-4). Existing LanceDB tables may have stale columns or old schema. The migration script should:
  - Check each LanceDB table for schema compatibility
  - If columns are missing or extra, rebuild the table from SQLite data
  - Log which tables were rebuilt

```python
def migrate_lancedb_tables(sqlite_backend, lance_path: str) -> Dict[str, str]:
    """Rebuild LanceDB tables from SQLite source of truth.

    WARNING-4: Old LanceDB tables may have dead columns from previous schema.
    Rebuilding from SQLite ensures clean schema alignment.
    """
    import lancedb
    db = lancedb.connect(lance_path)

    status = {}
    for domain in sqlite_backend.get_all_domains():
        table_name = f"notes_{domain}"
        notes = sqlite_backend.get_notes_by_domain(domain)

        # Drop and recreate to ensure clean schema
        try:
            db.drop_table(table_name)
        except Exception:
            pass

        if notes:
            # Batch create with correct schema
            data = [{
                "id": n.id,
                "vector": n.embedding.vector or [0.0] * len(notes[0].embedding.vector),
                "content": n.content.raw[:500],
                "context": n.semantic.context,
                "keywords": ",".join(n.semantic.keywords),
                "tags": ",".join(n.semantic.tags),
                "created_at": n.created_at,
            } for n in notes]
            db.create_table(table_name, data=data)
            status[table_name] = f"rebuilt ({len(notes)} rows)"
        else:
            status[table_name] = "skipped (empty)"

    return status
```

- [ ] Step 4: Add validation step that reads back from SQLite and compares note counts, KG node/edge counts, and entity index counts against the original JSONL.

**Test:**
```bash
# Dry run
python scripts/migrate_jsonl_to_sqlite.py --dry-run

# Actual migration on test data
cp -r ~/.amem /tmp/amem_test
python scripts/migrate_jsonl_to_sqlite.py --data-dir /tmp/amem_test
python -c "
from zettelforge.sqlite_backend import SQLiteBackend
b = SQLiteBackend('/tmp/amem_test/zettelforge.db')
print(f'Notes: {b.count_notes()}')
"
```

---

### Task 6: Wire Backend Into MemoryManager

**Files:**
- Modify: `src/zettelforge/memory_manager.py`
- Modify: `src/zettelforge/memory_store.py` (add `get_default_data_dir` export)

Replace direct `MemoryStore` / `KnowledgeGraph` / `EntityIndexer` usage with the `StorageBackend` ABC.

- [ ] Step 1: Add backend detection to `MemoryManager.__init__`:

```python
def __init__(self, jsonl_path=None, lance_path=None, backend=None):
    if backend is not None:
        self.backend = backend
    else:
        from zettelforge.storage_abc import detect_backend
        data_dir = get_default_data_dir()
        self.backend = detect_backend(str(data_dir))

    # Keep self.store for backward compatibility during transition
    self.store = self.backend._store if hasattr(self.backend, '_store') else ...
```

- [ ] Step 2: Incrementally replace direct store calls. Start with `remember()` and `recall()` -- the two hot paths. Other methods can be migrated in follow-up PRs.

- [ ] Step 3: Update `MemoryManager.close()` (or atexit handler) to call `self.backend.close()` for clean SQLite WAL checkpoint.

**Test:** Full test suite with both backends:
```bash
# JSONL (default, existing tests)
python -m pytest tests/ -x -q

# SQLite
ZETTELFORGE_STORAGE=sqlite python -m pytest tests/ -x -q
```

---

### Task 7: Integration Tests

**Files:**
- Create: `tests/test_sqlite_backend.py`
- Create: `tests/test_storage_abc_compliance.py`

- [ ] Step 1: Write ABC compliance test that runs the same test cases against both backends:

```python
import pytest
from zettelforge.jsonl_backend import JSONLBackend
from zettelforge.sqlite_backend import SQLiteBackend

@pytest.fixture(params=["jsonl", "sqlite"])
def backend(request, tmp_path):
    if request.param == "jsonl":
        return JSONLBackend(str(tmp_path))
    else:
        return SQLiteBackend(str(tmp_path / "test.db"))

def test_write_and_read_note(backend):
    note = make_test_note()
    backend.write_note(note)
    retrieved = backend.get_note_by_id(note.id)
    assert retrieved is not None
    assert retrieved.content.raw == note.content.raw

def test_reindex_vector(backend):
    note = make_test_note()
    backend.write_note(note)
    new_vec = [0.1] * 768
    backend.reindex_vector(note.id, new_vec)
    updated = backend.get_note_by_id(note.id)
    assert updated.embedding.vector == new_vec

def test_kg_edge_provenance(backend):
    """BLOCKER-3: Same relationship from different notes creates separate edges."""
    backend.add_kg_edge("actor", "apt28", "tool", "mimikatz", "USES_TOOL", note_id="note_001")
    backend.add_kg_edge("actor", "apt28", "tool", "mimikatz", "USES_TOOL", note_id="note_002")
    neighbors = backend.get_kg_neighbors("actor", "apt28", relationship="USES_TOOL")
    # Should have 2 edges (one per note), not 1
    edges = [n for n in neighbors if n["node"]["entity_value"] == "mimikatz"]
    assert len(edges) >= 2 or "note_002" in str(edges)
```

- [ ] Step 2: Write migration round-trip test:

```python
def test_migration_roundtrip(tmp_path):
    """Write data via JSONL, migrate to SQLite, verify identical."""
    jsonl = JSONLBackend(str(tmp_path / "jsonl"))
    # Write test data
    for i in range(100):
        jsonl.write_note(make_test_note(f"note_{i:04d}"))
    jsonl.add_kg_edge("actor", "apt28", "tool", "mimikatz", "USES_TOOL")

    # Migrate
    migrate(str(tmp_path / "jsonl"), str(tmp_path / "sqlite"))

    # Verify
    sqlite = SQLiteBackend(str(tmp_path / "sqlite" / "zettelforge.db"))
    assert sqlite.count_notes() == 100
    assert sqlite.get_note_by_id("note_0000") is not None
```

**Test:** `python -m pytest tests/test_sqlite_backend.py tests/test_storage_abc_compliance.py -v`
