# Memory System — OPUS Research Notes
**Date:** 2026-03-31
**Source:** OPUS (Claude Code agent) via Patrick

## Landscape Validation

All 5 phases are genuinely on the frontier. Available memory plugins (memsearch, Mem0, Redis Agent Memory, Cognee) are all semantic-search-first. Our entity-first deterministic retrieval with typed recalls (recall_cve, recall_actor) is architecturally different and stronger for cybersecurity.

Key sources:
- A-MEM paper (Zettelkasten-inspired linking/evolution)
- Zep/Graphiti (temporal awareness, scored 94.8% on Deep Memory Retrieval)
- Cognee (6-stage pipeline: classify → extract → embed → graph)
- Neo4j team findings on entity extraction
- iDmem (epistemic tiers)

## Critical Gaps Identified

### Gap 1: Actor Alias Resolution (HIGH PRIORITY)
MuddyWater = Mercury = TEMP.Zagros. Our CVE dedup works (exact string match) but actor aliasing creates phantom duplicates that bypass entity_index entirely.

Current named lists (50 actors, 30 tools) are static and will drift.

**Recommendation:** Make entity lists self-updating from note content. Add alias mapping table. Do this before scaling past ~100 notes.

### Gap 2: Epistemic Tiering (HIGH PRIORITY)
Current evolution cycle (NO_CHANGE / UPDATE_CONTEXT / UPDATE_TAGS / UPDATE_BOTH / SUPERSEDE) doesn't distinguish between:
- **Tier A** — Human direct facts, tool-observed state (authoritative, can supersede)
- **Tier B** — Agent direct reports (add context, cannot override Tier A)
- **Tier C** — Summaries, interpretations, hypotheses (support-only)

Without this: agent summarizes something → re-ingests → paraphrase becomes org truth. Circular reinforcement.

**Recommendation:** Add epistemic tier to note metadata. Evolution rules respect tier priority.

### Gap 3: Cold Archive Deferral Risk
All systems that shipped without forgetting had to retrofit under pressure.

Phase 5 already implemented (confidence < 0.3, access_count == 0 for > 30 days → archive). Must not defer further.

### Gap 4: Reasoning Memory (FUTURE)
Systems cover short-term (conversations) and long-term (entities). Missing: **reasoning memory** — how the agent thought through a problem.

Without it: can't explain decisions, can't learn from errors, can't debug unexpected behavior.

**Recommendation:** Phase 6 candidate. Record: why a link was made, what hypothesis triggered an evolution, which recall results were acted on.

### Gap 5: Self-Updating Entity Lists
Current actor/tool lists are hand-maintained. Should extract from note content and auto-update.

**Recommendation:** Entity indexer updates named lists when it encounters new actors/tools that meet confidence threshold.

## Priority Ranking for Next Project

1. **Actor Alias Resolution** — before graph gets large enough for circular dupes to become invisible
2. **Epistemic Tiering** — before agent-generated inferences start overriding operator facts
3. **Phase 6: Reasoning Memory** — capture the "why" behind linking decisions

## What We Did Right

- Entity-first deterministic extraction for structured cybersecurity domain
- JSONL-on-disk (not context-window memory) — sidesteps compaction risk entirely
- Separate entity_index.json from note JSONL — allows typed recalls without embedding search
- Phases 1-2 complete before advancing — good gate discipline
