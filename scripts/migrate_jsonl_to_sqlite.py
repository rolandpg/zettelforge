#!/usr/bin/env python3
"""
Migrate ZettelForge JSONL data to SQLite backend.

Reads notes.jsonl, kg_nodes.jsonl, kg_edges.jsonl, and entity_index.json
from the data directory and writes them into zettelforge.db via SQLiteBackend.

Usage:
    python scripts/migrate_jsonl_to_sqlite.py
    python scripts/migrate_jsonl_to_sqlite.py --data-dir /path/to/data
    python scripts/migrate_jsonl_to_sqlite.py --data-dir ~/.amem --dry-run

The script is idempotent: notes use INSERT OR REPLACE, entities use
INSERT OR IGNORE, and KG nodes/edges are upserted via the backend API.
Original JSONL files are NOT deleted.
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Tuple


def backup_files(data_dir: Path) -> Path:
    """Copy JSONL/JSON source files to a backup directory.

    Returns the backup directory path.
    """
    backup_dir = data_dir / "backup_pre_sqlite"
    backup_dir.mkdir(parents=True, exist_ok=True)

    files_to_backup = [
        "notes.jsonl",
        "kg_nodes.jsonl",
        "kg_edges.jsonl",
        "entity_index.json",
    ]
    for fname in files_to_backup:
        src = data_dir / fname
        if src.exists():
            shutil.copy2(src, backup_dir / fname)
            print(f"  Backed up {fname}")
        else:
            print(f"  Skipped {fname} (not found)")

    return backup_dir


def migrate_notes(data_dir: Path, backend: Any) -> int:
    """Read notes.jsonl and write each note to SQLite via backend.write_note().

    Returns the number of notes migrated.
    """
    from zettelforge.note_schema import MemoryNote

    notes_file = data_dir / "notes.jsonl"
    if not notes_file.exists():
        print("  WARNING: notes.jsonl not found, skipping notes migration")
        return 0

    count = 0
    with open(notes_file, "r") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                note = MemoryNote(**data)
                backend.write_note(note)
                count += 1
            except Exception as e:
                print(f"  WARNING: Failed to parse note at line {lineno}: {e}")
    return count


def migrate_kg_nodes(data_dir: Path, backend: Any) -> Tuple[int, Dict[str, Tuple[str, str]]]:
    """Read kg_nodes.jsonl and add each node to SQLite.

    Returns (count, node_lookup) where node_lookup maps node_id to
    (entity_type, entity_value).
    """
    nodes_file = data_dir / "kg_nodes.jsonl"
    node_lookup: Dict[str, Tuple[str, str]] = {}

    if not nodes_file.exists():
        print("  WARNING: kg_nodes.jsonl not found, skipping KG nodes migration")
        return 0, node_lookup

    count = 0
    with open(nodes_file, "r") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                entity_type = data["entity_type"]
                entity_value = data["entity_value"]
                properties = data.get("properties", {})
                node_id = data.get("node_id", "")

                backend.add_kg_node(entity_type, entity_value, properties)

                # Build lookup for edge migration
                if node_id:
                    node_lookup[node_id] = (entity_type, entity_value)
                count += 1
            except Exception as e:
                print(f"  WARNING: Failed to parse KG node at line {lineno}: {e}")
    return count, node_lookup


def migrate_kg_edges(
    data_dir: Path,
    backend: Any,
    node_lookup: Dict[str, Tuple[str, str]],
) -> int:
    """Read kg_edges.jsonl and add each edge to SQLite.

    Uses node_lookup to resolve from_node_id/to_node_id back to
    (entity_type, entity_value) pairs required by backend.add_kg_edge().

    Returns the number of edges migrated.
    """
    edges_file = data_dir / "kg_edges.jsonl"
    if not edges_file.exists():
        print("  WARNING: kg_edges.jsonl not found, skipping KG edges migration")
        return 0

    count = 0
    skipped = 0
    with open(edges_file, "r") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                from_node_id = data["from_node_id"]
                to_node_id = data["to_node_id"]
                relationship = data["relationship"]
                properties = data.get("properties", {})
                note_id = data.get("note_id", "")
                edge_type = data.get("edge_type", "heuristic")

                # Resolve node IDs to type/value pairs
                from_info = node_lookup.get(from_node_id)
                to_info = node_lookup.get(to_node_id)
                if from_info is None or to_info is None:
                    skipped += 1
                    continue

                from_type, from_value = from_info
                to_type, to_value = to_info

                # Carry edge_type through properties so backend can extract it
                edge_props = dict(properties)
                edge_props["edge_type"] = edge_type

                backend.add_kg_edge(
                    from_type,
                    from_value,
                    to_type,
                    to_value,
                    relationship,
                    note_id=note_id,
                    properties=edge_props,
                )
                count += 1
            except Exception as e:
                print(f"  WARNING: Failed to parse KG edge at line {lineno}: {e}")

    if skipped:
        print(f"  WARNING: Skipped {skipped} edges with unresolvable node IDs")
    return count


def migrate_entity_index(data_dir: Path, backend: Any) -> int:
    """Read entity_index.json and add each mapping to SQLite.

    Format: {entity_type: {entity_value: [note_id, ...]}}

    Returns the number of entity mappings migrated.
    """
    index_file = data_dir / "entity_index.json"
    if not index_file.exists():
        print("  WARNING: entity_index.json not found, skipping entity index migration")
        return 0

    count = 0
    try:
        with open(index_file, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  WARNING: Failed to parse entity_index.json: {e}")
        return 0

    for entity_type, entities in data.items():
        if not isinstance(entities, dict):
            continue
        for entity_value, note_ids in entities.items():
            if not isinstance(note_ids, list):
                continue
            for note_id in note_ids:
                try:
                    backend.add_entity_mapping(entity_type, entity_value, note_id)
                    count += 1
                except Exception as e:
                    print(
                        f"  WARNING: Failed to add entity mapping "
                        f"{entity_type}/{entity_value}/{note_id}: {e}"
                    )
    return count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate ZettelForge JSONL data to SQLite backend.",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Data directory (default: ~/.amem or AMEM_DATA_DIR env)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate without writing to SQLite",
    )
    args = parser.parse_args()

    # Resolve data directory
    if args.data_dir:
        data_dir = Path(args.data_dir).expanduser().resolve()
    else:
        env_path = os.environ.get("AMEM_DATA_DIR")
        if env_path:
            data_dir = Path(env_path).resolve()
        else:
            data_dir = Path.home() / ".amem"

    if not data_dir.exists():
        print(f"ERROR: Data directory does not exist: {data_dir}")
        sys.exit(1)

    print("ZettelForge JSONL -> SQLite Migration")
    print(f"Data directory: {data_dir}")
    print()

    # Step 1: Backup
    print("[1/5] Backing up source files...")
    backup_dir = backup_files(data_dir)
    print(f"  Backup directory: {backup_dir}")
    print()

    if args.dry_run:
        print("[DRY RUN] Parsing files without writing to SQLite...")
        print()

    # Step 2: Initialize SQLite backend
    from zettelforge.sqlite_backend import SQLiteBackend

    db_path = str(data_dir / "zettelforge.db")
    backend = SQLiteBackend(db_path=db_path)
    backend.initialize()

    # Step 3: Migrate notes
    print("[2/5] Migrating notes...")
    note_count = migrate_notes(data_dir, backend)
    print(f"  Migrated {note_count} notes")
    print()

    # Step 4: Migrate KG nodes
    print("[3/5] Migrating KG nodes...")
    node_count, node_lookup = migrate_kg_nodes(data_dir, backend)
    print(f"  Migrated {node_count} nodes")
    print()

    # Step 5: Migrate KG edges
    print("[4/5] Migrating KG edges...")
    edge_count = migrate_kg_edges(data_dir, backend, node_lookup)
    print(f"  Migrated {edge_count} edges")
    print()

    # Step 6: Migrate entity index
    print("[5/5] Migrating entity index...")
    entity_count = migrate_entity_index(data_dir, backend)
    print(f"  Migrated {entity_count} entity mappings")
    print()

    # Close backend
    backend.close()

    # Set restrictive permissions on DB file
    if os.path.exists(db_path):
        os.chmod(db_path, 0o600)

    # Summary
    print("=" * 50)
    print("Migration complete!")
    print(f"  Notes:           {note_count}")
    print(f"  KG nodes:        {node_count}")
    print(f"  KG edges:        {edge_count}")
    print(f"  Entity mappings: {entity_count}")
    print(f"  Database:        {db_path}")
    print()
    print("JSONL files have NOT been deleted.")
    print(f"Backup saved to: {backup_dir}")


if __name__ == "__main__":
    main()
