#!/usr/bin/env python3
"""
Rebuild ZettelForge memory index with local Ollama embeddings.
Clears existing vector table and re-ingests from MEMORY.md + daily notes.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "skills/zettelforge/src"))

from zettelforge.vector_memory import VectorMemory
from datetime import datetime
import lancedb

def load_notes(file_path: Path):
    if not file_path.exists():
        return []
    content = file_path.read_text(encoding="utf-8")
    # Split by § delimiter, skip headers
    entries = [e.strip() for e in content.split('§') if e.strip() and not e.strip().startswith('#')]
    return entries

def rebuild_index():
    print("Starting memory index rebuild with local Ollama...")

    vm = VectorMemory()
    print("DB path:", vm.db_path)

    # Force drop for clean rebuild
    try:
        vm.db = lancedb.connect(str(vm.db_path))
        if 'memories' in vm.db.list_tables():
            vm.db.drop_table("memories")
            print("Dropped existing 'memories' table for rebuild.")
    except:
        pass

    vm.init()

    # Sources to ingest
    sources = [
        Path("MEMORY.md"),
        Path("memory/2026-04-07.md"),
        Path("memory/2026-04-06.md"),
    ]

    total = 0
    for source in sources:
        if source.exists():
            entries = load_notes(source)
            print(f"Processing {len(entries)} entries from {source.name}")
            for entry in entries:
                if len(entry) < 20:
                    continue
                tags = ["memory", "cti"] if "CTI" in entry or "threat" in entry.lower() else ["memory"]
                vm.add(
                    text=entry,
                    tags=tags,
                    source=source.name,
                    session_key="rebuild-2026-04-07",
                    chunk=True,
                    overwrite=True
                )
                total += 1

    print(f"\nRebuild complete. {total} entries re-indexed with local Ollama embeddings.")
    print("Vector memory now fully rebuilt and operational.")

    # Quick validation search
    test_results = vm.search("ZettelForge or OpenCTI or Vault", top_k=3)
    print(f"Validation search returned {len(test_results)} results.")

if __name__ == "__main__":
    rebuild_index()
