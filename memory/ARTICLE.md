# Building an Agentic Memory System for AI Agents: The Roland Fleet Experience

*A practical implementation of A-MEM-inspired memory architecture for multi-agent systems*

**By Patrick Roland & Claude (Patton)**

*March 2026*

---

## Introduction

Every AI agent built today faces the same fundamental problem: memory is treated like a filing cabinet. You define the schema upfront, you decide when to store, you decide when to retrieve. The moment your agent encounters something it wasn't designed to organize, it breaks. The memory can't adapt. It can't reorganize itself. It can't discover relationships between things it already knows.

We built the Roland Fleet Agentic Memory System to solve this. This is the story of how a homelab implementation of a research paper became a production-ready memory architecture for autonomous agents.

---

## The Problem We Were Solving

Running a fleet of AI agents handling cybersecurity operations, threat intelligence, and strategic research, I needed memory that could:

1. **Self-organize** — The agent should decide how to structure and link memories, not the engineer
2. **Evolve** — When new information arrives, existing memories should be refined automatically
3. **Scale** — Token-efficient operations that don't choke local inference on M4 Mini and RTX 5090 hardware
4. **Recover** — Versioned history with rollback capability when evolution goes wrong
5. **Stay local** — No cloud dependencies for memory operations

The existing solutions either required cloud services with overhead we didn't need, or were research prototypes with no production path, or were personal knowledge tools being stretched beyond their intended use.

So we built our own.

---

## Core Inspiration: A-MEM

The foundational paper driving our architecture is **A-MEM** (Agentic Memory), from researchers exploring how to give AI agents dynamic memory self-organization inspired by the Zettelkasten method.

### What A-MEM Gets Right

**The Zettelkasten Insight**: Every note should be atomic (one idea per note), richly tagged, and linked to other notes by conceptual similarity rather than rigid hierarchy. The system learns to organize itself rather than being organized.

**Four Core Operations**:

1. **Note Construction**: When new information arrives, the LLM generates structured metadata — keywords, tags, context summary — not just dumps raw text into a vector store

2. **Link Generation**: After storing a new note, the system retrieves similar existing notes and uses the LLM to identify meaningful conceptual relationships (supports, contradicts, extends, causes) that pure vector similarity would miss

3. **Memory Evolution**: This is the key differentiator. When new information arrives, existing memories can be refined. The LLM evaluates whether an old memory's context summary or tags should be updated based on what the new information reveals. The knowledge base gets smarter over time without manual curation.

4. **Retrieval**: Query embedding + top-k similar notes + link expansion = both direct matches and contextually related information

**The Numbers That Matter**:
- 1,200-2,500 tokens per memory operation vs 16,900+ for context-stuffing approaches (85-93% reduction)
- 5.4 seconds on GPT-4o-mini, 1.1 seconds on Llama 3.2 1B for local models
- Near-constant retrieval time (3.7 microseconds) even at 1 million memories
- Doubles performance on multi-hop reasoning tasks

### Where A-MEM Falls Short

The paper acknowledges: quality depends on the underlying model, the system is text-only, and there's no rollback mechanism if evolution corrupts good memories. We addressed these gaps in our implementation.

---

## Other Systems We Drew From

### Cognee

Cognee implements a full **knowledge graph** approach with entities, relationships, and ontology grounding. Unlike simple vector retrieval, Cognee transforms raw documents into structured knowledge graphs where every inferred piece of information is linked back to its source document.

**What we borrowed**: The importance of source attribution and the distinction between raw content and derived semantic structure. Our note schema separates `content.raw` from `semantic.context` for exactly this reason.

**What we left behind**: Cognee's heavier ECL (Extract, Cognify, Load) pipeline adds latency on writes. For our use case with frequent subagent output ingestion, we needed faster write operations.

### Mem0

Mem0 is the most **commercially mature** memory system for AI agents — $24M in funding, AWS's exclusive memory provider for their new Agent SDK.

**What we borrowed**: Their hybrid store concept combining vector databases for semantic search, graph databases for relationships, and key-value stores for fast fact retrieval. Our architecture mirrors this with JSONL (structured facts) + LanceDB (vectors) + link graph.

**What we left behind**: Mem0's managed cloud offering doesn't fit our local-first requirements. For a homelab deployment, we needed something we could run without internet dependency.

### Obsidian

Obsidian is the gold standard for **personal knowledge management** using markdown and the Zettelkasten method. The philosophy A-MEM borrows from is exactly what Obsidian power users practice manually.

**What we borrowed**: The Zettelkasten philosophy itself — atomic notes, rich linking, emergence of structure through use rather than design. Our memory notes are fundamentally markdown-friendly JSONL for this reason.

**What we left behind**: Obsidian is a desktop app with an ecosystem of plugins. It's not infrastructure you hook an agent fleet into. We needed a programmable API, not a GUI.

---

## Our Architecture

We started this project with the intention of using Cognee for memory management. After weeks of fighting CUDA compatibility issues, Java dependency hell with their graph database backend, and the embedding model crashing during generation on the DGX Spark's ARM architecture, we stepped back and asked: what do we actually need?

The answer: memory that self-organizes, evolves, and stays efficient enough to run locally. We didn't need a full knowledge graph pipeline with all its complexity. We needed the core concepts implemented lean.

That's when we found A-MEM.

### Storage Topology

We run on an ASUS Ascent DGX Spark GB10 with a 1TB NVMe SSD and an 8TB USB 3.2 HDD.

```
HOT TIER (SSD)
├── notes.jsonl          Active memory notes
├── vectordb/           LanceDB vector indices
├── embeddings/         Embedding model cache
└── tmp/                Temporary processing

COLD TIER (HDD)
├── archive/            Evolved-out note versions
├── snapshots/          Daily memory exports
├── backups/weekly/     Full system backups
└── daily/             Operational logs
```

**Critical rule**: Vector database stays on SSD. USB 3.2 at 20 Gbps handles sequential throughput fine, but spinning disk random IOPS (80-160 IOPS) destroys vector search latency. SSD delivers 100K+ random IOPS. That 600x difference matters on every retrieval.

### Note Schema

Every memory note is a structured document with multiple representation layers:

```json
{
  "id": "note_20260320_143022_a7f3",
  "version": 3,
  "content": {
    "raw": "Original interaction content",
    "source_type": "conversation",
    "source_ref": "session_123"
  },
  "semantic": {
    "context": "LLM-generated one-sentence summary",
    "keywords": ["keyword1", "keyword2"],
    "tags": ["security_ops", "cti"],
    "entities": ["CVE-2024-1234"]
  },
  "embedding": {
    "model": "nomic-embed-text-v2-moe",
    "vector": [0.012, -0.034, ...],
    "dimensions": 768
  },
  "links": {
    "related": ["note_id_1", "note_id_2"],
    "causal_chain": []
  },
  "metadata": {
    "confidence": 0.87,
    "evolution_count": 2,
    "domain": "security_ops"
  }
}
```

**Version tracking** enables rollback. Every evolution archives the previous version to cold storage. If an evolution cycle produces garbage, you revert.

**Confidence scoring** starts at 1.0 for direct observations and decays for inferred or evolved content. Below 0.5, notes get flagged for human review rather than being served as fact.

**Evolution hop limit** of 5 prevents runaway drift. After five evolutions, a note is frozen and new notes capture further refinement.

### Software Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Vector DB | LanceDB | Embedded (no server process), ARM-native, file-based |
| Embedding | nomic-embed-text-v2-moe | 768-dim, strong benchmarks, runs locally |
| LLM (Memory Ops) | nemotron-3-nano | Fast enough for 2.7s note construction |
| LLM (Agent) | nemotron-3-super | Full reasoning when needed |
| Storage | JSONL + LanceDB | Human-readable + fast vector search |

### The Four Operations

**1. Note Construction**

Input → Content Extraction → LLM Semantic Enrichment (keywords, tags, context, entities) → Embedding Generation → Dual Write (JSONL + LanceDB)

The LLM generates structured metadata rather than just storing raw text. This enrichment step is what enables the sophisticated retrieval later.

**2. Link Generation**

New Note → Vector Retrieval (top-k candidates) → LLM Link Analysis → Bidirectional Linking

The LLM identifies relationships beyond pure vector similarity. "Topically related" vs "contradicts" vs "extends" — these semantic distinctions matter for retrieval quality.

**3. Memory Evolution**

New Note + Linked Notes → Evolution Assessment (LLM decides per-note) → Versioned Update → Confidence Decay → Cold Archive

This is where we extended A-MEM with production safeguards:
- Max 5 evolution hops prevents corruption drift
- Every version archived enables rollback
- Confidence decay reflects growing uncertainty with each evolution pass

**4. Retrieval**

Query → Embed → Vector Search → Link Expansion → Context Assembly → Agent Prompt

Link expansion is the key to multi-hop reasoning. Vector search finds direct matches, then linked notes surface contextually related information that wouldn't match the query text but is connected through the relationship graph.

---

## Agent Integration

We run a **single primary agent with ephemeral subagents** model rather than a persistent multi-agent fleet.

**Primary Agent (Patton)**: Owns memory exclusively. Handles construction, linking, evolution. Spawns subagents with scoped read-only context.

**Subagents**: Execute specific tasks. Return output + observations. Self-terminate. No direct memory access. Workspace wiped on completion.

This eliminates the hardest problem with multi-agent memory: cross-agent synchronization. The primary agent is the single source of truth. Subagents inherit read access for task duration, return results, and die.

---

## Performance

From load testing on our DGX Spark GB10:

| Metric | Value |
|--------|-------|
| Retrieval latency (avg) | 103-271ms |
| Retrieval latency (p95) | 130-1800ms |
| Note construction | 2,700ms (range 1.2-4.8s) |
| Evolution accuracy | 100% (3/3 test cases) |
| Storage per note | ~17 KB |

Token efficiency is the real win. A typical retrieval with 5 relevant notes, link expansion to 10 total, and formatted context comes in under 2,000 tokens. Compare that to dumping 16,900 tokens of conversation history into context.

---

## What We'd Do Differently

**Try Cognee first on x86 hardware**: If you're on standard x86_64 Linux without ARM compatibility concerns, give Cognee a proper evaluation. Their knowledge graph approach is more sophisticated than what we built. We ran into ARM-specific issues that may not affect you.

**Consider the simpler path from the start**: We spent weeks fighting Cognee before stepping back to build lean. If you know you need A-MEM-style lean memory rather than full knowledge graphs, start there. You'll save time.

**Watch for hardware**: The DGX Spark GB10 with its 128GB unified memory pool changes the equation for local inference. Running 70B+ models locally for memory operations becomes feasible. We're planning to move memory construction and linking to larger models when the hardware supports it.

---

## Conclusion

A-MEM gave us the theoretical foundation. Obsidian, Mem0, and our own Cognee frustrations gave us architectural patterns and hard-won lessons. Our implementation ties it together with production safeguards (versioning, rollback, confidence tracking) that the research prototype lacks.

The result is a memory system that:
- Self-organizes through LLM-driven linking and evolution
- Stays efficient enough for local inference on consumer hardware
- Recovers from corruption through versioned archival
- Scales from a few dozen notes to potential millions without architecture changes

We're not claiming this replaces Mem0 or Cognee for everyone. But for operators who need local-first, privacy-preserving memory for agent fleets, the A-MEM approach combined with solid production engineering gets you most of the way there.

The code is in our workspace. The architecture doc and runbook are there too. If you're building something similar, learn from what we got right and don't repeat our mistakes.

---

## References

1. **A-MEM: Agentic Memory for LLM-based Agents** — The foundational research on dynamic memory self-organization inspired by Zettelkasten
2. **Cognee** — Open-source knowledge graph engine with ECL pipeline (Extract, Cognify, Load)
3. **Mem0** — Production memory infrastructure for AI agents, $24M funding, AWS exclusive partner
4. **Obsidian** — Markdown-based personal knowledge management with Zettelkasten philosophy
5. **LanceDB** — Embedded vector database, ARM-native, file-based (no server process)
6. **nomic-embed-text** — Open-source embedding model, 768 dimensions, strong benchmarks
7. **MITRE ATT&CK** — Threat actor tactic taxonomy referenced in memory entity extraction
8. **Zettelkasten Method** — Niklas Luhmann's note-taking system: atomic, linked, emergent structure

---

*The Roland Fleet Agentic Memory System was built on the ASUS Ascent DGX Spark GB10. Architecture V1.1, March 2026.*
