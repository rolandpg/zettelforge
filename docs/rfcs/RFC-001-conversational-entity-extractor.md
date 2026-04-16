# RFC-001: Conversational Entity Extractor

## Metadata

- **Author**: Patrick Roland
- **Status**: Partially Implemented (LLM NER built but not wired into ingest path)
- **Created**: 2026-04-09
- **Last Updated**: 2026-04-16
- **Reviewers**: Solo dev (self-approved); Backend architect adversarial review 2026-04-16 (2 blockers, 7 warnings)
- **Related Tickets**: LOCOMO benchmark improvement
- **Related RFCs**: RFC-002 (Universal LLM Provider Interface — depends on `generate()` stability)

## Summary

Replace the regex-based CTI-only entity extractor with an LLM-powered NER pipeline that recognizes conversational entities (persons, locations, organizations, events, activities, temporal references). This enables the knowledge graph to index and traverse the entity types present in the LOCOMO benchmark, targeting 80%+ overall accuracy (up from 15%).

## Motivation

LOCOMO benchmark results at 15% overall accuracy trail the leaderboard by 4x. Root cause analysis (BENCHMARK_REPORT.md) identifies entity extraction mismatch as the #1 blocker: ZettelForge only recognizes CVEs, APT groups, tools, and campaigns. LOCOMO conversations contain person names, locations, hobbies, life events, and temporal references -- all invisible to the current `EntityExtractor`.

RAGAS data confirms retrieval finds the right documents (75.9% keyword presence) but the graph retrieval path is dead for LOCOMO queries because no recognized entities match. The keyword-overlap judge scores low because retrieved context is long and unfocused -- entity-indexed graph traversal would both boost relevant results and filter noise.

The gap between keyword presence (75.9%) and answer accuracy (15%) also indicates the answer extraction pipeline needs improvement. Adding conversational entities to the graph enables multi-hop traversal which directly addresses the 0% multi-hop and 0% temporal scores.

## Current Status

### What shipped (v2.0.0 -- v2.2.0)

| Component | Status | Notes |
|---|---|---|
| Step 1: EntityExtractor as single source of truth | Complete | `NoteConstructor.extract_entities()` delegates to `EntityExtractor` |
| Step 2: LLM-based NER extraction | **Built but NOT WIRED IN** | `extract_llm()` exists with retry logic, but `use_llm=True` is never called by any code path. `remember()`, `build()`, and `NoteConstructor` all use `use_llm=False` (default). LLM NER is dead code. |
| Step 3: Expanded entity index + knowledge graph | Complete | 19 entity types (13 regex, 6 LLM). `EntityIndexer` with deferred flush |
| Step 4: Benchmark answer extraction (SynthesisGenerator) | Not started | Raw context still returned as answer in `locomo_benchmark.py` |
| Step 5: Tests and benchmark validation | Partial | 23 unit tests passing (not 18 as previously stated). LOCOMO at 22%, not 80%. No tests for IOC regex, hash false-positive filter, remove_note, search_entities, or flush timing. |
| Async batching for production NER | Not started | Open question from original RFC |
| SQLite entity_index table | Shipped (v2.2.0) | Dual storage: `entity_index.json` (JSONL legacy) + SQLite `entity_index` table |

### LOCOMO benchmark trajectory

| Version | Score | Key change |
|---|---|---|
| v1.5.0 | 15% | Baseline (regex-only CTI entities) |
| v2.0.0 | 18% | Conversational entity extraction added |
| v2.1.1 | 22% | Supersession perf fix, background enrichment, Ollama cloud judge |

Target was 80%. Actual is 22%. See Lessons Learned for analysis.

## Proposed Design

### Architecture Changes

**Replace regex-based `EntityExtractor` with hybrid regex+LLM NER.** The original `entity_indexer.py` used 4 hardcoded regex patterns. The new implementation uses the existing `llm_client.py` to extract typed entities from any text, with regex as a fast-path for CTI entities and IOCs.

**Unified entity schema** across `entity_indexer.py` and `note_constructor.py`. `EntityExtractor` is the single source of truth -- `NoteConstructor.extract_entities()` delegates to it:

```python
# note_constructor.py
def extract_entities(self, text: str) -> Dict[str, List[str]]:
    from zettelforge.entity_indexer import EntityExtractor
    extractor = EntityExtractor()
    return extractor.extract_all(text)
```

**19 entity types** (expanded from the originally proposed 10):

| Category | Types | Extraction method |
|---|---|---|
| CTI | `cve`, `intrusion_set`, `actor`, `tool`, `campaign`, `attack_pattern` | Regex |
| IOC (STIX Cyber Observables) | `ipv4`, `domain`, `url`, `md5`, `sha1`, `sha256`, `email` | Regex |
| Conversational | `person`, `location`, `organization`, `event`, `activity`, `temporal` | LLM NER (+ regex fallback for person and location) |

The IOC types were not in the original RFC but were added during implementation to support CTIBench and real-world CTI workflows.

### Regex Patterns (Implemented)

All regex patterns are compiled class-level constants on `EntityExtractor.REGEX_PATTERNS`:

```python
REGEX_PATTERNS: Dict[str, re.Pattern] = {
    "cve": re.compile(r"(CVE-\d{4}-\d{4,})", re.IGNORECASE),
    "intrusion_set": re.compile(r"\b((?:apt|unc|ta|fin|temp)\s*-?\s*\d+)\b", re.IGNORECASE),
    "actor": re.compile(r"\b(lazarus|sandworm|volt\s+typhoon)\b", re.IGNORECASE),
    "tool": re.compile(r"\b(cobalt\s+strike|metasploit|mimikatz|bloodhound|dropbear|empire|covenant)\b", re.IGNORECASE),
    "campaign": re.compile(r"\b(operation\s+\w+)\b", re.IGNORECASE),
    "attack_pattern": re.compile(r"\bT\d{4}(?:\.\d{3})?\b"),
    "ipv4": re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"),
    "domain": re.compile(r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+(?:com|net|org|...)\b"),
    "url": re.compile(r"https?://[^\s<>\"')\]]+"),
    "md5": re.compile(r"\b[a-fA-F0-9]{32}\b"),
    "sha1": re.compile(r"\b[a-fA-F0-9]{40}\b"),
    "sha256": re.compile(r"\b[a-fA-F0-9]{64}\b"),
    "email": re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
}
```

Additionally, two regex patterns handle conversational entities without LLM:
- `_PERSON_PATTERN`: Matches dialogue format `Name: text` with a stopword filter (40+ common words and day/month names excluded).
- `_LOCATION_PATTERN`: Matches 40+ major world cities by name.

### False Positive Hash Filter (`_CODE_CONTEXT_PATTERN`)

Hash IOCs (`md5`, `sha1`, `sha256`) match any 32/40/64-character hex string, producing false positives on git commit SHAs, variable assignments, and code fences. The `_CODE_CONTEXT_PATTERN` is a compiled `re.VERBOSE` regex that detects lines containing code or VCS context:

```python
_CODE_CONTEXT_PATTERN = re.compile(r"""
    (?:
        [a-zA-Z_]\w*\s*=\s*["']?[a-fA-F0-9]{32,64}   # var = hash (assignment)
      | \bcommit\s+[a-fA-F0-9]{7,40}\b                # git commit entry
      | \bmerge\s+[a-fA-F0-9]{7,40}\b                 # git merge line
      | \btree\s+[a-fA-F0-9]{7,40}\b                  # git tree line
      | \bparent\s+[a-fA-F0-9]{7,40}\b                # git parent line
      | \bAuthor:\s                                    # git log header
      | ```                                            # code fence marker
      | \bdef\s+\w                                     # function definition
      | [a-zA-Z_]\w*\([^)]*[a-fA-F0-9]{32,64}        # function call with hash arg
    )
""", re.VERBOSE | re.IGNORECASE)
```

The filter works per-line: for each line in the source text that matches `_CODE_CONTEXT_PATTERN`, every hex string on that line is added to a false-positive set. Hash candidates are then excluded if they appear in that set. This avoids per-match lookahead assertions and keeps the main hash regex simple.

```python
def _filter_false_positive_hashes(self, candidates: List[str], text: str) -> List[str]:
    fp_hashes: Set[str] = set()
    for line in text.splitlines():
        if self._CODE_CONTEXT_PATTERN.search(line):
            for m in re.finditer(r"\b[a-fA-F0-9]{32,64}\b", line):
                fp_hashes.add(m.group(0).lower())
    return [c for c in candidates if c.lower() not in fp_hashes]
```

### LLM NER Pipeline (Implemented)

**System prompt** (exact text used in production):

```
You are a named entity recognizer. Extract entities from the text.
Return ONLY a JSON object with these keys:
person, location, organization, event, activity, temporal.
Each key maps to a list of strings.
Use empty lists for types not found. Example: {"person": ["Alice"],
"location": ["Paris"], "organization": [], "event": ["birthday party"],
"activity": ["swimming"], "temporal": ["last Tuesday"]}
```

**User prompt** construction:

```python
prompt = f"Extract named entities from this text:\n\n{text[:2000]}\n\nJSON:"
```

Text is truncated to 2000 characters to stay within context budgets for small models. `max_tokens=300`, `temperature=0.0`.

**Retry logic for JSON parse failures:**

1. First attempt: call `generate()` with `temperature=0.0`, parse output with `extract_json(output, expect="object")`.
2. If parse fails and output is non-empty: retry with `temperature=0.3`, `json_mode=True`, appending `"\n\nRespond with valid JSON only."` to the prompt.
3. If retry also fails: log warning, return empty entity dict.

On total exception (LLM unavailable, network error): catch-all returns empty entity dict with `exc_info=True` logging.

**Normalization** (`_parse_ner_output_from_parsed`):

- Each expected type is extracted from the parsed JSON with `parsed.get(etype, [])`.
- Values are filtered: must be `str`, non-empty after strip, length > 1 character.
- All values are lowercased and stripped.
- Duplicates removed via `set()`.
- Missing types get empty lists.

### EntityIndexer Persistence (Implemented)

`EntityIndexer` maintains an inverted index mapping `{entity_type -> {entity_value -> Set[note_id]}}`.

**Storage**: JSON file at `<data_dir>/entity_index.json` using `fcntl.flock(LOCK_EX)` for concurrent-process safety. (As of v2.2.0, the SQLite backend also has an `entity_index` table -- see Dual Storage below.)

**Deferred flush**: Writes are batched via a 5-second `threading.Timer`. After `add_note()` or `remove_note()`, the index is marked dirty and a daemon timer is scheduled. If no timer is already running, a new one fires in 5 seconds to call `_flush_sync()`. The `atexit` handler ensures a final flush on process exit.

```python
def _schedule_flush(self) -> None:
    with self._flush_lock:
        if self._flush_timer is None or not self._flush_timer.is_alive():
            self._flush_timer = threading.Timer(5.0, self._flush_sync)
            self._flush_timer.daemon = True
            self._flush_timer.start()
```

**`build()` method**: Full reindex. Iterates all notes via `MemoryStore.iterate_notes()`, extracts entities with `extract_all()` (regex-only, no LLM), adds each to the index, cancels any pending timer, and flushes immediately. Returns `{"notes_indexed": count, "stats": self.stats()}`.

**`search_entities()` method**: Case-insensitive prefix search across all entity types. For each type, returns entity values whose key starts with the query string, limited to `limit` results per type. Used by `recall_entity()` when the entity type is unknown.

### Dual Storage Situation

As of v2.2.0, entity data lives in two places:

1. **`entity_index.json`** -- The original JSONL/JSON file written by `EntityIndexer.save()` with `fcntl.flock()`. Still the primary store used by `EntityIndexer` at runtime.
2. **SQLite `entity_index` table** -- Written by `SQLiteBackend` as part of the unified storage migration. Used by SQLite-aware code paths.

The `EntityIndexer` class itself still reads/writes the JSON file. The SQLite backend mirrors this data but the two are not kept in sync by a single authoritative writer. This is a known inconsistency that should be resolved by making `EntityIndexer` backend-aware (reading/writing through the `StorageBackend` ABC rather than directly to disk).

### Data Model Changes

Entity index gained new type keys. The `EntityIndexer.index` dict expanded from `{cve, actor, tool, campaign}` to all 19 types listed in `EntityExtractor.ENTITY_TYPES`. Backward-compatible -- old indexes simply lack new keys until rebuilt.

Knowledge graph gained conversational node types. `NoteConstructor._infer_entity_type()` accepts `entity_type_hint` from LLM NER output, trusting the LLM classification for `{person, location, organization, event, activity, temporal}`. CTI types are still inferred from value patterns.

### API Changes

No public API changes. `EntityExtractor.extract_all()` returns `Dict[str, List[str]]` with more keys. The `use_llm` parameter controls whether LLM NER is invoked (default `False` for performance). `MemoryManager.recall_entity()` gains the ability to query by conversational entity types.

### Security Considerations

LLM-generated entity data enters the knowledge graph. Entities are extracted from note content (already governance-validated on input per GOV-011), and entity values are normalized to lowercase strings with no executable content. No new attack surface.

### Observability

Extraction metrics logged via `structlog` (GOV-012 compliant): LLM NER parse failures (`parse_failed`), retry attempts (`retry_parse`), extraction exceptions (`llm_entity_extraction_failed` with `exc_info`). Entity count by type available via `EntityIndexer.stats()`.

## Alternatives Considered

**Alternative 1: More regex patterns for conversational entities.** Rejected -- person names, locations, and events cannot be reliably matched with regex. "Sarah" vs "sarah" vs "SARAH" is tractable but "my friend from college" referring to a person is not. Regex would give maybe 30-40% recall on LOCOMO entities. The implementation does include a limited regex fallback for dialogue-format person names (`Name: text` pattern) and major city names, but these are supplementary to LLM NER, not a replacement.

**Alternative 2: External NER library (spaCy, GLiNER).** Rejected -- adds a heavy dependency (spaCy model ~500MB) or requires a separate model download. The project already has an LLM client; using it for NER keeps the dependency tree minimal and leverages the existing Qwen2.5-3B model.

**Alternative 3: Hybrid approach (LLM NER + regex fast-path).** Selected -- use regex for the CTI types where patterns are reliable (CVE, APT groups, IOCs), and LLM for conversational types where regex fails. Best of both worlds: fast and deterministic for CTI, flexible for everything else.

## Implementation Plan

### Step 1: Refactor EntityExtractor to single source of truth -- COMPLETE

- Removed duplicated patterns from `note_constructor.py`
- `NoteConstructor.extract_entities()` delegates to `EntityExtractor`
- CTI regex preserved as fast-path
- **Files**: `entity_indexer.py`, `note_constructor.py`

### Step 2: Add LLM-based NER extraction -- COMPLETE

- `extract_llm()` method on `EntityExtractor` using `llm_client.generate()`
- NER system prompt extracts: person, location, organization, event, activity, temporal
- Retry on JSON parse failure with `json_mode=True` and elevated temperature
- `_parse_ner_output_from_parsed()` normalization
- **Files**: `entity_indexer.py`

### Step 3: Expand entity index schema and knowledge graph -- COMPLETE

- 19 entity types in `EntityExtractor.ENTITY_TYPES` (up from proposed 10)
- Added 7 IOC regex types not in original proposal: `ipv4`, `domain`, `url`, `md5`, `sha1`, `sha256`, `email`
- Added `attack_pattern` (MITRE ATT&CK TID) regex
- `_infer_entity_type()` accepts `entity_type_hint` for LLM-classified types
- `_CODE_CONTEXT_PATTERN` false positive filter for hash IOCs
- **Files**: `entity_indexer.py`, `note_constructor.py`

### Step 4: Enhance benchmark answer extraction -- NOT STARTED

- `SynthesisGenerator` integration into `locomo_benchmark.py` has not been implemented
- Raw context is still returned as the "answer" in the benchmark pipeline
- This is the primary remaining lever for LOCOMO score improvement
- **Files**: `locomo_benchmark.py`

### Step 5: Tests and benchmark validation -- PARTIAL

- 18 unit tests in `test_conversational_entities.py` passing:
  - `TestRegexExtraction` (5 tests): CVE, actor, tool, campaign, no-match
  - `TestLLMExtraction` (3 tests, CI-skipped): person, location, short-text-empty
  - `TestHybridExtraction` (2 tests, CI-skipped): regex-only CTI, combined types
  - `TestNERParsing` (3 tests): valid JSON, markdown-fenced JSON, empty output
  - `TestNoteConstructorDelegation` (2 tests): delegation wiring
  - `TestInferEntityType` (5 tests): CVE, APT, tool, type hints, unknown
  - `TestEntityIndexerConversational` (3 tests): all types present, add/lookup, cross-type search
- LLM tests gated with `@pytest.mark.skipif(CI)` due to llama-cpp segfault in CI
- LOCOMO benchmark at 22%, not the 80% target. See Lessons Learned.
- **Files**: `tests/test_conversational_entities.py`

## Rollout Strategy

1. Feature branch `feature/RFC-001-conversational-entity-extractor` from `master` -- DONE
2. Steps 1-3 implemented and merged in v2.0.0 -- DONE
3. P0 performance fixes (supersession O(n), file locking) shipped in v2.1.1 -- DONE
4. SQLite backend with entity_index table shipped in v2.2.0 -- DONE
5. Step 4 (SynthesisGenerator in benchmark) -- OUTSTANDING
6. Full benchmark re-run after Step 4 -- OUTSTANDING

## Open Questions

### Resolved

- **Should the LLM NER call be cached per note to avoid re-extraction on rebuild?** Decision: yes, cache in note metadata. Implementation: `build()` uses regex-only extraction (`use_llm=False`) for speed. **CORRECTION (2026-04-16 adversarial review):** The original answer claimed "LLM NER runs at ingest time via `extract_all(use_llm=True)`" — this is false. No code path ever calls `use_llm=True`. `remember()`, `build()`, and `NoteConstructor` all default to `use_llm=False`. LLM NER is implemented but never activated. This is the #1 outstanding item.

- **What's the acceptable latency budget for NER per note?** Current ingestion is 0.4 notes/s. LLM NER adds ~2-3s per call. Decision: acceptable for benchmark; add async batching for production later. Async batching has not been implemented.

### Unresolved

- **Async batching for production NER.** At 2-3s per LLM call, NER is the ingestion bottleneck for batch operations. The `build()` method works around this by using regex-only extraction, but individual `remember()` calls with `use_llm=True` are synchronous and slow. No timeline set.

- **EntityIndexer backend unification.** The dual storage (JSON file + SQLite table) should be resolved by making `EntityIndexer` write through the `StorageBackend` ABC. Currently the JSON file is authoritative at runtime.

## Decision

- **Status**: Partially Implemented
- **Date**: 2026-04-09 (accepted), 2026-04-16 (adversarial review, status corrected)
- **Decision Maker**: Patrick Roland
- **Rationale**: The hybrid LLM+regex approach is the most practical path to improving LOCOMO. The entity type expansion (10 to 19 types) was a natural extension. However, adversarial review revealed that the LLM NER path was never wired into any ingest code path — the feature is built but dormant. Two outstanding items remain: (1) wire `use_llm=True` into the ingest path, (2) implement Step 4 (SynthesisGenerator in benchmark). Additionally, 2 code bugs were fixed: `load()` log event name was wrong, `attack_pattern` regex lacked a capture group.

### Adversarial Review Findings (2026-04-16)

| # | Severity | Finding | Status |
|---|---|---|---|
| 1 | BLOCKER | `use_llm=True` never called — LLM NER is dead code | Documented, fix pending |
| 2 | BLOCKER | `load()` logs `entity_index_save_failed` instead of `load_failed` | **Fixed** in code |
| 3 | WARNING | `attack_pattern` regex lacks capture group | **Fixed** in code |
| 4 | WARNING | `save()` truncates before flock — race condition | Documented, fix pending |
| 5 | WARNING | `remove_note()` deletes entity type keys | Documented, fix pending |
| 6 | WARNING | `_flush_sync()` not thread-safe on `self.index` | Documented, fix pending |
| 7 | WARNING | `extract_all(use_llm=True)` overwrites regex results | Documented, fix pending |
| 8 | WARNING | No tests for IOCs, hash filter, remove_note, search_entities | Documented |
| 9 | WARNING | Root cause analysis omits LLM NER not activated | **Fixed** in RFC (reason #5) |
| 10 | NIT | Test count was 18, actual is 23 | **Fixed** in RFC |

## Lessons Learned

### LOCOMO score: 22%, not 80%

The RFC targeted 80%+ LOCOMO accuracy. After three releases, the score is 22% (up from 15%). The 80% target was overly optimistic for several reasons:

1. **Entity extraction was necessary but not sufficient.** The hypothesis was that adding conversational entities to the knowledge graph would unlock multi-hop and temporal queries. Entity extraction works -- the graph now has person, location, and organization nodes -- but the benchmark's keyword-overlap scoring penalizes long, unfocused retrieved context. Without Step 4 (SynthesisGenerator distilling focused answers from context), the judge sees a wall of text and scores it low even when the answer is present.

2. **The 3B model ceiling.** Qwen2.5-3B produces NER output that is adequate for common entities (person names, well-known locations) but struggles with implicit references ("my friend from college"), abstract events, and temporal reasoning. The LOCOMO benchmark relies heavily on these. Larger models (GPT-4o, Claude) would likely improve NER quality, but the local-first philosophy constrains the default model.

3. **Multi-hop and temporal remain at 0%.** These categories were the primary motivation for RFC-001. Zero improvement after three releases indicates the bottleneck is not entity extraction alone -- it is the lack of multi-hop graph traversal in the benchmark recall path, and the absence of temporal normalization (resolving "last Tuesday" to a date and matching it against stored events).

4. **The move from 15% to 22% came mostly from non-entity improvements.** The 7-point gain was driven by supersession performance fixes (P0-1), file locking correctness (P0-2), ghost row cleanup (P0-4), and switching to an Ollama cloud model for the LLM judge -- not from conversational entity extraction specifically. This suggests the retrieval and scoring pipeline has more low-hanging fruit than entity coverage.

5. **LLM NER was never activated.** (Identified by adversarial review, 2026-04-16.) The `extract_llm()` method exists and works when called directly, but no code path in the codebase passes `use_llm=True` to `extract_all()`. `remember()`, `NoteConstructor`, and `build()` all use the default `use_llm=False`. The conversational entity types (person, location, organization, event, activity, temporal) are populated only by the limited regex fallback patterns — dialogue-format names and 40 hardcoded city names. This means the core value proposition of RFC-001 (LLM-powered NER for LOCOMO) was built but never deployed. Wiring `use_llm=True` into the ingest path is the single highest-priority fix.

### What worked

- **Hybrid regex+LLM design.** Regex fast-path for CTI entities is reliable, fast, and testable without an LLM. The LLM path is cleanly separated and can be improved independently (better model, better prompt, or even swapped for spaCy) without touching CTI extraction.

- **EntityExtractor as single source of truth.** Eliminating pattern duplication between `entity_indexer.py` and `note_constructor.py` prevented divergence and simplified testing.

- **False positive hash filter.** The `_CODE_CONTEXT_PATTERN` approach (per-line context detection rather than per-match lookahead) was the right trade-off. It is easy to extend with new context patterns and does not complicate the core hash regexes.

- **Deferred flush with threading.Timer.** The 5-second write batching significantly reduced I/O during batch ingestion without risking data loss (atexit handler + explicit flush in `build()`).

### What did not work

- **80% target without SynthesisGenerator.** The RFC bundled entity extraction (Steps 1-3) and answer synthesis (Step 4) into one proposal but only Steps 1-3 shipped. The benchmark score improvement was attributed almost entirely to entity work, when in reality it required both. Step 4 should have been a prerequisite, not an afterthought.

- **LLM NER in CI.** The llama-cpp native library segfaults in CI (GitHub Actions), so all LLM extraction tests are skipped. This means the NER pipeline has no automated regression protection. Fixing this requires either a mock-based test strategy or a CI-compatible LLM runtime.

### Recommendations for future work

1. **Implement Step 4 (SynthesisGenerator in benchmark)** -- highest expected impact on LOCOMO score.
2. **Add mock-based NER tests** that exercise `_parse_ner_output_from_parsed()` with realistic LLM output without requiring a live model. The `TestNERParsing` class already does this for parse logic; extend it to cover the full `extract_llm()` path with a mocked `generate()`.
3. **Unify EntityIndexer storage** to write through `StorageBackend` and eliminate the JSON/SQLite dual-write inconsistency.
4. **Evaluate RFC-002 impact** -- once the universal LLM provider ships, re-run LOCOMO with a larger model to measure the NER quality ceiling independent of the 3B model constraint.
