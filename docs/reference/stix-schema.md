---
title: "STIX Ontology Schema Reference"
description: "All STIX 2.1 entity types, relation types, role assignments, TypeDB functions, and entity type mappings defined in stix_core.tql and stix_rules.tql."
diataxis_type: "reference"
audience: "Senior CTI Practitioner"
tags:
  - stix
  - typedb
  - ontology
  - knowledge-graph
  - schema
last_updated: "2026-04-09"
version: "2.0.0"
---

# STIX Ontology Schema Reference

Schema files: `src/zettelforge/schema/stix_core.tql`, `src/zettelforge/schema/stix_rules.tql`

---

## Shared Attributes

All STIX Domain Objects inherit from the abstract `stix-domain-object` entity.

| Attribute | TypeDB Type | Description |
|:----------|:------------|:------------|
| `stix-id` | `string` | STIX identifier. `@key` on `stix-domain-object`. |
| `name` | `string` | Display name. |
| `description` | `string` | Free-text description. |
| `created-at` | `datetime` | Creation timestamp. |
| `modified-at` | `datetime` | Last modification timestamp. |
| `confidence` | `double` | Confidence score (0.0--1.0). |
| `revoked` | `boolean` | Whether the object has been revoked. |
| `tier` | `string` | Epistemic tier: `A`, `B`, or `C`. |
| `importance` | `integer` | Importance score (1--10). Used by `zettel-note`. |
| `aliases` | `string` | Known aliases. Used by `threat-actor`. |

### Temporal Attributes

| Attribute | TypeDB Type | Used By |
|:----------|:------------|:--------|
| `valid-from` | `datetime` | `indicator`, `uses`, `targets` |
| `valid-until` | `datetime` | `indicator`, `uses`, `targets` |
| `first-observed` | `datetime` | `campaign` |
| `last-observed` | `datetime` | `campaign` |

### CTI-Specific Attributes

| Attribute | TypeDB Type | Used By |
|:----------|:------------|:--------|
| `external-id` | `string` | `attack-pattern`, `vulnerability` |
| `malware-types` | `string` | `malware` |
| `tool-types` | `string` | `tool` |
| `pattern` | `string` | `indicator` |
| `pattern-type` | `string` | `indicator` |
| `sophistication` | `string` | `threat-actor` |
| `resource-level` | `string` | `threat-actor` |
| `goals` | `string` | `threat-actor` |
| `objective` | `string` | `campaign` |
| `infrastructure-types` | `string` | `infrastructure` |
| `note-id` | `string` | `zettel-note` (`@key`) |

---

## Entity Types

### STIX Domain Objects

All SDOs inherit shared attributes from `stix-domain-object @abstract`.

| TypeDB Entity | STIX SDO | ZettelForge Alias | Key Attributes (beyond shared) | Plays Roles |
|:--------------|:---------|:------------------|:-------------------------------|:------------|
| `threat-actor` | `threat-actor` | `actor` | `aliases`, `goals`, `sophistication`, `resource-level` | `uses:user`, `targets:source`, `attributed-to:attributing`, `alias-of:canonical`, `alias-of:aliased` |
| `malware` | `malware` | `malware` | `malware-types` | `uses:used`, `indicates:indicated`, `mitigates:mitigated` |
| `tool` | `tool` | `tool` | `tool-types` | `uses:used`, `mitigates:mitigated` |
| `attack-pattern` | `attack-pattern` | -- | `external-id` | `uses:used`, `mitigates:mitigated`, `indicates:indicated` |
| `vulnerability` | `vulnerability` | `cve` | `external-id` | `targets:target`, `mitigates:mitigated` |
| `campaign` | `campaign` | -- | `objective`, `first-observed`, `last-observed` | `attributed-to:attributed`, `targets:source`, `uses:user` |
| `indicator` | `indicator` | -- | `pattern`, `pattern-type`, `valid-from`, `valid-until` | `indicates:indicating` |
| `infrastructure` | `infrastructure` | -- | `infrastructure-types` | `targets:target`, `uses:used` |

### Zettel Note (Bridge Entity)

| TypeDB Entity | STIX SDO | ZettelForge Alias | Key Attributes | Plays Roles |
|:--------------|:---------|:------------------|:---------------|:------------|
| `zettel-note` | *(custom)* | `note` | `note-id` (`@key`), `created-at`, `importance`, `tier` | `mentioned-in:note`, `supersedes:newer`, `supersedes:older` |

`zettel-note` does **not** inherit from `stix-domain-object`. It bridges the TypeDB knowledge graph to the LanceDB vector store via the `note-id` field.

---

## Relation Types

| Relation | Role: From | Role: To | Owns Attributes | Description |
|:---------|:-----------|:---------|:-----------------|:------------|
| `uses` | `user` | `used` | `stix-id`, `confidence`, `created-at`, `valid-from`, `valid-until`, `description` | Actor/campaign uses tool/malware/attack-pattern/infrastructure. |
| `targets` | `source` | `target` | `stix-id`, `confidence`, `created-at`, `valid-from`, `valid-until` | Actor/campaign targets vulnerability/infrastructure. |
| `attributed-to` | `attributing` | `attributed` | `stix-id`, `confidence`, `created-at` | Actor attributed to campaign. |
| `indicates` | `indicating` | `indicated` | `stix-id`, `confidence`, `created-at` | Indicator indicates malware/attack-pattern. |
| `mitigates` | `mitigating` | `mitigated` | `stix-id`, `confidence`, `created-at` | Course of action mitigates malware/tool/attack-pattern/vulnerability. |
| `mentioned-in` | `mentioned-entity` | `note` | `created-at` | STIX entity is mentioned in a zettel-note. |
| `supersedes` | `newer` | `older` | `created-at` | Newer note supersedes an older note. |
| `alias-of` | `canonical` | `aliased` | `confidence` | Canonical name maps to an alias. |

---

## Entity Type Mapping

| ZettelForge Type | TypeDB Entity | STIX 2.1 Type | Entity Index Key |
|:-----------------|:--------------|:--------------|:-----------------|
| `actor` | `threat-actor` | `threat-actor` | `actor` |
| `cve` | `vulnerability` | `vulnerability` | `cve` |
| `tool` | `tool` | `tool` | `tool` |
| `malware` | `malware` | `malware` | `malware` |
| `note` | `zettel-note` | *(custom)* | `note` |
| -- | `attack-pattern` | `attack-pattern` | -- |
| -- | `campaign` | `campaign` | `campaign` |
| -- | `indicator` | `indicator` | -- |
| -- | `infrastructure` | `infrastructure` | -- |

---

## TypeDB Functions

Defined in `stix_rules.tql`. These replace TypeDB 2.x inference rules.

### `get_aliases`

```python
fun get_aliases($actor: threat-actor) -> { threat-actor }
```

Returns all aliased threat-actors linked to `$actor` via the `alias-of` relation (canonical to aliased direction).

```typeql
match
    $a isa threat-actor, has name "APT28";
    $aliases in get_aliases($a);
fetch $aliases: name;
```

### `get_tools_used`

```python
fun get_tools_used($actor: threat-actor) -> { malware }
```

Returns all malware entities linked to `$actor` via the `uses` relation (user to used direction). Returns `malware` type only; does not return `tool` type entities.

```typeql
match
    $a isa threat-actor, has name "APT28";
    $m in get_tools_used($a);
fetch $m: name, malware-types;
```

### `get_entity_notes`

```python
fun get_entity_notes($sdo: stix-domain-object) -> { zettel-note }
```

Returns all `zettel-note` entities linked to any STIX domain object via the `mentioned-in` relation.

```typeql
match
    $v isa vulnerability, has external-id "CVE-2024-1234";
    $n in get_entity_notes($v);
fetch $n: note-id, importance;
```

---

## Knowledge Graph Edge Types (In-Memory)

The in-memory `KnowledgeGraph` (JSONL backend) uses these edge relationship strings, distinct from TypeDB relations:

| Edge Type | From Entity | To Entity | Created By |
|:----------|:------------|:----------|:-----------|
| `MENTIONED_IN` | any entity type | `note` | `remember()` |
| `USES_TOOL` | `actor` | `tool` | `remember()` (heuristic) |
| `EXPLOITS_CVE` | `actor`, `tool` | `cve` | `remember()` (heuristic) |
| `TARGETS_ASSET` | `actor`, `tool` | `asset` | `remember()` (heuristic) |
| `CONDUCTS_CAMPAIGN` | `actor` | `campaign` | `remember()` (heuristic) |
| `SUPERSEDES` | `note` | `note` | `mark_note_superseded()` (temporal edge) |

---

## LLM Quick Reference

ZettelForge's STIX ontology is defined in two TypeQL schema files loaded into TypeDB. `stix_core.tql` defines 9 entity types, 8 relation types, and their role assignments. `stix_rules.tql` defines 3 reusable functions.

**Entity hierarchy:** All STIX entities inherit from the abstract `stix-domain-object`, which owns shared attributes (`stix-id` as `@key`, `name`, `description`, `confidence`, `tier`, etc.). The exception is `zettel-note`, which is a standalone entity keyed on `note-id` that bridges TypeDB to LanceDB.

**Entity type mapping:** ZettelForge uses shorthand aliases in the entity indexer: `actor` maps to `threat-actor`, `cve` maps to `vulnerability`, `tool` and `malware` map directly. The `note` alias maps to `zettel-note`.

**Relations:** `uses` connects actors/campaigns to tools/malware/attack-patterns/infrastructure. `targets` connects actors/campaigns to vulnerabilities/infrastructure. `attributed-to` links actors to campaigns. `indicates` links indicators to malware/attack-patterns. `mitigates` links countermeasures to threats. `mentioned-in` bridges STIX entities to zettel-notes. `supersedes` tracks note evolution. `alias-of` maps canonical names to aliases.

**Functions:** `get_aliases` traverses alias-of chains for threat-actors. `get_tools_used` returns malware used by an actor via the uses relation. `get_entity_notes` returns all zettel-notes mentioning a given STIX entity.

**Dual backend:** When the backend is `typedb`, entities and relations live in TypeDB with full TypeQL query support. When the backend is `jsonl`, an in-memory knowledge graph stores edges with relationship strings like `MENTIONED_IN`, `USES_TOOL`, `EXPLOITS_CVE`, `TARGETS_ASSET`, `CONDUCTS_CAMPAIGN`, and `SUPERSEDES`. The in-memory graph infers entity-to-entity edges heuristically when entities co-occur in a note (e.g., if an actor and tool appear in the same note, a `USES_TOOL` edge is created).
