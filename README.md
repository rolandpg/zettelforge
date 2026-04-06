# ZettelForge

**Proprietary Agentic Memory System for the Roland Fleet**

A production-grade, governed memory system designed specifically for CTI analysis, threat intelligence, and long-term agent reasoning.

## Purpose

ZettelForge is the primary memory architecture for the Roland Fleet. It provides:

- **Entity-aware memory** with automatic extraction of threat actors, CVEs, campaigns, and tools
- **Knowledge graph** with temporal reasoning and relationship mapping
- **Synthesis layer** capable of generating briefs, timelines, and relationship maps
- **Governance integration** — automatically validates operations against our internal standards
- **High performance** with optimized LanceDB indexing, caching, and resilience patterns

## Key Features

- **Zettelkasten-inspired** atomic notes with rich metadata
- **Alias resolution** (Fancy Bear → APT28, etc.)
- **Epistemic tiers** (confidence levels)
- **Domain-aware** storage and retrieval (CTI, operations, research, etc.)
- **Full governance compliance** (GOV-003, GOV-007, GOV-011, GOV-012)

## Status

**Proprietary** — All rights reserved. Commercial use, redistribution, or derivative works are prohibited without explicit written permission from Patrick Roland / Roland Fleet.

This system is for internal use only.

## Architecture Overview

ZettelForge uses a layered architecture:

- **Core**: LanceDB vector store with IVF_PQ indexing
- **Entity Layer**: Automatic extraction of actors, CVEs, tools, campaigns
- **Ontology Layer**: Typed knowledge graph with governance rules
- **Synthesis Layer**: Generates briefs, timelines, and relationship maps
- **Governance Layer**: Automatic validation against GOV-003, GOV-007, GOV-011, GOV-012

See `research/system-architecture.mmd` for visual diagrams and `research/zettelforge-lancedb-optimization-plan-20260406.md` for technical details.

## Installation

```bash
cd ~/.openclaw/workspace/skills/zettelforge
pip install -e .
```

Or use directly:

```bash
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
```

## Usage

```python
from zettelforge import MemoryManager

mm = MemoryManager()

# Store information
mm.remember("APT28 used malware X in campaign Y", domain="cti")

# Retrieve with synthesis
results = mm.recall("What malware does APT28 use?", k=10)

# Get synthesized answer
answer = mm.synthesize("Summarize APT28 activity in 2026", format="synthesized_brief")
```

## License

See `LICENSE` file.

---

**© 2026 Patrick Roland. All Rights Reserved.**
**Proprietary - Internal Use Only**
```

Now, create a strong proprietary license.