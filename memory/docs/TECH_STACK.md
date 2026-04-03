# A-MEM Technology Stack Document

**Version:** 1.3  
**Date:** 2026-04-02  
**Project:** A-MEM (Agentic Memory)

---

## Programming Languages

| Language | Version | Usage |
|----------|---------|-------|
| Python | 3.12 | Primary language - all core logic |
| JavaScript | N/A | Not used |
| Go | N/A | Not used |

---

## Frameworks and Libraries

| Package | Version | Purpose | Runtime/Dev |
|---------|---------|---------|-------------|
| pydantic | latest | Data validation and schema definition | Runtime |
| pydantic[email] | latest | Email validation (if needed) | Runtime |
| ollama | latest | Local LLM for semantic enrichment and embeddings | Runtime |
| lancedb | latest | Vector database for semantic search | Runtime |
| pyarrow | latest | Arrow schema for LanceDB | Runtime |
| requests | latest | HTTP client (Ollama fallback) | Runtime |

**Dependency Analysis:**
- **pydantic**: Used for MemoryNote schema validation
- **ollama**: Local LLM for embedding generation and text generation
- **lancedb**: Local vector database for cross-session semantic search
- **requests**: HTTP client for Ollama embeddings (fallback)

---

## Database and Storage Technologies

| Technology | Version | Purpose | Configuration |
|------------|---------|---------|---------------|
| JSONL | N/A | Primary note storage | `notes.jsonl` |
| LanceDB | latest | Vector index | `vector_memory.lance/memories.lance` |
| JSON | N/A | Index storage | `entity_index.json` |
| File System | N/A | Archive storage | `/media/rolandpg/USB-HDD/archive/` |

**Storage Layout:**
```
/home/rolandpg/.openclaw/workspace/
├── notes.jsonl              # Main storage (JSONL, append-only)
├── entity_index.json        # Entity → note ID index (JSON)
├── reasoning_log.jsonl      # Audit trail (JSONL)
├── dedup_log.jsonl          # Deduplication events (JSONL)
├── alias_observations.json  # Auto-update tracking (JSON)
├── plan_iterations.jsonl    # PRD iteration history (JSONL)
└── vector_memory.lance/     # LanceDB vector store
    └── memories.lance/      # Vector index
        ├── _versions/       # Version metadata
        └── _transactions/   # Transaction log
```

---

## Infrastructure and Hosting

| Platform | Details |
|----------|---------|
| **Environment** | Local homelab (single machine) |
| **OS** | Linux (NVIDIA driver) |
| **Memory** | RAM-based processing with disk persistence |
| **CPU/GPU** | Local computation (no cloud) |

**Cold Storage Path:**
- `/media/rolandpg/USB-HDD/` - External HDD for archive
- `/media/rolandpg/USB-HDD/archive/` - Superseded note versions

---

## Authentication and Authorization

| Technology | Implementation |
|------------|----------------|
| **Local Authentication** | None (single-machine homelab) |
| **API Keys** | None configured |
| **OAuth** | None |
| **Session Management** | None (stateless per request) |

**Security Model:**
- Single-user homelab environment
- No authentication required
- No authorization checks on API endpoints
- File system permissions provide basic security

---

## Build Tools, Test Frameworks, and CI/CD

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12 | Runtime |
| pytest | Not used | Test framework (custom suite used) |
| systemadm | Systemd | Service scheduling |
| bash | latest | Cron job wrapper scripts |

**Test Suite:**
- `test_memory_system.py` - 33 tests across 8 phases
- `test_phase_3_5.py` - 7 alias resolution tests
- `test_phase_4_5.py` - 10 epistemic tiering tests
- `test_phase_5_5.py` - 9 reasoning memory tests

**Scheduling:**
- Daily maintenance: `openclaw-memory-daily.service` (06:00 CDT)
- Weekly maintenance: `openclaw-memory-weekly.service` (Friday 23:00 CDT)

---

## Third-Party Service Integrations

| Service | Integration | Authentication | Status |
|---------|-------------|----------------|--------|
| Ollama (local) | LLM enrichment, embedding generation | None (localhost) | Active |
| Local LLM Server | Embedding generation (GPU-accelerated) | None (localhost) | Active |
| LanceDB | Vector storage and search | None (filesystem) | Active |

**Local Services Used:**
- `http://localhost:8080/embedding` - LLM server for embeddings
- Ollama (default) - Fallback LLM for text generation

---

## Technology Rationale

### Why JSONL over Database?

**Rationale:** Simple append-only format, easy to audit, version, and debug. No database server required for homelab deployment.

**Trade-offs:**
- Pros: Simple, human-readable, append-only (safe), easy to version
- Cons: No ACID guarantees, slower for complex queries (mitigated by entity index)

### Why Ollama over Cloud LLM?

**Rationale:** Local LLM enables zero external API dependency, full data control, and no API costs.

**Trade-offs:**
- Pros: Zero API costs, full data control, no network dependencies
- Cons: Requires local GPU/ML hardware, limited to local model capabilities

### Why LanceDB over Pinecone/Weaviate?

**Rationale:** Local vector database for homelab use case, no external dependencies.

**Trade-offs:**
- Pros: Local, no API costs, simple deployment
- Cons: Single-machine scale, no distributed capabilities

### Why Zettelkasten Architecture?

**Rationale:** Atomic notes with links enable self-organizing knowledge base that compounds over time without manual organization.

**Trade-offs:**
- Pros: Zero manual organization, links auto-generate, evolution supported
- Cons: More complex than flat file storage

---

## Compatibility Notes

### Between Stack Components

| Component Pair | Compatibility | Notes |
|----------------|---------------|-------|
| pydantic ↔ Python 3.12 | Compatible | Pydantic v2 works with Python 3.12 |
| ollama ↔ local LLM | Compatible | Uses standard Ollama API |
| lancedb ↔ pyarrow | Compatible | Arrow schema for LanceDB |
| requests ↔ ollama | Compatible | HTTP fallback for embeddings |

### Known Incompatibilities

- None identified

---

## Version Pinning

| Package | Version Pin | Source |
|---------|-------------|--------|
| Python | 3.12 | System Python |
| ollama | latest | Local installation |
| lancedb | latest | pip |
| pydantic | latest | pip |

---

*End of Technology Stack Document*
