---
title: "Migrate JSONL Data to SQLite"
description: "Move a v2.1.x ZettelForge deployment from the legacy JSONL notes store to the v2.2.0 SQLite default backend, with backup and idempotent re-runs."
diataxis_type: "how-to"
audience: "Operator upgrading from v2.1.x"
tags: [migration, sqlite, jsonl, upgrade]
last_updated: "2026-04-16"
version: "2.2.0"
---

# Migrate JSONL Data to SQLite

Use this guide when you are upgrading an existing ZettelForge install
from v2.1.x (JSONL) to v2.2.x (SQLite default) and want to carry your
notes, knowledge graph, and entity index forward.

Fresh installs do **not** need this — SQLite is the default and
`MemoryManager()` will create an empty database in the configured data
directory on first use.

## Prerequisites

- ZettelForge **v2.2.0 or newer** installed (`pip install -U zettelforge`)
- Write access to your data directory (`~/.amem` by default, or whatever
  `AMEM_DATA_DIR` / `storage.data_dir` points at)
- Enough free disk for a full backup of the JSONL files alongside the
  new `zettelforge.db` file (expect roughly 1.5× the original size for
  the duration of the migration)

## What the script does

`scripts/migrate_jsonl_to_sqlite.py`:

1. Copies `notes.jsonl`, `kg_nodes.jsonl`, `kg_edges.jsonl`, and
   `entity_index.json` into `<data_dir>/backup_pre_sqlite/`.
2. Creates or re-uses `<data_dir>/zettelforge.db` via
   `SQLiteBackend` (WAL mode, 33-method ABC).
3. Writes every note with `INSERT OR REPLACE`, every entity with
   `INSERT OR IGNORE`, and upserts knowledge-graph nodes and edges.
4. Leaves the original JSONL files on disk so you can roll back.

The script is idempotent — running it twice produces the same database.

## Run the migration

```bash
# Dry run first — shows what would be imported without writing
python scripts/migrate_jsonl_to_sqlite.py --data-dir ~/.amem --dry-run

# Execute the migration
python scripts/migrate_jsonl_to_sqlite.py --data-dir ~/.amem
```

Expected output tail:

```
Migrated 7,193 notes
Migrated 12,408 KG nodes / 34,117 KG edges
Migrated 28,442 entity mappings
SQLite WAL checkpointed. Done.
```

## Verify

After the migration completes, point ZettelForge at the same data
directory and confirm your notes are reachable through SQLite:

```python
from zettelforge import MemoryManager

mm = MemoryManager()               # reads ~/.amem by default
print(mm.get_stats())              # total_notes should match the migration log
print(mm.recall("APT28", k=3))     # sanity-check retrieval
```

You can also inspect the database directly:

```bash
sqlite3 ~/.amem/zettelforge.db "SELECT COUNT(*) FROM notes;"
sqlite3 ~/.amem/zettelforge.db "SELECT COUNT(*) FROM kg_edges;"
```

## Roll back

If anything looks wrong, set the backend back to the legacy JSONL
paths (they were not deleted), investigate, and re-run:

```bash
ls ~/.amem/backup_pre_sqlite/
# notes.jsonl, kg_nodes.jsonl, kg_edges.jsonl, entity_index.json
```

The `zettelforge.db` file can be deleted at any time — it is a
derivative artifact and the migration can be re-run from the JSONL
originals.

## Clean up (optional)

Once you are confident SQLite is healthy, move the backup out of your
data directory so it does not confuse future tooling:

```bash
mv ~/.amem/backup_pre_sqlite ~/zettelforge-jsonl-backup-2026-04-16
# delete once a release cycle has passed with no regressions
```

## Related

- [Configuration Reference](../reference/configuration.md) — `backend`
  and `storage.data_dir` keys.
- [CHANGELOG v2.2.0](https://github.com/rolandpg/zettelforge/blob/master/CHANGELOG.md) —
  SQLite default rollout notes.
