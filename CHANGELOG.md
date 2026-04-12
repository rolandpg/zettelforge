# Changelog

All notable changes to ZettelForge are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [2.1.0] - 2026-04-12

### Added
- Open-core edition system (Community MIT + Enterprise BSL-1.1)
- Edition detection via `THREATENGRAM_LICENSE_KEY` or enterprise package
- `/api/edition` endpoint showing feature availability
- `EditionError` for clear upgrade messaging
- `LICENSE-ENTERPRISE` (BSL-1.1) for enterprise features
- GitHub issue/PR templates, SECURITY.md, CODE_OF_CONDUCT.md

### Changed
- Dependencies split: core (MIT) vs `pip install zettelforge[enterprise]`
- Enterprise-only features: TypeDB STIX ontology, temporal KG queries,
  advanced synthesis formats, report ingestion, multi-hop traversal,
  OpenCTI integration, Sigma generation, multi-tenant auth
- Community gets full memory pipeline: blended retrieval, two-phase
  extraction, intent routing, causal triples, cross-encoder reranking

## [2.0.0] - 2026-04-09

### Added
- Hybrid TypeDB + LanceDB architecture
- STIX 2.1 schema with 9 entity types, 8 relationship types
- TypeDB alias inference (36 CTI aliases: APT28/Fancy Bear/Strontium, etc.)
- Report ingestion with auto-chunking (`remember_report()`)
- In-process embeddings via fastembed (no Ollama needed for embeddings)
- Local LLM via llama-cpp-python (Qwen 2.5 3B)
- Conversational entity extraction (person, location, org, event, activity, temporal)
- Multi-tenant OAuth/JWT authentication
- ThreatRecall web UI (FastAPI)
- MCP server for Claude Code integration
- OpenCTI continuous sync
- MemoryAgentBench (ICLR 2026) benchmark
- Configuration system with layered resolution (env > yaml > defaults)
- Documentation suite (Diataxis framework)

### Changed
- Knowledge graph backend: TypeDB-first with JSONL fallback
- Embedding provider: fastembed (in-process ONNX) replaces Ollama HTTP
- Bumped all benchmarks: CTI 75%, LOCOMO 18%, RAGAS 78.1%

## [1.5.0] - 2026-04-08

### Added
- GraphRetriever for multi-hop note discovery via knowledge graph
- BlendedRetriever combining vector + graph results with policy weights
- Rewritten `recall()` with blended vector + graph retrieval
- CTIBench (NeurIPS 2024) benchmark adapter
- RAGAS retrieval quality benchmark

## [1.4.0] - 2026-04-07

### Added
- FactExtractor (Phase 1): LLM-based salient fact extraction with importance scoring
- MemoryUpdater (Phase 2): ADD/UPDATE/DELETE/NOOP decision engine
- `remember_with_extraction()` two-phase pipeline

## [1.3.0] - 2026-04-07

### Added
- Sigma rule generation from IOCs
- Microsoft Sentinel rule conversion

## [1.2.0] - 2026-04-07

### Added
- CTI platform integration (Django CTI database connector)
- Proactive context injection for agent workflows

## [1.0.0] - 2026-04-06

### Added
- Core memory pipeline (remember, recall, vector search)
- Knowledge graph with JSONL persistence
- Entity extraction (CVE, actor, tool, campaign)
- Causal triple extraction (LLM-powered)
- Temporal graph indexing
- RAG synthesis (direct_answer format)
- Intent classification and query routing
- Cross-encoder reranking
