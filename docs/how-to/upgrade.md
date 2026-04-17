---
title: "Upgrade ZettelForge"
description: "Upgrade paths between ZettelForge releases, with required migration steps, breaking changes to watch for, and rollback instructions."
diataxis_type: "how-to"
audience: "Operator / Maintainer"
tags: [upgrade, migration, release, breaking-changes]
last_updated: "2026-04-16"
version: "2.2.0"
---

# Upgrade ZettelForge

Use this as a checklist whenever you move between minor releases. For
the full list of changes per release see
[CHANGELOG.md](https://github.com/rolandpg/zettelforge/blob/master/CHANGELOG.md).

## Upgrade matrix

| From → To | Required action | Data migration? |
|-----------|-----------------|-----------------|
| 2.2.x → 2.2.y (patch) | `pip install -U zettelforge` | No |
| 2.1.x → 2.2.x | `pip install -U zettelforge` + run JSONL → SQLite migration | **Yes** |
| 2.0.x → 2.2.x | Upgrade in two hops via 2.1.x is recommended but not required | **Yes** |
| < 2.0 | Not supported — export notes manually, fresh-install 2.2.x |

## 2.1.x → 2.2.x

The headline change is the **SQLite default backend**. Notes, the
knowledge graph, and the entity index now live in
`<data_dir>/zettelforge.db` instead of a loose set of JSONL files.

### Steps

1. `pip install -U 'zettelforge>=2.2.0'`
2. Back up your data directory:
   ```bash
   cp -a ~/.amem ~/.amem.pre-2.2
   ```
3. Run the migration — see
   [Migrate JSONL to SQLite](migrate-jsonl-to-sqlite.md).
4. Confirm with `mm.get_stats()` that `total_notes` matches the
   migration log.

### What else changed in v2.2.0

- **Causal chain retrieval** now works for `why did X happen?` queries.
  If you relied on the old (silent) behaviour, audit existing
  downstream code — `edge_type="causal"` is now filterable.
- **Memory evolution is on by default** on `remember()` once the
  store has ≥ 3 notes. Pass `evolve=False` to opt out.
- **STIX alignment:** APT/UNC/TA/FIN groups now store as
  `intrusion_set`. `recall_actor()` remains backward-compatible and
  searches `actor`, `threat_actor`, and `intrusion_set`.
- **Governance controls consolidated** into
  `governance/controls.yaml`. CI now runs spec-drift detection
  automatically — no action required unless you have forked the
  governance test suite.
- **MCP server is now a first-class module:**
  `python -m zettelforge.mcp` replaces the v2.1.x shim at
  `web/mcp_server.py` (the shim still works for backward compat).

## 2.0.x → 2.1.x (interim notes)

- Dual-stream write path lands in 2.1.1. `remember()` now returns in
  ~45 ms; pass `sync=True` where you need the background enrichment
  complete before a subsequent `recall()`.
- P0 security fixes — SQL injection in `VectorMemory.search/delete`
  was fixed in 2.1.1. Upgrade immediately.
- File locking on JSONL and entity-index writes added in 2.1.1.

## Rollback

All of ZettelForge's state lives in the configured data directory,
plus the installed package. To roll back:

```bash
# 1. Pin the previous version
pip install 'zettelforge==2.1.1'

# 2. Restore the JSONL data directory (the SQLite file is ignored by
#    older releases)
rm -rf ~/.amem
cp -a ~/.amem.pre-2.2 ~/.amem
```

The SQLite database file (`zettelforge.db`) is harmless left in place
— older versions will not read it, and deleting it does not affect
JSONL data.

## Related

- [Migrate JSONL to SQLite](migrate-jsonl-to-sqlite.md)
- [Troubleshoot](troubleshoot.md)
- [CHANGELOG.md](https://github.com/rolandpg/zettelforge/blob/master/CHANGELOG.md)
