# Changelog

All notable changes to ZettelForge are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [2.3.0] - 2026-04-17

Pluggable LLM provider infrastructure (RFC-002 Phase 1), MCP server
as a first-class Python module, PyPI discoverability refresh, SEO
foundations across the docs site, and a full docs-vs-code
reconciliation. All additions are backward-compatible; no existing
API changes. Supersedes the never-tagged 2.2.1 metadata patch —
its PyPI classifier / keyword / image-URL changes are folded in
below.

### Added

- **Pluggable LLM provider infrastructure (RFC-002 Phase 1)** — new
  `zettelforge.llm_providers` package with a `@runtime_checkable`
  `LLMProvider` protocol, a thread-safe registry, and built-in
  providers for `local` (llama-cpp-python), `ollama`, and `mock`.
  The public `generate()` signature is unchanged; all 7 existing call
  sites (`fact_extractor`, `memory_updater`, `synthesis_generator`,
  `intent_classifier`, `note_constructor`, `entity_indexer`,
  `memory_evolver`) keep working without modification. Third-party
  providers can register via the `zettelforge.llm_providers`
  entry-point group. `openai_compat` and `anthropic` providers land
  in Phase 2 and Phase 3.
- **`LLMConfig` expanded** — new `api_key`, `timeout`, `max_retries`,
  `fallback`, and `extra` fields. `api_key` supports `${ENV_VAR}`
  references and is redacted from `repr()`. Sensitive keys inside
  `extra` (matching `key|token|secret|password|credential|auth`) are
  redacted as well. New env overrides: `ZETTELFORGE_LLM_API_KEY`,
  `ZETTELFORGE_LLM_TIMEOUT`, `ZETTELFORGE_LLM_MAX_RETRIES`,
  `ZETTELFORGE_LLM_FALLBACK`.
- **`LLMProviderConfigurationError`** — new exception surfaced for
  non-recoverable provider setup problems (bad API key, missing
  optional SDK) so `generate()` can distinguish "try the fallback"
  from "stop and report".
- **`llm_client.reload()` helper** — clears the provider registry
  and config cache so test suites and long-lived processes can
  reconfigure the LLM backend without a process restart.
- **Hardened .gitignore** per GOV-023 — added `.env.*`, `*.key`,
  `*.pem`.
- **MCP server as a first-class module** — `python -m zettelforge.mcp`
  now works out of a `pip install zettelforge` with no git clone
  required. New package `zettelforge.mcp` (with `server.py`,
  `__main__.py`, and a console-script entry `zettelforge-mcp`).
  The previous entry point at `web/mcp_server.py` is retained as a
  thin backward-compat shim.
- **Console scripts** — `zettelforge` and `zettelforge-mcp` entry
  points added to `pyproject.toml`.
- **How-to guides** — migration (`migrate-jsonl-to-sqlite.md`),
  benchmark reproduction (`reproduce-benchmarks.md`), troubleshooting
  (`troubleshoot.md`), and upgrade (`upgrade.md`). Linked from the
  MkDocs nav.
- **Design and About sections in the docs nav** — RFC-001, RFC-002,
  RFC-003 and the origin-story narrative are now discoverable from
  `docs.threatrecall.ai`.
- **RFC-003 design proposal (docs only)** — read-path depth routing
  with a deterministic Quality Gate plus System 1 / System 2 recall
  paths. Ships with an adversarial-review artifact (4 blockers, 13
  warnings). No runtime changes yet — implementation deferred.
- **Archive directory** — `docs/archive/` holds retired v1.0.0-alpha
  snapshots (`SKILL.md`, `PACKAGE_SUMMARY.md`) with a README explaining
  their provenance.
- **`llm_ner` configuration reference** — `docs/reference/configuration.md`
  now documents `llm_ner.enabled` and the `ZETTELFORGE_LLM_NER_ENABLED`
  environment override.
- **Docs SEO foundation** — per-page canonical URLs, OpenGraph and
  Twitter-card metadata, and a `SoftwareApplication` JSON-LD block on
  the home page via a `docs/overrides/main.html` theme override. The
  `softwareVersion` value is sourced from `config.extra.version` in
  `mkdocs.yml` so it stays in sync with releases.
- **PyPI classifier refresh** — added `Topic :: Security` (primary
  filter security engineers use to browse PyPI) and
  `Topic :: Software Development :: Libraries :: Python Modules`.
  Existing `Topic :: Scientific/Engineering :: Artificial Intelligence`
  retained. Development Status stays at `4 - Beta`.
- **PyPI keyword refresh** — swapped `agent-memory` → `agentic-memory`
  (emerging category keyword) and `zettelkasten` → `llm-memory`
  (direct intent match for Mem0/Graphiti discovery traffic). Still
  10 keywords total; within the PyPI display limit.

### Changed

- **SECURITY.md** — contact updated to `contact@threatrecall.ai`,
  supported-versions table refreshed to mark `2.3.x` as current and
  `2.2.x` as the prior minor release; storage section refreshed to
  reflect SQLite-by-default.
- **`docs/llms.txt`** — rewritten to match current reality (SQLite
  default, 19 runtime entity types, correct GOV-003/007/011/012
  descriptions, MCP invocation).
- **BENCHMARK_REPORT.md** — CTIBench ATE row updated (F1 = 0.146);
  architecture summary reframed as SQLite + LanceDB default with
  TypeDB as an extension; `ctibench_results.json` date bumped.
- **README** — above-fold rewritten (CTA row, keyword density,
  PyPI-safe absolute-URL images). Pipeline step 1 entity count
  corrected from "10 types" to the 19 types `EntityExtractor`
  actually recognises.
- **README image paths** — `docs/assets/demo.gif` and
  `docs/assets/zettelforge_architecture.svg` rewritten to absolute
  `raw.githubusercontent.com` URLs so the PyPI long description
  renders correctly (relative paths 404 on the PyPI CDN). Pinned to
  the `master` ref; can be re-pinned to the `v2.3.0` tag in the
  next release PR if PyPI-side stability matters.
- **`docs/superpowers/plans/` renamed to `docs/superpowers/research/`**
  with a README making clear these are aspirational synthesis, not
  roadmap commitments. The stray untracked `docs/plans/` directory
  was removed.
- **Tutorials and governance-controls reference** — `last_updated`
  and `version` metadata refreshed.
- **`zettelforge.ontology` exports** — `TypedEntityStore`,
  `OntologyValidator`, `get_ontology_store`, `get_ontology_validator`
  removed from the top-level `__all__` (still importable from
  `zettelforge.ontology`). They are a parallel store not wired into
  `MemoryManager`.
- **`observability.py` and `cache.py` headers** — annotated as
  currently unwired; kept for future integration.
- **OCSF `_PRODUCT_VERSION`** — sourced from
  `importlib.metadata.version("zettelforge")` instead of a hard-coded
  string, so emitted OCSF events stop drifting when `__version__`
  bumps.
- **OpenGraph `og:type`** — `website` on the home page, `article`
  elsewhere (was unconditionally `article`).

### Fixed

- **OllamaProvider host routing** — now instantiates
  `ollama.Client(host=self._url)` so the configured URL actually
  takes effect (previously the module-level `ollama.generate()` call
  ignored per-instance host).
- **Provider registry race** — `register()` now checks and mutates
  under the registry lock, closing a TOCTOU window on concurrent
  provider registration.
- **MCP server lazy instantiation** — `MemoryManager` is now created
  on first tool call rather than at server import time, so `--help`
  and protocol-handshake tests don't pay the model-load cost.

### Removed

- Six superseded branches that had already been squash-merged into
  master — `feat/causal-chain-fix-and-demo-gif`,
  `feat/entity-vocabulary-expansion`,
  `feature/RFC-001-conversational-entity-extractor`,
  `fix/intent-classifier-graph-weight`,
  `fix/p0-production-blockers`, `feat/remember-evolve`.

## [2.2.0] - 2026-04-16

SQLite default backend, causal chain retrieval, memory evolution, STIX taxonomy alignment, and community-first package cleanup.

### Added

- **SQLite default backend** — SQLite (WAL mode) replaces JSONL as the default storage for notes, knowledge graph, and entity index. Zero-config, ACID guarantees. LanceDB stays for vector search. `StorageBackend` ABC (33 methods), `SQLiteBackend` (700+ lines), backend factory with auto-detection.
- **JSONL to SQLite migration script** — `scripts/migrate_jsonl_to_sqlite.py` with backup, verification, and idempotent re-runs.
- **Causal chain retrieval** — Fixed `edge_type="causal"` bug that made all LLM-extracted causal edges invisible. Added reverse traversal (`get_incoming_causal`) for "why did X happen?" queries. Bidirectional `provenance_chain()` with direction parameter.
- **Memory Evolution wired** — `MemoryEvolver` (A-Mem inspired, 255 lines) now auto-triggers after `remember()` when 3+ notes exist. Background enrichment queue dispatches evolution jobs alongside causal extraction. Public `evolve_note()` API.
- **Spec-driven governance** — `governance/controls.yaml` manifest as single source of truth. Spec-drift detection tests catch phantom controls in CI.
- **Demo GIF** — Playwright-based terminal animation in README hero.
- **LangChain retriever** — `ZettelForgeRetriever` integration for LangChain pipelines.
- **SQLite integration tests** — 5 end-to-end tests with real SQLiteBackend.
- **CODE_OF_CONDUCT.md** — Contributor Covenant v2.1.

### Changed

- **STIX 2.1 entity taxonomy** — APT/UNC/TA/FIN groups now stored as `intrusion_set` (not `actor`). `recall_actor()` searches `actor`, `threat_actor`, and `intrusion_set` for backward compatibility.
- **Web app hardened** — API key authentication required for exposed endpoints, localhost-only default, XSS fix, rate limiting, request bounds.
- **Backend defaults aligned** — `config.py`, `config.default.yaml`, `knowledge_graph.py`, tutorials, and docs all default to SQLite.
- **CI simplified** — Extension-only tests gated with `pytest.importorskip()`, no more `--ignore` flags. Backend matrix dropped fake JSONL entry.
- **Coverage threshold** — Governance doc updated from 80% to 67% to match actual enforcement.
- **CTIBench ATE** — F1 improved from 0.0 to 0.146 (fixed broken ingestion pipeline, removed ICS matrix noise).

### Fixed

- **Causal edges invisible to retrieval** — `store_causal_edges()` was not setting `edge_type="causal"` in properties, defaulting all causal edges to `"heuristic"`. `get_causal_edges()` filter found nothing.
- **Alias resolution on causal triples** — Subjects and objects now resolved before storage, preventing duplicate graph nodes.
- **Graph traversal blackout on relational queries** — FACTUAL intent was dominating CTI relational queries. Graph weight raised, RELATIONAL keywords expanded.
- **LangChain test fixture** — `persist_directory` kwarg corrected to `jsonl_path`.
- **Phantom governance controls removed** — GOV-006 (CODEOWNERS) and undocumented print() scan were in CI without spec backing.

### Removed

- One-off demo recording scripts (`record-demo-playwright.js`, `frames-to-gif.py`) — SafeSkill flagged filesystem operations.

## [2.1.1] - 2026-04-15

Production hardening release targeting P0 blockers identified in the
2026-04-14 architecture review (5 P0 issues, conducted by 3 independent
agent reviewers across 7,193-note production system). Also includes the
Sprint 3 dual-stream write path and updated benchmark results.

### Added

- **Dual-stream write path** — `remember()` now returns in ~45ms (fast
  path) by deferring causal enrichment to a background worker. Callers
  that need enrichment to complete before the next read can pass
  `sync=True` to block until the worker finishes.
- **`sync` parameter on `remember()`** — `bool`, default `False`. When
  `True`, the call blocks until background causal enrichment completes.
  Useful in tests and batch pipelines.
- **LOCOMO benchmark updated to 22.0%** (up from 18.0%) — measured with
  Ollama cloud models via the LLM judge evaluation path.

### Fixed

- **P0-1** — `_check_supersession` was O(n) on every `remember()` call,
  re-extracting entities and scanning all notes linearly. Replaced with
  entity-index lookup and vector pre-filter, reducing supersession check
  from ~500 ms at 7K notes to sub-millisecond. Usable writes now viable
  past 50K notes.
- **P0-2** — No file locking on JSONL or entity index writes allowed
  concurrent processes to corrupt data. Added `fcntl.flock()` guards on
  all JSONL and entity index write paths.
- **P0-3** — SQL injection in `VectorMemory.search()` and
  `VectorMemory.delete()` via string interpolation in LanceDB queries.
  Parameterized all LanceDB query expressions.
- **P0-4** — 378 ghost rows in LanceDB (7,571 rows vs 7,193 JSONL notes)
  caused stale embeddings to be returned. Added dedup guard in
  `_index_in_lance()` to prevent duplicate row creation on re-indexing.
  Existing ghost rows cleared by a one-time rebuild. Closes #26.
- **P0-5** — 3 orphaned temp files (206 MB total) from crashed
  `_rewrite_note()` calls had no cleanup routine. Added startup sweep to
  remove `*.tmp` files left in the notes directory.
- **P1-10** — Entity index was not invalidated on supersession, so
  superseded notes remained queryable by entity lookup. Entity index
  entries are now removed when a note is superseded.

### Security

- Parameterized LanceDB queries eliminate the SQL injection surface in
  `VectorMemory` (see P0-3 above).

---

## [2.1.0] - 2026-04-12

GOV-012 logging and observability compliance, CI/CD pipeline, and memory
evolution support.

### Added

- **GOV-012 compliance** — Structured logging via `structlog` with JSON
  output throughout all production code paths. Eliminates all bare
  `print()` calls from production code.
- **OCSF v1.3 audit events** — New `ocsf.py` module emits typed
  OCSF-schema events for all auditable operations:
  - `remember()` → OCSF API Activity (class 6003), Create activity
  - `recall()` → OCSF API Activity with query, result_count, duration_ms
  - `synthesize()` → OCSF API Activity with source_count, duration_ms
  - `GovernanceValidator.enforce()` → OCSF Authorization (class 3003)
    with `status_id` 1 (allowed) or 2 (denied) and triggering rule
  - `_index_in_lance()` → OCSF File Activity (class 1001) with
    table_name, note_id, status, duration_ms
- **Audit trail** — All OCSF events include required base fields:
  `class_uid`, `class_name`, `severity_id`, `time` (UTC ISO 8601),
  `metadata.version` ("1.3.0"), `metadata.product.name` ("zettelforge"),
  `metadata.product.version`
- **Memory evolution** — `remember()` and `remember_with_extraction()`
  accept `evolve=True` parameter to trigger supersession checks and
  knowledge graph updates rather than treating the note as additive
- **CI/CD pipeline** — Lint, test, and governance jobs added; `ruff
  format` compliance enforced on all Python source files
- **Extension detection** — detects optional `zettelforge-enterprise`
  package presence and enables extension features when available;
  `/api/edition` endpoint reports installed extensions
- GitHub issue/PR templates and CODE_OF_CONDUCT.md

### Fixed

- **LanceDB single-row bug (#26)** — Silent exception swallowing in
  `_index_in_lance()` masked indexing failures for single-note writes,
  causing the 378-row ghost row accumulation later measured at production
  scale. Structured logging and explicit error propagation prevent this
  class of silent data loss going forward.

### Changed

- All bare `print()` calls replaced with `structlog` structured logger
  instances (`get_logger("zettelforge.*")`)
- Silent `except Exception: pass` blocks replaced with logged,
  re-raised, or explicitly handled exceptions
- Dependencies split: core vs `pip install zettelforge[extensions]`
- Extension features: TypeDB STIX ontology, OpenCTI integration,
  Sigma generation, multi-tenant auth
- Core includes full memory pipeline: blended retrieval, two-phase
  extraction, intent routing, causal triples, cross-encoder reranking

---

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
- ZettelForge web UI (FastAPI)
- MCP server for Claude Code integration
- OpenCTI continuous sync
- MemoryAgentBench (ICLR 2026) benchmark
- Configuration system with layered resolution (env > yaml > defaults)
- Documentation suite (Diataxis framework)

### Changed

- Knowledge graph backend: TypeDB-first with JSONL fallback
- Embedding provider: fastembed (in-process ONNX) replaces Ollama HTTP
- Bumped all benchmarks: CTI 75%, LOCOMO 18%, RAGAS 78.1%

---

## [1.5.0] - 2026-04-08

### Added

- GraphRetriever for multi-hop note discovery via knowledge graph
- BlendedRetriever combining vector + graph results with policy weights
- Rewritten `recall()` with blended vector + graph retrieval
- CTIBench (NeurIPS 2024) benchmark adapter
- RAGAS retrieval quality benchmark

---

## [1.4.0] - 2026-04-07

### Added

- FactExtractor (Phase 1): LLM-based salient fact extraction with importance scoring
- MemoryUpdater (Phase 2): ADD/UPDATE/DELETE/NOOP decision engine
- `remember_with_extraction()` two-phase pipeline

---

## [1.3.0] - 2026-04-07

### Added

- Sigma rule generation from IOCs
- Microsoft Sentinel rule conversion

---

## [1.2.0] - 2026-04-07

### Added

- CTI platform integration (Django CTI database connector)
- Proactive context injection for agent workflows

---

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
