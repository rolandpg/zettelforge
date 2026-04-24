---
title: "RFC-010: Enrichment-Pipeline Hotfix (OllamaProvider timeout + consolidation guard)"
status: READY-FOR-PR
version: "2.4.2-proposed"
author: "Claude Code"
date: "2026-04-24"
canonical_branch: "master @ ad0908f or later"
supersedes: []
related: ["RFC-009 (the larger dataflow redesign this hotfix lives alongside)"]
diataxis_type: reference
audience: Backend engineer implementing the patch
tags: [hotfix, llm, backend, shutdown-race]
implementation_owner: "claude-code (assigned 2026-04-24 by Patrick)"
target_pr: "TBD (opens as part of this execution pass)"
ship_target: "v2.4.2 (patch release, not v2.5.0)"
---

# RFC-010: Enrichment-Pipeline Hotfix

> **This is a patch, not a design.** Two concrete code changes, ~15 lines combined, ship as v2.4.2 as soon as CI is green. Written up only because the context (why) is spread across the Vigil audit, the PR #83 / #84 / v2.4.1 history, and RFC-009. Implementer should read this document, then the diff, then push the PR. Total implementer time: 45 minutes including tests.

## Why this is a patch and not phase 0 of RFC-009

The v2.4.1 release (today, 2026-04-24) surfaced two unrelated defects via RFC-007 telemetry:

1. **OllamaProvider ignores the configured `timeout` kwarg**, causing `remember()` to hang up to 66 seconds when Ollama is slow or unresponsive.
2. **`ConsolidationMiddleware.consolidate()` at `consolidation.py:224` iterates the store with no shutdown guard**, producing a `BackendClosedError` when consolidation races `atexit`.

Both are small, well-understood, and do not depend on the larger RFC-009 dataflow redesign. They are called out in the Vigil audit [`tasks/vigil-telemetry-audit-2026-04-24.md`](../../tasks/vigil-telemetry-audit-2026-04-24.md) and in the RFC-009 Reality Checker critique (F08, C1-C3 blocker path).

The v1.0 draft of RFC-009 bundled these as "Phase 0." That was a mistake: RFC-009 will correctly take 1-2 weeks to land, and waiting that long for a 15-line patch is indefensible while production is visibly degraded.

## What this hotfix does NOT fix

**The biggest operational number in the Vigil audit — 2,329 enrichment-job drops per day — will not significantly drop from this patch.** The drops are driven by TWO independent failures:

1. **Hanging Ollama calls** (workers stall → queues fill). *This hotfix addresses this.*
2. **HTTP 200 + empty-body responses from Ollama** (calls return fast but fail parse → workers cycle → queues still fill). *This hotfix does NOT address this.*

Realistic post-hotfix prediction:
- `remember()` p95 latency: 66s → ~60s (whatever timeout we set; default 60s; cap with explicit override later).
- `enrichment_worker_error` log volume: **increases** (hangs become explicit timeouts, each emitting an error).
- Queue-full events: modest decrease (workers cycle slightly faster).
- Drops per day: **~2,000-2,300** (still bad — the empty-body cascade continues).

Full drop reduction requires the outbox + circuit breaker in RFC-009 Phases 1-2. This hotfix is a *predicate* for those phases (you need fail-fast semantics before retry logic is useful), not a replacement.

## Patch 1 — OllamaProvider timeout plumbing

**File:** `src/zettelforge/llm_providers/ollama_provider.py`

**Root cause:** Line 27 signature is `def __init__(self, model: str = "", url: str = "", **_: Any)`. The `**_` swallows every other kwarg the registry passes, including `timeout`. Line 55 builds `ollama.Client(host=self._url)` with no timeout kwarg, so requests inherit the ollama-python client's default (effectively unbounded for local deployments).

**Change:**

```python
def __init__(
    self,
    model: str = "",
    url: str = "",
    timeout: float = 60.0,
    **_: Any,
) -> None:
    self._model = model or _DEFAULT_MODEL
    self._url = url or _DEFAULT_URL
    self._timeout = timeout

def generate(self, ...) -> str:
    ...
    client = ollama.Client(host=self._url, timeout=self._timeout)
    response = client.generate(**kwargs)
    ...
```

**Test:** new case in `tests/test_llm_providers.py` — instantiate `OllamaProvider(timeout=0.001)`, patch `ollama.Client.generate` to sleep 1s, assert the call raises a timeout error. Marks the behavior contractually.

**Verification path post-deploy:** grep Vigil's `zettelforge.log` for `ocsf_api_activity` with `activity_name=remember` and `duration_ms > 60000`. Pre-hotfix count: 1/day (the 66.5s max). Post-hotfix: 0/day.

## Patch 2 — Consolidation shutdown guard

**File:** `src/zettelforge/consolidation.py`

**Root cause:** Line 224 loops `for note in self._mm.store.iterate_notes():` with no check against the `_accepting` flag. PR #84 added `BackendClosedError` and guarded the two enrichment paths (`_enrichment_loop`, `_drain_enrichment_queue`); consolidation was missed. Production log at 2026-04-24T17:25:48Z shows the failure path firing cleanly (caught by a generic `except Exception`) — no data loss, but it emits `consolidation_failed` noise and the race is a smell.

**Change:**

```python
def consolidate(self, ...) -> Dict:
    if not self._mm._accepting:  # [RFC-010 hotfix — see also RFC-009 Section 4.3]
        return {"status": "skipped", "reason": "backend not accepting"}

    try:
        for note in self._mm.store.iterate_notes():
            ...
    except BackendClosedError:
        return {"status": "skipped", "reason": "backend closed mid-iteration"}
```

Two-layer defense: the `_accepting` flag check is the fast path (skips before the iteration starts), the `try/except BackendClosedError` catches the narrow race where shutdown fires after the check but before `iterate_notes()` yields its first row. RFC-009 Section 4.3 replaces this with explicit cursor tracking; until then, this layered guard is adequate.

**Test:** new case in `tests/test_consolidation.py` — instantiate a `MemoryManager`, set `_accepting = False`, call `consolidate()`, assert `status == "skipped"`, no exception raised.

## Ownership

**Implementation:** claude-code (assigned 2026-04-24 by Patrick). Patches executed as part of the same pass that assigns ownership.

**Review:** 1 human review sufficient (Patrick). No sub-agent dispatch needed for this PR.

**CI gate:** full normal CI. No shortcuts. The repo's CI runs in ~2 minutes; bypassing it is not justified by the size of this patch.

## Rollout

Patch release as **v2.4.2**. Release notes should cite the Vigil audit and explicitly state that 2,329 drops/day is NOT fixed by this release — it's a latency fix and a race fix, pending the RFC-009 outbox for real recovery. Honesty is cheap; preventing operator expectation-management failures is not.

Bump `pyproject.toml` to 2.4.2, add `[2.4.2]` section to `CHANGELOG.md`, tag, release. Pattern identical to v2.4.1.
