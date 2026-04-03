# Changelog

All notable changes to A-MEM (Agentic Memory) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 6: Knowledge Graph and IEP 2.0 support
- Phase 7: Synthesis Layer with RAG-as-Answer
- Integration tests for Phase 6/7 interoperability
- Performance and scaling test suite

### Changed
- Improved graph traversal performance
- Enhanced context retrieval latency

## [1.0.0] - 2026-04-02

### Added
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

### Performance Metrics
- Note creation: 1151.7 notes/second
- Edge creation: 4517.8 edges/second
- Graph traversal latency: 0.00ms average
- Context retrieval: 137.42ms average
- Memory for 500 notes: 0.1MB peak

### Changed
- MemoryNote schema updated with embedding, links, and metadata fields
- Version control policy aligned with organization standards

### Security
- Commit signing enabled
- Branch protection rules configured on main

## Format

### Types
- `Added` for new features
- `Changed` for modifications to existing functionality
- `Deprecated` for features marked for removal
- `Removed` for features removed
- `Fixed` for bug fixes
- `Security` for vulnerability fixes

### Breaking Changes
Breaking changes are marked with a `BREAKING:` prefix and include migration notes.
