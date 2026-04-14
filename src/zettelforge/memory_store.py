"""
Memory Note Storage - JSONL Read/Write Utilities
A-MEM Agentic Memory Architecture V1.0
"""
import json
import os
import hashlib
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Iterator

from zettelforge.log import get_logger
from zettelforge.ocsf import (
    log_file_activity, STATUS_SUCCESS, STATUS_FAILURE,
    SEVERITY_INFO, SEVERITY_HIGH,
)
from zettelforge.note_schema import MemoryNote

_logger = get_logger("zettelforge.store")


def get_default_data_dir() -> Path:
    """Get default data directory from environment or default to ~/.amem"""
    env_path = os.environ.get("AMEM_DATA_DIR")
    if env_path:
        return Path(env_path)
    return Path.home() / ".amem"


class MemoryStore:
    """JSONL-based memory note storage with LanceDB vector indexing"""
    
    def __init__(
        self, 
        jsonl_path: Optional[str] = None,
        lance_path: Optional[str] = None
    ):
        data_dir = get_default_data_dir()
        
        self.jsonl_path = Path(jsonl_path) if jsonl_path else data_dir / "notes.jsonl"
        self.lance_path = Path(lance_path) if lance_path else data_dir / "vectordb"
        
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        self.lance_path.mkdir(parents=True, exist_ok=True)
        self._lancedb = None
        self._note_cache: Optional[Dict[str, MemoryNote]] = None
    
    @property
    def lancedb(self):
        """Lazy-load LanceDB"""
        if self._lancedb is None:
            try:
                import lancedb
                self._lancedb = lancedb.connect(str(self.lance_path))
            except Exception as e:
                _logger.error("lancedb_connection_failed", error=str(e), exc_info=True)
                self._lancedb = None
        return self._lancedb
    
    def compute_input_hash(self, note: MemoryNote) -> str:
        """Compute SHA256 hash of note's text fields for change detection"""
        text = (
            note.content.raw +
            note.semantic.context +
            " ".join(note.semantic.keywords) +
            " ".join(note.semantic.tags)
        )
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def generate_note_id(self) -> str:
        """Generate unique note ID"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        import random
        suffix = str(random.randint(0, 9999)).zfill(4)
        return f"note_{ts}_{suffix}"
    
    def _ensure_cache(self):
        """Load all notes into memory cache on first access."""
        if self._note_cache is not None:
            return
        self._note_cache = {}
        if not self.jsonl_path.exists():
            return
        with open(self.jsonl_path, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        note = MemoryNote(**data)
                        self._note_cache[note.id] = note
                    except Exception:
                        pass

    def write_note(self, note: MemoryNote) -> None:
        """Append a note to the JSONL store"""
        note.id = note.id or self.generate_note_id()
        note.created_at = note.created_at or datetime.now().isoformat()
        note.updated_at = datetime.now().isoformat()
        
        # Compute input hash for change detection
        note.embedding.input_hash = self.compute_input_hash(note)
        
        # Write to JSONL
        with open(self.jsonl_path, "a") as f:
            f.write(note.model_dump_json() + "\n")

        # Update in-memory cache
        if self._note_cache is not None:
            self._note_cache[note.id] = note

        # Index in LanceDB if available
        if self.lancedb is not None:
            self._index_in_lance(note)
    
    def _index_in_lance(self, note: MemoryNote) -> None:
        """Index note in LanceDB vector store"""
        start = time.perf_counter()
        table_name = f"notes_{note.metadata.domain}"
        try:
            import pyarrow as pa

            note_data = {
                "id": note.id,
                "vector": note.embedding.vector if note.embedding.vector else [0.0] * 768,
                "content": note.content.raw[:500],
                "context": note.semantic.context,
                "keywords": ",".join(note.semantic.keywords),
                "tags": ",".join(note.semantic.tags),
                "created_at": note.created_at,
            }

            result = self.lancedb.list_tables()
            tables = result.tables if hasattr(result, 'tables') else (result if isinstance(result, list) else [])

            if table_name not in tables:
                schema = pa.schema([
                    ("id", pa.string()),
                    ("vector", pa.list_(pa.float32(), 768)),
                    ("content", pa.string()),
                    ("context", pa.string()),
                    ("keywords", pa.string()),
                    ("tags", pa.string()),
                    ("created_at", pa.string()),
                ])
                self.lancedb.create_table(table_name, data=[note_data], schema=schema)
                activity = "Create"
            else:
                tbl = self.lancedb.open_table(table_name)
                tbl.add([note_data])
                activity = "Update"

            duration_ms = (time.perf_counter() - start) * 1000
            log_file_activity(
                file_path=table_name, activity=activity,
                status_id=STATUS_SUCCESS,
                note_id=note.id, duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            _logger.error(
                "lancedb_indexing_failed",
                table_name=table_name, note_id=note.id,
                error=str(e), duration_ms=round(duration_ms, 2),
                exc_info=True,
            )
            log_file_activity(
                file_path=table_name, activity="Update",
                status_id=STATUS_FAILURE, severity_id=SEVERITY_HIGH,
                note_id=note.id, error=str(e), duration_ms=duration_ms,
            )
    
    def read_all_notes(self) -> List[MemoryNote]:
        """Read all notes from JSONL store"""
        notes = []
        if not self.jsonl_path.exists():
            return notes
        
        with open(self.jsonl_path, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        notes.append(MemoryNote(**data))
                    except Exception as e:
                        _logger.warning("note_parse_failed", error=str(e))
        return notes
    
    def iterate_notes(self) -> Iterator[MemoryNote]:
        """Iterate through notes. Uses in-memory cache after first load."""
        self._ensure_cache()
        yield from self._note_cache.values()
        return
        # Dead code below — kept for reference of old disk-based path
        if not self.jsonl_path.exists():
            return
        with open(self.jsonl_path, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        yield MemoryNote(**data)
                    except Exception as e:
                        _logger.warning("note_parse_failed", error=str(e))
    
    def get_note_by_id(self, note_id: str) -> Optional[MemoryNote]:
        """Retrieve a specific note by ID. O(1) via cache."""
        self._ensure_cache()
        return self._note_cache.get(note_id)
    
    def get_notes_by_domain(self, domain: str) -> List[MemoryNote]:
        """Retrieve all notes for a specific domain"""
        return [n for n in self.iterate_notes() if n.metadata.domain == domain]
    
    def get_recent_notes(self, limit: int = 10) -> List[MemoryNote]:
        """Get most recent notes"""
        notes = list(self.iterate_notes())
        notes.sort(key=lambda n: n.created_at, reverse=True)
        return notes[:limit]
    
    def count_notes(self) -> int:
        """Count total notes"""
        if not self.jsonl_path.exists():
            return 0
        with open(self.jsonl_path, "r") as f:
            return sum(1 for line in f if line.strip())
    
    def _rewrite_note(self, note: MemoryNote) -> None:
        """Rewrite a note in place (for updates) — atomic via temp file + os.replace()."""
        if not self.jsonl_path.exists():
            return
        
        # Read all notes
        notes = []
        updated = False
        with open(self.jsonl_path, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if data.get('id') == note.id:
                            notes.append(note.model_dump())
                            updated = True
                        else:
                            notes.append(data)
                    except:
                        pass
        
        if not updated:
            notes.append(note.model_dump())
        
        # Write to temp file in same directory, then atomically replace
        dir_path = self.jsonl_path.parent
        fd, tmp_path = tempfile.mkstemp(suffix='.jsonl', dir=str(dir_path))
        try:
            with os.fdopen(fd, 'w') as f:
                for n in notes:
                    f.write(json.dumps(n) + "\n")
            os.replace(tmp_path, self.jsonl_path)  # atomic on POSIX
            # Update cache
            if self._note_cache is not None:
                self._note_cache[note.id] = note
        except:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def export_snapshot(self, output_path: str) -> None:
        """Export full memory state for cold storage"""
        import shutil
        if self.jsonl_path.exists():
            shutil.copy(
                self.jsonl_path, 
                f"{output_path}/notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            )
