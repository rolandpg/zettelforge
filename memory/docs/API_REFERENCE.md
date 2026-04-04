# A-MEM API Reference

**Version:** 1.3  
**Date:** 2026-04-02  
**Project:** A-MEM (Agentic Memory)

---

## 1. MemoryManager API

### Constructor

```python
MemoryManager(
    jsonl_path: str = "/home/rolandpg/.openclaw/workspace/memory/notes.jsonl",
    lance_path: str = "/home/rolandpg/.openclaw/workspace/vectordb/",
    cold_path: str = "/media/rolandpg/USB-HDD"
)
```

### Core Methods

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `remember` | `remember(content, source_type, source_ref, domain, auto_evolve)` | `(MemoryNote, str)` | Create a new memory note |
| `recall` | `recall(query, domain, k, include_links, exclude_superseded)` | `List[MemoryNote]` | Semantic search |
| `recall_cve` | `recall_cve(cve_id, k, exclude_superseded)` | `List[MemoryNote]` | Fast CVE lookup |
| `recall_actor` | `recall_actor(actor_name, k, exclude_superseded)` | `List[MemoryNote]` | Fast actor lookup |
| `recall_tool` | `recall_tool(tool_name, k, exclude_superseded)` | `List[MemoryNote]` | Fast tool lookup |
| `recall_campaign` | `recall_campaign(campaign_name, k, exclude_superseded)` | `List[MemoryNote]` | Fast campaign lookup |
| `recall_sector` | `recall_sector(sector, k, exclude_superseded)` | `List[MemoryNote]` | Fast sector lookup |
| `recall_entity` | `recall_entity(entity_type, entity_value, k, exclude_superseded)` | `List[MemoryNote]` | Generic entity lookup |
| `get_snapshot` | `get_snapshot()` | `List[MemoryNote]` | Current memory state |
| `get_stats` | `get_stats()` | `Dict` | System statistics |

### Advanced Methods

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `get_context` | `get_context(query, domain, k, token_budget)` | `str` | Formatted context for prompts |
| `get_subagent_context` | `get_subagent_context(task, domain, k, token_budget)` | `str` | Scoped context for subagents |
| `ingest_subagent_output` | `ingest_subagent_output(task_id, output, observations, domain)` | `(MemoryNote, str)` | Store subagent results |
| `mark_note_superseded` | `mark_note_superseded(note_id, superseded_by_id)` | `bool` | Manually mark supersession |
| `get_superseded_notes` | `get_superseded_notes()` | `List[MemoryNote]` | Get all superseded notes |
| `archive_low_confidence_notes` | `archive_low_confidence_notes(threshold, dry_run)` | `Dict` | Archive low-confidence notes |
| `get_archived_notes` | `get_archived_notes()` | `List[str]` | List archived note IDs |
| `get_entity_stats` | `get_entity_stats()` | `Dict` | Entity index statistics |
| `rebuild_entity_index` | `rebuild_entity_index()` | `Dict` | Force rebuild entity index |
| `daily_maintenance` | `daily_maintenance()` | `Dict` | Daily maintenance tasks |
| `weekly_maintenance` | `weekly_maintenance()` | `Dict` | Weekly maintenance tasks |
| `snapshot` | `snapshot()` | `str` | Export memory snapshot |
| `synthesize` | `synthesize(query, format, k, include_graph, tier_filter)` | `Dict` | LLM-based answer synthesis |
| `retrieve_synthesis_context` | `retrieve_synthesis_context(query, k, tier_filter, expand_graph)` | `Dict` | Hybrid context retrieval for synthesis |
| `validate_synthesis` | `validate_synthesis(response)` | `(bool, List[str])` | Validate synthesis response |

### Global Access

```python
# Get global instance
mm = get_memory_manager()
```

---

## 2. MemoryNote Schema

### Content

```python
class Content:
    raw: str                    # Raw input text
    source_type: str           # e.g., "conversation", "cisa_advisory"
    source_ref: str            # Reference like "subagent:task_id"
```

### Semantic

```python
class Semantic:
    context: str               # One-sentence summary
    keywords: List[str]        # Up to 7 keywords
    tags: List[str]           # Up to 5 tags
    entities: List[str]        # Extracted entities
```

### Embedding

```python
class Embedding:
    model: str = "nomic-embed-text-v2-moe"
    vector: List[float]        # 768-dim vector
    dimensions: int = 768
    input_hash: str            # SHA256 hash
```

### Links

```python
class Links:
    related: List[str]                # Related note IDs
    superseded_by: Optional[str]      # Superseding note ID
    supersedes: List[str]             # Superseded note IDs
    causal_chain: List[str]           # Causal relationship chain
```

### Metadata

```python
class Metadata:
    access_count: int = 0
    last_accessed: Optional[str] = None
    evolution_count: int = 0
    confidence: float = 1.0
    ttl: Optional[int] = None
    domain: str = "general"
    tier: str = "B"  # A, B, or C
```

---

## 3. AliasResolver API

### Constructor

```python
AliasResolver(alias_map_dir: str = None)  # Default: memory/alias_maps/
```

### Methods

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `resolve` | `resolve(entity_type, raw_name)` | `str` | Resolve to canonical name |
| `get_canonical` | `get_canonical(entity_type, raw_name)` | `Optional[str]` | Get canonical or None |
| `get_all_aliases` | `get_all_aliases(entity_type, canonical)` | `List[str]` | Get all aliases for canonical |
| `get_mitre_id` | `get_mitre_id(entity_type, canonical)` | `Optional[str]` | Get MITRE ATT&CK ID |
| `reload` | `reload()` | `None` | Reload maps from disk |
| `stats` | `stats()` | `dict` | Coverage statistics |
| `add_alias` | `add_alias(entity_type, canonical, alias)` | `bool` | Add new alias |
| `add_canonical_with_alias` | `add_canonical_with_alias(entity_type, canonical, alias, mitre_id)` | `bool` | Add new canonical entry |
| `is_known_alias` | `is_known_alias(entity_type, name)` | `bool` | Check if alias exists |
| `is_known_canonical` | `is_known_canonical(entity_type, name)` | `bool` | Check if canonical exists |

### resolve_all() Helper

```python
def resolve_all(extracted: Dict, resolver: AliasResolver) -> Dict:
    """Resolve all raw entities to canonical forms"""
```

---

## 4. EntityIndexer API

### Constructor

```python
EntityIndexer(
    jsonl_path: str = "notes.jsonl",
    index_path: str = "entity_index.json"
)
```

### Methods

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `build` | `build()` | `Dict` | Rebuild index from all notes |
| `add_note` | `add_note(note_id, content_raw)` | `Dict` | Index a single note |
| `add_note_resolved` | `add_note_resolved(note_id, resolved_entities)` | `None` | Index with pre-resolved entities |
| `remove_note` | `remove_note(note_id)` | `None` | Remove note from index |
| `get_note_ids` | `get_note_ids(entity_type, entity_value)` | `List[str]` | Get note IDs for entity |
| `has_entity` | `has_entity(entity_type, entity_value)` | `bool` | Check entity existence |
| `get_cves` | `get_cves()` | `List[str]` | All CVEs in index |
| `get_actors` | `get_actors()` | `List[str]` | All actors in index |
| `get_tools` | `get_tools()` | `List[str]` | All tools in index |
| `get_all_entities` | `get_all_entities()` | `Dict[str, int]` | Entity counts by type |
| `stats` | `stats()` | `Dict` | Index statistics |
| `load` | `load()` | `bool` | Load index from disk |

### EntityExtractor

```python
class EntityExtractor:
    def extract_all(self, text: str) -> Dict[str, List[str]]:
        # Returns: {'cves': [...], 'actors': [...], 'tools': [...], 'campaigns': [...], 'sectors': [...]}
```

---

## 5. LinkGenerator API

### Constructor

```python
LinkGenerator(
    llm_model: str = "nemotron-3-nano",
    similarity_threshold: float = 0.65
)
```

### Methods

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `generate_links` | `generate_links(new_note, candidate_notes, max_candidates)` | `List[Dict]` | Generate links from new note |
| `update_note_links` | `update_note_links(note, outgoing_links, all_notes)` | `MemoryNote` | Apply links to note |

### Relationship Types

- `SUPPORTS`: Corroborates information
- `CONTRADICTS`: Conflicts information
- `EXTENDS`: Adds nuance
- `CAUSES`: Causal relationship
- `RELATED`: Topically connected

---

## 6. EvolutionDecider API

### Constructor

```python
EvolutionDecider(llm_model: str = "nemotron-3-nano")
```

### Methods

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `assess` | `assess(new_note, existing_note, log_reasoning)` | `Tuple[str, str]` | Assess evolution need |

### Decision Values

| Decision | Meaning |
|----------|---------|
| `NO_CHANGE` | No update needed |
| `UPDATE_CONTEXT` | Revise context summary |
| `UPDATE_TAGS` | Update tags |
| `UPDATE_BOTH` | Update both |
| `SUPERSEDE` | Archive old, update new |
| `REJECT` | Tier constraint prevented |

---

## 7. MemoryEvolver API

### Constructor

```python
MemoryEvolver(store: MemoryStore = None, evolver: EvolutionDecider = None)
```

### Methods

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `evolve_note` | `evolve_note(new_note, existing_note, decision, reason)` | `MemoryNote` | Apply evolution |
| `run_evolution_cycle` | `run_evolution_cycle(new_note)` | `Dict` | Run full evolution cycle |

---

## 8. EmbeddingGenerator API

### Constructor

```python
EmbeddingGenerator(
    model: str = "nomic-embed-text-v2-moe",
    use_llama_server: Optional[bool] = None
)
```

### Methods

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `embed` | `embed(text)` | `List[float]` | Single text embedding |
| `embed_batch` | `embed_batch(texts)` | `List[List[float]]` | Batch embeddings |
| `embed_note_fields` | `embed_note_fields(content, context, keywords, tags)` | `List[float]` | Note embedding |
| `compute_hash` | `compute_hash(text)` | `str` | SHA256 hash |
| `cosine_similarity` | `cosine_similarity(a, b)` | `float` | Vector similarity |

---

## 9. VectorRetriever API

### Constructor

```python
VectorRetriever(similarity_threshold: float = 0.30)
```

### Methods

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `retrieve` | `retrieve(query, domain, k, include_links)` | `List[MemoryNote]` | Semantic search |
| `retrieve_by_embedding` | `retrieve_by_embedding(query_vector, domain, k)` | `List[Tuple[MemoryNote, float]]` | Vector search |
| `get_memory_context` | `get_memory_context(query, domain, k, token_budget)` | `str` | Formatted context |

---

## 10. ReasoningLogger API

### Constructor

```python
ReasoningLogger(log_path: str = None, cold_path: str = None)
```

### Logging Methods

| Method | Signature | Purpose |
|--------|-----------|---------|
| `log_evolution` | `log_evolution(note_id, decision, reason, tier, superseded_note_id, extra)` | Log evolution decision |
| `log_link` | `log_link(from_note, to_note, relationship, reason, tier)` | Log link creation |
| `log_tier_assignment` | `log_tier_assignment(note_id, tier, source_type, auto, override)` | Log tier assignment |
| `log_alias_added` | `log_alias_added(entity_type, canonical, alias, trigger_note_ids)` | Log alias auto-add |

### Query Methods

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `get_reasoning` | `get_reasoning(note_id)` | `List[Dict]` | Get reasoning for note |
| `get_recent` | `get_recent(limit)` | `List[Dict]` | Recent entries |
| `get_stats` | `get_stats()` | `Dict` | Log statistics |
| `prune_old_entries` | `prune_old_entries(retention_days)` | `Dict` | Archive old entries |

### Event Types

- `evolution_decision`: Evolution assessment
- `link_created`: Link generation
- `tier_assignment`: Tier assignment
- `alias_added`: Auto-added alias

---

## 11. MemoryStore API

### Constructor

```python
MemoryStore(jsonl_path: str = None, lance_path: str = None)
```

### Methods

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `write_note` | `write_note(note)` | `None` | Append note to store |
| `read_all_notes` | `read_all_notes()` | `List[MemoryNote]` | Read all notes |
| `iterate_notes` | `iterate_notes()` | `Iterator[MemoryNote]` | Stream notes |
| `get_note_by_id` | `get_note_by_id(note_id)` | `Optional[MemoryNote]` | Get note by ID |
| `get_notes_by_domain` | `get_notes_by_domain(domain)` | `List[MemoryNote]` | Get notes by domain |
| `get_recent_notes` | `get_recent_notes(limit)` | `List[MemoryNote]` | Get recent notes |
| `count_notes` | `count_notes()` | `int` | Count total notes |
| `_rewrite_note` | `_rewrite_note(note)` | `None` | Update note in place |
| `export_snapshot` | `export_snapshot(output_path)` | `None` | Export to cold storage |

---

## 12. VectorMemory API (Cross-Session)

### Constructor

```python
VectorMemory(workspace_path: str = None)
```

### Methods

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `init` | `init()` | `None` | Connect/create DB |
| `add` | `add(text, tags, session_key, source, metadata, chunk, overwrite)` | `List[str]` | Add memory entry |
| `search` | `search(query, top_k, source_filter, session_filter, tags_filter)` | `List[Dict]` | Semantic search |
| `search_text` | `search_text(query, top_k)` | `List[Dict]` | Text search |
| `get_recent` | `get_recent(session_key, limit)` | `List[Dict]` | Get recent entries |
| `delete` | `delete(content_hash, entry_id)` | `None` | Delete entry |
| `count` | `count()` | `int` | Entry count |
| `stats` | `stats()` | `Dict` | Store statistics |
| `sync_from_memory_files` | `sync_from_memory_files(dry_run)` | `Dict` | Historical import |
| `save_session_summary` | `save_session_summary(summary, session_key, tags)` | `None` | Save session summary |

---

## 13. CLI Commands

```bash
# MemoryManager CLI
python memory/memory_manager.py stats
python memory/memory_manager.py remember "content here"
python memory/memory_manager.py recall "search query"
python memory/memory_manager.py entity <type> <value>
python memory/memory_manager.py cve <id>
python memory/memory_manager.py actor <name>
python memory/memory_manager.py context <query>
python memory/memory_manager.py maintenance
python memory/memory_manager.py snapshot
python memory/memory_manager.py rebuild-index

# EntityIndexer CLI
python memory/entity_indexer.py build
python memory/entity_indexer.py stats
python memory/entity_indexer.py cves
python memory/entity_indexer.py actors
python memory/entity_indexer.py lookup <type> <value>
python memory/entity_indexer.py extract "text to analyze"
python memory/entity_indexer.py check "content to check"

# AliasResolver CLI
python memory/alias_resolver.py  # Shows stats and tests

---

## 14. Phase 6 API (Ontology & Knowledge Graph)

### KnowledgeGraph

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `add_node` | `add_node(entity_type, entity_id, metadata)` | `Dict` | Add graph node |
| `get_node` | `get_node(node_id)` | `Optional[Dict]` | Get node by ID |
| `add_edge` | `add_edge(from_id, to_id, relationship)` | `Dict` | Add graph edge |
| `get_edges_from` | `get_edges_from(node_id)` | `List[Dict]` | Get outgoing edges |
| `traverse_from` | `traverse_from(node_id, depth)` | `Dict` | Graph traversal |
| `get_node_by_entity` | `get_node_by_entity(entity_type, entity_id)` | `Optional[Dict]` | Get node by entity |
| `get_neighbors` | `get_neighbors(node_id)` | `List[Dict]` | Get adjacent nodes |
| `stats` | `stats()` | `Dict` | Graph statistics |
| `export_graph_visualization` | `export_graph_visualization(format)` | `str` | Export DOT/JSON |

### OntologyValidator

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `validate_entity` | `validate_entity(entity_type, entity)` | `(bool, List[str])` | Validate entity against schema |
| `validate_relationship` | `validate_relationship(relationship)` | `(bool, List[str])` | Validate relationship type |
| `validate_hasl` | `validate_hasl(handling, action, share, license)` | `(bool, List[str])` | Validate HASL fields |

### IEPolicyManager

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `create_policy` | `create_policy(policy_data)` | `Dict` | Create IEP 2.0 policy |
| `update_policy` | `update_policy(policy_id, updates)` | `Dict` | Update policy |
| `check_compliance` | `check_compliance(entity_type, entity_id, policy_id)` | `(bool, List[str])` | Check compliance |
| `get_active_policies` | `get_active_policies(entity_type, entity_id)` | `List[Dict]` | Get active policies |
| `create_tlp_policy` | `create_tlp_policy(country, tlp_level, policy_data)` | `Dict` | Create TLP-based policy |

### GraphRetriever

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `recall` | `recall(query, k, tier_filter)` | `List[MemoryNote]` | Graph-based recall |
| `recall_with_path` | `recall_with_path(query, max_depth)` | `Dict` | Recall with path expansion |
| `expand` | `expand(node_id, depth)` | `Dict` | Expand graph neighborhood |
| `traverse_from` | `traverse_from(entity_type, entity_id, relationship)` | `List[MemoryNote]` | Traverse by relationship |

---

## 15. Phase 7 API (Synthesis Layer)

### SynthesisGenerator

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `synthesize` | `synthesize(query, format, k, include_graph, tier_filter)` | `Dict` | Full answer synthesis |
| `get_llm_client` | `get_llm_client()` | `Optional[Ollama]` | Get LLM client |
| `fallback_synthesis` | `fallback_synthesis(query, format)` | `Dict` | Fallback synthesis |

### SynthesisRetriever

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `retrieve_context` | `retrieve_context(query, k, tier_filter, expand_graph)` | `Dict` | Retrieve comprehensive context |
| `get_context_summary` | `get_context_summary(context, max_length)` | `str` | Summary of retrieved context |

### SynthesisValidator

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `validate_response` | `validate_response(response)` | `(bool, List[str])` | Validate complete response |
| `check_quality_score` | `check_quality_score(response)` | `Dict` | Compute quality score |
| `validate_answer` | `validate_answer(answer, confidence, sources)` | `(bool, List[str])` | Validate direct answer |
| `validate_brief` | `validate_brief(summary, themes, confidence, evidence)` | `(bool, List[str])` | Validate synthesized brief |

---

## 16. CLI Commands

```bash
# MemoryManager CLI
python memory/memory_manager.py stats
python memory/memory_manager.py remember "content here"
python memory/memory_manager.py recall "search query"
python memory/memory_manager.py entity <type> <value>
python memory/memory_manager.py cve <id>
python memory/memory_manager.py actor <name>
python memory/memory_manager.py context <query>
python memory/memory_manager.py maintenance
python memory/memory_manager.py snapshot
python memory/memory_manager.py rebuild-index

# EntityIndexer CLI
python memory/entity_indexer.py build
python memory/entity_indexer.py stats
python memory/entity_indexer.py cves
python memory/entity_indexer.py actors
python memory/entity_indexer.py lookup <type> <value>
python memory/entity_indexer.py extract "text to analyze"
python memory/entity_indexer.py check "content to check"

# AliasResolver CLI
python memory/alias_resolver.py  # Shows stats and tests

# Phase 6 Graph CLI
python memory/knowledge_graph.py stats
python memory/knowledge_graph.py export <format>
python memory/knowledge_graph.py add-node <type> <id>
python memory/knowledge_graph.py add-edge <from> <to> <relationship>

# Phase 7 Synthesis CLI
python memory/synthesis_generator.py "query" --format <format>
python memory/synthesis_retriever.py "query"
python memory/synthesis_validator.py <response_file>
```

---

*End of API Reference*
