# Roland Fleet Agentic Memory Architecture
## DGX Spark GB10 Implementation

Version: 1.1
Date: 2026-03-20
Author: Patrick Roland / Claude (Collaborative)
Platform: ASUS Ascent DGX Spark GB10 (Homelab)

---

## Version History

- **1.0** (2026-03-20): Initial architecture design
- **1.1** (2026-03-20): Removed LUKS encryption (homelab environment)
- **1.2** (2026-03-31): Added alias resolution layer (Phase 2.5) — alias_maps/, alias_resolver.py, canonical entity indexing

---

## 1. Hardware Topology and Storage Strategy

### Compute Profile

The DGX Spark GB10 provides a Grace CPU (ARM Neoverse V2) paired with a Blackwell GPU sharing 128GB unified memory. This architecture eliminates the CPU-GPU memory transfer bottleneck that plagues discrete GPU setups.

### Storage Tiers

```
┌─────────────────────────────────────────────────────────┐
│ DGX Spark GB10                                         │
│                                                         │
│ ┌─────────────────────────┐ ┌──────────────────────┐  │
│ │ 1TB NVMe SSD            │ │ 8TB HDD (USB 3.2)    │  │
│ │ "HOT TIER"              │ │ "COLD TIER"          │  │
│ │                         │ │                      │  │
│ │ /home/rolandpg/.openclaw│ │ /media/rolandpg/     │  │
│ │ /workspace/             │ │ USB-HDD/             │  │
│ │ ├── memory/            │ │ ├── archive/         │  │
│ │ │   ├── notes.jsonl    │ │ ├── notes/           │  │
│ │ │   ├── *.py           │ │ ├── snapshots/       │  │
│ │ ├── vectordb/          │ │ ├── raw_logs/        │  │
│ │ ├── embeddings/        │ │ ├── ingest/          │  │
│ │ ├── index/            │ │ ├── documents/       │  │
│ │ ├── models/           │ │ ├── queue/           │  │
│ │ └── tmp/              │ │ ├── backups/         │  │
│ └── cti-workspace/      │ │ ├── daily/           │  │
│                         │ │ ├── weekly/          │  │
│                         │ │ └── oc-cron/         │  │
│                         │ │                      │  │
│                         │ │ /mnt/cold (symlink)  │  │
│                         │ │                      │  │
│                         │ └──────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Storage Allocation Rules

**SSD (Hot Tier)** -- everything that touches inference or retrieval:
- Vector DB (LanceDB) -- Random IOPS critical
- Active notes (JSONL) -- Read on every memory operation
- Embedding model cache -- Loaded into memory
- Agent workspace, configs, SOUL.md
- Temporary processing directories

**HDD (Cold Tier)** -- bulk storage, sequential access:
- Raw conversation logs -- Append-only
- Memory snapshots -- Daily/weekly exports
- Archived note versions -- Evolved-out memories
- Document ingestion queue -- Pre-processing staging
- Backups -- Full system state

**CRITICAL:** Vector DB stays on SSD. USB 3.2 Gen 2 at 20 Gbps handles sequential throughput fine, but spinning disk random IOPS (80-160 IOPS) destroys vector search latency. SSD delivers 100K+ random IOPS.

### Security Model

This is a **homelab environment** behind a firewall. No LUKS encryption required. Data classification follows standard OPSEC:
- Memory store treated as sensitive (contains client context, CTI)
- No cloud sync or remote backup
- Subagent workspace isolation enforced

---

## 2. Memory Note Schema

### Note Structure

```json
{
  "id": "note_20260320_143022_a7f3",
  "version": 3,
  "created_at": "2026-03-20T14:30:22-05:00",
  "updated_at": "2026-03-20T16:45:11-05:00",
  "evolved_from": null,
  "evolved_by": ["note_20260320_162201_b8e1"],

  "content": {
    "raw": "Original interaction content or observation",
    "source_type": "conversation|task_output|ingestion|observation",
    "source_ref": "subagent:task_id or conversation:session_id"
  },

  "semantic": {
    "context": "LLM-generated one-sentence contextual summary",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "tags": ["category1", "domain1", "type1"],
    "entities": ["entity1", "entity2"]
  },

  "embedding": {
    "model": "nomic-embed-text-v2-moe",
    "vector": [0.012, -0.034, ...],
    "dimensions": 768,
    "input_hash": "sha256_of_concatenated_text_fields"
  },

  "links": {
    "related": ["note_id_1", "note_id_2"],
    "supersedes": null,
    "superseded_by": null,
    "causal_chain": []
  },

  "metadata": {
    "access_count": 12,
    "last_accessed": "2026-03-20T16:00:00-05:00",
    "evolution_count": 2,
    "confidence": 0.87,
    "ttl": null,
    "domain": "security_ops|project|personal|research"
  }
}
```

### Schema Design Decisions

- **Version tracking**: Every evolution increments version. Previous version archived to cold storage. Enables rollback.
- **Input hash on embeddings**: Before re-embedding, check if text fields changed. Skip embedding call if hash matches. Saves GPU cycles.
- **Confidence score**: Starts at 1.0 for direct observations, decays for inferred/evolved content. Below 0.5 = flagged for human review.
- **Domain tagging**: Separates security_ops from personal from research. Subagent context scoped by domain.

---

## 3. Software Stack

### Core Components

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Vector DB | LanceDB | File-based (no server), ARM-native, embedded in-process |
| Embedding | nomic-embed-text-v2-moe | 768-dim, 8192 token context, strong benchmarks |
| LLM (Memory Ops) | nemotron-3-nano | Fast MoE for note construction, linking, evolution |
| LLM (Agent Tasks) | nemotron-3-super | Larger model for complex reasoning |
| Note Storage | JSONL + LanceDB | Human-readable + vector index, dual-write |
| Scheduling | systemd timers | Daily 6AM, Weekly Monday 6AM |

### Directory Structure

```
memory/
├── __init__.py                 # Module exports
├── note_schema.py              # Pydantic models
├── note_constructor.py        # A-MEM note construction
├── link_generator.py          # Concept linking
├── memory_evolver.py          # Evolution with versioning
├── vector_retriever.py        # Embedding similarity search
├── memory_store.py            # JSONL persistence
├── memory_manager.py          # Primary agent interface
├── embedding_utils.py         # Ollama embedding generation
├── daily_maintenance.py       # Snapshot, decay, stats
├── weekly_maintenance.py      # Backup, reindex, purge
├── openclaw-memory-daily.service
├── openclaw-memory-daily.timer
├── openclaw-memory-weekly.service
└── openclaw-memory-weekly.timer
```

---

## 4. Memory Lifecycle

### 4.1 Note Construction

Input → Content Extraction → Semantic Enrichment (LLM) → Embedding → Dual Write (JSONL + LanceDB)

### 4.2 Link Generation

New Note → Vector Retrieval (top-k candidates) → LLM Link Analysis → Bidirectional Linking

Relationship types: SUPPORTS, CONTRADICTS, EXTENDS, CAUSES, RELATED

### 4.3 Memory Evolution

New Note + Linked Notes → Evolution Assessment (LLM) → Versioned Update → Confidence Decay

- Max 5 evolution hops per note
- Previous version archived to cold storage
- Confidence decays with each evolution

### 4.4 Retrieval

Query → Embed Query → Vector Search → Link Expansion → Context Assembly → Agent Prompt

---

## 5. Agent-Subagent Memory Flow

### Primary Agent (Patton)

- Owns memory store exclusively (write access)
- READ all memories
- WRITE via construction/linking/evolution
- SPAWN subagents with scoped read-only context
- INGEST subagent outputs

### Subagent (Ephemeral)

- Receives: task + memory context (read-only) + domain filter
- Returns: output + observations + status
- No direct memory access
- Workspace in `/tmp/subagent_<task_id>/` wiped on termination

### Memory Flow

```
User Input → Primary Agent
              ↓
        Retrieve memory
              ↓
    ┌─────────┴─────────┐
    ↓                   ↓
Handle Directly    Spawn Subagent
    ↓                   ↓
Construct Note    Execute Task
    ↓                   ↓
Link Generation   Return Output
    ↓                   ↓
Evolution Cycle  Primary Agent Ingests
    ↓                   ↓
    └─────────┬─────────┘
              ↓
        Respond to User
```

---

## 6. Maintenance Operations

### Daily (systemd timer: 6:00 AM)

| Operation | Description |
|-----------|-------------|
| Snapshot | Export memory state to cold storage |
| Stats | Log note count, confidence, link density |
| Decay | Reduce confidence by 0.01 for stale notes |
| Prune | Flag low-confidence orphaned notes |

### Weekly (systemd timer: Monday 6:00 AM)

| Operation | Description |
|-----------|-------------|
| Full Backup | Compress archive to cold storage |
| Reindex | Rebuild LanceDB from JSONL source |
| Orphan Check | Repair broken links |
| Retention | Purge archives older than 90 days |

### Monthly (Human-Triggered)

| Operation | Description |
|-----------|-------------|
| Review Queue | Surface notes flagged for review |
| Cold Purge | Delete old archived notes |
| Performance Audit | Measure latency, evolution accuracy |

---

## 7. Implementation Status

| Phase | Status | Date |
|-------|--------|------|
| 1: Foundation | ✅ COMPLETE | 2026-03-20 |
| 2: Core Memory Ops | ✅ COMPLETE | 2026-03-20 |
| 3: Evolution | ✅ COMPLETE | 2026-03-20 |
| 4: Agent Integration | ✅ COMPLETE | 2026-03-20 |
| 5: Maintenance | ✅ COMPLETE | 2026-03-20 |
| 6: Hardening | ✅ COMPLETE | 2026-03-20 |

### Phase 6 Completion Notes

- Subagent workspace cleanup: Implemented in maintenance scripts
- Telemetry: Stats tracked in MemoryManager
- Load testing: VectorDB benchmarks available
- Documentation: This document

**Removed from Phase 6:**
- ~~LUKS Encryption~~ — Not required for homelab environment

---

## 8. Future Considerations

### Hardware Upgrade (DGX Spark)

When migrating to production DGX Spark hardware:
- Re-evaluate LUKS encryption based on deployment context
- 70B+ models locally for improved memory operations
- Consider managed vector DB (Qdrant) for multi-node scaling

### Fleet Expansion

If persistent subagents are needed later:
- Primary agent remains memory authority
- Subagents get domain-scoped read access
- LanceDB supports concurrent readers

### Alternative Memory Systems

Pathways to other technologies if needs evolve:
- **Cognee**: Knowledge graph integration if relational queries needed
- **Mem0**: Production-grade memory if compliance requirements emerge

---

## 9. Quick Reference

### Python API

```python
from memory import get_memory_manager
mm = get_memory_manager()

# Create memory
note = mm.remember("Content", domain="security_ops")

# Retrieve
results = mm.recall("query", domain="security_ops", k=10)

# Get agent context
context = mm.get_context("query", token_budget=4000)

# Subagent context
sub_context = mm.get_subagent_context("task description", domain="security_ops")

# Ingest subagent results
mm.ingest_subagent_output(task_id, output, observations, domain)

# Maintenance
mm.daily_maintenance()
mm.weekly_maintenance()
mm.snapshot()

# Stats
print(mm.get_stats())
```

### Storage Locations

| Component | Path |
|-----------|------|
| Active notes | `/home/rolandpg/.openclaw/workspace/memory/notes.jsonl` |
| Entity index | `/home/rolandpg/.openclaw/workspace/memory/entity_index.json` |
| Alias maps | `/home/rolandpg/.openclaw/workspace/memory/alias_maps/` |
| Alias resolver | `/home/rolandpg/.openclaw/workspace/memory/alias_resolver.py` |
| Vector DB | `/home/rolandpg/.openclaw/workspace/vectordb/` |
| Cold archive | `/media/rolandpg/USB-HDD/archive/` |
| Daily logs | `/media/rolandpg/USB-HDD/daily/` |
| Weekly backups | `/media/rolandpg/USB-HDD/backups/weekly/` |
| Maintenance logs | `/media/rolandpg/USB-HDD/weekly/` |

### systemd Timers

```bash
# Enable timers
sudo cp openclaw-memory-daily.service /etc/systemd/system/
sudo cp openclaw-memory-daily.timer /etc/systemd/system/
sudo cp openclaw-memory-weekly.service /etc/systemd/system/
sudo cp openclaw-memory-weekly.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now openclaw-memory-daily.timer
sudo systemctl enable --now openclaw-memory-weekly.timer

# Check status
systemctl list-timers | grep openclaw-memory
```
