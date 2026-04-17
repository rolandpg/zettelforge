---
title: "Test Suite Audit — Skipped / XFailed / Flaky (Python 3.12)"
date: 2026-04-17
status: shipped
owner: completed via NEXUS sprint
---

# Test Suite Audit — Python 3.12

## Sprint outcome (added 2026-04-17 after NEXUS sprint)

| Item | Status | Landed in |
|------|--------|-----------|
| AI-1 (conversational-entities unskip) | SHIPPED | PR #64 `7fdf013` |
| AI-2 (llm_client split + contract) | SHIPPED | PR #64 `7fdf013` |
| AI-3 (two_phase_e2e generate() audit) | SHIPPED | PR #63 `0136888` |
| AI-4 (xfail fix via prompt-routed mock) | SHIPPED | PR #63 `0136888` |
| AI-5 (get_note_by_id race) | SHIPPED | issue #68, PR #69 (wrap 16 readers in `_write_lock`) |
| AI-6 (test_recall_cve flake) | SHIPPED | PR #65 `af080ec` |
| AI-7 (Pydantic V3 ConfigDict) | SHIPPED | PR #62 `24ca6bd` |
| AI-8 (return→assert in test_causal_extraction) | SHIPPED + REWRITTEN | PR #65 `af080ec`, then properly validated via mock-routed triples + SQLite query in PR #67 `ba558a3` |
| AI-9 (lancedb table_names) | NO-OP | already migrated upstream; residual warning is lancedb-internal |
| AI-10 (fastembed revision pin) | DEFERRED | awaiting decision on revision choice |

Stabilization PR #67 also addressed 3 CI regressions exposed by the sprint merges (weakened causal_extraction assertion, vector_recall_latency race, metadata_fields fuzzy-query ranking miss).

**Net test-suite delta:** `280 passed / 17 skipped / 2 xfailed` → `305 passed / 10 skipped / 0 xfailed / 0 failed` on test-3.12.

---

## Source of truth

CI run `24586625581` (master, commit `3a378c6`), test-3.12 job `71897758930`:

> `280 passed, 17 skipped, 2 xfailed, 7 warnings in 13.13s`

Plus known-flaky tests from the PR #60 first-attempt failure (both passed on rerun, both pre-existing):

- `tests/test_core.py::TestEntityRecall::test_recall_cve_returns_notes`
- `tests/test_memory_updater.py::TestMemoryUpdaterApply::test_apply_delete_marks_superseded`

## Total 16 non-pass outcomes grouped by root cause

| Bucket | Count | Root cause | Fix effort |
|---|---|---|---|
| A. LLM native crash in CI | 5 | `llama-cpp-python` segfaults on GH runner | M — swap to mock provider in CI |
| B. LLM integration needs model/server | 5 | No model or Ollama on CI runners | S — swap to mock provider |
| C. Performance tests off on CI | 4 | Runner hardware variance | — keep skipped, verify locally on cadence |
| D. Two-phase e2e mock drift (xfail) | 2 | Mock `side_effect` length mismatch after `generate()` call-site changes | M — retune mock or switch to recorded fixtures |
| E. Flaky | 2 | Enrichment-queue race + retrieval timing | M — add synchronization point or use `sync=True` |

---

## Action items

### P1 — Convert CI skips that can actually run

Both buckets A and B skip *because* CI can't run a real LLM, but the `mock`
provider from RFC-002 Phase 1 (now shipped in v2.3.0) makes them
runnable. The skip markers were written before the mock provider
existed; they are out of date.

#### AI-1. Rewrite the 5 Category-A tests against the mock provider

- **File:** `tests/test_conversational_entities.py`
- **What:** Remove the `@pytest.mark.skipif(os.environ.get("CI") == "true", ...)` class decorators on `TestLLMExtraction` and `TestHybridExtraction`. Inject the mock provider via a fixture that calls `llm_client.reload()` after setting `ZETTELFORGE_LLM_PROVIDER=mock`, with seeded mock responses that match the assertions (e.g. a "person: Alice, Bob" JSON for the Alice/Bob input).
- **Why:** These tests assert output shape / entity counts, not real model quality. The mock provider produces deterministic output suitable for shape checks.
- **Risk:** Low. The assertions are `len(result.get("person", [])) >= 1` — easy to satisfy with seeded mock data.

#### AI-2. Rewrite the 5 Category-B tests against the mock provider

- **File:** `tests/test_llm_client.py`
- **What:** `TestLocalLLM` class currently exercises `_get_local_llm()` and end-to-end `generate()`. Split it: keep the integration tests skipped in CI (rename class to `TestLocalLLMIntegration` so intent is explicit), and add a new `TestGenerateContract` class that exercises the public `generate()` surface through the mock provider (asserts return type, system-prompt handoff, JSON mode formatting — not real model output).
- **Why:** The public `generate()` API contract should be covered in CI even when no model is present. We currently have zero CI coverage for any path through `llm_client.generate()`.
- **Risk:** Low. The contract tests don't care about model quality.

### P2 — Retire the 2 XFails

Both `test_two_phase_e2e.py` xfails have a stale `xfail` reason:

> "remember_with_extraction calls generate 4x; mock side_effect count and NOOP/UPDATE routing need rework"

This marks broken tests that are being ignored. They were probably
accurate when written but need re-evaluation now that RFC-002 changed the
`generate()` call path.

#### AI-3. Audit the current `remember_with_extraction` call sites for `generate()`

- **File:** `src/zettelforge/memory_manager.py` — search for every call into `llm_client.generate` inside `remember_with_extraction`.
- **What:** Count the actual invocations. Either fix the mock `side_effect` list length, or switch to a `mocker.patch` that returns a fixed value regardless of call count.
- **Why:** XFails that sit for more than one release are waste — they look like test coverage but provide none.

#### AI-4. Decide: fix, delete, or replace with a fixture-recording test

- If the supersession / NOOP routing is still interesting behavior: fix AI-3 and remove the xfail.
- If it's covered by other tests: delete these two and their fixtures.
- If the mock-heavy approach keeps drifting: record real `generate()` outputs once (via the mock-provider harness from AI-2) and replay them. Lowest maintenance path.

### P3 — Stabilize the 2 flaky tests

Both flakes are in the enrichment-queue async write path that landed in
v2.1.1's dual-stream architecture. They pass on rerun.

#### AI-5. `test_apply_delete_marks_superseded` — force-sync the enrichment queue

- **File:** `tests/test_memory_updater.py`
- **Symptom:** `Links(related=[], superseded_by=None, ...)` — the superseded_by field isn't set yet when the assertion runs.
- **Cause:** Enrichment-queue worker hasn't finished dispatching the supersession write before the test reads.
- **Fix:** Add `mm.remember(..., sync=True)` to block until background enrichment completes (the `sync` param already exists per v2.1.1 CHANGELOG). Or call an explicit flush on the enrichment queue at the assertion boundary.

#### AI-6. `test_recall_cve_returns_notes` — investigate the 0-hit variant

- **File:** `tests/test_core.py`
- **Symptom:** `assert 0 >= 1` — vector recall returns empty.
- **Hypothesis 1:** The entity-index lookup hasn't flushed yet (same race as AI-5).
- **Hypothesis 2:** Fastembed lazy-init on first `recall()` races with the concurrent `remember()` embedding.
- **Fix candidates:** (a) force `sync=True` on the seed `remember()` calls in the fixture, (b) call `mm.rebuild_index()` before the first `recall()`, (c) add a tiny explicit wait on the embedding singleton.

### P4 — Clean up warnings (7 during last run)

Cheap hygiene fixes; none blocks CI but each one will become a hard
failure on a future dep bump.

#### AI-7. Pydantic V3 migration in `langchain_retriever.py`

- **File:** `src/zettelforge/integrations/langchain_retriever.py:31`
- **What:** `class ZettelForgeRetriever(BaseRetriever)` uses class-based `Config`; Pydantic V3 (already warning in V2.13) will remove it.
- **Fix:** Replace `class Config:` with `model_config = ConfigDict(...)`.

#### AI-8. `test_causal_extraction` returns bool instead of asserting

- **File:** `tests/test_causal_extraction.py`
- **What:** `PytestReturnNotNoneWarning: Test functions should return None, but ... returned <class 'bool'>.` Test function ends with `return <expr>` instead of `assert <expr>`.
- **Fix:** One-line change — `return` → `assert`.

#### AI-9. lancedb `table_names()` → `list_tables()`

- **File:** `src/zettelforge/vector_memory.py` (the one that triggers via `tests/test_core.py::TestLanceDBIntegration::test_lancedb_tables_created`)
- **What:** `DeprecationWarning: table_names() is deprecated, use list_tables() instead`.
- **Fix:** Rename the call sites; API is a drop-in replacement per lancedb docs.

#### AI-10. Fastembed "model updated on HuggingFace" warning

- **File:** `src/zettelforge/vector_memory.py:76`
- **What:** `UserWarning: The model 'nomic-ai/nomic-embed-text-v1.5-Q' has been updated on HuggingFace.`
- **Decision needed:** Pin to a specific revision (stable), accept the warning (status quo), or upgrade to `v1.5` full-precision (bigger download, slightly better quality).
- **Fix:** Add `revision="<commit-sha>"` to the `TextEmbedding(...)` call to pin to current behavior, and note the revision in `docs/reference/configuration.md` so future bumps are intentional.

---

## Priority recommendation

Ship in one PR:

1. **AI-5 + AI-6** (flake fixes) — eliminates the two known-flaky tests that have been failing PRs on first CI run this month.
2. **AI-8 + AI-9** (one-line warning fixes) — zero risk, green the warnings list.

Ship separately (each a small-to-medium PR):

3. **AI-1 + AI-2** — move from 10 CI skips to 10 CI-run contract tests via the mock provider. Meaningful coverage gain.
4. **AI-3 + AI-4** — xfail cleanup.
5. **AI-7** — Pydantic migration (coordinate with any other pydantic-touching changes).
6. **AI-10** — fastembed revision pin (requires a decision, not a typing sweep).

Defer: **Category C** (performance tests) — skip-in-CI is the right call.
Cadence: run `pytest tests/test_performance.py` on a dev box weekly and
append results to `benchmarks/BENCHMARK_REPORT.md`.

---

## Scope boundary

This audit covers **test-suite hygiene**. It does not cover:

- Coverage gaps (currently 64% — separate concern, tracked in governance).
- Test performance / runtime budget (13 s is healthy).
- Test environment bootstrapping (the local hang on lancedb C-extension
  calls is a platform quirk on NVIDIA-kernel hosts, not a CI issue).
