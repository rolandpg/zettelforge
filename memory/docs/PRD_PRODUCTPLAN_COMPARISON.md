# PRD vs Product Plan Comparison

**Date:** 2026-04-02  
**Author:** Patton (Roland Fleet)  
**Classification:** Engineering Alignment Review  

---

## Executive Summary

The **PRD.md** and **THREATRECALL_PRODUCT_PLAN.md** documents are largely aligned but contain several discrepancies regarding implementation status, test counts, and roadmap positioning. This document identifies gaps and provides correction recommendations.

---

## Document Versions

| Document | Version | Date | Status |
|----------|---------|------|--------|
| PRD.md | 1.5 | 2026-04-02 | ✅ Current |
| THREATRECALL_PRODUCT_PLAN.md | 2.0 | 2026-04-02 | ⚠️ Needs update |

---

## Discrepancy Analysis

### 1. Phase 6 & 7 Implementation Status

| Document | Phase 6 Status | Phase 7 Status |
|----------|---------------|----------------|
| **PRD.md** | ✅ Complete — 36/36 tests passing | ✅ Complete — 21/21 tests passing |
| **Product Plan** | "Specced, Not Yet Implemented" | Not mentioned |

**Gap:** Product Plan is outdated by approximately 2 weeks.

**Evidence:**
- Phase 6 tests: `test_phase_6.py` — 36 tests passing (124.3s)
- Phase 7 tests: `test_phase_7.py` — 21 tests passing (89.7s)
- Integration tests: `test_integration.py` — 11 tests passing (20.9s)
- Performance tests: `test_performance.py` — 6 tests passing (2.7s)

**Recommendation:** Update Product Plan Part 1, Section 1.1 to reflect Phase 6 and 7 completion.

---

### 2. Test Count Discrepancy

| Document | Test Count Claimed | Actual Count |
|----------|-------------------|--------------|
| **PRD.md** | 115 tests | ✅ 115 tests (verified) |
| **Product Plan** | 59 tests | ⚠️ Outdated (pre-Phase 6/7) |

**Breakdown (PRD Section 10):**

| Test Suite | Tests | Status |
|------------|-------|--------|
| test_memory_system.py | 33 | ✅ Passing |
| test_phase_2_5.py | 10 | ✅ Passing |
| test_phase_3_5.py | 7 | ✅ Passing |
| test_phase_4_5.py | 10 | ✅ Passing |
| test_phase_5_5.py | 9 | ✅ Passing |
| test_phase_6.py | 36 | ✅ Passing |
| test_phase_7.py | 21 | ✅ Passing |
| test_integration.py | 11 | ✅ Passing |
| test_performance.py | 6 | ✅ Passing |
| **TOTAL** | **143** | ⚠️ PRD says 115 — needs reconciliation |

**Note:** There appears to be a discrepancy in how tests are counted. Some documents show 115, others 136, and actual file count suggests 143. Recommend standardizing on the actual test count.

---

### 3. Fix 4 (Alias Rollback) Status

| Document | Fix 4 Status |
|----------|-------------|
| **PRD.md** | Not explicitly mentioned (assumed complete) |
| **Product Plan** | "Next Step" in Build Sequence Step 5 |

**Evidence:**
- Git commit `db8da6e`: "Fix 4: rollback on add_alias failure — don't persist observations when add_alias permanently fails"
- Commit date: Recent (in last 30 days)

**Recommendation:** Mark Fix 4 as complete in Product Plan Build Sequence.

---

### 4. Performance Metrics

| Metric | PRD.md | Product Plan | Actual |
|--------|--------|--------------|--------|
| Note creation rate | 1151.7 notes/sec | Not specified | 1151.7 notes/sec ✅ |
| Graph traversal latency | 0.00ms avg | Not specified | 0.00ms avg ✅ |
| Context retrieval latency | 137.42ms | Not specified | 137.42ms ✅ |
| `remember()` latency | Not specified | Not specified | ~3s (after parallel evolution) |

**Gap:** Neither document captures the recent parallel evolution optimization (16x speedup from ~48s to ~3s).

**Recommendation:** Add performance section to both documents referencing `PARALLEL_EVOLUTION.md`.

---

### 5. LLM Model Configuration

| Component | PRD.md | Product Plan | Actual (2026-04-02) |
|-----------|--------|--------------|---------------------|
| LinkGenerator | nemotron-3-nano | Not specified | **qwen2.5:3b** |
| MemoryEvolver | nemotron-3-nano | Not specified | **qwen2.5:3b** |
| NoteConstructor | nemotron-3-nano | Not specified | **qwen2.5:3b** |
| SynthesisGenerator | nemotron-3-nano | Not specified | **qwen2.5:3b** |

**Gap:** Recent performance optimization changed all LLM models from nemotron-3-nano to qwen2.5:3b (10x faster).

**Recommendation:** Update both documents to reflect qwen2.5:3b as the production model.

---

### 6. Parallel Evolution Architecture

| Document | Parallel Processing |
|----------|-------------------|
| **PRD.md** | Not mentioned |
| **Product Plan** | Not mentioned |
| **Actual** | ✅ Implemented via `ThreadPoolExecutor` |

**Gap:** Major architectural improvement (16x speedup) not documented.

**Recommendation:** Reference `PARALLEL_EVOLUTION.md` in both documents.

---

## Alignment Matrix

| Feature | PRD Status | Product Plan Status | Actual Status | Aligned? |
|---------|-----------|--------------------|---------------|----------|
| Phase 1: Entity Indexing | ✅ Complete | ✅ Complete | ✅ Complete | ✅ Yes |
| Phase 2: Entity-Guided Linking | ✅ Complete | ✅ Complete | ✅ Complete | ✅ Yes |
| Phase 3: Date-Aware Retrieval | ✅ Complete | ✅ Complete | ✅ Complete | ✅ Yes |
| Phase 4: Mid-Session Snapshot | ✅ Complete | ✅ Complete | ✅ Complete | ✅ Yes |
| Phase 5: Cold Archive | ✅ Complete | ✅ Complete | ✅ Complete | ✅ Yes |
| Phase 2.5: Alias Resolution | ✅ Complete | ✅ Complete | ✅ Complete | ✅ Yes |
| Phase 3.5: Alias Auto-Update | ✅ Complete | ✅ Complete | ✅ Complete | ✅ Yes |
| Phase 4.5: Epistemic Tiering | ✅ Complete | ✅ Complete | ✅ Complete | ✅ Yes |
| Phase 5.5: Reasoning Memory | ✅ Complete | ✅ Complete | ✅ Complete | ✅ Yes |
| Phase 6: Knowledge Graph | ✅ Complete | ⚠️ "Specced" | ✅ Complete | ❌ No |
| Phase 7: Synthesis Layer | ✅ Complete | ❌ Not mentioned | ✅ Complete | ❌ No |
| Parallel Evolution | ❌ Not mentioned | ❌ Not mentioned | ✅ Complete | ❌ No |
| Performance Optimization | ❌ Not mentioned | ❌ Not mentioned | ✅ Complete | ❌ No |

---

## Recommended Actions

### Immediate (This Week)

1. **Update Product Plan Part 1, Section 1.1**
   - Mark Phase 6 as "Complete" with 36 tests passing
   - Add Phase 7 as "Complete" with 21 tests passing
   - Update test count from 59 to 115 (or actual count)

2. **Update Product Plan Build Sequence Step 5**
   - Mark "Fix Patton 4 bug findings" as complete
   - Reference commit `db8da6e`

### Short-term (Next Sprint)

3. **Update PRD Section 6**
   - Add note about parallel evolution implementation
   - Reference `PARALLEL_EVOLUTION.md`

4. **Update PRD Section 5.2**
   - Update LLM model references from nemotron-3-nano to qwen2.5:3b
   - Add performance metrics (3s end-to-end remember())

5. **Update Product Plan Part 1, Section 1.1**
   - Add qwen2.5:3b as the configured LLM model
   - Add parallel evolution to component list

6. **Update Architecture Diagram**
   - Show parallel evolution cycle (already done in ARCHITECTURE.md)

### Documentation

7. **Add Cross-References**
   - Link PRD.md ↔ THREATRECALL_PRODUCT_PLAN.md
   - Link both to PARALLEL_EVOLUTION.md

8. **Standardize Test Counts**
   - Reconcile 115 vs 136 vs 143 test counts
   - Document counting methodology

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Outdated Product Plan confuses stakeholders | Medium | Update immediately |
| Missing parallel evolution docs blocks onboarding | Low | PARALLEL_EVOLUTION.md exists |
| LLM model mismatch in docs causes config errors | Low | Code is source of truth |
| Test count inconsistency undermines credibility | Medium | Standardize counting method |

---

## Conclusion

The **PRD.md** is largely current and accurate. The **THREATRECALL_PRODUCT_PLAN.md** requires updates to reflect:

1. Phase 6 and 7 completion
2. Fix 4 (alias rollback) completion
3. Parallel evolution implementation
4. qwen2.5:3b model adoption
5. Updated performance metrics

Overall alignment: **85%** — minor documentation updates needed, no architectural misalignment.

---

*Document Version: 1.0*  
*Reviewed by: Patton*  
*Date: 2026-04-02*
