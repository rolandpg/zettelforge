#!/usr/bin/env python3
"""
ZettelForge Index Rebuild Utility
Rebuilds entity index and reindexes LanceDB from JSONL notes.

Usage:
    python scripts/rebuild_index.py [--jsonl PATH] [--lance PATH]

Run periodically via:
    - systemd timer (recommended)
    - cron job
    - After bulk note deletions
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/src')

import argparse
from pathlib import Path

from zettelforge.memory_store import MemoryStore, get_default_data_dir
from zettelforge.entity_indexer import EntityIndexer


def rebuild_indexes(jsonl_path=None, lance_path=None):
    """Rebuild entity index and reindex LanceDB from JSONL."""
    
    # Use defaults if not specified
    data_dir = get_default_data_dir()
    jsonl_path = Path(jsonl_path) if jsonl_path else data_dir / "notes.jsonl"
    lance_path = Path(lance_path) if lance_path else data_dir / "vectordb"
    
    print(f"Rebuilding indexes from: {jsonl_path}")
    print(f"LanceDB path: {lance_path}")
    
    # Initialize store
    store = MemoryStore(jsonl_path=str(jsonl_path), lance_path=str(lance_path))
    
    # Count notes
    notes = list(store.iterate_notes())
    print(f"\nFound {len(notes)} notes in JSONL")
    
    if len(notes) == 0:
        print("No notes to index. Done.")
        return
    
    # 1. Rebuild entity index
    print("\n[1/2] Rebuilding entity index...")
    indexer = EntityIndexer(index_path=str(data_dir / "entity_index.json"))
    result = indexer.build()
    print(f"  Notes indexed: {result['notes_indexed']}")
    print(f"  Stats: {result['stats']}")
    
    # 2. Reindex LanceDB
    print("\n[2/2] Reindexing LanceDB...")
    if store.lancedb is not None:
        # Drop existing tables so we rebuild from scratch
        existing = store.lancedb.list_tables()
        tables = existing.tables if hasattr(existing, 'tables') else (existing if isinstance(existing, list) else [])
        for t in tables:
            if t.startswith('notes_'):
                store.lancedb.drop_table(t)
        print(f"  Dropped {len([t for t in tables if t.startswith('notes_')])} stale table(s)")
        
        # Count by domain
        domain_counts = {}
        for note in notes:
            domain = note.metadata.domain
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        print(f"  Notes by domain: {domain_counts}")
        
        # Reindex each note
        indexed = 0
        for i, note in enumerate(notes):
            try:
                store._index_in_lance(note)
                indexed += 1
                if (i + 1) % 50 == 0:
                    print(f"    Indexed {i + 1}/{len(notes)}...")
            except Exception as e:
                print(f"    Error indexing {note.id}: {e}")
        
        print(f"  Indexed: {indexed}/{len(notes)} notes")
        
        # Verify
        final = store.lancedb.list_tables()
        tables = final.tables if hasattr(final, 'tables') else (final if isinstance(final, list) else [])
        print(f"  Final tables: {tables}")
        
        for t in tables:
            if t.startswith('notes_'):
                tbl = store.lancedb.open_table(t)
                print(f"    {t}: {len(tbl)} rows")
    else:
        print("  LanceDB not available, skipping vector indexing")
    
    # Summary
    print("\n" + "="*50)
    print("REBUILD COMPLETE")
    print("="*50)
    print(f"JSONL notes: {len(notes)}")
    print(f"Entity index: {result['stats']}")
    if store.lancedb is not None:
        print(f"LanceDB: Reindexed {indexed} notes")


def main():
    parser = argparse.ArgumentParser(description="Rebuild ZettelForge indexes")
    parser.add_argument("--jsonl", help="Path to JSONL file", default=None)
    parser.add_argument("--lance", help="Path to LanceDB directory", default=None)
    args = parser.parse_args()
    
    rebuild_indexes(args.jsonl, args.lance)


if __name__ == "__main__":
    main()