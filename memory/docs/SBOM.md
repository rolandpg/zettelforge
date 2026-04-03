# A-MEM Software Bill of Materials

**Version:** 1.3  
**Date:** 2026-04-02  
**Project:** A-MEM (Agentic Memory)

---

## 1. Software Components

### Core Python Modules

| Module | Version | License | Purpose |
|--------|---------|---------|---------|
| pydantic | 2.9.2 | MIT | Data validation and schema definition |
| requests | 2.31.0 | Apache 2.0 | HTTP client for LLM communication |
| pyarrow | 16.1.0 | Apache 2.0 | Arrow schema for LanceDB |
| lancedb | 0.6.4 | Apache 2.0 | Vector database |
| ollama | 0.2.0 | MIT | Local LLM client |

### System Dependencies

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| Python | 3.12.3 | PSF | Runtime environment |
| SQLite3 | 3.45.1 | Public Domain | Python stdlib (lancedb dependency) |

---

## 2. Project-Specific Modules

| File | Purpose | Dependencies |
|------|---------|--------------|
| `memory/note_schema.py` | MemoryNote Pydantic schema | pydantic |
| `memory/memory_store.py` | JSONL storage + LanceDB indexing | lancedb, pyarrow |
| `memory/entity_indexer.py` | Entity extraction and indexing | alias_resolver |
| `memory/link_generator.py` | LLM-based link generation | ollama |
| `memory/memory_evolver.py` | Evolution cycle management | ollama |
| `memory/alias_resolver.py` | Entity alias resolution | None |
| `memory/alias_manager.py` | Auto-update alias tracking | alias_resolver |
| `memory/reasoning_logger.py` | Decision audit logging | None |
| `memory/note_constructor.py` | LLM note enrichment | ollama |
| `memory/vector_retriever.py` | Semantic search | lancedb |
| `memory/vector_memory.py` | Cross-session embeddings | ollama |
| `embedding_utils.py` | Embedding generation | ollama |
| `memory/ontology_schema.json` | Formal ontology definition | None |
| `memory/knowledge_graph.py` | Graph storage and traversal | None |
| `memory/ontology_validator.py` | Schema validation | None |
| `memory/graph_retriever.py` | Graph-based retrieval | None |
| `memory/iep_policy.py` | IEP 2.0 policy management | None |
| `memory/synthesis_generator.py` | LLM-based answer synthesis | ollama |
| `memory/synthesis_retriever.py` | Hybrid retrieval | lancedb, ollama |
| `memory/synthesis_validator.py` | Response validation | None |

---

## 3. External Service Dependencies

| Service | Integration | Authentication | Status |
|---------|-------------|----------------|--------|
| Ollama (localhost:11434) | LLM enrichment, embeddings | None | Required |
| Local LLM Server (localhost:8080) | Embedding generation | None | Required |

---

## 4. Dependency Tree

```
A-MEM (memory/)
├── pydantic (data validation)
│   └── typing_extensions (Python < 3.12)
├── lancedb (vector database)
│   ├── pyarrow (Arrow schema)
│   └── requests (HTTP client)
├── ollama (local LLM)
│   └── requests (HTTP client)
└── pyarrow (Arrow types)
```

---

## 5. Transitive Dependencies

| Package | Via | License |
|---------|-----|---------|
| numpy | lancedb | BSD |
| pandas | lancedb | BSD |
| fsspec | lancedb | BSD |
| packaging | lancedb | Apache 2.0 |

---

## 6. License Compliance

| Component | License | Compliance Status |
|-----------|---------|-------------------|
| pydantic | MIT | Compliant |
| requests | Apache 2.0 | Compliant |
| pyarrow | Apache 2.0 | Compliant |
| lancedb | Apache 2.0 | Compliant |
| ollama | MIT | Compliant |
| Python 3.12 | PSF | Compliant |

**Note:** All dependencies are open source with permissive licenses. No copyleft (GPL) dependencies present.

---

## 7. Vulnerability Scanning

| Tool | Last Scan | Status |
|------|-----------|--------|
| pip-audit | N/A | Not automated |
| Snyk | N/A | Not integrated |
| Dependabot | N/A | Not configured |

**Recommendation:** Add CI vulnerability scanning for production deployment.

---

## 8. Version Pinning

| Package | Current | Pin Required | Notes |
|---------|---------|--------------|-------|
| pydantic | 2.9.2 | Recommended | Pydantic v2 required |
| ollama | latest | Not pinned | Local installation |
| lancedb | latest | Not pinned | Active development |
| pyarrow | latest | Not pinned | Auto-sync with lancedb |

---

## 9. Build-Time Dependencies

| Tool | Purpose |
|------|---------|
| Python 3.12 | Runtime |
| pip | Package installation |
| No compile step | Pure Python project |

---

## 10. Runtime Environment Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.12 | 3.12.3 |
| RAM | 4 GB | 8 GB |
| GPU | None | CUDA-capable (optional) |
| Disk | 1 GB | 10 GB (with archive) |

---

*End of SBOM*
