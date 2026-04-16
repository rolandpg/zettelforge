# ZettelForge — Master TODO

**Last verified:** 2026-04-15
**Current version:** 2.1.1
**Phase:** Community Launch + Research-Driven Features (Format Stability + Consolidation DONE)

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

---

## P0: Anti-Aversion Cleanup (COMPLETE)

- [x] Created extensions.py — clean extension loader with env var fallback
- [x] Ungated all community features (temporal queries, remember_report, traverse_graph, synthesize)
- [x] Rewrote edition.py as thin shim over extensions.py
- [x] Cleaned web layer — all ThreatRecall → ZettelForge, 402→501, MCP tools renamed
- [x] Cleaned config/ocsf/__init__ branding
- [x] Deleted LICENSE-ENTERPRISE, enterprise/ stub
- [x] README: "Extensions" replaces "Community vs Enterprise"
- [x] Added GOVERNANCE.md (MIT commitment) + ARCHITECTURE.md
- [x] Cleaned issue/PR templates, CONTRIBUTING, CHANGELOG
- [x] Cleaned docs site, MCP skill, pyproject
- [x] CI green on all changes

---

## P0: Growth Week 1 (COMPLETE)

- [x] README overhaul — hero, comparison table, quickstart, features, badges
- [x] pyproject.toml keywords (10 terms)
- [x] GitHub topics (12 topics)
- [x] `python -m zettelforge demo` command + examples/
- [x] 12 good-first-issues created (#36-#47)
- [x] Labels + CODEOWNERS
- [x] 6 awesome list PRs submitted (84K+ combined reach)
- [x] Demo recording script
- [x] Record demo GIF (Playwright-based: scripts/record-demo-playwright.js)
- [x] Enable GitHub Discussions (repo Settings → Features)
- [x] MCP marketplace submission (mcpmarket.com — auto-indexed, already listed)
- [x] awesome-mcp-servers PR submitted (punkpeye/awesome-mcp-servers#4911)

---

## P0: Format Stability Phase 1 (COMPLETE)

- [x] `json_parse.py` — shared LLM output extraction with code fence handling + stats
- [x] Fixed Ollama system prompt bug (was silently dropped)
- [x] Added `json_mode` parameter → Ollama `format: "json"`
- [x] Refactored all 5 parse sites to use `json_parse.py`
- [x] Single retry on memory_updater + entity_indexer (temp bump 0.1→0.3, json_mode=True)
- [x] Moved llama-cpp-python to optional dep (`pip install zettelforge[local]`)
- [x] Causal relation validation against allowlist
- [x] Parse failure logging with schema name + raw output

### Format Stability Phase 2 (P2 — developer experience)
- [ ] `zettelforge init` command (interactive provider setup)
- [ ] `zettelforge health` command (parse rate tracking, LLM connectivity)
- [ ] OpenAI + Anthropic provider backends
- [ ] Config file support (config.toml)
- [ ] Demo improvements (synthesis step, LLM availability detection)
- [ ] Integration test: 100 memory updates with format validation
- [ ] Test on actual DGX Spark local model

---

## P1: Merge consolidation.py (COMPLETE)

- [x] Copied consolidation.py + tests from dev branch
- [x] Fixed tier persistence (Critical Bug 1) — `_rewrite_note()` after promotion
- [x] Fixed EPG window filter (Critical Bug 2) — `_last_consolidation_time` tracking
- [x] Fixed timezone blocker — naive timestamps throughout (matches NoteConstructor)
- [x] Cached entity extraction (O(N) not O(N^2))
- [x] Thread safety lock on async consolidation
- [x] Dead imports removed
- [x] Tests with real MemoryNote objects (14 total)
- [x] Integrated into MemoryManager.remember() write path
- [x] 186 tests passing

---

## P1: Memory Evolution (A-Mem, NeurIPS 2025)

Highest-value missing feature per research. When new CTI arrives, existing notes should auto-update.

- [x] Implement `MemoryEvolver` — find_evolution_candidates, evaluate_evolution, apply_evolution, rollback (255 lines, 25+ tests)
- [x] Find top-k neighbors via vector similarity (uses recall() with blended retrieval)
- [x] LLM prompt: new note + neighbors → evolved version with confidence scoring
- [x] Apply updates to neighbor notes (persist changes, re-embed, previous_raw rollback)
- [x] Wire into MemoryManager enrichment queue (job_type dispatch, background worker)
- [x] Public API: `evolve_note(note_id, sync=False)` for manual/MCP invocation
- [x] Auto-triggers after `remember()` when >= 3 notes exist
- [x] Tests: 25+ unit tests covering full pipeline, all passing
- [ ] Add config toggle: `memory_evolution: bool = True`
- [ ] Integration test: store APT28 note, add new TTP, verify APT28 note updated

---

## P1: SQLite + LanceDB Storage Migration

Replace JSONL with SQLite for notes, KG, and entity index. LanceDB stays for vectors. Reduces 5 stores → 2 with ACID guarantees.

### Prerequisites
- [ ] Define storage adapter interface (Python ABC)
- [ ] Decouple GraphRetriever from KG private internals

### SQLite Backend
- [ ] `notes` table replacing notes.jsonl (WAL mode)
- [ ] `kg_nodes` + `kg_edges` tables replacing KG JSONL files
- [ ] Entity index as SQL index (eliminates 5s deferred flush)
- [ ] Access count via SQL UPDATE (eliminates 60s deferred flush)
- [ ] Migration script: JSONL → SQLite
- [ ] Reconciliation: detect notes in SQLite missing from LanceDB

### LanceDB Cleanup
- [ ] Remove dead metadata columns (content, context, keywords, tags — never read)
- [ ] Fix supersession: remove superseded note vectors from LanceDB
- [ ] Fix silent indexing failures: retry or flag failed notes
- [ ] Add `last_indexed_at` in SQLite for drift detection

### Backend Routing
- [ ] `ZETTELFORGE_BACKEND=sqlite` as new default
- [ ] `ZETTELFORGE_BACKEND=jsonl` as legacy fallback
- [ ] Auto-detect: SQLite exists → use it; only JSONL → use JSONL

---

## P1: Benchmarks

- [ ] CTIBench ATE fix — ~2.25 hrs, projected F1: 0.30-0.40
  - [ ] Isolate techniques in separate domain
  - [ ] Increase k from 10 to 20-30
  - [ ] Reframe query without wrapper
- [ ] RAGAS re-run with `--domain cti`

---

## P1: Causal Graph (MAGMA paper — CTI differentiator)

Enables "why" queries. Infrastructure was already built but broken by edge_type bug.

- [x] Fix edge_type bug — store_causal_edges() now passes edge_type="causal" (was defaulting to "heuristic", making all causal edges invisible)
- [x] Alias resolution on causal triple subjects/objects before storage
- [x] Reverse causal traversal — get_incoming_causal() for "why did X happen?" queries
- [x] provenance_chain() supports forward + backward direction
- [x] recall() causal boost uses both forward + backward traversal + source note_id
- [x] Existing infrastructure verified working: extract_causal_triples(), store_causal_edges(), get_causal_edges(), intent classifier CAUSAL routing, background enrichment queue

---

## P1: Persistence Semantics (Knowledge Layer paper)

Notes need different update/decay behavior by type.

- [ ] Add `persistence_semantics` field to MemoryNote: `knowledge | memory | wisdom | intelligence`
- [ ] Knowledge (IOCs, TTP defs): indefinite, strict consistency, no decay
- [ ] Memory (analyst sessions): Ebbinghaus decay, soft updates
- [ ] Wisdom (synthesized insights): evidence-gated revision
- [ ] Intelligence (reasoning context): ephemeral

---

## P2: Sprint 3 — Architecture

- [ ] Decompose MemoryManager — 945 lines, 26 methods, 7+ subsystem deps
- [ ] Move llama-cpp-python to optional deps
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
- [ ] Immutable Episodic Log (append-only JSONL for audit trail)

---

## P2: Growth Weeks 2-4

### Week 2: Launch Push
- [ ] r/netsec deep-dive post draft
- [ ] Show HN draft (ready in tasks/show-hn-draft.md)
- [ ] Post Show HN (Tuesday 8-9 AM ET)
- [ ] Twitter/X thread with demo GIF + comparison table
- [ ] LinkedIn post (SaaS hosting angle, waitlist CTA)
- [ ] Blog post: "Why Your AI Agent Needs CTI-Specific Memory"
- [ ] LangChain retriever wrapper
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

### Research Validated (no change needed)
- [x] Tool-based memory actions (ADD/UPDATE/DELETE/NOOP) — AgeMem, Mem0, Anatomy confirm
- [x] Dual-stream write (fast+slow) — MAGMA confirms
- [x] Intent classifier (5 types) — MAGMA confirms
- [x] Blended retrieval — Mem0 confirms (graph adds only ~2% over base)

---

## What To Do Next (in order)

1. **Growth Week 1 remainder** — demo GIF, Discussions, Discord, r/netsec draft, Show HN
2. **Causal graph** — the CTI differentiator, enables "why" queries (MAGMA paper)
3. **Memory evolution** — highest-value missing feature per 12 papers (A-Mem paper)
4. **SQLite migration** — storage reliability, eliminates 8 crash windows per remember()
5. **CTIBench ATE fix** — 2.25 hrs for 8-11x F1 improvement
6. **Persistence semantics** — 4-tier note types (knowledge/memory/wisdom/intelligence)
7. **Format stability Phase 2** — init/health commands, cloud providers, config file

---

## Research References

| Paper | Key Takeaway for ZettelForge | Status |
|-------|------------------------------|--------|
| A-Mem (NeurIPS 2025) | Memory evolution — neighbors update on new evidence | NOT IMPL |
| MAGMA | 4-graph separation (semantic/temporal/causal/entity) + intent routing | PARTIAL (intent classifier done, causal missing) |
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
