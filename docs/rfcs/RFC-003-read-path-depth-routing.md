# RFC-003: Read-Path Depth Routing (Quality Gate + System 1/System 2)

## Metadata

- **Author**: Patrick Roland
- **Status**: Draft
- **Created**: 2026-04-16
- **Last Updated**: 2026-04-16
- **Reviewers**: TBD
- **Related Tickets**: CTI benchmark accuracy ceiling at 75%; LOCOMO p95 at 2282ms; multi-hop attribution failures
- **Related RFCs**: RFC-001 (Conversational Entity Extractor — feeds System 2 candidate expansion), RFC-002 (Universal LLM Provider — Quality Gate MUST run without LLM calls)

## Summary

Introduce a **Quality Gate** on `recall()` that routes queries to one of two retrieval depths: **System 1** (the current blended-retrieval pipeline — fast, vector + graph + entity + reranker) or **System 2** (a new exhaustive-scan path with pre-filtering and temporal-chunk scoring). The gate is deterministic, LLM-free on the fast path, and uses heuristic signals derived from the already-computed intent classification, query entity extraction, and explicit query markers. Per D-Mem (arXiv:2603.18631), routing ~3% of queries to System 2 recovers 96.7% of full-deliberation accuracy while preserving System 1 latency for the other 97%.

The existing `intent_classifier.py` and `blended_retriever.py` are not modified. System 1 is the current `recall()` body, lifted behind an interface. System 2 is a new module built on ZettelForge's existing primitives (LanceDB, SQLite, fastembed, entity indexer) — no external dependencies.

## Motivation

Current `recall()` applies a single pipeline to every query regardless of complexity. Measured on a DGX Spark ARM64 with a ~4450-note store:

- CTI queries (single-entity lookups, factual): **p50 111ms, p95 ~200ms, 75% accuracy**
- LOCOMO queries (multi-hop, long-horizon): **p50 1240ms, p95 2282ms**
- Intent classification (keyword path): **<1ms**
- Cross-encoder reranking: **~20ms**

Two failure modes are visible in these numbers:

**1. Low-complexity queries pay for machinery they don't need.** A query like `CVE-2024-1234` triggers intent classification, entity extraction, vector retrieval over ~4450 notes, graph traversal at depth 2, entity-augmented pull, and cross-encoder reranking — when a single entity-index lookup would answer it. The CTI p50 of 111ms is inflated by phases that contribute no signal for this query class.

**2. High-complexity queries are capped at System 1's ceiling.** Multi-hop CTI attribution (e.g., *"which threat actor used CVE-2024-3400 in campaigns that targeted healthcare between Q3 2024 and Q1 2025?"*) requires crossing 3+ entity boundaries with temporal constraints. The current top-k blend (default k=10) with depth-2 graph traversal cannot guarantee coverage of the full causal chain. Notes that are individually low-similarity but collectively form the answer are dropped before reranking ever sees them. This manifests as the 25% accuracy gap on CTI and the long-tail p95 on LOCOMO.

The 5-way intent classifier already identifies these query classes — but today it only weights traversal policy, not depth. FACTUAL queries still run the full blended pipeline. CAUSAL queries still cap at depth 2. Depth is currently a fixed constant of the code path, not a function of the query.

### D-Mem finding

D-Mem observed that a Quality Gate routing queries to fast-vector (System 1) vs. exhaustive-scan (System 2) recovers **96.7% of full-deliberation accuracy at System 1 cost**, because only ~3% of queries require deliberation. The System 2 path scans raw history (vs. top-k) and scores temporal chunks rather than individual memories, which catches the "collectively true, individually weak" pattern that multi-hop CTI questions exhibit.

### Who benefits

- **CTI analysts** asking multi-hop attribution questions (System 2 finds the full chain instead of truncating at top-10).
- **Incident responders** asking temporal-correlation questions spanning weeks (System 2's chunk scoring beats top-k vector on long time horizons).
- **Fast-path users** running entity lookups and FAQ-style queries — they are routed to a leaner System 1 variant with lower p50 than today's uniform pipeline.
- **Benchmark reviewers**: closes the gap between CTI (75%) and the theoretical ceiling by eliminating truncation-driven misses.

## Proposed Design

### Architecture Overview

```
recall(query, ...)
  |
  v
IntentClassifier.classify(query)        # Existing — unchanged, <1ms
  |
  v
QueryProfile                            # NEW — cheap feature bundle
  ├─ intent + confidence
  ├─ query entities (from EntityExtractor)
  ├─ span markers (temporal, causal, multi-hop)
  └─ aggregation markers
  |
  v
QualityGate.route(profile) ─────┐       # NEW — deterministic, <5ms
  |                             |
  | System1                     | System2
  v                             v
System1Retriever                System2Retriever       # NEW module
  = current recall() body       = candidate pre-filter
  (vector + graph + entity      + temporal chunking
   + reranker, unchanged)       + chunk scoring
  |                             + note-level rerank within top chunks
  |                             |
  +-─── results ─── upgrade? ───+
  |         (if System1 score floor breached)
  v
[optional] System1→System2 upgrade
  |
  v
results: List[MemoryNote]
```

Two design principles:

1. **The Quality Gate is deterministic and LLM-free on the fast path.** It reads features that are already computed (intent, entities) plus one additional cheap probe (vector top-1 score). LLM fallback exists but is opt-in and only fires on explicit ambiguity signals.

2. **System 1 is the existing pipeline, unmodified.** The current `recall()` body is lifted into `System1Retriever.retrieve()` verbatim. This preserves CTI p50 performance, keeps all existing tests green, and means rolling back the feature is a one-line config flip.

### QueryProfile

A `QueryProfile` is a cheap feature bundle computed once per query. Every gate decision and every retriever phase reads from this same object — no re-classification, no re-extraction.

```python
# src/zettelforge/query_profile.py

from dataclasses import dataclass, field
from typing import Dict, List

from zettelforge.intent_classifier import QueryIntent


@dataclass
class QueryProfile:
    """Features computed once per query, consumed by gate + retrievers."""

    query: str
    query_lower: str

    # From IntentClassifier (existing)
    intent: QueryIntent
    intent_confidence: float
    intent_method: str  # "keyword" | "keyword_unambiguous" | "llm" | "default"

    # From EntityIndexer.extractor (existing)
    entities: Dict[str, List[str]] = field(default_factory=dict)
    resolved_entities: Dict[str, List[str]] = field(default_factory=dict)

    # Derived span markers (computed by QueryProfile.build)
    has_multi_hop_markers: bool = False      # 2+ entities + relational glue
    has_temporal_span: bool = False          # date range, "over time", "evolved"
    has_causal_chain_markers: bool = False   # "trace", "root cause", "led to", ≥2 causal verbs
    has_aggregation_markers: bool = False    # "all", "every", "comprehensive", "complete list"
    has_comparison_markers: bool = False     # "vs", "versus", "compare", "difference between"

    # Counts used by the gate
    entity_count: int = 0                    # total resolved entities
    entity_type_count: int = 0               # distinct entity types

    @property
    def is_ambiguous(self) -> bool:
        return self.intent_confidence < 0.4
```

`QueryProfile.build(query)` is a single function that runs intent classification, entity extraction, and marker detection. It is the only place query features are computed. System 1 and System 2 both accept a `QueryProfile`, not a raw string.

### Span Marker Detection

Markers are detected by compiled regex against `query_lower`. Compilation happens once at import time. Marker sets are deliberately CTI-flavored because that is ZettelForge's primary domain.

```python
# src/zettelforge/query_markers.py

import re

# Multi-hop glue: phrases that chain 2+ entities together
_MULTI_HOP_PATTERNS = [
    r"\band then\b", r"\bafter (?:that|which|the)\b",
    r"\bused by .+ (?:to|in|for|against)\b",
    r"\battributed to .+ (?:via|through|using)\b",
    r"\b(?:targeted|hit|compromised) .+ (?:with|via|using)\b",
    r"\b(?:which|what) .+ (?:used|deployed|executed) .+ (?:against|to compromise)\b",
]

# Temporal span: query covers a range, evolution, or change over time
_TEMPORAL_SPAN_PATTERNS = [
    r"\bover time\b", r"\bevolved\b", r"\bevolution (?:of|in)\b",
    r"\bchanged (?:from|over|since)\b", r"\btrend\b",
    r"\bbetween \d{4}\b.+\b(?:and|to) \d{4}\b",
    r"\b(?:q[1-4]|quarter) \d{4}\b.+\b(?:q[1-4]|quarter) \d{4}\b",
    r"\bfrom .+ (?:to|until|through) .+",
    r"\bacross (?:multiple|several) (?:months|quarters|years|campaigns)\b",
]

# Causal chain: root cause, trace-back, multi-step causation
_CAUSAL_CHAIN_PATTERNS = [
    r"\btrace (?:back|the)\b", r"\broot cause\b",
    r"\bchain of\b", r"\bled to .+ (?:which|that)\b",
    r"\b(?:how|why) did .+ (?:cause|lead|result|trigger)\b",
    r"\bbecause .+ (?:which|and then|led)\b",
]

_AGGREGATION_PATTERNS = [
    r"\ball (?:known|observed|reported|documented)\b",
    r"\bevery (?:instance|case|campaign|incident)\b",
    r"\bcomprehensive (?:list|overview|summary)\b",
    r"\bcomplete (?:list|picture|history)\b",
    r"\b(?:exhaustive|full) (?:list|history)\b",
]

_COMPARISON_PATTERNS = [
    r"\bvs\.?\b", r"\bversus\b",
    r"\bcompare (?:to|with|between)\b",
    r"\bdifference between\b",
    r"\bhow does .+ differ from\b",
]

MULTI_HOP_RE = re.compile("|".join(_MULTI_HOP_PATTERNS), re.IGNORECASE)
TEMPORAL_SPAN_RE = re.compile("|".join(_TEMPORAL_SPAN_PATTERNS), re.IGNORECASE)
CAUSAL_CHAIN_RE = re.compile("|".join(_CAUSAL_CHAIN_PATTERNS), re.IGNORECASE)
AGGREGATION_RE = re.compile("|".join(_AGGREGATION_PATTERNS), re.IGNORECASE)
COMPARISON_RE = re.compile("|".join(_COMPARISON_PATTERNS), re.IGNORECASE)
```

Markers are additive signals, not classifications. A query can hit zero, one, or several marker sets; the gate scores them.

### QualityGate

```python
# src/zettelforge/quality_gate.py

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from zettelforge.intent_classifier import QueryIntent
from zettelforge.query_profile import QueryProfile


class Depth(Enum):
    SYSTEM_1 = "system_1"  # Fast blended retrieval (current path)
    SYSTEM_2 = "system_2"  # Exhaustive scan + temporal chunk scoring


@dataclass
class GateDecision:
    depth: Depth
    score: float             # 0.0 (confident System 1) to 1.0 (confident System 2)
    reasons: list[str]       # Which signals fired
    upgrade_eligible: bool   # If System 1, may be upgraded post-hoc


class QualityGate:
    """
    Deterministic, LLM-free router. Runs in <5ms on keyword path.

    Scoring is additive. Each signal contributes a bounded weight.
    Total score is clamped to [0, 1]. Threshold-based routing.
    """

    def __init__(
        self,
        system2_threshold: float = 0.7,
        system1_confidence_floor: float = 0.4,
        enabled: bool = True,
    ):
        self.system2_threshold = system2_threshold
        self.system1_confidence_floor = system1_confidence_floor
        self.enabled = enabled

    def route(self, profile: QueryProfile) -> GateDecision:
        if not self.enabled:
            return GateDecision(Depth.SYSTEM_1, 0.0, ["gate_disabled"], False)

        score = 0.0
        reasons: list[str] = []

        # Signal 1: Intent class prior (CAUSAL and some EXPLORATORY are System-2-leaning)
        intent_prior = {
            QueryIntent.FACTUAL:     0.00,
            QueryIntent.TEMPORAL:    0.10,
            QueryIntent.RELATIONAL:  0.20,
            QueryIntent.EXPLORATORY: 0.20,
            QueryIntent.CAUSAL:      0.35,
            QueryIntent.UNKNOWN:     0.25,
        }.get(profile.intent, 0.10)
        if intent_prior > 0:
            score += intent_prior
            reasons.append(f"intent:{profile.intent.value}(+{intent_prior:.2f})")

        # Signal 2: Ambiguous intent → System 2 is safer
        if profile.is_ambiguous:
            score += 0.15
            reasons.append("ambiguous_intent(+0.15)")

        # Signal 3: Multi-hop markers
        if profile.has_multi_hop_markers:
            score += 0.25
            reasons.append("multi_hop(+0.25)")

        # Signal 4: Temporal span (range, evolution, trend)
        if profile.has_temporal_span:
            score += 0.20
            reasons.append("temporal_span(+0.20)")

        # Signal 5: Causal chain markers
        if profile.has_causal_chain_markers:
            score += 0.25
            reasons.append("causal_chain(+0.25)")

        # Signal 6: Aggregation (all / every / comprehensive)
        if profile.has_aggregation_markers:
            score += 0.30
            reasons.append("aggregation(+0.30)")

        # Signal 7: Comparison (needs both sides fully retrieved)
        if profile.has_comparison_markers:
            score += 0.15
            reasons.append("comparison(+0.15)")

        # Signal 8: Entity density — 3+ entities OR 2+ distinct types signals breadth
        if profile.entity_count >= 3:
            score += 0.10
            reasons.append(f"entity_count:{profile.entity_count}(+0.10)")
        if profile.entity_type_count >= 2:
            score += 0.05
            reasons.append(f"entity_types:{profile.entity_type_count}(+0.05)")

        # Signal 9: Single-entity factual shortcut — force System 1
        if (
            profile.intent == QueryIntent.FACTUAL
            and profile.entity_count <= 1
            and not profile.has_multi_hop_markers
            and not profile.has_aggregation_markers
        ):
            return GateDecision(
                Depth.SYSTEM_1, 0.0,
                ["factual_single_entity_shortcut"], upgrade_eligible=False,
            )

        score = min(score, 1.0)
        depth = Depth.SYSTEM_2 if score >= self.system2_threshold else Depth.SYSTEM_1
        upgrade_eligible = (depth == Depth.SYSTEM_1 and score >= 0.4)

        return GateDecision(depth, score, reasons, upgrade_eligible)

    def should_upgrade(
        self,
        profile: QueryProfile,
        system1_top_score: Optional[float],
        system1_result_count: int,
    ) -> bool:
        """
        Post-System-1 upgrade check.

        Fires when the initial gate allowed System 1 but returned a weak result:
          - Top vector score below floor, OR
          - Fewer results than expected for the intent's default top-k.
        """
        if system1_top_score is not None and system1_top_score < self.system1_confidence_floor:
            return True
        if profile.intent in (QueryIntent.CAUSAL, QueryIntent.EXPLORATORY):
            if system1_result_count < 3:
                return True
        return False
```

**Why additive, bounded scoring rather than a learned model:**

- Deterministic — identical query always routes identically. Critical for CTI where reproducibility matters.
- Inspectable — the `reasons` list tells the user (and the log) exactly why a query was routed. No black box.
- LLM-free — no dependency on the LLM provider on the hot path. Satisfies the Qwen2.5-3B on DGX Spark constraint.
- Tunable per deployment — thresholds and per-signal weights are config-exposed.
- Cheap to evolve — adding a new marker is one regex + one score line; no retraining.

A learned router is viable in a later RFC once we have enough routed traffic to build ground truth labels. It is explicitly **not** in scope for v2.3.0.

### System 1 — Existing Path, Extracted

System 1 is the current `recall()` body, moved verbatim into a class. No behavior changes.

```python
# src/zettelforge/retrieval/system1.py

class System1Retriever:
    """
    Existing fast path: vector + graph + entity + cross-encoder rerank.
    Code is lifted from recall() in memory_manager.py — no semantic changes.
    """

    def __init__(self, memory_manager):
        self._mm = memory_manager

    def retrieve(
        self,
        profile: QueryProfile,
        domain: Optional[str],
        k: int,
        include_links: bool,
        exclude_superseded: bool,
        include_expired: bool,
    ) -> tuple[list[MemoryNote], dict]:
        # Body = current recall() from line 469 (vector retrieval) through
        # line 594 (cap at k), unmodified. Intent/entity fields are read from
        # `profile` instead of re-computed. Returns (results, metadata).
```

The only edit to the original code is reading `profile.intent` / `profile.resolved_entities` instead of calling the classifier/extractor inline. Everything downstream — the temporal date-pattern boost, blended retrieval, causal edge traversal, entity-augmented recall, cross-encoder reranking, superseded/expired filters — is unchanged.

Metadata returned includes `top_vector_score` (used by the upgrade gate) and the list of phases executed.

### System 2 — Pre-Filtered Exhaustive Scan with Temporal Chunking

System 2 is the new path. It is O(candidates) × chunk_scoring, not O(store_size) × rerank. Given a ~4450-note store, the target budget is **p95 ≤ 800ms** with no LLM calls (synthesis happens outside `recall()`).

#### Pipeline

```
QueryProfile ──────────────────────────────┐
                                           v
                         1. CandidateFilter.select()
                            ├── Entity-index expansion
                            │     (all notes mentioning any resolved entity
                            │      OR any 1-hop neighbor entity)
                            ├── Time-window expansion
                            │     (if temporal markers: all notes in window)
                            ├── Domain filter (if domain specified)
                            └── Vector top-N fallback (N=200) for coverage
                                           |
                                           v
                        candidate notes (target: 200–500)
                                           |
                                           v
                         2. TemporalChunker.bucket()
                            ├── Sort by created_at
                            └── Group into buckets (hourly | daily | weekly)
                                           |
                                           v
                             list[TemporalChunk]
                                           |
                                           v
                         3. ChunkScorer.score_chunks()
                            For each chunk:
                              coverage:   entities matched / total query entities
                              density:    query-entity mentions / chunk size
                              causal:     causal edges crossing chunk boundary
                              centrality: graph PageRank of chunk entities
                              recency:    time-decay relative to newest note
                            score = w1*coverage + w2*density + w3*causal
                                  + w4*centrality + w5*recency
                                           |
                                           v
                         4. Select top-M chunks (default 5)
                                           |
                                           v
                         5. Within-chunk note ranking
                            ├── Cross-encoder rerank on top-M chunks only
                            └── Flatten, dedupe, cap at k
                                           |
                                           v
                                results: list[MemoryNote]
```

#### CandidateFilter

The pre-filter is the single most important component. A naive `store.iterate_notes()` over 4450 notes reading content and extracting entities per note would bust the latency budget. The filter uses existing indexes to narrow to the 200–500 notes most likely to be relevant.

```python
# src/zettelforge/retrieval/system2.py

class CandidateFilter:
    """
    Narrow the store to ~200–500 candidate notes using existing indexes.
    No full-text scan. No LLM calls.
    """

    def __init__(self, memory_manager, max_candidates: int = 500):
        self._mm = memory_manager
        self._max_candidates = max_candidates

    def select(
        self,
        profile: QueryProfile,
        domain: Optional[str],
    ) -> list[MemoryNote]:
        candidates: dict[str, MemoryNote] = {}  # id -> note, dedup by id

        # Path 1: Entity-index expansion (fastest, highest precision)
        for etype, values in profile.resolved_entities.items():
            for v in values:
                if not v:
                    continue
                for note in self._mm.recall_entity(etype, v, k=50):
                    candidates[note.id] = note

        # Path 2: 1-hop neighbor entities via knowledge graph
        #   For each query entity, pull notes that mention directly-linked
        #   entities. This is what lets multi-hop questions find the middle
        #   hop that the query doesn't name explicitly.
        if profile.has_multi_hop_markers or profile.intent in (
            QueryIntent.RELATIONAL, QueryIntent.CAUSAL,
        ):
            for etype, values in profile.resolved_entities.items():
                for v in values:
                    neighbor_notes = self._mm.store.get_entity_neighbors(
                        etype, v, hop=1, max_notes=100,
                    )
                    for note in neighbor_notes:
                        candidates[note.id] = note

        # Path 3: Time-window expansion for temporal queries
        if profile.has_temporal_span:
            window = self._extract_time_window(profile.query)
            if window:
                start, end = window
                for note in self._mm.store.iterate_notes_in_range(start, end):
                    candidates[note.id] = note

        # Path 4: Vector top-N fallback for coverage
        #   Always run. Catches notes that don't share an entity literal but
        #   are semantically related (e.g., paraphrased TTPs).
        vector_hits = self._mm.retriever.retrieve(
            query=profile.query, domain=domain, k=200, include_links=True,
        )
        for note in vector_hits:
            candidates[note.id] = note

        # Domain filter (if specified)
        if domain:
            candidates = {
                nid: n for nid, n in candidates.items()
                if (n.metadata.domain or "") == domain
            }

        # Cap at max_candidates (keep most recent on overflow)
        if len(candidates) > self._max_candidates:
            ranked = sorted(
                candidates.values(),
                key=lambda n: n.created_at or "",
                reverse=True,
            )
            return ranked[: self._max_candidates]

        return list(candidates.values())
```

`store.get_entity_neighbors()` and `store.iterate_notes_in_range()` are new thin wrappers on existing SQLite/LanceDB primitives — see *Implementation Plan / Phase 2*.

#### TemporalChunker

```python
class TemporalChunker:
    """
    Group candidate notes into time buckets.

    Bucket size is chosen based on the query's temporal span:
      - No temporal markers, default          → daily
      - "over time" / "evolved" (span markers) → weekly
      - Explicit date range < 7 days          → hourly
    """

    def bucket(
        self, notes: list[MemoryNote], profile: QueryProfile
    ) -> list[TemporalChunk]:
        bucket_size = self._choose_bucket_size(profile)
        chunks: dict[str, list[MemoryNote]] = {}
        for note in notes:
            if not note.created_at:
                continue
            key = self._bucket_key(note.created_at, bucket_size)
            chunks.setdefault(key, []).append(note)
        return [
            TemporalChunk(key=k, notes=sorted(v, key=lambda n: n.created_at))
            for k, v in sorted(chunks.items())
        ]
```

#### ChunkScorer

The scoring step is where "collectively true, individually weak" patterns get caught. A single note that mentions "APT28" with similarity 0.42 is below System 1's reranker cutoff — but a chunk containing five such notes over a 2-day window, with a causal edge to a CVE referenced in the query, scores high at the chunk level.

```python
class ChunkScorer:
    """
    Score chunks by how well they cover the query, not individual notes.
    Weights are tunable via config.
    """

    DEFAULT_WEIGHTS = {
        "coverage": 0.30,    # fraction of query entities found in chunk
        "density":  0.20,    # entity mentions / chunk size
        "causal":   0.20,    # causal edges crossing chunk boundary
        "centrality": 0.15,  # PageRank of chunk's entities in KG
        "recency":  0.15,    # time-decay against newest candidate
    }

    def score_chunks(
        self,
        chunks: list[TemporalChunk],
        profile: QueryProfile,
        weights: dict[str, float] | None = None,
    ) -> list[tuple[TemporalChunk, float, dict]]:
        w = weights or self.DEFAULT_WEIGHTS
        scored = []
        newest = max((c.notes[-1].created_at for c in chunks if c.notes), default=None)

        for chunk in chunks:
            components = {
                "coverage":   self._coverage(chunk, profile),
                "density":    self._density(chunk, profile),
                "causal":     self._causal(chunk, profile),
                "centrality": self._centrality(chunk, profile),
                "recency":    self._recency(chunk, newest),
            }
            total = sum(w[k] * v for k, v in components.items())
            scored.append((chunk, total, components))

        scored.sort(key=lambda t: t[1], reverse=True)
        return scored
```

The five sub-scores use only cached data:
- **coverage / density**: entity extractor is run once per candidate note during filter (cached on `QueryProfile._entity_cache`). No re-extraction during scoring.
- **causal**: `store.get_causal_edges()` scoped to chunk's entities. Already used by System 1.
- **centrality**: Degree centrality (not full PageRank) as a cheap proxy — `store.get_entity_degree(etype, value)` is O(1) via SQLite index.
- **recency**: Pure arithmetic on timestamps.

#### Within-Chunk Reranking

After the top-M chunks are selected (default M=5), the cross-encoder reranker runs on **only those notes**. This keeps reranker cost bounded even as candidate count grows: 5 chunks × ~20 notes each = 100 rerank pairs, same order of magnitude as System 1's reranker call.

### Upgrade Path: System 1 → System 2

The initial gate decision is conservative — prefer System 1 when unsure. A second check fires after System 1 completes:

```python
# In recall()
if decision.depth == Depth.SYSTEM_1:
    results, meta = system1.retrieve(profile, ...)
    if decision.upgrade_eligible and gate.should_upgrade(
        profile, meta.get("top_vector_score"), len(results),
    ):
        _logger.info("system1_upgraded_to_system2",
                     reason_system1=decision.reasons,
                     top_score=meta.get("top_vector_score"))
        results, _ = system2.retrieve(profile, ...)
```

The upgrade adds worst-case latency of `System 1 + System 2`. That is accepted because:
- Upgrade fires only when `upgrade_eligible` was set (score ≥ 0.4, so already "borderline").
- Upgrade fires only when System 1 actually returned a weak signal.
- The alternative is shipping a wrong answer at System 1 latency, which is worse.

Config caps the upgrade with `max_upgrade_rate` — if > X% of queries upgrade in a rolling window, raise the gate threshold automatically. This is a runtime safety valve for pathologically mis-tuned deployments.

### Modified `recall()`

The public signature is unchanged. The body becomes a short dispatch:

```python
def recall(
    self,
    query: str,
    domain: Optional[str] = None,
    k: int = 10,
    include_links: bool = True,
    exclude_superseded: bool = True,
    include_expired: bool = False,
) -> List[MemoryNote]:
    request_id = uuid.uuid4().hex
    start = time.perf_counter()
    self.stats["retrievals"] += 1

    profile = QueryProfile.build(
        query,
        intent_classifier=get_intent_classifier(),
        entity_extractor=self.indexer.extractor,
        alias_resolver=self.resolver,
    )

    gate = get_quality_gate()   # singleton, config-driven
    decision = gate.route(profile)

    if decision.depth == Depth.SYSTEM_2:
        results, _ = self._system2.retrieve(
            profile, domain, k, include_links, exclude_superseded, include_expired,
        )
    else:
        results, meta = self._system1.retrieve(
            profile, domain, k, include_links, exclude_superseded, include_expired,
        )
        if decision.upgrade_eligible and gate.should_upgrade(
            profile, meta.get("top_vector_score"), len(results),
        ):
            results, _ = self._system2.retrieve(
                profile, domain, k, include_links, exclude_superseded, include_expired,
            )
            decision = GateDecision(
                Depth.SYSTEM_2, decision.score,
                decision.reasons + ["upgraded_post_system1"], False,
            )

    duration_ms = (time.perf_counter() - start) * 1000
    log_api_activity(
        operation="recall",
        status_id=STATUS_SUCCESS,
        query=query[:200],
        domain=domain,
        k=k,
        result_count=len(results),
        duration_ms=duration_ms,
        request_id=request_id,
        gate_depth=decision.depth.value,
        gate_score=round(decision.score, 3),
        gate_reasons=decision.reasons,
    )
    return results
```

### Config Schema

```yaml
# config.default.yaml — new section

recall:
  depth_routing:
    # Master switch. When false, recall() runs System 1 only (current behavior).
    enabled: true

    quality_gate:
      # Threshold for routing to System 2. Range [0.0, 1.0].
      # Lower = more queries go to System 2 (higher recall, higher latency).
      # Higher = more queries stay on System 1 (lower latency, possible misses).
      # Default 0.7 targets ~3–5% System 2 rate on CTI workloads.
      system2_threshold: 0.7

      # After System 1 completes, if top vector score is below this floor,
      # upgrade to System 2. Range [0.0, 1.0]. Set 0.0 to disable upgrades.
      system1_confidence_floor: 0.4

      # Max fraction of queries allowed to upgrade in a rolling 100-query
      # window. Protects against pathological threshold settings. 0.0 disables.
      max_upgrade_rate: 0.15

    system2:
      # Upper bound on candidates passed to chunk scoring.
      max_candidates: 500

      # Chunk bucket size. "auto" picks based on query temporal markers.
      # Explicit values: "hourly" | "daily" | "weekly"
      chunk_size: auto

      # Top-M chunks whose notes are passed to the reranker.
      max_chunks: 5

      # Chunk scoring weights (must sum to 1.0; validated at load).
      chunk_weights:
        coverage:   0.30
        density:    0.20
        causal:     0.20
        centrality: 0.15
        recency:    0.15
```

### File Layout

```
src/zettelforge/
  memory_manager.py                    # MODIFIED — recall() becomes a dispatcher
  query_profile.py                     # NEW — QueryProfile dataclass + build()
  query_markers.py                     # NEW — compiled regex marker sets
  quality_gate.py                      # NEW — QualityGate, Depth, GateDecision
  retrieval/                           # NEW package
    __init__.py
    system1.py                         # NEW — System1Retriever (lifted from recall())
    system2.py                         # NEW — System2Retriever + CandidateFilter
                                       #       + TemporalChunker + ChunkScorer
  storage_backend.py                   # MODIFIED — new primitives (see below)
  sqlite_backend.py                    # MODIFIED — implement new primitives
config.default.yaml                    # MODIFIED — new recall.depth_routing section
tests/
  test_query_profile.py                # NEW
  test_query_markers.py                # NEW
  test_quality_gate.py                 # NEW — routing decision truth table
  test_system1_parity.py               # NEW — System 1 output == current recall()
  test_system2_candidate_filter.py     # NEW
  test_system2_chunk_scoring.py        # NEW
  test_recall_depth_routing.py         # NEW — end-to-end
benchmarks/
  bench_depth_routing.py               # NEW — CTI + LOCOMO with/without routing
```

### New Storage Primitives

System 2 requires two new read primitives on the storage backend:

```python
# src/zettelforge/storage_backend.py (interface)

def get_entity_neighbors(
    self, etype: str, evalue: str, hop: int = 1, max_notes: int = 100,
) -> list[MemoryNote]:
    """Notes mentioning any entity 1-hop-linked to (etype, evalue) in the KG."""

def iterate_notes_in_range(
    self, start: str, end: str,
) -> Iterator[MemoryNote]:
    """Notes with created_at in [start, end]. Uses existing created_at index."""

def get_entity_degree(self, etype: str, evalue: str) -> int:
    """Number of edges incident on (etype, evalue). Used for centrality score."""
```

All three are thin SQLite queries on existing indexes. No schema migrations required.

## Implementation Plan

### Phase 1: QueryProfile + Gate infrastructure (non-breaking)

Build the feature bundle and the gate. Do **not** wire them into `recall()` yet — they are testable in isolation.

**Files created:**
- `src/zettelforge/query_profile.py`
- `src/zettelforge/query_markers.py`
- `src/zettelforge/quality_gate.py`
- `tests/test_query_profile.py`
- `tests/test_query_markers.py`
- `tests/test_quality_gate.py`

**Validation:**
- Marker regexes have unit tests per pattern.
- `QualityGate.route()` has a truth table covering every signal combination that produces a different decision.
- Benchmark: `QueryProfile.build()` p95 < 3ms on CTI query suite.

### Phase 2: System 1 extraction + storage primitives (non-breaking)

Lift the current `recall()` body into `System1Retriever`. Behavior is identical. Add the three new storage primitives.

**Files created:**
- `src/zettelforge/retrieval/__init__.py`
- `src/zettelforge/retrieval/system1.py`
- `tests/test_system1_parity.py`

**Files modified:**
- `src/zettelforge/memory_manager.py` — `recall()` delegates to `System1Retriever`; `QueryProfile` computed once at entry.
- `src/zettelforge/storage_backend.py` — add interface methods.
- `src/zettelforge/sqlite_backend.py` — implement `get_entity_neighbors`, `iterate_notes_in_range`, `get_entity_degree`.
- `src/zettelforge/memory_store.py` — same three methods for LanceDB-backed path.

**Validation:**
- `test_system1_parity.py` replays the CTI benchmark queries and asserts output equality with git HEAD before Phase 2.
- CTI p50 within ±10% of baseline (111ms → expect 105–120ms).
- LOCOMO p95 within ±10% of baseline.
- All existing tests pass unchanged.

### Phase 3: System 2 path

Build `CandidateFilter`, `TemporalChunker`, `ChunkScorer`, `System2Retriever`. Gate remains off — System 2 is reachable only by explicit `gate.enabled=false` + call-site override in tests.

**Files created:**
- `src/zettelforge/retrieval/system2.py`
- `tests/test_system2_candidate_filter.py`
- `tests/test_system2_chunk_scoring.py`
- `benchmarks/bench_depth_routing.py`

**Validation:**
- `CandidateFilter` output size stays within `[20, max_candidates]` on CTI + LOCOMO corpora.
- `ChunkScorer` unit tests for each sub-score (coverage, density, causal, centrality, recency) with synthetic chunks.
- Benchmark: System 2 p95 < 800ms on ~4450-note store.
- LOCOMO accuracy on System 2 only: target ≥ +10 points over System 1 on the multi-hop subset.

### Phase 4: Wire the gate into `recall()`

Gate routes queries. Upgrade path active. Ship behind `recall.depth_routing.enabled: false` by default for the first minor release so existing deployments see zero change.

**Files modified:**
- `src/zettelforge/memory_manager.py` — final `recall()` body as shown above.
- `config.default.yaml` — add `recall.depth_routing` section (disabled).
- `tests/test_recall_depth_routing.py` — end-to-end tests of routing, upgrade, and metadata fields.

**Validation:**
- With `enabled: false`, output is bit-identical to Phase 2 baseline (no regression).
- With `enabled: true`, CTI accuracy ≥ 75% (no regression), LOCOMO accuracy materially improves.
- Structured logs include `gate_depth`, `gate_score`, `gate_reasons` on every `recall()` call.

### Phase 5: Flip default, tune thresholds, publish dashboards

After two weeks of telemetry on opt-in deployments, flip the default in `config.default.yaml` to `enabled: true`. Publish a recall-routing dashboard showing System 1 vs System 2 ratios, upgrade rates, and latency percentiles per bucket.

## Migration

### Existing users on default config

**No changes required for v2.3.0.** Default ships with `recall.depth_routing.enabled: false`. `recall()` behavior is bit-identical to current code because it delegates to `System1Retriever`, whose body is the current `recall()` body.

### Users who opt in (v2.3.0+)

Set `recall.depth_routing.enabled: true` in `config.yaml`. No code changes. Queries begin routing; metadata fields `gate_depth`, `gate_score`, `gate_reasons` appear in structured logs.

### Users on the flipped default (v2.4.0+)

No changes required. To revert to pre-routing behavior, set `enabled: false`.

### Callers of `recall()`

**Zero signature changes.** `recall(query, domain, k, include_links, exclude_superseded, include_expired)` is preserved exactly. Return type is unchanged (`List[MemoryNote]`).

### Callers of `intent_classifier.py` / `blended_retriever.py` directly

**Zero changes.** Both modules are read by `QueryProfile.build()` and `System1Retriever` respectively. Their public APIs are not modified.

## Alternatives Considered

**Alternative 1: LLM-based router.** Send the query to the LLM with a prompt asking "System 1 or System 2?". Rejected because: (a) adds 300–500ms to every query on the Qwen2.5-3B/DGX Spark default — System 1 CTI p50 is 111ms, so the router alone costs 3–5× the work it routes; (b) non-deterministic — identical query may route differently on retry; (c) LLM-free fast path is an explicit constraint of this RFC; (d) the signals the LLM would use are the same features the deterministic gate already reads.

**Alternative 2: Learned router (small classifier).** Train a logistic regression or small MLP on labeled (query, correct_depth) pairs. Rejected for v2.3.0 because: (a) no labeled dataset exists today — bootstrapping requires the deterministic gate to generate training data first; (b) the deterministic gate is inspectable and debuggable in a way a learned model is not; (c) a learned router is a valid follow-up RFC once telemetry accumulates.

**Alternative 3: Always-System-2.** Skip the gate entirely, route everything through the exhaustive path. Rejected because: (a) System 2 p95 target is 800ms; System 1 CTI p50 is 111ms — forcing everything through System 2 is a 7× latency regression on the dominant query class; (b) D-Mem explicitly shows that ~97% of queries don't benefit from System 2; (c) reranker cost grows with chunk count.

**Alternative 4: Depth as an argument to `recall()`.** Let callers pass `depth="deep"` explicitly. Rejected as the **only** mechanism because: (a) agents calling `recall()` programmatically don't know when depth is warranted; (b) it pushes the decision back onto the caller who has less context than the gate; (c) an optional `depth_override` parameter is a reasonable addition later (deferred to Open Questions) but it cannot be the primary routing mechanism.

**Alternative 5: Graph depth expansion inside System 1 instead of a separate System 2.** Increase graph traversal depth from 2 to 3–4 for CAUSAL/RELATIONAL intents. Rejected because: (a) traversal cost is exponential in depth; depth 4 on 2-entity queries on this KG explodes to 10K+ visited nodes; (b) doesn't address the "collectively true, individually weak" pattern — top-k truncation still drops the answer; (c) temporal chunk scoring is fundamentally different from graph traversal and solves different failure modes.

**Alternative 6: Use `consolidation.py`'s EPG/TAN tier as the routing signal.** Route queries hitting EPG notes to fast path, queries touching TAN to deep path. Rejected because tier correlates with note stability, not query complexity — a multi-hop question can easily span both tiers, and single-entity factual questions on long-stable TAN entities shouldn't pay System 2 cost.

## Open Questions

1. **Should `recall()` expose a `depth_override` parameter for power callers?**
   Arguments for: lets an agent that already knows it's running a multi-hop synthesis prompt force System 2 without gate heuristics. Arguments against: callers don't have a systematic way to decide; the gate is supposed to be the decision-maker. **Proposal: defer to v2.4.0**, introduce as `depth: Optional[Literal["system_1", "system_2"]] = None` — None uses the gate, explicit value bypasses.

2. **Chunk bucket auto-sizing — is daily the right default?**
   With ~4450 notes accumulated over the measurement period, daily buckets give roughly O(20–50 notes/bucket), which is within reranker budget. But for heavier ingest rates (thousands of notes per day), daily buckets blow up. **Proposal: `chunk_size: auto` dynamically picks based on candidate count** — `candidates / target_notes_per_bucket` where `target_notes_per_bucket = 25`.

3. **Centrality approximation — is degree centrality enough, or do we need incremental PageRank?**
   Degree is O(1) via SQLite index. PageRank requires traversal and caching. For CTI where a handful of high-degree entities (e.g., "Windows", "PowerShell") would otherwise dominate every chunk's score, degree may over-reward them. **Proposal: start with degree, measure in Phase 3 benchmarks, add normalized degree or partial PageRank only if the centrality component is observably misbehaving.**

4. **How should the gate behave when `intent_confidence` comes from the LLM fallback (300–500ms)?**
   Today `intent_classifier.py` only runs the LLM when keywords are ambiguous AND `use_llm_fallback=True`. The gate reads `intent_method` — if `"llm"`, the classification already paid LLM cost, but downstream latency budget is tighter. **Proposal: when `intent_method == "llm"`, bias toward System 1 by subtracting 0.10 from the gate score** — the ambiguity that forced LLM fallback is already reflected in the `is_ambiguous` signal, and we don't want to double-pay.

5. **Should the reranker run on System 2 chunk selection, or only on the final within-chunk notes?**
   Running the reranker between chunks (cross-encoder on concatenated chunk text) could improve chunk ordering but is expensive. **Proposal: reranker runs only within selected top-M chunks.** Chunk ordering is owned by `ChunkScorer`; reranker ordering is owned by per-note relevance. These are different concerns and mixing them is a regression risk.

6. **Telemetry: should gate decisions feed a training dataset for the learned-router follow-up?**
   Yes — but this requires writing the outcome (user satisfaction, downstream accuracy proxy) back to a store, which is out of scope for this RFC. **Proposal: `gate_score`, `gate_reasons`, and `gate_depth` are logged structurally; a later RFC defines the ground-truth capture mechanism.**

7. **Does the upgrade path risk a latency pathology on specific query shapes?**
   Worst case: a query that scores 0.6 (System 1), returns 2 results with top score 0.35 (triggers upgrade), then runs System 2. Total latency = System 1 + System 2 ≈ 150 + 800 = 950ms. **Mitigation: `max_upgrade_rate` caps upgrade frequency; deployments that see chronic upgrades should lower `system2_threshold` so the gate sends those queries to System 2 directly on the first pass.**

## Rollout Strategy

1. **Phase 1** (v2.3.0-alpha) — `QueryProfile`, markers, and `QualityGate` land. Not wired in. Dev-only.
2. **Phase 2** (v2.3.0-beta) — `System1Retriever` extraction. `recall()` delegates. Parity tests must pass. Ship to internal users.
3. **Phase 3** (v2.3.0-rc) — `System2Retriever` lands. Reachable via explicit test hooks. Benchmark suite compares System 1 vs System 2 vs combined.
4. **Phase 4** (v2.3.0) — Gate wired in. Ships disabled by default. Public release. Users can opt in.
5. **Phase 5** (v2.4.0) — Based on two weeks of opt-in telemetry, flip default to `enabled: true`. Publish tuning guide + dashboard. Address `depth_override` (Open Question 1) if demand confirms.
6. **Phase 6** (v2.5.0+) — Consider learned-router follow-up RFC once enough labeled routing data exists.

Each phase is independently shippable. If Phase 3 shows that System 2 doesn't meet its latency budget, Phases 1–2 still deliver value (cleaner architecture, future-proofed `recall()`, a tested gate component ready for a different deep-path implementation).

## Decision

- **Status**: Draft — awaiting adversarial review
- **Date**: 2026-04-16
- **Decision Maker**: Patrick Roland
- **Rationale**: Current uniform-depth `recall()` sacrifices latency on the 97% of queries that don't need it and caps accuracy on the 3% that do. D-Mem's Quality Gate pattern is directly applicable and the required primitives (intent classification, entity extraction, vector top-N, KG traversal, cross-encoder rerank) all already exist in ZettelForge. The deterministic, LLM-free gate satisfies the Qwen2.5-3B/DGX Spark default-provider constraint. System 1 being a verbatim lift of the current pipeline makes rollback a one-line config change.
