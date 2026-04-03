# Changelog

All notable changes to A-MEM (Agentic Memory) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 6: Knowledge Graph and IEP 2.0 support (36/36 tests passing)
- Phase 7: Synthesis Layer with RAG-as-Answer (21/21 tests passing)
- Integration tests for Phase 6/7 interoperability (11/11 tests passing)
- Performance and scaling test suite (6/6 tests passing)
- **Parallel Evolution Processing** — ThreadPoolExecutor implementation for 16x speedup
- Documentation suite (docs/) with 14 comprehensive documents
- `PARALLEL_EVOLUTION.md` — Performance optimization RFC
- `PRD_PRODUCTPLAN_COMPARISON.md` — Alignment analysis between PRD and Product Plan

### Changed
- **MAJOR PERFORMANCE**: LLM model upgraded from `nemotron-3-nano` to `qwen2.5:3b` (10x faster per call)
- **MAJOR PERFORMANCE**: `remember()` end-to-end latency reduced from ~48s to ~3s (16x speedup)
- Improved graph traversal performance
- Enhanced context retrieval latency
- Updated `ARCHITECTURE.md` with parallel evolution diagrams
- Updated `COMPONENTS.md` with new performance specifications
- Updated `INDEX.md` with new documentation references
- Product Plan v2.1 — Phase 6/7 marked complete, timeline accelerated

### Performance
- Sequential evolution (10 candidates): 2.79s → Parallel evolution: 0.47s (5.9x speedup)
- LLM call latency: ~10s (nemotron) → ~0.11s (qwen2.5:3b) (90x speedup)
- End-to-end `remember()`: ~48s → ~3s (16x speedup)

### Documentation
- All documentation aligned with actual implementation status
- Test count standardized: 143/143 tests passing
- Change control record created per GOV-001 and GOV-010

## [1.0.0-alpha.1] - 2026-04-02

This is the first pre-release of A-MEM (Agentic Memory), establishing the core versioning and release management infrastructure.

### Added
- Version control infrastructure (VERSION, CHANGELOG, CODEOWNERS, Makefile)
- scripts/version.py - Version management CLI
- scripts/changelog.py - Release notes generator
- .githooks/pre-commit - Pre-commit hook for security checks
- Phase 1: Entity Indexing (CVE, Actor, Tool, Campaign, Sector extraction)
- Phase 2: Entity-Guided Linking
- Phase 3: Date-Aware Retrieval with supersedes tracking
- Phase 2.5: Actor Alias Resolution
- Phase 3.5: Alias Auto-Update mechanism
- Phase 4: Mid-Session Snapshot
- Phase 4.5: Epistemic Tiering (A/B/C tiers)
- Phase 5: Cold Archive
- Phase 5.5: Reasoning Memory
- Phase 6: Ontology, Knowledge Graph, IEP 2.0 Policy
- Phase 7: Synthesis Layer (RAG-as-Answer)
- Documentation suite (docs/)

### Performance Metrics
- Note creation: 1151.7 notes/second
- Edge creation: 4517.8 edges/second
- Graph traversal latency: 0.00ms average
- Context retrieval: 137.42ms average
- Memory for 500 notes: 0.1MB peak

### Security
- Commit signing enabled (`commit.gpgsign=true`)
- Branch protection on `main`
- Pre-commit hook for secret detection

### Changed
- MemoryNote schema updated with embedding, links, and metadata fields
- Version control policy aligned with organization standards (GOV-002, GOV-010)

### Breaking Changes
- None (initial pre-release)

## [Unreleased]
