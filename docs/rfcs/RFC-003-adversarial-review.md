# RFC-003 Adversarial Review

**Reviewer**: Senior AI Engineering (adversarial pass)
**Date**: 2026-04-16
**Target**: `docs/rfcs/RFC-003-read-path-depth-routing.md`
**Code under review**: `memory_manager.py`, `intent_classifier.py`, `blended_retriever.py`, `consolidation.py`

---

## Verdict: REQUEST CHANGES

The design is sound in spirit and the phased rollout is defensive, but the RFC contains **multiple blockers that will cause the motivating example to be misrouted**, understates the delta between System 1 and the current `recall()`, and relies on storage primitives and extraction modes that are either unspecified or incompatible with the claimed latency budget. Fix the blockers, clarify the ambiguities in Warnings 9–20, and this is a solid APPROVE.

## Summary

RFC-003 proposes a deterministic Quality Gate that routes queries to System 1 (current blended pipeline) or System 2 (new exhaustive-scan + temporal chunking). The Gate is cleanly specified as additive, bounded scoring over cheap features. Rollback posture is excellent (one-line config flip). However:

1. **The gate's weight table misroutes the RFC's own motivating query to System 1.** The `Which threat actor used CVE-2024-3400 in campaigns targeting healthcare between Q3 2024 and Q1 2025?` example scores 0.40 under the proposed weights — below the 0.70 threshold.
2. **System 1 is NOT a verbatim lift.** Reading `profile.*` instead of re-calling classifier/extractor is semantic parity, fine. But `meta["top_vector_score"]` is required by the upgrade path and does not exist anywhere in the current `VectorRetriever` return shape. That is an unreported API change.
3. **System 2's latency budget (p95 ≤ 800ms) is incompatible with LLM NER.** Current `recall()` calls `extract_all(query)` with the default `use_llm=True`. If CandidateFilter runs `extract_all` across 200–500 candidate notes, that is an LLM-call-per-note cost well above budget. The RFC never pins `use_llm=False` for System 2.
4. **Two of three "thin SQLite wrappers" require indexes that are not stated to exist.** `iterate_notes_in_range(start, end)` assumes an index on `created_at`; `get_entity_degree` assumes an incidence index. Phase 2 will regress if these indexes are missing and a full scan substitutes.

---

## Blockers

### B1. Motivating example is misrouted to System 1 under the proposed weights

The RFC cites this as its motivating query (RFC line 32):

> *"which threat actor used CVE-2024-3400 in campaigns that targeted healthcare between Q3 2024 and Q1 2025?"*

Score trace under the RFC's own rules:

- `intent_classifier.py` matches `"which actor"` (RELATIONAL) and `"between"` (RELATIONAL) — best_score ≥ 2 → **RELATIONAL, confidence 0.5**. `is_ambiguous=False`.
- Intent prior: `RELATIONAL = +0.20`.
- Multi-hop pattern `\bused by .+ (?:to|in|for|against)\b` — query contains `"used CVE"` not `"used by"`. **No match.**
- Temporal span `\b(?:q[1-4]|quarter) \d{4}\b.+\b(?:q[1-4]|quarter) \d{4}\b` — matches `"Q3 2024 ... Q1 2025"`. **+0.20.**
- Causal chain: no match. **0.**
- Aggregation: no match. **0.**
- Comparison: no match. **0.**
- Entity density: CVE-2024-3400 = 1; `"healthcare"` is not an extracted asset in the current entity extractor. entity_count ≤ 2, **no bonus**.

**Total: 0.40. System 1.** The gate sends the exact query class the RFC exists to fix to the exact path it already fails on.

**Fix options** (pick one and document):

- Add a multi-hop pattern for `\bused .+ (?:in|against|to target) .+`.
- Raise RELATIONAL intent prior from 0.20 → 0.30.
- Fire multi-hop when `entity_type_count ≥ 2` regardless of regex markers.
- Lower `system2_threshold` default to 0.5 (but quantify the System 2 rate increase — 0.5 may push well past the "3% of queries" target).

Without a change, Phase 4 validation ("CTI accuracy ≥ 75%, LOCOMO materially improves") is at serious risk of failing on exactly the example the RFC promises to fix.

### B2. `meta["top_vector_score"]` does not exist in the current pipeline

The upgrade path (RFC line 610–617) reads `meta.get("top_vector_score")`. The current `VectorRetriever.retrieve()` returns `List[MemoryNote]` — scalar scores are not exposed. The current `recall()` body (`memory_manager.py:470`) captures nothing of the sort.

To deliver this, `VectorRetriever.retrieve()` must be extended to return either scored tuples or a metadata dict. That is **not a verbatim lift**. The RFC presents it as a no-op change ("System 1 is the current recall() body, unmodified") but Phase 2 cannot deliver without patching `VectorRetriever`. At minimum, the RFC must:

1. Acknowledge the `VectorRetriever` signature or return-shape change.
2. Add a parity test that confirms the scored-tuple version produces identical ordering when scores are stripped.
3. Note the API compatibility implications for other callers of `retriever.retrieve()` (there is at least one in `get_context()` at `memory_manager.py:670`).

### B3. System 2 candidate filter will bust the 800ms budget if LLM NER is used

Current `recall()` at `memory_manager.py:464`:

```python
query_entities = self.indexer.extractor.extract_all(query)
```

No `use_llm=False`, so this uses the default — and per `remember()` at line 231 the explicit-regex-only path sets `use_llm=False`. This asymmetry means **recall path uses LLM NER, write path does not**. The RFC's ChunkScorer comments state:

> "entity extractor is run once per candidate note during filter (cached on `QueryProfile._entity_cache`). No re-extraction during scoring."

If each candidate note (200–500) runs `extract_all(note.content.raw)` with `use_llm=True` — at, say, 50–200ms per LLM NER call on Qwen2.5-3B — that is 10–100 seconds. Budget blown by 10–100×.

**Required clarifications:**

1. Pin explicit `use_llm=False` for all per-candidate extraction in System 2, OR
2. Reuse the entity index (`store.get_note_ids_for_entity`) as the coverage source — do not re-extract at all; trust the indexed entities written during `remember()`. (This is probably the correct answer — the indexer already stored resolved entities at write time.)
3. Document which path and add a bench assertion: System 2 p95 ≤ 800ms with 300 candidates.

Also: the RFC says entities are cached on `QueryProfile._entity_cache`, but the `QueryProfile` dataclass in §QueryProfile has no such field. Either add it or drop the claim.

### B4. Two storage primitives assume indexes that are not stated to exist

RFC lines 775–784:

> *"All three are thin SQLite queries on existing indexes. No schema migrations required."*

- `iterate_notes_in_range(start, end)` — requires a SQLite index on `notes.created_at`. Nothing in the read code confirms this index exists. If absent, Phase 2 introduces a silent O(N) scan and the temporal-window path latency becomes unbounded.
- `get_entity_degree(etype, evalue)` — requires an efficient incidence count on the KG edge table. Achievable via `COUNT(*)` on an indexed `(from_type, from_value)` + `(to_type, to_value)`, but not guaranteed by this RFC.

**Fix:** Add an "Indexes required / added" subsection. If new indexes are needed, that is a schema migration and belongs in Phase 2 with a migration test, not in the "no schema migrations required" bucket.

### B5. Signal 9 shortcut is one-way and bypasses the upgrade path

```python
if (profile.intent == QueryIntent.FACTUAL
    and profile.entity_count <= 1
    and not profile.has_multi_hop_markers
    and not profile.has_aggregation_markers):
    return GateDecision(Depth.SYSTEM_1, 0.0, [...], upgrade_eligible=False)
```

Setting `upgrade_eligible=False` means a FACTUAL single-entity query that returns **zero results** or very weak results cannot be rescued by the upgrade path. This is the most common failure mode for genuine questions with novel entities (e.g., a freshly-minted CVE not yet well-indexed).

**Fix:** Either (a) allow upgrade after zero/weak results even on the shortcut path (`upgrade_eligible=True` when `system1_result_count == 0`), or (b) document the intentional tradeoff and log a distinct diagnostic when the shortcut returns empty so operators can observe the cost.

---

## Warnings

### W1. UNKNOWN intent is dead code in the gate

The gate's intent_prior table assigns `QueryIntent.UNKNOWN: 0.25`. But `intent_classifier.py` **has no code path that returns UNKNOWN** — the keyword fallback emits EXPLORATORY, the LLM fallback emits EXPLORATORY. UNKNOWN is declared but never produced. Remove the entry, or wire UNKNOWN into the classifier's real fallback.

### W2. `is_ambiguous` threshold hardcoded, collides with `system1_confidence_floor`

`QueryProfile.is_ambiguous` uses `intent_confidence < 0.4` (hardcoded). `system1_confidence_floor=0.4` is config-exposed and uses the same number. Either (a) unify these into one config key, or (b) document why the two `0.4`s are semantically independent. As written, operators will tune one and not the other and get subtle routing shifts.

### W3. `upgrade_eligible ... score >= 0.4` — another magic 0.4

Three different `0.4` thresholds in gate logic, none cross-referenced. Promote to a named constant or config.

### W4. Candidate budget cap is non-deterministic when paths overlap

§CandidateFilter picks "keep most recent" when `len(candidates) > max_candidates`. With 3 query entities → up to 3×50=150 from entity-index, up to 3×100=300 from 1-hop neighbors, always 200 from vector fallback = up to 650 pre-dedup. Dedup by id, cap at 500 by recency.

Problem: **entity-index matches (highest precision) get discarded in favor of recency-sorted neighbors/vector hits.** For CTI campaigns spanning 2+ years, the cap policy actively harms the multi-hop path.

**Fix:** Give explicit priority — entity-index > 1-hop > vector fallback > temporal-window — and cap per-source before the union. Or score candidates before capping.

### W5. Superseded/expired filtering is missing from System 2 candidate filter

System 1 filters superseded and expired notes after the pipeline (`memory_manager.py:581–591`). System 2's CandidateFilter returns raw candidates. Running chunk-scoring on notes that get dropped at the end wastes budget and risks top-M chunks dominated by superseded content. Add the filter to CandidateFilter, or document why post-filter is preferable.

### W6. `_extract_time_window()` is referenced but never defined

RFC line 484 calls `self._extract_time_window(profile.query)` to extract a date range for temporal candidate expansion. The function is nowhere in the RFC. Parsing natural-language ranges (`"between Q3 2024 and Q1 2025"`, `"last 6 months"`, `"since the MOVEit incident"`) is non-trivial. The RFC needs at least a sketch: dateparser? custom regex? timezone? behavior on unparseable spans?

### W7. Centrality sub-score risks dominating chunks with generic high-degree nouns

Degree centrality is O(1) but high-degree entities in CTI are exactly the low-information ones (`Windows`, `PowerShell`, `Mimikatz`). A chunk that scores high on centrality is likely a chunk about nothing in particular. Open Question 3 acknowledges this but defers. At minimum, subtract a "popularity penalty" or use inverse-degree weighting as a baseline so Phase 3 does not ship an observably broken default.

### W8. Comparison pattern requires trailing preposition that natural queries often omit

`_COMPARISON_PATTERNS = [r"\bcompare (?:to|with|between)\b", ...]`

Real queries: `"compare APT28 and APT29 tactics"`, `"compare ransomware families"`. Neither has `"compare to|with|between"`. The comparison marker will miss almost every comparison query. Either loosen the pattern, or accept that comparison detection is low-recall and rely on entity_count ≥ 2 as a proxy (which currently only adds 0.10 and requires ≥ 3 entities, not 2).

### W9. Aggregation query, just below threshold → System 1

See Misrouted Example M3. The clearest aggregation example misses System 2 by 0.05. Raise aggregation weight to 0.35, or lower default threshold to 0.65.

### W10. Multi-hop markers under-recall on natural paraphrase

Patterns require exact connectives: `"and then"`, `"used by X to"`, `"attributed to X via"`. Typical analyst phrasing:

- `"APT28 leveraged CVE-X on healthcare targets"` — no marker.
- `"the group behind the breach used CVE-X"` — no marker.
- `"Mustang Panda ran PlugX against Taiwan"` — no marker.

All multi-hop queries, all route to System 1 because regexes are prescriptive rather than semantic. Consider a **structural** multi-hop signal: `entity_type_count ≥ 2 AND intent in {RELATIONAL, CAUSAL}` contributes +0.15.

### W11. Upgrade-rate auto-tuning is under-specified

> *"Config caps the upgrade with `max_upgrade_rate` — if > X% of queries upgrade in a rolling window, raise the gate threshold automatically."*

Open:

- Where is the rolling window stored? In-process? Shared across processes?
- Concurrency — is the window state locked across threads?
- What is the step size for raising the threshold? How does it fall back down?
- If threshold creeps 0.7 → 0.85 due to a workload burst, does it ever return to 0.7?

This needs a state machine or it is a bug farm. Alternative: drop the auto-tune and only emit a warning log + metric when upgrade rate exceeds the cap. Let operators tune manually.

### W12. Concurrency and stateful singletons

`get_quality_gate()` is described as a singleton. If it holds the upgrade-rate window, it is mutable shared state and needs a lock. If it does not, the auto-tune mechanism has no natural home. The RFC should pick one and state the concurrency model.

### W13. LOCOMO p95 post-routing is not committed to a number

The motivation sets up LOCOMO p95 at 2282ms as a problem. System 2 budget is 800ms. The RFC does **not** state expected LOCOMO p95 post-routing. Worst case for upgraded queries is `System1 + System2 ≈ 1000ms+`. If 15% of LOCOMO queries upgrade, p95 could still be dominated by the upgrade path. Add a concrete Phase 4 target: *"LOCOMO p95 ≤ 900ms with routing enabled, ≥ 90% of queries routed correctly on first pass."*

### W14. Enterprise extension boundary is ignored

`memory_manager.py:1143` caps `traverse_graph` depth at 2 without the `enterprise` extension. System 2's ChunkScorer uses `store.get_causal_edges(... max_depth=3 ...)`. Does System 2 require the enterprise extension? If so, state it. If not, confirm non-enterprise compatibility.

### W15. Alias resolution is inconsistent between write and chunk-scoring paths

`remember()` resolves entities via `AliasResolver` before indexing (`memory_manager.py:234–237`). The RFC's ChunkScorer coverage/density must compare **resolved** entity sets. But `indexer.extractor.extract_all()` returns raw entities. Either resolve in ChunkScorer, or document that coverage uses raw-match and accept that `APT28` vs `FANCY BEAR` will not match across notes.

### W16. Open Question 4's proposed LLM-intent adjustment has the wrong rationale

Open Question 4: *"when intent_method == "llm", bias toward System 1 by subtracting 0.10 ... already reflected in is_ambiguous."*

But `is_ambiguous` is `intent_confidence < 0.4`. LLM fallback returns confidence 0.8 on success → `is_ambiguous=False`. So the LLM path actually **loses** the ambiguity signal, it does not preserve it. Subtracting 0.10 for LLM intent is defensible, but the stated reason is wrong. Consider: if LLM fallback fired, the keyword scorer could not decide — evidence of complexity. Arguably LLM-fallback should **raise** the score.

### W17. Phase 2 parity test needs to check ordering, not just membership

> *"test_system1_parity.py replays the CTI benchmark queries and asserts output equality with git HEAD before Phase 2."*

Equality of what — set of IDs? Order? Only order matters for cross-encoder-reranked result lists. Specify: `assert [n.id for n in before] == [n.id for n in after]`.

### W18. Logging payload may break the OCSF emitter

`log_api_activity(..., gate_reasons=decision.reasons)` passes a `list[str]`. OCSF activity logging traditionally serializes flat fields. Check whether `log_api_activity` accepts list values or coerces them. If it JSON-stringifies, fine — but pin the expected serialization so downstream dashboard parsers do not silently break.

### W19. Phase 5 default flip lacks an exit criterion

*"After two weeks of telemetry..."* is a schedule, not a criterion. Specify: *"flip when System 2 rate ∈ [2%, 8%], upgrade rate < max_upgrade_rate, CTI accuracy ≥ 75%, LOCOMO accuracy improved by ≥ 5 points vs. pre-routing baseline."*

### W20. No rollback test

Migration covers forward compatibility. There is no test for: enable routing → observe production issue → flip `enabled: false` → assert zero residual state, zero new files, zero queries stuck in System 2. Standard kill-switch requirement.

---

## Nits

### N1. `\bvs\.?\b` fails on `"APT28 vs."` at end-of-string

`\b` after `\.?` will not match at end-of-string when the preceding char is `.`. Real queries like `"APT28 vs. APT29."` may or may not trigger depending on punctuation. Minor; the comparison path is brittle anyway (W8).

### N2. `_choose_bucket_size` cases do not cover explicit `chunk_size` config

Config has `chunk_size: "auto" | "hourly" | "daily" | "weekly"`. `TemporalChunker._choose_bucket_size` is described as auto-selecting based on temporal markers. What if config says `"hourly"` explicitly? Is config honored or overridden? Unclear.

### N3. Per-signal `reasons` strings use inconsistent formatting

`"intent:causal(+0.35)"` vs `"ambiguous_intent(+0.15)"` vs `"entity_count:3(+0.10)"`. Pick one convention.

### N4. `QueryProfile.build()` dependencies vs. `System1Retriever(memory_manager)`

Prose: `QueryProfile.build(query, intent_classifier, entity_extractor, alias_resolver)`. But `System1Retriever` takes `memory_manager`. Transitively fine, but document: System1Retriever is not stateless; it reuses mm's `retriever`, `store`, `indexer`, and reranker singleton.

### N5. CTI keyword sets in markers hardcode domain assumptions

For `domain="general"` or `domain="conversational"`, the CTI-flavored markers (`"targeted"`, `"compromised"`, `"campaign"`, `"APT"`) will almost never fire. Non-CTI users effectively get System 1 for everything, making the gate a no-op for them. State this explicitly in Motivation so non-CTI operators set expectations correctly.

### N6. `get_quality_gate()` is proposed but not shown

Mentioned in the modified `recall()` body, never defined in any §. Minor.

---

## Misrouted Query Examples

Traced under the exact rules in §QualityGate. Threshold = 0.70.

### M1. The RFC's own motivating example → System 1 (should be System 2)

Query: `"which threat actor used CVE-2024-3400 in campaigns that targeted healthcare between Q3 2024 and Q1 2025?"`

- Intent: RELATIONAL (`"which actor"`, `"between"` both match). confidence=0.5, not ambiguous.
- `intent_prior(RELATIONAL) = +0.20`
- `temporal_span` on `"Q3 2024 ... Q1 2025"` = +0.20
- `multi_hop` does NOT fire (query has `"used ... in"`, pattern requires `"used by ... to|in|for|against"`)
- Causal / aggregation / comparison: none
- entity_count / entity_type_count bonuses: none (too few)

**Total: 0.40. Routes to System 1.** See Blocker B1.

### M2. Comparison query → System 1 (should be System 2)

Query: `"compare APT28 and APT29 tactics"`

- Intent: no keyword match → EXPLORATORY default, confidence 0.3, ambiguous.
- `intent_prior(EXPLORATORY) = +0.20`
- `ambiguous_intent = +0.15`
- `comparison` does NOT fire (regex requires `"compare to|with|between"`; query has only `"compare"`).
- entity_count = 2 → no bonus (requires ≥ 3).
- entity_type_count = 1 → no bonus.

**Total: 0.35. Routes to System 1.**

Fix: loosen comparison regex, or bonus `entity_count==2 AND entity_type_count==1` (same-type comparison).

### M3. Aggregation query → System 1 (should be System 2)

Query: `"show me every instance of PowerShell abuse this quarter"`

- Intent: EXPLORATORY default (no keyword match), confidence 0.3, ambiguous.
- `intent_prior(EXPLORATORY) = +0.20`
- `ambiguous = +0.15`
- `aggregation` fires on `"every instance"` = +0.30
- `temporal_span` on `"this quarter"` — not in patterns. NO match.
- No other signals.

**Total: 0.65 < 0.70. Routes to System 1.**

Off by 0.05. Raise aggregation weight to 0.35 or lower threshold to 0.65.

### M4. Root-cause query → System 1 (borderline; should be System 2)

Query: `"what's the root cause of the MOVEit incident and what actor was responsible?"`

- `"what is"/"what was"` do not match `"what's"` (contraction).
- No other intent keywords → EXPLORATORY default, confidence 0.3, ambiguous.
- `intent_prior = +0.20`
- `ambiguous = +0.15`
- `causal_chain` on `"root cause"` = +0.25
- No aggregation, no temporal span, no multi-hop pattern match.
- entity_count likely 0–1 (MOVEit may or may not be extracted).

**Total: 0.60. Routes to System 1.**

Classic multi-hop causal attribution — misrouted.

### M5. Paraphrased multi-hop → System 1 (should be System 2)

Query: `"Mustang Panda ran PlugX against Taiwanese government targets last year"`

- No intent keyword match → EXPLORATORY default, confidence 0.3, ambiguous.
- `intent_prior = +0.20`
- `ambiguous = +0.15`
- `multi_hop` does NOT fire (no `"used by"`, no `"attributed to"`, no `"then"`). Semantically multi-hop but lexically invisible.
- `temporal_span` on `"last year"` — not in patterns.
- entity_count: actor + tool + location ≈ 3 → +0.10.
- entity_type_count = 3 → +0.05.

**Total: 0.50. Routes to System 1.**

Exactly the "crossing 3+ entity boundaries with temporal constraints" class the RFC names as its target.

### M6. Aggregate factual query — shortcut bypass

Query: `"all known CVEs affecting Windows 11 22H2"`

- `"cve"` keyword → FACTUAL. score=1, unambiguous keyword path → confidence 0.6.
- Shortcut check: FACTUAL, **has_aggregation_markers=True** (`"all known"` matches) → shortcut does NOT fire.
- `intent_prior(FACTUAL) = 0.00`
- `aggregation = +0.30`
- entity_count 2–3, entity_type_count 2 → +0.15 max.

**Total: 0.35–0.45. Routes to System 1.**

This routes to System 1 — plausibly correct for a factual index lookup, but note that the shortcut opt-out for `has_aggregation_markers` intentionally blocks the fast path. Whether that is desirable depends on whether the analyst wants "look up the entity" (System 1 fine) or "enumerate every CVE" (System 2 needed). The shortcut design bakes in the latter assumption but does not quantify the tradeoff.

### M7. `UNKNOWN` is unreachable

No query routes through `QueryIntent.UNKNOWN` because the classifier never returns it (W1). Dead code.

---

## Test Coverage Gaps

Missing tests (implied but not in the RFC's test matrix):

1. **Upgrade-rate window concurrency.** Multi-threaded `recall()` — does upgrade-rate state remain consistent under race?
2. **Upgrade when System 1 returns 0 results.** `should_upgrade` checks `system1_result_count < 3` only for CAUSAL/EXPLORATORY. A RELATIONAL query returning 0 results is ineligible to upgrade — desired?
3. **Shortcut + zero-result path.** B5: FACTUAL single-entity with no matches, `upgrade_eligible=False`. Assert the diagnostic log fires.
4. **Entity-extractor casing disagreement.** Note indexed as `"APT28"` at write time, query extracts `"apt28"` — test normalization.
5. **Missing `created_at` in candidate overflow sort.** Empty-string sort is stable but untested.
6. **Regex compilation failure at import.** A typo in `query_markers.py` bricks the package. Pin a regression test that imports the module.
7. **`max_candidates=0` misconfig.** What happens? Empty results? Filter to vector-only?
8. **`chunk_size: "auto"` with 10 candidates.** What bucket size? Does the chunker degenerate to 1 chunk?
9. **Query with only stop-words.** `"the when of"` — defaults, no entities, no markers. Should degrade cleanly to vector-only.
10. **`has_extension("enterprise") == False` with System 2's max_depth=3 call.** Does System 2 honor the 2-hop cap or bypass it?
11. **Parity test asserts ordering, not just set equality** (W17).
12. **Upgrade-path latency ceiling.** Assert `p95(System1 + System2 latency) < 2× System 2 budget` under upgrade load.
13. **Disabled state bit-identical.** `enabled: false` produces **identical** output (not just similar) to pre-RFC HEAD across the full CTI + LOCOMO suite.
14. **Non-CTI domain.** General-domain query with no CTI markers — does the gate behave sensibly?
15. **Adversarial marker input.** Long queries (10KB+) should not blow up regex engines. Pin a length limit or confirm linear-time behavior.
16. **Truth-table test in `test_quality_gate.py`** is claimed; confirm it actually enumerates every signal-combination that produces a different Decision (≥ 128 rows for 7 bool markers × 6 intents × ambiguous flag).

---

## Positive Notes

1. **Deterministic, inspectable gate is the right call.** The `reasons` list is first-rate for operator debugging and for generating training data for a future learned router. This decision alone justifies the architecture.

2. **Phased rollout is genuinely defensive.** Phase-by-phase decoupling, disabled-by-default shipping, parity tests at each boundary — this is how you de-risk a significant refactor.

3. **System 1 as a verbatim lift** (modulo B2) is the correct minimum-delta approach. Most RFCs at this scope would over-reach; this one does not.

4. **Alternatives Considered is thorough and honest.** Each alternative is engaged with, not strawmanned. The learned-router rejection with follow-up-RFC posture is mature.

5. **Explicit LLM-free fast-path constraint.** Tied to the Qwen2.5-3B/DGX Spark reality. Many RFCs hand-wave provider costs; this one names the constraint up front.

6. **Upgrade path as a safety valve** (not a default) correctly reflects that the gate will sometimes be wrong and that shipping the wrong answer fast is worse than shipping the right answer slow.

7. **Configurable chunk weights with a load-time validation** (must sum to 1.0) is a small touch that prevents a class of production footguns.

8. **Related-RFC references** (001 for entities, 002 for LLM-free constraint) are accurate — the author read the neighboring docs.

9. **D-Mem citation with specific numbers** (96.7%, ~3%) is better than hand-wave grounding. The claim is testable in Phase 3 benchmarks.

10. **Open Questions are real open questions**, not rhetorical. Each has an actual proposal a reviewer can agree or disagree with. That is how Open Questions are supposed to work.
