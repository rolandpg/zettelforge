# ZettelForge: Agentic Memory System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)](https://github.com/rolandpg/zettelforge)

A production-grade memory system for AI agents, purpose-built for cyber threat intelligence (CTI). Combines a **TypeDB STIX 2.1 ontology layer** with **LanceDB vector search**, knowledge graph traversal, and intent-based query routing to give agents persistent, structured memory across sessions.

## Features

- **Hybrid Architecture**: TypeDB for STIX 2.1 ontology (entities, relations, inference) + LanceDB for vector embeddings and Zettelkasten notes
- **STIX 2.1 Schema**: 9 typed entity types (threat-actor, malware, vulnerability, etc.), 8 relationship types (uses, targets, attributed-to, etc.), with confidence and temporal validity on every relation
- **Inference-Ready**: TypeDB functions for transitive alias resolution, tool attribution via campaigns, and entity-to-note bridging
- **Blended Retrieval**: Combines vector similarity + knowledge graph traversal, weighted by query intent
- **Two-Phase Extraction Pipeline**: Mem0-style selective ingestion -- LLM extracts salient facts with importance scores, then decides ADD/UPDATE/DELETE/NOOP per fact
- **36 CTI Aliases Seeded**: APT28/Fancy Bear/Strontium/Forest Blizzard, APT29/Cozy Bear/Midnight Blizzard, Lazarus/Hidden Cobra, and more -- resolved via TypeDB at query time
- **Entity Extraction**: Automatic indexing of CVEs, threat actors, tools, campaigns with alias resolution
- **RAG Synthesis**: Answer generation in multiple formats (direct answer, brief, timeline, relationship map)
- **Report Ingestion**: `remember_report()` for chunked news/threat report processing with published date metadata
- **Graceful Fallback**: If TypeDB is unavailable, automatically falls back to JSONL knowledge graph
- **Local-First**: Runs entirely on local hardware -- Ollama for LLM, LanceDB for vectors, TypeDB in Docker

## Quick Start

```bash
# Clone and install
git clone https://github.com/rolandpg/zettelforge.git
cd zettelforge
pip install -e ".[dev]"

# Start TypeDB (ontology layer)
docker compose -f docker/docker-compose.yml up -d

# Start Ollama (embeddings + LLM)
ollama pull nomic-embed-text
ollama pull qwen2.5:3b
ollama serve
```

```python
from zettelforge import MemoryManager

mm = MemoryManager()

# Store a memory -- entities go to TypeDB, text+vectors to LanceDB
note, status = mm.remember(
    "APT28 uses Cobalt Strike for lateral movement via CVE-2024-1111",
    domain="cti"
)

# Two-phase extraction (selective, deduplicating)
results = mm.remember_with_extraction(
    "APT28 has shifted tactics. They dropped DROPBEAR and now exploit edge devices.",
    domain="cti"
)

# Ingest a threat report (auto-chunks, extracts per chunk)
results = mm.remember_report(
    content=open("report.txt").read(),
    source_url="https://example.com/apt28-report",
    published_date="2026-04-09",
    domain="cti"
)

# Retrieve -- blends vector similarity + STIX graph traversal
results = mm.recall("What tools does APT28 use?", k=10)

# Alias resolution works automatically via TypeDB
results = mm.recall_actor("Fancy Bear")  # resolves to APT28

# Synthesize answers
result = mm.synthesize("Summarize APT28 activity", format="synthesized_brief")

# Traverse the STIX knowledge graph
paths = mm.traverse_graph("actor", "apt28", max_depth=2)
# APT28 -[USES_TOOL]-> cobalt-strike -[EXPLOITS_CVE]-> CVE-2024-1111
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                           MemoryManager                              │
│  remember()  remember_with_extraction()  remember_report()           │
│  recall()    synthesize()    traverse_graph()                        │
├──────────┬───────────┬──────────────┬───────────┬────────────────────┤
│  Note    │  Fact     │   Memory     │  Blended  │   Synthesis        │
│Constructor│ Extractor │  Updater     │ Retriever │   Generator        │
│(enrich)  │(Phase 1)  │(Phase 2)     │(vec+graph)│   (RAG)            │
├──────────┴───────────┴──────────────┼───────────┴────────────────────┤
│       Entity Indexer + Alias        │  Intent Classifier             │
│       Resolver (TypeDB-first)       │  (factual/temporal/causal)     │
├─────────────────────────────────────┼────────────────────────────────┤
│                                     │                                │
│   ┌─────────────────────────┐       │  ┌──────────────────────────┐  │
│   │  TypeDB (Ontology)      │       │  │  LanceDB (Conversational)│  │
│   │  STIX 2.1 Schema        │       │  │  Vector Embeddings       │  │
│   │  9 Entity Types         │◄──────┤  │  Zettelkasten Notes      │  │
│   │  8 Relation Types       │bridge │  │  768-dim nomic-embed     │  │
│   │  Alias Inference        │───────►  │  Unstructured Reports    │  │
│   │  Temporal Edges         │       │  │  IVF_PQ Index            │  │
│   │  Confidence Scoring     │       │  │                          │  │
│   └─────────────────────────┘       │  └──────────────────────────┘  │
│         mentioned-in bridge ────────┘                                │
└──────────────────────────────────────────────────────────────────────┘
```

The **bridge** between the two databases is the `mentioned-in` relation in TypeDB, which stores `(entity) --mentioned-in--> (note-id)`. The note itself (raw text + vector embedding) lives in LanceDB. This clean separation means:
- **TypeDB** answers: "what entities exist and how are they related?"
- **LanceDB** answers: "what context exists about this topic?"
- **BlendedRetriever** merges both answers using intent-based policy weights

## Deployment

### Option 1: On-Premises (Homelab / Air-Gapped)

Best for: security-sensitive environments, development, single-analyst workstations.

**Prerequisites:**
- Linux (Ubuntu 22.04+ / RHEL 9+) or macOS 13+
- Docker 24+ and Docker Compose v2
- Python 3.10+
- 8 GB RAM minimum (4 GB TypeDB + 2 GB Ollama + 2 GB ZettelForge)
- 20 GB disk (TypeDB data + LanceDB vectors + Ollama models)

**Step 1: Clone and install**

```bash
git clone https://github.com/rolandpg/zettelforge.git
cd zettelforge
pip install -e .
```

**Step 2: Start TypeDB**

```bash
# Start TypeDB container
docker compose -f docker/docker-compose.yml up -d

# Verify it's running
docker compose -f docker/docker-compose.yml ps
# Should show: typedb  Up (healthy)  0.0.0.0:1729->1729/tcp

# Seed CTI aliases (one-time)
python3 -c "from zettelforge.schema.seed_aliases import seed_aliases; seed_aliases()"
```

**Step 3: Start Ollama**

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull nomic-embed-text    # Embeddings (768-dim)
ollama pull qwen2.5:3b          # LLM for extraction, classification, synthesis

# Start server (runs on port 11434)
ollama serve
```

**Step 4: Configure environment**

```bash
# Create .env or export these variables
export AMEM_DATA_DIR=~/.amem                    # LanceDB data + JSONL notes
export AMEM_EMBEDDING_URL=http://127.0.0.1:8081 # Embedding server (llama.cpp)
export TYPEDB_HOST=localhost                      # TypeDB gRPC host
export TYPEDB_PORT=1729                           # TypeDB gRPC port
export TYPEDB_DATABASE=zettelforge                # TypeDB database name
export ZETTELFORGE_BACKEND=typedb                 # "typedb" or "jsonl" (fallback)
```

**Step 5: Verify**

```bash
# Run tests
pytest tests/ -v

# Quick smoke test
python3 -c "
from zettelforge import MemoryManager
mm = MemoryManager()
note, status = mm.remember('APT28 uses Cobalt Strike', domain='cti')
print(f'Status: {status}, Note: {note.id}')
results = mm.recall('APT28 tools', k=3)
print(f'Recall: {len(results)} results')
"
```

**Air-gapped deployment notes:**
- Pre-pull Docker images: `docker save typedb/typedb:latest | gzip > typedb.tar.gz`
- Pre-download Ollama models: copy `~/.ollama/models/` from a connected machine
- All data stays local -- no external API calls required

---

### Option 2: Azure Cloud (SaaS / Team Deployment)

Best for: multi-analyst teams, integration with Azure Sentinel/Defender, scalable workloads.

**Architecture on Azure:**

```
┌─────────────────────────────────────────────────────┐
│                   Azure Resource Group                │
│                                                       │
│  ┌─────────────────┐    ┌──────────────────────────┐ │
│  │ Azure Container  │    │ Azure Container Instance │ │
│  │ Instance: TypeDB │    │ or App Service:          │ │
│  │ (1729, 8000)     │    │ ZettelForge API          │ │
│  │ 4 GB RAM         │    │ + Ollama sidecar         │ │
│  └────────┬─────────┘    └────────────┬─────────────┘ │
│           │ gRPC                      │               │
│           └───────────┬───────────────┘               │
│                       │                               │
│  ┌────────────────────▼──────────────────────────┐   │
│  │         Azure Blob Storage                     │   │
│  │  - LanceDB vector data                         │   │
│  │  - JSONL notes (fallback)                      │   │
│  │  - Ollama model cache                          │   │
│  └────────────────────────────────────────────────┘   │
│                                                       │
│  ┌────────────────────────────────────────────────┐   │
│  │  Azure Key Vault                               │   │
│  │  - TypeDB credentials                          │   │
│  │  - API keys                                    │   │
│  └────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Step 1: Create Resource Group**

```bash
az group create --name rg-zettelforge --location eastus2
```

**Step 2: Deploy TypeDB as Azure Container Instance**

```bash
az container create \
  --resource-group rg-zettelforge \
  --name typedb-server \
  --image typedb/typedb:latest \
  --cpu 2 --memory 4 \
  --ports 1729 8000 \
  --azure-file-volume-share-name typedb-data \
  --azure-file-volume-account-name <storage-account> \
  --azure-file-volume-mount-path /opt/typedb/server/data \
  --restart-policy Always \
  --dns-name-label zettelforge-typedb
```

**Step 3: Deploy ZettelForge as Azure App Service**

```bash
# Create App Service Plan (B2 minimum for Ollama models)
az appservice plan create \
  --name plan-zettelforge \
  --resource-group rg-zettelforge \
  --sku B2 --is-linux

# Deploy from container (build your own image or use the repo)
az webapp create \
  --resource-group rg-zettelforge \
  --plan plan-zettelforge \
  --name zettelforge-api \
  --runtime "PYTHON:3.12"

# Configure environment
az webapp config appsettings set \
  --resource-group rg-zettelforge \
  --name zettelforge-api \
  --settings \
    TYPEDB_HOST=zettelforge-typedb.eastus2.azurecontainer.io \
    TYPEDB_PORT=1729 \
    TYPEDB_DATABASE=zettelforge \
    ZETTELFORGE_BACKEND=typedb \
    AMEM_DATA_DIR=/home/site/data \
    AMEM_EMBEDDING_URL=http://localhost:11434
```

**Step 4: Store secrets in Key Vault**

```bash
az keyvault create \
  --name kv-zettelforge \
  --resource-group rg-zettelforge

az keyvault secret set \
  --vault-name kv-zettelforge \
  --name typedb-password \
  --value "<your-typedb-password>"
```

**Step 5: Persistent storage for LanceDB**

```bash
# Create storage account for LanceDB vectors and notes
az storage account create \
  --name stzettelforge \
  --resource-group rg-zettelforge \
  --sku Standard_LRS

az storage share create \
  --name zettelforge-data \
  --account-name stzettelforge

# Mount as persistent volume in App Service
az webapp config storage-account add \
  --resource-group rg-zettelforge \
  --name zettelforge-api \
  --custom-id data-mount \
  --storage-type AzureFiles \
  --share-name zettelforge-data \
  --account-name stzettelforge \
  --mount-path /home/site/data
```

**Alternative: GPU-enabled for larger models**

For production workloads requiring larger LLMs (70B+ parameters), use Azure Container Instances with GPU or Azure Kubernetes Service:

```bash
# ACI with GPU (for Ollama with large models)
az container create \
  --resource-group rg-zettelforge \
  --name zettelforge-gpu \
  --image your-registry.azurecr.io/zettelforge:latest \
  --cpu 4 --memory 16 \
  --gpu-count 1 --gpu-sku V100 \
  --ports 8080 \
  --environment-variables \
    TYPEDB_HOST=zettelforge-typedb.eastus2.azurecontainer.io \
    ZETTELFORGE_BACKEND=typedb
```

**Azure cost estimate (B2 tier):**

| Resource | SKU | Monthly |
|----------|-----|---------|
| TypeDB ACI | 2 vCPU, 4 GB | ~$70 |
| App Service | B2 (2 vCPU, 3.5 GB) | ~$55 |
| Storage (Files) | Standard LRS, 50 GB | ~$3 |
| Key Vault | Standard | ~$1 |
| **Total** | | **~$130/mo** |

---

### Option 3: Docker Compose (All-in-One)

Best for: quick evaluation, demos, CI/CD testing.

Create `docker-compose.full.yml`:

```yaml
services:
  typedb:
    image: typedb/typedb:latest
    ports:
      - "1729:1729"
    volumes:
      - typedb-data:/opt/typedb/server/data
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    restart: unless-stopped

  zettelforge:
    build: .
    depends_on:
      - typedb
      - ollama
    environment:
      TYPEDB_HOST: typedb
      TYPEDB_PORT: 1729
      TYPEDB_DATABASE: zettelforge
      ZETTELFORGE_BACKEND: typedb
      AMEM_EMBEDDING_URL: http://ollama:11434
      AMEM_DATA_DIR: /data
    volumes:
      - zettelforge-data:/data
    ports:
      - "8080:8080"

volumes:
  typedb-data:
  ollama-data:
  zettelforge-data:
```

```bash
docker compose -f docker-compose.full.yml up -d
# Then pull models: docker exec -it <ollama-container> ollama pull nomic-embed-text
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AMEM_DATA_DIR` | `~/.amem` | LanceDB vectors + JSONL notes |
| `AMEM_EMBEDDING_URL` | `http://127.0.0.1:8081` | Embedding server endpoint |
| `AMEM_EMBEDDING_MODEL` | `nomic-embed-text-v2-moe.gguf` | Embedding model |
| `TYPEDB_HOST` | `localhost` | TypeDB gRPC host |
| `TYPEDB_PORT` | `1729` | TypeDB gRPC port |
| `TYPEDB_DATABASE` | `zettelforge` | TypeDB database name |
| `ZETTELFORGE_BACKEND` | `typedb` | `typedb` or `jsonl` (fallback) |

## API Reference

### MemoryManager

Primary interface for all memory operations.

#### `remember(content, source_type, source_ref, domain)`

Store a memory. Entities extracted to TypeDB, text + vectors to LanceDB.

```python
note, status = mm.remember("APT28 targets NATO", domain="cti")
```

#### `remember_with_extraction(content, domain, context, min_importance, max_facts)`

Two-phase Mem0-style pipeline. Phase 1: LLM extracts salient facts. Phase 2: ADD/UPDATE/DELETE/NOOP per fact.

```python
results = mm.remember_with_extraction(
    "APT28 dropped DROPBEAR, now uses edge device exploitation",
    domain="cti", min_importance=3
)
```

#### `remember_report(content, source_url, published_date, domain, chunk_size)`

Ingest a news or threat report. Auto-chunks long content and runs two-phase extraction per chunk.

```python
results = mm.remember_report(
    content="Full report text...",
    source_url="https://example.com/report",
    published_date="2026-04-09",
    domain="cti"
)
```

#### `recall(query, domain, k, include_links, exclude_superseded)`

Blended retrieval: vector similarity + STIX graph traversal, weighted by intent.

```python
results = mm.recall("What tools does APT28 use?", k=10)
```

#### `synthesize(query, format, k, tier_filter)`

RAG synthesis over retrieved memories.

```python
result = mm.synthesize("Summarize APT28 activity", format="synthesized_brief")
# formats: "direct_answer", "synthesized_brief", "timeline_analysis", "relationship_map"
```

#### Entity Lookups

```python
mm.recall_cve("CVE-2024-3094")        # Fast CVE lookup
mm.recall_actor("Fancy Bear")         # Resolves to APT28 via TypeDB alias-of
mm.recall_tool("cobalt-strike")       # Tool/malware lookup
```

#### Knowledge Graph

```python
mm.traverse_graph("actor", "apt28", max_depth=2)
mm.get_entity_relationships("actor", "apt28")
```

## Benchmarks

Evaluated across three benchmark suites (2026-04-09):

| Benchmark | What it measures | Key result |
|-----------|-----------------|------------|
| [LOCOMO](https://snap-research.github.io/locomo/) (ACL 2024) | Conversational memory recall | 15.0% accuracy, 0.33 avg score |
| [CTIBench](https://huggingface.co/datasets/AI4Sec/cti-bench) (NeurIPS 2024) | CTI entity extraction & attribution | Baseline established |
| RAGAS | Retrieval quality | 75.9% keyword presence |

### LOCOMO Results (v1.3.0 -> v1.5.0)

| Category | v1.3.0 | v1.5.0 | Change |
|----------|--------|--------|--------|
| single-hop | 5.0% | 10.0% | +5.0 |
| multi-hop | 0.0% | 0.0% | avg_score 0.0 -> 0.15 |
| temporal | 0.0% | 0.0% | -- |
| open-domain | 30.0% | 30.0% | avg_score +0.025 |
| adversarial | 35.0% | 35.0% | -- |
| **Overall** | **14.0%** | **15.0%** | **+1pp, p95 latency 190s -> 1.3s** |

See the [full benchmark report](benchmarks/BENCHMARK_REPORT.md) for analysis and roadmap.

## Project Structure

```
src/zettelforge/
    memory_manager.py       # Primary agent interface
    typedb_client.py        # TypeDB STIX 2.1 knowledge graph client
    note_schema.py          # Pydantic MemoryNote model
    note_constructor.py     # Content enrichment, entity extraction
    memory_store.py         # JSONL + LanceDB persistence
    fact_extractor.py       # Phase 1: LLM salient fact extraction
    memory_updater.py       # Phase 2: ADD/UPDATE/DELETE/NOOP decisions
    knowledge_graph.py      # Graph factory (TypeDB-first, JSONL fallback)
    graph_retriever.py      # BFS traversal, hop-distance scoring
    blended_retriever.py    # Merge vector + graph with policy weights
    vector_retriever.py     # Cosine similarity + entity boost
    intent_classifier.py    # Query intent routing
    entity_indexer.py       # Entity extraction and O(1) index
    alias_resolver.py       # TypeDB alias resolution + JSON fallback
    synthesis_generator.py  # RAG answer generation
    cti_integration.py      # OpenCTI platform connector
    sigma_generator.py      # Sigma rule generation from IOCs
    context_injection.py    # Proactive agent context loading
    schema/
        stix_core.tql       # STIX 2.1 TypeQL schema definition
        stix_rules.tql      # TypeDB inference functions
        seed_aliases.py     # CTI alias seeding script

docker/
    docker-compose.yml      # TypeDB container

benchmarks/
    BENCHMARK_REPORT.md     # Unified results and analysis
    locomo_benchmark.py     # LOCOMO evaluation script
    ctibench_benchmark.py   # CTIBench adapter (NeurIPS 2024)
    ragas_benchmark.py      # RAGAS retrieval quality wrapper
```

## Development

```bash
git clone https://github.com/rolandpg/zettelforge.git
cd zettelforge
pip install -e ".[dev]"

# Start TypeDB
docker compose -f docker/docker-compose.yml up -d

# Run tests (82 tests)
pytest tests/ -v

# Run benchmarks
python benchmarks/locomo_benchmark.py --samples 20
python benchmarks/ctibench_benchmark.py --task ate --samples 50
python benchmarks/ragas_benchmark.py --samples 20

# Format and lint
black src/zettelforge/
ruff check src/zettelforge/
```

## Roadmap

- [x] Core storage and retrieval (JSONL + LanceDB)
- [x] Entity extraction and indexing (CVEs, actors, tools, campaigns)
- [x] Knowledge graph with temporal indexing
- [x] Intent-based query routing
- [x] RAG synthesis layer
- [x] Causal triple extraction
- [x] CTI platform integration + Sigma generation
- [x] Mem0-style two-phase extraction pipeline (v1.4.0)
- [x] Graph traversal retrieval with blended scoring (v1.5.0)
- [x] Benchmark suite: LOCOMO + CTIBench + RAGAS
- [x] **Hybrid TypeDB + LanceDB architecture (v2.0.0)**
- [x] **STIX 2.1 schema with 9 entity types and 8 relation types**
- [x] **TypeDB alias inference (36 CTI aliases seeded)**
- [x] **Report ingestion with chunking (`remember_report()`)**
- [ ] Conversational entity extractor (improve LOCOMO from 15% to ~30%)
- [ ] CTIBench adapter fixes (ATT&CK DB cross-reference)
- [ ] LLM-judge scoring for benchmarks
- [ ] Azure Bicep/Terraform IaC templates

## License

MIT License - see [LICENSE](LICENSE) file

## Acknowledgments

- Inspired by [Zettelkasten](https://en.wikipedia.org/wiki/Zettelkasten) and [A-Mem](https://arxiv.org/abs/2602.10715) (NeurIPS 2025)
- Two-phase pipeline inspired by [Mem0](https://mem0.ai/research) architecture
- STIX 2.1 schema informed by [typedb-cti](https://github.com/typedb-osi/typedb-cti)
- Benchmarked against [LOCOMO](https://snap-research.github.io/locomo/) (ACL 2024) and [CTIBench](https://arxiv.org/abs/2406.07599) (NeurIPS 2024)
- Ontology: [TypeDB](https://typedb.com) (Apache-2.0) | Vectors: [LanceDB](https://lancedb.com) | LLM: [Ollama](https://ollama.com) | Schema: [Pydantic](https://pydantic.dev)

## Links

- Repository: https://github.com/rolandpg/zettelforge
- Issues: https://github.com/rolandpg/zettelforge/issues
- Benchmark Report: [benchmarks/BENCHMARK_REPORT.md](benchmarks/BENCHMARK_REPORT.md)
- Architecture Plan: [docs/superpowers/plans/2026-04-09-hybrid-typedb-lancedb-architecture.md](docs/superpowers/plans/2026-04-09-hybrid-typedb-lancedb-architecture.md)
