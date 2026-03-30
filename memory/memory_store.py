"""
Memory Note Storage - JSONL Read/Write Utilities
Roland Fleet Agentic Memory Architecture V1.0
"""
import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Iterator
from note_schema import MemoryNote


class MemoryStore:
    """JSONL-based memory note storage with LanceDB vector indexing"""
    
    def __init__(
        self, 
        jsonl_path: str = "/home/rolandpg/.openclaw/workspace/memory/notes.jsonl",
        lance_path: str = "/home/rolandpg/.openclaw/workspace/vectordb/"
    ):
        self.jsonl_path = Path(jsonl_path)
        self.lance_path = Path(lance_path)
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        self.lance_path.mkdir(parents=True, exist_ok=True)
        self._lancedb = None
    
    @property
    def lancedb(self):
        """Lazy-load LanceDB"""
        if self._lancedb is None:
            try:
                import lancedb
                self._lancedb = lancedb.connect(str(self.lance_path))
            except Exception as e:
                print(f"LanceDB connection failed: {e}")
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
        
        # Index in LanceDB if available
        if self.lancedb:
            self._index_in_lance(note)
    
    def _index_in_lance(self, note: MemoryNote) -> None:
        """Index note in LanceDB vector store"""
        try:
            table_name = f"notes_{note.metadata.domain}"
            if table_name not in self.lancedb.table_names():
                self.lancedb.create_table(table_name, schema={
                    "id": "string",
                    "vector": "vector<float, 768>",
                    "content": "string",
                    "context": "string",
                    "keywords": "string",
                    "tags": "string",
                    "created_at": "string"
                })
            
            table = self.lancedb.open_table(table_name)
            table.add([{
                "id": note.id,
                "vector": note.embedding.vector if note.embedding.vector else [0.0] * 768,
                "content": note.content.raw[:500],  # Truncate for index
                "context": note.semantic.context,
                "keywords": ",".join(note.semantic.keywords),
                "tags": ",".join(note.semantic.tags),
                "created_at": note.created_at
            }])
        except Exception as e:
            print(f"LanceDB indexing failed: {e}")
    
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
                        print(f"Failed to parse note: {e}")
        return notes
    
    def iterate_notes(self) -> Iterator[MemoryNote]:
        """Iterate through notes without loading all into memory"""
        if not self.jsonl_path.exists():
            return
        
        with open(self.jsonl_path, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        yield MemoryNote(**data)
                    except Exception as e:
                        print(f"Failed to parse note: {e}")
    
    def get_note_by_id(self, note_id: str) -> Optional[MemoryNote]:
        """Retrieve a specific note by ID"""
        for note in self.iterate_notes():
            if note.id == note_id:
                return note
        return None
    
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
        """Rewrite a note in place (for updates)"""
        notes = []
        updated = False
        
        if not self.jsonl_path.exists():
            return
        
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
        
        with open(self.jsonl_path, "w") as f:
            for n in notes:
                f.write(json.dumps(n) + "\n")
    
    def export_snapshot(self, output_path: str) -> None:
        """Export full memory state for cold storage"""
        import shutil
        if self.jsonl_path.exists():
            shutil.copy(
                self.jsonl_path, 
                f"{output_path}/notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            )
