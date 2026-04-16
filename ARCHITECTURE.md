# Architecture

Visual diagram: [`docs/architecture-diagram.mmd`](docs/architecture-diagram.mmd)
Deep explanation: [`docs/explanation/architecture.md`](docs/explanation/architecture.md)

## Storage

ZettelForge uses a `StorageBackend` ABC (33 methods) with pluggable
implementations. Set `ZETTELFORGE_BACKEND` to select.

- **SQLite** (default since v2.2.0): WAL mode, ACID, zero-config.
  Notes, knowledge graph, and entity index in one database file.
- **LanceDB**: Vector index alongside SQLite. 768-dim embeddings
  via fastembed (nomic-embed-text-v1.5-Q, ONNX, in-process).

## Core Pipeline

1. **Ingestion** — Governance validation → Note construction → Entity
   extraction (regex fast-path + LLM) → Alias resolution → Storage
2. **Enrichment** (background) — Causal triple extraction, memory
   evolution (A-Mem neighbor refinement), HGAM consolidation
3. **Retrieval** — Intent classification → Blended vector + graph
   search → Temporal/causal boosting → Cross-encoder reranking
4. **Synthesis** — RAG-as-Answer with quality validation

## Extension Points

Extensions are optional packages discovered at startup via
`src/zettelforge/extensions.py`. If installed, they provide
alternative backends and integrations.

- Knowledge graph: TypeDB STIX 2.1 ontology with inference rules
- Authentication: Multi-tenant OAuth/JWT
- Integrations: OpenCTI bi-directional sync, Sigma rule generation

## Why These Boundaries

TypeDB requires a running server. OpenCTI is a complex platform.
These dependencies should not be required to try ZettelForge.

The default backends are not toy implementations — they are
production-capable for single-user and small-team deployments.
