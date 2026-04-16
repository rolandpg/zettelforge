# RFC-003 Adversarial Review

**Reviewer**: Senior AI Engineer (adversarial)
**Date**: 2026-04-16
**RFC Version Reviewed**: docs/rfcs/RFC-003-read-path-depth-routing.md @ draft (2026-04-16)

## Verdict: REQUEST CHANGES

## Summary

The core architecture is sound: a deterministic, LLM-free gate that lifts today's `recall()` body into a verbatim `System1Retriever` is the right frame, and the D-Mem-inspired chunk-scoring pipeline for multi-hop CTI questions addresses a real accuracy ceiling. However, the scoring table is miscalibrated against the existing intent classifier, the `factual_single_entity_shortcut` silently disables the upgrade safety net for exactly the case it's supposed to catch, and several System 2 primitives (`get_entity_neighbors`, `_extract_time_window`, the claimed `_entity_cache`) are declared but not specified with enough precision to bound their cost. At least three of the RFC's own motivating examples (multi-hop attribution, "evolved over time," aggregation) score below the 0.7 threshold with its own weight table, so the gate as drawn will under-route to System 2, not hit the claimed 3% rate.

## Blockers

### 1. `factual_single_entity_shortcut` disables the upgrade path for its riskiest case

**Description**: `QualityGate.route()` (lines 299–309) short-circuits any FACTUAL query with ≤1 entity to `GateDecision(Depth.SYSTEM_1, 0.0, [...], upgrade_eligible=False)`. The hard-coded `upgrade_eligible=False` means `should_upgrade()` is never consulted. A query like `"CVE-2099-9999"` (not in the store) returns 0 matches with `top_vector_score≈0.1` — exactly the condition the upgrade safety net exists for — and the gate refuses to upgrade because the shortcut preemptively decided not to.

**Impact**: Silent accuracy regression on single-entity factual queries where the entity isn't well-represented in the store. The RFC claims the upgrade path is the "runtime safety valve for pathologically mis-tuned deployments," but the shortcut bypasses it. Also breaks the stated goal of "closing the gap between CTI (75%) and theoretical ceiling by eliminating truncation-driven misses," because truncation-driven misses often manifest as low top-scores on single-entity queries.

**Proposed fix**: Set `upgrade_eligible = (system1_confidence_floor > 0.0)` on the shortcut return, so an unknown CVE still gets a chance to upgrade. Alternatively, run the shortcut only when `intent_confidence >= 0.6` AND the entity exists in the entity index (cheap O(1) check via `store.get_note_ids_for_entity`). Add an explicit test: `CVE-NEVER-SEEN` with empty store → must not route-and-lock to System 1.

### 2. The weight table under-routes the RFC's own motivating examples

**Description**: Walk the scoring algorithm with the exact query from §Motivation: *"which threat actor used CVE-2024-3400 in campaigns that targeted healthcare between Q3 2024 and Q1 2025?"*

- `intent`: "used", "campaigns", "targeted" → RELATIONAL keyword hits. Intent prior = **0.20**.
- `intent_confidence`: high → NOT ambiguous. +0.00.
- Multi-hop markers: `r"\bused by .+ (?:to|in|for|against)\b"` is subject-inverted from "used ... in", doesn't match; `r"\b(?:targeted|hit|compromised) .+ (?:with|via|using)\b"` also doesn't match "targeted healthcare between". **No multi_hop hit.** +0.00.
- Temporal span: `r"\bbetween \d{4}\b"` doesn't match "between Q3 2024" (no \d{4} immediately after "between"). `r"\b(?:q[1-4]|quarter) \d{4}\b.+\b(?:q[1-4]|quarter) \d{4}\b"` *does* match → **+0.20**.
- Causal: no hit. +0.00.
- Aggregation: no hit. +0.00.
- Comparison: no hit. +0.00.
- Entity count ≥3: cve, sector (asset), maybe actor → possibly 3, +0.10. Type count ≥2: +0.05.

**Total: 0.20 + 0.20 + 0.10 + 0.05 = 0.55 < 0.70 → System 1.**

The single most prominent motivating example does not cross the threshold. Similarly, "how did Kimsuky's tooling evolve?" scores 0.55, "compare APT28 and APT29 targets" scores 0.50, and "list every tool used by Lazarus" scores 0.50 (see §Misrouted Query Examples for traces).

**Impact**: With the published defaults, the claimed System 2 rate of ~3% will be closer to 0–1%. The accuracy improvement the RFC is selling will not materialize. Worse, the benchmark claim in Phase 4 ("LOCOMO accuracy materially improves") is a post-hoc moving target rather than a hypothesis the gate is designed to meet.

**Proposed fix**: Either (a) lower `system2_threshold` default to 0.5 and re-audit false-positives, or (b) raise per-signal weights (multi_hop → 0.35, temporal_span → 0.25, aggregation → 0.40). Empirically calibrate by running the CTI + LOCOMO suites through `QualityGate.route()` offline, computing the distribution of scores, and picking a threshold that yields the target 3–5% System 2 rate on the *actual* query mix. Ship the calibration script in `benchmarks/`.

### 3. `is_ambiguous` threshold (0.4) is unreachable from the current intent classifier

**Description**: `QueryProfile.is_ambiguous` returns `intent_confidence < 0.4`. Tracing `intent_classifier.py`:
- `best_score >= 2` → confidence = `min(1.0, best_score/4)` → minimum **0.5**.
- `best_score == 1 and competing == 0` → confidence **0.6**.
- Default (low-confidence fallback, no LLM) → confidence **0.3** → EXPLORATORY.
- LLM fallback success → **0.8**.
- LLM fallback failure → **0.5**.

Only the `"default"` path produces `confidence < 0.4`, and that path always returns EXPLORATORY, not any nuanced intent. So `is_ambiguous` fires if-and-only-if the classifier completely failed — in which case the query has essentially no signal for the gate to use, and +0.15 is not enough to cross 0.7 anyway.

**Impact**: Signal 2 contributes approximately zero routing decisions in practice. The RFC describes ambiguity as "safer to route to System 2," but the mechanism doesn't wire through. Worse, a genuinely ambiguous query (e.g., "Kimsuky activity") ends up at 0.30 confidence + EXPLORATORY intent (+0.20) + ambiguous (+0.15) = 0.35 — quarters below threshold.

**Proposed fix**: Either raise the `is_ambiguous` threshold to 0.6 (catches `keyword_unambiguous` too), or make the gate read `intent_method` directly and apply ambiguity boost for `"default"` and `"keyword_unambiguous"`. Document which confidence bands exist in `intent_classifier.py` and keep the gate in sync as part of Phase 1 validation.

### 4. `CandidateFilter` Path 4 ignores `include_links` and always uses k=200

**Description**: `CandidateFilter.select()` calls `self._mm.retriever.retrieve(query=profile.query, domain=domain, k=200, include_links=True)` unconditionally. The caller's `include_links` parameter is thrown away. `k=200` is hardcoded regardless of the caller's requested `k` (commonly 3 for CTI) and regardless of how much the entity-expansion paths already returned.

**Impact**:
- Changes user-facing semantics when a caller explicitly passed `include_links=False` (e.g., to avoid transitively pulling in linked notes for a privacy/scope reason).
- Forces 200-vector LanceDB query on every System 2 call even when entity expansion already produced 500 candidates — wasted I/O and CPU.
- Exacerbates the DoS concern in Warning 1 by ensuring vector retrieval always runs at max-k on the deep path.

**Proposed fix**: Pass `include_links=include_links` and set `k=min(200, max_candidates - len(candidates))` so the vector fallback is budget-aware. Make it skippable via config (`system2.vector_fallback_k: 200`).

### 5. `should_upgrade` returns False when `top_vector_score is None`, silently disabling the safety net for graph-dominant results

**Description**: `should_upgrade()` starts with `if system1_top_score is not None and system1_top_score < floor: return True`. If `top_vector_score` is None — which happens when `vector_results` was empty and results came entirely from graph retrieval — the first branch is skipped. The second branch only upgrades CAUSAL/EXPLORATORY intents with <3 results. A RELATIONAL query returning 2 graph-only matches with no vector grounding is *the* canonical "collectively weak" case, and it silently skips the safety net.

**Impact**: Exactly the class of query System 2 was designed to help gets no upgrade. Appears in logs as a confident System 1 answer that's actually low-signal.

**Proposed fix**: Treat `top_vector_score is None` as evidence-of-weakness, not absence-of-signal. Upgrade when `system1_top_score is None AND len(results) < 5`. Alternatively, upgrade when `meta.get("phases_executed")` indicates vector phase returned zero.

### 6. `get_entity_neighbors` and `_extract_time_window` are specified by name only

**Description**: Phase 2 adds three storage primitives. The RFC calls them "thin SQLite queries on existing indexes." But:

- `get_entity_neighbors(etype, evalue, hop=1, max_notes=100)` — does `max_notes` mean 100 total, or 100 per neighbor entity? If "Windows" has 500 linked entities, the per-neighbor read could yield 50,000 note IDs and hammer SQLite. If total, the neighbor sort order matters and isn't specified. Neither is the dedup/truncation rule.
- `_extract_time_window(profile.query)` — called in Path 3 but not defined. How does it parse "last quarter"? "Q3 2024 through Q1 2025"? "recently"? If it uses `dateparser`, that's an optional/conditional import in the current code and can fail silently.
- `get_entity_degree` — RFC says "O(1) via SQLite index," but the schema currently has no dedicated degree column; counting edges is O(degree) unless a materialized view is added. That's a schema change the RFC says is unnecessary.

**Impact**: Phase 2's "thin wrapper" claim is not thin. The System 2 latency budget (p95 ≤ 800ms) depends on these primitives being cheap, but the RFC hasn't demonstrated they are. Implementation risk high.

**Proposed fix**: Add a §"Storage Primitive Specifications" subsection with the exact SQL for each primitive, parameterized by the existing indexes, with worst-case row counts for the top-10 highest-degree entities in the current store (measurable today from SQLite). If `get_entity_degree` requires a new index, say so — don't hide it.

### 7. `QueryProfile._entity_cache` is referenced but not declared on the dataclass

**Description**: §ChunkScorer says "entity extractor is run once per candidate note during filter (cached on `QueryProfile._entity_cache`). No re-extraction during scoring." But the `QueryProfile` dataclass definition (lines 103–132) has no `_entity_cache` field. Without it, `ChunkScorer._coverage` and `_density` must re-extract entities from each of up to 500 candidate notes *per query*. Even regex-only extraction at ~1–3ms per note is 500–1500ms — blowing the 800ms budget before chunk scoring begins.

**Impact**: Either the cache doesn't exist (budget busted) or it does exist and is mutable on the frozen-looking dataclass (thread-safety risk if `QueryProfile` is ever shared). The RFC doesn't commit either way.

**Proposed fix**: Add `_entity_cache: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)` to the dataclass. Populate in `CandidateFilter.select()`. Document the lifecycle: cache is per-query, never shared across `recall()` calls.

### 8. Cross-encoder reranker cost on System 2 is understated

**Description**: RFC says "5 chunks × ~20 notes each = 100 rerank pairs, same order of magnitude as System 1's reranker call." But System 1 reranks ≤ k results (typically 10), not 100. 100 pairs is 10× System 1 at the same model (Xenova/ms-marco-MiniLM-L-6-v2). On the measured 20ms/System-1-rerank baseline, that projects to 200ms for System 2 reranking alone.

Combined budget math:
- CandidateFilter: unknown (see Blocker 6), assume 100–300ms
- Entity extraction on 500 candidates (if no cache, see Blocker 7): 500–1500ms
- Temporal chunking: negligible
- Chunk scoring: 200–500ms (degree/edge lookups per chunk)
- Within-chunk rerank: 200ms
- **Total: 500–2500ms, well past 800ms p95 target.**

**Impact**: System 2 won't meet its advertised latency. Users running the upgrade path pay System 1 + System 2 = 650ms–2.6s.

**Proposed fix**: Either (a) reduce `max_chunks` default to 3 and `target_notes_per_bucket` to 10 (caps rerank at 30 pairs), or (b) commit to a smaller reranker model for System 2 and accept a quality trade. Publish a measured budget breakdown in Phase 3 before wiring the gate.

## Warnings

### 1. System 2 is a DoS amplifier with no rate limit or timeout

An attacker who knows the marker regexes can craft queries that always route to System 2: *"comprehensive list of every campaign that every actor conducted that led to each incident and trace the root cause chain between Q1 2024 and Q4 2025"* — hits aggregation (+0.30), causal_chain (+0.25), temporal_span (+0.20), comparison-adjacent. Each query forces 500-candidate entity extraction + chunk scoring + reranking. With no per-caller rate limit or per-query timeout, a handful of concurrent clients saturates the process. `max_upgrade_rate` only caps the upgrade *ratio*, not absolute System 2 traffic.
**Fix**: Add `system2.max_concurrent` (semaphore) and `system2.timeout_ms` (hard cutoff → fall back to System 1 result or empty list).

### 2. Silent data loss on notes without `created_at`

`TemporalChunker.bucket()` does `if not note.created_at: continue` — notes with missing timestamps are silently dropped from chunk scoring, so they can never appear in System 2 results even if they're the best semantic match. Old imported data, corrupted records, or sync artifacts can all have missing timestamps.
**Fix**: Bucket undated notes into an `__undated__` chunk with `recency=0` but full coverage/density scoring. Log a WARN once per query when this happens.

### 3. Non-English queries bypass marker detection entirely

All marker regexes are English. A Spanish CTI analyst asking *"¿qué actores usan CVE-2024-3400 en campañas entre Q3 2024 y Q1 2025?"* scores exactly zero on every span marker. The gate routes every non-English query to System 1 by construction, regardless of how deliberation-worthy it is. RFC doesn't acknowledge this.
**Fix**: Document as a known limitation. Consider a config-loadable marker set (`config.recall.depth_routing.marker_sets: [en, es, fr]`) in a follow-up.

### 4. The intent classifier tie-breaking leaks nondeterminism

`max(scores, key=scores.get)` on ties picks the first-inserted intent in `INTENT_KEYWORDS`. Multiple keyword hits across intents (e.g., "why was CVE-X used by APT28?" hits CAUSAL:why, FACTUAL:cve-, RELATIONAL:used by) tie at 1 each → FACTUAL wins only because it's first in the dict. The RFC relies on intent as a primary routing signal but inherits this nondeterminism. Reordering `INTENT_KEYWORDS` silently changes the gate's behavior for tied queries.
**Fix**: Call out as a known upstream behavior. Add an intent_classifier regression test that asserts the ordering isn't accidentally changed.

### 5. Temporal regex false-positive on causal queries

`r"\bfrom .+ (?:to|until|through) .+"` matches *"trace the causal chain from the phishing email to credential theft"* — a purely causal query gets flagged `has_temporal_span`. TemporalChunker would then bucket by week when daily-or-finer is what the query needs.
**Fix**: Make the temporal regex require a date-ish right-hand side, or score causal_chain first and suppress temporal_span when both fire on the same short distance.

### 6. `max_upgrade_rate` enforcement is underspecified

§Upgrade path says "if > X% of queries upgrade in a rolling window, raise the gate threshold automatically." §Config schema describes it as "caps upgrade frequency." These are two different behaviors (auto-tune vs. hard cap). Implementation ambiguity = different production behaviors across deployments.
**Fix**: Pick one. If auto-tune, specify the adjustment step and cooldown. If cap, specify what happens when capped (drop to empty? return System 1 result?).

### 7. Entity extraction on query vs. on notes uses different LLM policy

Current `recall()` line 464 calls `self.indexer.extractor.extract_all(query)` — parameter `use_llm` defaults to False, but the entity extractor docstring notes "Uses regex for CTI types (always) and LLM for conversational types (when use_llm=True and text is long enough)." The RFC says Phase 2 is a "verbatim lift," but `QueryProfile.build()` must explicitly match the current parameter semantics — including whatever `use_llm` default applies when `extract_all` is called with one positional argument. If `QueryProfile.build` defaults differently, System 1 parity breaks.
**Fix**: `test_system1_parity.py` must parameterize over the same `extract_all` call as today's line 464. Explicitly state in §QueryProfile that `use_llm` for query extraction matches current behavior.

### 8. Signal 8 double-counts entity breadth

Signal 8 gives +0.10 for `entity_count >= 3` and additionally +0.05 for `entity_type_count >= 2`. A query with 3 entities of 2 distinct types gets +0.15; a query with 3 entities all of the same type gets +0.10. But for multi-hop questions, type-diversity is actually *more* predictive than raw count. The weighting has it partly backward.
**Fix**: Invert: `entity_type_count >= 2` → +0.15; `entity_count >= 3` → +0.05. Or make them mutually exclusive (bigger of the two).

### 9. No graceful degradation for System 2 exceptions

If `ChunkScorer._causal` raises (KG traversal bug, SQLite locked), does `recall()` raise to the caller? The current `recall()` wraps reranker in try/except. The RFC's final `recall()` body does not wrap System 2. With System 2 at 3% of traffic, a latent bug means 3% of all recalls start raising.
**Fix**: Wrap the `self._system2.retrieve()` call in `recall()` with a try/except → log + fallback to System 1 results (if available) or empty list. Emit a metric so the failure is visible.

### 10. Upgrade can re-execute expensive System 1 phases inside System 2

After System 1 runs (vector + graph + entity + rerank), the upgrade hands control to System 2, which runs its own vector fallback (k=200), entity expansion, and rerank. Nothing is passed across. Worst case: the query executes two full retrieval pipelines for a single `recall()` call.
**Fix**: Pass `system1_results` into `System2Retriever.retrieve()` so System 2 can seed its candidate set from System 1's output and skip the redundant vector fallback.

### 11. Reproducibility claim is weakened by reranker non-determinism

RFC: "Deterministic — identical query always routes identically." True for the gate. But downstream, cross-encoder reranker ordering on ties depends on floating-point arithmetic that can vary by batch size / backend / hardware. System 2's bucket boundaries shift if candidate timestamps are identical to the second. The guarantee is "same route, possibly different result ordering."
**Fix**: State the guarantee scope explicitly: "gate decision is deterministic; downstream retrieval result ordering is subject to existing reranker/vector-backend determinism guarantees." No code change.

### 12. `chunk_weights` validation at config load isn't shown

Schema says "(must sum to 1.0; validated at load)" but no validation code. If a user sets weights summing to 0.9 or 1.2, chunk scores become un-comparable across queries (a low-scoring chunk under one config may be a high-scoring chunk under another).
**Fix**: Add explicit validation in config loader. Reject (or renormalize + warn) at startup.

### 13. `depth_override` deferral is reasonable but callers have no escape hatch today

Existing test suites and benchmarks often need to pin depth for reproducibility (e.g., "run this benchmark entirely on System 2"). Per the RFC, the only escape hatch in Phase 3 is "explicit test hooks" — undefined. Without a `depth_override` path, Phase 3 validation is awkward.
**Fix**: Ship `depth_override` in Phase 3 scoped to internal callers only; expose it publicly in v2.4.0 per the Open Question proposal.

## Nits

1. **`GateDecision.reasons` format** mixes human-readable strings with embedded scores (`"multi_hop(+0.25)"`). Makes structured log parsing brittle. Prefer `list[tuple[str, float]]` and render to string at log time.
2. **"D-Mem (arXiv:2603.18631)"** — never expanded. arXiv IDs are `YYMM.NNNNN`, so `2603` is March 2026. If this is a real paper, fine; if it's a forward-dated placeholder, readers will notice. Expand the acronym on first use and link the paper.
3. **`Depth` enum values are `"system_1"`/`"system_2"`** with underscore — but log fields, config YAML, and docstrings use `System 1`/`System 2` with space. Trivial inconsistency, easy to fix before users grep for the wrong string.
4. **`Optional[Literal[...]]` in Open Question 1** uses `typing.Literal` but the rest of the RFC uses lowercase `list[str]` / `tuple[...]`. Python-version baseline isn't stated — call it out once (3.9+ or 3.10+).
5. **Fast-path latency claim is aspirational.** RFC says single-entity lookups are "routed to a leaner System 1 variant with lower p50 than today's uniform pipeline" — but the shortcut just returns `Depth.SYSTEM_1` with no change to what System 1 does. Today's p50 is 111ms and stays 111ms; there's no "lean" variant. Either introduce one (entity-index-only path for the shortcut) or soften the claim.
6. **"Bit-identical"** is used twice to describe Phase 4-disabled behavior. Bit-identical is a strong claim; cross-encoder reranking on identical inputs may produce different float scores run-to-run on GPUs. Prefer "output-equivalent on the CTI parity harness."
7. **`QueryProfile.query_lower`** is stored but never shown being used in the dataclass code; markers use `query_lower` internally. Since markers take raw query today via `re.IGNORECASE`, consider dropping `query_lower` from the dataclass or using it consistently in markers.
8. **§File Layout** shows `memory_store.py` being modified in Phase 2 bullet but the top §File Layout only lists `sqlite_backend.py` as modified. Tighten.
9. **Config key `chunk_size: auto`** mixes string and enum values (`"hourly" | "daily" | "weekly"` vs `"auto"`). Consider `chunk_size: "auto"` with `bucket_override: null | "hourly" | "daily" | "weekly"` for clarity.
10. **`Signal 9` comment** says "Single-entity factual shortcut — force System 1" but the *logic* also excludes queries with `has_aggregation_markers`. The signal name should be `factual_shortcut` (or more explicit).
11. **Test layout** splits `test_system2_candidate_filter.py` and `test_system2_chunk_scoring.py` but no `test_system2_end_to_end.py` is listed for full-pipeline integration testing. Add.
12. **§Migration "Callers of `recall()`"** says "Zero signature changes." True for positional args, but the function now produces new structured log fields (`gate_depth`, `gate_score`, `gate_reasons`). Any log-schema consumers need to know.

## Misrouted Query Examples

With `system2_threshold: 0.7` (published default), the following motivating queries are misrouted to System 1. Each trace shows exact signal contributions.

### 1. "which threat actor used CVE-2024-3400 in campaigns that targeted healthcare between Q3 2024 and Q1 2025?"
**The RFC's own headline example.** Traces to: intent=RELATIONAL (0.20) + temporal_span via quarter-regex (0.20) + entity_count≥3 (0.10) + entity_type_count≥2 (0.05) = **0.55 → System 1.** Below threshold by 0.15. Multi_hop pattern `\b(?:targeted|hit|compromised) .+ (?:with|via|using)\b` does not match "targeted healthcare between" because it requires `with/via/using`.

### 2. "how did Kimsuky's tooling evolve over the past year?"
intent=EXPLORATORY default (0.20, "how"/"evolve" not in keywords), not ambiguous if any single keyword hits — but here nothing hits, so default 0.3 → ambiguous (+0.15) + temporal_span "evolve" (+0.20) + 1 entity (no bonus) = **0.55 → System 1.** Exactly the long-horizon query D-Mem cites as System 2 territory.

### 3. "compare APT28 and APT29 campaign targets"
intent=EXPLORATORY (0.20) + ambiguous (+0.15) + comparison (+0.15) + entity_type_count≥2 if actors counted separately (+0.05) = **0.55 → System 1.** A classic multi-branch comparison. Both branches need full retrieval; top-k truncation will miss one.

### 4. "list every tool used by Lazarus that was also seen in APT41 operations"
intent=RELATIONAL ("used by" keyword) (0.20) + aggregation "every" (+0.30) + entity_count=2 (no bonus) + entity_type_count≥2 (+0.05) = **0.55 → System 1.** Multi-hop set-intersection question that System 1 top-k will fail.

### 5. "why did APT28 start using WMI in 2023 after previously preferring PowerShell?"
intent=CAUSAL ("why") (0.35) + temporal markers — "in 2023" has no year-range, "previously" hits intent_classifier TEMPORAL but the temporal_span regex doesn't trigger — +0.00 + entity_count=3 (+0.10) = **0.45 → System 1.** Five-entity, two-time-point, causal question. Routed to the fast path.

### 6. "CVE-2099-9999" (unknown CVE, not in store)
intent=FACTUAL, single entity → `factual_single_entity_shortcut` fires → System 1, `upgrade_eligible=False`. System 1 returns 0 notes, `top_vector_score=0.05`, but the upgrade gate is locked off. **Silent no-result at fast-path latency**, when a deliberation pass would have at least tried adjacent-CVE or referenced-advisory notes.

### 7. "trace the causal chain from the phishing email to credential theft"
"trace" hits causal_chain (+0.25). "from ... to ..." *also* hits temporal_span regex `\bfrom .+ (?:to|until|through) .+` — a false positive. intent=EXPLORATORY default (0.20) + ambiguous (+0.15) + causal (+0.25) + temporal_span spurious (+0.20) = **0.80 → System 2.** Correctly routed — but for the wrong reasons. TemporalChunker then buckets by weekly (span marker), when the actual query wants sub-hour granularity. Chunk scoring produces degraded recency ranking.

### 8. "¿Qué actores usan CVE-2024-3400 en campañas entre Q3 2024 y Q1 2025?"
Spanish translation of Example 1. intent=FACTUAL or EXPLORATORY (depending on "cve-" keyword match on lowercased Spanish — "cve-" probably still hits). But *no marker regex hits anything else* — all patterns are English. Score = 0.00 + ambiguous (+0.15) + entities(+0.10)(+0.05) = **0.30 → System 1.** An identical-intent query misroutes differently based on language.

### 9. "Tell me everything about APT28"
"tell me about" is EXPLORATORY keyword (score=1, competing=0 → keyword_unambiguous, confidence=0.6, not ambiguous) → intent=EXPLORATORY (0.20) + 1 entity (no bonus) = **0.20 → System 1.** "Everything" signals aggregation intent but isn't in the aggregation regex (regex requires `every + {instance,case,campaign,incident}` or `comprehensive + {list,overview,...}`).

### 10. "list all CVEs exploited by Lazarus"
"all" alone doesn't hit aggregation regex (needs `all + {known,observed,reported,documented}`). intent=RELATIONAL ("used by" NOT present; "exploited by" not a keyword). EXPLORATORY default (0.20) + ambiguous (+0.15) + entity_count=1 = **0.35 → System 1.** Aggregation query that needs deliberation misses due to overly-specific aggregation regex.

## Test Coverage Gaps

Tests explicitly missing from the RFC's Phase validation plan:

1. **Factual shortcut + unknown entity** — CVE-NEVER-SEEN query must not lock off the upgrade path (Blocker 1).
2. **Calibration test** — apply `QualityGate.route()` to the full CTI + LOCOMO query suite, assert the System 2 rate is 3–5% as claimed. Fail the build if outside band.
3. **`is_ambiguous` coverage** — assert that at least one non-default-intent path can trigger `is_ambiguous` (currently none do, see Blocker 3).
4. **System 2 empty store** — `count_notes() == 0` path through CandidateFilter / TemporalChunker / ChunkScorer / Reranker must not raise.
5. **System 2 degenerate query** — `recall("")`, `recall("   ")`, `recall(".....")`, `recall("the a and or")` — must route and return without crashing.
6. **System 2 non-English** — at minimum test Spanish and French equivalents of motivating queries. Document behavior.
7. **System 2 exception handling** — inject a fault in `ChunkScorer._causal` (mock) and assert `recall()` still returns results (fallback to System 1 or empty list).
8. **System 2 timeout** — query that exceeds `system2.timeout_ms` must fall back gracefully, not block indefinitely.
9. **`include_links=False` end-to-end** — assert System 2 respects the parameter (currently ignored in Path 4 — Blocker 4).
10. **`is_expired()` filter in System 2** — System 1 applies it (line 588 of current `recall()`), RFC doesn't show System 2 applying it. Test both paths.
11. **`exclude_superseded` in System 2** — same concern as above.
12. **Gate disabled → bit-identical output** — parity test run with `recall.depth_routing.enabled: false`, compared against git HEAD pre-Phase-2 output on the same query suite.
13. **Thread-safety** — 10 concurrent System 2 calls on distinct queries; no race, no shared-state corruption.
14. **Upgrade-path latency pathology** — query matching the 0.4 ≤ score < 0.7 band with weak System 1 result. Assert worst-case latency is logged and within a published p99 bound.
15. **`max_upgrade_rate` enforcement** — force 20% of queries to trigger upgrade; assert either throttling or auto-tuning kicks in per the spec (Warning 6).
16. **Marker regex ReDoS resistance** — feed a 100KB query with pathological character runs (`"x" * 100_000`), assert bounded latency.
17. **Chunk_weights validation at config load** — sum < 1.0, sum > 1.0, negative weight, missing key → load must fail or renormalize + warn (Warning 12).
18. **`get_entity_degree` on high-cardinality entity** — "Windows" / "DNS" / "PowerShell"; assert O(1) claim (Blocker 6).
19. **`iterate_notes_in_range` with invalid ISO strings** — malformed timestamps in store must not crash the scan.
20. **QueryProfile entity cache lifetime** — assert cache is per-query, not shared; assert cache is populated by CandidateFilter and consumed by ChunkScorer without re-extraction (Blocker 7).
21. **Causal-chain + temporal false-positive** — assert chunk size selection is sane when both markers fire spuriously together (Warning 5).

## Positive Notes

- **Deterministic, LLM-free gate on the hot path** is the right call for CTI reproducibility and for the Qwen2.5-3B/DGX Spark latency envelope. The rejection of Alternative 1 (LLM router) is well-argued and self-consistent.
- **System 1 as verbatim lift** is a smart reversibility story. One-line config flip to roll back is genuinely safer than any alternative I considered.
- **Phased implementation plan** where each phase is independently shippable (Phases 1–2 deliver value even if Phase 3 misses its latency budget) is mature.
- **`upgrade_eligible` safety net** is a good architectural hedge — the design correctly acknowledges that the initial gate decision can be wrong.
- **Additive bounded scoring + reasons list** gives inspectability that a learned model wouldn't. This is the right baseline to gather training data for a future learned router.
- **Explicit rejection of Alternative 6 (tier-based routing)** — correct reasoning; tier measures note stability, not query complexity.
- **Structured logging fields** (`gate_depth`, `gate_score`, `gate_reasons`) set up the observability foundation for tuning and for the eventual learned-router RFC.
- **Reuse of existing primitives** (entity index, KG, LanceDB) with no new external dependencies keeps the dependency surface flat.
- **Backward compatibility posture** (`enabled: false` default for v2.3.0, flip in v2.4.0 after telemetry) is disciplined and conservative.
- **Open Questions section** captures the right uncertainties — none are being papered over. Open Q 7 (latency pathology) correctly identifies the worst-case risk.

---

## Summary of Required Actions Before Approve

**Must-fix before merge** (blockers):
1. Restore upgrade eligibility for factual shortcut (or condition the shortcut on entity existence).
2. Calibrate weight table against actual CTI/LOCOMO query mix; publish the calibration script.
3. Fix `is_ambiguous` threshold to match intent_classifier confidence bands.
4. CandidateFilter Path 4 honors `include_links` and budgets its k.
5. `should_upgrade` handles `top_vector_score is None` as weak-evidence, not absent.
6. Specify storage primitive SQL + worst-case bounds.
7. Add `_entity_cache` to `QueryProfile` dataclass.
8. Audit System 2 latency budget against measured chunk-scoring + rerank cost.

**Should-fix before GA** (warnings): System 2 concurrency caps + timeout, undated-note chunking, exception handling around System 2, marker false-positive suppression, `max_upgrade_rate` unambiguous semantics.

**Nice-to-have before GA** (nits): structured reasons list, logging schema doc, `depth_override` for internal test hooks.

With these addressed, the RFC is a net-positive change. As-written, it ships with a gate that under-routes its own motivating examples and a safety net with two holes.
