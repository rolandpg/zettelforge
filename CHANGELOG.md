# Changelog

## [Unreleased]

### Added
- **ZettelForge**: New proprietary memory system (rebranded and evolved from A-MEM)
  - Automatic governance validation (GOV-011)
  - Smart caching layer with TTL and metrics
  - Structured observability and logging (GOV-012)
  - Retry logic with exponential backoff for resilience
  - Full performance test suite (GOV-007 compliant)

### Changed
- Memory architecture: ZettelForge is now the single primary system
- Honcho has been deprecated due to crashes and availability issues
- Skills ontology now includes governance as first-class entities
- Architecture diagrams updated to reflect new system

### Technical Debt Addressed
- Removed dependency on external research prototype naming
- Integrated governance directly into core memory operations
- Improved LanceDB indexing and performance

**Full details**: See `research/lessons-learned-memory-architecture-20260406.md` and `research/zettelforge-lancedb-optimization-plan-20260406.md`

---
*Generated 2026-04-06 by Nexus during memory architecture modernization sprint.*
