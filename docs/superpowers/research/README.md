# Research notes

These documents are **aspirational research synthesis**, not an executable
roadmap. They were produced during deep-dive sessions over Tamara / Nexus
corpora and Codex research agents, and capture the direction a feature
*could* take — not what is committed to ship.

If you are looking for the roadmap of what has actually landed, see:

- [CHANGELOG.md](../../../CHANGELOG.md) — shipped per release
- [docs/rfcs/](../../rfcs/) — formal design records (Draft → Accepted → Implemented)
- `TODO.md` at the repo root — active backlog (gitignored)

Files in this directory:

| File | Topic | Relationship to shipped code |
|------|-------|------------------------------|
| `2026-04-09-ctibench-ragas-benchmarks.md` | Benchmark methodology | Shipped in v2.0.0, refined through v2.2.0 |
| `2026-04-09-fastembed-local-embeddings.md` | fastembed ONNX embeddings | Shipped in v2.0.0 (now default) |
| `2026-04-09-hybrid-typedb-lancedb-architecture.md` | TypeDB + LanceDB hybrid | Partial — TypeDB moved to enterprise extension in v2.2.0 |
| `2026-04-09-local-llm-llama-cpp.md` | llama-cpp-python default | Shipped in v2.0.0 |
| `2026-04-15-anti-aversion-cleanup.md` | Community-first repo clean-up | Shipped in v2.2.0 |
| `2026-04-15-causal-graph.md` | Causal triple + intent-routed retrieval | Partially shipped in v2.2.0 (causal fix); System 1/2 routing is future work |
| `2026-04-15-ctibench-ate-fix.md` | CTIBench ATE ingestion fix | Shipped in v2.2.0 (F1 = 0 → 0.146) |
| `2026-04-15-format-stability.md` | JSON output stability | Aspirational |
| `2026-04-15-memory-evolution.md` | Governed evolve / buffer / ignore / keep | Partial — ADD/UPDATE/DELETE/NOOP shipped, governed evolution still aspirational |
| `2026-04-15-merge-consolidation.md` | Semantic merge of overlapping notes | Aspirational |
| `2026-04-15-persistence-semantics.md` | Expanded CTI lifecycle tiers | Partial — 4-tier system shipped, 8-field expansion aspirational |
| `2026-04-15-sqlite-migration.md` | JSONL → SQLite | Shipped in v2.2.0 |

These are preserved for provenance. Do not rely on any of them as a
commitment that work will land.
