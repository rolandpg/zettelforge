# ZettelForge — Master TODO

**Last verified:** 2026-04-16
**Current version:** 2.1.1
**Phase:** SQLite Migration Complete, Package Alignment Next

---

## Legend

- [x] Verified complete
- [ ] Outstanding
Priority: **P0** = do now, **P1** = this sprint, **P2** = next sprint, **P3** = backlog

---

## Decisions Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-04-15 | Anti-aversion cleanup is P0 | OS community adoption drives SaaS revenue. Repo must feel community-first. |
| 2026-04-15 | Enterprise/on-prem is hidden menu | Separate repo, not advertised in OS repo. For clients who can't use SaaS (FedRAMP etc). |
| 2026-04-15 | SaaS hosting is the revenue pitch | "We host it for you" not "upgrade to unlock features" |
| 2026-04-15 | SQLite + LanceDB is the community storage path | Embedded, zero-config, ACID for notes+KG+entities. LanceDB stays for vectors. |
| 2026-04-15 | PostgreSQL + AGE + pgvector for SaaS tier | Single managed DB on Azure. Replaces all stores. Future work. |
| 2026-04-15 | TypeDB stays enterprise-only (hidden menu) | 4 blockers from adversarial review. Lives in separate repo. |
| 2026-04-15 | FalkorDB: PASS | SSPLv1 blocks SaaS, hybrid search unsupported, FalkorDBLite immature |
| 2026-04-15 | OpenCTI shared TypeDB DB: parked | Rely on sync agent for now |
| 2026-04-15 | TE-009 research validates architecture | Tool-based actions, dual-stream write, intent routing all confirmed by 12 papers. Three gaps identified. |
| 2026-04-16 | SQLite is default backend | Runtime factory, StorageBackend ABC, and SQLiteBackend are present. Config/docs/web defaults still need alignment. |

---

## P0: Package Alignment Fixes

Docs-first reassessment on 2026-04-16 found that code, tests, and older docs lag the current decision log.
Current-state reconciliation on 2026-04-16 found SQLite wiring in place, but package defaults, extension boundaries, STIX taxonomy, and local test collection are still inconsistent.

### Backend Defaults + Extension Boundary
- [x] Runtime backend factory defaults to SQLite (`backend_factory.py`, unset `ZETTELFORGE_BACKEND` -> `sqlite`)
- [x] CI uses SQLite for community package tests instead of advertising a fake JSONL backend matrix
- [x] Stop advertising `ZETTELFORGE_BACKEND=jsonl` as a supported backend; legacy JSONL is migration input
- [x] Align defaults across `config.py`, `config.default.yaml`, README, docs, `web/mcp_server.py`, and `knowledge_graph.py`
- [x] Remove TypeDB as a community default from `config.py`, `config.default.yaml`, README, and reference docs
- [x] Mark TypeDB docs as extension-only/hidden-menu, not baseline package architecture
- [x] Move or skip TypeDB-only tests using `pytest.importorskip("zettelforge_enterprise...")`
- [x] Move or skip CTI/OpenCTI integration tests that import extension-only modules

### STIX 2.1 Entity Taxonomy
- [x] EntityExtractor regex extracts APT-style designations as `intrusion_set`
- [x] Update remaining tests that still expect `APT28` under `actor` (`tests/test_conversational_entities.py`)
- [x] Update `NoteConstructor._infer_entity_type("APT28")` to return `intrusion_set`
- [x] Update graph edge creation so `intrusion_set` gets CTI relationships
- [x] Keep `recall_actor()` as compatibility helper searching `actor`, `threat_actor`, and `intrusion_set`
- [ ] Update docs/examples that call APT groups "actors" where STIX 2.1 requires `intrusion_set`

### Deployable Web App Hardening
- [x] Require authentication for exposed `web/app.py` API endpoints (API key minimum; localhost remains usable without setup)
- [x] Default web host to `127.0.0.1`; require API key before binding to `0.0.0.0`
- [x] Add request limits for `content`, `query`, `k`, synthesis format
- [x] Add rate limiting or backpressure guards for `remember()`, `synthesize()`
- [x] Fix stored XSS by escaping dynamic `innerHTML` rendering

### Runtime/Test Reliability
- [ ] Add `MemoryManager(enable_background: bool = True)` or equivalent test switch
- [ ] Add explicit `MemoryManager.close()` / shutdown API; current code only registers `atexit` handlers and `store.close`
- [x] Make local test collection pass; `pytest --collect-only -q` collects community tests and skips missing enterprise modules
- [ ] Ensure `pytest -q` passes from clean checkout with no TypeDB, OpenCTI, Ollama
- [ ] Add package smoke tests: import, `python -m zettelforge version`, temp-dir round trip

### Storage Boundary Cleanup
- [x] Add compatibility alias from `store._rewrite_note` to public `store.rewrite_note`
- [ ] Replace remaining private store call sites (`memory_updater.py`, `memory_evolver.py`, `consolidation.py`, and tests) with `rewrite_note()`
- [x] Replace production causal-recall graph private access with `store.get_kg_node_by_id()`
- [ ] Replace remaining test/debug direct graph access (`kg._nodes`) with public graph/backend APIs
- [ ] Decouple `GraphRetriever` from JSONL internals (partially done — recall() uses backend, but GraphRetriever still accepts KnowledgeGraph)
- [ ] Make config/runtime/docs agree on `llm.provider`, `backend`, OpenCTI, TypeDB availability

---

## P1: Memory Evolution — Remaining Items

- [x] MemoryEvolver implementation + wired into enrichment queue
- [ ] Add config toggle: `memory_evolution: bool = True`
- [ ] Integration test: store APT28 note, add new TTP, verify APT28 note updated

---

## P1: SQLite + LanceDB Storage Migration (COMPLETE)

- [x] StorageBackend ABC (27 abstract methods + 6 added in review)
- [x] SQLiteBackend (697+ lines, WAL mode, threading.RLock, OCSF logging)
- [x] VulnerabilityMeta column (P0 from architecture review)
- [x] Backend factory with SQLite default + auto-detection
- [x] MemoryManager wired to StorageBackend
- [x] KG calls routed through backend (add_kg_node, add_kg_edge, traverse, causal BFS)
- [x] Entity index routed through backend (add_entity_mapping, get_note_ids_for_entity)
- [x] mark_access_dirty via targeted SQL UPDATE
- [x] Migration script: JSONL → SQLite with backup + verification
- [x] CI backend matrix configured for `jsonl` and `sqlite`
- [x] CI/backend tests drop JSONL as a supported backend claim
- [x] 5 integration tests (remember/recall roundtrip, entity lookup, KG edges, supersession, count)
- [x] 30 SQLite unit tests passing

### LanceDB Cleanup (P2)
- [ ] Remove dead metadata columns (content, context, keywords, tags — never read)
- [ ] Fix supersession: remove superseded note vectors from LanceDB
- [ ] Fix silent indexing failures: retry or flag failed notes
- [ ] Add `last_indexed_at` in SQLite for drift detection

---

## P1: Benchmarks

- [x] CTIBench ATE: F1 0.0 → 0.146 (pipeline fixed, ICS noise removed)
- [ ] F1 ceiling ~0.15 with retrieval-only — LLM-based mapping needed for 0.30+ (P2)
- [ ] RAGAS re-run with `--domain cti`

---

## P1: Causal Graph (COMPLETE)

- [x] edge_type bug fix, alias resolution, reverse traversal, bidirectional provenance_chain
- [x] recall() causal boost (forward + backward + source note_id)

---

## P1: Persistence Semantics (Knowledge Layer paper)

- [ ] Add `persistence_semantics` field to MemoryNote: `knowledge | memory | wisdom | intelligence`
- [ ] Knowledge (IOCs, TTP defs): indefinite, strict consistency, no decay
- [ ] Memory (analyst sessions): Ebbinghaus decay, soft updates
- [ ] Wisdom (synthesized insights): evidence-gated revision
- [ ] Intelligence (reasoning context): ephemeral

---

## P2: Format Stability Phase 2 (developer experience)

- [ ] `zettelforge init` command (interactive provider setup)
- [ ] `zettelforge health` command (parse rate tracking, LLM connectivity)
- [ ] OpenAI + Anthropic provider backends
- [ ] Config file support (config.toml)
- [ ] Demo improvements (synthesis step, LLM availability detection)
- [ ] Integration test: 100 memory updates with format validation

---

## P2: Architecture

- [ ] Decompose MemoryManager — 1000+ lines, 26 methods, 7+ subsystem deps
- [ ] Wire GovernanceValidator to config

---

## P2: Graph Traversal Optimization

- [ ] Strategy 2: Alias consolidation during traversal
- [ ] Strategy 3: Relationship-typed traversal
- [ ] Strategy 4: Bi-directional BFS

---

## P2: Governance Middleware (SSGM paper)

- [ ] Upgrade contradiction detection from negation heuristic to NLI-based
- [ ] Weibull temporal decay for note scoring in recall()
- [ ] Immutable Episodic Log (append-only for audit trail)

---

## P2: Growth Weeks 2-4

### Week 2: Launch Push
- [x] Show HN posted (2026-04-15)
- [x] LangChain retriever wrapper (PR #48)
- [ ] r/netsec deep-dive post draft
- [ ] Twitter/X thread with demo GIF + comparison table
- [ ] LinkedIn post (SaaS hosting angle, waitlist CTA)
- [ ] Blog post: "Why Your AI Agent Needs CTI-Specific Memory"
- [ ] r/cybersecurity post

### Week 3: Ecosystem
- [ ] CrewAI tool wrapper
- [ ] Blog post: "How ZettelForge Extracts Entities from CTI Text"
- [ ] YouTube 5-min demo
- [ ] BSides CFP + DEF CON AI Village demo application

### Week 4: Compound
- [ ] Blog post: "Giving Claude Code a Cybersecurity Brain with MCP"
- [ ] Podcast outreach (5 cybersecurity podcasts)
- [ ] GitHub Sponsors setup
- [ ] LlamaIndex integration

---

## P2: Evaluation Improvements (from research)

- [ ] LLM-as-Judge benchmark (replace lexical metrics like F1/BLEU)
- [ ] Context saturation measurement (does memory actually help vs full context?)
- [ ] Interdependent CTI task chains (report → predict → defend)
- [ ] CTI-Specific Benchmark v2
- [ ] Scale test at 10K/50K/100K notes

---

## P2: OpenCTI Data Parity

- [ ] Rebuild OpenCTI sync client (community, basic)
- [ ] Infrastructure entity type extractor

---

## P3: Future / SaaS Foundation

- [ ] PostgreSQL + AGE + pgvector SaaS backend (when first customer)
- [ ] Thread tenant_id through storage
- [ ] API reference auto-generation
- [ ] Reduce CI runtime
- [ ] Graph densification (strategy 5)
- [ ] DeltaMem evaluation (when code open-sourced)
- [ ] Discord server (5 channels) — parked from Growth Week 1

---

## Completed (verified in code)

### Phase 0 — Intelligence & Discovery
- [x] Architecture review — 3 agents, P0-P2 findings
- [x] Governance audit — 12 controls
- [x] GOV-012 implementation — structlog + OCSF, 38/38 tests
- [x] Research synthesis — 12 papers, 14 findings, 3 critical gaps
- [x] Benchmark strategic briefing
- [x] Dual-stream write — 10-15x latency improvement
- [x] OpenCTI gap analysis

### Phase 1, Sprint 1 — P0 Blockers
- [x] O(n) supersession → entity-index lookup
- [x] File locking on JSONL writes (fcntl.flock)
- [x] SQL injection fix (_sanitize_filter_value)
- [x] LanceDB dedup guard
- [x] Orphaned temp file cleanup
- [x] Entity index invalidation on supersession

### Phase 1, Sprint 2 (partial)
- [x] Async entity index saves (5s write-behind)
- [x] Persist access_count (60s deferred flush)
- [x] GraphRetriever uses public API
- [x] Config unification via get_config()

### Anti-Aversion Cleanup
- [x] extensions.py replacing edition gating
- [x] All features ungated
- [x] ThreatRecall/Threatengram branding removed
- [x] LICENSE-ENTERPRISE + enterprise/ stub deleted
- [x] GOVERNANCE.md + ARCHITECTURE.md added
- [x] All templates/docs cleaned

### Growth Week 1
- [x] README overhaul + demo command + examples
- [x] 12 good-first-issues + labels + CODEOWNERS
- [x] 6 awesome list PRs (84K+ reach)
- [x] GitHub topics (12)

### CI/CD
- [x] All CI jobs green
- [x] CI segfault fix
- [x] Entity taxonomy alignment
- [x] Internal docs gitignored
- [x] CI backend matrix (jsonl + sqlite)

### Entity Extraction & Schema
- [x] IOC extractors (ipv4, domain, hash, url, email)
- [x] AttackPattern extraction (MITRE T-codes)
- [x] IntrusionSet split (APT/UNC/TA/FIN)
- [x] TLP + STIX confidence fields
- [x] CVSS/EPSS fields (VulnerabilityMeta)
- [x] Intent classifier (5 intents)
- [x] Graph traversal strategy 1
- [x] Dual-stream write (async enrichment queue)

### Format Stability Phase 1
- [x] json_parse.py — shared extraction with stats
- [x] Fixed Ollama system prompt bug
- [x] json_mode parameter (Ollama format: "json")
- [x] All 5 parse sites refactored
- [x] Retry on memory_updater + entity_indexer
- [x] llama-cpp-python → optional dep
- [x] Causal relation validation

### Consolidation Layer (GAM-inspired)
- [x] Merged from dev branch with 5 bug fixes
- [x] EPG/TAN dual-tier with semantic shift detection
- [x] Integrated into MemoryManager.remember() write path
- [x] 14 consolidation tests passing

### Causal Chain (MAGMA-inspired)
- [x] Fixed edge_type bug (causal edges invisible to retrieval)
- [x] Alias resolution on causal triple subjects/objects
- [x] Reverse causal traversal (get_incoming_causal for "why" queries)
- [x] Bidirectional provenance_chain() with direction param
- [x] recall() causal boost traverses both forward + backward

### Memory Evolution (A-Mem inspired)
- [x] MemoryEvolver implementation (255 lines, 25+ tests)
- [x] Wired into enrichment queue (job_type dispatch)
- [x] Auto-triggers after remember() when >= 3 notes
- [x] Public evolve_note() API for manual/MCP invocation

### SQLite Storage Migration (2026-04-16)
- [x] StorageBackend ABC (33 methods)
- [x] SQLiteBackend (700+ lines, WAL, RLock, OCSF logging, VulnerabilityMeta)
- [x] Backend factory with auto-detection
- [x] MemoryManager wired to StorageBackend (KG, entities, notes)
- [x] Migration script with backup + verification
- [x] 30 unit tests + 5 integration tests
- [x] CI backend matrix (jsonl + sqlite)

### Governance
- [x] Spec-driven governance manifest (governance/controls.yaml)
- [x] Spec-drift detection tests (7 tests, catches phantom controls)
- [x] Removed phantom GOV-006 and undocumented print() check
- [x] Coverage gate enforced (--cov-fail-under=67)

### Growth (Session: 2026-04-15)
- [x] Demo GIF (Playwright-generated, 699KB, in README)
- [x] README badges (PyPI downloads, stars, contributors, last commit, SafeSkill)
- [x] "Why ZettelForge?" narrative section
- [x] ThreatRecall logo set (mark + wordmark, SVG + PNG)
- [x] Social preview image (1280x640)
- [x] CODE_OF_CONDUCT.md (Contributor Covenant v2.1)
- [x] 9 good-first-issues updated with acceptance criteria
- [x] 3 Discussions seeded with substantive replies
- [x] Show HN posted
- [x] SafeSkill: removed one-off scripts, dynamic badge
- [x] LangChain retriever wrapper + test fix

### Benchmarks
- [x] CTIBench ATE: F1 0.0 → 0.146 (pipeline was broken, ICS noise removed)

### Research Validated (no change needed)
- [x] Tool-based memory actions (ADD/UPDATE/DELETE/NOOP) — AgeMem, Mem0, Anatomy confirm
- [x] Dual-stream write (fast+slow) — MAGMA confirms
- [x] Intent classifier (5 types) — MAGMA confirms
- [x] Blended retrieval — Mem0 confirms (graph adds only ~2% over base)

---

## What To Do Next (in order)

1. **Package Alignment P0** — TypeDB removal from community defaults, STIX taxonomy fix, web hardening, test reliability
2. **Persistence semantics** — 4-tier note types (knowledge/memory/wisdom/intelligence)
3. **Growth Week 2** — r/netsec, r/cybersecurity, LinkedIn, Twitter launch
4. **Format stability Phase 2** — init/health commands, cloud providers
5. **CTIBench ATE Phase 2** — LLM-based technique mapping for 0.30+ F1

---

## Research References

| Paper | Key Takeaway for ZettelForge | Status |
|-------|------------------------------|--------|
| A-Mem (NeurIPS 2025) | Memory evolution — neighbors update on new evidence | WIRED + ACTIVE |
| MAGMA | 4-graph separation (semantic/temporal/causal/entity) + intent routing | DONE |
| GAM (April 2026) | Hierarchical consolidation (EPG/TAN) + semantic shift detection | MERGED + INTEGRATED |
| SSGM | Governance middleware — NLI contradiction checks, Weibull decay, drift bounds | NOT IMPL |
| Anatomy | Format stability critical for local models, LLM-as-Judge > lexical metrics | NOT IMPL |
| Knowledge Layer | 4-layer persistence semantics (knowledge/memory/wisdom/intelligence) | NOT IMPL |
| Mem0 | Tool-based actions validated, graph variant adds only ~2% | VALIDATED |
| MemoryArena | Interdependent task chains needed for evaluation | NOT IMPL |
| PaperScope | Multi-document reasoning is universal bottleneck | ACKNOWLEDGED |
| DeltaMem | Memory-based Levenshtein Distance — monitor for open-source release | MONITORING |
| AgeMem | Tool-based RL memory management — overkill for v1 | DEFERRED |
| MemGPT | Tiered paging — conversational focus, not CTI-relevant | DEFERRED |
