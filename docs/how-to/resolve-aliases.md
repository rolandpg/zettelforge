---
title: "Resolve Threat Actor Aliases"
description: "Use AliasResolver to map threat actor aliases (Fancy Bear, Pawn Storm) to canonical names (APT28) via TypeDB and local fallback."
diataxis_type: "how-to"
audience: "CTI analysts, platform engineers configuring entity resolution"
tags: [alias-resolver, entity-resolution, typedb, threat-actor, cti]
last_updated: "2026-04-09"
version: "2.0.0"
---

# Resolve Threat Actor Aliases

Map threat actor aliases to canonical names automatically. ZettelForge's `AliasResolver` tries TypeDB `alias-of` relations first, then falls back to a local JSON file with hardcoded mappings.

## Prerequisites

- ZettelForge installed (`pip install zettelforge`)
- TypeDB running (optional; local JSON fallback works without it)

## Steps

### 1. Observe automatic alias resolution via `recall_actor()`

```python
from zettelforge.memory_manager import MemoryManager

mm = MemoryManager()

# "Fancy Bear" resolves to "apt28" internally
notes = mm.recall_actor("Fancy Bear", k=5)

print(f"Found {len(notes)} notes for Fancy Bear (resolved to apt28)")
for note in notes:
    print(f"  {note.id}: {note.content.raw[:80]}")
```

All query methods resolve aliases before lookup. These queries return identical results:

```python
mm.recall_actor("Fancy Bear")     # resolves -> apt28
mm.recall_actor("Pawn Storm")     # resolves -> apt28
mm.recall_actor("Forest Blizzard")# resolves -> apt28
mm.recall_actor("APT28")          # already canonical
```

### 2. Use AliasResolver directly

```python
from zettelforge.alias_resolver import AliasResolver

resolver = AliasResolver()

# Actor aliases
print(resolver.resolve("actor", "Fancy Bear"))      # "apt28"
print(resolver.resolve("actor", "Cozy Bear"))        # "apt29"
print(resolver.resolve("actor", "Hidden Cobra"))     # "lazarus"
print(resolver.resolve("actor", "Bronze Silhouette"))# "volt typhoon"

# Tool aliases
print(resolver.resolve("tool", "CS Beacon"))         # "cobalt strike"
print(resolver.resolve("tool", "MSF"))               # "metasploit"

# Unknown entities pass through unchanged
print(resolver.resolve("actor", "NewGroup42"))       # "newgroup42"
```

> [!NOTE]
> Resolution is case-insensitive and hyphen-normalized. "Fancy Bear", "fancy-bear", "FANCY BEAR" all resolve to "apt28".

### 3. View built-in alias mappings

The seed script at `src/zettelforge/schema/seed_aliases.py` defines all built-in mappings:

| Canonical | Aliases |
|-----------|---------|
| `apt28` | Fancy Bear, Pawn Storm, Sofacy, Sednit, Strontium, Forest Blizzard |
| `apt29` | Cozy Bear, The Dukes, Nobelium, Midnight Blizzard |
| `lazarus` | Lazarus Group, Hidden Cobra, Zinc, Diamond Sleet |
| `volt typhoon` | Bronze Silhouette, Vanguard Panda |
| `sandworm` | Voodoo Bear, Iridium, Seashell Blizzard |
| `cobalt strike` | CobaltStrike, CS Beacon |

### 4. Add custom aliases via the JSON file

Custom aliases are stored in `~/.amem/entity_aliases.json`. Create or edit the file:

```python
import json
from pathlib import Path

alias_file = Path.home() / ".amem" / "entity_aliases.json"
alias_file.parent.mkdir(parents=True, exist_ok=True)

# Load existing aliases
aliases = {}
if alias_file.exists():
    aliases = json.loads(alias_file.read_text())

# Add custom actor alias
aliases.setdefault("actor", {})
aliases["actor"]["charming kitten"] = "apt35"
aliases["actor"]["phosphorus"] = "apt35"

# Add custom tool alias
aliases.setdefault("tool", {})
aliases["tool"]["sliver c2"] = "sliver"

alias_file.write_text(json.dumps(aliases, indent=2))
print(f"Written to {alias_file}")
```

Verify:

```python
resolver = AliasResolver()  # Reloads from file
print(resolver.resolve("actor", "Charming Kitten"))  # "apt35"
```

### 5. Seed TypeDB with alias relations

For production deployments with TypeDB:

```bash
python -m zettelforge.schema.seed_aliases
```

```
Seeded 42 alias relations into TypeDB.
```

> [!TIP]
> TypeDB alias resolution is queried live on each `resolve()` call (with caching). Adding aliases to TypeDB makes them available immediately without restarting ZettelForge.

### 6. Verify TypeDB alias resolution

```python
from zettelforge.alias_resolver import AliasResolver

resolver = AliasResolver()

# Force TypeDB path (bypasses local JSON)
canonical = resolver._try_typedb_resolve("actor", "fancy bear")
print(f"TypeDB resolved: {canonical}")  # "apt28" or None if TypeDB unavailable
```

> [!WARNING]
> If TypeDB is unreachable, `_try_typedb_resolve()` returns `None` and sets `_typedb_available = False` for the lifetime of that `AliasResolver` instance. The local JSON fallback handles all built-in aliases.

## LLM Quick Reference

**Task**: Map threat actor and tool aliases to canonical names for consistent entity indexing.

**Resolution order**: (1) TypeDB `alias-of` relation query, (2) local `~/.amem/entity_aliases.json`, (3) hardcoded fallback dict in `AliasResolver.__init__()`, (4) passthrough (lowercased input returned as-is).

**Automatic usage**: All `MemoryManager` methods (`remember()`, `recall()`, `recall_actor()`, `traverse_graph()`, `get_entity_relationships()`) resolve aliases internally before indexing or querying.

**Direct API**: `AliasResolver().resolve(entity_type, entity_value)` returns canonical name as `str`. Entity types: "actor", "tool", "malware".

**Custom aliases**: Write to `~/.amem/entity_aliases.json` with structure `{"actor": {"alias": "canonical"}, "tool": {"alias": "canonical"}}`. Reload by creating a new `AliasResolver()` instance.

**TypeDB seeding**: `python -m zettelforge.schema.seed_aliases` inserts `alias-of` relations for all known actors (APT28, APT29, APT31, Lazarus, Sandworm, Volt Typhoon, Kimsuky, Turla, MuddyWater) and tools (Cobalt Strike, Metasploit, Mimikatz).

**Normalization**: Input is lowercased and hyphens normalized to spaces before lookup. "Fancy-Bear" and "fancy bear" are equivalent.
