---
title: "Ingest a Long Threat Report"
description: "Use remember_report() to ingest multi-page threat reports with automatic chunking, fact extraction, and deduplication."
diataxis_type: "how-to"
audience: "CTI analysts processing vendor reports, security teams building automated ingestion pipelines"
tags: [remember-report, chunking, ingestion, report, cti, extraction]
last_updated: "2026-04-09"
version: "2.0.0"
---

# Ingest a Long Threat Report

Ingest threat reports of any length using `remember_report()`. ZettelForge chunks content on sentence boundaries, runs the two-phase extraction pipeline on each chunk, deduplicates against existing notes, and stores published-date metadata for temporal queries.

## Prerequisites

- ZettelForge installed (`pip install zettelforge`)
- Ollama running with `qwen2.5:3b` (extraction) and `nomic-embed-text-v2-moe:latest` (embeddings)

## Steps

### 1. Prepare the report content

```python
report_content = """
Volt Typhoon Campaign Analysis - March 2026

Executive Summary: Volt Typhoon (Bronze Silhouette) continued targeting
U.S. critical infrastructure in Q1 2026, focusing on water treatment
facilities and energy grid operators in the Pacific Northwest.

Initial access leveraged living-off-the-land binaries (LOLBins) and
compromised SOHO routers as operational relay nodes. No custom malware
was deployed; the group relied exclusively on built-in Windows tools
including PowerShell, certutil, and netsh for lateral movement.

The campaign exploited CVE-2024-3094 in xz-utils on exposed Linux
jump hosts to establish footholds in hybrid environments. CISA issued
advisory AA26-091A on March 15, 2026.

Attribution confidence: HIGH (NSA/CISA joint assessment).
Linked infrastructure overlaps with previous Volt Typhoon campaigns
tracked since May 2023.
"""
```

### 2. Ingest with `remember_report()`

```python
from zettelforge.memory_manager import MemoryManager

mm = MemoryManager()

results = mm.remember_report(
    content=report_content,
    source_url="https://example.com/volt-typhoon-q1-2026",
    published_date="2026-03-20",
    domain="cti",
    chunk_size=3000
)

print(f"Total facts processed: {len(results)}")
for note, status in results:
    if note:
        print(f"  [{status}] {note.id}: {note.content.raw[:80]}...")
```

> [!NOTE]
> `chunk_size=3000` (default) splits content on sentence boundaries so no sentence is cut mid-word. Each chunk runs independently through the extraction pipeline.

### 3. Inspect extraction results

```python
added = [(n, s) for n, s in results if s == "added"]
updated = [(n, s) for n, s in results if s == "updated"]
noops = [(n, s) for n, s in results if s == "noop"]

print(f"Added: {len(added)}, Updated: {len(updated)}, No-op: {len(noops)}")
```

Status values:

| Status | Meaning |
|--------|---------|
| `added` | New fact stored as a new note |
| `updated` | Existing note updated with new information |
| `corrected` | Existing note corrected (factual conflict resolved) |
| `noop` | Fact already exists, no action taken |

### 4. Verify entities were extracted and graphed

```python
relationships = mm.get_entity_relationships("actor", "volt typhoon")

for rel in relationships:
    print(f"  {rel['relationship']}: {rel['to_type']}:{rel['to_value']}")
```

### 5. Query the ingested report data

```python
# Semantic query
notes = mm.recall(
    "What infrastructure does Volt Typhoon target?",
    domain="cti",
    k=5
)

for note in notes:
    print(f"  {note.content.raw[:120]}")
```

```python
# Synthesized answer
result = mm.synthesize(
    "Summarize Volt Typhoon activity in Q1 2026",
    format="synthesized_brief",
    k=10
)

print(result["synthesis"]["summary"])
```

### 6. Adjust extraction sensitivity

For dense reports with many facts:

```python
results = mm.remember_report(
    content=report_content,
    source_url="https://example.com/report",
    published_date="2026-03-20",
    domain="cti",
    min_importance=2,   # Lower threshold, keep more facts
    max_facts=10,       # More facts per chunk
    chunk_size=2000     # Smaller chunks for granularity
)
```

> [!TIP]
> For short reports (<3000 chars), `remember_report()` skips chunking and processes the content as a single block.

> [!WARNING]
> Each chunk makes LLM calls for extraction and update decisions. A 15,000-character report with `chunk_size=3000` produces 5 chunks, each with up to `max_facts` LLM calls. Budget ~2 seconds per fact on local Ollama with `qwen2.5:3b`.

## LLM Quick Reference

**Task**: Ingest long-form threat reports with chunking, extraction, and deduplication.

**Primary method**: `mm.remember_report(content, source_url="...", published_date="2026-03-20", domain="cti", chunk_size=3000)` returns `List[Tuple[Optional[MemoryNote], str]]`.

**Chunking**: Content exceeding `chunk_size` is split on sentence boundaries (`. ` delimiter). Each chunk runs independently through the two-phase extraction pipeline (`remember_with_extraction()`).

**Two-phase pipeline per chunk**: Phase 1 (LLM extraction) distills salient facts scored by importance. Phase 2 (LLM update decision) compares each fact to existing notes and returns ADD/UPDATE/DELETE/NOOP.

**Parameters**: `min_importance` (default 3, range 1-10) filters low-value facts. `max_facts` (default 10) caps extracted facts per chunk. `chunk_size` (default 3000) controls split granularity.

**Temporal metadata**: `published_date` (ISO 8601 string) is passed as context to the extraction LLM and stored in note metadata for temporal queries.

**Status values**: "added" (new note), "updated" (existing note merged), "corrected" (conflict resolved), "noop" (duplicate skipped).

**Source tracking**: `source_url` is stored as `source_ref` with `:chunk:N` suffix per chunk for provenance tracing.
