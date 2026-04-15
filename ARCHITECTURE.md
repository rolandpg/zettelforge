# Architecture

## Storage Backends

ZettelForge uses a backend abstraction for the knowledge graph:

- **JSONL** (default): File-based, zero-config, works everywhere.
- **TypeDB** (via extension): STIX 2.1 ontology with inference rules.

Set `ZETTELFORGE_BACKEND` environment variable to select.

## Extension Points

Extensions are optional packages discovered at startup via
`src/zettelforge/extensions.py`. If installed, they provide
alternative backends and integrations.

### Knowledge Graph
- Default: JSONL (`src/zettelforge/knowledge_graph.py`)
- Extension: TypeDB STIX 2.1 (`zettelforge-enterprise`)

### Authentication
- Default: Single-tenant, no auth
- Extension: Multi-tenant OAuth/JWT (`zettelforge-enterprise`)

### Integrations
- OpenCTI sync: extension (requires running OpenCTI instance)
- Sigma generation: extension

## Why These Boundaries

TypeDB requires a running server. OpenCTI is a complex platform.
These dependencies should not be required to try ZettelForge.

The JSONL backends are not toy implementations — they are
production-capable for single-user and small-team deployments.
